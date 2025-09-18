"""
Страница каталога товаров
"""

from typing import Dict, Any, Optional
from .base import BasePage
from database import db
from keyboards import get_categories_keyboard, get_category_products_keyboard, get_product_card_keyboard, get_category_products_keyboard_with_stock
from i18n import _
from utils.formatters import format_product_card


class CatalogPage(BasePage):
    """Страница каталога"""
    
    def __init__(self):
        super().__init__('catalog')
    
    async def render(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Отрендерить каталог"""
        category_id = kwargs.get('category_id')
        product_id = kwargs.get('product_id')
        from_category = kwargs.get('from_category')
        
        if product_id:
            return await self._render_product(user_id, product_id, from_category)
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
            'keyboard': get_categories_keyboard(categories, user_id=user_id)
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
                'keyboard': await get_category_products_keyboard_with_stock([], category_id, user_id=user_id)
            }
        
        text = f"📂 <b>{category.name}</b>\n\n{_('catalog.select_product', user_id=user_id)}"
        
        return {
            'text': text,
            'keyboard': await get_category_products_keyboard_with_stock(products, category_id, user_id=user_id)
        }
    
    async def _render_product(self, user_id: int, product_id: int, from_category: Optional[int] = None) -> Dict[str, Any]:
        """Отрендерить карточку товара"""
        product = await db.get_product(product_id)
        if not product:
            return await self._render_categories(user_id)
        
        # Получаем информацию о корзине
        cart_items = await db.get_cart(user_id)
        quantity_in_cart = 0
        for item in cart_items:
            if item.product_id == product_id:
                quantity_in_cart = item.quantity
                break
        
        # Используем унифицированный форматтер
        text = await format_product_card(product, quantity_in_cart, user_id)
        
        result = {
            'text': text,
            'keyboard': get_product_card_keyboard(product.id, in_cart=(quantity_in_cart > 0), from_category=from_category)
        }
        
        # Добавляем фото если есть
        if product.photo:
            result['photo'] = product.photo
            
        return result