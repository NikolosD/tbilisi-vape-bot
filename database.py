import asyncpg
import asyncio
from datetime import datetime
import json
from config import DATABASE_URL
from models import User, Category, Product, CartItem, Order
from typing import List, Optional

class Database:
    def __init__(self):
        self.database_url = DATABASE_URL
        self._pool = None
    
    async def init_pool(self):
        """Инициализация пула соединений"""
        if not self._pool:
            self._pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
    
    async def close_pool(self):
        """Закрытие пула соединений"""
        if self._pool:
            await self._pool.close()
    
    async def execute(self, query, *params):
        """Выполнение запроса"""
        await self.init_pool()
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *params)
    
    async def fetchone(self, query, *params):
        """Получение одной записи"""
        await self.init_pool()
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *params)
    
    async def fetchall(self, query, *params):
        """Получение всех записей"""
        await self.init_pool()
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *params)
    
    # Методы для работы с пользователями
    async def add_user(self, user_id, username=None, first_name=None):
        """Добавление пользователя"""
        query = """INSERT INTO users (user_id, username, first_name) 
                   VALUES ($1, $2, $3) ON CONFLICT (user_id) DO NOTHING"""
        await self.execute(query, user_id, username, first_name)
    
    async def update_user_contact(self, user_id, phone, address):
        """Обновление контактных данных пользователя"""
        query = "UPDATE users SET phone = $1, address = $2 WHERE user_id = $3"
        await self.execute(query, phone, address, user_id)
    
    async def get_user(self, user_id) -> Optional[User]:
        """Получение информации о пользователе"""
        query = "SELECT user_id, username, first_name, phone, address, created_at FROM users WHERE user_id = $1"
        row = await self.fetchone(query, user_id)
        return User(*row) if row else None
    
    # Методы для работы с категориями
    async def add_category(self, name, emoji=None, description=None):
        """Добавление категории"""
        query = """INSERT INTO categories (name, emoji, description) 
                   VALUES ($1, $2, $3) ON CONFLICT (name) DO NOTHING"""
        await self.execute(query, name, emoji, description)
    
    async def get_categories(self):
        """Получение всех категорий"""
        query = "SELECT * FROM categories ORDER BY id"
        return await self.fetchall(query)
    
    async def get_categories_with_products(self):
        """Получение только категорий, в которых есть товары в наличии"""
        query = """SELECT DISTINCT c.* FROM categories c 
                   INNER JOIN products p ON c.id = p.category_id 
                   WHERE p.in_stock = true AND p.stock_quantity > 0
                   ORDER BY c.id"""
        return await self.fetchall(query)
    
    async def get_category(self, category_id):
        """Получение категории по ID"""
        query = "SELECT * FROM categories WHERE id = $1"
        row = await self.fetchone(query, category_id)
        if row:
            return Category(
                id=row['id'],
                name=row['name'],
                emoji=row['emoji']
            )
        return None
    
    # Методы для работы с товарами
    async def add_product(self, name, price, description, photo=None, category_id=None, stock_quantity=1):
        """Добавление товара"""
        query = """INSERT INTO products (name, price, description, photo, category_id, stock_quantity) 
                   VALUES ($1, $2, $3, $4, $5, $6)"""
        await self.execute(query, name, price, description, photo, category_id, stock_quantity)
    
    async def get_products(self, category_id=None):
        """Получение списка товаров"""
        if category_id:
            query = """SELECT p.*, c.name as category_name, c.emoji as category_emoji 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_id = c.id 
                       WHERE p.category_id = $1 AND p.in_stock = true 
                       ORDER BY p.id"""
            return await self.fetchall(query, category_id)
        else:
            query = """SELECT p.*, c.name as category_name, c.emoji as category_emoji 
                       FROM products p 
                       LEFT JOIN categories c ON p.category_id = c.id 
                       WHERE p.in_stock = true 
                       ORDER BY p.id"""
            return await self.fetchall(query)
    
    async def get_products_by_category(self, category_id):
        """Получение товаров по категории (только те, что в наличии)"""
        query = """SELECT * FROM products 
                   WHERE category_id = $1 AND in_stock = true AND stock_quantity > 0
                   ORDER BY id"""
        rows = await self.fetchall(query, category_id)
        return [
            Product(
                id=row['id'],
                name=row['name'],
                price=row['price'],
                description=row['description'],
                photo=row['photo'],
                category_id=row['category_id'],
                in_stock=row['in_stock'],
                created_at=row['created_at'],
                stock_quantity=row['stock_quantity']
            ) for row in rows
        ]
    
    async def get_all_products(self):
        """Получение всех товаров (для админки)"""
        query = """SELECT * FROM products ORDER BY id"""
        rows = await self.fetchall(query)
        return [
            Product(
                id=row['id'],
                name=row['name'],
                price=row['price'],
                description=row['description'],
                photo=row['photo'],
                category_id=row['category_id'],
                in_stock=row['in_stock'],
                created_at=row['created_at'],
                stock_quantity=row['stock_quantity']
            ) for row in rows
        ]
    
    async def get_product(self, product_id):
        """Получение товара по ID"""
        query = "SELECT * FROM products WHERE id = $1"
        row = await self.fetchone(query, product_id)
        if row:
            return Product(
                id=row['id'],
                name=row['name'],
                price=row['price'],
                description=row['description'],
                photo=row['photo'],
                category_id=row['category_id'],
                in_stock=row['in_stock'],
                created_at=row['created_at'],
                stock_quantity=row['stock_quantity']
            )
        return None
    
    async def update_product_stock(self, product_id, in_stock):
        """Обновление наличия товара"""
        query = "UPDATE products SET in_stock = $1 WHERE id = $2"
        await self.execute(query, in_stock, product_id)
    
    # Методы для работы с корзиной
    async def add_to_cart(self, user_id, product_id, quantity=1):
        """Добавление товара в корзину"""
        query = """INSERT INTO cart (user_id, product_id, quantity) 
                   VALUES ($1, $2, $3) 
                   ON CONFLICT (user_id, product_id) 
                   DO UPDATE SET quantity = $3"""
        await self.execute(query, user_id, product_id, quantity)
    
    async def get_cart(self, user_id) -> List[CartItem]:
        """Получение корзины пользователя"""
        query = """
        SELECT c.product_id, c.quantity, p.name, p.price, p.photo 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = $1 AND p.in_stock = true
        """
        rows = await self.fetchall(query, user_id)
        return [CartItem(*row) for row in rows]
    
    async def remove_from_cart(self, user_id, product_id):
        """Удаление товара из корзины"""
        query = "DELETE FROM cart WHERE user_id = $1 AND product_id = $2"
        await self.execute(query, user_id, product_id)
    
    async def clear_cart(self, user_id):
        """Очистка корзины"""
        query = "DELETE FROM cart WHERE user_id = $1"
        await self.execute(query, user_id)
    
    async def update_cart_quantity(self, user_id, product_id, quantity):
        """Обновление количества товара в корзине"""
        if quantity <= 0:
            await self.remove_from_cart(user_id, product_id)
        else:
            query = "UPDATE cart SET quantity = $1 WHERE user_id = $2 AND product_id = $3"
            await self.execute(query, quantity, user_id, product_id)
    
    # Методы для работы с заказами
    async def create_order(self, user_id, products, total_price, delivery_zone, delivery_price, phone, address, latitude=None, longitude=None):
        """Создание заказа"""
        import random
        
        # Генерируем уникальный номер заказа (5-6 цифр)
        while True:
            order_number = random.randint(10000, 999999)
            # Проверяем что такого номера еще нет
            existing = await self.fetchone("SELECT id FROM orders WHERE order_number = $1", order_number)
            if not existing:
                break
        
        query = """
        INSERT INTO orders (order_number, user_id, products, total_price, delivery_zone, delivery_price, phone, address, latitude, longitude) 
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) RETURNING id, order_number
        """
        # Преобразуем цены в float для корректной сериализации
        total_price_float = float(total_price)
        delivery_price_float = float(delivery_price)
        
        result = await self.fetchone(query, order_number, user_id, json.dumps(products), total_price_float, 
                                   delivery_zone, delivery_price_float, phone, address, latitude, longitude)
        return result['order_number']  # Возвращаем order_number вместо id
    
    async def get_order(self, order_id) -> Optional[Order]:
        """Получение заказа по ID"""
        query = "SELECT id, order_number, user_id, products, total_price, delivery_zone, delivery_price, phone, address, status, payment_screenshot, created_at FROM orders WHERE id = $1"
        row = await self.fetchone(query, order_id)
        return Order(*row) if row else None
    
    async def get_order_by_number(self, order_number) -> Optional[Order]:
        """Получение заказа по номеру заказа"""
        query = "SELECT id, order_number, user_id, products, total_price, delivery_zone, delivery_price, phone, address, status, payment_screenshot, created_at FROM orders WHERE order_number = $1"
        row = await self.fetchone(query, order_number)
        return Order(*row) if row else None
    
    async def get_user_orders(self, user_id):
        """Получение заказов пользователя"""
        query = "SELECT id, order_number, user_id, products, total_price, delivery_zone, delivery_price, phone, address, status, payment_screenshot, created_at FROM orders WHERE user_id = $1 ORDER BY created_at DESC"
        rows = await self.fetchall(query, user_id)
        return [Order(*row) for row in rows]
    
    async def get_user_orders_count(self, user_id) -> int:
        """Получение количества заказов пользователя"""
        query = "SELECT COUNT(*) FROM orders WHERE user_id = $1"
        row = await self.fetchone(query, user_id)
        return row[0] if row else 0
    
    async def get_order_items(self, order_id):
        """Получение товаров заказа"""
        # Пока что возвращаем пустой список, так как структура заказов хранится в JSON
        # В будущем можно добавить отдельную таблицу order_items
        return []
    
    async def update_order_status(self, order_id, status):
        """Обновление статуса заказа"""
        query = "UPDATE orders SET status = $1 WHERE id = $2"
        await self.execute(query, status, order_id)
    
    async def update_order_screenshot(self, order_id, screenshot):
        """Обновление скриншота оплаты"""
        query = "UPDATE orders SET payment_screenshot = $1 WHERE id = $2"
        await self.execute(query, screenshot, order_id)
    
    async def update_order_status_by_number(self, order_number, status):
        """Обновление статуса заказа по номеру заказа"""
        query = "UPDATE orders SET status = $1 WHERE order_number = $2"
        await self.execute(query, status, order_number)
    
    async def update_order_screenshot_by_number(self, order_number, screenshot):
        """Обновление скриншота оплаты по номеру заказа"""
        query = "UPDATE orders SET payment_screenshot = $1 WHERE order_number = $2"
        await self.execute(query, screenshot, order_number)
    
    async def get_pending_orders(self):
        """Получение заказов ожидающих обработки"""
        query = "SELECT id, order_number, user_id, products, total_price, delivery_zone, delivery_price, phone, address, status, payment_screenshot, created_at FROM orders WHERE status IN ('waiting_payment', 'payment_check', 'paid', 'shipping') ORDER BY created_at"
        rows = await self.fetchall(query)
        return [Order(*row) for row in rows]
    
    async def get_all_orders(self, limit=50):
        """Получение всех заказов (для админа)"""
        query = "SELECT id, order_number, user_id, products, total_price, delivery_zone, delivery_price, phone, address, status, payment_screenshot, created_at FROM orders ORDER BY created_at DESC LIMIT $1"
        rows = await self.fetchall(query, limit)
        return [Order(*row) for row in rows]
    
    async def get_orders_by_status(self, status, limit=50):
        """Получение заказов по статусу"""
        query = "SELECT id, order_number, user_id, products, total_price, delivery_zone, delivery_price, phone, address, status, payment_screenshot, created_at FROM orders WHERE status = $1 ORDER BY created_at DESC LIMIT $2"
        rows = await self.fetchall(query, status, limit)
        return [Order(*row) for row in rows]
    
    async def get_orders_by_multiple_statuses(self, statuses, limit=50):
        """Получение заказов по нескольким статусам"""
        placeholders = ', '.join([f'${i+1}' for i in range(len(statuses))])
        query = f"SELECT id, order_number, user_id, products, total_price, delivery_zone, delivery_price, phone, address, status, payment_screenshot, created_at FROM orders WHERE status IN ({placeholders}) ORDER BY created_at DESC LIMIT ${len(statuses)+1}"
        rows = await self.fetchall(query, *statuses, limit)
        return [Order(*row) for row in rows]
    
    async def get_new_orders(self, limit=50):
        """Получение новых заказов (ожидающих оплаты)"""
        return await self.get_orders_by_status('waiting_payment', limit)
    
    async def get_checking_orders(self, limit=50):
        """Получение заказов на проверке оплаты"""
        return await self.get_orders_by_status('payment_check', limit)
    
    async def get_paid_orders(self, limit=50):
        """Получение оплаченных заказов"""
        return await self.get_orders_by_status('paid', limit)
    
    async def get_shipping_orders(self, limit=50):
        """Получение заказов в доставке"""
        return await self.get_orders_by_status('shipping', limit)
    
    async def get_delivered_orders(self, limit=50):
        """Получение доставленных заказов"""
        return await self.get_orders_by_status('delivered', limit)
    
    async def get_cancelled_orders(self, limit=50):
        """Получение отмененных заказов"""
        return await self.get_orders_by_status('cancelled', limit)
    
    # Методы для работы с администраторами
    async def add_admin(self, user_id, username, first_name, added_by):
        """Добавить администратора"""
        query = """INSERT INTO admins (user_id, username, first_name, added_by) 
                   VALUES ($1, $2, $3, $4) 
                   ON CONFLICT (user_id) DO UPDATE 
                   SET username = $2, first_name = $3"""
        await self.execute(query, user_id, username, first_name, added_by)
    
    async def remove_admin(self, user_id):
        """Удалить администратора"""
        query = "DELETE FROM admins WHERE user_id = $1"
        await self.execute(query, user_id)
    
    async def get_all_admins(self):
        """Получить список всех администраторов из БД"""
        query = "SELECT * FROM admins ORDER BY added_at DESC"
        rows = await self.fetchall(query)
        return rows
    
    async def is_admin_in_db(self, user_id):
        """Проверить, является ли пользователь администратором в БД"""
        query = "SELECT user_id FROM admins WHERE user_id = $1"
        result = await self.fetchone(query, user_id)
        return result is not None


async def init_db():
    """Инициализация базы данных"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Таблица пользователей
    await conn.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        phone TEXT,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица категорий
    await conn.execute('''CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        emoji TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица товаров
    await conn.execute('''CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        description TEXT,
        photo TEXT,
        category_id INTEGER REFERENCES categories(id),
        in_stock BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица заказов
    await conn.execute('''CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        order_number INTEGER UNIQUE,
        user_id BIGINT,
        products TEXT,
        total_price DECIMAL(10,2),
        delivery_zone TEXT,
        delivery_price DECIMAL(10,2),
        phone TEXT,
        address TEXT,
        latitude DECIMAL(10,8),
        longitude DECIMAL(11,8),
        status TEXT DEFAULT 'waiting_payment',
        payment_screenshot TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )''')
    
    # Добавляем поле order_number если его нет (для существующих баз)
    try:
        await conn.execute('ALTER TABLE orders ADD COLUMN order_number INTEGER UNIQUE')
    except:
        pass  # Поле уже существует
    
    # Добавляем поля координат если их нет (для существующих баз)
    try:
        await conn.execute('ALTER TABLE orders ADD COLUMN latitude DECIMAL(10,8)')
        await conn.execute('ALTER TABLE orders ADD COLUMN longitude DECIMAL(11,8)')
    except:
        pass  # Поля уже существуют
    
    # Таблица корзины
    await conn.execute('''CREATE TABLE IF NOT EXISTS cart (
        user_id BIGINT,
        product_id INTEGER,
        quantity INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, product_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )''')
    
    # Таблица администраторов
    await conn.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        added_by BIGINT,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    await conn.close()

# Глобальная переменная базы данных
db = Database()