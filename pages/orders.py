"""
Страница заказов пользователя с улучшенным функционалом
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .base import BasePage
from database import db
from keyboards import get_orders_keyboard, get_order_details_keyboard
from models import OrderStatus
from components.pagination import pagination
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from i18n import _


class OrdersPage(BasePage):
    """Улучшенная страница заказов с фильтрацией и поиском"""
    
    def __init__(self):
        super().__init__('orders')
    
    async def render(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Отрендерить страницу заказов"""
        order_id = kwargs.get('order_id')
        page = kwargs.get('page', 1)
        status_filter = kwargs.get('status_filter', 'all')
        search_query = kwargs.get('search_query')
        
        if order_id:
            return await self._render_order_details(user_id, order_id)
        else:
            return await self._render_orders_list(user_id, page, status_filter, search_query)
    
    async def _render_orders_list(self, user_id: int, page: int = 1, status_filter: str = 'all', search_query: Optional[str] = None) -> Dict[str, Any]:
        """Отрендерить список заказов с фильтрацией и поиском"""
        
        # Получаем статистику заказов
        stats = await db.get_user_orders_stats(user_id)
        
        # Получаем заказы с фильтрацией
        orders = await db.get_user_orders(user_id, status_filter, search_query)
        
        if not orders and not search_query:
            from keyboards import get_back_to_menu_keyboard
            return {
                'text': f"📋 <b>{self.get_title(user_id)}</b>\n\n{self.get_empty_message(user_id)}",
                'keyboard': get_back_to_menu_keyboard(user_id=user_id)
            }
        
        # Формируем заголовок с фильтрами
        text = f"📋 <b>Мои заказы</b>\n"
        
        # Добавляем информацию о поиске
        if search_query:
            text += f"🔍 Поиск: <i>{search_query}</i>\n"
        
        # Показываем статистику
        if not search_query:
            text += f"📊 Всего: {stats['total']} | Активных: {stats['active']} | Завершено: {stats['completed']} | Отменено: {stats['cancelled']}\n"
        
        text += "\n"
        
        if not orders:
            text += "❌ Заказы не найдены\n\n"
        else:
            # Используем компонент пагинации
            pagination_info = pagination.paginate(orders, page)
            
            # Добавляем информацию о странице только если есть несколько страниц
            if pagination_info.get('total_pages', 1) > 1:
                text += pagination.get_page_info_text(pagination_info, user_id)
            
            # Отображаем заказы текущей страницы
            for order in pagination_info.get('items', orders):
                text += await self._format_order_preview(order, user_id)
        
        # Создаем клавиатуру
        keyboard = await self._create_orders_keyboard(orders, page, status_filter, search_query, stats, user_id)
        
        return {
            'text': text,
            'keyboard': keyboard
        }
    
    async def _render_order_details(self, user_id: int, order_id: int) -> Dict[str, Any]:
        """Отрендерить детализированную информацию о заказе"""
        order = await db.get_order(order_id)
        if not order or order.user_id != user_id:
            return await self._render_orders_list(user_id)
        
        status_emoji = self._get_status_emoji(order.status)
        status_text = self._get_status_text(order.status, user_id)
        
        # Заголовок
        text = f"🧾 <b>Заказ #{order.order_number}</b>\n\n"
        
        # Статус с цветовым индикатором
        status_indicator = "🟢" if order.status in ['paid', 'shipping', 'delivered'] else "🟡" if order.status in ['waiting_payment', 'payment_check'] else "🔴"
        text += f"📊 <b>Статус:</b> {status_indicator} {status_text}\n"
        
        # Дата и время с учетом временной зоны Грузии (GMT+4)
        from datetime import timezone, timedelta
        tbilisi_tz = timezone(timedelta(hours=4))
        order_time = order.created_at.replace(tzinfo=timezone.utc).astimezone(tbilisi_tz)
        created_time = order_time.strftime('%d.%m.%Y в %H:%M')
        text += f"📅 <b>Создан:</b> {created_time}\n\n"
        
        # Информация о резерве для заказов в ожидании оплаты
        if order.status == 'waiting_payment':
            reservation = await db.get_order_reservation(order.id)
            if reservation:
                if reservation['minutes_left'] > 0:
                    text += f"⏰ <b>Резерв истекает через:</b> {reservation['minutes_left']} мин\n"
                else:
                    text += f"⚠️ <b>Резерв товаров истек</b>\n"
            text += "\n"
        
        # Контактная информация
        if order.phone:
            text += f"📞 <b>Телефон:</b> {order.phone}\n"
        if order.address:
            text += f"📍 <b>Адрес доставки:</b> {order.address}\n"
        if order.latitude and order.longitude:
            text += f"🗺️ <b>Координаты:</b> {order.latitude:.6f}, {order.longitude:.6f}\n"
        text += "\n"
        
        # Товары
        text += f"📦 <b>Товары в заказе:</b>\n"
        products = order.products_data
        items_total = 0
        for i, product in enumerate(products, 1):
            item_cost = product['price'] * product['quantity']
            items_total += item_cost
            text += f"{i}. {product['name']}\n"
            text += f"   └─ {product['quantity']} шт × {product['price']}₾ = {item_cost}₾\n\n"
        
        # Итоговая стоимость
        text += f"💰 <b>Стоимость товаров:</b> {items_total}₾\n"
        text += f"🚚 <b>Стоимость доставки:</b> {order.delivery_price}₾\n"
        text += f"💳 <b>Итого к оплате:</b> {order.total_price}₾\n"
        
        return {
            'text': text,
            'keyboard': await self._create_order_details_keyboard(order, user_id)
        }
    
    async def _create_order_details_keyboard(self, order, user_id: int) -> InlineKeyboardMarkup:
        """Создание клавиатуры для детализации заказа"""
        keyboard = []
        
        # Действия в зависимости от статуса
        if order.status == 'waiting_payment':
            keyboard.append([
                InlineKeyboardButton(text="📸 Отправить чек", callback_data=f"resend_screenshot_{order.order_number}"),
                InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel_order_{order.id}")
            ])
        elif order.status == 'payment_check':
            keyboard.append([
                InlineKeyboardButton(text="📸 Обновить чек", callback_data=f"resend_screenshot_{order.order_number}")
            ])
        elif order.status == 'delivered':
            keyboard.append([
                InlineKeyboardButton(text="🔄 Повторить заказ", callback_data=f"repeat_order_{order.id}")
            ])
        
        # Кнопка связи с поддержкой для всех заказов
        keyboard.append([
            InlineKeyboardButton(text="💬 Связаться с поддержкой", callback_data=f"support_order_{order.id}")
        ])
        
        # Кнопки навигации
        keyboard.append([
            InlineKeyboardButton(text="⬅️ К списку заказов", callback_data="my_orders"),
            InlineKeyboardButton(text="🔄 Обновить", callback_data=f"order_{order.id}")
        ])
        
        keyboard.append([
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def _get_status_emoji(self, status) -> str:
        """Получить эмодзи для статуса заказа"""
        # Преобразуем status в строку для сопоставления
        if hasattr(status, 'value'):
            status_str = status.value
        else:
            status_str = status
            
        status_emojis = {
            "waiting_payment": "⏳",
            "payment_check": "💰",
            "paid": "✅",
            "shipping": "🚚",
            "delivered": "📦",
            "cancelled": "❌"
        }
        return status_emojis.get(status_str, "❓")
    
    def _get_status_text(self, status, user_id: int) -> str:
        """Получить текст статуса заказа"""
        # status может быть как строкой, так и enum, обрабатываем оба случая
        if hasattr(status, 'value'):
            status_value = status.value
        else:
            status_value = status
        return _(f"orders.status_{status_value}", user_id=user_id)
    
    async def _format_order_preview(self, order, user_id: int) -> str:
        """Форматирование превью заказа с улучшенной информацией"""
        status_emoji = self._get_status_emoji(order.status)
        status_text = self._get_status_text(order.status, user_id)
        
        # Отображение времени с учетом временной зоны Грузии (GMT+4)
        from datetime import timezone, timedelta
        tbilisi_tz = timezone(timedelta(hours=4))
        order_time = order.created_at.replace(tzinfo=timezone.utc).astimezone(tbilisi_tz)
        created_time = order_time.strftime('%d.%m.%Y %H:%M')
        
        text = f"┌─ {status_emoji} <b>№{order.order_number}</b> ─ {status_text}\n"
        text += f"│ 📅 {created_time}\n"
        text += f"│ 💰 {order.total_price}₾\n"
        
        # Добавляем информацию о резерве для активных заказов
        if order.status == 'waiting_payment':
            reservation = await db.get_order_reservation(order.id)
            if reservation and reservation['minutes_left'] > 0:
                text += f"│ ⏰ Резерв: {reservation['minutes_left']} мин\n"
            else:
                text += f"│ ⚠️ Резерв истек\n"
        
        # Показываем превью товаров (первые 2)
        products = order.products_data
        if products:
            text += f"│ 📦 "
            preview_items = products[:2]
            for i, product in enumerate(preview_items):
                if i > 0:
                    text += ", "
                text += f"{product['name']} x{product['quantity']}"
            if len(products) > 2:
                text += f" и еще {len(products) - 2}"
            text += "\n"
        
        text += f"└─────────────────────\n\n"
        
        return text
    
    async def _create_orders_keyboard(self, orders, page: int, status_filter: str, search_query: Optional[str], stats: dict, user_id: int) -> InlineKeyboardMarkup:
        """Создание клавиатуры для страницы заказов"""
        keyboard = []
        
        # Кнопки фильтров (только если нет поиска)
        if not search_query:
            filter_row1 = []
            filter_row2 = []
            
            # Все заказы
            button_text = f"🗂️ Все ({stats['total']})"
            if status_filter == 'all':
                button_text = f"✅ {button_text}"
            filter_row1.append(InlineKeyboardButton(text=button_text, callback_data="orders_filter_all"))
            
            # Активные заказы
            button_text = f"🟢 Активные ({stats['active']})"
            if status_filter == 'active':
                button_text = f"✅ {button_text}"
            filter_row1.append(InlineKeyboardButton(text=button_text, callback_data="orders_filter_active"))
            
            # Завершенные заказы
            button_text = f"✅ Завершено ({stats['completed']})"
            if status_filter == 'completed':
                button_text = f"✅ {button_text}"
            filter_row2.append(InlineKeyboardButton(text=button_text, callback_data="orders_filter_completed"))
            
            # Отмененные заказы
            button_text = f"❌ Отменено ({stats['cancelled']})"
            if status_filter == 'cancelled':
                button_text = f"✅ {button_text}"
            filter_row2.append(InlineKeyboardButton(text=button_text, callback_data="orders_filter_cancelled"))
            
            keyboard.append(filter_row1)
            keyboard.append(filter_row2)
        
        # Кнопка поиска
        search_text = "🔍 Поиск по номеру" if not search_query else "🔄 Сбросить поиск"
        search_callback = "orders_search" if not search_query else "orders_filter_all"
        keyboard.append([InlineKeyboardButton(text=search_text, callback_data=search_callback)])
        
        # Разделитель
        if orders:
            keyboard.append([InlineKeyboardButton(text="─── Заказы ───", callback_data="noop")])
        
        # Кнопки заказов с пагинацией
        if orders:
            pagination_info = pagination.paginate(orders, page)
            
            # Кнопки заказов
            for order in pagination_info['items']:
                status_emoji = self._get_status_emoji(order.status)
                button_text = f"{status_emoji} №{order.order_number} - {order.total_price}₾"
                keyboard.append([InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"order_{order.id}"
                )])
            
            # Кнопки пагинации
            if pagination_info.get('total_pages', 1) > 1:
                pagination_row = []
                if pagination_info.get('has_prev', False):
                    prev_page = pagination_info.get('page', 1) - 1
                    callback_data = f"orders_page_{prev_page}"
                    if status_filter != 'all':
                        callback_data += f"_{status_filter}"
                    if search_query:
                        callback_data += f"_search_{search_query}"
                    pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=callback_data))
                
                current_page = pagination_info.get('page', 1)
                total_pages = pagination_info.get('total_pages', 1)
                pagination_row.append(InlineKeyboardButton(
                    text=f"{current_page}/{total_pages}", 
                    callback_data="noop"
                ))
                
                if pagination_info.get('has_next', False):
                    next_page = pagination_info.get('page', 1) + 1
                    callback_data = f"orders_page_{next_page}"
                    if status_filter != 'all':
                        callback_data += f"_{status_filter}"
                    if search_query:
                        callback_data += f"_search_{search_query}"
                    pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=callback_data))
                
                keyboard.append(pagination_row)
        
        # Кнопки управления
        control_row = []
        
        # Кнопка обновления
        callback_data = f"orders_refresh"
        if status_filter != 'all':
            callback_data += f"_{status_filter}"
        if search_query:
            callback_data += f"_search_{search_query}"
        control_row.append(InlineKeyboardButton(text="🔄 Обновить", callback_data=callback_data))
        
        # Кнопка связи с поддержкой
        control_row.append(InlineKeyboardButton(text="💬 Поддержка", callback_data="contact_support"))
        
        keyboard.append(control_row)
        
        # Кнопка главного меню
        keyboard.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)