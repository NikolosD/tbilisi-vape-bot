#!/usr/bin/env python3
"""
Тест для проверки работы динамических фильтров кнопок
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from button_filters import get_all_translations_for_key

def test_translation_lookup():
    """Тестирование получения переводов"""
    print("🧪 Тест получения переводов для кнопок:")
    
    keys_to_test = [
        "menu.catalog",
        "menu.cart", 
        "menu.orders",
        "menu.contact",
        "menu.info",
        "menu.language"
    ]
    
    for key in keys_to_test:
        translations = get_all_translations_for_key(key)
        print(f"  {key}: {translations}")
    
    print("\n✅ Тест завершен!")

if __name__ == "__main__":
    test_translation_lookup()