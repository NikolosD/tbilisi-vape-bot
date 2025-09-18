"""
Тест исправления часового пояса для резервирования
"""
import asyncio
from datetime import datetime, timezone, timedelta
from database import db, init_db

async def test_timezone_fix():
    """Тест правильности работы часового пояса"""
    
    print("🌍 Тест часового пояса для системы резервирования...")
    
    await init_db()
    
    # Проверяем текущее время в базе
    print("⏰ Проверка времени:")
    db_time_result = await db.fetchone("SHOW timezone")
    print(f"Часовой пояс PostgreSQL: {db_time_result[0]}")
    
    db_time_result = await db.fetchone("SELECT CURRENT_TIMESTAMP as current_time")
    db_time = db_time_result['current_time']
    print(f"Текущее время в PostgreSQL: {db_time}")
    
    # Тестируем создание резерва
    test_user_id = 999999
    test_product_id = 1
    
    try:
        # Добавляем тестового пользователя
        await db.add_user(test_user_id, "testuser", "Test User")
        
        # Очищаем корзину
        await db.clear_cart(test_user_id)
        
        # Добавляем товар в корзину
        success = await db.add_to_cart(test_user_id, test_product_id, 1)
        if success:
            print("✅ Товар добавлен в корзину")
        else:
            print("❌ Не удалось добавить товар в корзину")
            return
        
        # Проверяем время резерва
        cart_data = await db.fetchone("""
            SELECT reserved_until, 
                   CURRENT_TIMESTAMP as current_time,
                   EXTRACT(EPOCH FROM (reserved_until - CURRENT_TIMESTAMP))/60 as minutes_left
            FROM cart 
            WHERE user_id = $1
        """, test_user_id)
        
        if cart_data:
            print(f"🕐 Резерв установлен на: {cart_data['reserved_until']}")
            print(f"🕐 Текущее время: {cart_data['current_time']}")
            print(f"⏱ Осталось минут: {cart_data['minutes_left']:.1f}")
            
            # Тестируем функцию get_cart_expiry_time
            expiry_data = await db.get_cart_expiry_time(test_user_id)
            if expiry_data:
                print(f"✅ get_cart_expiry_time работает: {expiry_data['minutes_left']} минут")
                if expiry_data['minutes_left'] > 10:
                    print("✅ Время резерва корректное (больше 10 минут)")
                else:
                    print("⚠️ Время резерва подозрительно мало")
            else:
                print("❌ get_cart_expiry_time не вернула данные")
        else:
            print("❌ Данные о резерве не найдены")
        
        # Очищаем тестовые данные
        await db.clear_cart(test_user_id)
        print("🧹 Тестовые данные очищены")
        
    except Exception as e:
        print(f"❌ Ошибка во время теста: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.close_pool()

if __name__ == "__main__":
    asyncio.run(test_timezone_fix())