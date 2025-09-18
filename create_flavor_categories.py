#!/usr/bin/env python3
"""
Скрипт для создания таблицы категорий вкусов и добавления базовых категорий
"""

import asyncio
import asyncpg
from config import DATABASE_URL


async def create_flavor_categories():
    """Создать таблицу категорий вкусов и добавить базовые категории"""
    
    # SQL для создания таблицы и базовых данных
    sql_script = """
    -- Создание таблицы категорий вкусов
    CREATE TABLE IF NOT EXISTS flavor_categories (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        emoji VARCHAR(10) DEFAULT '',
        description TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Создание функции для автоматического обновления updated_at
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    -- Создание триггера для автоматического обновления updated_at
    DROP TRIGGER IF EXISTS update_flavor_categories_updated_at ON flavor_categories;
    CREATE TRIGGER update_flavor_categories_updated_at
        BEFORE UPDATE ON flavor_categories
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """
    
    # Базовые категории вкусов
    flavor_categories = [
        ('Ягодные', '🍓', 'Клубника, малина, черника и другие ягодные вкусы'),
        ('Ментол/Лед', '❄️', 'Ментоловые и освежающие вкусы с охлаждающим эффектом'),
        ('Цитрусы', '🍊', 'Лимон, апельсин, грейпфрут и другие цитрусовые'),
        ('Экзотика', '🥭', 'Манго, маракуйя, киви и другие экзотические фрукты'),
        ('Сладкие', '🍰', 'Десертные и сладкие вкусы: торты, конфеты, мороженое')
    ]
    
    try:
        # Подключение к базе данных
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Подключение к базе данных установлено")
        
        # Выполнение SQL скрипта для создания таблицы и функций
        await conn.execute(sql_script)
        print("✅ Таблица flavor_categories создана")
        
        # Добавление базовых категорий
        for name, emoji, description in flavor_categories:
            try:
                await conn.execute(
                    "INSERT INTO flavor_categories (name, emoji, description) VALUES ($1, $2, $3)",
                    name, emoji, description
                )
                print(f"✅ Добавлена категория: {emoji} {name}")
            except asyncpg.UniqueViolationError:
                print(f"⚠️  Категория уже существует: {emoji} {name}")
        
        # Проверяем созданные категории
        categories = await conn.fetch("SELECT * FROM flavor_categories ORDER BY id")
        print(f"\n📋 Всего категорий в базе: {len(categories)}")
        for cat in categories:
            print(f"   {cat['id']}. {cat['emoji']} {cat['name']}")
        
        await conn.close()
        print("\n🎉 Миграция успешно завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблицы: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(create_flavor_categories())