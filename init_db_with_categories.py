#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных с категориями
"""
import asyncio
from database import Database

async def init_database():
    """Инициализировать базу данных"""
    db = Database()
    await db.init_pool()
    
    print("🔥 Инициализация базы данных...")
    
    # Создаем таблицы
    await db.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        phone TEXT,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица категорий
    await db.execute('''CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        emoji TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица товаров
    await db.execute('''CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        description TEXT,
        photo TEXT,
        category_id INTEGER REFERENCES categories(id),
        in_stock BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица заказов
    await db.execute('''CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        products TEXT,
        total_price DECIMAL(10,2),
        delivery_zone TEXT,
        delivery_price DECIMAL(10,2),
        phone TEXT,
        address TEXT,
        status TEXT DEFAULT 'waiting_payment',
        payment_screenshot TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица корзины
    await db.execute('''CREATE TABLE IF NOT EXISTS cart (
        user_id BIGINT,
        product_id INTEGER,
        quantity INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, product_id)
    )''')
    
    print("✅ База данных инициализирована!")
    
    await db.close_pool()

if __name__ == "__main__":
    asyncio.run(init_database())
