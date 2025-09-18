"""
Text formatting utilities for consistent display across the application
"""

from typing import List, Optional
from i18n import _


def format_product_card(product, quantity_in_cart: int = 0, user_id: Optional[int] = None) -> str:
    """
    Format product information for display
    
    Args:
        product: Product object with name, description, price, in_stock, stock_quantity attributes
        quantity_in_cart: Quantity of this product in user's cart
        user_id: User ID for translations
    
    Returns:
        Formatted product text string
    """
    text = f"🛍️ <b>{product.name}</b>\n\n"
    
    if product.description:
        text += f"{product.description}\n\n"
    
    text += f"💰 <b>{_('product.price', user_id=user_id)}</b> {product.price}₾\n"
    
    # Stock information
    if product.in_stock and product.stock_quantity > 0:
        text += f"📦 <b>{_('product.in_stock', user_id=user_id)}:</b> {product.stock_quantity} {_('product.pieces', user_id=user_id)}\n"
    else:
        text += f"❌ <b>{_('product.out_of_stock', user_id=user_id)}</b>\n"
    
    # Cart information
    if quantity_in_cart > 0:
        text += f"🛒 <b>{_('product.in_cart', user_id=user_id)}:</b> {quantity_in_cart} {_('product.pieces', user_id=user_id)}"
    
    return text


def format_cart_display(cart_items: List, user_id: Optional[int] = None) -> tuple[str, float]:
    """
    Format cart items for display
    
    Args:
        cart_items: List of cart item objects with name, quantity, price attributes
        user_id: User ID for translations
    
    Returns:
        Tuple of (formatted cart text, total price)
    """
    if not cart_items:
        return _('cart.empty', user_id=user_id), 0
    
    cart_text = f"{_('cart.title', user_id=user_id)}\n\n"
    total = 0
    
    for item in cart_items:
        item_total = item.price * item.quantity
        total += item_total
        cart_text += _("cart.item", 
                      name=item.name,
                      quantity=item.quantity, 
                      price=item.price,
                      total=item_total,
                      user_id=user_id)
    
    cart_text += f"\n{_('cart.total', total=total, user_id=user_id)}"
    
    return cart_text, total


def format_order_details(order, order_items: List, user_id: Optional[int] = None) -> str:
    """
    Format order details for display
    
    Args:
        order: Order object with order_number, status, total_price, delivery_address, created_at
        order_items: List of order items
        user_id: User ID for translations
    
    Returns:
        Formatted order details text
    """
    from utils.status import get_status_emoji, get_status_text_key
    
    status_emoji = get_status_emoji(order.status)
    status_text = _(get_status_text_key(order.status), user_id=user_id)
    
    text = f"📦 <b>{_('orders.order', user_id=user_id)} #{order.order_number}</b>\n\n"
    text += f"📅 {_('orders.date', user_id=user_id)}: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    text += f"{status_emoji} {_('orders.status', user_id=user_id)}: <b>{status_text}</b>\n\n"
    
    # Order items
    text += f"<b>{_('orders.items', user_id=user_id)}:</b>\n"
    for item in order_items:
        text += f"• {item.product_name} x{item.quantity} - {item.price * item.quantity}₾\n"
    
    text += f"\n💰 <b>{_('orders.total', user_id=user_id)}: {order.total_price}₾</b>\n"
    
    # Delivery address
    if order.delivery_address:
        text += f"📍 <b>{_('orders.delivery_address', user_id=user_id)}:</b> {order.delivery_address}\n"
    
    return text


def format_product_list_item(product, category_id: Optional[int] = None, user_id: Optional[int] = None) -> str:
    """
    Format product for list display (in category view)
    
    Args:
        product: Product object
        category_id: Category ID for navigation
        user_id: User ID for translations
    
    Returns:
        Formatted product list item text
    """
    if product.stock_quantity > 0:
        return f"{product.name} - {product.price}₾ (📦 {product.stock_quantity} {_('product.pieces', user_id=user_id)})"
    else:
        return f"{product.name} - {product.price}₾ (❌ {_('product.out_of_stock', user_id=user_id)})"