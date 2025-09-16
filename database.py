import sqlite3
from datetime import datetime
import json
from config import DATABASE_PATH

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        phone TEXT,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица товаров
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT,
        photo TEXT,
        category TEXT,
        in_stock INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица заказов
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        products TEXT,
        total_price REAL,
        delivery_zone TEXT,
        delivery_price REAL,
        phone TEXT,
        address TEXT,
        status TEXT DEFAULT 'waiting_payment',
        payment_screenshot TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )''')
    
    # Таблица корзины
    cursor.execute('''CREATE TABLE IF NOT EXISTS cart (
        user_id INTEGER,
        product_id INTEGER,
        quantity INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, product_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )''')
    
    conn.commit()
    conn.close()

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
    
    def execute(self, query, params=()):
        """Выполнение запроса"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        result = cursor.fetchall()
        conn.close()
        return result
    
    def fetchone(self, query, params=()):
        """Получение одной записи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        return result
    
    def fetchall(self, query, params=()):
        """Получение всех записей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.close()
        return result
    
    # Методы для работы с пользователями
    def add_user(self, user_id, username=None, first_name=None):
        """Добавление пользователя"""
        query = "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)"
        self.execute(query, (user_id, username, first_name))
    
    def update_user_contact(self, user_id, phone, address):
        """Обновление контактных данных пользователя"""
        query = "UPDATE users SET phone = ?, address = ? WHERE user_id = ?"
        self.execute(query, (phone, address, user_id))
    
    def get_user(self, user_id):
        """Получение информации о пользователе"""
        query = "SELECT * FROM users WHERE user_id = ?"
        return self.fetchone(query, (user_id,))
    
    # Методы для работы с товарами
    def add_product(self, name, price, description, photo=None, category="vape"):
        """Добавление товара"""
        query = "INSERT INTO products (name, price, description, photo, category) VALUES (?, ?, ?, ?, ?)"
        self.execute(query, (name, price, description, photo, category))
    
    def get_products(self, category=None):
        """Получение списка товаров"""
        if category:
            query = "SELECT * FROM products WHERE category = ? AND in_stock = 1 ORDER BY id"
            return self.fetchall(query, (category,))
        else:
            query = "SELECT * FROM products WHERE in_stock = 1 ORDER BY id"
            return self.fetchall(query)
    
    def get_product(self, product_id):
        """Получение товара по ID"""
        query = "SELECT * FROM products WHERE id = ?"
        return self.fetchone(query, (product_id,))
    
    def update_product_stock(self, product_id, in_stock):
        """Обновление наличия товара"""
        query = "UPDATE products SET in_stock = ? WHERE id = ?"
        self.execute(query, (in_stock, product_id))
    
    # Методы для работы с корзиной
    def add_to_cart(self, user_id, product_id, quantity=1):
        """Добавление товара в корзину"""
        query = "INSERT OR REPLACE INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)"
        self.execute(query, (user_id, product_id, quantity))
    
    def get_cart(self, user_id):
        """Получение корзины пользователя"""
        query = """
        SELECT c.product_id, c.quantity, p.name, p.price, p.photo 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ? AND p.in_stock = 1
        """
        return self.fetchall(query, (user_id,))
    
    def remove_from_cart(self, user_id, product_id):
        """Удаление товара из корзины"""
        query = "DELETE FROM cart WHERE user_id = ? AND product_id = ?"
        self.execute(query, (user_id, product_id))
    
    def clear_cart(self, user_id):
        """Очистка корзины"""
        query = "DELETE FROM cart WHERE user_id = ?"
        self.execute(query, (user_id,))
    
    def update_cart_quantity(self, user_id, product_id, quantity):
        """Обновление количества товара в корзине"""
        if quantity <= 0:
            self.remove_from_cart(user_id, product_id)
        else:
            query = "UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?"
            self.execute(query, (quantity, user_id, product_id))
    
    # Методы для работы с заказами
    def create_order(self, user_id, products, total_price, delivery_zone, delivery_price, phone, address):
        """Создание заказа"""
        query = """
        INSERT INTO orders (user_id, products, total_price, delivery_zone, delivery_price, phone, address) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, (user_id, json.dumps(products), total_price, delivery_zone, delivery_price, phone, address))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return order_id
    
    def get_order(self, order_id):
        """Получение заказа по ID"""
        query = "SELECT * FROM orders WHERE id = ?"
        return self.fetchone(query, (order_id,))
    
    def get_user_orders(self, user_id):
        """Получение заказов пользователя"""
        query = "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC"
        return self.fetchall(query, (user_id,))
    
    def update_order_status(self, order_id, status):
        """Обновление статуса заказа"""
        query = "UPDATE orders SET status = ? WHERE id = ?"
        self.execute(query, (status, order_id))
    
    def update_order_screenshot(self, order_id, screenshot):
        """Обновление скриншота оплаты"""
        query = "UPDATE orders SET payment_screenshot = ? WHERE id = ?"
        self.execute(query, (screenshot, order_id))
    
    def get_pending_orders(self):
        """Получение заказов ожидающих обработки"""
        query = "SELECT * FROM orders WHERE status IN ('waiting_payment', 'payment_check') ORDER BY created_at"
        return self.fetchall(query)

# Инициализация базы данных при импорте модуля
init_db()
db = Database()