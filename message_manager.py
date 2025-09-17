"""
Менеджер сообщений для предотвращения накопления старых сообщений
"""
import logging
from typing import Dict, Optional, List
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

class MessageManager:
    """Управляет сообщениями пользователей для предотвращения накопления"""
    
    def __init__(self):
        # Словарь для хранения ID последних сообщений пользователей
        # user_id -> {'last_message_id': int, 'menu_state': str}
        self.user_messages: Dict[int, Dict] = {}
        
    def set_user_message(self, user_id: int, message_id: int, menu_state: str = 'main'):
        """Сохранить ID последнего сообщения пользователя"""
        self.user_messages[user_id] = {
            'last_message_id': message_id,
            'menu_state': menu_state
        }
        logger.debug(f"Сохранено сообщение {message_id} для пользователя {user_id}, состояние: {menu_state}")
    
    def get_user_message(self, user_id: int) -> Optional[Dict]:
        """Получить информацию о последнем сообщении пользователя"""
        return self.user_messages.get(user_id)
    
    def clear_user_message(self, user_id: int):
        """Очистить информацию о сообщениях пользователя"""
        if user_id in self.user_messages:
            del self.user_messages[user_id]
            logger.debug(f"Очищена информация о сообщениях пользователя {user_id}")
    
    async def delete_user_message(self, bot: Bot, user_id: int) -> bool:
        """Удалить последнее сообщение пользователя"""
        user_info = self.get_user_message(user_id)
        if not user_info:
            return False
            
        try:
            await bot.delete_message(user_id, user_info['last_message_id'])
            logger.debug(f"Удалено сообщение {user_info['last_message_id']} пользователя {user_id}")
            self.clear_user_message(user_id)
            return True
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось удалить сообщение {user_info['last_message_id']} пользователя {user_id}: {e}")
            return False
    
    async def send_or_edit_message(
        self, 
        bot: Bot, 
        user_id: int, 
        text: str, 
        reply_markup=None, 
        parse_mode: str = 'HTML',
        menu_state: str = 'main',
        force_new: bool = False,
        send_reply_keyboard: bool = True
    ) -> Message:
        """
        Отправить новое сообщение или отредактировать существующее
        
        Args:
            bot: Экземпляр бота
            user_id: ID пользователя
            text: Текст сообщения
            reply_markup: Клавиатура
            parse_mode: Режим парсинга
            menu_state: Состояние меню
            force_new: Принудительно создать новое сообщение
        """
        user_info = self.get_user_message(user_id)
        
        # Если принудительно создаем новое или нет предыдущего сообщения
        if force_new or not user_info:
            # Удаляем предыдущее сообщение если есть
            if user_info and not force_new:
                await self.delete_user_message(bot, user_id)
            
            # Получаем нижнюю клавиатуру если нужно
            keyboard_markup = None
            if send_reply_keyboard:
                keyboard_markup = await self._get_reply_keyboard(user_id)
            
            # Отправляем новое сообщение
            message = await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=reply_markup or keyboard_markup,
                parse_mode=parse_mode
            )
            self.set_user_message(user_id, message.message_id, menu_state)
            logger.debug(f"Отправлено новое сообщение {message.message_id} пользователю {user_id}")
            return message
        
        # Пытаемся отредактировать существующее сообщение
        try:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=user_info['last_message_id'],
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            # Обновляем состояние меню
            user_info['menu_state'] = menu_state
            
            
            logger.debug(f"Отредактировано сообщение {user_info['last_message_id']} пользователя {user_id}")
            return None  # Возвращаем None для отредактированного сообщения
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось отредактировать сообщение пользователя {user_id}: {e}")
            
            # Если не удалось отредактировать, удаляем старое и создаем новое
            await self.delete_user_message(bot, user_id)
            
            # Получаем нижнюю клавиатуру если нужно
            keyboard_markup = None
            if send_reply_keyboard:
                keyboard_markup = await self._get_reply_keyboard(user_id)
            
            message = await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=reply_markup or keyboard_markup,
                parse_mode=parse_mode
            )
            self.set_user_message(user_id, message.message_id, menu_state)
            logger.debug(f"Создано новое сообщение {message.message_id} после неудачного редактирования для пользователя {user_id}")
            return message
    
    async def handle_callback_navigation(
        self, 
        callback: CallbackQuery, 
        text: str, 
        reply_markup=None, 
        parse_mode: str = 'HTML',
        menu_state: str = 'main',
        send_reply_keyboard: bool = True
    ):
        """
        Обработать навигацию через callback с автоматическим редактированием
        
        Args:
            callback: CallbackQuery объект
            text: Новый текст сообщения
            reply_markup: Новая клавиатура
            parse_mode: Режим парсинга
            menu_state: Новое состояние меню
            send_reply_keyboard: Отправлять ли нижнюю клавиатуру при создании нового сообщения
        """
        user_id = callback.from_user.id
        
        # Всегда удаляем старое и создаем новое сообщение для сохранения нижней клавиатуры
        try:
            await callback.message.delete()
        except:
            pass
        
        # Получаем нижнюю клавиатуру если нужно
        keyboard_markup = None
        if send_reply_keyboard:
            keyboard_markup = await self._get_reply_keyboard(user_id)
            
        message = await callback.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup or keyboard_markup,
            parse_mode=parse_mode
        )
        self.set_user_message(user_id, message.message_id, menu_state)
        logger.debug(f"Callback навигация: создано новое сообщение {message.message_id} с нижней клавиатурой")
    
    def get_user_menu_state(self, user_id: int) -> str:
        """Получить текущее состояние меню пользователя"""
        user_info = self.get_user_message(user_id)
        return user_info.get('menu_state', 'main') if user_info else 'main'
    
    def is_menu_state_changed(self, user_id: int, new_state: str) -> bool:
        """Проверить, изменилось ли состояние меню"""
        current_state = self.get_user_menu_state(user_id)
        return current_state != new_state
    
    async def clear_on_state_change(self, bot: Bot, user_id: int, new_state: str):
        """Очистить сообщения при смене состояния меню"""
        if self.is_menu_state_changed(user_id, new_state):
            await self.delete_user_message(bot, user_id)
            logger.debug(f"Очищены сообщения пользователя {user_id} при смене состояния на {new_state}")
    
    async def _get_reply_keyboard(self, user_id: int):
        """Получить нижнюю клавиатуру для пользователя"""
        try:
            from keyboards import get_main_menu
            from config import ADMIN_IDS
            
            is_admin = user_id in ADMIN_IDS
            return get_main_menu(is_admin=is_admin, user_id=user_id)
        except Exception as e:
            logger.warning(f"Не удалось получить клавиатуру для пользователя {user_id}: {e}")
            return None
    
    async def ensure_reply_keyboard(self, bot: Bot, user_id: int):
        """Убедиться что у пользователя есть нижняя клавиатура навигации"""
        # Эта функция временно отключена из-за эффекта мигания
        # Клавиатура будет отправляться вместе с основными сообщениями
        pass

# Глобальный экземпляр менеджера сообщений
message_manager = MessageManager()