#!/usr/bin/env python3
"""
Инициализация супер-администратора в базе данных
"""
import asyncio
from database import db, init_db
from config import SUPER_ADMIN_ID

async def init_super_admin():
    """Добавить супер-админа в БД если его там нет"""
    # Инициализируем БД
    await init_db()
    
    # Проверяем, есть ли супер-админ в БД
    if not await db.is_admin_in_db(SUPER_ADMIN_ID):
        print(f"Добавляем супер-администратора (ID: {SUPER_ADMIN_ID}) в базу данных...")
        await db.add_admin(
            user_id=SUPER_ADMIN_ID,
            username=None,
            first_name="Super Admin",
            added_by=SUPER_ADMIN_ID
        )
        print("✅ Супер-администратор добавлен в базу данных")
    else:
        print(f"✅ Супер-администратор (ID: {SUPER_ADMIN_ID}) уже есть в базе данных")
    
    # Показываем всех админов
    admins = await db.get_all_admins()
    print(f"\n📋 Список администраторов в БД:")
    print(f"Супер-админ: ID {SUPER_ADMIN_ID}")
    for admin in admins:
        print(f"- ID: {admin[0]}, Username: {admin[1] or 'Нет'}, Имя: {admin[2] or 'Нет'}")

if __name__ == "__main__":
    asyncio.run(init_super_admin())