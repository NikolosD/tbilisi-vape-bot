from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json

from database import db
from config import ADMIN_IDS, DELIVERY_ZONES
from keyboards import (
    get_admin_keyboard, get_admin_products_keyboard, 
    get_admin_orders_keyboard, get_admin_order_actions_keyboard
)

router = Router()

# Состояния для админки
class AdminStates(StatesGroup):
    waiting_product_name = State()
    waiting_product_price = State()
    waiting_product_description = State()
    waiting_product_photo = State()
    waiting_broadcast_message = State()

# Фильтр для админов
def admin_filter(message_or_callback):
    """Проверка прав администратора"""
    user_id = message_or_callback.from_user.id
    return user_id in ADMIN_IDS

# Админ панель
@router.callback_query(F.data == "admin_panel", admin_filter)
async def show_admin_panel(callback: CallbackQuery):
    """Показать админ панель"""
    pending_orders = db.get_pending_orders()
    
    await callback.message.edit_text(
        f"🔧 <b>Админ-панель</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"🆕 Новых заказов: {len(pending_orders)}\n"
        f"📦 Товаров в каталоге: {len(db.get_products())}\n\n"
        f"Выберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode='HTML'
    )

# Управление товарами
@router.callback_query(F.data == "admin_products", admin_filter)
async def admin_products_menu(callback: CallbackQuery):
    """Меню управления товарами"""
    products = db.get_products()
    
    await callback.message.edit_text(
        f"📦 <b>Управление товарами</b>\n\n"
        f"Всего товаров: {len(products)}",
        reply_markup=get_admin_products_keyboard(),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "admin_add_product", admin_filter)
async def start_add_product(callback: CallbackQuery, state: FSMContext):
    """Начать добавление товара"""
    await callback.message.edit_text(
        "➕ <b>Добавление товара</b>\n\n"
        "Напишите название товара:",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_product_name)

@router.message(AdminStates.waiting_product_name, admin_filter)
async def process_product_name(message: Message, state: FSMContext):
    """Обработка названия товара"""
    product_name = message.text
    await state.update_data(name=product_name)
    
    await message.answer(
        f"📝 <b>Название:</b> {product_name}\n\n"
        f"Теперь укажите цену товара (в лари):",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_product_price)

@router.message(AdminStates.waiting_product_price, admin_filter)
async def process_product_price(message: Message, state: FSMContext):
    """Обработка цены товара"""
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Неверный формат цены. Введите число больше 0:")
        return
    
    data = await state.get_data()
    await state.update_data(price=price)
    
    await message.answer(
        f"📝 <b>Название:</b> {data['name']}\n"
        f"💰 <b>Цена:</b> {price}₾\n\n"
        f"Напишите описание товара:",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_product_description)

@router.message(AdminStates.waiting_product_description, admin_filter)
async def process_product_description(message: Message, state: FSMContext):
    """Обработка описания товара"""
    description = message.text
    data = await state.get_data()
    await state.update_data(description=description)
    
    await message.answer(
        f"📝 <b>Название:</b> {data['name']}\n"
        f"💰 <b>Цена:</b> {data['price']}₾\n"
        f"📋 <b>Описание:</b> {description}\n\n"
        f"Теперь пришлите фото товара (или напишите 'пропустить' без фото):",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_product_photo)

@router.message(AdminStates.waiting_product_photo, F.content_type == 'photo', admin_filter)
async def process_product_photo(message: Message, state: FSMContext):
    """Обработка фото товара"""
    photo_file_id = message.photo[-1].file_id
    data = await state.get_data()
    
    # Добавляем товар в базу
    db.add_product(
        name=data['name'],
        price=data['price'],
        description=data['description'],
        photo=photo_file_id
    )
    
    await message.answer(
        f"✅ <b>Товар добавлен!</b>\n\n"
        f"📝 <b>Название:</b> {data['name']}\n"
        f"💰 <b>Цена:</b> {data['price']}₾\n"
        f"📋 <b>Описание:</b> {data['description']}\n"
        f"📸 <b>Фото:</b> Добавлено",
        parse_mode='HTML'
    )
    
    await state.clear()

@router.message(AdminStates.waiting_product_photo, F.text == "пропустить", admin_filter)
async def process_product_no_photo(message: Message, state: FSMContext):
    """Добавление товара без фото"""
    data = await state.get_data()
    
    # Добавляем товар в базу без фото
    db.add_product(
        name=data['name'],
        price=data['price'],
        description=data['description'],
        photo=None
    )
    
    await message.answer(
        f"✅ <b>Товар добавлен!</b>\n\n"
        f"📝 <b>Название:</b> {data['name']}\n"
        f"💰 <b>Цена:</b> {data['price']}₾\n"
        f"📋 <b>Описание:</b> {data['description']}\n"
        f"📸 <b>Фото:</b> Не добавлено",
        parse_mode='HTML'
    )
    
    await state.clear()

# Управление заказами
@router.callback_query(F.data == "admin_orders", admin_filter)
async def admin_orders_menu(callback: CallbackQuery):
    """Меню заказов для админа"""
    orders = db.get_pending_orders()
    
    if not orders:
        await callback.message.edit_text(
            "📋 <b>Новые заказы</b>\n\n"
            "Новых заказов нет.",
            reply_markup=get_admin_keyboard(),
            parse_mode='HTML'
        )
        return
    
    await callback.message.edit_text(
        f"📋 <b>Заказы требующие внимания</b>\n\n"
        f"Всего: {len(orders)} заказов\n\n"
        f"Выберите заказ:",
        reply_markup=get_admin_orders_keyboard(orders),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("admin_order_"), admin_filter)
async def show_admin_order(callback: CallbackQuery):
    """Показать детали заказа для админа"""
    order_id = int(callback.data.split("_")[2])
    order = db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Парсим продукты
    products = json.loads(order[2])
    user = db.get_user(order[1])
    
    status_text = {
        'waiting_payment': '⏳ Ожидает оплаты',
        'payment_check': '💰 Проверка оплаты',
        'paid': '✅ Оплачен, готовится к отправке',
        'shipping': '🚚 Отправлен',
        'delivered': '✅ Доставлен',
        'cancelled': '❌ Отменен'
    }
    
    order_text = f"""📋 <b>Заказ #{order[0]}</b>

👤 <b>Клиент:</b>
• Имя: {user[2] if user else 'Неизвестно'}
• Username: @{user[1] if user and user[1] else 'нет'}
• ID: {order[1]}

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
    
    # Если есть скриншот оплаты, показываем его
    if order[9]:  # payment_screenshot
        try:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=order[9],
                caption=order_text,
                reply_markup=get_admin_order_actions_keyboard(order_id, order[8]),
                parse_mode='HTML'
            )
        except:
            await callback.message.edit_text(
                order_text + "\n\n📸 Скриншот оплаты прикреплен",
                reply_markup=get_admin_order_actions_keyboard(order_id, order[8]),
                parse_mode='HTML'
            )
    else:
        await callback.message.edit_text(
            order_text,
            reply_markup=get_admin_order_actions_keyboard(order_id, order[8]),
            parse_mode='HTML'
        )

# Действия с заказами
@router.callback_query(F.data.startswith("admin_confirm_payment_"), admin_filter)
async def confirm_payment(callback: CallbackQuery):
    """Подтвердить оплату заказа"""
    order_id = int(callback.data.split("_")[3])
    order = db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Обновляем статус
    db.update_order_status(order_id, 'paid')
    
    # Уведомляем клиента
    try:
        await callback.message.bot.send_message(
            order[1],  # user_id
            f"✅ <b>Оплата подтверждена!</b>\n\n"
            f"Заказ #{order_id} принят в обработку.\n"
            f"Готовим ваш заказ к отправке! 📦",
            parse_mode='HTML'
        )
    except:
        pass
    
    await callback.answer("✅ Оплата подтверждена!")
    
    # Обновляем отображение
    await show_admin_order(callback)

@router.callback_query(F.data.startswith("admin_reject_payment_"), admin_filter)
async def reject_payment(callback: CallbackQuery):
    """Отклонить оплату заказа"""
    order_id = int(callback.data.split("_")[3])
    order = db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Возвращаем статус
    db.update_order_status(order_id, 'waiting_payment')
    
    # Уведомляем клиента
    try:
        await callback.message.bot.send_message(
            order[1],  # user_id
            f"❌ <b>Оплата не подтверждена</b>\n\n"
            f"Заказ #{order_id}: Скриншот оплаты не прошел проверку.\n"
            f"Пожалуйста, проверьте корректность перевода и пришлите новый скриншот.",
            parse_mode='HTML'
        )
    except:
        pass
    
    await callback.answer("❌ Оплата отклонена!")
    
    # Обновляем отображение
    await show_admin_order(callback)

@router.callback_query(F.data.startswith("admin_ship_"), admin_filter)
async def ship_order(callback: CallbackQuery):
    """Отметить заказ как отправленный"""
    order_id = int(callback.data.split("_")[2])
    order = db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Обновляем статус
    db.update_order_status(order_id, 'shipping')
    
    # Уведомляем клиента
    try:
        await callback.message.bot.send_message(
            order[1],  # user_id
            f"🚚 <b>Заказ в пути!</b>\n\n"
            f"Заказ #{order_id} отправлен по адресу:\n"
            f"{order[7]}\n\n"
            f"Ожидайте курьера! 📦",
            parse_mode='HTML'
        )
    except:
        pass
    
    await callback.answer("🚚 Заказ отправлен!")
    
    # Обновляем отображение
    await show_admin_order(callback)

@router.callback_query(F.data.startswith("admin_deliver_"), admin_filter)
async def deliver_order(callback: CallbackQuery):
    """Отметить заказ как доставленный"""
    order_id = int(callback.data.split("_")[2])
    order = db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Обновляем статус
    db.update_order_status(order_id, 'delivered')
    
    # Уведомляем клиента
    try:
        await callback.message.bot.send_message(
            order[1],  # user_id
            f"✅ <b>Заказ доставлен!</b>\n\n"
            f"Заказ #{order_id} успешно доставлен.\n"
            f"Спасибо за покупку! 🙏\n\n"
            f"Оцените качество обслуживания и поделитесь отзывом!",
            parse_mode='HTML'
        )
    except:
        pass
    
    await callback.answer("✅ Заказ доставлен!")
    
    # Возвращаемся к списку заказов
    await admin_orders_menu(callback)

@router.callback_query(F.data.startswith("admin_cancel_"), admin_filter)
async def cancel_order(callback: CallbackQuery):
    """Отменить заказ"""
    order_id = int(callback.data.split("_")[2])
    order = db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Обновляем статус
    db.update_order_status(order_id, 'cancelled')
    
    # Уведомляем клиента
    try:
        await callback.message.bot.send_message(
            order[1],  # user_id
            f"❌ <b>Заказ отменен</b>\n\n"
            f"Заказ #{order_id} был отменен администратором.\n"
            f"Если у вас есть вопросы, обратитесь в поддержку.",
            parse_mode='HTML'
        )
    except:
        pass
    
    await callback.answer("❌ Заказ отменен!")
    
    # Возвращаемся к списку заказов
    await admin_orders_menu(callback)

# Статистика
@router.callback_query(F.data == "admin_stats", admin_filter)
async def show_stats(callback: CallbackQuery):
    """Показать статистику"""
    # Получаем данные для статистики
    all_orders = db.fetchall("SELECT status FROM orders")
    users_count = db.fetchone("SELECT COUNT(*) FROM users")[0]
    products_count = db.fetchone("SELECT COUNT(*) FROM products WHERE in_stock = 1")[0]
    
    # Подсчитываем заказы по статусам
    status_counts = {
        'waiting_payment': 0,
        'payment_check': 0,
        'paid': 0,
        'shipping': 0,
        'delivered': 0,
        'cancelled': 0
    }
    
    for order in all_orders:
        status = order[0]
        if status in status_counts:
            status_counts[status] += 1
    
    # Вычисляем доходы
    delivered_orders = db.fetchall("SELECT total_price FROM orders WHERE status = 'delivered'")
    total_revenue = sum(order[0] for order in delivered_orders)
    
    stats_text = f"""📊 <b>Статистика магазина</b>

👥 <b>Пользователи:</b> {users_count}
📦 <b>Товары в наличии:</b> {products_count}

📋 <b>Заказы:</b>
⏳ Ожидают оплаты: {status_counts['waiting_payment']}
💰 На проверке: {status_counts['payment_check']}
✅ Оплачены: {status_counts['paid']}
🚚 Отправлены: {status_counts['shipping']}
✅ Доставлены: {status_counts['delivered']}
❌ Отменены: {status_counts['cancelled']}

💰 <b>Доходы:</b>
Всего заработано: {total_revenue:.2f}₾"""

    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_keyboard(),
        parse_mode='HTML'
    )

# Рассылка
@router.callback_query(F.data == "admin_broadcast", admin_filter)
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку"""
    await callback.message.edit_text(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Напишите сообщение для рассылки всем пользователям:",
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_broadcast_message)

@router.message(AdminStates.waiting_broadcast_message, admin_filter)
async def process_broadcast(message: Message, state: FSMContext):
    """Обработка рассылки"""
    broadcast_text = message.text
    
    # Получаем всех пользователей
    users = db.fetchall("SELECT user_id FROM users")
    
    sent = 0
    failed = 0
    
    status_msg = await message.answer("📢 Отправка сообщений...")
    
    for user in users:
        try:
            await message.bot.send_message(user[0], broadcast_text)
            sent += 1
        except:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}",
        parse_mode='HTML'
    )
    
    await state.clear()