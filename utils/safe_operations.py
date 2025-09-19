"""
Safe message operations utilities
"""

from typing import Optional, Dict, Any
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest
import logging

logger = logging.getLogger(__name__)

# Track user operations to prevent race conditions
user_operations: Dict[int, bool] = {}


async def safe_edit_message(
    callback: CallbackQuery, 
    text: str, 
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = 'HTML'
) -> bool:
    """
    Safely edit a message, handling both text and photo messages.
    If editing fails, sends a new message as fallback.
    
    Args:
        callback: The callback query to respond to
        text: New text for the message
        reply_markup: Optional inline keyboard
        parse_mode: Parse mode for the text
    
    Returns:
        True if edit was successful, False otherwise
    """
    try:
        if callback.message.photo:
            # For messages with photos, edit caption
            await callback.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            # For text messages, edit text
            await callback.message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        return True
    except TelegramBadRequest as e:
        logger.warning(f"Failed to edit message, sending new one: {e}")
        # Fallback: send a new message
        try:
            await callback.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return True
        except Exception as fallback_e:
            logger.error(f"Failed to send fallback message: {fallback_e}")
            return False
    except Exception as e:
        logger.error(f"Unexpected error editing message: {e}")
        # Fallback: send a new message
        try:
            await callback.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return True
        except Exception as fallback_e:
            logger.error(f"Failed to send fallback message: {fallback_e}")
            return False


async def safe_delete_message(
    bot, 
    chat_id: int, 
    message_id: int
) -> bool:
    """
    Safely delete a message, ignoring errors if already deleted
    
    Args:
        bot: Bot instance
        chat_id: Chat ID
        message_id: Message ID to delete
    
    Returns:
        True if deletion was successful or message already deleted
    """
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception:
        # Message might already be deleted
        return True


async def safe_answer_callback(
    callback: CallbackQuery,
    text: Optional[str] = None,
    show_alert: bool = False
) -> bool:
    """
    Safely answer a callback query
    
    Args:
        callback: The callback query to answer
        text: Optional notification text
        show_alert: Whether to show as alert
    
    Returns:
        True if answer was successful
    """
    try:
        await callback.answer(text=text, show_alert=show_alert)
        return True
    except Exception:
        # Callback might already be answered
        return True


async def with_user_lock(
    user_id: int,
    callback: CallbackQuery,
    operation_func,
    busy_message: str = "⏳ Подождите, операция выполняется..."
) -> Any:
    """
    Execute an operation with user lock to prevent race conditions
    
    Args:
        user_id: User ID to lock
        callback: Callback query for response
        operation_func: Async function to execute
        busy_message: Message to show if operation is already in progress
    
    Returns:
        Result of operation_func or None if locked
    """
    if user_id in user_operations:
        await safe_answer_callback(callback, busy_message, show_alert=False)
        return None
    
    try:
        user_operations[user_id] = True
        return await operation_func()
    finally:
        user_operations.pop(user_id, None)