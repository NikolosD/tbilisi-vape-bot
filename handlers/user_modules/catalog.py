from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from database import db
from keyboards import (
    get_product_card_keyboard, get_quantity_input_cancel_keyboard
)
from message_manager import message_manager
from i18n import _
from button_filters import is_catalog_button
from pages.manager import page_manager

logger = logging.getLogger(__name__)

router = Router()

class CatalogStates(StatesGroup):
    waiting_quantity_input = State()

# Обработчик текстовых сообщений из главного меню
@router.message(is_catalog_button)
async def show_catalog(message: Message):
    """Показать каталог категорий"""
    await page_manager.catalog.show_from_message(message)

# Обработчики callback-запросов
@router.callback_query(F.data == "catalog")
async def callback_catalog(callback: CallbackQuery):
    """Показать каталог категорий через callback"""
    await page_manager.catalog.show_from_callback(callback)

@router.callback_query(F.data.startswith("category_"))
async def show_category_products(callback: CallbackQuery):
    """Показать товары выбранной категории"""
    category_id = int(callback.data.split("_")[1])
    await page_manager.catalog.show_from_callback(callback, category_id=category_id)

@router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    """Показать карточку товара"""
    data_parts = callback.data.split("_")
    product_id = int(data_parts[1])
    
    # Проверяем, пришли ли из категории  
    from_category = None
    if len(data_parts) > 3 and data_parts[2] == "from":
        from_category = int(data_parts[3])
    
    await page_manager.catalog.show_from_callback(callback, product_id=product_id, from_category=from_category)

@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery):
    """Добавить товар в корзину"""
    product_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    # Проверяем существование товара
    product = await db.get_product(product_id)
    if not product or not product.in_stock or product.stock_quantity <= 0:
        await callback.answer(_("common.error"), show_alert=True)
        return
    
    # Убеждаемся, что пользователь существует в базе
    user = await db.get_user(user_id)
    if not user:
        # Добавляем пользователя в базу
        await db.add_user(
            user_id=user_id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name
        )
    
    # Проверяем текущее количество в корзине
    cart_items = await db.get_cart(user_id)
    current_quantity_in_cart = 0
    for item in cart_items:
        if item.product_id == product_id:
            current_quantity_in_cart = item.quantity
            break
    
    # Проверяем, не превышает ли добавление лимит склада
    if current_quantity_in_cart >= product.stock_quantity:
        await callback.answer(
            _("error.max_quantity", user_id=callback.from_user.id, quantity=product.stock_quantity, current=current_quantity_in_cart), 
            show_alert=True
        )
        return
    
    # Добавляем в корзину
    await db.add_to_cart(user_id, product_id, 1)
    
    # Получаем количество в корзине после добавления
    cart_items = await db.get_cart(user_id)
    quantity_in_cart = 0
    for item in cart_items:
        if item.product_id == product_id:
            quantity_in_cart = item.quantity
            break
    
    await callback.answer(_("cart.item_added"))
    
    # Получаем from_category из исходного callback_data если есть
    original_data = callback.message.reply_markup.inline_keyboard
    from_category = None
    for row in original_data:
        for button in row:
            if button.callback_data and button.callback_data.startswith("category_"):
                from_category = int(button.callback_data.split("_")[1])
                break
    
    # Обновляем текст товара с информацией о количестве в корзине
    product_text = f"🛍️ {product.name}\n\n"
    product_text += f"{product.description}\n\n"
    product_text += f"💰 Цена: {product.price}₾\n"
    product_text += f"📦 {'В наличии' if product.in_stock else 'Нет в наличии'}\n"
    if quantity_in_cart > 0:
        product_text += f"🛒 В корзине: {quantity_in_cart} шт."
    
    # Обновляем сообщение с новым текстом и кнопками
    keyboard = get_product_card_keyboard(product_id, in_cart=True, from_category=from_category)
    
    # Пытаемся отредактировать текущее сообщение
    try:
        await callback.message.edit_text(product_text, reply_markup=keyboard, parse_mode='HTML')
    except Exception:
        # Если не получается отредактировать, удаляем и создаем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        await message_manager.send_or_edit_message(
            callback.bot, user_id,
            product_text,
            reply_markup=keyboard,
            menu_state='product_view',
            force_new=True
        )

# Обработчик для ввода количества
@router.callback_query(F.data.startswith("set_quantity_"))
async def set_quantity(callback: CallbackQuery, state: FSMContext):
    """Установить количество товара"""
    product_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Извлекаем from_category из клавиатуры
    from_category = None
    if callback.message.reply_markup:
        for row in callback.message.reply_markup.inline_keyboard:
            for button in row:
                if button.callback_data and button.callback_data.startswith("category_"):
                    from_category = int(button.callback_data.split("_")[1])
                    break
    
    # Сохраняем информацию о товаре в состоянии
    await state.update_data(
        product_id=product_id,
        original_message_id=callback.message.message_id,
        original_text=callback.message.text,
        original_markup=callback.message.reply_markup,
        from_category=from_category  # Сохраняем категорию для правильного возврата
    )
    
    # Редактируем сообщение и сохраняем его ID для последующего удаления
    quantity_message = await callback.message.edit_text(
        "🔢 <b>Введите количество товара:</b>\n\n"
        "📝 Отправьте число от 1 до 999",
        reply_markup=get_quantity_input_cancel_keyboard(),
        parse_mode='HTML'
    )
    
    # Обновляем state с ID сообщения для ввода количества
    await state.update_data(quantity_message_id=quantity_message.message_id)
    
    await state.set_state(CatalogStates.waiting_quantity_input)

@router.callback_query(F.data.startswith("cancel_quantity_") & ~F.data.endswith("_input"))
async def cancel_quantity(callback: CallbackQuery, state: FSMContext):
    """Отменить ввод количества"""
    product_id = int(callback.data.split("_")[2])
    
    # Восстанавливаем исходное сообщение
    data = await state.get_data()
    if 'original_text' in data and 'original_markup' in data:
        await callback.message.edit_text(
            data['original_text'],
            reply_markup=data['original_markup'],
            parse_mode='HTML'
        )
    
    await state.clear()
    await callback.answer("❌ Ввод количества отменен")

@router.message(CatalogStates.waiting_quantity_input)
async def process_quantity_input(message: Message, state: FSMContext):
    """Обработка ввода количества"""
    user_id = message.from_user.id
    data = await state.get_data()
    product_id = data.get('product_id')
    
    if not product_id:
        await message.answer("❌ Ошибка: не найден товар")
        await state.clear()
        return
    
    try:
        quantity = int(message.text.strip())
        
        if quantity < 1 or quantity > 999:
            await message.answer(
                _("error.quantity_range", user_id=user_id),
                reply_markup=get_quantity_input_cancel_keyboard()
            )
            return
        
        # Проверяем товар и его наличие
        product = await db.get_product(product_id)
        if not product or not product.in_stock:
            await message.answer(_("error.product_unavailable", user_id=user_id))
            await state.clear()
            return
        
        if quantity > product.stock_quantity:
            await message.answer(
                _("error.stock_limit", user_id=user_id, stock=product.stock_quantity),
                reply_markup=get_quantity_input_cancel_keyboard()
            )
            return
        
        # Обновляем количество в корзине
        await db.update_cart_quantity(user_id, product_id, quantity)
        
        # Удаляем сообщение пользователя
        await message.delete()
        
        # Удаляем сообщение с инструкцией ввода количества
        quantity_message_id = data.get('quantity_message_id')
        if quantity_message_id:
            try:
                await message.bot.delete_message(chat_id=user_id, message_id=quantity_message_id)
            except Exception:
                pass  # Сообщение уже могло быть удалено
        
        # Получаем обновленную информацию о корзине
        cart_items = await db.get_cart(user_id)
        quantity_in_cart = 0
        for item in cart_items:
            if item.product_id == product_id:
                quantity_in_cart = item.quantity
                break
        
        # Формируем обновленный текст товара
        product_text = f"🛍️ {product.name}\n\n"
        product_text += f"{product.description}\n\n"
        product_text += f"💰 Цена: {product.price}₾\n"
        product_text += f"📦 {'В наличии' if product.in_stock else 'Нет в наличии'}\n"
        if quantity_in_cart > 0:
            product_text += f"🛒 В корзине: {quantity_in_cart} шт."
        
        # Получаем from_category из данных состояния или сообщения
        from_category = data.get('from_category')
        if not from_category and data.get('original_markup'):
            for row in data['original_markup'].inline_keyboard:
                for button in row:
                    if button.callback_data and button.callback_data.startswith("category_"):
                        from_category = int(button.callback_data.split("_")[1])
                        break
        
        # Отправляем новое сообщение (по ID из данных состояния)
        original_message_id = data.get('original_message_id')
        
        try:
            await message.bot.edit_message_text(
                chat_id=user_id,
                message_id=original_message_id,
                text=product_text,
                reply_markup=get_product_card_keyboard(product_id, in_cart=True, from_category=from_category),
                parse_mode='HTML'
            )
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await message.answer(
                product_text,
                reply_markup=get_product_card_keyboard(product_id, in_cart=True, from_category=from_category),
                parse_mode='HTML'
            )
        
        
    except ValueError:
        await message.answer(
            _("error.invalid_number", user_id=user_id),
            reply_markup=get_quantity_input_cancel_keyboard()
        )
        return
    
    await state.clear()

@router.callback_query(F.data == "cancel_quantity_input", CatalogStates.waiting_quantity_input)
async def cancel_quantity_input(callback: CallbackQuery, state: FSMContext):
    """Отмена ввода количества"""
    user_id = callback.from_user.id
    data = await state.get_data()
    product_id = data.get('product_id')
    
    await state.clear()
    
    if not product_id:
        await callback.answer(_("error.product_not_found", user_id=user_id))
        return
    
    # Получаем товар и информацию о корзине
    product = await db.get_product(product_id)
    if not product:
        await callback.answer(_("error.product_not_found", user_id=user_id))
        return
    
    cart_items = await db.get_cart(user_id)
    quantity_in_cart = 0
    for item in cart_items:
        if item.product_id == product_id:
            quantity_in_cart = item.quantity
            break
    
    # Формируем текст товара
    product_text = f"🛍️ {product.name}\n\n"
    product_text += f"{product.description}\n\n"
    product_text += f"💰 {_('product.price', user_id=user_id)} {product.price}₾\n"
    product_text += f"📦 {_('product.in_stock', user_id=user_id) if product.in_stock else _('product.out_of_stock', user_id=user_id)}\n"
    if quantity_in_cart > 0:
        product_text += f"🛒 {_('product.in_cart_quantity', user_id=user_id)} {quantity_in_cart} {_('product.pieces', user_id=user_id)}"
    
    # Получаем from_category из данных состояния
    from_category = data.get('from_category')
    
    # Обновляем сообщение
    try:
        await callback.message.edit_text(
            product_text,
            reply_markup=get_product_card_keyboard(product_id, in_cart=(quantity_in_cart > 0), from_category=from_category),
            parse_mode='HTML'
        )
    except Exception:
        # Если не удалось отредактировать, отправляем новое сообщение
        await callback.message.answer(
            product_text,
            reply_markup=get_product_card_keyboard(product_id, in_cart=(quantity_in_cart > 0), from_category=from_category),
            parse_mode='HTML'
        )
    
    await callback.answer(_("error.quantity_input_cancelled", user_id=user_id))