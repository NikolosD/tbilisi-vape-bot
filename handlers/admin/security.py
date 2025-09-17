from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
import time

from config import ADMIN_IDS
from database import db
from filters.admin import admin_filter

router = Router()

@router.message(F.text == "/antispam", admin_filter)
async def show_antispam_menu(message: Message):
    """Показать меню анти-спам системы"""
    try:
        from anti_spam import anti_spam
        blocked_count = len(anti_spam.get_blocked_users())
        total_users = len(anti_spam.user_stats)
        
        text = f"""🛡 <b>Анти-спам система</b>

📊 <b>Статистика:</b>
• Всего пользователей: {total_users}
• Заблокированных: {blocked_count}

⚙️ <b>Настройки:</b>
• Макс. сообщений/мин: {anti_spam.MAX_MESSAGES_PER_MINUTE}
• Макс. сообщений/час: {anti_spam.MAX_MESSAGES_PER_HOUR}
• Мин. интервал: {anti_spam.MIN_MESSAGE_INTERVAL}с
• Порог блокировки: {anti_spam.SPAM_THRESHOLD}

<b>Команды:</b>
/blocked - список заблокированных
/unblock [ID] - разблокировать пользователя
/stats [ID] - статистика пользователя
/block [ID] - заблокировать пользователя"""

        await message.answer(text, parse_mode="HTML")
    except ImportError:
        await message.answer("❌ Модуль анти-спам недоступен")

@router.message(F.text == "/blocked", admin_filter)
async def show_blocked_users(message: Message):
    """Показать заблокированных пользователей"""
    try:
        from anti_spam import anti_spam
        blocked = anti_spam.get_blocked_users()
        
        if not blocked:
            await message.answer("✅ Заблокированных пользователей нет.")
            return
        
        text = "🚫 <b>Заблокированные пользователи:</b>\n\n"
        
        for user in blocked[:10]:
            user_id = user["user_id"]
            spam_score = user["spam_score"]
            warnings = user["warning_count"]
            
            if user["permanent"]:
                status = "Навсегда"
            else:
                remaining = user["remaining_time"]
                status = f"{remaining}с" if remaining > 0 else "Истекает"
            
            text += f"• ID: {user_id}\n"
            text += f"  Спам-счет: {spam_score}, Предупреждения: {warnings}\n"
            text += f"  Блокировка: {status}\n\n"
        
        if len(blocked) > 10:
            text += f"... и еще {len(blocked) - 10} пользователей"
        
        await message.answer(text, parse_mode="HTML")
    except ImportError:
        await message.answer("❌ Модуль анти-спам недоступен")

@router.message(F.text.startswith("/unblock "), admin_filter)
async def unblock_user_command(message: Message):
    """Разблокировать пользователя"""
    try:
        from anti_spam import anti_spam
        user_id = int(message.text.split()[1])
        anti_spam.unblock_user(user_id)
        await message.answer(f"✅ Пользователь {user_id} разблокирован.")
    except ImportError:
        await message.answer("❌ Модуль анти-спам недоступен")
    except (ValueError, IndexError):
        await message.answer("❌ Использование: /unblock [ID пользователя]")

@router.message(F.text.startswith("/block "), admin_filter)
async def block_user_command(message: Message):
    """Заблокировать пользователя"""
    try:
        from anti_spam import anti_spam
        user_id = int(message.text.split()[1])
        anti_spam.block_user(user_id, 0, "Заблокирован администратором")
        await message.answer(f"🚫 Пользователь {user_id} заблокирован.")
    except ImportError:
        await message.answer("❌ Модуль анти-спам недоступен")
    except (ValueError, IndexError):
        await message.answer("❌ Использование: /block [ID пользователя]")

@router.message(F.text.startswith("/stats "), admin_filter)
async def show_user_stats(message: Message):
    """Показать статистику пользователя"""
    try:
        from anti_spam import anti_spam
        user_id = int(message.text.split()[1])
        stats = anti_spam.get_user_stats(user_id)
        
        text = f"""📊 <b>Статистика пользователя {user_id}:</b>

💬 Сообщений всего: {stats["message_count"]}
🕐 За последний час: {stats["messages_last_hour"]}
🎯 Спам-счет: {stats["spam_score"]}
⚠️ Предупреждений: {stats["warning_count"]}

🚫 Заблокирован: {"Да" if stats["is_blocked"] else "Нет"}"""
        
        if stats["remaining_block_time"] > 0:
            text += f"\n⏰ Осталось: {stats['remaining_block_time']}с"
        
        await message.answer(text, parse_mode="HTML")
    except ImportError:
        await message.answer("❌ Модуль анти-спам недоступен")
    except (ValueError, IndexError):
        await message.answer("❌ Использование: /stats [ID пользователя]")

@router.message(F.text == "/security", admin_filter)
async def show_security_stats(message: Message):
    """Показать статистику безопасности"""
    try:
        from security_monitor import security_monitor
        stats = security_monitor.get_security_stats()
        
        text = f"""🛡️ <b>Статистика безопасности</b>

📊 <b>За последний час:</b>
• События: {stats["events_last_hour"]}
• Блокировки: {stats["blocks_last_hour"]}
• Сообщения: {stats["messages_last_hour"]}

📈 <b>Общая статистика:</b>
• Всего событий: {stats["total_events"]}
• Заблокированных пользователей: {stats["unique_blocked_users"]}

⚠️ <b>Серьезность событий:</b>
• Низкая: {stats["severity_breakdown"]["low"]}
• Средняя: {stats["severity_breakdown"]["medium"]}
• Высокая: {stats["severity_breakdown"]["high"]}
• Критическая: {stats["severity_breakdown"]["critical"]}

Команды:
/events - последние события
/ddos - проверка DDoS
/cleanup - очистка старых данных"""
        
        await message.answer(text, parse_mode="HTML")
    except ImportError:
        await message.answer("❌ Модуль мониторинга безопасности недоступен")

@router.message(F.text == "/events", admin_filter)
async def show_recent_events(message: Message):
    """Показать последние события безопасности"""
    try:
        from security_monitor import security_monitor
        events = security_monitor.get_recent_events(10)
        
        if not events:
            await message.answer("📋 Последние события отсутствуют")
            return
        
        text = "📋 <b>Последние события безопасности:</b>\n\n"
        
        for event in reversed(events[-10:]):
            severity_emoji = {
                "low": "🟢",
                "medium": "🟡", 
                "high": "🟠",
                "critical": "🔴"
            }
            
            time_str = time.strftime("%H:%M:%S", time.localtime(event.timestamp))
            text += f"{severity_emoji.get(event.severity, '⚪')} <code>{time_str}</code> "
            text += f"<b>{event.event_type}</b>\n"
            text += f"👤 User: {event.user_id}\n"
            text += f"📝 {event.details}\n\n"
        
        await message.answer(text, parse_mode="HTML")
    except ImportError:
        await message.answer("❌ Модуль мониторинга безопасности недоступен")

@router.message(F.text == "/ddos", admin_filter)
async def check_ddos(message: Message):
    """Проверить активность на предмет DDoS"""
    try:
        from security_monitor import security_monitor
        is_ddos = security_monitor.detect_ddos_attempt()
        
        if is_ddos:
            text = "🚨 <b>ВНИМАНИЕ!</b> Обнаружена подозрительная активность!\n\n"
            text += "Возможная DDoS атака или массовый спам.\n"
            text += "Рекомендуется усилить защиту."
        else:
            text = "✅ <b>Система в норме</b>\n\n"
            text += "Подозрительной активности не обнаружено."
        
        await message.answer(text, parse_mode="HTML")
    except ImportError:
        await message.answer("❌ Модуль мониторинга безопасности недоступен")

@router.message(F.text == "/cleanup", admin_filter) 
async def cleanup_security_data(message: Message):
    """Очистить старые данные безопасности"""
    try:
        from security_monitor import security_monitor
        security_monitor.cleanup_old_data()
        await message.answer("✅ Старые данные безопасности очищены")
    except ImportError:
        await message.answer("❌ Модуль мониторинга безопасности недоступен")

@router.message(F.text == "/topblocked", admin_filter)
async def show_top_blocked(message: Message):
    """Показать топ заблокированных пользователей"""
    try:
        from security_monitor import security_monitor
        top_users = security_monitor.get_top_blocked_users(10)
        
        if not top_users:
            await message.answer("📋 Нет заблокированных пользователей")
            return
        
        text = "📊 <b>Топ заблокированных пользователей:</b>\n\n"
        
        for i, user_data in enumerate(top_users, 1):
            text += f"{i}. 👤 ID: <code>{user_data['user_id']}</code>\n"
            text += f"   🚫 Блокировок: {user_data['block_count']}\n\n"
        
        await message.answer(text, parse_mode="HTML")
    except ImportError:
        await message.answer("❌ Модуль мониторинга безопасности недоступен")