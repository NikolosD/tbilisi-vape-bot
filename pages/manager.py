"""
Менеджер страниц - центральное место для управления всеми страницами
"""

from .catalog import CatalogPage
from .cart import CartPage
from .orders import OrdersPage
from .profile import ProfilePage
from .info import InfoPage


class PageManager:
    """Менеджер страниц"""
    
    def __init__(self):
        self.catalog = CatalogPage()
        self.cart = CartPage()
        self.orders = OrdersPage()
        self.profile = ProfilePage()
        self.info = InfoPage()
    
    def get_page(self, page_name: str):
        """Получить страницу по имени"""
        pages = {
            'catalog': self.catalog,
            'cart': self.cart,
            'orders': self.orders,
            'profile': self.profile,
            'info': self.info
        }
        return pages.get(page_name)


# Глобальный экземпляр менеджера страниц
page_manager = PageManager()