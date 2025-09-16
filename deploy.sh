#!/bin/bash

echo "🚀 Начинаем деплой..."

# Удаляем webhook
echo "📡 Удаляем webhook..."
python delete_webhook.py

# Ждем 2 секунды
echo "⏳ Ждем 2 секунды..."
sleep 2

# Добавляем все изменения
echo "📁 Добавляем изменения в git..."
git add .

# Коммитим с сообщением
echo "💾 Создаем коммит..."
git commit -m "$1"

# Отправляем на GitHub
echo "🚀 Отправляем на GitHub..."
git push origin main

echo "✅ Деплой завершен! Подождите 2-3 минуты пока Render пересоберет сервис."
