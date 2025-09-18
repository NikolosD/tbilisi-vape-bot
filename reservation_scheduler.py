"""
Планировщик для автоматической очистки просроченных резервов товаров
"""
import asyncio
import logging
from datetime import datetime
from database import db

logger = logging.getLogger(__name__)

class ReservationScheduler:
    """Планировщик для управления резервированием товаров"""
    
    def __init__(self):
        self._running = False
        self._task = None
    
    async def start(self):
        """Запуск планировщика"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info("Планировщик очистки резервов запущен")
    
    async def stop(self):
        """Остановка планировщика"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Планировщик очистки резервов остановлен")
    
    async def _cleanup_loop(self):
        """Основной цикл очистки просроченных резервов"""
        while self._running:
            try:
                # Очищаем просроченные резервы каждые 2 минуты
                await db.cleanup_expired_reservations()
                
                # Получаем статистику для логирования
                reserved_count = await self._get_total_reserved_items()
                if reserved_count > 0:
                    logger.debug(f"Активных резервов в корзинах: {reserved_count}")
                
                # Ожидаем 2 минуты перед следующей очисткой
                await asyncio.sleep(120)
                
            except Exception as e:
                logger.error(f"Ошибка в планировщике очистки резервов: {e}")
                # В случае ошибки ждем 30 секунд и продолжаем
                await asyncio.sleep(30)
    
    async def _get_total_reserved_items(self):
        """Получить общее количество зарезервированных товаров"""
        try:
            query = "SELECT COUNT(*) FROM cart WHERE reserved_until > CURRENT_TIMESTAMP"
            result = await db.fetchone(query)
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Ошибка получения статистики резервов: {e}")
            return 0
    
    async def force_cleanup(self):
        """Принудительная очистка просроченных резервов"""
        try:
            await db.cleanup_expired_reservations()
            logger.info("Выполнена принудительная очистка просроченных резервов")
        except Exception as e:
            logger.error(f"Ошибка принудительной очистки: {e}")

# Глобальный экземпляр планировщика
reservation_scheduler = ReservationScheduler()