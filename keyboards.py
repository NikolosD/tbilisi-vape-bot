from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import i18n
from i18n import _

# Главное меню
def get_main_menu(is_admin=False, user_id=None):
    # Получаем переведенные тексты кнопок
    catalog_text = _("menu.catalog", user_id=user_id)
    cart_text = _("menu.cart", user_id=user_id)
    orders_text = _("menu.orders", user_id=user_id)
    contact_text = _("menu.contact", user_id=user_id)
    info_text = _("menu.info", user_id=user_id)
    language_text = _("menu.language", user_id=user_id)
    admin_text = _("menu.admin_panel", user_id=user_id)
    
    keyboard_rows = [
        [KeyboardButton(text=catalog_text), KeyboardButton(text=cart_text)],
        [KeyboardButton(text=orders_text), KeyboardButton(text=contact_text)],
        [KeyboardButton(text=info_text), KeyboardButton(text=language_text)]
    ]
    
    # Добавляем кнопку админ-панели только для администраторов
    if is_admin:
        keyboard_rows.append([KeyboardButton(text=admin_text)])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
        resize_keyboard=True
    )
    return keyboard

# Inline версия главного меню (для редактирования сообщений)
def get_main_menu_inline(is_admin=False, user_id=None):
    # Получаем переведенные тексты кнопок
    catalog_text = _("menu.catalog", user_id=user_id)
    cart_text = _("menu.cart", user_id=user_id)
    orders_text = _("menu.orders", user_id=user_id)
    contact_text = _("menu.contact", user_id=user_id)
    info_text = _("menu.info", user_id=user_id)
    language_text = _("menu.language", user_id=user_id)
    admin_text = _("menu.admin_panel", user_id=user_id)
    
    keyboard = [
        [InlineKeyboardButton(text=catalog_text, callback_data="catalog")],
        [InlineKeyboardButton(text=cart_text, callback_data="cart")],
        [InlineKeyboardButton(text=orders_text, callback_data="my_orders")],
        [InlineKeyboardButton(text=contact_text, callback_data="contact")],
        [InlineKeyboardButton(text=info_text, callback_data="info")],
        [InlineKeyboardButton(text=language_text, callback_data="language")]
    ]
    
    # Добавляем кнопку админ-панели только для администраторов
    if is_admin:
        keyboard.append([InlineKeyboardButton(text=admin_text, callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Каталог категорий
def get_categories_keyboard(categories, user_id=None):
    keyboard = []
    for category in categories:
        emoji = category[2] if category[2] else "📦"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{emoji} {category[1]}",
                callback_data=f"category_{category[0]}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text=_("common.main_menu", user_id=user_id), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Каталог товаров (inline)
def get_catalog_keyboard(products):
    keyboard = []
    for product in products:
        # Проверяем, является ли product объектом Product или кортежем
        if hasattr(product, 'name'):  # Это объект Product
            name, price, product_id = product.name, product.price, product.id
        else:  # Это кортеж (старый формат)
            name, price, product_id = product[1], product[2], product[0]
            
        keyboard.append([
            InlineKeyboardButton(
                text=f"{name} - {price}₾",
                callback_data=f"product_{product_id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text=_("common.to_categories"), callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Товары в категории (с информацией о категории)
def get_category_products_keyboard(products, category_id, user_id=None):
    keyboard = []
    for product in products:
        # Проверяем, является ли product объектом Product или кортежем
        if hasattr(product, 'name'):  # Это объект Product
            name, price, product_id = product.name, product.price, product.id
            stock_quantity = getattr(product, 'stock_quantity', 0)
        else:  # Это кортеж (старый формат)
            name, price, product_id = product[1], product[2], product[0]
            stock_quantity = 0
        
        # Формируем текст кнопки с количеством
        if stock_quantity > 0:
            button_text = f"{name} - {price}₾ (📦 {stock_quantity} {_('product.pieces', user_id=user_id)})"
        else:
            button_text = f"{name} - {price}₾ (❌ {_('product.out_of_stock', user_id=user_id)})"
            
        keyboard.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"product_{product_id}_from_{category_id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text=_("common.to_categories", user_id=user_id), callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Карточка товара
def get_product_card_keyboard(product_id, in_cart=False, from_category=None):
    if in_cart:
        keyboard = [
            [
                InlineKeyboardButton(text="➖", callback_data=f"cart_decrease_{product_id}"),
                InlineKeyboardButton(text="🔢", callback_data=f"cart_input_qty_{product_id}"),
                InlineKeyboardButton(text="➕", callback_data=f"cart_increase_{product_id}")
            ],
            [InlineKeyboardButton(text=_("product.remove_from_cart"), callback_data=f"cart_remove_{product_id}")],
            [
                InlineKeyboardButton(text=_("menu.cart"), callback_data="cart"),
                InlineKeyboardButton(text=_("common.back"), callback_data=f"category_{from_category}" if from_category else "catalog")
            ],
            [InlineKeyboardButton(text=_("common.to_catalog"), callback_data="catalog")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text=_("product.add_to_cart"), callback_data=f"add_to_cart_{product_id}")],
            [
                InlineKeyboardButton(text=_("menu.cart"), callback_data="cart"),
                InlineKeyboardButton(text=_("common.back"), callback_data=f"category_{from_category}" if from_category else "catalog")
            ],
            [InlineKeyboardButton(text=_("common.to_catalog"), callback_data="catalog")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Клавиатура для отмены ввода количества
def get_quantity_input_cancel_keyboard():
    keyboard = [
        [InlineKeyboardButton(text=_("common.cancel"), callback_data="cancel_quantity_input")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Корзина
def get_cart_keyboard(cart_items):
    keyboard = []
    
    for item in cart_items:
        keyboard.append([
            InlineKeyboardButton(text=f"{item.name} ({item.quantity})", callback_data=f"noop")
        ])
        keyboard.append([
            InlineKeyboardButton(text="➖", callback_data=f"cart_decrease_{item.product_id}"),
            InlineKeyboardButton(text="🔢", callback_data=f"cart_input_qty_{item.product_id}"),
            InlineKeyboardButton(text="➕", callback_data=f"cart_increase_{item.product_id}")
        ])
    
    if cart_items:
        keyboard.append([InlineKeyboardButton(text=_("cart.checkout"), callback_data="checkout")])
        keyboard.append([InlineKeyboardButton(text=_("cart.clear"), callback_data="clear_cart")])
    
    keyboard.append([InlineKeyboardButton(text=_("common.main_menu"), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Запрос геолокации для доставки
def get_location_request_keyboard(user_id=None):
    """Клавиатура для запроса геолокации"""
    keyboard = [
        # Кнопка для отправки геолокации (reply keyboard)
        [KeyboardButton(text=_("checkout.share_location", user_id=user_id), request_location=True)],
        [KeyboardButton(text=_("checkout.manual_address", user_id=user_id))],
        [KeyboardButton(text="🗺️ Отправить точку на карте")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

# Inline клавиатура для геолокации
def get_location_inline_keyboard(user_id=None):
    """Inline клавиатура для геолокации"""
    keyboard = [
        [InlineKeyboardButton(text=_("checkout.manual_address", user_id=user_id), callback_data="manual_address")],
        [InlineKeyboardButton(text=_("common.back", user_id=user_id), callback_data="cart")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Подтверждение заказа
def get_order_confirmation_keyboard(order_id, user_id=None):
    keyboard = [
        [InlineKeyboardButton(text=_("common.paid", user_id=user_id), callback_data=f"payment_done_{order_id}")],
        [InlineKeyboardButton(text=_("orders.cancel", user_id=user_id), callback_data=f"cancel_order_{order_id}")],
        [InlineKeyboardButton(text=_("common.my_orders", user_id=user_id), callback_data="my_orders")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Заказы пользователя
def get_orders_keyboard(orders, user_id=None):
    keyboard = []
    
    for order in orders:
        # Теперь order - это объект модели Order
        order_id = order.id  # внутренний ID для callback
        order_number = order.order_number  # реальный номер заказа для отображения
        status = order.status
        total = order.total_price
        
        status_emoji = {
            'waiting_payment': '⏳',
            'payment_check': '💰',
            'paid': '✅',
            'shipping': '🚚',
            'delivered': '✅',
            'cancelled': '❌'
        }
        
        status_text = {
            'waiting_payment': _('status.waiting_payment', user_id=user_id),
            'payment_check': _('status.payment_check', user_id=user_id),
            'paid': _('status.paid', user_id=user_id),
            'shipping': _('status.shipping', user_id=user_id),
            'delivered': _('status.delivered', user_id=user_id),
            'cancelled': _('status.cancelled', user_id=user_id)
        }
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status_emoji.get(status, '❓')} " + _("common.order_number", user_id=user_id, order_id=order_number, total=total),
                callback_data=f"order_{order_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text=_("common.main_menu", user_id=user_id), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Детали заказа
def get_order_details_keyboard(order_id, status):
    keyboard = []
    
    if status == 'waiting_payment':
        keyboard.append([InlineKeyboardButton(text=_("common.paid"), callback_data=f"payment_done_{order_id}")])
        keyboard.append([InlineKeyboardButton(text=_("common.cancel"), callback_data=f"cancel_order_{order_id}")])
    elif status == 'payment_check':
        keyboard.append([InlineKeyboardButton(text=_("common.resend_screenshot"), callback_data=f"resend_screenshot_{order_id}")])
    
    keyboard.append([InlineKeyboardButton(text=_("common.to_orders"), callback_data="my_orders")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Запрос контакта
def get_contact_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("common.share_phone"), request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_contact_keyboard_with_message(user_id=None):
    """Клавиатура для страницы контактов с кнопкой написать админу"""
    buttons = [
        [InlineKeyboardButton(text=_("contact.message_admin", user_id=user_id), callback_data="message_admin")],
        [InlineKeyboardButton(text=_("common.main_menu", user_id=user_id), callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Админ панель
def get_admin_keyboard(user_id=None):
    from config import SUPER_ADMIN_ID
    
    keyboard = [
        [InlineKeyboardButton(text=_("admin.products"), callback_data="admin_products")],
        [InlineKeyboardButton(text=_("admin.all_orders"), callback_data="admin_all_orders")],
        [InlineKeyboardButton(text=_("admin.stats"), callback_data="admin_stats")],
        [InlineKeyboardButton(text=_("admin.broadcast"), callback_data="admin_broadcast")],
        [InlineKeyboardButton(text=_("admin.message_client"), callback_data="admin_message_client")]
    ]
    
    # Добавляем кнопку управления админами только для супер-админа
    if user_id == SUPER_ADMIN_ID:
        keyboard.append([InlineKeyboardButton(text=_("admin.manage_admins"), callback_data="manage_admins")])
    
    keyboard.append([InlineKeyboardButton(text=_("common.main_menu"), callback_data="back_to_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Управление администраторами (для супер-админа)
def get_admin_management_keyboard():
    keyboard = [
        [InlineKeyboardButton(text=_("admin.add_admin"), callback_data="add_admin")],
        [InlineKeyboardButton(text=_("admin.remove_admin"), callback_data="remove_admin")],
        [InlineKeyboardButton(text=_("admin.list_admins"), callback_data="list_admins")],
        [InlineKeyboardButton(text=_("common.back"), callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Клавиатура со списком админов для удаления
def get_admins_list_keyboard(admins, action="remove"):
    keyboard = []
    for admin in admins:
        user_id = admin['user_id'] if isinstance(admin, dict) else admin[0]
        username = admin.get('username', 'Нет username') if isinstance(admin, dict) else admin[1] or 'Нет username'
        first_name = admin.get('first_name', 'Нет имени') if isinstance(admin, dict) else admin[2] or 'Нет имени'
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"❌ {first_name} (@{username})",
                callback_data=f"{action}_admin_{user_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text=_("common.back"), callback_data="manage_admins")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Управление товарами (админ)
def get_admin_products_keyboard():
    keyboard = [
        [InlineKeyboardButton(text=_("admin.add_product"), callback_data="admin_add_product")],
        [InlineKeyboardButton(text=_("admin.edit_products"), callback_data="admin_edit_products")],
        [InlineKeyboardButton(text=_("admin.categories"), callback_data="admin_categories")],
        [InlineKeyboardButton(text=_("common.to_admin"), callback_data="admin_panel")]
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
    keyboard.append([InlineKeyboardButton(text=_("common.to_products"), callback_data="admin_products")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Управление категориями (админ)
def get_admin_categories_keyboard():
    keyboard = [
        [InlineKeyboardButton(text=_("admin.add_category"), callback_data="admin_add_category")],
        [InlineKeyboardButton(text=_("admin.edit_categories"), callback_data="admin_edit_categories")],
        [InlineKeyboardButton(text=_("common.to_products"), callback_data="admin_products")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Заказы для админа
def get_admin_orders_keyboard(orders):
    keyboard = []
    
    for order in orders:
        # Теперь order - это объект модели Order
        order_id = order.id  # внутренний ID для callback
        order_number = order.order_number  # реальный номер заказа для отображения
        user_id = order.user_id
        status = order.status
        total = order.total_price
        
        status_emoji = {
            'waiting_payment': '⏳',
            'payment_check': '💰',
            'paid': '✅',
            'shipping': '🚚',
            'delivered': '✅',
            'cancelled': '❌'
        }
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status_emoji.get(status, '❓')} {_('orders.order')} #{order_number} - {total}₾ (ID: {user_id})",
                callback_data=f"admin_order_{order_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text=_("common.back"), callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Действия с заказом (админ)
def get_admin_order_actions_keyboard(order_id, status, from_all_orders=False):
    keyboard = []
    
    # Основные действия в зависимости от статуса
    if status == 'payment_check':
        keyboard.append([InlineKeyboardButton(text=_("admin_actions.confirm_payment"), callback_data=f"admin_confirm_payment_{order_id}")])
        keyboard.append([InlineKeyboardButton(text=_("admin_actions.reject_payment"), callback_data=f"admin_reject_payment_{order_id}")])
    elif status == 'paid':
        keyboard.append([InlineKeyboardButton(text=_("admin_actions.mark_shipped"), callback_data=f"admin_ship_{order_id}")])
    elif status == 'shipping':
        keyboard.append([InlineKeyboardButton(text=_("admin_actions.mark_delivered"), callback_data=f"admin_deliver_{order_id}")])
    
    # Действия доступные всегда (для исправления ошибок)
    if status != 'cancelled':
        keyboard.append([InlineKeyboardButton(text=_("admin_actions.cancel_order"), callback_data=f"admin_cancel_{order_id}")])
    
    # Возможность изменить статус вручную для завершенных заказов
    if status in ['delivered', 'cancelled']:
        keyboard.append([InlineKeyboardButton(text=_("admin_actions.change_status"), callback_data=f"admin_change_status_{order_id}")])
    
    # Кнопка написать клиенту (доступна всегда)
    keyboard.append([InlineKeyboardButton(text=_("admin_actions.message_client"), callback_data=f"admin_message_client_{order_id}")])
    
    # Кнопка возврата
    keyboard.append([InlineKeyboardButton(text=_("common.to_admin"), callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Клавиатура для смены статуса заказа
def get_change_status_keyboard(order_id, user_id=None):
    keyboard = [
        [InlineKeyboardButton(text=f"⏳ {_('status.waiting_payment', user_id=user_id)}", callback_data=f"set_status_waiting_payment_{order_id}")],
        [InlineKeyboardButton(text=f"💰 {_('status.payment_check', user_id=user_id)}", callback_data=f"set_status_payment_check_{order_id}")],
        [InlineKeyboardButton(text=f"✅ {_('status.paid', user_id=user_id)}", callback_data=f"set_status_paid_{order_id}")],
        [InlineKeyboardButton(text=f"🚚 {_('status.shipping', user_id=user_id)}", callback_data=f"set_status_shipping_{order_id}")],
        [InlineKeyboardButton(text=f"✅ {_('status.delivered', user_id=user_id)}", callback_data=f"set_status_delivered_{order_id}")],
        [InlineKeyboardButton(text=f"❌ {_('status.cancelled', user_id=user_id)}", callback_data=f"set_status_cancelled_{order_id}")],
        [InlineKeyboardButton(text=_("common.back", user_id=user_id), callback_data=f"admin_order_{order_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Выбор языка
# Простая клавиатура с кнопкой "Назад в главное меню"
def get_back_to_menu_keyboard(user_id=None):
    keyboard = [
        [InlineKeyboardButton(text=_("common.main_menu", user_id=user_id), callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_language_keyboard(user_id=None):
    keyboard = []
    
    # Получаем список доступных языков
    available_languages = i18n.i18n.get_available_languages()
    
    # Сопоставление кодов языков с ключами переводов
    language_mapping = {
        'ru': 'russian',
        'en': 'english',
        'ka': 'georgian'
    }
    
    # Создаем кнопки для каждого доступного языка
    for lang_code in available_languages:
        language_key = language_mapping.get(lang_code)
        if language_key:
            button_text = _(f"language.{language_key}", user_id=user_id)
            callback_data = f"lang_{lang_code}"
            keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    
    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton(text=_("common.back", user_id=user_id), callback_data="back_to_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Быстрые действия в уведомлениях админу
def get_payment_notification_keyboard(order_id, user_id=None):
    keyboard = [
        [
            InlineKeyboardButton(text=f"✅ {_('common.confirm', user_id=user_id)}", callback_data=f"quick_confirm_{order_id}"),
            InlineKeyboardButton(text=f"❌ {_('admin_actions.reject_payment', user_id=user_id)}", callback_data=f"quick_reject_{order_id}")
        ],
        [InlineKeyboardButton(text=f"📊 {_('admin.all_orders', user_id=user_id)}", callback_data="admin_orders")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Улучшенная админ-панель с фильтрами заказов
def get_enhanced_admin_keyboard(user_id=None):
    from config import SUPER_ADMIN_ID
    
    keyboard = [
        [
            InlineKeyboardButton(text=f"🆕 {_('admin.orders', user_id=user_id)}", callback_data="admin_orders_new"),
            InlineKeyboardButton(text=f"💰 {_('status.payment_check', user_id=user_id)}", callback_data="admin_orders_checking")
        ],
        [
            InlineKeyboardButton(text=f"✅ {_('status.paid', user_id=user_id)}", callback_data="admin_orders_paid"),
            InlineKeyboardButton(text=f"🚚 {_('status.shipping', user_id=user_id)}", callback_data="admin_orders_shipping")
        ],
        [
            InlineKeyboardButton(text=f"📦 {_('status.delivered', user_id=user_id)}", callback_data="admin_orders_delivered"),
            InlineKeyboardButton(text=f"❌ {_('status.cancelled', user_id=user_id)}", callback_data="admin_orders_cancelled")
        ],
        [InlineKeyboardButton(text=_("admin.all_orders", user_id=user_id), callback_data="admin_all_orders")],
        [InlineKeyboardButton(text=_("admin.products", user_id=user_id), callback_data="admin_products")],
        [InlineKeyboardButton(text=_("admin.stats", user_id=user_id), callback_data="admin_stats")],
        [InlineKeyboardButton(text=_("admin.broadcast", user_id=user_id), callback_data="admin_broadcast")],
        [InlineKeyboardButton(text=_("admin.message_client", user_id=user_id), callback_data="admin_message_client")]
    ]
    
    # Добавляем кнопку управления админами только для супер-админа
    if user_id == SUPER_ADMIN_ID:
        keyboard.append([InlineKeyboardButton(text=_("admin.manage_admins", user_id=user_id), callback_data="manage_admins")])
    
    keyboard.append([InlineKeyboardButton(text=_("common.main_menu", user_id=user_id), callback_data="back_to_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Фильтр заказов по статусу
def get_orders_filter_keyboard(user_id=None):
    keyboard = [
        [
            InlineKeyboardButton(text=f"🆕 {_('admin.orders', user_id=user_id)}", callback_data="filter_waiting_payment"),
            InlineKeyboardButton(text=f"💰 {_('status.payment_check', user_id=user_id)}", callback_data="filter_payment_check")
        ],
        [
            InlineKeyboardButton(text=f"✅ {_('status.paid', user_id=user_id)}", callback_data="filter_paid"),
            InlineKeyboardButton(text=f"🚚 {_('status.shipping', user_id=user_id)}", callback_data="filter_shipping")
        ],
        [
            InlineKeyboardButton(text=f"📦 {_('status.delivered', user_id=user_id)}", callback_data="filter_delivered"),
            InlineKeyboardButton(text=f"❌ {_('status.cancelled', user_id=user_id)}", callback_data="filter_cancelled")
        ],
        [InlineKeyboardButton(text=f"📋 {_('admin.all_orders', user_id=user_id)}", callback_data="filter_all")],
        [InlineKeyboardButton(text=_("common.to_admin", user_id=user_id), callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)