import sqlite3

DATABASE_NAME = "stock_control.db"

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()

    # Create products table
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)

    # Create orders table
    # status: 0 for pending, 1 for completed, 2 for cancelled
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status INTEGER DEFAULT 0,
            customer_name TEXT
        )
    """)

    # Add customer_name column to orders table if it doesn't exist (for backward compatibility)
    try:
        c.execute("SELECT customer_name FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE orders ADD COLUMN customer_name TEXT")
    
    # Add metodo_pago column to orders table if it doesn't exist
    try:
        c.execute("SELECT metodo_pago FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE orders ADD COLUMN metodo_pago TEXT")

    # Add es_socio column to orders table if it doesn't exist
    try:
        c.execute("SELECT es_socio FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE orders ADD COLUMN es_socio INTEGER DEFAULT 0")

    # Create order_items table to link products to orders
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
    conn.close()

def add_product(name, price, stock):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO products (name, price, stock) VALUES (?, ?, ?)", (name, price, stock))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Error: Product with name '{name}' already exists.")
        return False
    finally:
        conn.close()

def get_products():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock FROM products")
    products = c.fetchall()
    conn.close()
    return products

def update_product_stock(product_id, new_stock):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
    conn.commit()
    conn.close()

def update_product(product_id, name, price, stock):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    try:
        c.execute("UPDATE products SET name = ?, price = ?, stock = ? WHERE id = ?", (name, price, stock, product_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Error: Product with name '{name}' already exists.")
        return False
    finally:
        conn.close()

def add_order(product_items, customer_name, es_socio):
    # product_items is a list of tuples: (product_id, quantity, item_price_at_order)
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO orders (customer_name, es_socio) VALUES (?, ?)", (customer_name, es_socio))
        order_id = c.lastrowid
        
        for product_id, quantity, item_price in product_items:
            c.execute("INSERT INTO order_items (order_id, product_id, quantity, item_price) VALUES (?, ?, ?, ?)",
                      (order_id, product_id, quantity, item_price))
            
            # Update product stock
            c.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
        
        conn.commit()
        return order_id
    except Exception as e:
        conn.rollback()
        print(f"Error adding order: {e}")
        return None
    finally:
        conn.close()

def get_orders(status=None):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    query = """
        SELECT
            o.id,
            o.order_date,
            o.status,
            o.customer_name,
            o.metodo_pago,
            o.es_socio,
            p.id,
            p.name,
            oi.quantity,
            oi.item_price
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
    """
    if status is not None:
        query += f" WHERE o.status = {status}"
    query += " ORDER BY o.order_date DESC"
    c.execute(query)
    orders_data = c.fetchall()
    conn.close()

    # Group order items by order ID
    orders_grouped = {}
    for order_id, order_date, order_status, customer_name, metodo_pago, es_socio, product_id, product_name, quantity, item_price in orders_data:
        if order_id not in orders_grouped:
            orders_grouped[order_id] = {
                "id": order_id,
                "order_date": order_date,
                "status": order_status,
                "customer_name": customer_name,
                "metodo_pago": metodo_pago,
                "es_socio": es_socio,
                "items": [],
                "total_price": 0
            }
        orders_grouped[order_id]["items"].append({
            "product_id": product_id,
            "product_name": product_name,
            "quantity": quantity,
            "item_price": item_price
        })
        orders_grouped[order_id]["total_price"] += (quantity * item_price)
    
    return list(orders_grouped.values())

def update_order_status_and_payment_method(order_id, status, metodo_pago):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("UPDATE orders SET status = ?, metodo_pago = ? WHERE id = ?", (status, metodo_pago, order_id))
    conn.commit()
    conn.close()

def get_total_sales_by_payment_method(metodo_pago):
    conn = sqlite3.connect(DATABASE_NAME)
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
    conn.close()
    return total_sales if total_sales else 0

def get_total_sales():
    conn = sqlite3.connect(DATABASE_NAME)
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
        WHERE o.status = 1  -- Only completed orders
    """)
    total_sales = c.fetchone()[0]
    conn.close()
    return total_sales if total_sales else 0

def update_order(order_id, new_items, original_order_data, es_socio):
    # new_items is a list of tuples: (product_id, quantity, item_price)
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    try:
        # --- 1. Update es_socio status ---
        c.execute("UPDATE orders SET es_socio = ? WHERE id = ?", (es_socio, order_id))

        # --- 2. Get original items and calculate stock changes ---
        original_items = {item['product_id']: item['quantity'] for item in original_order_data['items']}
        new_items_dict = {pid: qty for pid, qty, price in new_items}

        all_pids = set(original_items.keys()) | set(new_items_dict.keys())
        
        for pid in all_pids:
            original_qty = original_items.get(pid, 0)
            new_qty = new_items_dict.get(pid, 0)
            stock_change = original_qty - new_qty
            
            if stock_change != 0:
                c.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (stock_change, pid))

        # --- 3. Update order items ---
        # Delete items that are no longer in the order
        pids_to_delete = set(original_items.keys()) - set(new_items_dict.keys())
        if pids_to_delete:
            c.executemany("DELETE FROM order_items WHERE order_id = ? AND product_id = ?", 
                          [(order_id, pid) for pid in pids_to_delete])

        # Update existing items and insert new ones
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
        print(f"Error updating order: {e}")
        return False
    finally:
        conn.close()

def clear_all_orders():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM order_items")
        c.execute("DELETE FROM orders")
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error clearing orders: {e}")
        return False
    finally:
        conn.close()
