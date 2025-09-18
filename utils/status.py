"""
Status utilities for order management
"""

from typing import Union


def get_status_emoji(status: Union[str, object]) -> str:
    """
    Get emoji representation for order status
    
    Args:
        status: Either a string status or an object with a 'value' attribute
    
    Returns:
        Emoji string representing the status
    """
    status_emojis = {
        'waiting_payment': '⏳',
        'payment_check': '💰',
        'paid': '✅',
        'shipping': '🚚',
        'delivered': '📦',
        'cancelled': '❌'
    }
    
    # Handle both string and enum/object status
    if hasattr(status, 'value'):
        status_str = status.value
    else:
        status_str = str(status)
    
    return status_emojis.get(status_str, '❓')


def get_status_text_key(status: Union[str, object]) -> str:
    """
    Get translation key for status text
    
    Args:
        status: Either a string status or an object with a 'value' attribute
    
    Returns:
        Translation key for the status
    """
    # Handle both string and enum/object status
    if hasattr(status, 'value'):
        status_str = status.value
    else:
        status_str = str(status)
    
    return f'status.{status_str}'