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
        
        # Просто проверяем существование директории
        if not os.path.exists(translations_dir):
            print(f"Внимание: Директория {translations_dir} не найдена. Создайте JSON файлы переводов.")
            return
        
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
    
    def get_available_languages(self) -> list:
        """Получить список доступных языков"""
        return list(self.translations.keys())

# Глобальный экземпляр
i18n = I18n()

# Функция для удобства
def _(key: str, user_id: int = None, **kwargs) -> str:
    """Короткая функция для получения перевода"""
    return i18n.t(key, user_id=user_id, **kwargs)

