"""
Динамические фильтры для кнопок без хардкода
"""
from typing import List, Optional
from aiogram.types import Message
from i18n import i18n


def get_all_translations_for_key(key: str) -> List[str]:
    """Получить все переводы для ключа из всех языков"""
    translations = []
    
    for lang_code, lang_data in i18n.translations.items():
        # Разбираем вложенный ключ (например, "menu.catalog")
        keys = key.split('.')
        value = lang_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                value = None
                break
        
        if value and isinstance(value, str):
            translations.append(value)
    
    return list(set(translations))  # Убираем дубликаты


def create_button_filter(translation_key: str):
    """Создать фильтр для кнопки по ключу перевода"""
    def filter_func(message: Message) -> bool:
        if not message.text:
            return False
        
        button_texts = get_all_translations_for_key(translation_key)
        return message.text in button_texts
    
    return filter_func


# Создаем фильтры для всех кнопок
catalog_filter = create_button_filter("menu.catalog")
cart_filter = create_button_filter("menu.cart")
orders_filter = create_button_filter("menu.orders")
contact_filter = create_button_filter("menu.contact")
info_filter = create_button_filter("menu.info")
language_filter = create_button_filter("menu.language")


def is_catalog_button(message: Message) -> bool:
    """Проверить, является ли сообщение кнопкой каталога"""
    return catalog_filter(message)


def is_cart_button(message: Message) -> bool:
    """Проверить, является ли сообщение кнопкой корзины"""
    return cart_filter(message)


def is_orders_button(message: Message) -> bool:
    """Проверить, является ли сообщение кнопкой заказов"""
    return orders_filter(message)


def is_contact_button(message: Message) -> bool:
    """Проверить, является ли сообщение кнопкой контактов"""
    return contact_filter(message)


def is_info_button(message: Message) -> bool:
    """Проверить, является ли сообщение кнопкой информации"""
    return info_filter(message)


def is_language_button(message: Message) -> bool:
    """Проверить, является ли сообщение кнопкой языка"""
    return language_filter(message)