"""
Страница каталога товаров
"""

from typing import Dict, Any, Optional
from .base import BasePage
from database import db
from keyboards import get_categories_keyboard, get_category_products_keyboard, get_product_card_keyboard
from i18n import _


class CatalogPage(BasePage):
    """Страница каталога"""
    
    def __init__(self):
        super().__init__('catalog')
    
    async def render(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Отрендерить каталог"""
        category_id = kwargs.get('category_id')
        product_id = kwargs.get('product_id')
        
        if product_id:
            return await self._render_product(user_id, product_id)
        elif category_id:
            return await self._render_category(user_id, category_id)
        else:
            return await self._render_categories(user_id)
    
    async def _render_categories(self, user_id: int) -> Dict[str, Any]:
        """Отрендерить список категорий"""
        categories = await db.get_categories_with_products()
        
        if not categories:
            from keyboards import get_back_to_menu_keyboard
            return {
                'text': self.get_empty_message(user_id),
                'keyboard': get_back_to_menu_keyboard(user_id=user_id)
            }
        
        text = f"{self.get_title(user_id)}\n\n{_('catalog.select_category', user_id=user_id)}"
        
        return {
            'text': text,
            'keyboard': get_categories_keyboard(categories)
        }
    
    async def _render_category(self, user_id: int, category_id: int) -> Dict[str, Any]:
        """Отрендерить товары категории"""
        category = await db.get_category(category_id)
        if not category:
            return await self._render_categories(user_id)
        
        products = await db.get_products_by_category(category_id)
        
        if not products:
            text = f"📂 <b>{category.name}</b>\n\n{_('catalog.category_empty', user_id=user_id)}"
            return {
                'text': text,
                'keyboard': get_category_products_keyboard([], category_id)
            }
        
        text = f"📂 <b>{category.name}</b>\n\n{_('catalog.select_product', user_id=user_id)}"
        
        return {
            'text': text,
            'keyboard': get_category_products_keyboard(products, category_id)
        }
    
    async def _render_product(self, user_id: int, product_id: int) -> Dict[str, Any]:
        """Отрендерить карточку товара"""
        product = await db.get_product(product_id)
        if not product:
            return await self._render_categories(user_id)
        
        text = f"🛍️ <b>{product.name}</b>\n\n"
        
        if product.description:
            text += f"{product.description}\n\n"
        
        text += f"💰 <b>{_('product.price', user_id=user_id)}</b> {product.price}₾\n"
        
        if product.in_stock:
            text += f"📦 <b>{_('product.in_stock', user_id=user_id)}</b>"
        else:
            text += f"❌ <b>{_('product.out_of_stock', user_id=user_id)}</b>"
        
        return {
            'text': text,
            'keyboard': get_product_card_keyboard(product.id, in_cart=False, from_category=None)
        }