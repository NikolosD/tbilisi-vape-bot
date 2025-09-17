"""
Main user handlers module for the vape shop Telegram bot.

This module serves as the entry point for all user-related handlers.
All specific handler logic has been moved to separate modules in the user package:
- catalog: Product catalog and product management
- cart: Shopping cart management  
- orders: Order creation and management
- profile: User profile and language settings
- menu: Main menu and navigation

The modular structure improves code organization and maintainability.
"""

from aiogram import Router
import logging

# Import all user handler modules  
from handlers.user_modules import setup_user_routers

# Настройка логгера
logger = logging.getLogger(__name__)

# Set up the main router with all user sub-routers
router = setup_user_routers()

# Вспомогательная функция для удаления сообщений с задержкой
async def delete_message_after_delay(bot, chat_id, message_id, delay_seconds):
    """Удалить сообщение через указанное количество секунд"""
    import asyncio
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass  # Игнорируем ошибки если сообщение уже удалено