"""
Система уведомлений пользователей об изменениях заказов
"""
import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from typing import Dict, Any

logger = logging.getLogger(__name__)

class OrderNotificationSystem:
    """Система уведомлений о заказах"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self._status_emojis = {
            'waiting_payment': '⏳',
            'payment_check': '💰',
            'paid': '✅',
            'shipping': '🚚',
            'delivered': '📦',
            'cancelled': '❌'
        }
        self._status_texts = {
            'waiting_payment': 'Ожидает оплаты',
            'payment_check': 'Проверка оплаты',
            'paid': 'Оплачен и готовится к отправке',
            'shipping': 'Отправлен',
            'delivered': 'Доставлен',
            'cancelled': 'Отменен'
        }
    
    async def notify_status_change(self, order_id: int, old_status: str, new_status: str):
        """Уведомить пользователя об изменении статуса заказа"""
        try:
            order = await db.get_order(order_id)
            if not order:
                return
            
            # Не уведомляем о технических изменениях статуса
            if old_status == new_status:
                return
            
            status_emoji = self._status_emojis.get(new_status, '❓')
            status_text = self._status_texts.get(new_status, new_status)
            
            # Формируем сообщение в зависимости от статуса
            if new_status == 'payment_check':
                message_text = f"""📋 <b>Обновление заказа #{order.order_number}</b>

{status_emoji} <b>Статус изменен:</b> {status_text}

Ваш скриншот оплаты получен и проверяется администратором. Ожидайте подтверждения."""
                
            elif new_status == 'paid':
                message_text = f"""📋 <b>Заказ #{order.order_number} оплачен!</b>

{status_emoji} <b>Статус:</b> {status_text}

Ваш заказ подтвержден и передан в обработку. Скоро мы свяжемся с вами для уточнения деталей доставки."""
                
            elif new_status == 'shipping':
                message_text = f"""📋 <b>Заказ #{order.order_number} отправлен!</b>

{status_emoji} <b>Статус:</b> {status_text}

Ваш заказ отправлен и уже в пути. Ожидайте доставки по указанному адресу."""
                
            elif new_status == 'delivered':
                message_text = f"""📋 <b>Заказ #{order.order_number} доставлен!</b>

{status_emoji} <b>Статус:</b> {status_text}

Спасибо за покупку! Надеемся, вы остались довольны нашим сервисом. 

Будем рады видеть вас снова! ❤️"""
                
            elif new_status == 'cancelled':
                message_text = f"""📋 <b>Заказ #{order.order_number} отменен</b>

{status_emoji} <b>Статус:</b> {status_text}

К сожалению, ваш заказ был отменен. Если у вас есть вопросы, обратитесь к нашей поддержке."""
                
            else:
                message_text = f"""📋 <b>Обновление заказа #{order.order_number}</b>

{status_emoji} <b>Статус изменен:</b> {status_text}"""
            
            # Кнопки для взаимодействия
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Посмотреть заказ", callback_data=f"order_{order.id}")],
                [InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders")]
            ])
            
            # Добавляем дополнительные кнопки в зависимости от статуса
            if new_status == 'delivered':
                # Предлагаем повторить заказ
                keyboard.inline_keyboard.insert(-1, [
                    InlineKeyboardButton(text="🔄 Повторить заказ", callback_data=f"repeat_order_{order.id}")
                ])
            elif new_status == 'cancelled':
                # Предлагаем перейти в каталог
                keyboard.inline_keyboard.insert(-1, [
                    InlineKeyboardButton(text="🛍️ Каталог товаров", callback_data="catalog")
                ])
            
            # Отправляем уведомление
            await self.bot.send_message(
                chat_id=order.user_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            logger.info(f"Отправлено уведомление пользователю {order.user_id} об изменении статуса заказа #{order.order_number}: {old_status} -> {new_status}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об изменении статуса заказа {order_id}: {e}")
    
    async def notify_reservation_expiring(self, order_id: int, minutes_left: int):
        """Уведомить об истечении резерва товаров"""
        try:
            order = await db.get_order(order_id)
            if not order or order.status != 'waiting_payment':
                return
            
            if minutes_left <= 2:  # Уведомляем за 2 минуты до истечения
                message_text = f"""⚠️ <b>Резерв товаров истекает!</b>

📋 <b>Заказ:</b> #{order.order_number}
⏰ <b>Осталось:</b> {minutes_left} мин

Пожалуйста, отправьте скриншот оплаты как можно скорее, чтобы не потерять зарезервированные товары."""
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📸 Отправить чек", callback_data=f"resend_screenshot_{order.order_number}")],
                    [InlineKeyboardButton(text="📋 Посмотреть заказ", callback_data=f"order_{order.id}")]
                ])
                
                await self.bot.send_message(
                    chat_id=order.user_id,
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                
                logger.info(f"Отправлено уведомление пользователю {order.user_id} об истечении резерва заказа #{order.order_number}")
                
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об истечении резерва заказа {order_id}: {e}")

# Глобальный экземпляр системы уведомлений
notification_system = None

def init_notification_system(bot: Bot):
    """Инициализация системы уведомлений"""
    global notification_system
    notification_system = OrderNotificationSystem(bot)
    return notification_system