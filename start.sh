#!/bin/bash

echo "🔥 Запуск Tbilisi VAPE Shop Bot..."
echo ""

# Проверяем зависимости
if ! python3 -c "import aiogram" 2>/dev/null; then
    echo "⚠️  Устанавливаем зависимости..."
    python3 -m pip install -r requirements.txt
fi

# Запускаем бота
echo "🚀 Запускаем бота..."
python3 main.py