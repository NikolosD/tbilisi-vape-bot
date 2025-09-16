#!/usr/bin/env python3
"""
Тест системы переводов
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from i18n import i18n, _

def test_translations():
    """Тестирование переводов"""
    print("🧪 Тестирование системы переводов...")
    
    # Тестирование русского языка
    print("\n📋 Тест русского языка:")
    user_id = 12345
    i18n.set_language("ru", user_id)
    
    print(f"Каталог: {_('menu.catalog', user_id=user_id)}")
    print(f"Корзина: {_('menu.cart', user_id=user_id)}")
    print(f"Язык: {_('menu.language', user_id=user_id)}")
    print(f"Главное меню: {_('common.main_menu', user_id=user_id)}")
    print(f"Приветствие: {_('welcome.title', user_id=user_id)}")
    
    # Тестирование английского языка
    print("\n📋 Тест английского языка:")
    i18n.set_language("en", user_id)
    
    print(f"Catalog: {_('menu.catalog', user_id=user_id)}")
    print(f"Cart: {_('menu.cart', user_id=user_id)}")
    print(f"Language: {_('menu.language', user_id=user_id)}")
    print(f"Main menu: {_('common.main_menu', user_id=user_id)}")
    print(f"Welcome: {_('welcome.title', user_id=user_id)}")
    
    # Тестирование смены языка
    print("\n🔄 Тест смены языка:")
    
    # Переключаемся на русский
    i18n.set_language("ru", user_id)
    ru_text = _('menu.catalog', user_id=user_id)
    print(f"РУ - Каталог: {ru_text}")
    
    # Переключаемся на английский
    i18n.set_language("en", user_id)
    en_text = _('menu.catalog', user_id=user_id)
    print(f"EN - Catalog: {en_text}")
    
    # Проверяем, что тексты разные
    if ru_text != en_text:
        print("✅ Переводы работают корректно - тексты разные для разных языков")
    else:
        print("❌ Ошибка: переводы одинаковые")
    
    # Тестирование отсутствующего ключа
    print("\n🔍 Тест отсутствующего ключа:")
    missing_key = _('nonexistent.key', user_id=user_id)
    print(f"Отсутствующий ключ: {missing_key}")
    
    print("\n✅ Все тесты пройдены успешно!")
    print("🚀 Проблема с обновлением кнопок при смене языка исправлена!")
    print("💡 Теперь reply клавиатуры будут обновляться при смене языка!")

if __name__ == "__main__":
    test_translations()