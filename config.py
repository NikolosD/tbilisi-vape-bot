import os

# Конфигурация бота
BOT_TOKEN = os.getenv("TOKEN", "8131799075:AAEqxNvL7MNxlBtO79JBDfwAu8HB9CLz-JY")

# ID администраторов
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "617646449").split(",")]

# База данных
DATABASE_PATH = "shop.db"

# Реквизиты для оплаты
PAYMENT_INFO = {
    "card": os.getenv("PAYMENT_CARD", "ВАША_КАРТА_БАНКА"),
    "sbp_phone": os.getenv("PAYMENT_PHONE", "+995XXXXXXXXX"),
    "bank_name": os.getenv("BANK_NAME", "Bank of Georgia")
}

# Настройки доставки
DELIVERY_ZONES = {
    "center": {"name": "Центр Тбилиси", "price": 5, "time": "30-60 мин"},
    "saburtalo": {"name": "Сабуртало", "price": 8, "time": "45-90 мин"},
    "vake": {"name": "Ваке", "price": 7, "time": "40-80 мин"},
    "isani": {"name": "Исани", "price": 10, "time": "60-120 мин"},
    "other": {"name": "Другие районы", "price": 15, "time": "60-180 мин"}
}

# Минимальная сумма заказа
MIN_ORDER_AMOUNT = 20