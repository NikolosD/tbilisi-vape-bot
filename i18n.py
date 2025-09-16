#!/usr/bin/env python3
"""
Система интернационализации (i18n) для бота
"""
import json
import os
from typing import Dict, Any

class I18n:
    def __init__(self, default_language: str = "ru"):
        self.default_language = default_language
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.current_language = default_language
        self.user_languages: Dict[int, str] = {}  # user_id -> language
        self.load_translations()
    
    def load_translations(self):
        """Загрузить переводы из файлов"""
        translations_dir = "translations"
        
        if not os.path.exists(translations_dir):
            os.makedirs(translations_dir)
            # Создаем базовый файл с русскими переводами
            self.create_default_translations()
        
        # Загружаем все файлы переводов
        for filename in os.listdir(translations_dir):
            if filename.endswith('.json'):
                language = filename[:-5]  # убираем .json
                filepath = os.path.join(translations_dir, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.translations[language] = json.load(f)
                except Exception as e:
                    print(f"Ошибка загрузки переводов для {language}: {e}")
    
    def create_default_translations(self):
        """Создать файл с русскими переводами по умолчанию"""
        default_translations = {
            # Главное меню
            "menu": {
                "catalog": "🛍 Каталог",
                "cart": "🛒 Корзина", 
                "orders": "📋 Мои заказы",
                "contact": "💬 Связь",
                "info": "ℹ️ Информация",
                "admin_panel": "🔧 Админ панель"
            },
            
            # Каталог
            "catalog": {
                "title": "🛍 <b>Каталог товаров</b>",
                "select_category": "Выберите категорию:",
                "select_product": "Выберите товар:",
                "empty": "📦 Каталог пока пуст. Скоро добавим товары!",
                "category_empty": "📦 В этой категории пока нет товаров"
            },
            
            # Товар
            "product": {
                "price": "💰 Цена: {price}₾",
                "description": "📝 Описание:",
                "in_cart": "🛒 Товар уже в корзине",
                "add_to_cart": "🛒 Добавить в корзину",
                "remove_from_cart": "❌ Удалить из корзины",
                "back_to_catalog": "🔙 К каталогу"
            },
            
            # Корзина
            "cart": {
                "title": "🛒 <b>Ваша корзина:</b>",
                "empty": "🛒 <b>Ваша корзина пуста</b>\n\nДобавьте товары из каталога!",
                "item": "• {name}\n  Количество: {quantity} шт.\n  Цена: {price}₾ × {quantity} = {total}₾\n",
                "total": "💰 <b>Итого: {total}₾</b>",
                "checkout": "📝 Оформить заказ",
                "clear": "🗑 Очистить корзину",
                "back_to_menu": "🔙 Главное меню",
                "item_removed": "✅ Товар удален из корзины",
                "item_added": "✅ Товар добавлен в корзину",
                "quantity_increased": "✅ Количество увеличено до {quantity}",
                "quantity_decreased": "✅ Количество уменьшено до {quantity}",
                "item_deleted": "🗑 Товар удален из корзины"
            },
            
            # Заказы
            "orders": {
                "title": "📋 <b>Ваши заказы:</b>",
                "select_order": "Выберите заказ для просмотра деталей:",
                "empty": "📋 <b>У вас пока нет заказов</b>\n\nСделайте первый заказ!",
                "details": "📋 <b>Детали заказа #{order_id}</b>",
                "products": "🛍 <b>Товары:</b>",
                "delivery": "🚚 <b>Доставка:</b> {zone} - {price}₾",
                "address": "📍 <b>Адрес:</b> {address}",
                "phone": "📱 <b>Телефон:</b> {phone}",
                "date": "📅 <b>Дата:</b> {date}",
                "total": "💰 <b>Итого: {total}₾</b>",
                "status": "📊 <b>Статус:</b> {status}",
                "cancel": "❌ Отменить заказ",
                "canceled": "✅ Заказ отменен",
                "cannot_cancel": "❌ Заказ нельзя отменить"
            },
            
            # Оформление заказа
            "checkout": {
                "delivery_zones": "🚚 <b>Выберите зону доставки:</b>",
                "zone_info": "🚚 <b>Зона:</b> {name}\n💰 <b>Стоимость доставки:</b> {price}₾\n⏱ <b>Время доставки:</b> {time}",
                "enter_address": "Напишите точный адрес доставки:",
                "contact_request": "📱 <b>Контактные данные</b>\n\nПоделитесь номером телефона для связи:",
                "order_created": "✅ <b>Заказ создан!</b>\n\n📋 <b>Номер заказа:</b> #{order_id}\n💰 <b>Сумма к оплате:</b> {total}₾\n\n💳 <b>Способы оплаты:</b>\n{payment_info}\n\n📸 <b>После оплаты отправьте скриншот чека</b>",
                "order_error": "❌ Ошибка при создании заказа. Попробуйте еще раз."
            },
            
            # Связь и информация
            "contact": {
                "title": "💬 <b>Связь с нами</b>",
                "description": "❓ <b>По вопросам:</b>\n• Статус заказа\n• Помощь с выбором\n• Технические проблемы\n• Предложения и жалобы\n\n⚡ <b>Быстрый ответ в рабочее время!</b>"
            },
            
            "info": {
                "title": "ℹ️ <b>Информация о магазине</b>",
                "shop_name": "🏪 <b>Tbilisi VAPE Shop</b>\n🇬🇪 Лучший магазин одноразовых сигарет в Тбилиси",
                "advantages": "✅ <b>Наши преимущества:</b>\n• Только оригинальные товары\n• Быстрая доставка по Тбилиси\n• Конкурентные цены\n• Профессиональная консультация",
                "delivery": "🚚 <b>Доставка:</b>\n• По всему Тбилиси\n• Время: 30-90 минут\n• Минимальный заказ: {min_order}₾",
                "payment": "💳 <b>Оплата:</b>\n• Наличными при получении\n• Переводом на карту\n• Криптовалютой"
            },
            
            # Админ панель
            "admin": {
                "panel": "🔧 <b>Админ панель</b>",
                "products": "📦 Управление товарами",
                "orders": "📋 Новые заказы", 
                "stats": "📊 Статистика",
                "broadcast": "📢 Рассылка",
                "categories": "🏷️ Управление категориями",
                "add_product": "➕ Добавить товар",
                "edit_products": "📝 Редактировать товары",
                "add_category": "➕ Добавить категорию",
                "edit_categories": "📝 Редактировать категории",
                "back_to_panel": "🔙 Админ панель",
                "back_to_products": "🔙 Управление товарами",
                "back_to_categories": "🔙 Управление категориями"
            }
        }
        
        # Сохраняем в файл
        with open("translations/ru.json", 'w', encoding='utf-8') as f:
            json.dump(default_translations, f, ensure_ascii=False, indent=2)
    
    def t(self, key: str, user_id: int = None, **kwargs) -> str:
        """Получить перевод по ключу для конкретного пользователя"""
        # Определяем язык для пользователя
        language = self.current_language
        if user_id and user_id in self.user_languages:
            language = self.user_languages[user_id]
        
        keys = key.split('.')
        translation = self.translations.get(language, {})
        
        # Ищем перевод по вложенным ключам
        for k in keys:
            if isinstance(translation, dict) and k in translation:
                translation = translation[k]
            else:
                # Если перевод не найден, используем русский
                translation = self.translations.get(self.default_language, {})
                for k in keys:
                    if isinstance(translation, dict) and k in translation:
                        translation = translation[k]
                    else:
                        return key  # Возвращаем ключ, если перевод не найден
                break
        
        # Если это строка, форматируем её
        if isinstance(translation, str):
            try:
                return translation.format(**kwargs)
            except KeyError:
                return translation
        
        return str(translation)
    
    def set_language(self, language: str, user_id: int = None):
        """Установить язык для пользователя или глобально"""
        if language in self.translations:
            if user_id:
                self.user_languages[user_id] = language
            else:
                self.current_language = language
    
    def get_user_language(self, user_id: int) -> str:
        """Получить язык пользователя"""
        return self.user_languages.get(user_id, self.default_language)

# Глобальный экземпляр
i18n = I18n()

# Функция для удобства
def _(key: str, user_id: int = None, **kwargs) -> str:
    """Короткая функция для получения перевода"""
    return i18n.t(key, user_id=user_id, **kwargs)

