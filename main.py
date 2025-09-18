import asyncio
import logging
import signal
import sys
import subprocess
import os

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("⚠️ psutil не установлен. Автоматическое завершение других экземпляров недоступно.")

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web, ClientSession
import os

from config import BOT_TOKEN, ADMIN_IDS
from database import db, init_db
from keyboards import get_main_menu, get_main_menu_inline
from handlers.user import router as user_router
from handlers.admin import admin_router
from admin_management import router as admin_management_router
from i18n import _
from middleware import AntiSpamMiddleware
from anti_spam import anti_spam

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Настройка анти-спам системы
anti_spam.set_admin_ids(ADMIN_IDS)

# Подключение middleware
dp.message.middleware(AntiSpamMiddleware())
dp.callback_query.middleware(AntiSpamMiddleware())

# Подключение роутеров
dp.include_router(user_router)
dp.include_router(admin_management_router)  # Важно: подключаем ДО admin_router
dp.include_router(admin_router)

# ReplyKeyboard убран - теперь используем только inline кнопки

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Команда /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Добавляем пользователя в базу данных
    await db.add_user(user_id, username, first_name)
    
    # Устанавливаем язык по умолчанию для новых пользователей
    from i18n import i18n
    if user_id not in i18n.user_languages:
        i18n.set_language('ru', user_id)
    
    # Очищаем старые сообщения при старте
    from message_manager import message_manager
    await message_manager.delete_user_message(message.bot, user_id)
    
    # Проверяем, является ли пользователь администратором
    is_admin = user_id in ADMIN_IDS
    
    welcome_text = f"""{_('welcome.title', user_id=user_id)}

{_('welcome.description', user_id=user_id)}

{_('common.select_action', user_id=user_id)}"""
    
    sent_message = await message.answer(
        welcome_text,
        reply_markup=get_main_menu_inline(is_admin=is_admin, user_id=user_id),
        parse_mode='HTML'
    )
    
    # Сохраняем ID отправленного сообщения
    message_manager.set_user_message(user_id, sent_message.message_id, 'main')

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
    
    from keyboards import get_enhanced_admin_keyboard
    await message.answer(
        "🔧 <b>Улучшенная админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_enhanced_admin_keyboard(user_id=user_id),
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
    
    from keyboards import get_enhanced_admin_keyboard
    await message.answer(
        "🔧 <b>Улучшенная админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_enhanced_admin_keyboard(user_id=user_id),
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

# ТЕСТОВЫЙ обработчик рассылки в main.py (ВРЕМЕННО)
@dp.message()
async def debug_all_messages(message: Message, state: FSMContext):
    """Глобальный обработчик для отладки всех сообщений"""
    from config import ADMIN_IDS
    
    # ReplyKeyboard больше не используется - все кнопки inline
    
    # Логируем только сообщения от админов для уменьшения спама
    if message.from_user.id in ADMIN_IDS:
        current_state = await state.get_state()
        data = await state.get_data()
        print(f"🌐 GLOBAL DEBUG: Unhandled admin message from {message.from_user.id}")
        print(f"    Text: '{message.text}'")
        print(f"    State: {current_state}")
        print(f"    Data: {data}")
        
        # Используем красивую логику рассылки из communication.py
        if current_state and 'waiting_broadcast_message' in str(current_state):
            print(f"🚀 BEAUTIFUL BROADCAST: Processing broadcast with branding!")
            
            from handlers.admin.communication import process_broadcast_logic
            await process_broadcast_logic(message, state)
            return

def kill_other_bot_instances():
    """Завершить другие экземпляры бота"""
    if not PSUTIL_AVAILABLE:
        logger.warning("⚠️ psutil недоступен. Используем улучшенный альтернативный метод...")
        try:
            # Улучшенный альтернативный метод для Render.com и других серверов
            if sys.platform == "darwin" or sys.platform.startswith("linux"):
                # Ищем все Python процессы с main.py
                result = subprocess.run(
                    ["pgrep", "-f", "python.*main.py"], 
                    capture_output=True, 
                    text=True
                )
                if result.stdout:
                    pids = result.stdout.strip().split('\n')
                    current_pid = str(os.getpid())
                    killed_count = 0
                    
                    for pid in pids:
                        if pid and pid != current_pid:
                            logger.info(f"🔪 Завершаем старый экземпляр бота (PID: {pid})")
                            # Сначала пробуем мягкое завершение
                            subprocess.run(["kill", "-TERM", pid], capture_output=True)
                            killed_count += 1
                    
                    if killed_count > 0:
                        logger.info(f"⏳ Ждем завершения {killed_count} процессов...")
                        import time
                        time.sleep(5)  # Увеличили время ожидания
                        
                        # Проверяем что процессы завершились
                        result2 = subprocess.run(
                            ["pgrep", "-f", "python.*main.py"], 
                            capture_output=True, 
                            text=True
                        )
                        if result2.stdout:
                            remaining_pids = [p for p in result2.stdout.strip().split('\n') if p and p != current_pid]
                            if remaining_pids:
                                logger.warning(f"🔴 Принудительно завершаем оставшиеся процессы: {remaining_pids}")
                                for pid in remaining_pids:
                                    subprocess.run(["kill", "-KILL", pid], capture_output=True)
                                time.sleep(2)
                        
                        logger.info("✅ Завершение других экземпляров выполнено")
                    else:
                        logger.info("✅ Других экземпляров не найдено")
                else:
                    logger.info("✅ Других экземпляров не найдено")
            else:
                logger.info("💡 Платформа не поддерживается для автоматического завершения")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось завершить другие экземпляры: {e}")
            # Даже если не удалось, продолжаем запуск
        return
    
    current_pid = os.getpid()
    killed_count = 0
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Проверяем процессы Python
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline']
                    if cmdline and len(cmdline) > 1:
                        # Ищем процессы, запускающие main.py этого бота
                        if 'main.py' in ' '.join(cmdline) and proc.info['pid'] != current_pid:
                            logger.info(f"🔪 Завершаем старый экземпляр бота (PID: {proc.info['pid']})")
                            proc.terminate()
                            killed_count += 1
                            
                            # Ждем 2 секунды и принудительно убиваем если нужно
                            try:
                                proc.wait(timeout=2)
                            except psutil.TimeoutExpired:
                                proc.kill()
                                logger.info(f"💀 Принудительно завершен процесс {proc.info['pid']}")
                                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при завершении процессов: {e}")
    
    if killed_count > 0:
        logger.info(f"✅ Завершено {killed_count} старых экземпляров бота")
        # Небольшая пауза для освобождения ресурсов
        import time
        time.sleep(3)
    else:
        logger.info("✅ Других экземпляров бота не найдено")

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
        
        # Завершаем другие экземпляры бота
        logger.info("🔍 Поиск и завершение других экземпляров бота...")
        kill_other_bot_instances()
        logger.info("Инициализация базы данных...")
        await init_db()
        
        # Синхронизируем админов из БД
        logger.info("Синхронизация администраторов...")
        db_admins = await db.get_all_admins()
        for admin in db_admins:
            admin_id = admin[0]
            if admin_id not in ADMIN_IDS:
                ADMIN_IDS.append(admin_id)
                logger.info(f"Добавлен админ из БД: {admin_id}")
        
        # Загружаем языки пользователей
        logger.info("Загрузка языков пользователей...")
        from i18n import i18n
        await i18n.load_user_languages_from_db()
        
        # Удаляем webhook перед началом работы и ждем
        logger.info("Очистка webhook...")
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook удален")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при удалении webhook: {e}")
        
        # Дополнительная пауза для избежания конфликтов на Render.com
        logger.info("⏳ Дополнительная пауза для избежания конфликтов...")
        await asyncio.sleep(5)
        
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