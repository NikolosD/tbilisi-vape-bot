from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime, timedelta

from database import db
from filters.admin import admin_filter
from keyboards import get_admin_keyboard
from utils.safe_operations import safe_edit_message

router = Router()

@router.callback_query(F.data == "admin_stats", admin_filter)
async def show_stats(callback: CallbackQuery):
    """Показать статистику"""
    all_orders = await db.fetchall("SELECT status FROM orders")
    users_count = (await db.fetchone("SELECT COUNT(*) FROM users"))[0]
    products_count = (await db.fetchone("SELECT COUNT(*) FROM products WHERE in_stock = true"))[0]
    
    status_counts = {
        'waiting_payment': 0,
        'payment_check': 0,
        'paid': 0,
        'shipping': 0,
        'delivered': 0,
        'cancelled': 0
    }
    
    for order in all_orders:
        status = order[0]
        if status in status_counts:
            status_counts[status] += 1
    
    delivered_orders = await db.fetchall("SELECT total_price FROM orders WHERE status = 'delivered'")
    total_revenue = sum(order[0] for order in delivered_orders)
    
    # Статистика за сегодня
    today = datetime.now().date()
    today_orders = await db.fetchall(
        "SELECT COUNT(*), SUM(total_price) FROM orders WHERE DATE(created_at) = $1",
        today
    )
    today_count = today_orders[0][0] if today_orders[0][0] else 0
    today_revenue = today_orders[0][1] if today_orders[0][1] else 0
    
    # Статистика за неделю
    week_ago = today - timedelta(days=7)
    week_orders = await db.fetchall(
        "SELECT COUNT(*), SUM(total_price) FROM orders WHERE DATE(created_at) >= $1",
        week_ago
    )
    week_count = week_orders[0][0] if week_orders[0][0] else 0
    week_revenue = week_orders[0][1] if week_orders[0][1] else 0
    
    # Статистика за месяц
    month_ago = today - timedelta(days=30)
    month_orders = await db.fetchall(
        "SELECT COUNT(*), SUM(total_price) FROM orders WHERE DATE(created_at) >= $1",
        month_ago
    )
    month_count = month_orders[0][0] if month_orders[0][0] else 0
    month_revenue = month_orders[0][1] if month_orders[0][1] else 0

    stats_text = f"""📊 <b>Статистика магазина</b>

👥 <b>Пользователи:</b> {users_count}
📦 <b>Товары в наличии:</b> {products_count}

📋 <b>Заказы по статусам:</b>
⏳ Ожидают оплаты: {status_counts['waiting_payment']}
💰 На проверке: {status_counts['payment_check']}
✅ Оплачены: {status_counts['paid']}
🚚 Отправлены: {status_counts['shipping']}
✅ Доставлены: {status_counts['delivered']}
❌ Отменены: {status_counts['cancelled']}

📈 <b>Статистика продаж:</b>
🏆 Всего заработано: {total_revenue:.2f}₾

📅 <b>За сегодня:</b>
• Заказов: {today_count}
• Выручка: {today_revenue:.2f}₾

📅 <b>За неделю:</b>
• Заказов: {week_count}
• Выручка: {week_revenue:.2f}₾

📅 <b>За месяц:</b>
• Заказов: {month_count}
• Выручка: {month_revenue:.2f}₾"""

    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_keyboard(),
        parse_mode='HTML'
    )