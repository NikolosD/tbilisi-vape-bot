"""
Базовый класс для всех страниц бота.
Обеспечивает единообразный интерфейс и общую функциональность.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from aiogram.types import InlineKeyboardMarkup, Message, CallbackQuery
from aiogram import Bot

from message_manager import message_manager
from i18n import _


class BasePage(ABC):
    """Базовый класс для всех страниц"""
    
    def __init__(self, page_name: str):
        self.page_name = page_name
        self.menu_state = page_name
    
    @abstractmethod
    async def render(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        Отрендерить страницу
        Возвращает словарь с текстом и клавиатурой
        """
        pass
    
    async def show(self, bot: Bot, user_id: int, **kwargs):
        """Показать страницу пользователю"""
        page_data = await self.render(user_id, **kwargs)
        
        await message_manager.send_or_edit_message(
            bot, user_id,
            page_data.get('text', ''),
            reply_markup=page_data.get('keyboard'),
            menu_state=self.menu_state
        )
    
    async def show_from_message(self, message: Message, **kwargs):
        """Показать страницу из обработчика сообщения"""
        page_data = await self.render(message.from_user.id, **kwargs)
        
        from message_manager import message_manager
        await message_manager.send_or_edit_message(
            message.bot, message.from_user.id,
            page_data.get('text', ''),
            reply_markup=page_data.get('keyboard'),
            menu_state=self.menu_state
        )
    
    async def show_from_callback(self, callback: CallbackQuery, **kwargs):
        """Показать страницу из обработчика callback"""
        page_data = await self.render(callback.from_user.id, **kwargs)
        
        from message_manager import message_manager
        await message_manager.handle_callback_navigation(
            callback,
            page_data.get('text', ''),
            reply_markup=page_data.get('keyboard'),
            menu_state=self.menu_state
        )
    
    def get_title(self, user_id: int) -> str:
        """Получить заголовок страницы"""
        return _(f"{self.page_name}.title", user_id=user_id)
    
    def get_empty_message(self, user_id: int) -> str:
        """Получить сообщение для пустой страницы"""
        return _(f"{self.page_name}.empty", user_id=user_id)