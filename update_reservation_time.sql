-- Обновление времени резервирования заказов с 10 на 5 минут

-- Изменяем дефолтное значение для новых резервов
ALTER TABLE order_reservations 
ALTER COLUMN reserved_until 
SET DEFAULT CURRENT_TIMESTAMP + INTERVAL '5 minutes';

-- Обновляем активные резервы (которые еще не истекли)
-- Уменьшаем оставшееся время пропорционально
UPDATE order_reservations 
SET reserved_until = CURRENT_TIMESTAMP + 
    (EXTRACT(EPOCH FROM (reserved_until - CURRENT_TIMESTAMP)) / 2) * INTERVAL '1 second'
WHERE reserved_until > CURRENT_TIMESTAMP;

-- Выводим информацию об обновленных резервах
SELECT 
    order_id,
    EXTRACT(EPOCH FROM (reserved_until - CURRENT_TIMESTAMP))/60 as minutes_left
FROM order_reservations 
WHERE reserved_until > CURRENT_TIMESTAMP;