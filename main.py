import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
from database import db
from keyboards import get_main_menu
from handlers.user import router as user_router
from handlers.admin import router as admin_router

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
    db.add_user(user_id, username, first_name)
    
    welcome_text = """🔥 <b>Добро пожаловать в Tbilisi VAPE Shop!</b>

🚬 Лучшие одноразовые электронные сигареты в Тбилиси
🚀 Быстрая доставка по всему городу
💯 Только оригинальная продукция
💰 Лучшие цены в городе

Выберите действие в меню ниже:"""
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu(),
        parse_mode='HTML'
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
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

async def main():
    """Запуск бота"""
    try:
        logger.info("Запуск бота...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())