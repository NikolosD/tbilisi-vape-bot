from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from filters.admin import admin_filter
from i18n import _

router = Router()

class CommunicationStates(StatesGroup):
    waiting_broadcast_message = State()
    waiting_client_message = State()
    waiting_client_id = State()
    waiting_general_client_message = State()

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
    await state.set_state(CommunicationStates.waiting_broadcast_message)

@router.message(CommunicationStates.waiting_broadcast_message, admin_filter)
async def process_broadcast(message: Message, state: FSMContext):
    """Обработка рассылки"""
    broadcast_text = message.text
    
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

@router.callback_query(F.data.startswith("admin_message_client_"), admin_filter)
async def start_message_to_client(callback: CallbackQuery, state: FSMContext):
    """Начать отправку сообщения клиенту"""
    order_id = int(callback.data.split("_")[3])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    await state.update_data(
        client_id=order.user_id,
        order_number=order.order_number,
        order_id=order_id
    )
    await state.set_state(CommunicationStates.waiting_client_message)
    
    from i18n import i18n
    user_language = i18n.get_user_language(order.user_id)
    language_names = {'ru': 'Русский', 'ka': 'ქართული', 'en': 'English'}
    
    admin_language = 'ru'
    
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            _("admin.message_client_form", admin_language).format(
                order_number=order.order_number,
                user_id=order.user_id,
                user_language=language_names.get(user_language, user_language)
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("common.cancel", admin_language), callback_data=f"admin_order_{order_id}")]
            ]),
            parse_mode='HTML'
        )
    except Exception:
        await callback.message.answer(
            _("admin.message_client_form", admin_language).format(
                order_number=order.order_number,
                user_id=order.user_id,
                user_language=language_names.get(user_language, user_language)
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("common.cancel", admin_language), callback_data=f"admin_order_{order_id}")]
            ]),
            parse_mode='HTML'
        )

@router.callback_query(F.data == "admin_message_client", admin_filter)
async def start_general_message_to_client(callback: CallbackQuery, state: FSMContext):
    """Начать отправку сообщения клиенту по ID"""
    admin_language = 'ru'
    
    await callback.answer()
    await callback.message.edit_text(
        _("admin.message_client_id_form", admin_language),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=_("common.cancel", admin_language), callback_data="admin_panel")]
        ]),
        parse_mode='HTML'
    )
    
    await state.set_state(CommunicationStates.waiting_client_id)

@router.message(CommunicationStates.waiting_client_message, admin_filter)
async def process_client_message(message: Message, state: FSMContext):
    """Обработать и отправить сообщение клиенту"""
    data = await state.get_data()
    client_id = data.get('client_id')
    order_number = data.get('order_number')
    order_id = data.get('order_id')
    
    if not client_id:
        admin_language = 'ru'
        await message.answer(_("error.client_id_not_found", admin_language))
        await state.clear()
        return
    
    client_message = (
        f"{_('admin_message.header', user_id=client_id)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{_('admin_message.order_prefix', user_id=client_id)}{order_number}\n\n"
        f"{message.text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>{_('admin_message.footer', user_id=client_id)}</i>"
    )
    
    try:
        await message.bot.send_message(
            client_id,
            client_message,
            parse_mode='HTML'
        )
        
        admin_language = 'ru'
        await message.answer(
            _("admin.message_sent_success", admin_language).format(
                client_id=client_id,
                order_number=order_number
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("common.to_orders", admin_language), callback_data=f"admin_order_{order_id}")],
                [InlineKeyboardButton(text=_("common.to_admin", admin_language), callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
    except Exception as e:
        admin_language = 'ru'
        await message.answer(
            _("admin.message_send_error", admin_language).format(error=str(e)),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("common.to_orders", admin_language), callback_data=f"admin_order_{order_id}")],
                [InlineKeyboardButton(text=_("common.to_admin", admin_language), callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
    
    await state.clear()

@router.message(CommunicationStates.waiting_client_id, admin_filter)
async def process_client_id_input(message: Message, state: FSMContext):
    """Обработать ввод ID клиента"""
    admin_language = 'ru'
    
    try:
        client_id = int(message.text.strip())
        
        user = await db.get_user(client_id)
        if not user:
            await message.answer(
                _("admin.client_not_found", admin_language).format(client_id=client_id),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=_("common.to_admin", admin_language), callback_data="admin_panel")]
                ]),
                parse_mode='HTML'
            )
            await state.clear()
            return
        
        await state.update_data(
            client_id=client_id,
            client_name=user.first_name,
            client_username=user.username
        )
        await state.set_state(CommunicationStates.waiting_general_client_message)
        
        from i18n import i18n
        user_language = i18n.get_user_language(client_id)
        language_names = {'ru': 'Русский', 'ka': 'ქართული', 'en': 'English'}
        
        await message.answer(
            _("admin.general_message_client_form", admin_language).format(
                client_id=client_id,
                client_name=user.first_name,
                client_username=f"@{user.username}" if user.username else "нет",
                user_language=language_names.get(user_language, user_language)
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("common.cancel", admin_language), callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
        
    except ValueError:
        await message.answer(
            _("admin.invalid_client_id", admin_language),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("common.to_admin", admin_language), callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
        await state.clear()

@router.message(CommunicationStates.waiting_general_client_message, admin_filter)
async def process_general_client_message(message: Message, state: FSMContext):
    """Обработать и отправить общее сообщение клиенту"""
    admin_language = 'ru'
    data = await state.get_data()
    client_id = data.get('client_id')
    client_name = data.get('client_name')
    
    if not client_id:
        await message.answer(_("error.client_id_not_found", admin_language))
        await state.clear()
        return
    
    client_message = (
        f"{_('admin_message.header', user_id=client_id)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{message.text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>{_('admin_message.footer', user_id=client_id)}</i>"
    )
    
    try:
        await message.bot.send_message(
            client_id,
            client_message,
            parse_mode='HTML'
        )
        
        await message.answer(
            _("admin.general_message_sent_success", admin_language).format(
                client_id=client_id,
                client_name=client_name
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("admin.message_client", admin_language), callback_data="admin_message_client")],
                [InlineKeyboardButton(text=_("common.to_admin", admin_language), callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
    except Exception as e:
        await message.answer(
            _("admin.general_message_send_error", admin_language).format(
                client_name=client_name,
                error=str(e)
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("admin.message_client", admin_language), callback_data="admin_message_client")],
                [InlineKeyboardButton(text=_("common.to_admin", admin_language), callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
    
    await state.clear()