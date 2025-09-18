"""
Тест системы резервирования товаров
"""
import asyncio
from datetime import datetime, timedelta
from database import db, init_db

async def test_reservation_system():
    """Тест основных функций системы резервирования"""
    
    print("🧪 Запуск тестов системы резервирования...")
    
    # Инициализируем базу данных
    await init_db()
    
    # Тестовые пользователи
    user1_id = 123456
    user2_id = 789012
    product_id = 1  # Предполагаем, что товар с ID 1 существует
    
    try:
        # Добавляем тестовых пользователей
        await db.add_user(user1_id, "testuser1", "Test User 1")
        await db.add_user(user2_id, "testuser2", "Test User 2")
        
        # Очищаем корзины перед тестом
        await db.clear_cart(user1_id)
        await db.clear_cart(user2_id)
        
        print("✅ Подготовка тестовых данных завершена")
        
        # Проверяем наличие товара
        product = await db.get_product(product_id)
        if not product:
            print("❌ Товар с ID 1 не найден. Создайте товар для тестирования.")
            return
        
        initial_stock = product.stock_quantity
        print(f"📦 Начальное количество товара на складе: {initial_stock}")
        
        # Тест 1: Добавление товара в корзину первым пользователем
        print("\n🧪 Тест 1: Добавление товара в корзину")
        success = await db.add_to_cart(user1_id, product_id, 2)
        if success:
            print("✅ Пользователь 1 успешно добавил 2 шт. товара в корзину")
        else:
            print("❌ Не удалось добавить товар в корзину пользователя 1")
        
        # Проверяем доступное количество
        available = await db.get_available_product_quantity(product_id)
        reserved = await db.get_reserved_quantity(product_id)
        print(f"📊 Доступно: {available}, Зарезервировано: {reserved}")
        
        # Тест 2: Второй пользователь пытается добавить больше, чем доступно
        print("\n🧪 Тест 2: Конкуренция за товар")
        success = await db.add_to_cart(user2_id, product_id, available + 1)  # Больше чем доступно
        if not success:
            print("✅ Правильно! Пользователь 2 не смог добавить больше доступного количества")
        else:
            print("❌ Ошибка! Пользователь 2 смог добавить больше доступного")
        
        # Тест 3: Второй пользователь добавляет доступное количество
        if available > 0:
            success = await db.add_to_cart(user2_id, product_id, min(available, 1))
            if success:
                print("✅ Пользователь 2 успешно добавил доступное количество")
            else:
                print("❌ Пользователь 2 не смог добавить доступное количество")
        
        # Проверяем корзины
        print("\n📋 Проверка корзин:")
        cart1 = await db.get_cart(user1_id)
        cart2 = await db.get_cart(user2_id)
        
        print(f"🛒 Корзина пользователя 1: {len(cart1)} товаров")
        for item in cart1:
            remaining_time = (item.reserved_until - datetime.now()).total_seconds() / 60 if item.reserved_until else 0
            print(f"  - {item.name}: {item.quantity} шт., истекает через {remaining_time:.1f} мин")
        
        print(f"🛒 Корзина пользователя 2: {len(cart2)} товаров")
        for item in cart2:
            remaining_time = (item.reserved_until - datetime.now()).total_seconds() / 60 if item.reserved_until else 0
            print(f"  - {item.name}: {item.quantity} шт., истекает через {remaining_time:.1f} мин")
        
        # Тест 4: Очистка просроченных резервов
        print("\n🧪 Тест 4: Имитация истечения резерва")
        print("⏳ Устанавливаем просроченный резерв...")
        
        # Искусственно делаем резерв просроченным
        await db.execute(
            "UPDATE cart SET reserved_until = CURRENT_TIMESTAMP - INTERVAL '1 minute' WHERE user_id = $1", 
            user1_id
        )
        
        # Очищаем просроченные резервы
        await db.cleanup_expired_reservations()
        print("✅ Очистка просроченных резервов выполнена")
        
        # Проверяем что резерв исчез
        cart1_after_cleanup = await db.get_cart(user1_id)
        if len(cart1_after_cleanup) == 0:
            print("✅ Просроченные резервы успешно удалены")
        else:
            print("❌ Просроченные резервы не были удалены")
        
        # Проверяем что товар снова доступен
        available_after = await db.get_available_product_quantity(product_id)
        print(f"📦 Доступное количество после очистки: {available_after}")
        
        print("\n🎉 Тестирование системы резервирования завершено!")
        
    except Exception as e:
        print(f"❌ Ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Очищаем тестовые данные
        await db.clear_cart(user1_id)
        await db.clear_cart(user2_id)
        await db.close_pool()

if __name__ == "__main__":
    asyncio.run(test_reservation_system())