from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Contact, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
import json

from database import db
from config import DELIVERY_ZONES, MIN_ORDER_AMOUNT, PAYMENT_INFO, ADMIN_IDS
from models import OrderStatus
from message_manager import message_manager
from keyboards import (
    get_order_confirmation_keyboard,
    get_order_details_keyboard, get_payment_notification_keyboard,
    get_admin_quick_actions_keyboard
)
from i18n import _
from button_filters import is_orders_button
from pages.manager import page_manager
from utils.loader import with_loader

logger = logging.getLogger(__name__)

router = Router()

class OrderStates(StatesGroup):
    waiting_contact = State()
    waiting_location = State()
    waiting_address = State()
    waiting_payment_screenshot = State()

# Обработчик текстовых сообщений из главного меню
@router.message(is_orders_button)
async def show_orders(message: Message):
    """Показать заказы пользователя"""
    await page_manager.orders.show_from_message(message)

@router.callback_query(F.data == "my_orders")
async def show_my_orders(callback: CallbackQuery):
    """Показать заказы пользователя"""
    await page_manager.orders.show_from_callback(callback)

@router.callback_query(F.data.startswith("orders_page_"))
async def orders_pagination(callback: CallbackQuery):
    """Обработчик пагинации заказов"""
    page = int(callback.data.split("_")[2])
    await page_manager.orders.show_from_callback(callback, page=page)

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
    
    # Удаляем inline сообщение и отправляем новое
    await callback.message.delete()
    
    print(f"DEBUG: Пользователь {user_id} начал checkout, отправляем единое сообщение")
    
    # Формируем текст с полной информацией
    combined_text = _("checkout.location_request", user_id=user_id).format(total=total)
    combined_text += "\n\n🔽 <b>Выберите способ доставки:</b>"
    
    # Создаем inline клавиатуру со всеми опциями
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Отправить геолокацию", callback_data="send_location_guide")],
        [InlineKeyboardButton(text="✍️ Ввести адрес вручную", callback_data="manual_address")],
        [InlineKeyboardButton(text="🔙 Назад к корзине", callback_data="cart")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ])
    
    # Отправляем единое сообщение с inline клавиатурой
    location_request_msg = await callback.message.answer(
        combined_text,
        reply_markup=inline_keyboard,
        parse_mode='HTML'
    )
    
    await state.set_state(OrderStates.waiting_location)
    await state.update_data(total=total, location_request_msg_id=location_request_msg.message_id)
    
    print(f"DEBUG: Состояние установлено на waiting_location для пользователя {user_id}")

# Обработчик кнопки для отправки геолокации
@router.callback_query(F.data == "send_location_guide")
async def send_location_guide(callback: CallbackQuery, state: FSMContext):
    """Показать инструкцию для отправки геолокации"""
    user_id = callback.from_user.id
    
    guide_text = """📍 <b>Как отправить геолокацию:</b>

1️⃣ Нажмите на скрепку 📎 в поле ввода
2️⃣ Выберите «Геопозиция» или «Location» 🌍
3️⃣ Отправьте текущую позицию или выберите точку на карте

<i>После отправки геолокации вы сможете указать точный адрес доставки.</i>"""
    
    # Обновляем сообщение с инструкцией
    await callback.message.edit_text(
        guide_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Ввести адрес вручную", callback_data="manual_address")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="checkout")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ]),
        parse_mode='HTML'
    )
    
    # Состояние уже установлено в waiting_location
    await callback.answer()

# Обработчик геолокации (ДОЛЖЕН БЫТЬ ВЫШЕ ТЕКСТОВОГО!)
@router.message(OrderStates.waiting_location, F.location)
async def process_location(message: Message, state: FSMContext):
    """Обработка полученной геолокации"""
    user_id = message.from_user.id
    location = message.location
    
    current_state = await state.get_state()
    print(f"DEBUG: Получена геолокация от пользователя {user_id}: lat={location.latitude}, lon={location.longitude}")
    print(f"DEBUG: Текущее состояние пользователя {user_id}: {current_state}")
    
    # Получаем данные из состояния для удаления предыдущих сообщений
    data = await state.get_data()
    location_instruction_msg_id = data.get('location_instruction_msg_id')
    
    # Удаляем сообщение с инструкцией геопозиции если есть
    if location_instruction_msg_id:
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=location_instruction_msg_id)
        except Exception:
            pass  # Сообщение с инструкцией могло быть уже удалено
    
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

# Обработчик для inline кнопки manual_address
@router.callback_query(F.data == "manual_address")
async def manual_address(callback: CallbackQuery, state: FSMContext):
    """Ввод адреса вручную (inline кнопка)"""
    user_id = callback.from_user.id
    
    # Формируем текст для ввода адреса
    address_text = """📝 <b>Ввод адреса доставки</b>

Введите полный адрес доставки в следующем сообщении.

<b>Пример:</b>
ул. Руставели 25, кв. 10

<i>Укажите улицу, дом, квартиру и любые дополнительные детали для курьера.</i>"""
    
    await callback.message.edit_text(
        address_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="checkout")],
            [InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
        ]),
        parse_mode='HTML'
    )
    
    # Сохраняем ID сообщения для последующего удаления
    await state.update_data(address_msg_id=callback.message.message_id)
    await state.set_state(OrderStates.waiting_address)
    await callback.answer()

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
    
    # Убираем Reply клавиатуру и создаем сообщение для лоадера
    loading_msg = await message.answer(
        "⏳ Обрабатываем заказ...",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )
    
    # Получаем данные из состояния
    data = await state.get_data()
    logger.info(f"Данные состояния: {data}")
    
    # Удаляем предыдущие сообщения с геолокацией и запросом адреса
    location_msg_id = data.get('location_msg_id')
    address_msg_id = data.get('address_msg_id')
    enter_address_msg_id = data.get('enter_address_msg_id')
    location_map_msg_id = data.get('location_map_msg_id')
    location_request_msg_id = data.get('location_request_msg_id')
    location_instruction_msg_id = data.get('location_instruction_msg_id')
    navigation_msg_id = data.get('navigation_msg_id')
    
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
    
    if enter_address_msg_id:
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=enter_address_msg_id)
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
    
    if location_instruction_msg_id:
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=location_instruction_msg_id)
        except Exception:
            pass  # Сообщение с инструкцией геопозиции могло быть уже удалено
    
    if navigation_msg_id:
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=navigation_msg_id)
        except Exception:
            pass  # Навигационное сообщение могло быть уже удалено
    
    
    # Удаляем сообщение пользователя с адресом
    try:
        await message.delete()
    except Exception:
        pass
    
    # НЕ удаляем сообщение загрузки здесь - оно будет удалено позже
    
    # Проверяем есть ли общая сумма
    if 'total' not in data:
        # Удаляем сообщение загрузки
        try:
            await loading_msg.delete()
        except Exception:
            pass
        
        await message.answer(
            "❌ Произошла ошибка. Пожалуйста, начните заново.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ])
        )
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
        # Удаляем сообщение загрузки
        try:
            await loading_msg.delete()
        except Exception:
            pass
        
        await message.answer(
            "🛒 Корзина пуста. Добавьте товары для оформления заказа.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Каталог", callback_data="catalog")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ])
        )
        await state.clear()
        return
    
    if not user:
        logger.warning(f"Пользователь {user_id} не найден в базе данных, создаем...")
        
        # Определяем язык пользователя из Telegram
        user_lang = 'ru'  # По умолчанию русский
        if message.from_user.language_code:
            if message.from_user.language_code.startswith('ka'):
                user_lang = 'ka'
            elif message.from_user.language_code.startswith('en'):
                user_lang = 'en'
        
        # Создаем пользователя автоматически
        await db.add_user(
            user_id, 
            message.from_user.username, 
            message.from_user.first_name,
            user_lang
        )
        user = await db.get_user(user_id)
        if not user:
            logger.error(f"Не удалось создать пользователя {user_id}")
            # Удаляем сообщение загрузки
            try:
                await loading_msg.delete()
            except Exception:
                pass
            
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
    
    # Создаем функцию для выполнения заказа с лоадером
    async def create_order_operation():
        # Создаем заказ
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
        
        # Очищаем корзину
        await db.clear_cart(user_id)
        
        return order_id
    
    # Выполняем создание заказа с лоадером
    try:
        order_id = await with_loader(
            create_order_operation,
            message.bot,
            loading_msg.chat.id,
            loading_msg.message_id,
            user_id=user_id,
            loader_text="Создаем заказ и резервируем товары...",
            success_text="🔄 Формируем детали заказа..."
        )
    except Exception as e:
        logger.error(f"Ошибка создания заказа: {e}", exc_info=True)
        
        await message.answer(
            "❌ Ошибка при создании заказа. Попробуйте еще раз.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ])
        )
        await state.clear()
        return
    
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
    
    
    # Заменяем сообщение лоадера на финальные детали заказа
    try:
        await loading_msg.edit_text(
            order_text,
            reply_markup=get_order_confirmation_keyboard(order_id, user_id=user_id),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.warning(f"Не удалось отредактировать сообщение заказа: {e}")
        # Удаляем старое сообщение лоадера
        try:
            await loading_msg.delete()
        except Exception:
            pass
        # Отправляем новое сообщение
        await message_manager.send_or_edit_message(
            message.bot, user_id,
            order_text,
            reply_markup=get_order_confirmation_keyboard(order_id, user_id=user_id),
            menu_state='order_created',
            force_new=True
        )
    else:
        # Обновляем менеджер сообщений
        message_manager.set_user_message(user_id, loading_msg.message_id, 'order_created')
    
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
    user_id = message.from_user.id
    
    # Проверяем, не был ли уже отправлен скриншот для этого заказа
    order = await db.get_order_by_number(order_id)
    if order and order.payment_screenshot:
        # Скриншот уже был отправлен, удаляем новый и показываем предупреждение
        try:
            await message.delete()
        except:
            pass
        
        warning_msg = await message.answer(
            f"⚠️ <b>Скриншот уже отправлен!</b>\n\n"
            f"📸 Заказ #{order_id}\n\n"
            f"Вы уже отправили скриншот оплаты для этого заказа.\n"
            f"Ожидайте подтверждения от администратора.",
            parse_mode='HTML'
        )
        
        # Удаляем предупреждение через 5 секунд
        import asyncio
        from handlers.user_modules.cart import delete_message_after_delay
        asyncio.create_task(delete_message_after_delay(message.bot, message.chat.id, warning_msg.message_id, 5))
        return
    
    # Сохраняем file_id скриншота
    photo_file_id = message.photo[-1].file_id
    await db.update_order_screenshot_by_number(order_id, photo_file_id)
    await db.update_order_status_by_number(order_id, 'payment_check')
    
    # Удаляем сообщение пользователя со скриншотом
    try:
        await message.delete()
    except Exception:
        pass
    
    # Очищаем все сообщения пользователя чтобы убрать засорение чата
    user_id = message.from_user.id
    try:
        await message_manager.delete_all_user_messages(message.bot, user_id)
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
                reply_markup=get_admin_quick_actions_keyboard(order.id, 'payment_check'),
                parse_mode='HTML'
            )
            logger.info(f"✅ Уведомление успешно отправлено админу {admin_id}")
        except Exception as e:
            logger.error(f"❌ Не удалось отправить уведомление админу {admin_id}: {e}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"Полная ошибка: {traceback.format_exc()}")
    
    await state.clear()

@router.message(OrderStates.waiting_payment_screenshot)
async def reject_non_screenshot(message: Message, state: FSMContext):
    """Отклонение всех сообщений кроме скриншотов в состоянии ожидания оплаты"""
    user_id = message.from_user.id
    
    # Удаляем сообщение пользователя сразу
    try:
        await message.delete()
    except:
        pass
    
    # Получаем номер заказа из состояния
    data = await state.get_data()
    order_id = data.get('order_id', 'N/A')
    
    # Отправляем временное предупреждение
    warning_msg = await message.answer(
        f"⚠️ <b>Нужен скриншот оплаты!</b>\n\n"
        f"📸 Заказ #{order_id}\n\n"
        f"Пожалуйста, пришлите именно <b>изображение</b> (скриншот) с подтверждением оплаты.\n\n"
        f"💡 Нажмите на скрепку 📎 → Фото/видео → выберите скриншот",
        parse_mode='HTML'
    )
    
    # Удаляем предупреждение через 5 секунд
    import asyncio
    from handlers.user_modules.cart import delete_message_after_delay
    asyncio.create_task(delete_message_after_delay(message.bot, message.chat.id, warning_msg.message_id, 5))

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
    
    # Товары НЕ возвращаем, так как они не списывались при создании заказа
    # Списание происходит только при подтверждении платежа админом
    
    # Отменяем заказ
    await db.update_order_status(order.id, 'cancelled')
    
    # Popup убираем, так как сообщение обновляется ниже
    
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
    
    # Очищаем старый скриншот чтобы пользователь мог отправить новый
    await db.update_order_screenshot(order.id, None)
    
    # Очищаем все предыдущие сообщения пользователя
    try:
        await message_manager.delete_all_user_messages(callback.bot, user_id)
    except Exception:
        pass
    
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

# Обработчик текстовых сообщений в состоянии waiting_location - обрабатываем как возможный адрес
@router.message(OrderStates.waiting_location)
async def handle_text_in_waiting_location(message: Message, state: FSMContext):
    """Обработка текста в состоянии ожидания локации - возможно это адрес"""
    user_id = message.from_user.id
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    # Показываем временную подсказку
    hint_msg = await message.answer(
        "❓ Пожалуйста, используйте кнопки выше для выбора способа доставки.",
        parse_mode='HTML'
    )
    
    # Удаляем подсказку через 3 секунды
    import asyncio
    from handlers.user_modules.cart import delete_message_after_delay
    asyncio.create_task(delete_message_after_delay(message.bot, message.chat.id, hint_msg.message_id, 3))