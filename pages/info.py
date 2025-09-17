"""
Страница информации о магазине
"""

from typing import Dict, Any
from .base import BasePage
from config import MIN_ORDER_AMOUNT
from i18n import _


class InfoPage(BasePage):
    """Страница информации о магазине"""
    
    def __init__(self):
        super().__init__('info')
    
    async def render(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Отрендерить информацию о магазине"""
        
        info_text = f"""ℹ️ <b>{_('info.title', user_id=user_id)}</b>

🏪 <b>Tbilisi VAPE Shop</b>
🇬🇪 {_('info.description', user_id=user_id)}

✅ <b>{_('info.advantages', user_id=user_id)}</b>
• {_('info.advantage_1', user_id=user_id)}
• {_('info.advantage_2', user_id=user_id)}
• {_('info.advantage_3', user_id=user_id)}
• {_('info.advantage_4', user_id=user_id)}
• {_('info.advantage_5', user_id=user_id)}

🚚 <b>{_('info.delivery', user_id=user_id)}</b>
• {_('info.delivery_center', user_id=user_id)}
• {_('info.delivery_saburtalo', user_id=user_id)}
• {_('info.delivery_vake', user_id=user_id)}
• {_('info.delivery_isani', user_id=user_id)}
• {_('info.delivery_other', user_id=user_id)}

💳 <b>{_('info.payment', user_id=user_id)}</b>
• {_('info.payment_card', user_id=user_id)}
• {_('info.payment_sbp', user_id=user_id)}
• {_('info.payment_cash', user_id=user_id)}

📦 <b>{_('info.min_order', user_id=user_id)}</b> {MIN_ORDER_AMOUNT}₾

🔒 <b>{_('info.security', user_id=user_id)}</b>
{_('info.security_description', user_id=user_id)}"""

        from keyboards import get_back_to_menu_keyboard
        return {
            'text': info_text,
            'keyboard': get_back_to_menu_keyboard(user_id=user_id)
        }