import sqlite3

DATABASE_NAME = "stock_control.db"
_conn = None

def get_connection():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        # Optimización de rendimiento para hardware lento
        _conn.execute("PRAGMA journal_mode = WAL")
        _conn.execute("PRAGMA synchronous = NORMAL")
        _conn.execute("PRAGMA cache_size = -2000") # 2MB de caché
    return _conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Create products table
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            category TEXT
        )
    """)

    # Add category column to products table if it doesn't exist
    try:
        c.execute("SELECT category FROM products LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE products ADD COLUMN category TEXT")

    # Create orders table
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status INTEGER DEFAULT 0,
            customer_name TEXT
        )
    """)

    # Check and add missing columns for backward compatibility
    columns_to_add = [
        ("customer_name", "TEXT"),
        ("metodo_pago", "TEXT"),
        ("es_socio", "INTEGER DEFAULT 0")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            c.execute(f"SELECT {col_name} FROM orders LIMIT 1")
        except sqlite3.OperationalError:
            c.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}")

    # Create order_items table
    c.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            item_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)

    conn.commit()

def add_product(name, price, stock, category="Sin Categoría"):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO products (name, price, stock, category) VALUES (?, ?, ?, ?)", (name, price, stock, category))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_products():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock, category FROM products")
    return c.fetchall()

def update_product_stock(product_id, new_stock):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
    conn.commit()

def update_product(product_id, name, price, stock, category="Sin Categoría"):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE products SET name = ?, price = ?, stock = ?, category = ? WHERE id = ?", (name, price, stock, category, product_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def add_order(product_items, customer_name, es_socio, status=0, metodo_pago=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO orders (customer_name, es_socio, status, metodo_pago) VALUES (?, ?, ?, ?)", (customer_name, es_socio, status, metodo_pago))
        order_id = c.lastrowid
        
        for product_id, quantity, item_price in product_items:
            c.execute("INSERT INTO order_items (order_id, product_id, quantity, item_price) VALUES (?, ?, ?, ?)",
                      (order_id, product_id, quantity, item_price))
            c.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
        
        conn.commit()
        return order_id
    except Exception as e:
        conn.rollback()
        print(f"Error adding order: {e}")
        return None

def get_orders(status=None):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT o.id, o.order_date, o.status, o.customer_name, o.metodo_pago, o.es_socio,
               p.id, p.name, oi.quantity, oi.item_price
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
    """
    if status is not None:
        query += f" WHERE o.status = {status}"
    query += " ORDER BY o.order_date DESC"
    
    c.execute(query)
    orders_data = c.fetchall()

    orders_grouped = {}
    for order_id, order_date, order_status, customer_name, metodo_pago, es_socio, product_id, product_name, quantity, item_price in orders_data:
        if order_id not in orders_grouped:
            orders_grouped[order_id] = {
                "id": order_id, "order_date": order_date, "status": order_status,
                "customer_name": customer_name, "metodo_pago": metodo_pago,
                "es_socio": es_socio, "items": [], "total_price": 0
            }
        orders_grouped[order_id]["items"].append({
            "product_id": product_id, "product_name": product_name,
            "quantity": quantity, "item_price": item_price
        })
        orders_grouped[order_id]["total_price"] += (quantity * item_price)
    
    return list(orders_grouped.values())

def update_order_status_and_payment_method(order_id, status, metodo_pago):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ?, metodo_pago = ? WHERE id = ?", (status, metodo_pago, order_id))
    conn.commit()

def get_total_sales_by_payment_method(metodo_pago):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT SUM(
            CASE 
                WHEN o.es_socio = 1 THEN (oi.quantity * oi.item_price * 0.85)
                ELSE (oi.quantity * oi.item_price)
            END
        )
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        WHERE o.status = 1 AND o.metodo_pago = ?
    """, (metodo_pago,))
    total_sales = c.fetchone()[0]
    return total_sales if total_sales else 0

def get_total_sales():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT SUM(
            CASE 
                WHEN o.es_socio = 1 THEN (oi.quantity * oi.item_price * 0.85)
                ELSE (oi.quantity * oi.item_price)
            END
        )
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        WHERE o.status = 1 AND o.metodo_pago != '300'
    """)
    total_sales = c.fetchone()[0]
    return total_sales if total_sales else 0

def update_order(order_id, new_items, original_order_data, es_socio):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE orders SET es_socio = ? WHERE id = ?", (es_socio, order_id))

        original_items = {item['product_id']: item['quantity'] for item in original_order_data['items']}
        new_items_dict = {pid: qty for pid, qty, price in new_items}

        all_pids = set(original_items.keys()) | set(new_items_dict.keys())
        
        for pid in all_pids:
            original_qty = original_items.get(pid, 0)
            new_qty = new_items_dict.get(pid, 0)
            stock_change = original_qty - new_qty
            if stock_change != 0:
                c.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (stock_change, pid))

        pids_to_delete = set(original_items.keys()) - set(new_items_dict.keys())
        if pids_to_delete:
            c.executemany("DELETE FROM order_items WHERE order_id = ? AND product_id = ?", 
                          [(order_id, pid) for pid in pids_to_delete])

        for product_id, quantity, item_price in new_items:
            c.execute("""
                INSERT OR REPLACE INTO order_items (id, order_id, product_id, quantity, item_price)
                VALUES (
                    (SELECT id FROM order_items WHERE order_id = ? AND product_id = ?),
                    ?, ?, ?, ?
                )
            """, (order_id, product_id, order_id, product_id, quantity, item_price))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False

def clear_all_orders():
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM order_items")
        c.execute("DELETE FROM orders")
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
