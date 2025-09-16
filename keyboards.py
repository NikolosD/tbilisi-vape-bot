from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from i18n import _

# Главное меню
def get_main_menu(is_admin=False):
    keyboard_rows = [
        [KeyboardButton(text=_("menu.catalog")), KeyboardButton(text=_("menu.cart"))],
        [KeyboardButton(text=_("menu.orders")), KeyboardButton(text=_("menu.contact"))],
        [KeyboardButton(text=_("menu.info"))]
    ]
    
    # Добавляем кнопку админ-панели только для администраторов
    if is_admin:
        keyboard_rows.append([KeyboardButton(text=_("menu.admin_panel"))])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
        resize_keyboard=True,
        persistent=True
    )
    return keyboard

# Каталог категорий
def get_categories_keyboard(categories):
    keyboard = []
    for category in categories:
        emoji = category[2] if category[2] else "📦"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{emoji} {category[1]}",
                callback_data=f"category_{category[0]}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text=_("cart.back_to_menu"), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Каталог товаров (inline)
def get_catalog_keyboard(products):
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{product[1]} - {product[2]}₾",
                callback_data=f"product_{product[0]}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 К категориям", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Карточка товара
def get_product_card_keyboard(product_id, in_cart=False):
    if in_cart:
        keyboard = [
            [
                InlineKeyboardButton(text="➖", callback_data=f"cart_decrease_{product_id}"),
                InlineKeyboardButton(text="➕", callback_data=f"cart_increase_{product_id}")
            ],
            [InlineKeyboardButton(text="❌ Удалить из корзины", callback_data=f"cart_remove_{product_id}")],
            [InlineKeyboardButton(text="🔙 К каталогу", callback_data="catalog")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text="🛒 Добавить в корзину", callback_data=f"add_to_cart_{product_id}")],
            [InlineKeyboardButton(text="🔙 К каталогу", callback_data="catalog")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Корзина
def get_cart_keyboard(cart_items):
    keyboard = []
    
    for item in cart_items:
        product_id = item[0]
        quantity = item[1]
        name = item[2]
        keyboard.append([
            InlineKeyboardButton(text=f"➖", callback_data=f"cart_decrease_{product_id}"),
            InlineKeyboardButton(text=f"{name} ({quantity})", callback_data=f"product_{product_id}"),
            InlineKeyboardButton(text=f"➕", callback_data=f"cart_increase_{product_id}")
        ])
        keyboard.append([
            InlineKeyboardButton(text=f"❌ Удалить", callback_data=f"cart_remove_{product_id}")
        ])
    
    if cart_items:
        keyboard.append([InlineKeyboardButton(text="📝 Оформить заказ", callback_data="checkout")])
        keyboard.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")])
    
    keyboard.append([InlineKeyboardButton(text=_("cart.back_to_menu"), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Выбор зоны доставки
def get_delivery_zones_keyboard():
    from config import DELIVERY_ZONES
    keyboard = []
    
    for zone_id, zone_info in DELIVERY_ZONES.items():
        keyboard.append([
            InlineKeyboardButton(
                text=f"{zone_info['name']} - {zone_info['price']}₾ ({zone_info['time']})",
                callback_data=f"delivery_{zone_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cart")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Подтверждение заказа
def get_order_confirmation_keyboard(order_id):
    keyboard = [
        [InlineKeyboardButton(text="💳 Оплатил(а)", callback_data=f"payment_done_{order_id}")],
        [InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel_order_{order_id}")],
        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Заказы пользователя
def get_orders_keyboard(orders):
    keyboard = []
    
    for order in orders:
        order_id = order[0]
        status = order[8]
        created_at = order[10]
        total = order[3]
        
        status_emoji = {
            'waiting_payment': '⏳',
            'payment_check': '💰',
            'paid': '✅',
            'shipping': '🚚',
            'delivered': '✅',
            'cancelled': '❌'
        }
        
        status_text = {
            'waiting_payment': 'Ожидает оплаты',
            'payment_check': 'Проверка оплаты',
            'paid': 'Оплачен',
            'shipping': 'Отправлен',
            'delivered': 'Доставлен',
            'cancelled': 'Отменен'
        }
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status_emoji.get(status, '❓')} Заказ #{order_id} - {total}₾",
                callback_data=f"order_{order_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text=_("cart.back_to_menu"), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Детали заказа
def get_order_details_keyboard(order_id, status):
    keyboard = []
    
    if status == 'waiting_payment':
        keyboard.append([InlineKeyboardButton(text="💳 Оплатил(а)", callback_data=f"payment_done_{order_id}")])
        keyboard.append([InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_order_{order_id}")])
    elif status == 'payment_check':
        keyboard.append([InlineKeyboardButton(text="📸 Отправить скриншот еще раз", callback_data=f"resend_screenshot_{order_id}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Мои заказы", callback_data="my_orders")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Запрос контакта
def get_contact_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться номером", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

# Админ панель
def get_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📦 Управление товарами", callback_data="admin_products")],
        [InlineKeyboardButton(text="📋 Новые заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Управление товарами (админ)
def get_admin_products_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton(text="📝 Редактировать товары", callback_data="admin_edit_products")],
        [InlineKeyboardButton(text="🏷️ Управление категориями", callback_data="admin_categories")],
        [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Выбор категории для товара (админ)
def get_category_selection_keyboard(categories):
    keyboard = []
    for category in categories:
        emoji = category[2] if category[2] else "📦"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{emoji} {category[1]}",
                callback_data=f"select_category_{category[0]}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Управление товарами", callback_data="admin_products")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Управление категориями (админ)
def get_admin_categories_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin_add_category")],
        [InlineKeyboardButton(text="📝 Редактировать категории", callback_data="admin_edit_categories")],
        [InlineKeyboardButton(text="🔙 Управление товарами", callback_data="admin_products")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Заказы для админа
def get_admin_orders_keyboard(orders):
    keyboard = []
    
    for order in orders:
        order_id = order[0]
        user_id = order[1]
        status = order[8]
        total = order[3]
        
        status_emoji = {
            'waiting_payment': '⏳',
            'payment_check': '💰'
        }
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status_emoji.get(status, '❓')} #{order_id} - {total}₾ (ID: {user_id})",
                callback_data=f"admin_order_{order_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Действия с заказом (админ)
def get_admin_order_actions_keyboard(order_id, status):
    keyboard = []
    
    if status == 'payment_check':
        keyboard.append([InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"admin_confirm_payment_{order_id}")])
        keyboard.append([InlineKeyboardButton(text="❌ Отклонить оплату", callback_data=f"admin_reject_payment_{order_id}")])
    elif status == 'paid':
        keyboard.append([InlineKeyboardButton(text="🚚 Отметить как отправлено", callback_data=f"admin_ship_{order_id}")])
    elif status == 'shipping':
        keyboard.append([InlineKeyboardButton(text="✅ Отметить как доставлено", callback_data=f"admin_deliver_{order_id}")])
    
    keyboard.append([InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"admin_cancel_{order_id}")])
    keyboard.append([InlineKeyboardButton(text="🔙 К заказам", callback_data="admin_orders")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)