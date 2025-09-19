from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from filters.admin import admin_filter
from i18n import _
from utils.safe_operations import safe_edit_message

router = Router()

def format_broadcast_message(text: str, user_id: int = None) -> str:
    """
    Форматирует сообщение рассылки с красивым оформлением
    """
    # Выбираем заголовок в зависимости от языка пользователя
    from i18n import i18n
    user_lang = i18n.get_user_language(user_id) if user_id else 'ru'
    
    headers = {
        'ru': f"📢 <b>Новости от Tbilisi Vape Shop</b> 📢",
        'ka': f"📢 <b>ახალი ამბები Tbilisi Vape Shop-დან</b> 📢", 
        'en': f"📢 <b>News from Tbilisi Vape Shop</b> 📢"
    }
    
    footers = {
        'ru': f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n💨 <i>Tbilisi Vape Shop</i>\n🛍️ <i>Лучшие цены на вейпы в Тбилиси</i>",
        'ka': f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n💨 <i>Tbilisi Vape Shop</i>\n🛍️ <i>საუკეთესო ფასები ვეიფზე თბილისში</i>",
        'en': f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n💨 <i>Tbilisi Vape Shop</i>\n🛍️ <i>Best vape prices in Tbilisi</i>"
    }
    
    header = headers.get(user_lang, headers['ru'])
    footer = footers.get(user_lang, footers['ru'])
    
    return f"{header}\n\n{text}{footer}"

class CommunicationStates(StatesGroup):
    waiting_broadcast_message = State()
    waiting_broadcast_language = State()
    waiting_client_message = State()
    waiting_client_id = State()
    waiting_general_client_message = State()

async def process_broadcast_logic(message: Message, state: FSMContext):
    """Логика обработки рассылки с красивым форматированием"""
    data = await state.get_data()
    broadcast_mode = data.get('broadcast_mode')
    broadcast_text = message.text
    
    if not broadcast_text:
        await message.answer("❌ Пустое сообщение не может быть отправлено.")
        return
    
    if broadcast_mode == "auto":
        # Многоязычная рассылка
        messages = data.get('messages', {})
        from i18n import i18n
        
        users = await db.fetchall("SELECT user_id, language_code FROM users")
        stats = {"ru": {"sent": 0, "failed": 0},
                 "ka": {"sent": 0, "failed": 0}, 
                 "en": {"sent": 0, "failed": 0}}
        
        status_msg = await message.answer("📢 Отправка многоязычных сообщений...")
        
        for user in users:
            user_id = user[0]
            user_lang = user[1] if len(user) > 1 and user[1] else i18n.get_user_language(user_id)
            
            if user_lang not in messages:
                user_lang = "ru"
            
            # Форматируем сообщение с брендингом
            formatted_message = format_broadcast_message(messages[user_lang], user_id)
            
            try:
                # Добавляем кнопку "Главное меню" к рассылке
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
                ])
                await message.bot.send_message(user_id, formatted_message, parse_mode='HTML', reply_markup=keyboard)
                stats[user_lang]["sent"] += 1
            except:
                stats[user_lang]["failed"] += 1
        
        total_sent = sum(s["sent"] for s in stats.values())
        total_failed = sum(s["failed"] for s in stats.values())
        
        await status_msg.edit_text(
            f"✅ <b>Многоязычная рассылка завершена!</b>\n\n"
            f"📊 <b>Статистика по языкам:</b>\n\n"
            f"🇷🇺 Русский: ✅ {stats['ru']['sent']} | ❌ {stats['ru']['failed']}\n"
            f"🇬🇪 Грузинский: ✅ {stats['ka']['sent']} | ❌ {stats['ka']['failed']}\n"
            f"🇬🇧 Английский: ✅ {stats['en']['sent']} | ❌ {stats['en']['failed']}\n\n"
            f"📤 <b>Всего отправлено:</b> {total_sent}\n"
            f"❌ <b>Не доставлено:</b> {total_failed}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
    else:
        # Одноязычная рассылка
        broadcast_lang = data.get('broadcast_lang')
        users = await db.fetchall("SELECT user_id FROM users WHERE language_code = $1", broadcast_lang)
        
        sent = 0
        failed = 0
        
        status_msg = await message.answer("📢 Отправка сообщений...")
        
        for user in users:
            user_id = user[0]
            # Форматируем с брендингом в зависимости от выбранного языка
            formatted_message = format_broadcast_message(broadcast_text, user_id if broadcast_lang == 'auto' else None)
            # Если конкретный язык, используем его для всех
            if broadcast_lang != 'auto':
                formatted_message = format_broadcast_message(broadcast_text).replace(
                    format_broadcast_message("", None),
                    format_broadcast_message("", user_id).replace(broadcast_text, "")
                ).replace("", broadcast_text)
                # Упрощенный подход - используем язык рассылки
                headers = {
                    'ru': f"📢 <b>Новости от Tbilisi Vape Shop</b> 📢",
                    'ka': f"📢 <b>ახალი ამბები Tbilisi Vape Shop-დან</b> 📢", 
                    'en': f"📢 <b>News from Tbilisi Vape Shop</b> 📢"
                }
                footers = {
                    'ru': f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n💨 <i>Tbilisi Vape Shop</i>\n🛍️ <i>Лучшие цены на вейпы в Тбилиси</i>",
                    'ka': f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n💨 <i>Tbilisi Vape Shop</i>\n🛍️ <i>საუკეთესო ფასები ვეიფზე თბილისში</i>",
                    'en': f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n💨 <i>Tbilisi Vape Shop</i>\n🛍️ <i>Best vape prices in Tbilisi</i>"
                }
                formatted_message = f"{headers[broadcast_lang]}\n\n{broadcast_text}{footers[broadcast_lang]}"
            
            try:
                # Добавляем кнопку "Главное меню" к рассылке
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
                ])
                await message.bot.send_message(user_id, formatted_message, parse_mode='HTML', reply_markup=keyboard)
                sent += 1
            except Exception:
                failed += 1
        
        lang_names = {"ru": "русском", "ka": "грузинском", "en": "английском"}
        
        await status_msg.edit_text(
            f"✅ <b>Рассылка на {lang_names.get(broadcast_lang, broadcast_lang)} языке завершена!</b>\n\n"
            f"📤 Отправлено: {sent}\n"
            f"❌ Не доставлено: {failed}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
    
    await state.clear()

@router.callback_query(F.data == "admin_broadcast", admin_filter)
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку"""
    keyboard = [
        [InlineKeyboardButton(text="📢 Автоматически (по языку пользователя)", callback_data="broadcast_auto")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="broadcast_ru")],
        [InlineKeyboardButton(text="🇬🇪 ქართული", callback_data="broadcast_ka")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="broadcast_en")],
        [InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_panel")]
    ]
    
    await callback.message.edit_text(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Выберите режим рассылки:\n\n"
        "📢 <b>Автоматически</b> - отправит каждому пользователю на его языке\n"
        "(нужно будет ввести 3 версии сообщения)\n\n"
        "Или выберите конкретный язык для отправки всем:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("broadcast_"), admin_filter)
async def select_broadcast_mode(callback: CallbackQuery, state: FSMContext):
    """Выбор режима рассылки"""
    mode = callback.data.split("_")[1]
    
    if mode == "auto":
        await state.update_data(broadcast_mode="auto", messages={})
        await callback.message.edit_text(
            "📢 <b>Многоязычная рассылка</b>\n\n"
            "🇷🇺 <b>Шаг 1/3: Русская версия</b>\n"
            "Введите текст сообщения на русском языке:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
        await state.set_state(CommunicationStates.waiting_broadcast_language)
        await state.update_data(current_lang="ru")
    else:
        print(f"📢 DEBUG: Setting up single language broadcast for {mode}")
        await state.update_data(broadcast_mode="single", broadcast_lang=mode)
        lang_names = {"ru": "русском", "ka": "грузинском", "en": "английском"}
        await callback.message.edit_text(
            f"📢 <b>Рассылка на {lang_names.get(mode, mode)} языке</b>\n\n"
            f"Введите текст сообщения:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
        await state.set_state(CommunicationStates.waiting_broadcast_message)
        print(f"📢 DEBUG: State set to waiting_broadcast_message for user {callback.from_user.id}")

@router.message(CommunicationStates.waiting_broadcast_message, admin_filter)
async def process_single_lang_broadcast(message: Message, state: FSMContext):
    """Обработка одноязычной рассылки"""
    await process_broadcast_logic(message, state)
    await state.clear()

@router.message(CommunicationStates.waiting_broadcast_language, admin_filter)
async def process_multilang_broadcast(message: Message, state: FSMContext):
    """Обработка многоязычной рассылки"""
    data = await state.get_data()
    current_lang = data.get('current_lang')
    messages = data.get('messages', {})
    
    # Сохраняем сообщение для текущего языка
    messages[current_lang] = message.text
    await state.update_data(messages=messages)
    
    # Определяем следующий язык
    next_lang_map = {"ru": "ka", "ka": "en", "en": None}
    next_lang = next_lang_map.get(current_lang)
    
    if next_lang:
        lang_info = {
            "ka": ("🇬🇪 <b>Шаг 2/3: Грузинская версия</b>", "грузинском"),
            "en": ("🇬🇧 <b>Шаг 3/3: Английская версия</b>", "английском")
        }
        title, lang_name = lang_info[next_lang]
        
        await message.answer(
            f"📢 <b>Многоязычная рассылка</b>\n\n"
            f"{title}\n"
            f"Введите текст сообщения на {lang_name} языке:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
            ]),
            parse_mode='HTML'
        )
        await state.update_data(current_lang=next_lang)
    else:
        # Все языки собраны, начинаем рассылку
        await state.update_data(messages=messages)
        await process_broadcast_logic(message, state)


# Debug handler removed - was interfering with main handlers

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
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ]),
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
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ]),
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