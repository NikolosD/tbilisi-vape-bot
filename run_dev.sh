#!/bin/bash

# Скрипт для запуска бота в режиме разработки

echo "🚀 Запуск бота в режиме разработки..."

# Проверяем, установлен ли watchdog
if ! python3 -c "import watchdog" 2>/dev/null; then
    echo "📦 Устанавливаем watchdog..."
    pip3 install watchdog
fi

# Запускаем hot reload
echo "👀 Запуск с автоматической перезагрузкой..."
python3 dev_runner.py