#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы бота
"""

import asyncio
from aiogram import Bot
from config import BOT_TOKEN

async def test_bot():
    """Тестирование бота"""
    print("🔥 Тестирование Tbilisi VAPE Bot...")
    
    bot = Bot(token=BOT_TOKEN)
    
    try:
        # Получаем информацию о боте
        me = await bot.get_me()
        print(f"✅ Бот найден: @{me.username}")
        print(f"📝 Имя: {me.first_name}")
        print(f"🆔 ID: {me.id}")
        
        # Проверяем права
        try:
            updates = await bot.get_updates()
            print(f"📡 Получение обновлений: OK")
        except Exception as e:
            print(f"❌ Ошибка получения обновлений: {e}")
        
        print(f"\n🎉 БОТ РАБОТАЕТ!")
        print(f"Найдите @{me.username} в Telegram и напишите /start")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("Проверьте токен в config.py")
    
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test_bot())