"""
Отладка проблемы с временем резервирования
"""
import asyncio
from datetime import datetime, timezone
from database import db, init_db

async def debug_reservation_time():
    """Отладка времени резервирования"""
    
    print("🔍 Отладка времени резервирования...")
    
    await init_db()
    
    # Проверяем текущее время в базе и Python
    db_time_result = await db.fetchone("SELECT CURRENT_TIMESTAMP as db_time")
    db_time = db_time_result['db_time']
    python_time = datetime.now()
    
    print(f"🕐 Время в PostgreSQL: {db_time}")
    print(f"🕐 Время в Python: {python_time}")
    print(f"🕐 Разница: {(python_time - db_time.replace(tzinfo=None)).total_seconds()} секунд")
    
    # Проверяем активные резервы
    active_reservations = await db.fetchall("""
        SELECT user_id, product_id, quantity, reserved_until, 
               EXTRACT(EPOCH FROM (reserved_until - CURRENT_TIMESTAMP))/60 as minutes_left
        FROM cart 
        WHERE reserved_until > CURRENT_TIMESTAMP
    """)
    
    print(f"\n📋 Активные резервы: {len(active_reservations)}")
    for res in active_reservations:
        print(f"  User {res['user_id']}: продукт {res['product_id']}, "
              f"истекает через {res['minutes_left']:.1f} мин ({res['reserved_until']})")
    
    # Проверяем все резервы (включая просроченные)
    all_reservations = await db.fetchall("""
        SELECT user_id, product_id, quantity, reserved_until,
               EXTRACT(EPOCH FROM (reserved_until - CURRENT_TIMESTAMP))/60 as minutes_left
        FROM cart
    """)
    
    print(f"\n📋 Все резервы (включая просроченные): {len(all_reservations)}")
    for res in all_reservations:
        status = "активный" if res['minutes_left'] > 0 else "просрочен"
        print(f"  User {res['user_id']}: продукт {res['product_id']}, "
              f"{res['minutes_left']:.1f} мин ({status}) - {res['reserved_until']}")
    
    await db.close_pool()

if __name__ == "__main__":
    asyncio.run(debug_reservation_time())