from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Contact, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
import logging

from database import db
from config import DELIVERY_ZONES, MIN_ORDER_AMOUNT, PAYMENT_INFO, ADMIN_IDS
from models import OrderStatus
from message_manager import message_manager

# Настройка логгера
logger = logging.getLogger(__name__)
from keyboards import (
    get_main_menu, get_main_menu_inline, get_categories_keyboard, get_catalog_keyboard, get_category_products_keyboard, get_product_card_keyboard,
    get_cart_keyboard, get_location_request_keyboard, get_location_inline_keyboard, get_order_confirmation_keyboard,
    get_orders_keyboard, get_order_details_keyboard, get_contact_keyboard, get_language_keyboard, get_back_to_menu_keyboard,
    get_quantity_input_cancel_keyboard
)

# Вспомогательная функция для удаления сообщений с задержкой
async def delete_message_after_delay(bot, chat_id, message_id, delay_seconds):
    """Удалить сообщение через указанное количество секунд"""
    import asyncio
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass  # Игнорируем ошибки если сообщение уже удалено
import i18n
from i18n import _
from button_filters import (
    is_catalog_button, is_cart_button, is_orders_button, 
    is_contact_button, is_info_button, is_language_button
)
from pages.manager import page_manager


router = Router()

# Состояния для FSM
class OrderStates(StatesGroup):
    waiting_contact = State()
    waiting_location = State()
    waiting_address = State()
    waiting_payment_screenshot = State()
    waiting_admin_message = State()
    waiting_quantity_input = State()
    waiting_cart_quantity_input = State()

# Обработчик текстовых сообщений из главного меню
@router.message(is_catalog_button)
async def show_catalog(message: Message):
    """Показать каталог категорий"""
    await page_manager.catalog.show_from_message(message)

@router.message(is_cart_button)
async def show_cart(message: Message):
    """Показать корзину"""
    await page_manager.cart.show_from_message(message)

@router.message(is_orders_button)
async def show_orders(message: Message):
    """Показать заказы пользователя"""
    await page_manager.orders.show_from_message(message)

@router.message(is_contact_button)
async def show_contact(message: Message):
    """Показать контактную информацию"""
    await page_manager.profile.show_from_message(message, type='contact')


# Обработчик кнопки смены языка
@router.message(is_language_button)
async def show_language_selection(message: Message):
    """Показать выбор языка"""
    await page_manager.profile.show_from_message(message, type='language')

@router.message(is_info_button)
async def show_info(message: Message):
    """Показать информацию о магазине"""
    await page_manager.info.show_from_message(message)

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

@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    """Обработчик для неактивных кнопок"""
    await callback.answer()

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
    await state.set_state(OrderStates.waiting_cart_quantity_input)
    
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

@router.message(OrderStates.waiting_cart_quantity_input)
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
    
    await state.set_state(OrderStates.waiting_quantity_input)

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

@router.message(OrderStates.waiting_quantity_input)
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

@router.callback_query(F.data == "cancel_quantity_input", OrderStates.waiting_quantity_input)
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

@router.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    """Начать оформление заказа"""
    user_id = callback.from_user.id
    cart_items = await db.get_cart(user_id)
    
    if not cart_items:
        await callback.answer(_("cart.empty"), show_alert=True)
        return
    
    total = sum(item[1] * item[3] for item in cart_items)
    
    if total < MIN_ORDER_AMOUNT:
        await callback.answer(
            _("error.min_order_amount", user_id=callback.from_user.id, amount=MIN_ORDER_AMOUNT),
            show_alert=True
        )
        return
    
    # Удаляем inline сообщение и отправляем новое с Reply клавиатурой
    await callback.message.delete()
    
    print(f"DEBUG: Пользователь {user_id} начал checkout, отправляем Reply клавиатуру")
    
    location_request_msg = await callback.message.answer(
        _("checkout.location_request", user_id=user_id).format(total=total),
        reply_markup=get_location_request_keyboard(user_id=user_id),
        parse_mode='HTML'
    )
    
    await state.set_state(OrderStates.waiting_location)
    await state.update_data(total=total, location_request_msg_id=location_request_msg.message_id)
    
    print(f"DEBUG: Состояние установлено на waiting_location для пользователя {user_id}")

# Обработчик геолокации (ДОЛЖЕН БЫТЬ ВЫШЕ ТЕКСТОВОГО!)
@router.message(OrderStates.waiting_location, F.location)
async def process_location(message: Message, state: FSMContext):
    """Обработка полученной геолокации"""
    user_id = message.from_user.id
    location = message.location
    
    current_state = await state.get_state()
    print(f"DEBUG: Получена геолокация от пользователя {user_id}: lat={location.latitude}, lon={location.longitude}")
    print(f"DEBUG: Текущее состояние пользователя {user_id}: {current_state}")
    
    # Убираем Reply клавиатуру
    from aiogram.types import ReplyKeyboardRemove
    
    # Сохраняем координаты
    await state.update_data(
        latitude=location.latitude,
        longitude=location.longitude
    )
    
    location_msg = await message.answer(
        _("checkout.location_received", user_id=user_id).format(
            lat=location.latitude,
            lon=location.longitude
        ),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )
    
    # Переходим к вводу точного адреса
    address_msg = await message.answer(
        _("checkout.enter_exact_address", user_id=user_id),
        parse_mode='HTML'
    )
    
    # Сохраняем ID сообщений для последующего удаления
    await state.update_data(
        location_msg_id=location_msg.message_id,
        address_msg_id=address_msg.message_id,
        location_map_msg_id=message.message_id  # ID сообщения с картой геолокации
    )
    
    await state.set_state(OrderStates.waiting_address)

# Обработчик для текстовой кнопки "Ввести адрес вручную" из Reply клавиатуры
@router.message(OrderStates.waiting_location, F.text)
async def handle_manual_address_text(message: Message, state: FSMContext):
    """Обработка нажатия кнопки 'Ввести адрес вручную' в Reply клавиатуре"""
    user_id = message.from_user.id
    
    print(f"DEBUG: Получен текст от пользователя {user_id}: '{message.text}'")
    
    # Проверяем, что это именно кнопка "Ввести адрес вручную"
    if message.text == _("checkout.manual_address", user_id=user_id):
        # Убираем Reply клавиатуру и отправляем сообщение с запросом адреса
        from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
        
        await message.answer(
            _("checkout.enter_address", user_id=user_id),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        
        address_msg = await message.answer(
            "👆 Введите адрес в следующем сообщении:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("common.back", user_id=user_id), callback_data="cart")]
            ])
        )
        
        # Получаем существующие данные и сохраняем ID сообщения для последующего удаления
        data = await state.get_data()
        await state.update_data(address_msg_id=address_msg.message_id)
        
        await state.set_state(OrderStates.waiting_address)
    elif message.text == "🗺️ Отправить точку на карте":
        # Инструкция по отправке геолокации вручную
        from aiogram.types import ReplyKeyboardRemove
        
        await message.answer(
            "📍 <b>Отправьте свою геопозицию:</b>\n\n"
            "1️⃣ Нажмите на скрепку 📎\n"
            "2️⃣ Выберите «Геопозиция» 🌍\n"
            "3️⃣ Отправьте вашу текущую позицию или выберите точку на карте\n\n"
            "<i>Или используйте кнопки ниже:</i>",
            reply_markup=get_location_request_keyboard(user_id=user_id),
            parse_mode='HTML'
        )
    else:
        # Если это не кнопка, а произвольный текст, возможно это адрес
        await message.answer(
            "📍 Пожалуйста, используйте кнопки ниже или отправьте геолокацию:",
            reply_markup=get_location_request_keyboard(user_id=user_id)
        )

# Обработчик для старой inline кнопки (оставим для совместимости)
@router.callback_query(F.data == "manual_address")
async def manual_address(callback: CallbackQuery, state: FSMContext):
    """Ввод адреса вручную (inline кнопка)"""
    user_id = callback.from_user.id
    
    await callback.message.edit_text(
        _("checkout.enter_address", user_id=user_id),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=_("common.back", user_id=user_id), callback_data="cart")]
        ]),
        parse_mode='HTML'
    )
    
    await state.set_state(OrderStates.waiting_address)

# Дублированный обработчик геолокации удален

# Старый обработчик delivery зон удален - теперь используется геолокация

@router.message(OrderStates.waiting_contact, F.content_type == 'contact')
async def process_contact(message: Message, state: FSMContext):
    """Обработка контакта"""
    contact = message.contact
    user_id = message.from_user.id
    
    # Сохраняем номер телефона
    await db.update_user_contact(user_id, contact.phone_number, "")
    
    data = await state.get_data()
    zone_id = data['delivery_zone']
    zone_info = DELIVERY_ZONES[zone_id]
    
    is_admin = user_id in ADMIN_IDS
    await message.answer(
        f"📍 <b>Укажите адрес доставки</b>\n\n"
        f"🚚 Зона: {zone_info['name']}\n"
        f"💰 Стоимость доставки: {zone_info['price']}₾\n"
        f"⏱ Время доставки: {zone_info['time']}\n\n"
        f"Напишите точный адрес доставки:",
        reply_markup=get_main_menu(is_admin=is_admin),
        parse_mode='HTML'
    )
    await state.set_state(OrderStates.waiting_address)

@router.message(OrderStates.waiting_address)
async def process_address(message: Message, state: FSMContext):
    """Обработка адреса"""
    address = message.text
    user_id = message.from_user.id
    
    # Отладочная информация
    logger.info(f"Получен адрес: {address} от пользователя {user_id}")
    
    # Получаем данные из состояния
    data = await state.get_data()
    logger.info(f"Данные состояния: {data}")
    
    # Удаляем предыдущие сообщения с геолокацией и запросом адреса
    location_msg_id = data.get('location_msg_id')
    address_msg_id = data.get('address_msg_id')
    location_map_msg_id = data.get('location_map_msg_id')
    location_request_msg_id = data.get('location_request_msg_id')
    
    if location_msg_id:
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=location_msg_id)
        except Exception:
            pass  # Сообщение могло быть уже удалено
    
    if address_msg_id:
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=address_msg_id)
        except Exception:
            pass  # Сообщение могло быть уже удалено
    
    if location_map_msg_id:
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=location_map_msg_id)
        except Exception:
            pass  # Сообщение с картой могло быть уже удалено
    
    if location_request_msg_id:
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=location_request_msg_id)
        except Exception:
            pass  # Сообщение с запросом могло быть уже удалено
    
    # Удаляем сообщение пользователя с адресом
    try:
        await message.delete()
    except Exception:
        pass
    
    # Проверяем есть ли общая сумма
    if 'total' not in data:
        await message.answer(_("common.error"))
        await state.clear()
        return
    
    # Координаты (если были отправлены)
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    # Стандартная стоимость доставки (можно настроить в зависимости от расстояния)
    delivery_price = 10  # 10₾ по умолчанию
    
    # Получаем корзину и пользователя
    cart_items = await db.get_cart(user_id)
    user = await db.get_user(user_id)
    logger.info(f"Корзина пользователя: {cart_items}")
    logger.info(f"Данные пользователя: {user}")
    
    if not cart_items:
        logger.warning(f"Корзина пуста для пользователя {user_id}")
        await message.answer(_("cart.empty"))
        await state.clear()
        return
    
    if not user:
        logger.warning(f"Пользователь {user_id} не найден в базе данных, создаем...")
        # Создаем пользователя автоматически
        await db.add_user(
            user_id, 
            message.from_user.username, 
            message.from_user.first_name
        )
        user = await db.get_user(user_id)
        if not user:
            logger.error(f"Не удалось создать пользователя {user_id}")
            await message.answer("❌ Ошибка: не удалось создать пользователя. Попробуйте /start")
            await state.clear()
            return
        
    phone = user.phone
    
    # Вычисляем стоимость
    items_total = sum(float(item.quantity * item.price) for item in cart_items)
    total_price = items_total + delivery_price
    
    logger.info(f"Стоимость заказа: товары={items_total}, доставка={delivery_price}, итого={total_price}")
    
    # Подготавливаем данные заказа
    products_data = []
    for item in cart_items:
        products_data.append({
            'id': item.product_id,
            'name': item.name,
            'price': float(item.price),
            'quantity': item.quantity
        })
    
    logger.info(f"Данные товаров для заказа: {products_data}")
    
    # Создаем заказ
    try:
        order_id = await db.create_order(
            user_id=user_id,
            products=products_data,
            total_price=total_price,
            delivery_zone="custom",  # Заменяем на кастомную зону
            delivery_price=delivery_price,
            phone=phone,
            address=address,
            latitude=latitude,
            longitude=longitude
        )
        logger.info(f"Заказ создан с номером: {order_id}")
    except Exception as e:
        logger.error(f"Ошибка создания заказа: {e}", exc_info=True)
        await message.answer("❌ Ошибка при создании заказа. Попробуйте еще раз.")
        await state.clear()
        return
    
    # Очищаем корзину
    await db.clear_cart(user_id)
    
    # Формируем детали заказа
    order_text = f"""✅ <b>Заказ #{order_id} создан!</b>

📦 <b>Товары:</b>
"""
    
    for item in products_data:
        order_text += f"• {item['name']} × {item['quantity']} = {item['price'] * item['quantity']}₾\n"
    
    # Формируем информацию о доставке
    delivery_info = "По координатам"
    if latitude and longitude:
        delivery_info = f"По координатам ({latitude:.6f}, {longitude:.6f})"
    
    order_text += f"""
🚚 <b>Доставка:</b> {delivery_info} - {delivery_price}₾
📍 <b>Адрес:</b> {address}
📱 <b>Телефон:</b> {phone}

💰 <b>К оплате: {total_price}₾</b>

💳 <b>Реквизиты для оплаты:</b>
🏦 Банк: {PAYMENT_INFO['bank_name']}
💳 Карта: {PAYMENT_INFO['card']}
📱 СБП: {PAYMENT_INFO['sbp_phone']}

После оплаты нажмите кнопку "Оплатил(а)" и пришлите скриншот."""
    
    # Удаляем сообщение пользователя с адресом
    try:
        await message.delete()
    except Exception:
        pass
    
    # Удаляем предыдущее сообщение с запросом адреса
    try:
        await message_manager.delete_user_message(message.bot, user_id)
    except Exception:
        pass
    
    # Используем менеджер сообщений для замены предыдущего сообщения
    await message_manager.send_or_edit_message(
        message.bot, user_id,
        order_text,
        reply_markup=get_order_confirmation_keyboard(order_id, user_id=user_id),
        menu_state='order_created',
        force_new=True
    )
    
    # Уведомление админу будет отправлено только после загрузки скриншота оплаты
    
    await state.clear()

@router.callback_query(F.data.startswith("payment_done_"))
async def payment_done(callback: CallbackQuery, state: FSMContext):
    """Пользователь сообщает об оплате"""
    order_id = int(callback.data.split("_")[2])
    
    await state.update_data(order_id=order_id)
    
    await callback.message.edit_text(
        f"📸 <b>Заказ #{order_id}</b>\n\n"
        f"Пришлите скриншот оплаты для подтверждения заказа:",
        parse_mode='HTML'
    )
    
    # Сохраняем ID сообщения с запросом скриншота в менеджере
    user_id = callback.from_user.id
    message_manager.set_user_message(user_id, callback.message.message_id, 'waiting_screenshot')
    
    await state.set_state(OrderStates.waiting_payment_screenshot)

@router.message(OrderStates.waiting_payment_screenshot, F.content_type == 'photo')
async def process_payment_screenshot(message: Message, state: FSMContext):
    """Обработка скриншота оплаты"""
    data = await state.get_data()
    order_id = data['order_id']
    
    # Сохраняем file_id скриншота
    photo_file_id = message.photo[-1].file_id
    await db.update_order_screenshot_by_number(order_id, photo_file_id)
    await db.update_order_status_by_number(order_id, 'payment_check')
    
    # Удаляем сообщение пользователя со скриншотом
    try:
        await message.delete()
    except Exception:
        pass
    
    # Удаляем предыдущее сообщение с запросом скриншота
    user_id = message.from_user.id
    try:
        await message_manager.delete_user_message(message.bot, user_id)
    except Exception:
        pass
    
    # Используем менеджер сообщений для отправки подтверждения
    await message_manager.send_or_edit_message(
        message.bot, user_id,
        f"✅ <b>Скриншот получен!</b>\n\n"
        f"Заказ #{order_id} отправлен на проверку.\n"
        f"Мы свяжемся с вами в течение 15 минут.\n\n"
        f"Статус заказа можно посмотреть в разделе 'Мои заказы'",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]),
        menu_state='screenshot_confirmed',
        force_new=True
    )
    
    # Уведомляем админов с подробной информацией
    from config import ADMIN_IDS, DELIVERY_ZONES
    import json
    
    logger.info(f"Загружены ADMIN_IDS из config: {ADMIN_IDS}")
    logger.info(f"Тип ADMIN_IDS: {type(ADMIN_IDS)}")
    
    logger.info(f"Получаем данные заказа {order_id} для уведомления админов")
    order = await db.get_order_by_number(order_id)
    
    if not order:
        logger.error(f"Заказ {order_id} не найден в базе данных!")
        return
    
    logger.info(f"Заказ {order_id} найден, формируем уведомление для админов")
    logger.info(f"Структура заказа: {order}")
    
    # Парсим продукты  
    products = order.products_data
    
    # Получаем информацию о пользователе
    user = await db.get_user(message.from_user.id)
    
    # Получаем координаты из заказа (безопасно)
    latitude = getattr(order, 'latitude', None)
    longitude = getattr(order, 'longitude', None)
    
    # Формируем красивое уведомление с переводами
    admin_lang = 'ru'  # Язык администратора
    
    admin_text = f"""{_("admin_notifications.new_order", user_id=617646449).format(order_number=order.order_number)}

{_("admin_notifications.user", user_id=617646449)} {message.from_user.first_name or _("admin_notifications.unknown", user_id=617646449)} (@{message.from_user.username or _("admin_notifications.no_username", user_id=617646449)})
{_("admin_notifications.amount", user_id=617646449)} {order.total_price}₾
{_("admin_notifications.address", user_id=617646449)} {order.address}
"""

    # Добавляем координаты если есть
    if latitude and longitude:
        admin_text += f"{_('admin_notifications.coordinates', user_id=617646449)} {latitude:.6f}, {longitude:.6f}\n"
    
    admin_text += f"\n{_('admin_notifications.order_content', user_id=617646449)}\n"
    
    for product in products:
        admin_text += f"• {product['name']} × {product['quantity']} = {product['price'] * product['quantity']}₾\n"
    
    # Информация о доставке с учетом геолокации
    if order.delivery_zone == "custom":
        delivery_info = _("admin_notifications.by_coordinates", user_id=617646449)
        if latitude and longitude:
            delivery_info = f"{_('admin_notifications.by_coordinates', user_id=617646449)} ({latitude:.6f}, {longitude:.6f})"
    else:
        zone_info = DELIVERY_ZONES.get(order.delivery_zone, {'name': _("admin_notifications.unknown", user_id=617646449)})
        delivery_info = zone_info['name']
    
    admin_text += f"""
{_("admin_notifications.delivery", user_id=617646449)} {delivery_info} - {order.delivery_price}₾
{_("admin_notifications.phone", user_id=617646449)} {order.phone}
{_("admin_notifications.order_date", user_id=617646449)} {str(order.created_at)[:16]}

{_("admin_notifications.payment_screenshot", user_id=617646449)}
{_("admin_notifications.awaiting_verification", user_id=617646449)}"""
    
    # Импортируем клавиатуру быстрых действий
    from keyboards import get_payment_notification_keyboard
    
    logger.info(f"Отправляем уведомления админам. ADMIN_IDS: {ADMIN_IDS}")
    logger.info(f"Количество админов: {len(ADMIN_IDS)}")
    
    if not ADMIN_IDS:
        logger.error("ADMIN_IDS пуст! Проверьте переменную окружения ADMIN_IDS")
        return
    
    for admin_id in ADMIN_IDS:
        try:
            logger.info(f"Попытка отправить уведомление админу {admin_id}")
            await message.bot.send_photo(
                admin_id,
                photo=photo_file_id,
                caption=admin_text,
                reply_markup=get_payment_notification_keyboard(order.id),
                parse_mode='HTML'
            )
            logger.info(f"✅ Уведомление успешно отправлено админу {admin_id}")
        except Exception as e:
            logger.error(f"❌ Не удалось отправить уведомление админу {admin_id}: {e}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"Полная ошибка: {traceback.format_exc()}")
    
    await state.clear()

@router.callback_query(F.data == "my_orders")
async def show_my_orders(callback: CallbackQuery):
    """Показать заказы пользователя"""
    await page_manager.orders.show_from_callback(callback)

@router.callback_query(F.data.startswith("orders_page_"))
async def orders_pagination(callback: CallbackQuery):
    """Обработчик пагинации заказов"""
    page = int(callback.data.split("_")[2])
    await page_manager.orders.show_from_callback(callback, page=page)

@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order(callback: CallbackQuery):
    """Отменить заказ пользователем"""
    order_number = int(callback.data.split("_")[2])  # Это номер заказа, не ID
    user_id = callback.from_user.id
    
    # Проверяем, что заказ принадлежит пользователю
    order = await db.get_order_by_number(order_number)
    if not order or order.user_id != user_id:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Проверяем, что заказ можно отменить (только ожидающие оплату)
    if order.status not in [OrderStatus.WAITING_PAYMENT.value, OrderStatus.PAYMENT_CHECK.value]:
        await callback.answer("❌ Заказ нельзя отменить", show_alert=True)
        return
    
    # Возвращаем товары на склад
    import json
    products = json.loads(order.products)
    for product in products:
        await db.increase_product_quantity(product['id'], product['quantity'])
    
    # Отменяем заказ
    await db.update_order_status(order.id, 'cancelled')
    
    await callback.answer("✅ Заказ отменен", show_alert=True)
    
    # Обновляем сообщение
    await message_manager.handle_callback_navigation(
        callback,
        "❌ <b>Заказ отменен</b>\n\n"
        f"Заказ #{order.order_number} был отменен.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
        ]),
        menu_state='order_cancelled'
    )

@router.callback_query(F.data.startswith("order_"))
async def show_order_details(callback: CallbackQuery):
    """Показать детали заказа"""
    order_id = int(callback.data.split("_")[1])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Используем свойство модели для получения продуктов
    products = order.products_data
    
    status_text = {
        'waiting_payment': '⏳ Ожидает оплаты',
        'payment_check': '💰 Проверка оплаты',
        'paid': '✅ Оплачен, готовится к отправке',
        'shipping': '🚚 Отправлен',
        'delivered': '✅ Доставлен',
        'cancelled': '❌ Отменен'
    }
    
    order_text = f"""📋 <b>Заказ #{order.order_number}</b>

📦 <b>Товары:</b>
"""
    
    for product in products:
        order_text += f"• {product['name']} × {product['quantity']} = {product['price'] * product['quantity']}₾\n"
    
    zone_info = DELIVERY_ZONES.get(order.delivery_zone, {'name': 'Неизвестно'})
    
    order_text += f"""
🚚 <b>Доставка:</b> {zone_info['name']} - {order.delivery_price}₾
📍 <b>Адрес:</b> {order.address}
📱 <b>Телефон:</b> {order.phone}
📅 <b>Дата:</b> {str(order.created_at)[:16]}

💰 <b>Итого: {order.total_price}₾</b>

📊 <b>Статус:</b> {status_text.get(order.status, order.status)}"""
    
    await callback.message.edit_text(
        order_text,
        reply_markup=get_order_details_keyboard(order_id, order.status),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    user_id = callback.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    await message_manager.handle_callback_navigation(
        callback,
        _("welcome.title", user_id=user_id) + "\n\n" + _("welcome.description", user_id=user_id),
        reply_markup=get_main_menu_inline(is_admin=is_admin, user_id=user_id),
        menu_state='main'
    )

# Обработчики смены языка
@router.callback_query(F.data.startswith("lang_"))
async def change_language(callback: CallbackQuery):
    """Сменить язык пользователя"""
    user_id = callback.from_user.id
    language = callback.data.split("_")[1]
    
    # Устанавливаем язык для пользователя
    i18n.i18n.set_language(language, user_id)
    
    # Сопоставление кодов языков с ключами переводов
    language_mapping = {
        'ru': 'russian',
        'en': 'english',
        'ka': 'georgian'
    }
    
    # Получаем название языка из переводов
    language_key = language_mapping.get(language, language)
    language_name = _(f"language.{language_key}", user_id=user_id)
    
    # Подтверждаем смену языка
    await callback.answer(_("language.changed", user_id=user_id, language=language_name))
    
    # Обновляем главное меню с новым языком через message_manager
    is_admin = user_id in ADMIN_IDS
    
    # Используем message_manager для правильной замены сообщения
    await message_manager.handle_callback_navigation(
        callback,
        _("welcome.title", user_id=user_id) + "\n\n" + _("welcome.description", user_id=user_id),
        reply_markup=get_main_menu_inline(is_admin=is_admin, user_id=user_id),
        menu_state='main'
    )

# Обработчики для inline кнопок главного меню
@router.callback_query(F.data == "catalog")
async def callback_catalog(callback: CallbackQuery):
    """Показать каталог через callback"""
    await page_manager.catalog.show_from_callback(callback)

@router.callback_query(F.data == "cart")
async def callback_cart(callback: CallbackQuery):
    """Показать корзину через callback"""
    await page_manager.cart.show_from_callback(callback)

@router.callback_query(F.data == "my_orders")
async def callback_orders(callback: CallbackQuery):
    """Показать заказы через callback"""
    await page_manager.orders.show_from_callback(callback)

@router.callback_query(F.data == "contact")
async def callback_contact(callback: CallbackQuery):
    """Показать контакт через callback"""
    await page_manager.profile.show_from_callback(callback, type='contact')

@router.callback_query(F.data == "info")
async def callback_info(callback: CallbackQuery):
    """Показать информацию через callback"""
    await page_manager.info.show_from_callback(callback)

@router.callback_query(F.data == "language")
async def callback_language(callback: CallbackQuery):
    """Показать выбор языка через callback"""
    await page_manager.profile.show_from_callback(callback, type='language')

# Все callback функции теперь используют page_manager - дублированный код удален

@router.callback_query(F.data == "message_admin")
async def start_message_to_admin(callback: CallbackQuery, state: FSMContext):
    """Начать отправку сообщения администратору"""
    user_id = callback.from_user.id
    
    await callback.answer()
    await callback.message.edit_text(
        _("contact.message_form", user_id=user_id),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=_("common.cancel", user_id=user_id), callback_data="contact")]
        ]),
        parse_mode='HTML'
    )
    
    await state.set_state(OrderStates.waiting_admin_message)

@router.message(OrderStates.waiting_admin_message, F.text)
async def process_admin_message(message: Message, state: FSMContext):
    """Обработать сообщение для администратора"""
    user_id = message.from_user.id
    
    try:
        # Отправляем сообщение всем админам
        from config import ADMIN_IDS, SUPER_ADMIN_ID
        admin_message = (
            f"📨 <b>Новое сообщение от пользователя</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>От:</b> {message.from_user.first_name}"
        )
        
        if message.from_user.username:
            admin_message += f" (@{message.from_user.username})"
        
        admin_message += f"\n🆔 <b>ID:</b> {user_id}\n\n"
        admin_message += f"💬 <b>Сообщение:</b>\n{message.text}\n\n"
        admin_message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        admin_message += f"<i>Для ответа используйте функцию «Написать клиенту» в панели администратора</i>"
        
        # Отправляем супер-админу
        if SUPER_ADMIN_ID:
            await message.bot.send_message(
                SUPER_ADMIN_ID,
                admin_message,
                parse_mode='HTML'
            )
        
        # Отправляем всем админам
        for admin_id in ADMIN_IDS:
            if admin_id != SUPER_ADMIN_ID:  # Избегаем дублирования
                try:
                    await message.bot.send_message(
                        admin_id,
                        admin_message,
                        parse_mode='HTML'
                    )
                except Exception:
                    pass  # Игнорируем ошибки отправки отдельным админам
        
        # Подтверждение пользователю
        await message.answer(
            _("contact.message_sent", user_id=user_id),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("common.main_menu", user_id=user_id), callback_data="main_menu")]
            ]),
            parse_mode='HTML'
        )
        
    except Exception as e:
        # Ошибка отправки
        await message.answer(
            _("contact.message_error", user_id=user_id),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("common.main_menu", user_id=user_id), callback_data="main_menu")]
            ]),
            parse_mode='HTML'
        )
    
    await state.clear()

@router.callback_query(F.data.startswith("resend_screenshot_"))
async def resend_screenshot(callback: CallbackQuery, state: FSMContext):
    """Повторная отправка скриншота оплаты"""
    order_number = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Получаем заказ
    order = await db.get_order_by_number(order_number)
    if not order or order.user_id != user_id:
        await callback.answer(_("error.order_not_found", user_id=user_id), show_alert=True)
        return
    
    # Сохраняем номер заказа в состоянии
    await state.update_data(order_id=order_number)
    await state.set_state(OrderStates.waiting_payment_screenshot)
    
    # Отправляем инструкции для повторной отправки скриншота
    await callback.message.edit_text(
        f"📸 <b>Повторная отправка скриншота</b>\n\n"
        f"📋 Заказ #{order_number}\n"
        f"💰 К оплате: {order.total_price}₾\n\n"
        f"Пожалуйста, отправьте корректный скриншот оплаты.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=_("common.cancel", user_id=user_id), callback_data="my_orders")]
        ]),
        parse_mode='HTML'
    )
    
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    user_id = callback.from_user.id
    await callback.answer()
    
    # Проверяем, является ли пользователь админом
    from config import ADMIN_IDS, SUPER_ADMIN_ID
    is_admin = user_id in ADMIN_IDS or user_id == SUPER_ADMIN_ID
    
    try:
        await callback.message.edit_text(
            _("welcome.title", user_id=user_id) + "\n\n" + 
            _("welcome.description", user_id=user_id),
            reply_markup=get_main_menu_inline(is_admin=is_admin, user_id=user_id),
            parse_mode='HTML'
        )
    except Exception:
        # Если не удается отредактировать, отправляем новое сообщение
        await callback.message.delete()
        await callback.message.answer(
            _("welcome.title", user_id=user_id) + "\n\n" + 
            _("welcome.description", user_id=user_id),
            reply_markup=get_main_menu_inline(is_admin=is_admin, user_id=user_id),
            parse_mode='HTML'
        )

# Общий отладочный обработчик для всех сообщений в состоянии waiting_location (ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ!)
@router.message(OrderStates.waiting_location)
async def debug_waiting_location(message: Message, state: FSMContext):
    """Отладочный обработчик для всех сообщений в waiting_location"""
    user_id = message.from_user.id
    current_state = await state.get_state()
    
    print(f"DEBUG: Пользователь {user_id} отправил необработанное сообщение в состоянии {current_state}")
    print(f"DEBUG: Тип сообщения: {message.content_type}")
    if message.text:
        print(f"DEBUG: Текст сообщения: '{message.text}'")
    if message.location:
        print(f"DEBUG: Координаты: lat={message.location.latitude}, lon={message.location.longitude}")
    
    # Отвечаем пользователю, что мы получили сообщение, но не знаем что с ним делать
    await message.answer("🤔 Получил ваше сообщение, но что-то пошло не так. Попробуйте снова.")
