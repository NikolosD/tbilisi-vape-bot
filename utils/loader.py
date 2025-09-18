"""
Универсальная компонента лоадера для Telegram бота.
Показывает индикатор загрузки пользователю во время выполнения долгих операций.
"""
import asyncio
import logging
from typing import Optional, Callable, Any, Dict
from aiogram.types import Message, CallbackQuery
from aiogram import Bot
from i18n import _

logger = logging.getLogger(__name__)


class LoaderManager:
    """Менеджер лоадеров для отображения статуса загрузки"""
    
    def __init__(self):
        self._active_loaders: Dict[str, asyncio.Task] = {}
    
    async def show_loader(self, 
                         bot: Bot, 
                         chat_id: int, 
                         message_id: int, 
                         user_id: Optional[int] = None,
                         custom_text: Optional[str] = None) -> str:
        """
        Показать лоадер, заменив текст сообщения
        
        Args:
            bot: Экземпляр бота
            chat_id: ID чата
            message_id: ID сообщения для редактирования
            user_id: ID пользователя для переводов
            custom_text: Кастомный текст лоадера
        
        Returns:
            loader_id: Уникальный ID лоадера для последующей остановки
        """
        loader_id = f"{chat_id}_{message_id}"
        
        # Получаем текст лоадера
        if custom_text:
            loader_text = custom_text
        else:
            loader_text = _("common.loading", user_id=user_id)
        
        # Создаем задачу анимации лоадера
        task = asyncio.create_task(
            self._animate_loader(bot, chat_id, message_id, loader_text)
        )
        
        # Сохраняем задачу
        self._active_loaders[loader_id] = task
        
        logger.info(f"✨ Лоадер запущен: {loader_id}")
        return loader_id
    
    async def hide_loader(self, 
                         loader_id: str, 
                         bot: Bot, 
                         chat_id: int, 
                         message_id: int, 
                         final_text: str,
                         reply_markup=None) -> bool:
        """
        Скрыть лоадер и показать финальный текст
        
        Args:
            loader_id: ID лоадера для остановки
            bot: Экземпляр бота
            chat_id: ID чата
            message_id: ID сообщения
            final_text: Финальный текст для отображения
            reply_markup: Клавиатура для финального сообщения
        
        Returns:
            bool: True если лоадер был остановлен успешно
        """
        task = self._active_loaders.get(loader_id)
        if not task:
            logger.warning(f"⚠️ Лоадер {loader_id} не найден")
            return False
        
        # Останавливаем анимацию
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Удаляем из активных лоадеров
        del self._active_loaders[loader_id]
        
        # Показываем финальный текст
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=final_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            logger.info(f"✅ Лоадер {loader_id} остановлен и заменен финальным текстом")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при скрытии лоадера {loader_id}: {e}")
            return False
    
    async def _animate_loader(self, bot: Bot, chat_id: int, message_id: int, base_text: str):
        """
        Анимация лоадера с вращающимися точками
        
        Args:
            bot: Экземпляр бота
            chat_id: ID чата
            message_id: ID сообщения
            base_text: Базовый текст лоадера
        """
        animations = ["⏳", "⏳.", "⏳..", "⏳..."]
        counter = 0
        
        try:
            while True:
                animation = animations[counter % len(animations)]
                full_text = f"{animation} {base_text}"
                
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=full_text,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    # Игнорируем ошибки редактирования сообщения
                    logger.debug(f"Ошибка анимации лоадера: {e}")
                
                counter += 1
                await asyncio.sleep(0.5)  # Интервал анимации
                
        except asyncio.CancelledError:
            # Лоадер отменен - это нормально
            logger.debug(f"Анимация лоадера {chat_id}_{message_id} отменена")
            raise
        except Exception as e:
            logger.error(f"Ошибка в анимации лоадера: {e}")


# Глобальный экземпляр менеджера лоадеров
loader_manager = LoaderManager()


async def with_loader(operation: Callable, 
                     bot: Bot, 
                     chat_id: int, 
                     message_id: int,
                     user_id: Optional[int] = None,
                     loader_text: Optional[str] = None,
                     success_text: Optional[str] = None,
                     error_text: Optional[str] = None,
                     final_markup=None) -> Any:
    """
    Выполнить операцию с показом лоадера
    
    Args:
        operation: Асинхронная функция для выполнения
        bot: Экземпляр бота
        chat_id: ID чата
        message_id: ID сообщения
        user_id: ID пользователя для переводов
        loader_text: Кастомный текст лоадера
        success_text: Текст при успешном выполнении
        error_text: Текст при ошибке
        final_markup: Клавиатура для финального сообщения
    
    Returns:
        Результат выполнения операции
    """
    # Показываем лоадер
    loader_id = await loader_manager.show_loader(
        bot, chat_id, message_id, user_id, loader_text
    )
    
    try:
        # Выполняем операцию
        result = await operation()
        
        # Определяем финальный текст
        if success_text:
            final_text = success_text
        elif hasattr(result, 'get') and result.get('text'):
            final_text = result['text']
            final_markup = result.get('keyboard', final_markup)
        else:
            final_text = _("common.success", user_id=user_id)
        
        # Скрываем лоадер
        await loader_manager.hide_loader(
            loader_id, bot, chat_id, message_id, final_text, final_markup
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка выполнения операции с лоадером: {e}")
        
        # Показываем ошибку
        error_message = error_text or _("common.error", user_id=user_id)
        await loader_manager.hide_loader(
            loader_id, bot, chat_id, message_id, error_message
        )
        
        raise


# Вспомогательные функции для простого использования
async def show_simple_loader(callback: CallbackQuery, 
                           user_id: Optional[int] = None,
                           custom_text: Optional[str] = None) -> str:
    """Простая функция для показа лоадера из callback"""
    return await loader_manager.show_loader(
        callback.bot, 
        callback.message.chat.id, 
        callback.message.message_id,
        user_id,
        custom_text
    )


async def hide_simple_loader(loader_id: str,
                           callback: CallbackQuery,
                           final_text: str,
                           reply_markup=None) -> bool:
    """Простая функция для скрытия лоадера из callback"""
    return await loader_manager.hide_loader(
        loader_id,
        callback.bot,
        callback.message.chat.id,
        callback.message.message_id,
        final_text,
        reply_markup
    )