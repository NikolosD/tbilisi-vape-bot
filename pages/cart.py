"""
Страница корзины
"""

from typing import Dict, Any
from .base import BasePage
from database import db
from keyboards import get_cart_keyboard
from i18n import _


class CartPage(BasePage):
    """Страница корзины"""
    
    def __init__(self):
        super().__init__('cart')
    
    async def render(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Отрендерить корзину"""
        cart_items = await db.get_cart(user_id)
        
        if not cart_items:
            from keyboards import get_back_to_menu_keyboard
            return {
                'text': f"🛒<b>{self.get_title(user_id)}</b>\n\n{self.get_empty_message(user_id)}",
                'keyboard': get_back_to_menu_keyboard(user_id=user_id),
                'hide_reply_keyboard': True  # Скрываем Reply клавиатуру при пустой корзине
            }
        
        total = sum(item.quantity * item.price for item in cart_items)
        
        text = f"{self.get_title(user_id)}\n\n"
        
        for item in cart_items:
            text += _("cart.item", 
                     name=item.name,
                     quantity=item.quantity, 
                     price=item.price,
                     total=item.price * item.quantity,
                     user_id=user_id)
        
        text += _("cart.total", total=total, user_id=user_id)
        
        # Добавляем информацию о времени резервирования
        expiry_data = await db.get_cart_expiry_time(user_id)
        if expiry_data:
            remaining_minutes = expiry_data['minutes_left']
            if remaining_minutes > 0:
                text += f"\n⏱ Товары зарезервированы на {remaining_minutes} мин"
            else:
                text += f"\n⏱ Резерв истекает..."
        
        return {
            'text': text,
            'keyboard': get_cart_keyboard(cart_items),
            'hide_reply_keyboard': True  # Скрываем Reply клавиатуру при показе корзины
        }