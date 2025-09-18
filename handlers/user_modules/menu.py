from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging

from config import ADMIN_IDS, SUPER_ADMIN_ID
from keyboards import get_main_menu_inline
from message_manager import message_manager
from i18n import _
from button_filters import is_info_button
from pages.manager import page_manager

logger = logging.getLogger(__name__)

router = Router()

# Обработчики главного меню
@router.message(is_info_button)
async def show_info(message: Message):
    """Показать информацию о магазине"""
    await page_manager.info.show_from_message(message)

@router.callback_query(F.data == "info")
async def callback_info(callback: CallbackQuery):
    """Показать информацию через callback"""
    await page_manager.info.show_from_callback(callback)

@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    """Обработчик для неактивных кнопок"""
    await callback.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    user_id = callback.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    # Очищаем состояние при возврате в главное меню
    await state.clear()
    
    await message_manager.handle_callback_navigation(
        callback,
        _("welcome.title", user_id=user_id) + "\n\n" + _("welcome.description", user_id=user_id),
        reply_markup=get_main_menu_inline(is_admin=is_admin, user_id=user_id),
        menu_state='main',
        hide_reply_keyboard=True
    )

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Вернуться в главное меню"""
    user_id = callback.from_user.id
    await callback.answer()
    
    # Проверяем, является ли пользователь админом
    is_admin = user_id in ADMIN_IDS or user_id == SUPER_ADMIN_ID
    
    try:
        await callback.message.edit_text(
            _("welcome.title", user_id=user_id) + "\n\n" + 
            _("welcome.description", user_id=user_id),
            reply_markup=get_main_menu_inline(is_admin=is_admin, user_id=user_id),
            parse_mode='HTML'
        )
    except Exception:
        # Если не удается отредактировать, отправляем новое сообщение
        await callback.message.delete()
        await callback.message.answer(
            _("welcome.title", user_id=user_id) + "\n\n" + 
            _("welcome.description", user_id=user_id),
            reply_markup=get_main_menu_inline(is_admin=is_admin, user_id=user_id),
            parse_mode='HTML'
        )