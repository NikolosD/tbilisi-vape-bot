"""
Мониторинг безопасности и система алертов
"""
import time
import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

@dataclass
class SecurityEvent:
    """Событие безопасности"""
    timestamp: float
    event_type: str
    user_id: int
    details: str
    severity: str  # low, medium, high, critical

class SecurityMonitor:
    """Монитор безопасности"""
    
    def __init__(self):
        self.events: deque = deque(maxlen=1000)  # Последние 1000 событий
        self.blocked_users_count = defaultdict(int)
        self.global_message_count = defaultdict(int)
        self.suspicious_ips = set()
        self.admin_ids = set()
        
        # Счетчики для обнаружения атак
        self.recent_blocks = deque(maxlen=50)
        self.recent_messages = deque(maxlen=1000)
        
    def set_admin_ids(self, admin_ids: List[int]):
        """Установить ID администраторов"""
        self.admin_ids = set(admin_ids)
    
    def log_event(self, event_type: str, user_id: int, details: str, severity: str = "low"):
        """Записать событие безопасности"""
        event = SecurityEvent(
            timestamp=time.time(),
            event_type=event_type,
            user_id=user_id,
            details=details,
            severity=severity
        )
        
        self.events.append(event)
        
        # Логируем в файл
        logger.warning(f"Security Event: {event_type} - User {user_id} - {details} - Severity: {severity}")
        
        # Проверяем на критические события
        if severity == "critical":
            asyncio.create_task(self._notify_admins_critical(event))
    
    def log_user_blocked(self, user_id: int, reason: str, duration: int = 0):
        """Записать блокировку пользователя"""
        self.blocked_users_count[user_id] += 1
        self.recent_blocks.append({
            "timestamp": time.time(),
            "user_id": user_id,
            "reason": reason,
            "duration": duration
        })
        
        severity = "medium"
        if self.blocked_users_count[user_id] > 3:
            severity = "high"
        if duration == 0:  # Permanent block
            severity = "critical"
        
        self.log_event("USER_BLOCKED", user_id, f"Reason: {reason}, Duration: {duration}s", severity)
        
        # Проверяем на массовые блокировки
        self._check_mass_blocking()
    
    def log_message(self, user_id: int, message_type: str = "text"):
        """Записать сообщение для мониторинга"""
        current_time = time.time()
        self.recent_messages.append({
            "timestamp": current_time,
            "user_id": user_id,
            "type": message_type
        })
        
        # Обновляем глобальный счетчик
        minute_key = int(current_time // 60)
        self.global_message_count[minute_key] += 1
        
        # Очищаем старые записи (старше часа)
        hour_ago = current_time - 3600
        old_keys = [k for k in self.global_message_count.keys() if k * 60 < hour_ago]
        for key in old_keys:
            del self.global_message_count[key]
    
    def _check_mass_blocking(self):
        """Проверить на массовые блокировки (возможная атака)"""
        current_time = time.time()
        recent_blocks_5min = [
            block for block in self.recent_blocks 
            if current_time - block["timestamp"] < 300  # 5 минут
        ]
        
        if len(recent_blocks_5min) >= 5:  # 5 блокировок за 5 минут
            self.log_event(
                "MASS_BLOCKING_DETECTED",
                0,
                f"Detected {len(recent_blocks_5min)} blocks in 5 minutes",
                "critical"
            )
    
    def detect_ddos_attempt(self) -> bool:
        """Обнаружить попытку DDoS"""
        current_time = time.time()
        
        # Проверяем глобальную нагрузку за последнюю минуту
        current_minute = int(current_time // 60)
        messages_this_minute = self.global_message_count.get(current_minute, 0)
        
        if messages_this_minute > 100:  # Более 100 сообщений в минуту
            self.log_event(
                "POSSIBLE_DDOS",
                0,
                f"High message rate: {messages_this_minute}/min",
                "critical"
            )
            return True
        
        # Проверяем всплески активности
        recent_messages_10sec = [
            msg for msg in self.recent_messages 
            if current_time - msg["timestamp"] < 10
        ]
        
        if len(recent_messages_10sec) > 30:  # Более 30 сообщений за 10 секунд
            self.log_event(
                "ACTIVITY_BURST",
                0,
                f"Activity burst: {len(recent_messages_10sec)} messages in 10s",
                "high"
            )
            return True
        
        return False
    
    def get_security_stats(self) -> dict:
        """Получить статистику безопасности"""
        current_time = time.time()
        
        # События за последний час
        hour_ago = current_time - 3600
        recent_events = [e for e in self.events if e.timestamp > hour_ago]
        
        # Блокировки за последний час
        recent_blocks = [b for b in self.recent_blocks if current_time - b["timestamp"] < 3600]
        
        # Сообщения за последний час
        recent_messages = [m for m in self.recent_messages if current_time - m["timestamp"] < 3600]
        
        return {
            "events_last_hour": len(recent_events),
            "blocks_last_hour": len(recent_blocks),
            "messages_last_hour": len(recent_messages),
            "total_events": len(self.events),
            "unique_blocked_users": len(self.blocked_users_count),
            "severity_breakdown": {
                "low": len([e for e in recent_events if e.severity == "low"]),
                "medium": len([e for e in recent_events if e.severity == "medium"]),
                "high": len([e for e in recent_events if e.severity == "high"]),
                "critical": len([e for e in recent_events if e.severity == "critical"])
            }
        }
    
    def get_recent_events(self, limit: int = 20) -> List[SecurityEvent]:
        """Получить последние события"""
        return list(self.events)[-limit:]
    
    def get_top_blocked_users(self, limit: int = 10) -> List[dict]:
        """Получить топ заблокированных пользователей"""
        sorted_users = sorted(
            self.blocked_users_count.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {"user_id": user_id, "block_count": count}
            for user_id, count in sorted_users[:limit]
        ]
    
    async def _notify_admins_critical(self, event: SecurityEvent):
        """Уведомить администраторов о критическом событии"""
        # Здесь можно добавить отправку уведомлений админам
        # Например, через Telegram или email
        pass
    
    def cleanup_old_data(self):
        """Очистить старые данные"""
        current_time = time.time()
        week_ago = current_time - (7 * 24 * 3600)  # Неделя назад
        
        # Очищаем старые блокировки
        self.recent_blocks = deque([
            block for block in self.recent_blocks 
            if current_time - block["timestamp"] < week_ago
        ], maxlen=50)
        
        # Очищаем старые сообщения
        self.recent_messages = deque([
            msg for msg in self.recent_messages 
            if current_time - msg["timestamp"] < week_ago
        ], maxlen=1000)

# Глобальный экземпляр монитора
security_monitor = SecurityMonitor()