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
                # Очищаем просроченные резервы корзин каждые 2 минуты
                await db.cleanup_expired_reservations()
                
                # Проверяем заказы с истекающими резервами и отправляем уведомления
                await self._check_expiring_reservations()
                
                # Очищаем просроченные резервы заказов (с отменой заказов)
                await db.cleanup_expired_order_reservations()
                
                # Получаем статистику для логирования
                cart_reserved_count = await self._get_total_reserved_items()
                order_reserved_count = await self._get_total_order_reserved_items()
                
                if cart_reserved_count > 0:
                    logger.debug(f"Активных резервов в корзинах: {cart_reserved_count}")
                if order_reserved_count > 0:
                    logger.debug(f"Активных резервов в заказах: {order_reserved_count}")
                
                # Ожидаем 1 минуту перед следующей очисткой (сокращаем интервал для заказов)
                await asyncio.sleep(60)
                
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
    
    async def _get_total_order_reserved_items(self):
        """Получить общее количество зарезервированных товаров в заказах"""
        try:
            query = "SELECT COUNT(*) FROM order_reservations WHERE reserved_until > CURRENT_TIMESTAMP"
            result = await db.fetchone(query)
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Ошибка получения статистики резервов заказов: {e}")
            return 0
    
    async def _check_expiring_reservations(self):
        """Проверка заказов с истекающими резервами и отправка уведомлений"""
        try:
            # Получаем заказы с резервами, которые истекают в течение 2 минут
            query = """
            SELECT o.id, o.user_id, o.order_number,
                   EXTRACT(EPOCH FROM (ord_res.reserved_until - CURRENT_TIMESTAMP))/60 as minutes_left
            FROM orders o
            JOIN order_reservations ord_res ON o.id = ord_res.order_id
            WHERE o.status = 'waiting_payment' 
            AND ord_res.reserved_until > CURRENT_TIMESTAMP 
            AND ord_res.reserved_until <= CURRENT_TIMESTAMP + INTERVAL '2 minutes'
            """
            expiring_orders = await db.fetchall(query)
            
            for order_info in expiring_orders:
                minutes_left = int(order_info['minutes_left'])
                if minutes_left <= 2 and minutes_left > 0:
                    try:
                        from notifications import notification_system
                        if notification_system:
                            await notification_system.notify_reservation_expiring(
                                order_info['id'], 
                                minutes_left
                            )
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления об истечении резерва: {e}")
                        
        except Exception as e:
            logger.error(f"Ошибка проверки истекающих резервов: {e}")
    
    async def force_cleanup(self):
        """Принудительная очистка просроченных резервов"""
        try:
            await db.cleanup_expired_reservations()
            await db.cleanup_expired_order_reservations()
            logger.info("Выполнена принудительная очистка просроченных резервов")
        except Exception as e:
            logger.error(f"Ошибка принудительной очистки: {e}")

# Глобальный экземпляр планировщика
reservation_scheduler = ReservationScheduler()