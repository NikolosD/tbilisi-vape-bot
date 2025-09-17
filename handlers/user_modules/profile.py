from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from config import ADMIN_IDS, SUPER_ADMIN_ID
from keyboards import get_main_menu_inline
from message_manager import message_manager
from i18n import _
import i18n
from button_filters import is_contact_button, is_language_button
from pages.manager import page_manager

logger = logging.getLogger(__name__)

router = Router()

class ProfileStates(StatesGroup):
    waiting_admin_message = State()

# Обработчики кнопок профиля
@router.message(is_contact_button)
async def show_contact(message: Message):
    """Показать контактную информацию"""
    await page_manager.profile.show_from_message(message, type='contact')

@router.message(is_language_button)
async def show_language_selection(message: Message):
    """Показать выбор языка"""
    await page_manager.profile.show_from_message(message, type='language')

@router.callback_query(F.data == "contact")
async def callback_contact(callback: CallbackQuery):
    """Показать контакт через callback"""
    await page_manager.profile.show_from_callback(callback, type='contact')

@router.callback_query(F.data == "language")
async def callback_language(callback: CallbackQuery):
    """Показать выбор языка через callback"""
    await page_manager.profile.show_from_callback(callback, type='language')

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

# Обработчик для написания сообщения администратору
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
    
    await state.set_state(ProfileStates.waiting_admin_message)

@router.message(ProfileStates.waiting_admin_message, F.text)
async def process_admin_message(message: Message, state: FSMContext):
    """Обработать сообщение для администратора"""
    user_id = message.from_user.id
    
    try:
        # Отправляем сообщение всем админам
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