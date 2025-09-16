#!/usr/bin/env python3
"""
Скрипт для добавления примеров товаров в базу данных
"""

from database import db

def add_sample_products():
    """Добавить примеры товаров"""
    
    sample_products = [
        {
            "name": "ELFBAR BC5000 - Kiwi Passion Fruit Guava",
            "price": 25.0,
            "description": "🥝 Свежий микс киви, маракуйи и гуавы\n💨 До 5000 затяжек\n🔋 Встроенная батарея 650mAh\n🌟 Оригинальная продукция",
            "category": "elfbar"
        },
        {
            "name": "ELFBAR BC5000 - Blue Razz Ice",
            "price": 25.0,
            "description": "🫐 Синяя малина с ледяной свежестью\n💨 До 5000 затяжек\n🔋 Встроенная батарея 650mAh\n❄️ Охлаждающий эффект",
            "category": "elfbar"
        },
        {
            "name": "ELFBAR BC5000 - Watermelon Ice",
            "price": 25.0,
            "description": "🍉 Сочный арбуз с мятной прохладой\n💨 До 5000 затяжек\n🔋 Встроенная батарея 650mAh\n🧊 Ментоловая свежесть",
            "category": "elfbar"
        },
        {
            "name": "ELFBAR BC5000 - Strawberry Mango",
            "price": 25.0,
            "description": "🍓 Клубника и сочное манго\n💨 До 5000 затяжек\n🔋 Встроенная батарея 650mAh\n🥭 Тропический вкус",
            "category": "elfbar"
        },
        {
            "name": "LOST MARY OS5000 - Blueberry Raspberry",
            "price": 28.0,
            "description": "🫐 Черника с малиной\n💨 До 5000 затяжек\n⚡ Быстрая зарядка USB-C\n🔋 Аккумулятор 650mAh\n✨ Премиум качество",
            "category": "lostmary"
        },
        {
            "name": "LOST MARY OS5000 - Grape Ice",
            "price": 28.0,
            "description": "🍇 Сочный виноград с ледяной прохладой\n💨 До 5000 затяжек\n⚡ Быстрая зарядка USB-C\n❄️ Охлаждающий эффект",
            "category": "lostmary"
        },
        {
            "name": "LOST MARY OS5000 - Pineapple Ice",
            "price": 28.0,
            "description": "🍍 Тропический ананас с ментолом\n💨 До 5000 затяжек\n⚡ Быстрая зарядка USB-C\n🧊 Освежающий вкус",
            "category": "lostmary"
        },
        {
            "name": "VAPORESSO XROS 3 Pod Kit",
            "price": 45.0,
            "description": "🔥 Перезаряжаемая POD-система\n🔋 Батарея 1000mAh\n💨 Регулировка воздушного потока\n📱 Удобное управление\n🎯 Точная передача вкуса",
            "category": "pods"
        },
        {
            "name": "CALIBURN G2 Pod Kit",
            "price": 42.0,
            "description": "⚡ Мощность до 18W\n🔋 Батарея 750mAh\n💨 Плавная регулировка тяги\n🔄 Заменяемые картриджи\n🎨 Стильный дизайн",
            "category": "pods"
        },
        {
            "name": "HQD Cuvie Plus - Mixed Berries",
            "price": 22.0,
            "description": "🍓 Ассорти лесных ягод\n💨 До 1200 затяжек\n🔋 Встроенная батарея\n🌈 Яркий насыщенный вкус\n💎 Компактный размер",
            "category": "hqd"
        },
        {
            "name": "HQD Cuvie Plus - Mango Ice",
            "price": 22.0,
            "description": "🥭 Спелое манго с ледяной свежестью\n💨 До 1200 затяжек\n❄️ Охлаждающий эффект\n🌴 Тропический вкус",
            "category": "hqd"
        },
        {
            "name": "VOZOL Gear 10000 - Apple Ice",
            "price": 35.0,
            "description": "🍎 Зеленое яблоко с ментолом\n💨 До 10000 затяжек\n🔋 Мощная батарея\n📱 Индикатор заряда\n❄️ Освежающий вкус",
            "category": "vozol"
        },
        {
            "name": "VOZOL Gear 10000 - Peach Ice",
            "price": 35.0,
            "description": "🍑 Сочный персик с прохладой\n💨 До 10000 затяжек\n🔋 Долговечная батарея\n📱 LED индикация\n🧊 Ментоловая свежесть",
            "category": "vozol"
        },
        {
            "name": "JUUL Device Starter Kit",
            "price": 65.0,
            "description": "📱 Классическая JUUL система\n🔋 Перезаряжаемое устройство\n💨 Стабильная подача пара\n🎯 Точная передача вкуса\n✨ Премиум качество",
            "category": "juul"
        },
        {
            "name": "JUUL Pods - Virginia Tobacco (4 шт)",
            "price": 38.0,
            "description": "🚬 Классический табачный вкус\n📦 4 картриджа в упаковке\n🎯 Оригинальные JUUL поды\n💫 Насыщенный вкус",
            "category": "juul"
        }
    ]
    
    print("Добавление примеров товаров в базу данных...")
    
    for product in sample_products:
        try:
            db.add_product(
                name=product["name"],
                price=product["price"],
                description=product["description"],
                photo=None,  # Фото добавим позже через админ-панель
                category=product["category"]
            )
            print(f"✅ Добавлен: {product['name']}")
        except Exception as e:
            print(f"❌ Ошибка при добавлении {product['name']}: {e}")
    
    print(f"\n🎉 Добавлено {len(sample_products)} товаров!")
    print("\n📝 Что дальше:")
    print("1. Запустите бота: python main.py")
    print("2. Найдите @userinfobot чтобы узнать свой Telegram ID")
    print("3. Обновите ADMIN_IDS в config.py")
    print("4. Обновите реквизиты оплаты в config.py")
    print("5. Добавьте фото товаров через /admin → Управление товарами")

if __name__ == "__main__":
    add_sample_products()