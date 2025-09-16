"""
Middleware для защиты от спама
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
import logging
import asyncio

from anti_spam import anti_spam

logger = logging.getLogger(__name__)

class AntiSpamMiddleware(BaseMiddleware):
    """Middleware для защиты от спама"""
    
    def __init__(self):
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем пользователя из события
        user = None
        text = ""
        
        if isinstance(event, Message):
            user = event.from_user
            text = event.text or event.caption or ""
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            text = event.data or ""
        
        # Если нет пользователя, пропускаем
        if not user:
            return await handler(event, data)
        
        user_id = user.id
        
        # Проверяем сообщение через систему защиты
        is_allowed, message = anti_spam.process_message(user_id, text)
        
        if not is_allowed:
            # Логируем попытку спама
            logger.warning(f"Заблокировано сообщение от пользователя {user_id} ({user.username}): {message}")
            
            # Отправляем предупреждение пользователю
            if isinstance(event, Message):
                try:
                    # Удаляем спам-сообщение пользователя
                    asyncio.create_task(self._delete_spam_message(event, 1))
                    
                    # Отправляем предупреждение и удаляем его через 7 секунд
                    warning_msg = await event.answer(message)
                    asyncio.create_task(self._delete_warning_after_delay(warning_msg, 7))
                except Exception as e:
                    logger.error(f"Не удалось отправить предупреждение пользователю {user_id}: {e}")
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer(message, show_alert=True)
                except Exception as e:
                    logger.error(f"Не удалось отправить предупреждение пользователю {user_id}: {e}")
            
            # Не передаем управление дальше
            return
        
        # Если все хорошо, продолжаем обработку
        return await handler(event, data)
    
    async def _delete_warning_after_delay(self, message: Message, delay: int):
        """Удалить предупреждающее сообщение через указанную задержку"""
        try:
            await asyncio.sleep(delay)
            await message.delete()
        except Exception as e:
            logger.debug(f"Не удалось удалить предупреждающее сообщение: {e}")
    
    async def _delete_spam_message(self, message: Message, delay: int):
        """Удалить спам-сообщение пользователя через указанную задержку"""
        try:
            await asyncio.sleep(delay)
            await message.delete()
        except Exception as e:
            logger.debug(f"Не удалось удалить спам-сообщение: {e}")

class AdminOnlyMiddleware(BaseMiddleware):
    """Middleware для ограничения доступа только администраторам"""
    
    def __init__(self, admin_ids: list):
        super().__init__()
        self.admin_ids = set(admin_ids)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем пользователя из события
        user = None
        
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        # Если нет пользователя, блокируем
        if not user or user.id not in self.admin_ids:
            if isinstance(event, Message):
                try:
                    await event.answer("🚫 Доступ запрещен. Только для администраторов.")
                except:
                    pass
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer("🚫 Доступ запрещен. Только для администраторов.", show_alert=True)
                except:
                    pass
            return
        
        # Если админ, продолжаем
        return await handler(event, data)