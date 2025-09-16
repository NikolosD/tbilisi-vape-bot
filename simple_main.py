import asyncio
import logging
import json
import sqlite3
from datetime import datetime

# Простая версия без aiogram для тестирования
print("🔥 Tbilisi VAPE Bot - Тестовая версия")
print("✅ Проверка базы данных...")

# Проверим базу данных
conn = sqlite3.connect('shop.db')
cursor = conn.cursor()

# Проверим товары
cursor.execute("SELECT COUNT(*) FROM products")
products_count = cursor.fetchone()[0]
print(f"📦 Товаров в базе: {products_count}")

# Проверим пользователей
cursor.execute("SELECT COUNT(*) FROM users")
users_count = cursor.fetchone()[0]
print(f"👥 Пользователей в базе: {users_count}")

# Проверим заказы
cursor.execute("SELECT COUNT(*) FROM orders")
orders_count = cursor.fetchone()[0]
print(f"📋 Заказов в базе: {orders_count}")

# Покажем несколько товаров
print("\n🛍 Примеры товаров:")
cursor.execute("SELECT name, price FROM products LIMIT 5")
products = cursor.fetchall()
for product in products:
    print(f"• {product[0]} - {product[1]}₾")

conn.close()

print("\n🚀 База данных работает!")
print("✅ Структура проекта готова!")
print("\n📝 Для запуска полной версии:")
print("1. Установите Python 3.11 или 3.12 (у вас 3.13 - может быть проблема)")
print("2. pip install aiogram==3.4.1")
print("3. python3 main.py")
print("\nИли запустите на сервере/другом компьютере с подходящей версией Python.")