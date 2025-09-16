from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Contact
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
import logging

from database import db
from config import DELIVERY_ZONES, MIN_ORDER_AMOUNT, PAYMENT_INFO, ADMIN_IDS

# Настройка логгера
logger = logging.getLogger(__name__)
from keyboards import (
    get_main_menu, get_catalog_keyboard, get_product_card_keyboard,
    get_cart_keyboard, get_delivery_zones_keyboard, get_order_confirmation_keyboard,
    get_orders_keyboard, get_order_details_keyboard, get_contact_keyboard
)

router = Router()

# Состояния для FSM
class OrderStates(StatesGroup):
    waiting_contact = State()
    waiting_address = State()
    waiting_payment_screenshot = State()

# Обработчик текстовых сообщений из главного меню
@router.message(F.text == "🛍 Каталог")
async def show_catalog(message: Message):
    """Показать каталог товаров"""
    products = await db.get_products()
    
    if not products:
        await message.answer("📦 Каталог пока пуст. Скоро добавим товары!")
        return
    
    await message.answer(
        "🛍 <b>Каталог товаров</b>\n\nВыберите товар:",
        reply_markup=get_catalog_keyboard(products),
        parse_mode='HTML'
    )

@router.message(F.text == "🛒 Корзина")
async def show_cart(message: Message):
    """Показать корзину"""
    user_id = message.from_user.id
    cart_items = await db.get_cart(user_id)
    
    if not cart_items:
        await message.answer(
            "🛒 <b>Ваша корзина пуста</b>\n\nДобавьте товары из каталога!",
            parse_mode='HTML'
        )
        return
    
    total = sum(item[1] * item[3] for item in cart_items)  # quantity * price
    
    cart_text = "🛒 <b>Ваша корзина:</b>\n\n"
    for item in cart_items:
        product_id, quantity, name, price, photo = item
        cart_text += f"• {name}\n"
        cart_text += f"  Количество: {quantity} шт.\n"
        cart_text += f"  Цена: {price}₾ × {quantity} = {price * quantity}₾\n\n"
    
    cart_text += f"💰 <b>Итого: {total}₾</b>"
    
    await message.answer(
        cart_text,
        reply_markup=get_cart_keyboard(cart_items),
        parse_mode='HTML'
    )

@router.message(F.text == "📋 Мои заказы")
async def show_orders(message: Message):
    """Показать заказы пользователя"""
    user_id = message.from_user.id
    orders = await db.get_user_orders(user_id)
    
    if not orders:
        await message.answer(
            "📋 <b>У вас пока нет заказов</b>\n\nСделайте первый заказ из каталога!",
            parse_mode='HTML'
        )
        return
    
    await message.answer(
        "📋 <b>Ваши заказы:</b>\n\nВыберите заказ для просмотра деталей:",
        reply_markup=get_orders_keyboard(orders),
        parse_mode='HTML'
    )

@router.message(F.text == "💬 Связь")
async def show_contact(message: Message):
    """Показать контактную информацию"""
    contact_text = """💬 <b>Связь с нами</b>

📱 <b>Telegram:</b> @your_support_username
📞 <b>Телефон:</b> +995 555 123 456
🕒 <b>Время работы:</b> 10:00 - 22:00

❓ <b>По вопросам:</b>
• Статус заказа
• Помощь с выбором
• Технические проблемы
• Предложения и жалобы

⚡ <b>Быстрый ответ в рабочее время!</b>"""

    await message.answer(contact_text, parse_mode='HTML')

@router.message(F.text == "ℹ️ Информация")
async def show_info(message: Message):
    """Показать информацию о магазине"""
    info_text = """ℹ️ <b>Информация о магазине</b>

🏪 <b>Tbilisi VAPE Shop</b>
🇬🇪 Лучший магазин одноразовых сигарет в Тбилиси

✅ <b>Наши преимущества:</b>
• 100% оригинальная продукция
• Быстрая доставка по Тбилиси
• Большой выбор вкусов
• Конкурентные цены
• Гарантия качества

🚚 <b>Доставка:</b>
• Центр - 5₾ (30-60 мин)
• Сабуртало - 8₾ (45-90 мин)
• Ваке - 7₾ (40-80 мин)
• Исани - 10₾ (60-120 мин)
• Другие районы - 15₾ (60-180 мин)

💳 <b>Оплата:</b>
• Банковская карта
• СБП (быстрые платежи)
• Наличные при получении

📦 <b>Минимальная сумма заказа:</b> {MIN_ORDER_AMOUNT}₾

🔒 <b>Безопасность:</b>
Все транзакции защищены. Мы не храним данные ваших карт."""

    await message.answer(info_text.format(MIN_ORDER_AMOUNT=MIN_ORDER_AMOUNT), parse_mode='HTML')

# Обработчики callback-запросов

@router.callback_query(F.data == "catalog")
async def callback_catalog(callback: CallbackQuery):
    """Показать каталог через callback"""
    products = await db.get_products()
    
    if not products:
        await callback.message.edit_text("📦 Каталог пока пуст. Скоро добавим товары!")
        return
    
    await callback.message.edit_text(
        "🛍 <b>Каталог товаров</b>\n\nВыберите товар:",
        reply_markup=get_catalog_keyboard(products),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    """Показать карточку товара"""
    product_id = int(callback.data.split("_")[1])
    product = await db.get_product(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    # Проверяем, есть ли товар в корзине
    user_id = callback.from_user.id
    cart_items = await db.get_cart(user_id)
    in_cart = any(item[0] == product_id for item in cart_items)
    
    product_text = f"""🛍 <b>{product[1]}</b>

💰 <b>Цена:</b> {product[2]}₾

📝 <b>Описание:</b>
{product[3] or 'Описание отсутствует'}

{'🛒 <i>Товар уже в корзине</i>' if in_cart else ''}"""
    
    keyboard = get_product_card_keyboard(product_id, in_cart)
    
    if product[4]:  # Если есть фото
        try:
            # Удаляем старое сообщение и отправляем новое с фото
            await callback.message.delete()
            await callback.bot.send_photo(
                chat_id=callback.from_user.id,
                photo=product[4],
                caption=product_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        except Exception as e:
            # Если не удалось отправить фото, отправляем текст
            await callback.message.edit_text(
                product_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    else:
        await callback.message.edit_text(
            product_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery):
    """Добавить товар в корзину"""
    product_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    
    # Проверяем существование товара
    product = await db.get_product(product_id)
    if not product or product[6] == 0:  # Если товара нет в наличии
        await callback.answer("❌ Товара нет в наличии", show_alert=True)
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
    
    # Добавляем в корзину
    await db.add_to_cart(user_id, product_id, 1)
    
    await callback.answer(f"✅ {product[1]} добавлен в корзину!")
    
    # Обновляем кнопки
    keyboard = get_product_card_keyboard(product_id, in_cart=True)
    await callback.message.edit_reply_markup(reply_markup=keyboard)

@router.callback_query(F.data.startswith("cart_increase_"))
async def cart_increase(callback: CallbackQuery):
    """Увеличить количество товара в корзине"""
    product_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Получаем текущее количество
    cart_items = await db.get_cart(user_id)
    current_quantity = 0
    for item in cart_items:
        if item[0] == product_id:
            current_quantity = item[1]
            break
    
    new_quantity = current_quantity + 1
    await db.update_cart_quantity(user_id, product_id, new_quantity)
    
    await callback.answer(f"✅ Количество увеличено до {new_quantity}")
    
    # Обновляем корзину если мы на странице корзины
    if "cart" in callback.message.text:
        await update_cart_display(callback)

@router.callback_query(F.data.startswith("cart_decrease_"))
async def cart_decrease(callback: CallbackQuery):
    """Уменьшить количество товара в корзине"""
    product_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Получаем текущее количество
    cart_items = await db.get_cart(user_id)
    current_quantity = 0
    for item in cart_items:
        if item[0] == product_id:
            current_quantity = item[1]
            break
    
    if current_quantity <= 1:
        await db.remove_from_cart(user_id, product_id)
        await callback.answer("🗑 Товар удален из корзины")
    else:
        new_quantity = current_quantity - 1
        await db.update_cart_quantity(user_id, product_id, new_quantity)
        await callback.answer(f"✅ Количество уменьшено до {new_quantity}")
    
    # Обновляем корзину если мы на странице корзины
    if "cart" in callback.message.text:
        await update_cart_display(callback)

@router.callback_query(F.data.startswith("cart_remove_"))
async def cart_remove(callback: CallbackQuery):
    """Удалить товар из корзины"""
    product_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    product = await db.get_product(product_id)
    db.remove_from_cart(user_id, product_id)
    
    await callback.answer(f"🗑 {product[1]} удален из корзины")
    
    # Обновляем корзину если мы на странице корзины
    if "cart" in callback.message.text:
        await update_cart_display(callback)
    else:
        # Обновляем кнопки на странице товара
        keyboard = get_product_card_keyboard(product_id, in_cart=False)
        await callback.message.edit_reply_markup(reply_markup=keyboard)

async def update_cart_display(callback: CallbackQuery):
    """Обновить отображение корзины"""
    user_id = callback.from_user.id
    cart_items = await db.get_cart(user_id)
    
    if not cart_items:
        await callback.message.edit_text(
            "🛒 <b>Ваша корзина пуста</b>\n\nДобавьте товары из каталога!",
            parse_mode='HTML'
        )
        return
    
    total = sum(item[1] * item[3] for item in cart_items)
    
    cart_text = "🛒 <b>Ваша корзина:</b>\n\n"
    for item in cart_items:
        product_id, quantity, name, price, photo = item
        cart_text += f"• {name}\n"
        cart_text += f"  Количество: {quantity} шт.\n"
        cart_text += f"  Цена: {price}₾ × {quantity} = {price * quantity}₾\n\n"
    
    cart_text += f"💰 <b>Итого: {total}₾</b>"
    
    await callback.message.edit_text(
        cart_text,
        reply_markup=get_cart_keyboard(cart_items),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
    """Очистить корзину"""
    user_id = callback.from_user.id
    await db.clear_cart(user_id)
    
    await callback.message.edit_text(
        "🗑 <b>Корзина очищена</b>\n\nДобавьте товары из каталога!",
        parse_mode='HTML'
    )

@router.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    """Начать оформление заказа"""
    user_id = callback.from_user.id
    cart_items = await db.get_cart(user_id)
    
    if not cart_items:
        await callback.answer("❌ Корзина пуста!", show_alert=True)
        return
    
    total = sum(item[1] * item[3] for item in cart_items)
    
    if total < MIN_ORDER_AMOUNT:
        await callback.answer(
            f"❌ Минимальная сумма заказа {MIN_ORDER_AMOUNT}₾",
            show_alert=True
        )
        return
    
    # Показываем зоны доставки
    await callback.message.edit_text(
        f"🚚 <b>Выберите зону доставки</b>\n\n💰 Сумма товаров: {total}₾",
        reply_markup=get_delivery_zones_keyboard(),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("delivery_"))
async def select_delivery(callback: CallbackQuery, state: FSMContext):
    """Выбрать зону доставки"""
    zone_id = callback.data.split("_")[1]
    zone_info = DELIVERY_ZONES[zone_id]
    
    # Сохраняем выбранную зону
    await state.update_data(delivery_zone=zone_id)
    
    # Проверяем контактные данные пользователя
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user[3]:  # Если нет номера телефона
        # Удаляем сообщение и отправляем новое с ReplyKeyboard
        await callback.message.delete()
        await callback.message.answer(
            "📱 <b>Укажите номер телефона</b>\n\nДля оформления заказа нам нужен ваш номер телефона:",
            reply_markup=get_contact_keyboard(),
            parse_mode='HTML'
        )
        await state.set_state(OrderStates.waiting_contact)
    else:
        # Если есть контакт, запрашиваем адрес
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        cancel_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data="cart")]]
        )
        
        await callback.message.edit_text(
            f"📍 <b>Укажите адрес доставки</b>\n\n"
            f"🚚 Зона: {zone_info['name']}\n"
            f"💰 Стоимость доставки: {zone_info['price']}₾\n"
            f"⏱ Время доставки: {zone_info['time']}\n\n"
            f"Напишите точный адрес доставки:",
            reply_markup=cancel_keyboard,
            parse_mode='HTML'
        )
        await state.set_state(OrderStates.waiting_address)

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
    
    if 'delivery_zone' not in data:
        await message.answer("❌ Ошибка: данные заказа потеряны. Начните заказ заново.")
        await state.clear()
        return
        
    zone_id = data['delivery_zone']
    zone_info = DELIVERY_ZONES[zone_id]
    
    # Получаем корзину и пользователя
    cart_items = await db.get_cart(user_id)
    user = await db.get_user(user_id)
    logger.info(f"Корзина пользователя: {cart_items}")
    logger.info(f"Данные пользователя: {user}")
    
    if not cart_items:
        logger.warning(f"Корзина пуста для пользователя {user_id}")
        await message.answer("❌ Корзина пуста!")
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
        
    phone = user[3]
    
    # Вычисляем стоимость
    items_total = sum(item[1] * item[3] for item in cart_items)
    delivery_price = zone_info['price']
    total_price = items_total + delivery_price
    
    logger.info(f"Стоимость заказа: товары={items_total}, доставка={delivery_price}, итого={total_price}")
    
    # Подготавливаем данные заказа
    products_data = []
    for item in cart_items:
        products_data.append({
            'id': item[0],
            'name': item[2],
            'price': item[3],
            'quantity': item[1]
        })
    
    logger.info(f"Данные товаров для заказа: {products_data}")
    
    # Создаем заказ
    try:
        order_id = await db.create_order(
            user_id=user_id,
            products=products_data,
            total_price=total_price,
            delivery_zone=zone_id,
            delivery_price=delivery_price,
            phone=phone,
            address=address
        )
        logger.info(f"Заказ создан с ID: {order_id}")
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
    
    order_text += f"""
🚚 <b>Доставка:</b> {zone_info['name']} - {delivery_price}₾
📍 <b>Адрес:</b> {address}
📱 <b>Телефон:</b> {phone}

💰 <b>К оплате: {total_price}₾</b>

💳 <b>Реквизиты для оплаты:</b>
🏦 Банк: {PAYMENT_INFO['bank_name']}
💳 Карта: {PAYMENT_INFO['card']}
📱 СБП: {PAYMENT_INFO['sbp_phone']}

❗ <b>Обязательно укажите в комментарии:</b>
<code>Заказ #{order_id}</code>

После оплаты нажмите кнопку "Оплатил(а)" и пришлите скриншот."""
    
    await message.answer(
        order_text,
        reply_markup=get_order_confirmation_keyboard(order_id),
        parse_mode='HTML'
    )
    
    # Уведомляем админов о новом заказе
    from config import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"🆕 <b>Новый заказ #{order_id}</b>\n\n"
                f"👤 Пользователь: {message.from_user.first_name} (@{message.from_user.username})\n"
                f"💰 Сумма: {total_price}₾\n"
                f"📍 Адрес: {address}",
                parse_mode='HTML'
            )
        except:
            pass
    
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
    
    await state.set_state(OrderStates.waiting_payment_screenshot)

@router.message(OrderStates.waiting_payment_screenshot, F.content_type == 'photo')
async def process_payment_screenshot(message: Message, state: FSMContext):
    """Обработка скриншота оплаты"""
    data = await state.get_data()
    order_id = data['order_id']
    
    # Сохраняем file_id скриншота
    photo_file_id = message.photo[-1].file_id
    await db.update_order_screenshot(order_id, photo_file_id)
    await db.update_order_status(order_id, 'payment_check')
    
    await message.answer(
        f"✅ <b>Скриншот получен!</b>\n\n"
        f"Заказ #{order_id} отправлен на проверку.\n"
        f"Мы свяжемся с вами в течение 15 минут.\n\n"
        f"Статус заказа можно посмотреть в разделе 'Мои заказы'",
        parse_mode='HTML'
    )
    
    # Уведомляем админов
    from config import ADMIN_IDS
    order = await db.get_order(order_id)
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_photo(
                admin_id,
                photo=photo_file_id,
                caption=f"💰 <b>Скриншот оплаты заказа #{order_id}</b>\n\n"
                        f"👤 Пользователь: {message.from_user.first_name} (@{message.from_user.username})\n"
                        f"💰 Сумма: {order[3]}₾",
                parse_mode='HTML'
            )
        except:
            pass
    
    await state.clear()

@router.callback_query(F.data == "my_orders")
async def show_my_orders(callback: CallbackQuery):
    """Показать заказы пользователя"""
    user_id = callback.from_user.id
    orders = await db.get_user_orders(user_id)
    
    if not orders:
        await callback.message.edit_text(
            "📋 <b>У вас пока нет заказов</b>\n\nСделайте первый заказ из каталога!",
            parse_mode='HTML'
        )
        return
    
    await callback.message.edit_text(
        "📋 <b>Ваши заказы:</b>\n\nВыберите заказ для просмотра деталей:",
        reply_markup=get_orders_keyboard(orders),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("order_"))
async def show_order_details(callback: CallbackQuery):
    """Показать детали заказа"""
    order_id = int(callback.data.split("_")[1])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Парсим продукты
    products = json.loads(order[2])
    
    status_text = {
        'waiting_payment': '⏳ Ожидает оплаты',
        'payment_check': '💰 Проверка оплаты',
        'paid': '✅ Оплачен, готовится к отправке',
        'shipping': '🚚 Отправлен',
        'delivered': '✅ Доставлен',
        'cancelled': '❌ Отменен'
    }
    
    order_text = f"""📋 <b>Заказ #{order[0]}</b>

📦 <b>Товары:</b>
"""
    
    for product in products:
        order_text += f"• {product['name']} × {product['quantity']} = {product['price'] * product['quantity']}₾\n"
    
    zone_info = DELIVERY_ZONES.get(order[4], {'name': 'Неизвестно'})
    
    order_text += f"""
🚚 <b>Доставка:</b> {zone_info['name']} - {order[5]}₾
📍 <b>Адрес:</b> {order[7]}
📱 <b>Телефон:</b> {order[6]}
📅 <b>Дата:</b> {order[10][:16]}

💰 <b>Итого: {order[3]}₾</b>

📊 <b>Статус:</b> {status_text.get(order[8], order[8])}"""
    
    await callback.message.edit_text(
        order_text,
        reply_markup=get_order_details_keyboard(order_id, order[8]),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    user_id = callback.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    await callback.message.delete()
    await callback.message.answer(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        reply_markup=get_main_menu(is_admin=is_admin),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "cart")
async def callback_cart(callback: CallbackQuery):
    """Показать корзину через callback"""
    await update_cart_display(callback)