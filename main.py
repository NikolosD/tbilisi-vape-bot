import asyncio
import logging
import signal
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web, ClientSession
import os

from config import BOT_TOKEN, ADMIN_IDS
from database import db, init_db
from keyboards import get_main_menu
from handlers.user import router as user_router
from handlers.admin import router as admin_router
from i18n import _

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключение роутеров
dp.include_router(user_router)
dp.include_router(admin_router)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Команда /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Добавляем пользователя в базу данных
    await db.add_user(user_id, username, first_name)
    
    # Проверяем, является ли пользователь администратором
    is_admin = user_id in ADMIN_IDS
    
    welcome_text = f"""{_('welcome.title', user_id=user_id)}

{_('welcome.description', user_id=user_id)}

Выберите действие в меню ниже:"""
    
    await message.answer(
        welcome_text,
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
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
    
    from keyboards import get_admin_keyboard
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode='HTML'
    )

@dp.message(F.text == "🔧 Админ панель")
async def admin_panel_button(message: Message):
    """Обработчик кнопки 'Админ панель' в главном меню"""
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
    
    from keyboards import get_admin_keyboard
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard(),
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

async def health_check(request):
    """Health check endpoint для Render"""
    return web.Response(text="Bot is running!")

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
    """Запуск бота"""
    # Обработка сигналов для корректного завершения
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, f: asyncio.create_task(shutdown_handler()))
    
    try:
        logger.info("🔥 Запуск Tbilisi VAPE Shop Bot...")
        logger.info("Инициализация базы данных...")
        await init_db()
        
        # Удаляем webhook перед началом работы
        logger.info("Очистка webhook...")
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Небольшая задержка для избежания конфликтов
        await asyncio.sleep(2)
        
        # Запуск веб-сервера для Render
        if os.getenv('RENDER'):
            logger.info("🚀 Запуск в режиме веб-сервиса для Render...")
            app = web.Application()
            app.router.add_get('/', health_check)
            app.router.add_get('/health', health_check)
            
            # Запуск бота в фоне
            asyncio.create_task(dp.start_polling(bot, drop_pending_updates=True))
            
            # Запуск веб-сервера
            port = int(os.getenv('PORT', 10000))
            logger.info(f"🌐 Веб-сервер запущен на порту {port}")
            await web._run_app(app, host='0.0.0.0', port=port)
        else:
            logger.info("🚀 Запуск в режиме polling...")
            await dp.start_polling(bot, drop_pending_updates=True)
            
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        raise
    finally:
        await shutdown_handler()

if __name__ == "__main__":
    asyncio.run(main())