"""
Конфигурация безопасности и защиты от спама
"""

# Настройки rate limiting
RATE_LIMITS = {
    "MAX_MESSAGES_PER_MINUTE": 10,      # Максимум сообщений в минуту
    "MAX_MESSAGES_PER_HOUR": 60,        # Максимум сообщений в час
    "MIN_MESSAGE_INTERVAL": 1.0,        # Минимальный интервал между сообщениями (сек)
    "MAX_CALLBACK_PER_MINUTE": 15,      # Максимум callback'ов в минуту
}

# Настройки блокировки
BLOCKING_SETTINGS = {
    "SPAM_THRESHOLD": 50,               # Порог блокировки за спам
    "WARNING_THRESHOLD": 3,             # Количество предупреждений до блокировки
    "TEMP_BLOCK_DURATION": 300,         # Время временной блокировки (5 минут)
    "ESCALATION_MULTIPLIER": 2,         # Множитель увеличения времени блокировки
    "MAX_BLOCK_DURATION": 3600,         # Максимальное время блокировки (1 час)
}

# Паттерны для обнаружения спама
SPAM_PATTERNS = {
    # Рекламные слова
    "ADVERTISING": [
        "реклама", "продаю", "купи", "заработок", "доход", "работа на дому",
        "бесплатно", "халява", "раздача", "промокод", "скидка", "акция",
        "casino", "казино", "ставки", "bet", "игра", "выигрыш"
    ],
    
    # Криптовалюты и финансы
    "CRYPTO": [
        "bitcoin", "btc", "ethereum", "crypto", "крипта", "майнинг",
        "инвестиции", "форекс", "трейдинг", "биржа", "coin"
    ],
    
    # Спам ссылок
    "LINKS": [
        "http://", "https://", "www.", ".com", ".ru", ".org",
        "t.me/", "telegram.me/", "@", "канал", "группа", "чат"
    ],
    
    # Подозрительные символы
    "SUSPICIOUS": [
        "🔥🔥🔥", "💰💰💰", "!!!!", "????", "$$$$", "€€€€"
    ]
}

# Настройки обнаружения аномалий
ANOMALY_DETECTION = {
    "MAX_REPEATED_CHARS": 7,            # Максимум повторяющихся символов (aaaaaaa)
    "MAX_EMOJI_COUNT": 10,              # Максимум эмодзи в сообщении
    "MAX_CAPS_PERCENTAGE": 70,          # Максимум заглавных букв (%)
    "SUSPICIOUS_MESSAGE_LENGTH": 500,    # Подозрительная длина сообщения
    "MIN_WORD_LENGTH": 2,               # Минимальная длина слова
}

# Настройки для разных типов пользователей
USER_CATEGORIES = {
    "NEW_USER": {
        "MAX_MESSAGES_PER_MINUTE": 5,
        "SPAM_THRESHOLD": 20,
        "STRICTER_PATTERNS": True
    },
    
    "REGULAR_USER": {
        "MAX_MESSAGES_PER_MINUTE": 10,
        "SPAM_THRESHOLD": 50,
        "STRICTER_PATTERNS": False
    },
    
    "TRUSTED_USER": {
        "MAX_MESSAGES_PER_MINUTE": 20,
        "SPAM_THRESHOLD": 100,
        "STRICTER_PATTERNS": False
    }
}

# Белый список (пользователи, которые никогда не блокируются)
WHITELIST_SETTINGS = {
    "ADMIN_IMMUNITY": True,             # Админы не блокируются
    "VERIFIED_USERS": [],               # ID проверенных пользователей
    "PARTNER_CHANNELS": [],             # ID партнерских каналов
}

# Настройки логирования безопасности
SECURITY_LOGGING = {
    "LOG_ALL_BLOCKS": True,
    "LOG_WARNINGS": True,
    "LOG_SUSPICIOUS_ACTIVITY": True,
    "ALERT_ADMINS_ON_MASS_SPAM": True,
    "MASS_SPAM_THRESHOLD": 5,           # Количество блокировок за 5 минут для оповещения
}

# Настройки автоматических действий
AUTO_ACTIONS = {
    "AUTO_DELETE_SPAM": True,           # Автоматически удалять спам
    "NOTIFY_USER_ON_BLOCK": True,       # Уведомлять пользователя о блокировке
    "ESCALATE_REPEAT_OFFENDERS": True,  # Усиливать наказание для рецидивистов
    "CLEANUP_OLD_STATS": True,          # Очищать старую статистику
    "CLEANUP_INTERVAL_DAYS": 30,        # Интервал очистки (дни)
}

# Настройки для DDoS защиты
DDOS_PROTECTION = {
    "ENABLE_GLOBAL_RATE_LIMIT": True,
    "GLOBAL_MESSAGES_PER_SECOND": 50,   # Глобальный лимит сообщений в секунду
    "CONCURRENT_USERS_LIMIT": 100,      # Лимит одновременных пользователей
    "SUSPICIOUS_BURST_THRESHOLD": 20,   # Порог подозрительного всплеска активности
    "BURST_DETECTION_WINDOW": 10,       # Окно обнаружения всплеска (секунды)
}