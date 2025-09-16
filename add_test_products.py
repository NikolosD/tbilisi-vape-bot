#!/usr/bin/env python3
"""
Скрипт для добавления тестовых товаров в базу данных
"""

import asyncio
from database import db, init_db

async def add_test_products():
    """Добавить тестовые товары"""
    print("🔥 Инициализация базы данных...")
    await init_db()
    
    print("📦 Добавление тестовых товаров...")
    
    # Список тестовых товаров
    test_products = [
        {
            "name": "Elf Bar 600 Puffs - Манго",
            "price": 25.0,
            "description": "Одноразовая электронная сигарета с вкусом манго. 600 затяжек, 2% никотина.",
            "photo": None,
            "category": "vape"
        },
        {
            "name": "Elf Bar 600 Puffs - Клубника",
            "price": 25.0,
            "description": "Одноразовая электронная сигарета с вкусом клубники. 600 затяжек, 2% никотина.",
            "photo": None,
            "category": "vape"
        },
        {
            "name": "Elf Bar 600 Puffs - Мята",
            "price": 25.0,
            "description": "Одноразовая электронная сигарета с мятным вкусом. 600 затяжек, 2% никотина.",
            "photo": None,
            "category": "vape"
        },
        {
            "name": "Elf Bar 600 Puffs - Виноград",
            "price": 25.0,
            "description": "Одноразовая электронная сигарета с вкусом винограда. 600 затяжек, 2% никотина.",
            "photo": None,
            "category": "vape"
        },
        {
            "name": "Elf Bar 600 Puffs - Банан",
            "price": 25.0,
            "description": "Одноразовая электронная сигарета с банановым вкусом. 600 затяжек, 2% никотина.",
            "photo": None,
            "category": "vape"
        },
        {
            "name": "Elf Bar 600 Puffs - Кола",
            "price": 25.0,
            "description": "Одноразовая электронная сигарета с вкусом колы. 600 затяжек, 2% никотина.",
            "photo": None,
            "category": "vape"
        }
    ]
    
    # Добавляем товары
    for product in test_products:
        try:
            await db.add_product(
                name=product["name"],
                price=product["price"],
                description=product["description"],
                photo=product["photo"],
                category=product["category"]
            )
            print(f"✅ Добавлен: {product['name']} - {product['price']}₾")
        except Exception as e:
            print(f"❌ Ошибка при добавлении {product['name']}: {e}")
    
    print("\n🎉 Тестовые товары добавлены!")
    print("📱 Теперь можно тестировать бота!")

if __name__ == "__main__":
    asyncio.run(add_test_products())