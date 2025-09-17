"""
Модели данных для Telegram бота
"""
from typing import NamedTuple, Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


class User(NamedTuple):
    """Модель пользователя"""
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    created_at: datetime
    

class Category(NamedTuple):
    """Модель категории"""
    id: int
    name: str
    emoji: Optional[str]
    

class Product(NamedTuple):
    """Модель продукта"""
    id: int
    name: str
    price: Decimal
    description: Optional[str]
    photo: Optional[str]
    category_id: int
    in_stock: bool
    created_at: datetime
    

class CartItem(NamedTuple):
    """Элемент корзины"""
    product_id: int
    quantity: int
    name: str
    price: Decimal
    photo: Optional[str]
    

class Order(NamedTuple):
    """Модель заказа"""
    id: int
    order_number: int
    user_id: int
    products: str  # JSON строка
    total_price: Decimal
    delivery_zone: str
    delivery_price: Decimal
    phone: str
    address: str
    status: str
    payment_screenshot: Optional[str]
    created_at: datetime
    
    @property
    def products_data(self) -> List[Dict[str, Any]]:
        """Парсированные данные продуктов"""
        import json
        return json.loads(self.products)


class OrderStatus(Enum):
    """Статусы заказов"""
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    WAITING_PAYMENT = 'waiting_payment'
    PAYMENT_CHECK = 'payment_check'
    PAID = 'paid'