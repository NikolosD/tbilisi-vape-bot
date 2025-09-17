"""
Страница заказов пользователя
"""

from typing import Dict, Any, Optional
from .base import BasePage
from database import db
from keyboards import get_orders_keyboard, get_order_details_keyboard
from models import OrderStatus
from components.pagination import pagination
from aiogram.types import InlineKeyboardButton
from i18n import _


class OrdersPage(BasePage):
    """Страница заказов"""
    
    def __init__(self):
        super().__init__('orders')
    
    async def render(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Отрендерить страницу заказов"""
        order_id = kwargs.get('order_id')
        page = kwargs.get('page', 1)
        
        if order_id:
            return await self._render_order_details(user_id, order_id)
        else:
            return await self._render_orders_list(user_id, page)
    
    async def _render_orders_list(self, user_id: int, page: int = 1) -> Dict[str, Any]:
        """Отрендерить список заказов с пагинацией"""
        orders = await db.get_user_orders(user_id)
        
        if not orders:
            from keyboards import get_back_to_menu_keyboard
            return {
                'text': f"📋 <b>{self.get_title(user_id)}</b>\n\n{self.get_empty_message(user_id)}",
                'keyboard': get_back_to_menu_keyboard(user_id=user_id)
            }
        
        # Используем компонент пагинации
        pagination_info = pagination.paginate(orders, page)
        
        text = f"📋 <b>{self.get_title(user_id)}</b>\n\n"
        
        # Добавляем информацию о странице
        text += pagination.get_page_info_text(pagination_info, user_id)
        
        # Отображаем заказы текущей страницы
        for order in pagination_info['items']:
            status_emoji = self._get_status_emoji(order.status)
            status_text = self._get_status_text(order.status, user_id)
            
            text += f"{status_emoji} <b>{_('orders.order', user_id=user_id)} №{order.order_number}</b>\n"
            text += f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            text += f"💰 {order.total_price}₾\n"
            text += f"📊 {status_text}\n\n"
        
        # Создаем клавиатуру с пагинацией
        def order_button_generator(order, index):
            return InlineKeyboardButton(
                text=f"📋 №{order.order_number} - {order.total_price}₾",
                callback_data=f"order_{order.id}"
            )
        
        additional_buttons = [[
            InlineKeyboardButton(
                text=_("common.main_menu", user_id=user_id),
                callback_data="back_to_menu"
            )
        ]]
        
        keyboard = pagination.create_pagination_keyboard(
            pagination_info=pagination_info,
            callback_prefix="orders_page",
            user_id=user_id,
            item_button_generator=order_button_generator,
            additional_buttons=additional_buttons
        )
        
        return {
            'text': text,
            'keyboard': keyboard
        }
    
    async def _render_order_details(self, user_id: int, order_id: int) -> Dict[str, Any]:
        """Отрендерить детали заказа"""
        order = await db.get_order(order_id)
        if not order or order.user_id != user_id:
            return await self._render_orders_list(user_id)
        
        order_items = await db.get_order_items(order_id)
        
        status_emoji = self._get_status_emoji(order.status)
        status_text = self._get_status_text(order.status, user_id)
        
        text = f"{status_emoji} <b>{_('orders.order', user_id=user_id)} №{order.order_number}</b>\n\n"
        text += f"📅 <b>{_('orders.created', user_id=user_id)}</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"📊 <b>{_('orders.status', user_id=user_id)}</b> {status_text}\n\n"
        
        if order.contact:
            text += f"📞 <b>{_('orders.contact', user_id=user_id)}</b> {order.contact}\n"
        if order.address:
            text += f"📍 <b>{_('orders.address', user_id=user_id)}</b> {order.address}\n"
        
        text += f"\n<b>{_('orders.items', user_id=user_id)}</b>\n"
        for item in order_items:
            text += f"• {item.product_name} × {item.quantity} = {item.price * item.quantity}₾\n"
        
        text += f"\n💰 <b>{_('orders.total', user_id=user_id)}</b> {order.total_price}₾"
        
        if order.admin_comment:
            text += f"\n\n💬 <b>{_('orders.admin_comment', user_id=user_id)}</b>\n{order.admin_comment}"
        
        return {
            'text': text,
            'keyboard': get_order_details_keyboard(order)
        }
    
    def _get_status_emoji(self, status) -> str:
        """Получить эмодзи для статуса заказа"""
        # Преобразуем status в строку для сопоставления
        if hasattr(status, 'value'):
            status_str = status.value
        else:
            status_str = status
            
        status_emojis = {
            "waiting_payment": "⏳",
            "payment_check": "💰",
            "paid": "✅",
            "shipping": "🚚",
            "delivered": "📦",
            "cancelled": "❌"
        }
        return status_emojis.get(status_str, "❓")
    
    def _get_status_text(self, status, user_id: int) -> str:
        """Получить текст статуса заказа"""
        # status может быть как строкой, так и enum, обрабатываем оба случая
        if hasattr(status, 'value'):
            status_value = status.value
        else:
            status_value = status
        return _(f"orders.status_{status_value}", user_id=user_id)