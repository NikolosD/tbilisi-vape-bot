"""
Скрипт для обновления времени резервирования заказов с 10 на 5 минут
"""

import asyncio
from database import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_reservation_time():
    """Обновить время резервирования в базе данных"""
    
    await db.create_pool()
    
    logger.info("🔄 Начинаем обновление времени резервирования...")
    
    # Изменяем дефолтное значение для новых резервов
    try:
        await db.execute("""
            ALTER TABLE order_reservations 
            ALTER COLUMN reserved_until 
            SET DEFAULT CURRENT_TIMESTAMP + INTERVAL '5 minutes'
        """)
        logger.info("✅ Дефолтное время резервирования изменено на 5 минут")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось изменить дефолт (возможно уже изменен): {e}")
    
    # Проверяем текущие активные резервы
    active_reserves = await db.fetchall("""
        SELECT 
            order_id,
            EXTRACT(EPOCH FROM (reserved_until - CURRENT_TIMESTAMP))/60 as minutes_left
        FROM order_reservations 
        WHERE reserved_until > CURRENT_TIMESTAMP
    """)
    
    if active_reserves:
        logger.info(f"📋 Найдено активных резервов: {len(active_reserves)}")
        
        # Обновляем активные резервы
        await db.execute("""
            UPDATE order_reservations 
            SET reserved_until = CURRENT_TIMESTAMP + INTERVAL '5 minutes'
            WHERE reserved_until > CURRENT_TIMESTAMP
        """)
        
        logger.info("✅ Активные резервы обновлены на 5 минут")
        
        # Показываем обновленные резервы
        updated_reserves = await db.fetchall("""
            SELECT 
                order_id,
                EXTRACT(EPOCH FROM (reserved_until - CURRENT_TIMESTAMP))/60 as minutes_left
            FROM order_reservations 
            WHERE reserved_until > CURRENT_TIMESTAMP
        """)
        
        for reserve in updated_reserves:
            logger.info(f"  Заказ #{reserve['order_id']}: {reserve['minutes_left']:.1f} минут")
    else:
        logger.info("📋 Активных резервов не найдено")
    
    logger.info("✅ Обновление завершено!")
    
    await db.close_pool()


if __name__ == "__main__":
    asyncio.run(update_reservation_time())