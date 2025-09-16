#!/usr/bin/env python3
"""
Скрипт для миграции базы данных - добавление category_id
"""
import asyncio
from database import Database

async def migrate_database():
    """Мигрировать базу данных"""
    db = Database()
    await db.init_pool()
    
    print("🔄 Миграция базы данных...")
    
    try:
        # Добавляем колонку category_id если её нет
        await db.execute('''ALTER TABLE products ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES categories(id)''')
        print("✅ Колонка category_id добавлена!")
        
        # Удаляем старую колонку category если она есть
        try:
            await db.execute('''ALTER TABLE products DROP COLUMN IF EXISTS category''')
            print("✅ Старая колонка category удалена!")
        except:
            print("ℹ️ Колонка category не найдена или уже удалена")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
    
    await db.close_pool()

if __name__ == "__main__":
    asyncio.run(migrate_database())
