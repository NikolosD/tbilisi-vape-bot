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
        catalog_type = kwargs.get('catalog_type')  # 'brands' или 'flavors'
        flavor_id = kwargs.get('flavor_id')  # ID категории вкуса
        
        if product_id:
            return await self._render_product(user_id, product_id, from_category)
        elif flavor_id:
            return await self._render_flavor_products(user_id, flavor_id)
        elif category_id:
            return await self._render_category(user_id, category_id)
        elif catalog_type == 'brands':
            return await self._render_brands(user_id)
        elif catalog_type == 'flavors':
            return await self._render_flavors(user_id)
        else:
            return await self._render_categories(user_id)
    
    async def _render_categories(self, user_id: int) -> Dict[str, Any]:
        """Отрендерить выбор типа каталога (по вкусам/по брендам)"""
        from keyboards import get_catalog_type_keyboard
        
        text = f"{self.get_title(user_id)}\n\n{_('catalog.choose_type', user_id=user_id)}"
        
        return {
            'text': text,
            'keyboard': get_catalog_type_keyboard(user_id=user_id)
        }
    
    async def _render_brands(self, user_id: int) -> Dict[str, Any]:
        """Отрендерить список брендов (старая логика)"""
        categories = await db.get_categories_with_products()
        
        if not categories:
            from keyboards import get_back_to_menu_keyboard
            return {
                'text': self.get_empty_message(user_id),
                'keyboard': get_back_to_menu_keyboard(user_id=user_id)
            }
        
        text = f"🏷️ {_('catalog.brands_title', user_id=user_id)}\n\n{_('catalog.select_category', user_id=user_id)}"
        
        return {
            'text': text,
            'keyboard': get_categories_keyboard(categories, user_id=user_id)
        }
    
    async def _render_flavors(self, user_id: int) -> Dict[str, Any]:
        """Отрендерить список категорий вкусов"""
        flavor_categories = await db.get_flavor_categories(only_with_products=True)
        
        if not flavor_categories:
            from keyboards import get_back_to_menu_keyboard
            text = f"🍓 {_('catalog.flavors_title', user_id=user_id)}\n\n{_('catalog.flavors_coming_soon', user_id=user_id)}"
            return {
                'text': text,
                'keyboard': get_back_to_menu_keyboard(user_id=user_id)
            }
        
        from keyboards import get_flavor_categories_keyboard
        text = f"🍓 {_('catalog.flavors_title', user_id=user_id)}\n\n{_('catalog.select_flavor', user_id=user_id)}"
        
        return {
            'text': text,
            'keyboard': get_flavor_categories_keyboard(flavor_categories, user_id=user_id)
        }
    
    async def _render_flavor_products(self, user_id: int, flavor_id: int) -> Dict[str, Any]:
        """Отрендерить товары выбранного вкуса"""
        flavor_category = await db.get_flavor_category(flavor_id)
        if not flavor_category:
            return await self._render_flavors(user_id)
        
        products = await db.get_products_by_flavor(flavor_id)
        
        if not products:
            from keyboards import get_flavor_products_keyboard
            text = f"{flavor_category.emoji} <b>{flavor_category.name}</b>\n\n{_('catalog.flavor_empty', user_id=user_id)}"
            return {
                'text': text,
                'keyboard': get_flavor_products_keyboard([], flavor_id, user_id=user_id)
            }
        
        from keyboards import get_flavor_products_keyboard
        text = f"{flavor_category.emoji} <b>{flavor_category.name}</b>\n\n{_('catalog.select_product', user_id=user_id)}"
        
        return {
            'text': text,
            'keyboard': get_flavor_products_keyboard(products, flavor_id, user_id=user_id)
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
        """Отрендерить карточку товара (оптимизированная версия)"""
        # Оптимизированно: получаем товар с уже вычисленным доступным количеством
        product = await db.get_product_with_availability(product_id)
        if not product:
            return await self._render_categories(user_id)
        
        # Оптимизированно: получаем только количество товара в корзине, не всю корзину
        quantity_in_cart = await db.get_product_quantity_in_cart(user_id, product_id)
        
        # Используем быстрый форматтер без дополнительных запросов к БД
        from utils.formatters import format_product_card_fast
        text = format_product_card_fast(product, quantity_in_cart, user_id)
        
        result = {
            'text': text,
            'keyboard': get_product_card_keyboard(product.id, in_cart=(quantity_in_cart > 0), from_category=from_category)
        }
        
        # Добавляем фото если есть
        if product.photo:
            result['photo'] = product.photo
            
        return result