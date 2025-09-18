#!/usr/bin/env python3
"""
Скрипт для добавления поля flavor_category_id в таблицу products
"""

import asyncio
import asyncpg
from config import DATABASE_URL


async def add_flavor_field():
    """Добавить поле flavor_category_id в таблицу products"""
    
    try:
        # Подключение к базе данных
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Подключение к базе данных установлено")
        
        # Проверяем существует ли уже поле
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'products' 
                AND column_name = 'flavor_category_id'
            )
        """)
        
        if column_exists:
            print("⚠️  Поле flavor_category_id уже существует в таблице products")
        else:
            # Добавляем поле flavor_category_id
            await conn.execute("""
                ALTER TABLE products 
                ADD COLUMN flavor_category_id INTEGER 
                REFERENCES flavor_categories(id) ON DELETE SET NULL
            """)
            print("✅ Поле flavor_category_id добавлено в таблицу products")
        
        # Проверяем структуру таблицы
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'products' 
            ORDER BY ordinal_position
        """)
        
        print(f"\n📋 Структура таблицы products:")
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"   {col['column_name']} ({col['data_type']}) {nullable}")
        
        # Проверяем внешние ключи
        foreign_keys = await conn.fetch("""
            SELECT 
                tc.constraint_name, 
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' 
            AND tc.table_name = 'products'
        """)
        
        print(f"\n🔗 Внешние ключи таблицы products:")
        for fk in foreign_keys:
            print(f"   {fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
        
        await conn.close()
        print("\n🎉 Миграция успешно завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении поля: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(add_flavor_field())