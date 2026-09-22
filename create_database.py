import sqlite3
from pathlib import Path
from config import Config

def create_database():
    
    # Удаляем старый файл базы
    if Config.DB_PATH.exists():
        Config.DB_PATH.unlink()
    
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()
    
    # Включаем поддержку внешних ключей
    cursor.execute("PRAGMA foreign_keys = ON")
    
    print("Создание таблиц...")
    
    # 1. Таблица Категории закройщиков/изделий
    cursor.execute("""
    CREATE TABLE categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL CHECK(category_name IN (
            'верхняя одежда', 'легкое платье', 'мужская одежда', 
            'шляпы', 'меховые изделия'
        )),
        UNIQUE(category_name)
    )
    """)
    
    # 2. Таблица Типы ткани
    cursor.execute("""
    CREATE TABLE fabric_types (
        type_id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_name TEXT NOT NULL,
        UNIQUE(type_name)
    )
    """)
    
    # 3. Таблица Закройщики
    cursor.execute("""
    CREATE TABLE cutters (
        cutter_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        category_id INTEGER NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
    )
    """)
    
    # 4. Таблица Изделия
    cursor.execute("""
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        base_price DECIMAL(10,2) NOT NULL CHECK(base_price > 0),
        category_id INTEGER NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
    )
    """)
    
    # 5. Таблица Ткань
    cursor.execute("""
    CREATE TABLE fabrics (
        fabric_article TEXT PRIMARY KEY,
        fabric_name TEXT NOT NULL,
        unit TEXT NOT NULL,
        price DECIMAL(10,2) NOT NULL CHECK(price > 0),
        type_id INTEGER NOT NULL,
        quantity DECIMAL(10,2) NOT NULL CHECK(quantity >= 0),
        FOREIGN KEY (type_id) REFERENCES fabric_types(type_id)
    )
    """)
    
    # 6. Таблица Усложнения
    cursor.execute("""
    CREATE TABLE complications (
        complication_id INTEGER PRIMARY KEY AUTOINCREMENT,
        complication_name TEXT NOT NULL,
        price_per_element DECIMAL(10,2) NOT NULL CHECK(price_per_element > 0)
    )
    """)
    
    # 7. Таблица Заказы
    cursor.execute("""
    CREATE TABLE orders (
        order_number INTEGER PRIMARY KEY AUTOINCREMENT,
        order_date TEXT NOT NULL,
        cutter_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        customer_address TEXT,
        customer_phone TEXT,
        completion_date TEXT NOT NULL,
        urgency_percent DECIMAL(5,2) DEFAULT 0 CHECK(urgency_percent >= 0),
        FOREIGN KEY (cutter_id) REFERENCES cutters(cutter_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id),
        CHECK(completion_date >= order_date)
    )
    """)
    
    # 8. Таблица Заказ-Усложнение
    cursor.execute("""
    CREATE TABLE order_complications (
        order_number INTEGER NOT NULL,
        complication_id INTEGER NOT NULL,
        element_count INTEGER NOT NULL CHECK(element_count > 0),
        PRIMARY KEY (order_number, complication_id),
        FOREIGN KEY (order_number) REFERENCES orders(order_number) ON DELETE CASCADE,
        FOREIGN KEY (complication_id) REFERENCES complications(complication_id)
    )
    """)
    
    # 9. Таблица Заказ-Ткань
    cursor.execute("""
    CREATE TABLE order_fabrics (
        order_number INTEGER NOT NULL,
        fabric_article TEXT NOT NULL,
        quantity DECIMAL(10,2) NOT NULL CHECK(quantity > 0),
        PRIMARY KEY (order_number, fabric_article),
        FOREIGN KEY (order_number) REFERENCES orders(order_number) ON DELETE CASCADE,
        FOREIGN KEY (fabric_article) REFERENCES fabrics(fabric_article)
    )
    """)
    
    # 10. Таблица Касса
    cursor.execute("""
    CREATE TABLE cash_register (
        receipt_number INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number INTEGER NOT NULL UNIQUE,
        receipt_date TEXT NOT NULL,
        amount DECIMAL(10,2) NOT NULL CHECK(amount > 0),
        FOREIGN KEY (order_number) REFERENCES orders(order_number)
    )
    """)
    
    # 11. Представление для расчета стоимости заказа
    cursor.execute("""
    CREATE VIEW order_costs AS
    SELECT 
        o.order_number,
        p.base_price as base_amount,
        COALESCE(SUM(oc.element_count * c.price_per_element), 0) as complications_amount,
        COALESCE(SUM(of.quantity * f.price), 0) as fabric_amount,
        (p.base_price * o.urgency_percent / 100) as urgency_amount,
        (p.base_price + 
         COALESCE(SUM(oc.element_count * c.price_per_element), 0) +
         COALESCE(SUM(of.quantity * f.price), 0) +
         (p.base_price * o.urgency_percent / 100)) as total_amount
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
    LEFT JOIN order_complications oc ON o.order_number = oc.order_number
    LEFT JOIN complications c ON oc.complication_id = c.complication_id
    LEFT JOIN order_fabrics of ON o.order_number = of.order_number
    LEFT JOIN fabrics f ON of.fabric_article = f.fabric_article
    GROUP BY o.order_number
    """)
    
    print("Таблицы созданы")
    
    # Добавляем тестовые данные
    add_test_data(cursor)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\nБаза данных создана: {Config.DB_PATH}")
    print("Теперь запустите: python main.py")

def add_test_data(cursor):
    """Добавление тестовых данных"""
    
    # 1. Категории (фиксированные)
    categories = Config.CUTTER_CATEGORIES
    for category in categories:
        cursor.execute("INSERT OR IGNORE INTO categories (category_name) VALUES (?)", 
                      (category,))
    
    # 2. Типы ткани
    fabric_types = Config.FABRIC_TYPES
    for fabric_type in fabric_types:
        cursor.execute("INSERT OR IGNORE INTO fabric_types (type_name) VALUES (?)", 
                      (fabric_type,))
    
    # 3. Закройщики
    cutters = [
        ('Иванова Анна Петровна', 'верхняя одежда'),
        ('Петров Сергей Иванович', 'мужская одежда'),
        ('Сидорова Мария Владимировна', 'легкое платье'),
        ('Козлов Алексей Дмитриевич', 'шляпы'),
        ('Николаева Ольга Сергеевна', 'меховые изделия')
    ]
    
    for full_name, category_name in cutters:
        cursor.execute("""
        INSERT INTO cutters (full_name, category_id)
        VALUES (?, (SELECT category_id FROM categories WHERE category_name = ?))
        """, (full_name, category_name))
    
    # 4. Изделия
    products = [
        ('Пальто зимнее', 5000.00, 'верхняя одежда'),
        ('Костюм мужской', 4000.00, 'мужская одежда'),
        ('Платье вечернее', 3500.00, 'легкое платье'),
        ('Шляпа фетровая', 1500.00, 'шляпы'),
        ('Шуба норковая', 25000.00, 'меховые изделия'),
        ('Пиджак', 3000.00, 'мужская одежда'),
        ('Юбка', 2000.00, 'легкое платье')
    ]
    
    for name, price, category in products:
        cursor.execute("""
        INSERT INTO products (product_name, base_price, category_id)
        VALUES (?, ?, (SELECT category_id FROM categories WHERE category_name = ?))
        """, (name, price, category))
    
    # 5. Ткани
    fabrics = [
        ('ШЕЛК-001', 'Шелк натуральный', 'метр', 1200.00, 'шелк', 100.5),
        ('ХЛОП-002', 'Хлопок египетский', 'метр', 450.00, 'хлопок', 200.0),
        ('ШЕРСТ-003', 'Шерсть меринос', 'метр', 800.00, 'шерсть', 150.0),
        ('ДЖИНС-004', 'Джинсовая ткань', 'метр', 350.00, 'джинсовая', 300.0),
        ('КОЖА-005', 'Кожа натуральная', 'метр', 2500.00, 'кожа', 50.0)
    ]
    
    for article, name, unit, price, type_name, quantity in fabrics:
        cursor.execute("""
        INSERT INTO fabrics (fabric_article, fabric_name, unit, price, type_id, quantity)
        VALUES (?, ?, ?, ?, 
                (SELECT type_id FROM fabric_types WHERE type_name = ?), 
                ?)
        """, (article, name, unit, price, type_name, quantity))
    
    # 6. Усложнения
    complications = [
        ('Вышивка', 500.00),
        ('Аппликация', 300.00),
        ('Стразы', 200.00),
        ('Перфорация', 400.00),
        ('Инкрустация', 600.00)
    ]
    
    for name, price in complications:
        cursor.execute("""
        INSERT INTO complications (complication_name, price_per_element)
        VALUES (?, ?)
        """, (name, price))
    
    print("Тестовые данные добавлены")

if __name__ == '__main__':
    create_database()