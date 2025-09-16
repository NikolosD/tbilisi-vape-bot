#!/usr/bin/env python3
"""
Скрипт для добавления категорий по брендам
"""
import asyncio
from database import Database

async def add_categories():
    """Добавить категории по брендам"""
    db = Database()
    await db.init_pool()
    
    # Категории по брендам
    categories = [
        ("Elf Bar", "🧚", "Одноразовые сигареты Elf Bar - популярный бренд с разнообразными вкусами"),
        ("VOZOL", "💨", "Одноразовые сигареты VOZOL - качество и надежность"),
        ("LOST MARY", "🌊", "Одноразовые сигареты LOST MARY - уникальные вкусы"),
        ("Geek Bar", "⚡", "Одноразовые сигареты Geek Bar - мощные и долговечные"),
        ("HQD", "🔥", "Одноразовые сигареты HQD - премиум качество"),
        ("Puff Bar", "☁️", "Одноразовые сигареты Puff Bar - классика жанра"),
        ("Hyde", "🌪️", "Одноразовые сигареты Hyde - мощные затяжки"),
        ("Air Bar", "🌬️", "Одноразовые сигареты Air Bar - легкие и приятные"),
        ("Fume", "💫", "Одноразовые сигареты Fume - эксклюзивные вкусы"),
        ("Breeze", "🌊", "Одноразовые сигареты Breeze - освежающие вкусы")
    ]
    
    print("🏷️ Добавляем категории по брендам...")
    
    for name, emoji, description in categories:
        try:
            await db.add_category(name, emoji, description)
            print(f"✅ Добавлена категория: {emoji} {name}")
        except Exception as e:
            print(f"❌ Ошибка при добавлении категории {name}: {e}")
    
    print("\n🎉 Все категории добавлены!")
    
    # Показываем добавленные категории
    categories_list = await db.get_categories()
    print(f"\n📋 Всего категорий в базе: {len(categories_list)}")
    for category in categories_list:
        print(f"  {category[2]} {category[1]} - {category[3]}")
    
    await db.close_pool()

if __name__ == "__main__":
    asyncio.run(add_categories())
