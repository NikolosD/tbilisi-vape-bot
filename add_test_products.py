#!/usr/bin/env python3
"""
Скрипт для добавления тестовых товаров в базу данных
"""

import asyncio
from database import Database

async def add_test_products():
    """Добавить тестовые товары"""
    db = Database()
    await db.init_pool()
    
    print("📦 Добавление тестовых товаров...")
    
    # Сначала получаем категории
    categories = await db.get_categories()
    category_map = {cat[1]: cat[0] for cat in categories}  # name -> id
    
    # Список тестовых товаров по брендам
    test_products = [
        # Elf Bar
        {
            "name": "Elf Bar 600 Puffs - Манго",
            "price": 25.0,
            "description": "🍈 Сочный вкус манго\n💨 600 затяжек\n⚡ 2% никотина\n🔋 Встроенная батарея",
            "photo": None,
            "category_name": "Elf Bar"
        },
        {
            "name": "Elf Bar 600 Puffs - Клубника",
            "price": 25.0,
            "description": "🍓 Сладкий вкус клубники\n💨 600 затяжек\n⚡ 2% никотина\n🔋 Встроенная батарея",
            "photo": None,
            "category_name": "Elf Bar"
        },
        {
            "name": "Elf Bar 600 Puffs - Мята",
            "price": 25.0,
            "description": "🌿 Освежающий мятный вкус\n💨 600 затяжек\n⚡ 2% никотина\n🔋 Встроенная батарея",
            "photo": None,
            "category_name": "Elf Bar"
        },
        # VOZOL
        {
            "name": "VOZOL Gear 10000 - Apple Ice",
            "price": 35.0,
            "description": "🍎 Зеленое яблоко с ментолом\n💨 До 10000 затяжек\n🔋 Мощная батарея\n📱 Индикатор заряда\n❄️ Освежающий вкус",
            "photo": None,
            "category_name": "VOZOL"
        },
        {
            "name": "VOZOL Gear 10000 - Grape Ice",
            "price": 35.0,
            "description": "🍇 Виноград с ментолом\n💨 До 10000 затяжек\n🔋 Мощная батарея\n📱 Индикатор заряда\n❄️ Освежающий вкус",
            "photo": None,
            "category_name": "VOZOL"
        },
        # LOST MARY
        {
            "name": "LOST MARY OS5000 - Grape Ice",
            "price": 28.0,
            "description": "🍇 Виноград с ментолом\n💨 До 5000 затяжек\n🔋 Мощная батарея\n📱 Индикатор заряда\n❄️ Освежающий вкус",
            "photo": None,
            "category_name": "LOST MARY"
        },
        {
            "name": "LOST MARY OS5000 - Blueberry",
            "price": 28.0,
            "description": "🫐 Сочный вкус черники\n💨 До 5000 затяжек\n🔋 Мощная батарея\n📱 Индикатор заряда",
            "photo": None,
            "category_name": "LOST MARY"
        },
        # Geek Bar
        {
            "name": "Geek Bar Pulse 15000 - Watermelon Ice",
            "price": 40.0,
            "description": "🍉 Арбуз с ментолом\n💨 До 15000 затяжек\n🔋 Мощная батарея\n📱 Индикатор заряда\n❄️ Освежающий вкус",
            "photo": None,
            "category_name": "Geek Bar"
        }
    ]
    
    # Добавляем товары
    for product in test_products:
        try:
            category_id = category_map.get(product["category_name"])
            if not category_id:
                print(f"❌ Категория '{product['category_name']}' не найдена!")
                continue
                
            await db.add_product(
                name=product["name"],
                price=product["price"],
                description=product["description"],
                photo=product["photo"],
                category_id=category_id
            )
            print(f"✅ Добавлен: {product['name']} - {product['price']}₾ ({product['category_name']})")
        except Exception as e:
            print(f"❌ Ошибка при добавлении {product['name']}: {e}")
    
    print("\n🎉 Тестовые товары добавлены!")
    print("📱 Теперь можно тестировать бота!")
    
    await db.close_pool()

if __name__ == "__main__":
    asyncio.run(add_test_products())