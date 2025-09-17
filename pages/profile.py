"""
Страница профиля пользователя
"""

from typing import Dict, Any
from .base import BasePage
from database import db
from keyboards import get_language_keyboard, get_contact_keyboard
from i18n import _


class ProfilePage(BasePage):
    """Страница профиля"""
    
    def __init__(self):
        super().__init__('profile')
    
    async def render(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Отрендерить профиль"""
        page_type = kwargs.get('type', 'main')
        
        if page_type == 'language':
            return await self._render_language_settings(user_id)
        elif page_type == 'contact':
            return await self._render_contact_page(user_id)
        else:
            return await self._render_main_profile(user_id)
    
    async def _render_main_profile(self, user_id: int) -> Dict[str, Any]:
        """Отрендерить главную страницу профиля"""
        user = await db.get_user(user_id)
        if not user:
            return {
                'text': _('profile.error', user_id=user_id),
                'keyboard': None
            }
        
        text = f"👤 <b>{self.get_title(user_id)}</b>\n\n"
        text += f"🆔 <b>ID:</b> {user.user_id}\n"
        
        if user.username:
            text += f"👤 <b>{_('profile.username', user_id=user_id)}</b> @{user.username}\n"
        
        text += f"🌐 <b>{_('profile.language', user_id=user_id)}</b> {user.language}\n"
        text += f"📅 <b>{_('profile.registered', user_id=user_id)}</b> {user.created_at.strftime('%d.%m.%Y')}\n"
        
        # Статистика заказов
        orders_count = await db.get_user_orders_count(user_id)
        text += f"📋 <b>{_('profile.orders_count', user_id=user_id)}</b> {orders_count}\n"
        
        return {
            'text': text,
            'keyboard': None  # Добавить клавиатуру настроек профиля
        }
    
    async def _render_language_settings(self, user_id: int) -> Dict[str, Any]:
        """Отрендерить настройки языка"""
        text = f"🌐 <b>{_('language.title', user_id=user_id)}</b>\n\n"
        text += _('language.select', user_id=user_id)
        
        from keyboards import get_language_keyboard
        return {
            'text': text,
            'keyboard': get_language_keyboard(user_id=user_id)
        }
    
    async def _render_contact_page(self, user_id: int) -> Dict[str, Any]:
        """Отрендерить страницу контактов"""
        text = f"{_('contact.title', user_id=user_id)}\n\n"
        text += _('contact.description', user_id=user_id)
        
        from keyboards import get_contact_keyboard_with_message
        return {
            'text': text,
            'keyboard': get_contact_keyboard_with_message(user_id=user_id)
        }