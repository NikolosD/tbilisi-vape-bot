#!/usr/bin/env python3
"""
Версия main.py для разработки с автоматической перезагрузкой
"""
import asyncio
import logging
import signal
import sys
import os
from pathlib import Path
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web, ClientSession

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent))

from config import BOT_TOKEN, ADMIN_IDS
from database import db, init_db
from keyboards import get_main_menu
from handlers.user import router as user_router
from handlers.admin import router as admin_router
from i18n import _
from middleware import AntiSpamMiddleware
from anti_spam import anti_spam

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Создание бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрация middleware
dp.message.middleware(AntiSpamMiddleware(anti_spam))

# Регистрация роутеров
dp.include_router(user_router)
dp.include_router(admin_router)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Команда /start"""
    user_id = message.from_user.id
    
    # Убеждаемся, что пользователь существует в базе
    user = await db.get_user(user_id)
    if not user:
        await db.add_user(
            user_id, 
            message.from_user.username, 
            message.from_user.first_name
        )
    
    is_admin = user_id in ADMIN_IDS
    
    await message.answer(
        _("welcome.title", user_id=user_id) + "\n\n" + _("welcome.description", user_id=user_id),
        reply_markup=get_main_menu(is_admin=is_admin, user_id=user_id),
        parse_mode='HTML'
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    # Убеждаемся, что пользователь существует в базе
    user = await db.get_user(user_id)
    if not user:
        await db.add_user(
            user_id, 
            message.from_user.username, 
            message.from_user.first_name
        )
    
    from keyboards import get_enhanced_admin_keyboard
    await message.answer(
        "🔧 <b>Улучшенная админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_enhanced_admin_keyboard(),
        parse_mode='HTML'
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    help_text = """📖 <b>Помощь</b>

<b>Доступные команды:</b>
/start - Запуск бота
/help - Помощь
/admin - Админ-панель (только для администраторов)
/reload - Перезагрузка бота (только для разработки)

<b>Как сделать заказ:</b>
1️⃣ Откройте каталог товаров
2️⃣ Добавьте нужные товары в корзину
3️⃣ Перейдите в корзину и оформите заказ
4️⃣ Выберите зону доставки
5️⃣ Укажите контактные данные
6️⃣ Получите реквизиты для оплаты
7️⃣ Оплатите и пришлите скриншот
8️⃣ Дождитесь подтверждения и доставки

<b>Способы оплаты:</b>
💳 Банковская карта
📱 СБП (быстрые платежи)
💰 Наличные при получении (в некоторых зонах)

<b>Служба поддержки:</b>
💬 Используйте кнопку "Связь" в главном меню"""

    await message.answer(help_text, parse_mode='HTML')

@dp.message(Command("reload"))
async def cmd_reload(message: Message):
    """Команда для перезагрузки бота (только для разработки)"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к этой команде")
        return
    
    await message.answer("🔄 Перезагружаю модули...")
    
    try:
        # Перезагружаем модули
        import importlib
        import sys
        
        modules_to_reload = [
            'handlers.user',
            'handlers.admin', 
            'keyboards',
            'database',
            'config',
            'i18n'
        ]
        
        for module_name in modules_to_reload:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                logger.info(f"Перезагружен модуль: {module_name}")
        
        await message.answer("✅ Модули перезагружены успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка при перезагрузке: {e}")
        await message.answer(f"❌ Ошибка при перезагрузке: {e}")

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="Bot is running in development mode!")

async def shutdown_handler():
    """Обработчик корректного завершения работы"""
    logger.info("Получен сигнал завершения работы...")
    try:
        await db.close_pool()
    except:
        pass
    try:
        await bot.session.close()
    except:
        pass
    logger.info("Завершение работы завершено")

async def main():
    """Запуск бота в режиме разработки"""
    try:
        logger.info("🔥 Запуск бота в режиме разработки...")
        logger.info("Инициализация базы данных...")
        await init_db()
        
        # Удаляем webhook перед началом работы
        logger.info("Очистка webhook...")
        await bot.delete_webhook(drop_pending_updates=True)
        
        await asyncio.sleep(1)
        
        logger.info("🚀 Запуск в режиме polling...")
        logger.info("💡 Используйте /reload для перезагрузки модулей")
        await dp.start_polling(bot, drop_pending_updates=True)
            
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        raise
    finally:
        await shutdown_handler()

if __name__ == "__main__":
    # Обработка сигналов для корректного завершения
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, f: asyncio.create_task(shutdown_handler()))
    
    asyncio.run(main())