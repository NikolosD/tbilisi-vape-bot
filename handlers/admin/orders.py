from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS, DELIVERY_ZONES
from database import db
from filters.admin import admin_filter
from keyboards import get_admin_order_actions_keyboard
from i18n import _
from utils.loader import with_loader
from handlers.user_modules.cart import delete_message_after_delay

router = Router()

class OrderStates(StatesGroup):
    waiting_order_search = State()
    waiting_rejection_reason = State()
    waiting_client_message = State()

# Обработчик отклонения перенесен в main.py для избежания конфликтов

async def safe_edit_message(callback, text, reply_markup=None, parse_mode='HTML'):
    """Безопасно редактировать сообщение (поддерживает и text и caption)"""
    try:
        if callback.message.photo:
            # Если есть фото, редактируем caption
            await callback.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            # Если обычное текстовое сообщение, редактируем text
            await callback.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except Exception as e:
        # Если редактирование не удалось, удаляем старое и создаем новое
        try:
            await callback.message.delete()
        except:
            pass
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

@router.callback_query(F.data == "admin_all_orders", admin_filter)
async def admin_all_orders_menu(callback: CallbackQuery):
    """Меню всех заказов для админа с пагинацией"""
    await admin_all_orders_page(callback, 1)

@router.callback_query(F.data.startswith("admin_all_orders_page_"), admin_filter)
async def admin_all_orders_pagination(callback: CallbackQuery):
    """Пагинация для всех заказов админа"""
    page = int(callback.data.split("_")[-1])
    await admin_all_orders_page(callback, page)

@router.callback_query(F.data == "admin_search_order", admin_filter)
async def admin_search_order(callback: CallbackQuery, state: FSMContext):
    """Начать поиск заказа по номеру"""
    await state.set_state(OrderStates.waiting_order_search)
    await callback.message.edit_text(
        "🔍 <b>Поиск заказа</b>\n\n"
        "Введите номер заказа для поиска:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Все заказы", callback_data="admin_all_orders")]
        ]),
        parse_mode='HTML'
    )

async def admin_all_orders_page(callback: CallbackQuery, page: int):
    """Отобразить страницу всех заказов"""
    from components.pagination import pagination
    
    orders = await db.get_all_orders()
    
    if not orders:
        text = "📋 <b>Все заказы</b>\n\nЗаказов пока нет."
        
        try:
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
                ]),
                parse_mode='HTML'
            )
        except Exception:
            await callback.message.delete()
            await callback.message.answer(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
                ]),
                parse_mode='HTML'
            )
        return

    pagination.items_per_page = 8
    pagination_info = pagination.paginate(orders, page)
    
    text = f"📋 <b>Все заказы</b>\n\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"{_('admin.total_orders', user_id=callback.from_user.id)} <b>{len(orders)}</b>\n"
    text += pagination.get_page_info_text(pagination_info, user_id=callback.from_user.id)
    text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for order in pagination_info['items']:
        status_emoji = "⏳" if order.status == "waiting_payment" else "💰" if order.status == "payment_check" else "✅" if order.status == "paid" else "🚚" if order.status == "shipping" else "📦" if order.status == "delivered" else "❌"
        text += f"{status_emoji} <b>№{order.order_number}</b> - {order.total_price}₾\n"
        text += f"📅 {order.created_at.strftime('%d.%m %H:%M')} | 👤 ID:{order.user_id}\n\n"

    def order_button_generator(order, index):
        status_emoji = "⏳" if order.status == "waiting_payment" else "💰" if order.status == "payment_check" else "✅" if order.status == "paid" else "🚚" if order.status == "shipping" else "📦" if order.status == "delivered" else "❌"
        return InlineKeyboardButton(
            text=f"{status_emoji} №{order.order_number} - {order.total_price}₾",
            callback_data=f"admin_order_{order.id}"
        )

    additional_buttons = [
        [
            InlineKeyboardButton(text="⏳ Ожидающие", callback_data="filter_orders_pending"),
            InlineKeyboardButton(text="💰 На проверке", callback_data="filter_orders_checking")
        ],
        [
            InlineKeyboardButton(text="✅ Оплачены", callback_data="filter_orders_paid"),
            InlineKeyboardButton(text="🚚 В доставке", callback_data="filter_orders_shipping")
        ],
        [
            InlineKeyboardButton(text="📦 Доставлены", callback_data="filter_orders_delivered"),
            InlineKeyboardButton(text="❌ Отменены", callback_data="filter_orders_cancelled")
        ],
        [InlineKeyboardButton(text="🔍 Поиск по номеру", callback_data="admin_search_order")],
        [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
    ]

    keyboard = pagination.create_pagination_keyboard(
        pagination_info=pagination_info,
        callback_prefix="admin_all_orders_page",
        user_id=callback.from_user.id,
        item_button_generator=order_button_generator,
        additional_buttons=additional_buttons
    )
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    except Exception:
        await callback.message.delete()
        await callback.message.answer(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )

@router.callback_query(F.data.startswith("admin_reject_payment_"), admin_filter)
async def reject_payment(callback: CallbackQuery, state: FSMContext):
    """Отклонить оплату заказа - запрос причины"""
    order_id = int(callback.data.split("_")[3])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer(_("admin.order_not_found", user_id=callback.from_user.id), show_alert=True)
        return
    
    user = await db.get_user(order.user_id)
    user_lang = 'ru'
    if user:
        from i18n import i18n
        user_lang = i18n.get_user_language(order.user_id) or 'ru'
    
    await state.update_data(
        order_id=order_id, 
        order_number=order.order_number, 
        user_id=order.user_id,
        total_price=order.total_price,
        user_lang=user_lang
    )
    
    lang_names = {'ru': '🇷🇺 Русский', 'en': '🇺🇸 English', 'ka': '🇬🇪 ქართული'}
    
    text = _("admin.rejection_form", user_id=callback.from_user.id, 
             order_number=order.order_number, 
             total_price=order.total_price,
             user_language=lang_names.get(user_lang, user_lang))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_order_{order_id}")]
    ])
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=keyboard, parse_mode='HTML')
    else:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode='HTML')
    
    await state.set_state(OrderStates.waiting_rejection_reason)

@router.callback_query(F.data.startswith("admin_order_"), admin_filter)
async def show_admin_order(callback: CallbackQuery):
    """Показать детали заказа для админа"""
    parts = callback.data.split("_")
    if parts[0] == "admin" and parts[1] == "order":
        order_id = int(parts[2])
    elif len(parts) >= 3:
        order_id = int(parts[-1])
    else:
        await callback.answer("❌ Ошибка: некорректный формат данных", show_alert=True)
        return
        
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    products = order.products_data
    user = await db.get_user(order.user_id)
    
    status_text = {
        'waiting_payment': '⏳ Ожидает оплаты',
        'payment_check': '💰 Проверка оплаты',
        'paid': '✅ Оплачен, готовится к отправке',
        'shipping': '🚚 Отправлен',
        'delivered': '✅ Доставлен',
        'cancelled': '❌ Отменен'
    }
    
    from i18n import i18n
    user_language = i18n.get_user_language(order.user_id)
    language_names = {'ru': 'Русский', 'ka': 'ქართული', 'en': 'English'}
    
    order_text = f"""📋 <b>Заказ #{order.order_number}</b>

👤 <b>Клиент:</b>
• Имя: {user.first_name if user else 'Неизвестно'}
• Username: @{user.username if user and user.username else 'нет'}
• ID: {order.user_id}
• 🌐 Язык: {language_names.get(user_language, user_language)}

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
    
    if order.payment_screenshot:
        try:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=order.payment_screenshot,
                caption=order_text,
                reply_markup=get_admin_order_actions_keyboard(order_id, order.status),
                parse_mode='HTML'
            )
        except:
            await callback.message.edit_text(
                order_text + "\n\n📸 Скриншот оплаты прикреплен",
                reply_markup=get_admin_order_actions_keyboard(order_id, order.status),
                parse_mode='HTML'
            )
    else:
        await callback.message.edit_text(
            order_text,
            reply_markup=get_admin_order_actions_keyboard(order_id, order.status),
            parse_mode='HTML'
        )

@router.callback_query(F.data.startswith("admin_confirm_payment_"), admin_filter)
async def confirm_payment(callback: CallbackQuery):
    """Подтвердить оплату заказа"""
    order_id = int(callback.data.split("_")[3])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Создаем функцию для выполнения с лоадером
    async def confirm_payment_operation():
        # Списываем товары со склада при подтверждении платежа
        try:
            products = order.products_data
            for product in products:
                await db.decrease_product_quantity(product['id'], product['quantity'])
        except Exception as e:
            print(f"Error decreasing stock on payment confirmation: {e}")
        
        await db.update_order_status(order_id, 'paid')
        return order
    
    # Выполняем подтверждение с лоадером
    try:
        await with_loader(
            confirm_payment_operation,
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
            user_id=callback.from_user.id,
            loader_text="Подтверждаем оплату и списываем товары...",
            success_text="✅ Оплата подтверждена!"
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка подтверждения: {e}", show_alert=True)
        return
    
    try:
        await callback.message.bot.send_message(
            order.user_id,
            f"✅ <b>Оплата подтверждена!</b>\n\n"
            f"Заказ #{order.order_number} принят в обработку.\n"
            f"Готовим ваш заказ к отправке! 📦",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
            ]),
            parse_mode='HTML'
        )
    except:
        pass
    
    # Показываем временное уведомление об успехе
    success_msg = await callback.message.answer(
        "✅ <b>Оплата подтверждена!</b>\n\n"
        "🔄 Товары списаны со склада\n"
        "📧 Уведомление отправлено клиенту",
        parse_mode='HTML'
    )
    
    # Удаляем уведомление через 3 секунды
    import asyncio
    asyncio.create_task(delete_message_after_delay(callback.bot, callback.message.chat.id, success_msg.message_id, 3))
    
    await show_admin_order(callback)

@router.message(admin_filter)
async def debug_all_admin_messages(message: Message, state: FSMContext):
    """Отладочный обработчик для всех админских сообщений"""
    current_state = await state.get_state()
    data = await state.get_data()
    print("🐛" + "="*50)
    print(f"🐛 ADMIN MESSAGE INTERCEPTED!")
    print(f"🐛 User: {message.from_user.id}")
    print(f"🐛 Text: '{message.text}'")
    print(f"🐛 Current state: {current_state}")
    print(f"🐛 State data: {data}")
    print(f"🐛 Expected state: 'OrderStates:waiting_rejection_reason'")
    print("🐛" + "="*50)

@router.message(OrderStates.waiting_rejection_reason, admin_filter)
async def process_rejection_reason(message: Message, state: FSMContext):
    """Обработка причины отклонения платежа"""
    print("=" * 50)
    print("DEBUG: REJECTION HANDLER CALLED!")
    print(f"DEBUG: Admin ID: {message.from_user.id}")
    print(f"DEBUG: Message text: {message.text}")
    print(f"DEBUG: Current state: {await state.get_state()}")
    print("=" * 50)
    
    reason = message.text
    data = await state.get_data()
    print(f"DEBUG: State data: {data}")
    
    order_id = data.get('order_id')
    order_number = data.get('order_number')
    user_id = data.get('user_id')
    total_price = data.get('total_price')
    user_lang = data.get('user_lang', 'ru')
    
    print(f"DEBUG: Sending rejection message to user {user_id} for order {order_number}")
    
    if not order_id:
        await message.answer(_("admin.rejection_data_error", user_id=message.from_user.id))
        await state.clear()
        return
    
    await db.update_order_status(order_id, 'waiting_payment')
    # Очищаем скриншот чтобы пользователь мог отправить новый
    await db.update_order_screenshot(order_id, None)
    
    message_text = _("admin.payment_rejected", user_id=user_id, 
                    order_number=order_number, 
                    total_price=total_price,
                    reason=reason)
    
    resend_text = _("admin.resend_screenshot", user_id=user_id)
    contact_text = _("admin.contact_support", user_id=user_id)
    menu_text = _("common.main_menu", user_id=user_id)
    
    try:
        print(f"DEBUG: Sending message to user {user_id}")
        print(f"DEBUG: Message text: {message_text}")
        
        await message.bot.send_message(
            user_id,
            message_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=resend_text, callback_data=f"resend_screenshot_{order_number}")],
                [InlineKeyboardButton(text=contact_text, callback_data="contact")],
                [InlineKeyboardButton(text=menu_text, callback_data="back_to_menu")]
            ]),
            parse_mode='HTML'
        )
        print(f"DEBUG: Message sent successfully to user {user_id}")
        await message.answer("✅ Сообщение об отклонении отправлено пользователю!")
    except Exception as e:
        print(f"DEBUG: Error sending message to user {user_id}: {e}")
        import traceback
        print(f"DEBUG: Full error: {traceback.format_exc()}")
        await message.answer(f"❌ Ошибка отправки сообщения: {str(e)}")
    
    await state.clear()
    
    await message.answer(
        "📋 <b>Управление заказами</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_all_orders")],
            [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
        ]),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("admin_ship_"), admin_filter)
async def ship_order(callback: CallbackQuery):
    """Отметить заказ как отправленный"""
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Создаем функцию для выполнения с лоадером
    async def ship_order_operation():
        await db.update_order_status(order_id, 'shipping')
        
        try:
            await callback.message.bot.send_message(
                order.user_id,
                f"🚚 <b>Заказ в пути!</b>\n\n"
                f"Заказ #{order.order_number} отправлен по адресу:\n"
                f"{order.address}\n\n"
                f"Ожидайте курьера! 📦",
                parse_mode='HTML'
            )
        except:
            pass
        
        return {"text": "🚚 Заказ отправлен и клиент уведомлен!"}
    
    # Выполняем отправку с лоадером
    try:
        await with_loader(
            ship_order_operation,
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
            user_id=callback.from_user.id,
            loader_text="Отправляем заказ и уведомляем клиента..."
        )
        await show_admin_order(callback)
    except Exception as e:
        await callback.answer(f"❌ Ошибка отправки: {e}", show_alert=True)

@router.callback_query(F.data.startswith("admin_deliver_"), admin_filter)
async def deliver_order(callback: CallbackQuery):
    """Отметить заказ как доставленный"""
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Создаем функцию для выполнения с лоадером
    async def deliver_order_operation():
        await db.update_order_status(order_id, 'delivered')
        
        try:
            await callback.message.bot.send_message(
                order.user_id,
                f"✅ <b>Заказ доставлен!</b>\n\n"
                f"Заказ #{order.order_number} успешно доставлен.\n"
                f"Спасибо за покупку! 🙏\n\n"
                f"Оцените качество обслуживания и поделитесь отзывом!",
                parse_mode='HTML'
            )
        except:
            pass
        
        return {"text": "✅ Заказ доставлен и клиент уведомлен!"}
    
    # Выполняем доставку с лоадером
    try:
        await with_loader(
            deliver_order_operation,
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
            user_id=callback.from_user.id,
            loader_text="Отмечаем доставку и уведомляем клиента..."
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка доставки: {e}", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📋 <b>Управление заказами</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_all_orders")],
            [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
        ]),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("admin_cancel_"), admin_filter)
async def admin_cancel_order(callback: CallbackQuery):
    """Отменить заказ"""
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Возвращаем товары на склад только если заказ был подтвержден (товары были списаны)
    if order.status in ['paid', 'shipping', 'delivered'] and order.status != 'cancelled':
        try:
            products = order.products_data
            for product in products:
                await db.increase_product_quantity(product['id'], product['quantity'])
        except Exception as e:
            print(f"Error returning products to stock: {e}")
    
    await db.update_order_status(order_id, 'cancelled')
    
    try:
        await callback.message.bot.send_message(
            order.user_id,
            f"❌ <b>Заказ отменен</b>\n\n"
            f"Заказ #{order.order_number} был отменен администратором.\n"
            f"Если у вас есть вопросы, обратитесь в поддержку.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ]),
            parse_mode='HTML'
        )
    except:
        pass
    
    await callback.answer("❌ Заказ отменен!")
    
    await safe_edit_message(
        callback,
        "📋 <b>Управление заказами</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_all_orders")],
            [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
        ])
    )

@router.callback_query(F.data.startswith("admin_change_status_"), admin_filter)
async def change_order_status_menu(callback: CallbackQuery):
    """Меню изменения статуса заказа"""
    order_id = int(callback.data.split("_")[3])
    
    statuses = [
        ("waiting_payment", "⏳ Ожидает оплаты"),
        ("payment_check", "💰 Проверка оплаты"),
        ("paid", "✅ Оплачен"),
        ("shipping", "🚚 Отправлен"),
        ("delivered", "📦 Доставлен"),
        ("cancelled", "❌ Отменен")
    ]
    
    keyboard = []
    for status, text in statuses:
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"set_status_{status}_{order_id}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 К заказу", callback_data=f"admin_order_{order_id}")])
    
    await callback.message.edit_text(
        "📊 <b>Изменение статуса заказа</b>\n\nВыберите новый статус:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("set_status_"), admin_filter)  
async def set_order_status(callback: CallbackQuery):
    """Установить статус заказа"""
    parts = callback.data.split("_")
    status = parts[2]
    order_id = int(parts[3])
    
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Если заказ отменяется, возвращаем товары на склад только если они были списаны
    if status == 'cancelled' and order.status in ['paid', 'shipping', 'delivered']:
        try:
            import json
            products = order.products_data
            for product in products:
                await db.increase_product_quantity(product['id'], product['quantity'])
        except Exception as e:
            print(f"Error returning products to stock: {e}")
        
        # Уведомляем клиента об отмене
        try:
            await callback.message.bot.send_message(
                order.user_id,
                f"❌ <b>Заказ отменен</b>\n\n"
                f"Заказ #{order.order_number} был отменен администратором.\n"
                f"Если у вас есть вопросы, обратитесь в поддержку.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
                ]),
                parse_mode='HTML'
            )
        except:
            pass
    
    await db.update_order_status(order_id, status)
    
    status_names = {
        'waiting_payment': 'Ожидает оплаты',
        'payment_check': 'Проверка оплаты',
        'paid': 'Оплачен',
        'shipping': 'Отправлен',
        'delivered': 'Доставлен',
        'cancelled': 'Отменен'
    }
    
    # Показываем временное уведомление об изменении статуса
    status_msg = await callback.message.answer(
        f"✅ <b>Статус изменен!</b>\n\n"
        f"📋 Новый статус: {status_names.get(status, status)}\n"
        f"🔄 Уведомление отправлено клиенту",
        parse_mode='HTML'
    )
    
    # Удаляем уведомление через 3 секунды
    import asyncio
    asyncio.create_task(delete_message_after_delay(callback.bot, callback.message.chat.id, status_msg.message_id, 3))
    
    await show_admin_order(callback)

@router.callback_query(F.data.startswith("quick_confirm_"), admin_filter)
async def quick_confirm_payment(callback: CallbackQuery):
    """Быстрое подтверждение платежа"""
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Списываем товары со склада при подтверждении платежа
    try:
        products = order.products_data
        for product in products:
            await db.decrease_product_quantity(product['id'], product['quantity'])
    except Exception as e:
        print(f"Error decreasing stock on quick payment confirmation: {e}")
    
    await db.update_order_status(order_id, 'paid')
    
    try:
        await callback.message.bot.send_message(
            order.user_id,
            f"✅ <b>Оплата подтверждена!</b>\n\n"
            f"Заказ #{order.order_number} принят в обработку.\n"
            f"Готовим ваш заказ к отправке! 📦",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ]),
            parse_mode='HTML'
        )
    except:
        pass
    
    await callback.answer("✅ Платеж подтвержден!", show_alert=True)
    
    await safe_edit_message(
        callback,
        f"✅ <b>Платеж подтвержден</b>\n\n"
        f"Заказ #{order.order_number} - {order.total_price}₾\n"
        f"Статус изменен на: Оплачен",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Управлять заказом", callback_data=f"admin_order_{order_id}")],
            [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_all_orders")]
        ])
    )

@router.callback_query(F.data.startswith("quick_reject_") & ~F.data.startswith("quick_reject_with_reason_"), admin_filter)
async def quick_reject_payment(callback: CallbackQuery):
    """Быстрое отклонение платежа"""
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    await db.update_order_status(order_id, 'waiting_payment')
    # Очищаем скриншот чтобы пользователь мог отправить новый
    await db.update_order_screenshot(order_id, None)
    
    try:
        await callback.message.bot.send_message(
            order.user_id,
            f"❌ <b>Платеж отклонен</b>\n\n"
            f"Заказ #{order.order_number} требует повторной оплаты.\n"
            f"Проверьте правильность реквизитов и повторите попытку.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Отправить скриншот", callback_data=f"resend_screenshot_{order.order_number}")],
                [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_menu")]
            ]),
            parse_mode='HTML'
        )
    except:
        pass
    
    await callback.answer("❌ Платеж отклонен!", show_alert=True)
    
    new_text = (
        f"❌ <b>Платеж отклонен</b>\n\n"
        f"Заказ #{order.order_number} - {order.total_price}₾\n"
        f"Статус изменен на: Ожидает оплаты"
    )
    
    new_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Управлять заказом", callback_data=f"admin_order_{order_id}")],
        [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_all_orders")]
    ])
    
    # Используем безопасную функцию для редактирования сообщения
    await safe_edit_message(callback, new_text, new_markup)

@router.callback_query(F.data.startswith("quick_reject_with_reason_"), admin_filter)
async def quick_reject_with_reason(callback: CallbackQuery, state: FSMContext):
    """Быстрое отклонение платежа с запросом причины"""
    order_id = int(callback.data.split("_")[4])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    user = await db.get_user(order.user_id)
    user_lang = 'ru'
    if user:
        from i18n import i18n
        user_lang = i18n.get_user_language(order.user_id) or 'ru'
    
    await state.update_data(
        order_id=order_id, 
        order_number=order.order_number, 
        user_id=order.user_id,
        total_price=order.total_price,
        user_lang=user_lang
    )
    
    lang_names = {'ru': '🇷🇺 Русский', 'en': '🇺🇸 English', 'ka': '🇬🇪 ქართული'}
    
    text = f"""❌ <b>Отклонение платежа</b>

📋 Заказ #{order.order_number} - {order.total_price}₾
👤 Клиент ID: {order.user_id}
🌐 Язык клиента: {lang_names.get(user_lang, user_lang)}

Напишите причину отклонения платежа:
<i>Клиент получит это сообщение на своем языке</i>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_order_{order_id}")]
    ])
    
    await safe_edit_message(callback, text, keyboard)
    await state.set_state(OrderStates.waiting_rejection_reason)


@router.callback_query(F.data.startswith("quick_message_"), admin_filter)
async def quick_message_client(callback: CallbackQuery, state: FSMContext):
    """Быстрое сообщение клиенту"""
    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    await state.update_data(
        client_id=order.user_id,
        order_number=order.order_number,
        order_id=order_id
    )
    # Используем состояние из communication.py для избежания конфликтов
    from handlers.admin.communication import CommunicationStates
    await state.set_state(CommunicationStates.waiting_client_message)
    
    from i18n import i18n
    user_language = i18n.get_user_language(order.user_id)
    language_names = {'ru': 'Русский', 'ka': 'ქართული', 'en': 'English'}
    
    text = f"""💬 <b>Сообщение клиенту</b>

📋 Заказ #{order.order_number}
👤 Клиент ID: {order.user_id}
🌐 Язык: {language_names.get(user_language, user_language)}

Напишите сообщение клиенту:
<i>Сообщение будет отправлено с оформлением админа</i>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_order_{order_id}")]
    ])
    
    await safe_edit_message(callback, text, keyboard)


@router.callback_query(F.data.startswith("filter_orders_"), admin_filter)
async def filter_orders(callback: CallbackQuery):
    """Фильтрация заказов по статусу"""
    filter_type = callback.data.split("_")[2]
    await show_filtered_orders_page(callback, filter_type, 1)

async def show_filtered_orders_page(callback: CallbackQuery, filter_type: str, page: int):
    """Показать отфильтрованные заказы"""
    from components.pagination import pagination
    
    all_orders = await db.get_all_orders()
    
    # Фильтруем заказы в зависимости от типа
    if filter_type == "pending":
        orders = [order for order in all_orders if order.status == "waiting_payment"]
        title = "⏳ Ожидающие заказы"
    elif filter_type == "checking":
        orders = [order for order in all_orders if order.status == "payment_check"]
        title = "💰 Заказы на проверке"
    elif filter_type == "paid":
        orders = [order for order in all_orders if order.status == "paid"]
        title = "✅ Оплаченные заказы"
    elif filter_type == "shipping":
        orders = [order for order in all_orders if order.status == "shipping"]
        title = "🚚 Заказы в доставке"
    elif filter_type == "delivered":
        orders = [order for order in all_orders if order.status == "delivered"]
        title = "📦 Доставленные заказы"
    elif filter_type == "cancelled":
        orders = [order for order in all_orders if order.status == "cancelled"]
        title = "❌ Отмененные заказы"
    else:
        orders = all_orders
        title = "📋 Все заказы"
    
    if not orders:
        text = f"{title}\n\nЗаказов нет."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_all_orders")],
            [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
        ])
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
        except:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=keyboard, parse_mode='HTML')
        return
    
    pagination.items_per_page = 8
    pagination_info = pagination.paginate(orders, page)
    
    text = f"{title}\n\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"Найдено заказов: <b>{len(orders)}</b>\n"
    text += pagination.get_page_info_text(pagination_info, user_id=callback.from_user.id)
    text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for order in pagination_info['items']:
        status_emoji = "⏳" if order.status == "waiting_payment" else "💰" if order.status == "payment_check" else "✅" if order.status == "paid" else "🚚" if order.status == "shipping" else "📦" if order.status == "delivered" else "❌"
        text += f"{status_emoji} <b>№{order.order_number}</b> - {order.total_price}₾\n"
        text += f"📅 {order.created_at.strftime('%d.%m %H:%M')} | 👤 ID:{order.user_id}\n\n"
    
    def order_button_generator(order, index):
        status_emoji = "⏳" if order.status == "waiting_payment" else "💰" if order.status == "payment_check" else "✅" if order.status == "paid" else "🚚" if order.status == "shipping" else "📦" if order.status == "delivered" else "❌"
        return InlineKeyboardButton(
            text=f"{status_emoji} №{order.order_number} - {order.total_price}₾",
            callback_data=f"admin_order_{order.id}"
        )
    
    additional_buttons = [
        [InlineKeyboardButton(text="📋 Все заказы", callback_data="admin_all_orders")],
        [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
    ]
    
    keyboard = pagination.create_pagination_keyboard(
        pagination_info=pagination_info,
        callback_prefix=f"filter_orders_page_{filter_type}",
        user_id=callback.from_user.id,
        item_button_generator=order_button_generator,
        additional_buttons=additional_buttons
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard, parse_mode='HTML')

@router.callback_query(F.data.startswith("filter_orders_page_"), admin_filter)
async def filter_orders_pagination(callback: CallbackQuery):
    """Пагинация для отфильтрованных заказов"""
    parts = callback.data.split("_")
    filter_type = parts[3]
    page = int(parts[4])
    await show_filtered_orders_page(callback, filter_type, page)

@router.message(OrderStates.waiting_order_search, admin_filter)
async def process_order_search(message: Message, state: FSMContext):
    """Обработка поиска заказа по номеру"""
    order_number = message.text.strip()
    
    try:
        await message.delete()
        
        if not order_number.isdigit():
            await message.bot.send_message(
                chat_id=message.chat.id,
                text="🔍 <b>Ошибка</b>\n\n❌ Номер заказа должен содержать только цифры\n\nВведите правильный номер заказа:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Все заказы", callback_data="admin_all_orders")]
                ]),
                parse_mode='HTML'
            )
            return
        
        order_number_int = int(order_number)
        order = await db.get_order_by_number(order_number_int)
        
        if not order:
            text = f"🔍 <b>Результат поиска</b>\n\n"
            text += f"❌ Заказ №{order_number} не найден\n\n"
            text += f"Попробуйте другой номер заказа:"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Все заказы", callback_data="admin_all_orders")]
            ])
        else:
            await state.clear()
            
            order_items = await db.get_order_items(order.id)
            
            status_emoji = "⏳" if order.status == "waiting_payment" else "💰" if order.status == "payment_check" else "✅" if order.status == "paid" else "🚚" if order.status == "shipping" else "📦" if order.status == "delivered" else "❌"
            
            text = f"🔍 <b>Найден заказ</b>\n\n"
            text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            text += f"{status_emoji} <b>Заказ №{order.order_number}</b>\n"
            text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            text += f"👤 <b>Клиент ID:</b> {order.user_id}\n"
            text += f"📅 <b>Дата:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            text += f"📊 <b>Статус:</b> {order.status}\n"
            text += f"💰 <b>Сумма:</b> {order.total_price}₾\n\n"
            
            if order.phone:
                text += f"📞 <b>Контакт:</b> {order.phone}\n"
            if order.address:
                text += f"📍 <b>Адрес:</b> {order.address}\n"
            
            text += f"\n<b>📦 Товары:</b>\n"
            for item in order_items:
                text += f"• {item.product_name} × {item.quantity} = {item.price * item.quantity}₾\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 Управлять заказом", callback_data=f"admin_order_{order.id}")],
                [InlineKeyboardButton(text="🔙 Все заказы", callback_data="admin_all_orders")]
            ])
        
        await message.bot.send_message(
            chat_id=message.chat.id,
            text=text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        
        if not order:
            return
            
    except Exception as e:
        import traceback
        print(f"❌ ПОЛНАЯ ОШИБКА: {traceback.format_exc()}")
        await state.clear()
        await message.bot.send_message(
            chat_id=message.chat.id,
            text=f"❌ Ошибка при поиске заказа: {str(e)}\n\nПопробуйте еще раз.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Все заказы", callback_data="admin_all_orders")]
            ]),
            parse_mode='HTML'
        )