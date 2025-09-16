#!/bin/bash

echo "🔥 Запуск Tbilisi VAPE Shop Bot..."
echo ""

# Активируем виртуальную среду
if [ ! -d "vape-venv" ]; then
    echo "⚠️  Создаем виртуальную среду..."
    /opt/homebrew/bin/python3.12 -m venv vape-venv
    echo "📦 Устанавливаем зависимости..."
    source vape-venv/bin/activate
    pip install aiogram==3.4.1
else
    echo "✅ Активируем виртуальную среду..."
    source vape-venv/bin/activate
fi

echo "🚀 Запускаем бота..."
echo "📱 Ваш бот: @tbilisi_vape_bot"
echo "🔧 Админ: /admin"
echo "❌ Остановка: Ctrl+C"
echo ""

python main.py