from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
import time

from database import db
from config import ADMIN_IDS, DELIVERY_ZONES
from keyboards import (
    get_admin_keyboard, get_enhanced_admin_keyboard, get_admin_products_keyboard, 
    get_admin_orders_keyboard, get_admin_order_actions_keyboard,
    get_admin_categories_keyboard, get_category_selection_keyboard,
    get_change_status_keyboard
)
import i18n
from i18n import _
from anti_spam import anti_spam

router = Router()

# Состояния для админки
class AdminStates(StatesGroup):
    waiting_product_name = State()
    waiting_product_price = State()
    waiting_product_description = State()
    waiting_product_photo = State()
    waiting_broadcast_message = State()
    waiting_category_name = State()
    waiting_category_emoji = State()
    waiting_category_description = State()

# Фильтр для админов
def admin_filter(message_or_callback):
    """Проверка прав администратора"""
    user_id = message_or_callback.from_user.id
    return user_id in ADMIN_IDS

# Админ панель
@router.callback_query(F.data == "admin_panel", admin_filter)
async def show_admin_panel(callback: CallbackQuery):
    """Показать улучшенную админ панель"""
    # Получаем статистику по разным типам заказов
    new_orders = await db.get_new_orders()
    checking_orders = await db.get_checking_orders()
    paid_orders = await db.get_paid_orders()
    shipping_orders = await db.get_shipping_orders()
    products = await db.get_products()
    
    await callback.message.edit_text(
        f"🔧 <b>Улучшенная админ-панель</b>\n\n"
        f"📊 <b>Статистика заказов:</b>\n"
        f"🆕 Новых: {len(new_orders)}\n"
        f"💰 На проверке: {len(checking_orders)}\n" 
        f"✅ Подтвержденных: {len(paid_orders)}\n"
        f"🚚 В доставке: {len(shipping_orders)}\n"
        f"📦 Товаров: {len(products)}\n\n"
        f"Выберите действие:",
        reply_markup=get_enhanced_admin_keyboard(),
        parse_mode='HTML'
    )

# Управление товарами
@router.callback_query(F.data == "admin_products", admin_filter)
async def admin_products_menu(callback: CallbackQuery):
    """Меню управления товарами"""
    products = await db.get_products()
    
    await callback.message.edit_text(
        f"📦 <b>Управление товарами</b>\n\n"
        f"Всего товаров: {len(products)}",
        reply_markup=get_admin_products_keyboard(),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "admin_edit_products", admin_filter)
async def admin_edit_products(callback: CallbackQuery):
    """Показать список товаров для редактирования"""
    products = await db.get_products()
    
    if not products:
        await callback.message.edit_text(
            "📦 <b>Товары отсутствуют</b>\n\n"
            "Сначала добавьте товары через меню.",
            reply_markup=get_admin_products_keyboard(),
            parse_mode='HTML'
        )
        return
    
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                text=f"✏️ {product[1]} - {product[2]}₾",
                callback_data=f"edit_product_{product[0]}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Управление товарами", callback_data="admin_products")])
    
    await callback.message.edit_text(
        "📝 <b>Редактировать товары</b>\n\n"
        "Выберите товар для редактирования:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("edit_product_"), admin_filter)
async def edit_product_menu(callback: CallbackQuery):
    """Меню редактирования товара"""
    product_id = int(callback.data.split("_")[2])
    product = await db.get_product(product_id)
    
    if not product:
        await callback.answer(_("common.not_found", user_id=callback.from_user.id), show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"delete_product_{product_id}")],
        [InlineKeyboardButton(text="📦 Скрыть/Показать", callback_data=f"toggle_stock_{product_id}")],
        [InlineKeyboardButton(text="🔙 Список товаров", callback_data="admin_edit_products")]
    ]
    
    stock_status = "✅ В наличии" if product[6] else "❌ Скрыт"
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование товара</b>\n\n"
        f"📝 <b>Название:</b> {product[1]}\n"
        f"💰 <b>Цена:</b> {product[2]}₾\n"
        f"📋 <b>Описание:</b> {product[3] or 'Нет описания'}\n"
        f"📦 <b>Статус:</b> {stock_status}\n\n"
        f"Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("delete_product_"), admin_filter)
async def confirm_delete_product(callback: CallbackQuery):
    """Подтверждение удаления товара"""
    product_id = int(callback.data.split("_")[2])
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{product_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_product_{product_id}")]
    ]
    
    await callback.message.edit_text(
        "🗑 <b>Удаление товара</b>\n\n"
        "⚠️ Вы уверены, что хотите удалить этот товар?\n"
        "Это действие нельзя отменить!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("confirm_delete_"), admin_filter)
async def delete_product(callback: CallbackQuery):
    """Удаление товара"""
    product_id = int(callback.data.split("_")[2])
    
    await db.execute("DELETE FROM products WHERE id = $1", product_id)
    
    await callback.message.edit_text(
        "✅ <b>Товар удален!</b>\n\n"
        "Товар успешно удален из каталога.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Управление товарами", callback_data="admin_products")]
        ]),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("toggle_stock_"), admin_filter)
async def toggle_product_stock(callback: CallbackQuery):
    """Переключение наличия товара"""
    product_id = int(callback.data.split("_")[2])
    product = await db.get_product(product_id)
    
    if not product:
        await callback.answer(_("common.not_found", user_id=callback.from_user.id), show_alert=True)
        return
    
    new_stock = not product[6]  # Инвертируем статус
    await db.update_product_stock(product_id, new_stock)
    
    status_text = "показан в каталоге" if new_stock else "скрыт из каталога"
    
    await callback.answer(f"✅ Товар {status_text}!", show_alert=True)
    
    # Обновляем меню редактирования
    keyboard = [
        [InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"delete_product_{product_id}")],
        [InlineKeyboardButton(text="📦 Скрыть/Показать", callback_data=f"toggle_stock_{product_id}")],
        [InlineKeyboardButton(text="🔙 Список товаров", callback_data="admin_edit_products")]
    ]
    
    stock_status = "✅ В наличии" if new_stock else "❌ Скрыт"
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование товара</b>\n\n"
        f"📝 <b>Название:</b> {product[1]}\n"
        f"💰 <b>Цена:</b> {product[2]}₾\n"
        f"📋 <b>Описание:</b> {product[3] or 'Нет описания'}\n"
        f"📦 <b>Статус:</b> {stock_status}\n\n"
        f"Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "admin_add_product", admin_filter)
async def start_add_product(callback: CallbackQuery, state: FSMContext):
    """Начать добавление товара - выбор категории"""
    categories = await db.get_categories()
    
    if not categories:
        await callback.answer("❌ Сначала добавьте категории!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "➕ <b>Добавление товара</b>\n\n"
        "Выберите категорию для товара:",
        reply_markup=get_category_selection_keyboard(categories),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("select_category_"), admin_filter)
async def select_category_for_product(callback: CallbackQuery, state: FSMContext):
    """Выбор категории для товара"""
    category_id = int(callback.data.split("_")[2])
    category = await db.get_category(category_id)
    
    await state.update_data(category_id=category_id)
    
    keyboard = [
        [InlineKeyboardButton(text="🔙 Управление товарами", callback_data="admin_products")]
    ]
    
    await callback.message.edit_text(
        f"➕ <b>Добавление товара</b>\n\n"
        f"📂 <b>Категория:</b> {category[2]} {category[1]}\n\n"
        f"Напишите название товара:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
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
    await db.add_product(
        name=data['name'],
        price=data['price'],
        description=data['description'],
        photo=photo_file_id,
        category_id=data.get('category_id')
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
    await db.add_product(
        name=data['name'],
        price=data['price'],
        description=data['description'],
        photo=None,
        category_id=data.get('category_id')
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
@router.callback_query(F.data == "admin_all_orders", admin_filter)
async def admin_all_orders_menu(callback: CallbackQuery):
    """Меню всех заказов для админа"""
    orders = await db.get_all_orders(50)  # Показываем последние 50 заказов
    
    if not orders:
        text = "📋 <b>Все заказы</b>\n\nЗаказов пока нет."
        
        try:
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=_("common.to_admin"), callback_data="admin_panel")]
                ]),
                parse_mode='HTML'
            )
        except Exception:
            await callback.message.delete()
            await callback.message.answer(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=_("common.to_admin"), callback_data="admin_panel")]
                ]),
                parse_mode='HTML'
            )
        return
    
    text = f"📋 <b>Все заказы</b>\n\nВсего: {len(orders)} заказов\n\nВыберите заказ:"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_orders_keyboard(orders),
            parse_mode='HTML'
        )
    except Exception:
        await callback.message.delete()
        await callback.message.answer(
            text,
            reply_markup=get_admin_orders_keyboard(orders),
            parse_mode='HTML'
        )

@router.callback_query(F.data == "admin_orders", admin_filter)
async def admin_orders_menu(callback: CallbackQuery):
    """Меню заказов для админа"""
    orders = await db.get_pending_orders()
    
    if not orders:
        await callback.message.edit_text(
            "📋 <b>Новые заказы</b>\n\n"
            "Новых заказов нет.",
            reply_markup=get_admin_keyboard(),
            parse_mode='HTML'
        )
        return
    
    text = f"📋 <b>Заказы требующие внимания</b>\n\nВсего: {len(orders)} заказов\n\nВыберите заказ:"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_orders_keyboard(orders),
            parse_mode='HTML'
        )
    except Exception:
        # Если не удалось отредактировать (например, это было сообщение с фото), 
        # удаляем старое и отправляем новое
        await callback.message.delete()
        await callback.message.answer(
            text,
            reply_markup=get_admin_orders_keyboard(orders),
            parse_mode='HTML'
        )

@router.callback_query(F.data.startswith("admin_order_"), admin_filter)
async def show_admin_order(callback: CallbackQuery):
    """Показать детали заказа для админа"""
    # Определяем формат callback_data и извлекаем order_id
    parts = callback.data.split("_")
    if parts[0] == "admin" and parts[1] == "order":
        order_id = int(parts[2])  # admin_order_X
    elif len(parts) >= 3:
        order_id = int(parts[-1])  # admin_confirm_payment_X, admin_ship_X, etc.
    else:
        await callback.answer("❌ Ошибка: некорректный формат данных", show_alert=True)
        return
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Парсим продукты
    products = json.loads(order[2])
    user = await db.get_user(order[1])
    
    status_text = {
        'waiting_payment': '⏳ Ожидает оплаты',
        'payment_check': '💰 Проверка оплаты',
        'paid': '✅ Оплачен, готовится к отправке',
        'shipping': '🚚 Отправлен',
        'delivered': '✅ Доставлен',
        'cancelled': '❌ Отменен'
    }
    
    order_text = f"""📋 <b>Заказ #{order[1]}</b>

👤 <b>Клиент:</b>
• Имя: {user[2] if user else 'Неизвестно'}
• Username: @{user[1] if user and user[1] else 'нет'}
• ID: {order[2]}

📦 <b>Товары:</b>
"""
    
    for product in products:
        order_text += f"• {product['name']} × {product['quantity']} = {product['price'] * product['quantity']}₾\n"
    
    zone_info = DELIVERY_ZONES.get(order[5], {'name': 'Неизвестно'})
    
    order_text += f"""
🚚 <b>Доставка:</b> {zone_info['name']} - {order[6]}₾
📍 <b>Адрес:</b> {order[8]}
📱 <b>Телефон:</b> {order[7]}
📅 <b>Дата:</b> {str(order[11])[:16]}

💰 <b>Итого: {order[4]}₾</b>

📊 <b>Статус:</b> {status_text.get(order[9], order[9])}"""
    
    # Если есть скриншот оплаты, показываем его
    if order[10]:  # payment_screenshot
        try:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=order[10],
                caption=order_text,
                reply_markup=get_admin_order_actions_keyboard(order_id, order[9]),
                parse_mode='HTML'
            )
        except:
            await callback.message.edit_text(
                order_text + "\n\n📸 Скриншот оплаты прикреплен",
                reply_markup=get_admin_order_actions_keyboard(order_id, order[9]),
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
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Обновляем статус
    await db.update_order_status(order_id, 'paid')
    
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
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Возвращаем статус
    await db.update_order_status(order_id, 'waiting_payment')
    
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
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Обновляем статус
    await db.update_order_status(order_id, 'shipping')
    
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
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Обновляем статус
    await db.update_order_status(order_id, 'delivered')
    
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
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Обновляем статус
    await db.update_order_status(order_id, 'cancelled')
    
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
    all_orders = await db.fetchall("SELECT status FROM orders")
    users_count = (await db.fetchone("SELECT COUNT(*) FROM users"))[0]
    products_count = (await db.fetchone("SELECT COUNT(*) FROM products WHERE in_stock = true"))[0]
    
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
    delivered_orders = await db.fetchall("SELECT total_price FROM orders WHERE status = 'delivered'")
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
    keyboard = [
        [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
    ]
    
    await callback.message.edit_text(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Напишите сообщение для рассылки всем пользователям:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_broadcast_message)

@router.message(AdminStates.waiting_broadcast_message, admin_filter)
async def process_broadcast(message: Message, state: FSMContext):
    """Обработка рассылки"""
    broadcast_text = message.text
    
    # Получаем всех пользователей
    users = await db.fetchall("SELECT user_id FROM users")
    
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

# Обработчики для управления категориями
@router.callback_query(F.data == "admin_categories", admin_filter)
async def show_admin_categories(callback: CallbackQuery):
    """Показать управление категориями"""
    await callback.message.edit_text(
        "🏷️ <b>Управление категориями</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_categories_keyboard(),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "admin_add_category", admin_filter)
async def start_add_category(callback: CallbackQuery, state: FSMContext):
    """Начать добавление категории"""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Управление категориями", callback_data="admin_categories")]
    ]
    
    await callback.message.edit_text(
        "➕ <b>Добавление категории</b>\n\n"
        "Напишите название категории:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_category_name)

@router.message(AdminStates.waiting_category_name, admin_filter)
async def process_category_name(message: Message, state: FSMContext):
    """Обработка названия категории"""
    category_name = message.text
    await state.update_data(name=category_name)
    
    keyboard = [
        [InlineKeyboardButton(text="🔙 Управление категориями", callback_data="admin_categories")]
    ]
    
    await message.answer(
        f"➕ <b>Добавление категории</b>\n\n"
        f"📝 <b>Название:</b> {category_name}\n\n"
        f"Напишите эмодзи для категории (например: 🧚, 💨, 🔥):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_category_emoji)

@router.message(AdminStates.waiting_category_emoji, admin_filter)
async def process_category_emoji(message: Message, state: FSMContext):
    """Обработка эмодзи категории"""
    emoji = message.text
    await state.update_data(emoji=emoji)
    
    keyboard = [
        [InlineKeyboardButton(text="🔙 Управление категориями", callback_data="admin_categories")]
    ]
    
    await message.answer(
        f"➕ <b>Добавление категории</b>\n\n"
        f"📝 <b>Название:</b> {emoji} {message.text}\n\n"
        f"Напишите описание категории (или отправьте 'пропустить'):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )
    await state.set_state(AdminStates.waiting_category_description)

@router.message(AdminStates.waiting_category_description, admin_filter)
async def process_category_description(message: Message, state: FSMContext):
    """Обработка описания категории"""
    data = await state.get_data()
    description = message.text if message.text != "пропустить" else None
    
    # Добавляем категорию в базу
    await db.add_category(
        name=data['name'],
        emoji=data['emoji'],
        description=description
    )
    
    await message.answer(
        f"✅ <b>Категория добавлена!</b>\n\n"
        f"📝 <b>Название:</b> {data['emoji']} {data['name']}\n"
        f"📄 <b>Описание:</b> {description or 'Не указано'}",
        reply_markup=get_admin_categories_keyboard(),
        parse_mode='HTML'
    )
    
    await state.clear()

# Обработчики для управления статусами заказов
@router.callback_query(F.data.startswith("admin_change_status_"), admin_filter)
async def change_order_status_menu(callback: CallbackQuery):
    """Показать меню смены статуса заказа"""
    order_id = int(callback.data.split("_")[-1])
    
    await callback.message.edit_text(
        f"🔄 <b>Изменить статус заказа #{order_id}</b>\n\nВыберите новый статус:",
        reply_markup=get_change_status_keyboard(order_id),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("set_status_"), admin_filter)  
async def set_order_status(callback: CallbackQuery):
    """Установить новый статус заказа"""
    parts = callback.data.split("_")
    new_status = "_".join(parts[2:-1])  # Получаем статус между "set_status_" и номером заказа
    order_id = int(parts[-1])
    
    # Обновляем статус
    await db.update_order_status(order_id, new_status)
    
    status_names = {
        "waiting_payment": "ожидает оплаты",
        "payment_check": "на проверке оплаты", 
        "paid": "оплачен",
        "shipping": "отправлен",
        "delivered": "доставлен",
        "cancelled": "отменен"
    }
    
    await callback.answer(f"✅ Статус изменен на \"{status_names.get(new_status, new_status)}\"")
    
    # Возвращаемся к заказу
    await show_admin_order(callback)



# Команды для управления спамом (только для админов)
@router.message(F.text == "/antispam", admin_filter)
async def show_antispam_menu(message: Message):
    """Показать меню анти-спам системы"""
    blocked_count = len(anti_spam.get_blocked_users())
    total_users = len(anti_spam.user_stats)
    
    text = f"""🛡 <b>Анти-спам система</b>

📊 <b>Статистика:</b>
• Всего пользователей: {total_users}
• Заблокированных: {blocked_count}

⚙️ <b>Настройки:</b>
• Макс. сообщений/мин: {anti_spam.MAX_MESSAGES_PER_MINUTE}
• Макс. сообщений/час: {anti_spam.MAX_MESSAGES_PER_HOUR}
• Мин. интервал: {anti_spam.MIN_MESSAGE_INTERVAL}с
• Порог блокировки: {anti_spam.SPAM_THRESHOLD}

<b>Команды:</b>
/blocked - список заблокированных
/unblock [ID] - разблокировать пользователя
/stats [ID] - статистика пользователя
/block [ID] - заблокировать пользователя"""

    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "/blocked", admin_filter)
async def show_blocked_users(message: Message):
    """Показать заблокированных пользователей"""
    blocked = anti_spam.get_blocked_users()
    
    if not blocked:
        await message.answer("✅ Заблокированных пользователей нет.")
        return
    
    text = "🚫 <b>Заблокированные пользователи:</b>\n\n"
    
    for user in blocked[:10]:  # Показываем первые 10
        user_id = user["user_id"]
        spam_score = user["spam_score"]
        warnings = user["warning_count"]
        
        if user["permanent"]:
            status = "Навсегда"
        else:
            remaining = user["remaining_time"]
            status = f"{remaining}с" if remaining > 0 else "Истекает"
        
        text += f"• ID: {user_id}\n"
        text += f"  Спам-счет: {spam_score}, Предупреждения: {warnings}\n"
        text += f"  Блокировка: {status}\n\n"
    
    if len(blocked) > 10:
        text += f"... и еще {len(blocked) - 10} пользователей"
    
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.startswith("/unblock "), admin_filter)
async def unblock_user_command(message: Message):
    """Разблокировать пользователя"""
    try:
        user_id = int(message.text.split()[1])
        anti_spam.unblock_user(user_id)
        await message.answer(f"✅ Пользователь {user_id} разблокирован.")
    except (ValueError, IndexError):
        await message.answer("❌ Использование: /unblock [ID пользователя]")

@router.message(F.text.startswith("/block "), admin_filter)
async def block_user_command(message: Message):
    """Заблокировать пользователя"""
    try:
        user_id = int(message.text.split()[1])
        anti_spam.block_user(user_id, 0, "Заблокирован администратором")
        await message.answer(f"🚫 Пользователь {user_id} заблокирован.")
    except (ValueError, IndexError):
        await message.answer("❌ Использование: /block [ID пользователя]")

@router.message(F.text.startswith("/stats "), admin_filter)
async def show_user_stats(message: Message):
    """Показать статистику пользователя"""
    try:
        user_id = int(message.text.split()[1])
        stats = anti_spam.get_user_stats(user_id)
        
        text = f"""📊 <b>Статистика пользователя {user_id}:</b>

💬 Сообщений всего: {stats["message_count"]}
🕐 За последний час: {stats["messages_last_hour"]}
🎯 Спам-счет: {stats["spam_score"]}
⚠️ Предупреждений: {stats["warning_count"]}

🚫 Заблокирован: {"Да" if stats["is_blocked"] else "Нет"}"""
        
        if stats["remaining_block_time"] > 0:
            text += f"\n⏰ Осталось: {stats['remaining_block_time']}с"
        
        await message.answer(text, parse_mode="HTML")
        
    except (ValueError, IndexError):
        await message.answer("❌ Использование: /stats [ID пользователя]")

@router.message(F.text == "/security", admin_filter)
async def show_security_stats(message: Message):
    """Показать статистику безопасности"""
    try:
        from security_monitor import security_monitor
        stats = security_monitor.get_security_stats()
        
        text = f"""🛡️ <b>Статистика безопасности</b>

📊 <b>За последний час:</b>
• События: {stats["events_last_hour"]}
• Блокировки: {stats["blocks_last_hour"]}
• Сообщения: {stats["messages_last_hour"]}

📈 <b>Общая статистика:</b>
• Всего событий: {stats["total_events"]}
• Заблокированных пользователей: {stats["unique_blocked_users"]}

⚠️ <b>Серьезность событий:</b>
• Низкая: {stats["severity_breakdown"]["low"]}
• Средняя: {stats["severity_breakdown"]["medium"]}
• Высокая: {stats["severity_breakdown"]["high"]}
• Критическая: {stats["severity_breakdown"]["critical"]}

Команды:
/events - последние события
/ddos - проверка DDoS
/cleanup - очистка старых данных"""
        
        await message.answer(text, parse_mode="HTML")
    except ImportError:
        await message.answer("❌ Модуль мониторинга безопасности недоступен")

@router.message(F.text == "/events", admin_filter)
async def show_recent_events(message: Message):
    """Показать последние события безопасности"""
    try:
        from security_monitor import security_monitor
        events = security_monitor.get_recent_events(10)
        
        if not events:
            await message.answer("📋 Последние события отсутствуют")
            return
        
        text = "📋 <b>Последние события безопасности:</b>\n\n"
        
        for event in reversed(events[-10:]):  # Последние 10 событий
            severity_emoji = {
                "low": "🟢",
                "medium": "🟡", 
                "high": "🟠",
                "critical": "🔴"
            }
            
            time_str = time.strftime("%H:%M:%S", time.localtime(event.timestamp))
            text += f"{severity_emoji.get(event.severity, '⚪')} <code>{time_str}</code> "
            text += f"<b>{event.event_type}</b>\n"
            text += f"👤 User: {event.user_id}\n"
            text += f"📝 {event.details}\n\n"
        
        await message.answer(text, parse_mode="HTML")
    except ImportError:
        await message.answer("❌ Модуль мониторинга безопасности недоступен")

@router.message(F.text == "/ddos", admin_filter)
async def check_ddos(message: Message):
    """Проверить активность на предмет DDoS"""
    try:
        from security_monitor import security_monitor
        is_ddos = security_monitor.detect_ddos_attempt()
        
        if is_ddos:
            text = "🚨 <b>ВНИМАНИЕ!</b> Обнаружена подозрительная активность!\n\n"
            text += "Возможная DDoS атака или массовый спам.\n"
            text += "Рекомендуется усилить защиту."
        else:
            text = "✅ <b>Система в норме</b>\n\n"
            text += "Подозрительной активности не обнаружено."
        
        await message.answer(text, parse_mode="HTML")
    except ImportError:
        await message.answer("❌ Модуль мониторинга безопасности недоступен")

@router.message(F.text == "/cleanup", admin_filter) 
async def cleanup_security_data(message: Message):
    """Очистить старые данные безопасности"""
    try:
        from security_monitor import security_monitor
        security_monitor.cleanup_old_data()
        await message.answer("✅ Старые данные безопасности очищены")
    except ImportError:
        await message.answer("❌ Модуль мониторинга безопасности недоступен")

@router.message(F.text == "/topblocked", admin_filter)
async def show_top_blocked(message: Message):
    """Показать топ заблокированных пользователей"""
    try:
        from security_monitor import security_monitor
        top_users = security_monitor.get_top_blocked_users(10)
        
        if not top_users:
            await message.answer("📋 Нет заблокированных пользователей")
            return
        
        text = "📊 <b>Топ заблокированных пользователей:</b>\n\n"
        
        for i, user_data in enumerate(top_users, 1):
            text += f"{i}. 👤 ID: <code>{user_data['user_id']}</code>\n"
            text += f"   🚫 Блокировок: {user_data['block_count']}\n\n"
        
        await message.answer(text, parse_mode="HTML")
    except ImportError:
        await message.answer("❌ Модуль мониторинга безопасности недоступен")

# Быстрые действия из уведомлений
@router.callback_query(F.data.startswith("quick_confirm_"), admin_filter)
async def quick_confirm_payment(callback: CallbackQuery):
    """Быстрое подтверждение оплаты из уведомления"""
    order_id = int(callback.data.split("_")[2])
    
    # Подтверждаем оплату
    await db.update_order_status(order_id, 'paid')
    
    # Отправляем уведомление клиенту
    order = await db.get_order(order_id)
    if order:
        client_text = f"""✅ <b>Оплата подтверждена!</b>

📋 <b>Заказ #{order[1]}</b>
💰 <b>Сумма:</b> {order[3]}₾

Ваш заказ принят в работу и будет доставлен в ближайшее время.
Спасибо за покупку! 🎉"""
        
        try:
            await callback.bot.send_message(
                order[1],  # user_id
                client_text,
                parse_mode='HTML'
            )
        except:
            pass
    
    # Обновляем сообщение админа
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>ОПЛАТА ПОДТВЕРЖДЕНА</b>",
        parse_mode='HTML'
    )
    await callback.answer("✅ Оплата подтверждена")

@router.callback_query(F.data.startswith("quick_reject_"), admin_filter)
async def quick_reject_payment(callback: CallbackQuery):
    """Быстрое отклонение оплаты из уведомления"""
    order_id = int(callback.data.split("_")[2])
    
    # Возвращаем статус на ожидание оплаты
    await db.update_order_status(order_id, 'waiting_payment')
    
    # Отправляем уведомление клиенту
    order = await db.get_order(order_id)
    if order:
        client_text = f"""❌ <b>Оплата не подтверждена</b>

📋 <b>Заказ #{order[1]}</b>
💰 <b>Сумма:</b> {order[3]}₾

Пожалуйста, проверьте корректность перевода и пришлите новый скриншот.
Или свяжитесь с поддержкой для уточнения деталей."""
        
        try:
            await callback.bot.send_message(
                order[1],  # user_id
                client_text,
                parse_mode='HTML'
            )
        except:
            pass
    
    # Обновляем сообщение админа
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>ОПЛАТА ОТКЛОНЕНА</b>",
        parse_mode='HTML'
    )
    await callback.answer("❌ Оплата отклонена")

# Обработчики фильтрованных заказов
@router.callback_query(F.data.startswith("admin_orders_"), admin_filter)
async def show_filtered_orders(callback: CallbackQuery):
    """Показать заказы по категориям"""
    filter_type = callback.data.split("_")[2]  # new, checking, paid, etc.
    
    # Получаем заказы в зависимости от фильтра
    if filter_type == "new":
        orders = await db.get_new_orders()
        title = "🆕 Новые заказы"
    elif filter_type == "checking":
        orders = await db.get_checking_orders()
        title = "💰 Заказы на проверке"
    elif filter_type == "paid":
        orders = await db.get_paid_orders()
        title = "✅ Подтвержденные заказы"
    elif filter_type == "shipping":
        orders = await db.get_shipping_orders()
        title = "🚚 Заказы в доставке"
    elif filter_type == "delivered":
        orders = await db.get_delivered_orders()
        title = "📦 Доставленные заказы"
    elif filter_type == "cancelled":
        orders = await db.get_cancelled_orders()
        title = "❌ Отмененные заказы"
    else:
        orders = await db.get_all_orders()
        title = "📋 Все заказы"
    
    if not orders:
        await callback.message.edit_text(
            f"{title}\n\nЗаказов не найдено.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data=callback.data)],
                [InlineKeyboardButton(text=_("common.to_admin"), callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
        return
    
    text = f"<b>{title}</b>\n\nВсего заказов: {len(orders)}\n\n"
    
    # Показываем последние 10 заказов
    for order in orders[:10]:
        status_emoji = {
            'waiting_payment': '⏳',
            'payment_check': '💰',
            'paid': '✅',
            'shipping': '🚚',
            'delivered': '📦',
            'cancelled': '❌'
        }
        
        emoji = status_emoji.get(order[9], '❓')
        text += f"{emoji} Заказ #{order[1]} - {order[4]}₾\n"
        text += f"   {str(order[11])[:16]} - ID: {order[2]}\n\n"
    
    if len(orders) > 10:
        text += f"... и еще {len(orders) - 10} заказов"
    
    # Создаем клавиатуру с заказами
    keyboard = []
    for order in orders[:10]:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📋 Заказ #{order[1]}",
                callback_data=f"admin_order_{order[0]}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=callback.data)])
    keyboard.append([InlineKeyboardButton(text=_("common.to_admin"), callback_data="admin_panel")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )

