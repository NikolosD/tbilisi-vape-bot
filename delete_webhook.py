#!/usr/bin/env python3
"""
Скрипт для удаления webhook перед деплоем
"""
import asyncio
import aiohttp
import os
from config import BOT_TOKEN

async def delete_webhook():
    """Удалить webhook бота"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url) as response:
                result = await response.json()
                if result.get('ok'):
                    print("✅ Webhook успешно удален")
                else:
                    print(f"❌ Ошибка удаления webhook: {result}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(delete_webhook())
