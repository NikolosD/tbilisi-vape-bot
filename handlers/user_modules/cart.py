from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from database import db
from keyboards import (
    get_cart_keyboard, get_product_card_keyboard, get_back_to_menu_keyboard
)
from message_manager import message_manager
from i18n import _
from button_filters import is_cart_button
from pages.manager import page_manager

logger = logging.getLogger(__name__)

router = Router()

class CartStates(StatesGroup):
    waiting_cart_quantity_input = State()

# Обработчик текстовых сообщений из главного меню
@router.message(is_cart_button)
async def show_cart(message: Message):
    """Показать корзину"""
    await page_manager.cart.show_from_message(message)

@router.callback_query(F.data == "cart")
async def callback_cart(callback: CallbackQuery):
    """Показать корзину через callback"""
    await page_manager.cart.show_from_callback(callback)

@router.callback_query(F.data.startswith("cart_increase_"))
async def cart_increase(callback: CallbackQuery):
    """Увеличить количество товара в корзине"""
    product_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    logger.info(f"Увеличение количества товара {product_id} для пользователя {user_id}")
    logger.info(f"Текст сообщения: {callback.message.text[:100]}...")
    
    # Проверяем товар и его количество на складе
    product = await db.get_product(product_id)
    if not product or not product.in_stock or product.stock_quantity <= 0:
        await callback.answer(_("error.product_unavailable", user_id=callback.from_user.id), show_alert=True)
        return
    
    # Получаем текущее количество
    cart_items = await db.get_cart(user_id)
    current_quantity = 0
    for item in cart_items:
        if item.product_id == product_id:
            current_quantity = item.quantity
            break
    
    # Проверяем, не превышает ли увеличение лимит склада
    if current_quantity >= product.stock_quantity:
        await callback.answer(
            _("error.max_quantity", user_id=callback.from_user.id, quantity=product.stock_quantity, current=0), 
            show_alert=True
        )
        return
    
    new_quantity = current_quantity + 1
    await db.update_cart_quantity(user_id, product_id, new_quantity)
    
    await callback.answer(_("cart.quantity_increased", quantity=new_quantity))
    
    # Проверяем, находимся ли мы на странице товара или в корзине
    message_text = callback.message.text or ""
    if "🛒 Ваша корзина:" in message_text:
        # Мы в корзине - обновляем отображение корзины
        logger.info("Обновляем отображение корзины...")
        await update_cart_display(callback)
    else:
        # Мы на странице товара - обновляем отображение товара с новым количеством
        logger.info("Обновляем отображение товара...")
        product = await db.get_product(product_id)
        if product:
            # Получаем информацию о количестве в корзине
            cart_items = await db.get_cart(user_id)
            quantity_in_cart = 0
            for item in cart_items:
                if item.product_id == product_id:
                    quantity_in_cart = item.quantity
                    break
            
            # Формируем обновленный текст товара с количеством
            product_text = f"🛍️ {product.name}\n\n"
            product_text += f"{product.description}\n\n"
            product_text += f"💰 Цена: {product.price}₾\n"
            product_text += f"📦 {'В наличии' if product.in_stock else 'Нет в наличии'}\n"
            if quantity_in_cart > 0:
                product_text += f"🛒 В корзине: {quantity_in_cart} шт."
            
            # Получаем from_category из кнопок
            from_category = None
            for row in callback.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.callback_data and button.callback_data.startswith("category_"):
                        from_category = int(button.callback_data.split("_")[1])
                        break
            
            # Обновляем сообщение
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

@router.callback_query(F.data.startswith("cart_decrease_"))
async def cart_decrease(callback: CallbackQuery):
    """Уменьшить количество товара в корзине"""
    product_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    logger.info(f"Уменьшение количества товара {product_id} для пользователя {user_id}")
    
    # Получаем текущее количество
    cart_items = await db.get_cart(user_id)
    current_quantity = 0
    for item in cart_items:
        if item.product_id == product_id:
            current_quantity = item.quantity
            break
    
    if current_quantity <= 1:
        await db.remove_from_cart(user_id, product_id)
        await callback.answer(_("cart.item_deleted"))
    else:
        new_quantity = current_quantity - 1
        await db.update_cart_quantity(user_id, product_id, new_quantity)
        await callback.answer(_("cart.quantity_decreased", quantity=new_quantity))
    
    # Проверяем, находимся ли мы на странице товара или в корзине
    message_text = callback.message.text or ""
    if "🛒 Ваша корзина:" in message_text:
        # Мы в корзине - обновляем отображение корзины
        logger.info("Обновляем отображение корзины...")
        await update_cart_display(callback)
    else:
        # Мы на странице товара - обновляем отображение товара
        logger.info("Обновляем отображение товара...")
        product = await db.get_product(product_id)
        if product:
            # Получаем обновленную информацию о количестве в корзине
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
            
            # Получаем from_category из кнопок
            from_category = None
            for row in callback.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.callback_data and button.callback_data.startswith("category_"):
                        from_category = int(button.callback_data.split("_")[1])
                        break
            
            # Определяем правильную клавиатуру в зависимости от количества
            keyboard = get_product_card_keyboard(product_id, in_cart=(quantity_in_cart > 0), from_category=from_category)
            
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

@router.callback_query(F.data.startswith("cart_remove_"))
async def cart_remove(callback: CallbackQuery):
    """Удалить товар из корзины"""
    product_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    logger.info(f"Удаление товара {product_id} из корзины пользователя {user_id}")
    
    product = await db.get_product(product_id)
    await db.remove_from_cart(user_id, product_id)
    
    await callback.answer(_("cart.item_removed"))
    
    # Обновляем корзину если мы на странице корзины
    if "cart" in callback.message.text:
        logger.info("Обновляем отображение корзины...")
        await update_cart_display(callback)
    else:
        # Получаем from_category из исходного callback_data если есть
        original_data = callback.message.reply_markup.inline_keyboard
        from_category = None
        for row in original_data:
            for button in row:
                if button.callback_data and button.callback_data.startswith("category_"):
                    from_category = int(button.callback_data.split("_")[1])
                    break
        
        # Обновляем кнопки на странице товара
        keyboard = get_product_card_keyboard(product_id, in_cart=False, from_category=from_category)
        await callback.message.edit_reply_markup(reply_markup=keyboard)

@router.callback_query(F.data.startswith("cart_input_qty_"))
async def cart_input_quantity(callback: CallbackQuery, state: FSMContext):
    """Запросить ввод количества товара в корзине"""
    product_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    # Получаем информацию о товаре
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    # Получаем текущее количество в корзине
    cart_items = await db.get_cart(user_id)
    current_quantity = 0
    for item in cart_items:
        if item.product_id == product_id:
            current_quantity = item.quantity
            break
    
    # Сохраняем product_id в состояние
    await state.update_data(cart_product_id=product_id, cart_current_quantity=current_quantity)
    await state.set_state(CartStates.waiting_cart_quantity_input)
    
    # Отправляем сообщение с запросом количества используя message_manager
    await message_manager.send_or_edit_message(
        callback.bot, user_id,
        f"🔢 <b>Введите новое количество для товара:</b>\n\n"
        f"🛍️ {product.name}\n"
        f"📦 Текущее количество: {current_quantity} шт.\n"
        f"📦 Доступно на складе: {product.stock_quantity} шт.\n\n"
        f"💡 Введите число от 0 до {product.stock_quantity}\n"
        f"(0 - удалить товар из корзины)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_quantity_input")]
        ]),
        menu_state='quantity_input',
        force_new=True
    )
    
    await callback.answer()

@router.message(CartStates.waiting_cart_quantity_input)
async def process_cart_quantity_input(message: Message, state: FSMContext):
    """Обработать ввод количества для корзины"""
    user_id = message.from_user.id
    
    try:
        quantity = int(message.text)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число")
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    product_id = data.get('cart_product_id')
    current_quantity = data.get('cart_current_quantity', 0)
    
    if not product_id:
        await message.answer("❌ Ошибка. Попробуйте снова.")
        await state.clear()
        return
    
    # Получаем товар для проверки наличия
    product = await db.get_product(product_id)
    if not product:
        await message.answer("❌ Товар не найден")
        await state.clear()
        return
    
    # Проверяем количество
    if quantity < 0:
        await message.answer("❌ Количество не может быть отрицательным")
        return
    
    if quantity > product.stock_quantity:
        await message.answer(f"❌ Недостаточно товара на складе. Доступно: {product.stock_quantity} шт.")
        return
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    if quantity == 0:
        # Удаляем товар из корзины
        await db.remove_from_cart(user_id, product_id)
        result_text = "✅ Товар удален из корзины"
    else:
        # Обновляем количество
        await db.update_cart_quantity(user_id, product_id, quantity)
        result_text = f"✅ Количество обновлено: {quantity} шт."
    
    # Очищаем состояние
    await state.clear()
    
    # Удаляем сообщение с запросом количества
    try:
        await message_manager.delete_user_message(message.bot, user_id)
    except:
        pass
    
    # Показываем обновленную корзину с уведомлением об успехе
    cart_items = await db.get_cart(user_id)
    
    if not cart_items:
        cart_text = "🛒 Ваша корзина пуста"
        keyboard = get_back_to_menu_keyboard()
    else:
        total = sum(item.price * item.quantity for item in cart_items)
        cart_text = f"🛒 Ваша корзина:\n\n"
        
        for item in cart_items:
            cart_text += f"🛍️ {item.name}\n"
            cart_text += f"📦 {item.quantity} шт. × {item.price}₾ = {item.price * item.quantity}₾\n\n"
        
        cart_text += f"💰 Итого: {total}₾\n\n"
        cart_text += f"✅ {result_text}"
        
        keyboard = get_cart_keyboard(cart_items)
    
    # Используем message_manager для правильного управления сообщениями
    await message_manager.send_or_edit_message(
        message.bot, user_id,
        cart_text,
        reply_markup=keyboard,
        menu_state='cart',
        force_new=False  # Попытаемся отредактировать существующее сообщение
    )

@router.callback_query(F.data == "cancel_quantity_input")
async def cancel_quantity_input(callback: CallbackQuery, state: FSMContext):
    """Отмена ввода количества"""
    user_id = callback.from_user.id
    await state.clear()
    
    # Удаляем сообщение с запросом количества
    try:
        await message_manager.delete_user_message(callback.bot, user_id)
    except:
        pass
    
    await callback.answer("❌ Ввод количества отменен")
    
    # Возвращаемся к корзине, используя message_manager
    cart_items = await db.get_cart(user_id)
    
    if not cart_items:
        cart_text = "🛒 Ваша корзина пуста"
        keyboard = get_back_to_menu_keyboard()
    else:
        total = sum(item.price * item.quantity for item in cart_items)
        cart_text = f"🛒 Ваша корзина:\n\n"
        
        for item in cart_items:
            cart_text += f"🛍️ {item.name}\n"
            cart_text += f"📦 {item.quantity} шт. × {item.price}₾ = {item.price * item.quantity}₾\n\n"
        
        cart_text += f"💰 Итого: {total}₾"
        
        keyboard = get_cart_keyboard(cart_items)
    
    # Используем message_manager для правильного управления сообщениями
    await message_manager.send_or_edit_message(
        callback.bot, user_id,
        cart_text,
        reply_markup=keyboard,
        menu_state='cart',
        force_new=False
    )

async def update_cart_display(callback: CallbackQuery):
    """Обновить отображение корзины"""
    user_id = callback.from_user.id
    cart_items = await db.get_cart(user_id)
    
    if not cart_items:
        await message_manager.send_or_edit_message(
            callback.bot, user_id,
            "🛒 <b>Ваша корзина пуста</b>\n\nДобавьте товары из каталога!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("common.to_catalog"), callback_data="catalog")],
                [InlineKeyboardButton(text=_("common.main_menu"), callback_data="back_to_menu")]
            ]),
            menu_state='cart',
            force_new=True
        )
        return
    
    total = sum(item.quantity * item.price for item in cart_items)
    
    cart_text = f"{_('cart.title', user_id=user_id)}\n\n"
    for item in cart_items:
        cart_text += _("cart.item", 
                      name=item.name,
                      quantity=item.quantity, 
                      price=item.price,
                      total=item.price * item.quantity,
                      user_id=user_id)
    
    cart_text += _("cart.total", total=total, user_id=user_id)
    
    await message_manager.send_or_edit_message(
        callback.bot, user_id,
        cart_text,
        reply_markup=get_cart_keyboard(cart_items),
        menu_state='cart',
        force_new=False  # Попытаемся отредактировать существующее сообщение
    )

@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
    """Очистить корзину"""
    user_id = callback.from_user.id
    await db.clear_cart(user_id)
    
    await message_manager.handle_callback_navigation(
        callback,
        "🗑 <b>Корзина очищена</b>\n\nДобавьте товары из каталога!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=_("common.to_catalog", user_id=user_id), callback_data="catalog")],
            [InlineKeyboardButton(text=_("common.main_menu", user_id=user_id), callback_data="back_to_menu")]
        ]),
        menu_state='cart_cleared'
    )