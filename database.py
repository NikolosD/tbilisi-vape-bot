import asyncpg
import asyncio
from datetime import datetime
import json
from config import DATABASE_URL

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
    
    async def get_user(self, user_id):
        """Получение информации о пользователе"""
        query = "SELECT * FROM users WHERE user_id = $1"
        return await self.fetchone(query, user_id)
    
    # Методы для работы с товарами
    async def add_product(self, name, price, description, photo=None, category="vape"):
        """Добавление товара"""
        query = """INSERT INTO products (name, price, description, photo, category) 
                   VALUES ($1, $2, $3, $4, $5)"""
        await self.execute(query, name, price, description, photo, category)
    
    async def get_products(self, category=None):
        """Получение списка товаров"""
        if category:
            query = "SELECT * FROM products WHERE category = $1 AND in_stock = true ORDER BY id"
            return await self.fetchall(query, category)
        else:
            query = "SELECT * FROM products WHERE in_stock = true ORDER BY id"
            return await self.fetchall(query)
    
    async def get_product(self, product_id):
        """Получение товара по ID"""
        query = "SELECT * FROM products WHERE id = $1"
        return await self.fetchone(query, product_id)
    
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
    
    async def get_cart(self, user_id):
        """Получение корзины пользователя"""
        query = """
        SELECT c.product_id, c.quantity, p.name, p.price, p.photo 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = $1 AND p.in_stock = true
        """
        return await self.fetchall(query, user_id)
    
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
    async def create_order(self, user_id, products, total_price, delivery_zone, delivery_price, phone, address):
        """Создание заказа"""
        query = """
        INSERT INTO orders (user_id, products, total_price, delivery_zone, delivery_price, phone, address) 
        VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id
        """
        # Преобразуем цены в float для корректной сериализации
        total_price_float = float(total_price)
        delivery_price_float = float(delivery_price)
        
        result = await self.fetchone(query, user_id, json.dumps(products), total_price_float, 
                                   delivery_zone, delivery_price_float, phone, address)
        return result['id']
    
    async def get_order(self, order_id):
        """Получение заказа по ID"""
        query = "SELECT * FROM orders WHERE id = $1"
        return await self.fetchone(query, order_id)
    
    async def get_user_orders(self, user_id):
        """Получение заказов пользователя"""
        query = "SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC"
        return await self.fetchall(query, user_id)
    
    async def update_order_status(self, order_id, status):
        """Обновление статуса заказа"""
        query = "UPDATE orders SET status = $1 WHERE id = $2"
        await self.execute(query, status, order_id)
    
    async def update_order_screenshot(self, order_id, screenshot):
        """Обновление скриншота оплаты"""
        query = "UPDATE orders SET payment_screenshot = $1 WHERE id = $2"
        await self.execute(query, screenshot, order_id)
    
    async def get_pending_orders(self):
        """Получение заказов ожидающих обработки"""
        query = "SELECT * FROM orders WHERE status IN ('waiting_payment', 'payment_check', 'paid', 'shipping') ORDER BY created_at"
        return await self.fetchall(query)


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
    
    # Таблица товаров
    await conn.execute('''CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        description TEXT,
        photo TEXT,
        category TEXT,
        in_stock BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица заказов
    await conn.execute('''CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        products TEXT,
        total_price DECIMAL(10,2),
        delivery_zone TEXT,
        delivery_price DECIMAL(10,2),
        phone TEXT,
        address TEXT,
        status TEXT DEFAULT 'waiting_payment',
        payment_screenshot TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )''')
    
    # Таблица корзины
    await conn.execute('''CREATE TABLE IF NOT EXISTS cart (
        user_id BIGINT,
        product_id INTEGER,
        quantity INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, product_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )''')
    
    await conn.close()

# Глобальная переменная базы данных
db = Database()