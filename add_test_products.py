#!/usr/bin/env python3
"""
Добавление тестовых товаров в PostgreSQL базу данных
"""

import asyncio
from database import db, init_db

async def add_test_products():
    """Добавление тестовых товаров"""
    print("🔥 Подключение к PostgreSQL базе данных...")
    await init_db()
    
    # Проверяем, есть ли уже товары
    existing_products = await db.get_products()
    if existing_products:
        print(f"✅ В базе уже есть {len(existing_products)} товаров")
        print("Хотите добавить еще? (y/n)")
        # Для автоматического добавления закомментируем проверку
        # return
    
    print("➕ Добавляем тестовые товары...")
    
    test_products = [
        {
            "name": "ELFBAR BC5000 - Blue Razz Ice", 
            "price": 25.0,
            "description": "🫐 Синяя малина с ледяной свежестью\n💨 До 5000 затяжек\n🔋 Встроенная батарея 650mAh\n❄️ Охлаждающий эффект",
            "category": "elfbar"
        },
        {
            "name": "LOST MARY OS5000 - Grape Ice", 
            "price": 28.0,
            "description": "🍇 Сочный виноград с ледяной прохладой\n💨 До 5000 затяжек\n⚡ Быстрая зарядка USB-C\n❄️ Охлаждающий эффект",
            "category": "lostmary"
        },
        {
            "name": "HQD Cuvie Plus - Mango Ice", 
            "price": 22.0,
            "description": "🥭 Спелое манго с ледяной свежестью\n💨 До 1200 затяжек\n❄️ Охлаждающий эффект\n🌴 Тропический вкус",
            "category": "hqd"
        },
        {
            "name": "VOZOL Gear 10000 - Apple Ice", 
            "price": 35.0,
            "description": "🍎 Зеленое яблоко с ментолом\n💨 До 10000 затяжек\n🔋 Мощная батарея\n📱 Индикатор заряда\n❄️ Освежающий вкус",
            "category": "vozol"
        },
        {
            "name": "JUUL Pods - Virginia Tobacco", 
            "price": 38.0,
            "description": "🚬 Классический табачный вкус\n📦 4 картриджа в упаковке\n🎯 Оригинальные JUUL поды\n💫 Насыщенный вкус",
            "category": "juul"
        }
    ]
    
    # Добавляем товары
    for product in test_products:
        await db.add_product(
            name=product["name"],
            price=product["price"], 
            description=product["description"],
            category=product["category"]
        )
        print(f"✅ Добавлен: {product['name']} - {product['price']} лари")
    
    # Проверяем результат
    all_products = await db.get_products()
    print(f"\n🎉 Успешно! В базе теперь {len(all_products)} товаров")
    
    print("\n📱 Теперь проверьте бота:")
    print("1. Откройте @tbilisi_vape_bot в Telegram")
    print("2. Нажмите /start")
    print("3. Выберите '🛍 Каталог'")
    print("4. Должны появиться добавленные товары!")
    
    await db.close_pool()

if __name__ == "__main__":
    asyncio.run(add_test_products())