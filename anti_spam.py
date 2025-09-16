"""
Система защиты от спама и DDoS для Telegram бота
"""
import time
import asyncio
from typing import Dict, List, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Импортируем монитор безопасности
try:
    from security_monitor import security_monitor
    MONITORING_ENABLED = True
except ImportError:
    MONITORING_ENABLED = False
    security_monitor = None

@dataclass
class UserStats:
    """Статистика пользователя для анти-спам системы"""
    message_count: int = 0
    last_message_time: float = 0
    blocked_until: float = 0
    warning_count: int = 0
    spam_score: int = 0
    recent_messages: List[float] = field(default_factory=list)

class AntiSpamSystem:
    """Система защиты от спама"""
    
    def __init__(self):
        self.user_stats: Dict[int, UserStats] = defaultdict(UserStats)
        self.blocked_users: Set[int] = set()
        self.admin_ids: Set[int] = set()
        
        # Настройки лимитов
        self.MAX_MESSAGES_PER_MINUTE = 50  # Максимум сообщений в минуту (увеличено в 5 раз)
        self.MAX_MESSAGES_PER_HOUR = 300   # Максимум сообщений в час (увеличено в 5 раз)
        self.MIN_MESSAGE_INTERVAL = 0.2    # Минимальный интервал между сообщениями (уменьшено в 5 раз)
        self.SPAM_THRESHOLD = 250          # Порог блокировки за спам (увеличено в 5 раз)
        self.BLOCK_DURATION = 300          # Время блокировки (5 минут)
        self.WARNING_THRESHOLD = 15        # Количество предупреждений до блокировки (увеличено в 5 раз)
        
        # Паттерны спама
        self.SPAM_PATTERNS = [
            "реклама", "spam", "casino", "bitcoin", "crypto", "заработок",
            "бесплатно", "скидка", "акция", "промокод", "wwww", "http",
            "telegram.me", "t.me", "@", "канал", "подписка"
        ]
        
    def set_admin_ids(self, admin_ids: List[int]):
        """Установить ID администраторов (они не блокируются)"""
        self.admin_ids = set(admin_ids)
        if MONITORING_ENABLED:
            security_monitor.set_admin_ids(admin_ids)
    
    def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь админом"""
        return user_id in self.admin_ids
    
    def is_blocked(self, user_id: int) -> bool:
        """Проверить, заблокирован ли пользователь"""
        if self.is_admin(user_id):
            return False
            
        stats = self.user_stats[user_id]
        current_time = time.time()
        
        # Проверяем временную блокировку
        if stats.blocked_until > current_time:
            return True
            
        # Снимаем блокировку если время истекло
        if stats.blocked_until > 0 and stats.blocked_until <= current_time:
            stats.blocked_until = 0
            stats.spam_score = max(0, stats.spam_score - 10)  # Снижаем спам-счет
            logger.info(f"Пользователь {user_id} разблокирован")
            
        return user_id in self.blocked_users
    
    def check_rate_limit(self, user_id: int) -> tuple[bool, str]:
        """Проверить лимиты частоты сообщений"""
        if self.is_admin(user_id):
            return True, ""
            
        stats = self.user_stats[user_id]
        current_time = time.time()
        
        # Очищаем старые сообщения (старше часа)
        stats.recent_messages = [
            msg_time for msg_time in stats.recent_messages 
            if current_time - msg_time < 3600
        ]
        
        # Проверяем минимальный интервал
        if (current_time - stats.last_message_time) < self.MIN_MESSAGE_INTERVAL:
            stats.spam_score += 5
            return False, f"⚠️ Слишком быстро! Подождите {self.MIN_MESSAGE_INTERVAL} секунд между сообщениями."
        
        # Проверяем лимит в минуту
        recent_minute = [
            msg_time for msg_time in stats.recent_messages 
            if current_time - msg_time < 60
        ]
        if len(recent_minute) >= self.MAX_MESSAGES_PER_MINUTE:
            stats.spam_score += 10
            return False, f"⚠️ Превышен лимит сообщений в минуту ({self.MAX_MESSAGES_PER_MINUTE}). Подождите немного."
        
        # Проверяем лимит в час
        if len(stats.recent_messages) >= self.MAX_MESSAGES_PER_HOUR:
            stats.spam_score += 15
            return False, f"⚠️ Превышен лимит сообщений в час ({self.MAX_MESSAGES_PER_HOUR}). Попробуйте позже."
        
        return True, ""
    
    def check_spam_content(self, text: str) -> tuple[bool, str]:
        """Проверить содержимое на спам"""
        if not text:
            return True, ""
            
        text_lower = text.lower()
        spam_words_found = []
        
        for pattern in self.SPAM_PATTERNS:
            if pattern in text_lower:
                spam_words_found.append(pattern)
        
        # Проверяем на повторяющиеся символы (aaaaaaa, wwwwww)
        for char in text_lower:
            if char.isalpha() and text_lower.count(char) > 7:
                spam_words_found.append("повторяющиеся символы")
                break
        
        # Проверяем на большое количество эмодзи
        emoji_count = sum(1 for char in text if ord(char) > 0x1F000)
        if emoji_count > 10:
            spam_words_found.append("много эмодзи")
        
        if spam_words_found:
            return False, f"⚠️ Сообщение содержит признаки спама: {', '.join(spam_words_found[:3])}"
        
        return True, ""
    
    def process_message(self, user_id: int, text: str = "") -> tuple[bool, str]:
        """Обработать сообщение пользователя"""
        if self.is_admin(user_id):
            return True, ""
            
        # Проверяем блокировку
        if self.is_blocked(user_id):
            stats = self.user_stats[user_id]
            if stats.blocked_until > time.time():
                remaining = int(stats.blocked_until - time.time())
                return False, f"🚫 Вы заблокированы на {remaining} секунд за спам."
            else:
                return False, "🚫 Вы заблокированы за спам. Обратитесь к администратору."
        
        # Проверяем лимиты частоты
        rate_ok, rate_msg = self.check_rate_limit(user_id)
        if not rate_ok:
            self._apply_penalty(user_id, rate_msg)
            return False, rate_msg
        
        # Проверяем содержимое на спам
        content_ok, content_msg = self.check_spam_content(text)
        if not content_ok:
            stats = self.user_stats[user_id]
            stats.spam_score += 20
            self._apply_penalty(user_id, content_msg)
            return False, content_msg
        
        # Записываем успешное сообщение
        self._record_message(user_id)
        return True, ""
    
    def _record_message(self, user_id: int):
        """Записать успешное сообщение"""
        stats = self.user_stats[user_id]
        current_time = time.time()
        
        stats.message_count += 1
        stats.last_message_time = current_time
        stats.recent_messages.append(current_time)
        
        # Записываем в монитор безопасности
        if MONITORING_ENABLED:
            security_monitor.log_message(user_id)
        
        # Постепенно снижаем спам-счет за хорошее поведение
        if stats.spam_score > 0 and current_time - stats.last_message_time > 60:
            stats.spam_score = max(0, stats.spam_score - 1)
    
    def _apply_penalty(self, user_id: int, reason: str):
        """Применить наказание за нарушение"""
        stats = self.user_stats[user_id]
        
        logger.warning(f"Применяется наказание для пользователя {user_id}: {reason}")
        
        # Увеличиваем счетчик предупреждений
        stats.warning_count += 1
        
        # Записываем в монитор безопасности
        if MONITORING_ENABLED:
            security_monitor.log_event(
                "USER_WARNING",
                user_id,
                reason,
                "medium"
            )
        
        # Блокируем если превышен порог спама
        if stats.spam_score >= self.SPAM_THRESHOLD:
            self.block_user(user_id, self.BLOCK_DURATION, f"Превышен лимит спама (счет: {stats.spam_score})")
        
        # Блокируем если много предупреждений
        elif stats.warning_count >= self.WARNING_THRESHOLD:
            self.block_user(user_id, self.BLOCK_DURATION, f"Много предупреждений ({stats.warning_count})")
    
    def block_user(self, user_id: int, duration: int = 0, reason: str = ""):
        """Заблокировать пользователя"""
        if self.is_admin(user_id):
            return
            
        stats = self.user_stats[user_id]
        current_time = time.time()
        
        if duration > 0:
            stats.blocked_until = current_time + duration
            logger.warning(f"Пользователь {user_id} заблокирован на {duration} секунд. Причина: {reason}")
            
            # Записываем в монитор безопасности
            if MONITORING_ENABLED:
                security_monitor.log_user_blocked(user_id, reason, duration)
        else:
            self.blocked_users.add(user_id)
            logger.warning(f"Пользователь {user_id} заблокирован навсегда. Причина: {reason}")
            
            # Записываем в монитор безопасности (постоянная блокировка)
            if MONITORING_ENABLED:
                security_monitor.log_user_blocked(user_id, reason, 0)
    
    def unblock_user(self, user_id: int):
        """Разблокировать пользователя"""
        stats = self.user_stats[user_id]
        stats.blocked_until = 0
        stats.spam_score = 0
        stats.warning_count = 0
        
        if user_id in self.blocked_users:
            self.blocked_users.remove(user_id)
        
        logger.info(f"Пользователь {user_id} разблокирован администратором")
        
        # Записываем в монитор безопасности
        if MONITORING_ENABLED:
            security_monitor.log_event(
                "USER_UNBLOCKED",
                user_id,
                "Разблокирован администратором",
                "low"
            )
    
    def get_user_stats(self, user_id: int) -> dict:
        """Получить статистику пользователя"""
        stats = self.user_stats[user_id]
        current_time = time.time()
        
        return {
            "user_id": user_id,
            "message_count": stats.message_count,
            "spam_score": stats.spam_score,
            "warning_count": stats.warning_count,
            "is_blocked": self.is_blocked(user_id),
            "blocked_until": stats.blocked_until,
            "remaining_block_time": max(0, int(stats.blocked_until - current_time)),
            "messages_last_hour": len([
                msg_time for msg_time in stats.recent_messages 
                if current_time - msg_time < 3600
            ])
        }
    
    def get_blocked_users(self) -> List[dict]:
        """Получить список заблокированных пользователей"""
        blocked = []
        current_time = time.time()
        
        for user_id, stats in self.user_stats.items():
            if self.is_blocked(user_id):
                remaining = max(0, int(stats.blocked_until - current_time))
                blocked.append({
                    "user_id": user_id,
                    "spam_score": stats.spam_score,
                    "warning_count": stats.warning_count,
                    "remaining_time": remaining,
                    "permanent": user_id in self.blocked_users
                })
        
        return blocked

# Глобальный экземпляр системы защиты
anti_spam = AntiSpamSystem()