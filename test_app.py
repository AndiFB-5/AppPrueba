import sys
from unittest.mock import MagicMock

# Mock customtkinter and tkinter modules to run headlessly/without tkinter compiled
mock_ctk = MagicMock()

def mock_widget(*args, **kwargs):
    return MagicMock()

class MockCTk:
    def __init__(self, *args, **kwargs):
        pass
    def title(self, *args, **kwargs):
        pass
    def geometry(self, *args, **kwargs):
        pass
    def grid_columnconfigure(self, *args, **kwargs):
        pass
    def grid_rowconfigure(self, *args, **kwargs):
        pass
    def tab(self, *args, **kwargs):
        return MagicMock()
    def winfo_width(self):
        return 1000
    def winfo_height(self):
        return 700
    def winfo_x(self):
        return 100
    def winfo_y(self):
        return 100
    def update_idletasks(self):
        pass
    def update(self):
        pass

mock_ctk.CTk = MockCTk
mock_ctk.CTkFrame = mock_widget
mock_ctk.CTkLabel = mock_widget
mock_ctk.CTkEntry = mock_widget
mock_ctk.CTkButton = mock_widget
mock_ctk.CTkOptionMenu = mock_widget
mock_ctk.CTkScrollableFrame = mock_widget
mock_ctk.CTkTabview = mock_widget
mock_ctk.CTkTextbox = mock_widget
mock_ctk.CTkRadioButton = mock_widget

class MockToplevel:
    def __init__(self, master=None, *args, **kwargs):
        pass
    def title(self, *args, **kwargs):
        pass
    def geometry(self, *args, **kwargs):
        pass
    def grab_set(self):
        pass
    def grab_release(self):
        pass
    def protocol(self, *args, **kwargs):
        pass
    def wait_window(self, *args, **kwargs):
        pass
    def destroy(self):
        pass

mock_ctk.CTkToplevel = MockToplevel
mock_ctk.StringVar = MagicMock
mock_ctk.IntVar = MagicMock
mock_ctk.DoubleVar = MagicMock
mock_ctk.BooleanVar = MagicMock
mock_ctk.CTkFont = MagicMock
mock_ctk.END = "end"

sys.modules['customtkinter'] = mock_ctk

mock_tkinter = MagicMock()
mock_tkinter.messagebox = MagicMock()
sys.modules['tkinter'] = mock_tkinter
sys.modules['tkinter.messagebox'] = mock_tkinter.messagebox

# Now import the modules to test
import database
import main
import os
import unittest
import json
import csv
import glob
from datetime import datetime, timedelta

class TestStockControl(unittest.TestCase):
    def setUp(self):
        # Override database name to a temporary file
        database.DATABASE_NAME = "test_stock_control.db"
        database._conn = None # Reset cached connection
        database.init_db()
        
        # Populate initial products
        database.add_product("Pizza Especial", 1000.0, 10, "Pizzas")
        database.add_product("Empanada Carne", 150.0, 50, "Empanadas")
        database.add_product("Coca Cola 1.5L", 400.0, 5, "Bebidas")
        database.add_product("Fanta 1.5L", 380.0, 20, "Bebidas")

    def tearDown(self):
        # Close connection and clean up file
        if database._conn:
            database._conn.close()
            database._conn = None
        if os.path.exists("test_stock_control.db"):
            os.remove("test_stock_control.db")

    def test_products_sorting(self):
        # 1. Default (Categoría) sorting
        products = database.get_products()
        # Order should be by category (Bebidas, Empanadas, Pizzas), then name
        self.assertEqual(products[0][4], "Bebidas")
        self.assertEqual(products[0][1], "Coca Cola 1.5L")
        self.assertEqual(products[1][1], "Fanta 1.5L")
        self.assertEqual(products[2][4], "Empanadas")
        self.assertEqual(products[3][4], "Pizzas")

        # 2. Name sorting
        products_by_name = database.get_products("Nombre")
        self.assertEqual(products_by_name[0][1], "Coca Cola 1.5L")
        self.assertEqual(products_by_name[1][1], "Empanada Carne")
        self.assertEqual(products_by_name[2][1], "Fanta 1.5L")
        self.assertEqual(products_by_name[3][1], "Pizza Especial")

        # 3. Price ASC
        products_by_price_asc = database.get_products("Precio (Menor a Mayor)")
        self.assertEqual(products_by_price_asc[0][1], "Empanada Carne") # 150
        self.assertEqual(products_by_price_asc[-1][1], "Pizza Especial") # 1000

        # 4. Price DESC
        products_by_price_desc = database.get_products("Precio (Mayor a Menor)")
        self.assertEqual(products_by_price_desc[0][1], "Pizza Especial") # 1000
        self.assertEqual(products_by_price_desc[-1][1], "Empanada Carne") # 150

        # 5. Stock ASC
        products_by_stock = database.get_products("Stock (Menor a Mayor)")
        self.assertEqual(products_by_stock[0][1], "Coca Cola 1.5L") # 5
        self.assertEqual(products_by_stock[-1][1], "Empanada Carne") # 50

    def test_csv_export_format(self):
        products = {p[1]: p[0] for p in database.get_products()} # name -> id
        
        # Add a socio order
        # Pizza (x1) = 1000, Fanta (x2) = 380 each -> Total = 1760
        order1_items = [
            (products["Pizza Especial"], 1, 1000.0),
            (products["Fanta 1.5L"], 2, 380.0)
        ]
        database.add_order(order1_items, "Juan Perez", 1, status=1, metodo_pago="Efectivo")
        
        # Add a non-socio order
        # Coca (x1) = 400. Total = 400
        order2_items = [
            (products["Coca Cola 1.5L"], 1, 400.0)
        ]
        database.add_order(order2_items, "Maria Lopez", 0, status=1, metodo_pago="Transferencia")
        
        # Create a mock App to call the export method
        mock_app = MagicMock()
        mock_app.needs_refresh = {"Productos": False, "Pedidos": False, "Resumen de Ventas": False}
        
        # Keep track of pre-existing CSV files so they aren't removed
        pre_existing_csvs = set(glob.glob("csv_exports/pedidos_*.csv"))

        # Call the export event
        main.App.export_and_clear_orders_event(mock_app)
        
        # Find the new exported CSV file
        current_csvs = set(glob.glob("csv_exports/pedidos_*.csv"))
        new_csvs = list(current_csvs - pre_existing_csvs)
        self.assertEqual(len(new_csvs), 1)
        latest_csv = new_csvs[0]
        
        # Read the CSV to verify contents
        rows = []
        with open(latest_csv, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                rows.append(row)
                
        # Clean up exported CSVs generated by this test
        for f in new_csvs:
            try:
                os.remove(f)
            except OSError:
                pass
                
        # Header + 3 item rows (2 from Juan's order, 1 from Maria's order)
        self.assertEqual(len(rows), 4)
        
        # Verify header row
        expected_header = [
            'order_id',
            'customer_name',
            'MES',
            'Fecha Miercoles',
            'order_date',
            'metodo_pago',
            'product_name',
            'quantity',
            'item_price',
            'Item_total',
            'total_order_price'
        ]
        self.assertEqual(rows[0], expected_header)
        
        # Juan's rows
        juan_rows = [row for row in rows[1:] if row[1] == "Juan Perez"]
        maria_rows = [row for row in rows[1:] if row[1] == "Maria Lopez"]
        
        self.assertEqual(len(juan_rows), 2)
        self.assertEqual(len(maria_rows), 1)
        
        # Verify MES and Fecha Miercoles format
        for row in juan_rows + maria_rows:
            self.assertTrue(len(row[2]) > 0) # MES should not be empty (e.g., 'octubre')
            self.assertRegex(row[3], r"^\d{4}-\d{2}-\d{2}$") # Fecha Miercoles format YYYY-MM-DD (sin hora)
        
        # Check items for Juan: columns are [product_name, quantity, item_price, Item_total, total_order_price]
        juan_prods = {row[6]: (int(row[7]), float(row[8]), float(row[9]), float(row[10])) for row in juan_rows}
        self.assertIn("Pizza Especial", juan_prods)
        self.assertEqual(juan_prods["Pizza Especial"], (1, 1000, 1000, 1760))
        self.assertIn("Fanta 1.5L", juan_prods)
        self.assertEqual(juan_prods["Fanta 1.5L"], (2, 380, 760, 1760))
        for row in juan_rows:
            self.assertEqual(row[5], "Efectivo")
            
        # Maria's row
        self.assertEqual(maria_rows[0][5], "Transferencia")
        self.assertEqual(maria_rows[0][6], "Coca Cola 1.5L")
        self.assertEqual(int(maria_rows[0][7]), 1)
        self.assertEqual(float(maria_rows[0][8]), 400)
        self.assertEqual(float(maria_rows[0][9]), 400)
        self.assertEqual(float(maria_rows[0][10]), 400)
        
        # Ensure database.clear_all_orders was called and completed orders list is empty
        self.assertEqual(len(database.get_orders(status=1)), 0)

    def test_csv_export_exact_user_example(self):
        # Add Heineken and another product to reach total 246000
        database.add_product("Heineken", 9000.0, 100, "Bebidas")
        database.add_product("Pizza Extra", 16000.0, 100, "Pizzas")
        products = {p[1]: p[0] for p in database.get_products()}

        order_items = [
            (products["Heineken"], 22, 9000.0), # 198000
            (products["Pizza Extra"], 3, 16000.0) # 48000 -> Total = 246000
        ]
        order_id = database.add_order(order_items, "braian", 0, status=1, metodo_pago="300")
        
        # Manually set order_date to '2026-03-04 22:47:18'
        conn = database.get_connection()
        conn.execute("UPDATE orders SET order_date = '2026-03-04 22:47:18' WHERE id = ?", (order_id,))
        conn.commit()

        mock_app = MagicMock()
        mock_app.needs_refresh = {"Productos": False, "Pedidos": False, "Resumen de Ventas": False}

        pre_existing_csvs = set(glob.glob("csv_exports/pedidos_*.csv"))
        main.App.export_and_clear_orders_event(mock_app)

        current_csvs = set(glob.glob("csv_exports/pedidos_*.csv"))
        new_csvs = list(current_csvs - pre_existing_csvs)
        self.assertEqual(len(new_csvs), 1)
        latest_csv = new_csvs[0]

        rows = []
        with open(latest_csv, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                rows.append(row)

        for f in new_csvs:
            try:
                os.remove(f)
            except OSError:
                pass

        # Verify Heineken row matches exact user example values
        # order_id customer_name MES Fecha Miercoles order_date metodo_pago product_name quantity item_price Item_total total_order_price
        heineken_rows = [r for r in rows if len(r) > 6 and r[6] == "Heineken"]
        self.assertEqual(len(heineken_rows), 1)
        h_row = heineken_rows[0]

        self.assertEqual(h_row[0], str(order_id))
        self.assertEqual(h_row[1], "braian")
        self.assertEqual(h_row[2], "marzo")
        self.assertEqual(h_row[3], "2026-03-04")
        self.assertEqual(h_row[4], "2026-03-04 22:47:18")
        self.assertEqual(h_row[5], "300")
        self.assertEqual(h_row[6], "Heineken")
        self.assertEqual(h_row[7], "22")
        self.assertEqual(h_row[8], "9000")
        self.assertEqual(h_row[9], "198000")
        self.assertEqual(h_row[10], "246000")

    def test_order_date_is_utc_minus_3(self):
        # Create an order without passing an order_date
        products = {p[1]: p[0] for p in database.get_products()}
        order_items = [(products["Pizza Especial"], 1, 1000.0)]
        
        before = datetime.now(database.TZ_UTC_3)
        order_id = database.add_order(order_items, "Cliente Test", 0)
        after = datetime.now(database.TZ_UTC_3)
        
        order = database.get_orders(status=0)[0]
        order_dt = datetime.strptime(order["order_date"], "%Y-%m-%d %H:%M:%S")
        
        # Verify stored order_date matches current time in UTC-3 within a 2-second margin
        before_naive = before.replace(tzinfo=None)
        after_naive = after.replace(tzinfo=None)
        self.assertTrue(before_naive - timedelta(seconds=2) <= order_dt <= after_naive + timedelta(seconds=2))

    def test_edit_order_and_close(self):
        # Create an order that is pending (status=0)
        products = {p[1]: p[0] for p in database.get_products()}
        order_items = [
            (products["Pizza Especial"], 1, 1000.0)
        ]
        order_id = database.add_order(order_items, "Carlos Gomez", 0, status=0, metodo_pago=None)
        
        # Now edit it using CreateOrderWindow mock/test sequence
        order_data = database.get_orders(status=0)[0]
        
        # Instantiate a mock master App
        mock_master = MagicMock()
        mock_master.needs_refresh = {"Productos": False, "Pedidos": False, "Resumen de Ventas": False}
        
        # Instantiate CreateOrderWindow headlessly
        window = main.CreateOrderWindow(mock_master, order_data=order_data)
        
        # Select "Transferencia" as payment method and es_socio as 0 (using string and int to avoid sqlite3 Mock binding errors)
        window.payment_method_var.get.return_value = "Transferencia"
        window.es_socio_var.get.return_value = 0
        
        # Confirm and close
        window.confirm_action(close_order=True)
        
        # Verify that the order is now closed (status=1) and has the payment method set
        orders_completed = database.get_orders(status=1)
        self.assertEqual(len(orders_completed), 1)
        self.assertEqual(orders_completed[0]["customer_name"], "Carlos Gomez")
        self.assertEqual(orders_completed[0]["metodo_pago"], "Transferencia")
        self.assertEqual(orders_completed[0]["status"], 1)

    def test_es_barra_checkbox(self):
        # Instantiate a mock master App
        mock_master = MagicMock()
        mock_master.needs_refresh = {"Productos": False, "Pedidos": False, "Resumen de Ventas": False}
        
        # Instantiate CreateOrderWindow headlessly in creation mode
        window = main.CreateOrderWindow(mock_master, order_data=None)
        
        # Mock widgets to avoid None reference errors
        window.customer_name_entry = MagicMock()
        window.es_barra_var = MagicMock()
        
        # Simular tildar "Es Barra"
        window.es_barra_var.get.return_value = 1
        window.toggle_barra_event()
        
        # Verify that customer_name_entry.insert was called with "Barra" and state was disabled
        window.customer_name_entry.delete.assert_called_with(0, 'end')
        window.customer_name_entry.insert.assert_called_with(0, 'Barra')
        window.customer_name_entry.configure.assert_called_with(state='disabled')
        
        # Simular destildar "Es Barra"
        window.es_barra_var.get.return_value = 0
        window.toggle_barra_event()
        
        # Verify that state was configured back to normal
        window.customer_name_entry.configure.assert_called_with(state='normal')

    def test_desanidar_texto(self):
        import desanidar
        sample_input = '41,Barra,2026-09-04 00:09:17,Transferencia,"[{\\"producto\\": \\"Verdura\\", \\"cantidad\\": 1, \\"precio_unitario\\": 2000.0}, {\\"producto\\": \\"Carne\\", \\"cantidad\\": 2, \\"precio_unitario\\": 3000.0}]",8000.0'
        
        lines = desanidar.desanidar_texto(sample_input, delimiter=",", include_header=True)
        self.assertEqual(len(lines), 3) # 1 header + 2 items
        
        # Header
        self.assertEqual(lines[0], "order_id,customer_name,MES,Fecha Miercoles,order_date,metodo_pago,product_name,quantity,item_price,Item_total,total_order_price")
        
        # Verdura
        self.assertIn("Verdura", lines[1])
        self.assertIn("2000", lines[1])
        
        # Carne
        self.assertIn("Carne", lines[2])
        self.assertIn("6000", lines[2])

if __name__ == "__main__":
    unittest.main()
