"""
Модуль для управления страницами бота.
Содержит унифицированную архитектуру для всех страниц интерфейса.
"""

from .base import BasePage
from .catalog import CatalogPage
from .cart import CartPage
from .orders import OrdersPage
from .profile import ProfilePage
from .info import InfoPage

__all__ = [
    'BasePage',
    'CatalogPage', 
    'CartPage',
    'OrdersPage',
    'ProfilePage',
    'InfoPage'
]