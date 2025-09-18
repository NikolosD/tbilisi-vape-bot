-- Создание таблицы категорий вкусов
CREATE TABLE IF NOT EXISTS flavor_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    emoji VARCHAR(10) DEFAULT '',
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Добавление базовых категорий вкусов
INSERT INTO flavor_categories (name, emoji, description) VALUES
    ('Ягодные', '🍓', 'Клубника, малина, черника и другие ягодные вкусы'),
    ('Ментол/Лед', '❄️', 'Ментоловые и освежающие вкусы с охлаждающим эффектом'),
    ('Цитрусы', '🍊', 'Лимон, апельсин, грейпфрут и другие цитрусовые'),
    ('Экзотика', '🥭', 'Манго, маракуйя, киви и другие экзотические фрукты'),
    ('Сладкие', '🍰', 'Десертные и сладкие вкусы: торты, конфеты, мороженое')
ON CONFLICT (name) DO NOTHING;

-- Создание функции для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Создание триггера для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_flavor_categories_updated_at ON flavor_categories;
CREATE TRIGGER update_flavor_categories_updated_at
    BEFORE UPDATE ON flavor_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();