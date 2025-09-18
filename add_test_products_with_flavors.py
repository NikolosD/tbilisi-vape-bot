#!/usr/bin/env python3
"""
Скрипт для добавления тестовых товаров одноразовых сигарет с вкусами
"""

import asyncio
import asyncpg
from config import DATABASE_URL
from decimal import Decimal


async def add_test_products():
    """Добавить тестовые товары с вкусами"""
    
    # Тестовые товары с привязкой к вкусам
    test_products = [
        # Ягодные вкусы (flavor_category_id = 1)
        {
            'name': 'Elf Bar 600 Strawberry Ice',
            'price': Decimal('15.00'),
            'description': 'Одноразовая сигарета с ярким вкусом клубники и охлаждающим эффектом. 600 затяжек.',
            'category_id': 1,  # Elf Bar
            'flavor_category_id': 1,  # Ягодные
            'stock_quantity': 25
        },
        {
            'name': 'VOZOL Gear 10000 Blueberry',
            'price': Decimal('28.00'),
            'description': 'Премиум одноразовая сигарета с насыщенным вкусом черники. 10000 затяжек.',
            'category_id': 2,  # VOZOL
            'flavor_category_id': 1,  # Ягодные
            'stock_quantity': 15
        },
        {
            'name': 'LOST MARY Berry Mix',
            'price': Decimal('22.00'),
            'description': 'Микс лесных ягод в элегантном дизайне. 5000 затяжек.',
            'category_id': 3,  # LOST MARY
            'flavor_category_id': 1,  # Ягодные
            'stock_quantity': 20
        },
        
        # Ментол/Лед (flavor_category_id = 2)
        {
            'name': 'Geek Bar Pulse Cool Mint',
            'price': Decimal('32.00'),
            'description': 'Освежающий ментол с технологией Pulse. 15000 затяжек.',
            'category_id': 4,  # Geek Bar
            'flavor_category_id': 2,  # Ментол/Лед
            'stock_quantity': 18
        },
        {
            'name': 'HQD Cuvie Ice Mint',
            'price': Decimal('18.00'),
            'description': 'Классический ледяной ментол для освежения. 3000 затяжек.',
            'category_id': 5,  # HQD
            'flavor_category_id': 2,  # Ментол/Лед
            'stock_quantity': 30
        },
        
        # Цитрусы (flavor_category_id = 3)
        {
            'name': 'Puff Bar Plus Lemon Ice',
            'price': Decimal('12.00'),
            'description': 'Кислый лимон с ледяными нотками. 800 затяжек.',
            'category_id': 6,  # Puff Bar
            'flavor_category_id': 3,  # Цитрусы
            'stock_quantity': 35
        },
        {
            'name': 'Elf Bar BC5000 Orange Soda',
            'price': Decimal('20.00'),
            'description': 'Вкус апельсиновой газировки. 5000 затяжек.',
            'category_id': 1,  # Elf Bar
            'flavor_category_id': 3,  # Цитрусы
            'stock_quantity': 22
        },
        
        # Экзотика (flavor_category_id = 4)
        {
            'name': 'Air Bar Lux Mango Ice',
            'price': Decimal('16.00'),
            'description': 'Тропический манго с охлаждением. 2500 затяжек.',
            'category_id': 8,  # Air Bar
            'flavor_category_id': 4,  # Экзотика
            'stock_quantity': 28
        },
        {
            'name': 'Hyde Edge Passion Fruit',
            'price': Decimal('25.00'),
            'description': 'Экзотическая маракуйя в мощном устройстве. 6000 затяжек.',
            'category_id': 7,  # Hyde
            'flavor_category_id': 4,  # Экзотика
            'stock_quantity': 12
        },
        
        # Сладкие (flavor_category_id = 5)
        {
            'name': 'Fume Extra Vanilla Custard',
            'price': Decimal('19.00'),
            'description': 'Нежный ванильный крем. 1500 затяжек.',
            'category_id': 9,  # Fume
            'flavor_category_id': 5,  # Сладкие
            'stock_quantity': 20
        },
        {
            'name': 'Breeze Plus Cotton Candy',
            'price': Decimal('14.00'),
            'description': 'Сладкая сахарная вата. 2000 затяжек.',
            'category_id': 10,  # Breeze
            'flavor_category_id': 5,  # Сладкие
            'stock_quantity': 25
        }
    ]
    
    try:
        # Подключение к базе данных
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Подключение к базе данных установлено")
        
        # Добавляем тестовые товары
        added_count = 0
        for product in test_products:
            try:
                await conn.execute("""
                    INSERT INTO products (name, price, description, category_id, flavor_category_id, stock_quantity, in_stock) 
                    VALUES ($1, $2, $3, $4, $5, $6, true)
                """, 
                product['name'], 
                product['price'], 
                product['description'], 
                product['category_id'], 
                product['flavor_category_id'], 
                product['stock_quantity'])
                
                print(f"✅ Добавлен: {product['name']}")
                added_count += 1
                
            except asyncpg.UniqueViolationError:
                print(f"⚠️  Товар уже существует: {product['name']}")
            except Exception as e:
                print(f"❌ Ошибка при добавлении {product['name']}: {e}")
        
        # Проверяем результаты
        flavor_stats = await conn.fetch("""
            SELECT 
                fc.name as flavor_name,
                fc.emoji,
                COUNT(p.id) as products_count
            FROM flavor_categories fc
            LEFT JOIN products p ON fc.id = p.flavor_category_id AND p.in_stock = true
            GROUP BY fc.id, fc.name, fc.emoji
            ORDER BY fc.id
        """)
        
        print(f"\n🎉 Добавлено товаров: {added_count}")
        print(f"\n📊 Статистика по вкусам:")
        for stat in flavor_stats:
            print(f"   {stat['emoji']} {stat['flavor_name']}: {stat['products_count']} товаров")
        
        await conn.close()
        print("\n✅ Тестовые товары успешно добавлены!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(add_test_products())