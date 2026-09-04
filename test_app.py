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

    def test_csv_export_format_and_socio_discount(self):
        products = {p[1]: p[0] for p in database.get_products()} # name -> id
        
        # Add a socio order
        # Pizza (x1) = 1000, Fanta (x2) = 380 each -> Total = 1760. Socio total = 1760 * 0.85 = 1496.00
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
        
        # Clean up any existing exported CSV files in csv_exports before running the export
        for f in glob.glob("csv_exports/pedidos_*.csv"):
            try:
                os.remove(f)
            except OSError:
                pass

        # Call the export event
        main.App.export_and_clear_orders_event(mock_app)
        
        # Find the exported CSV file
        csv_files = glob.glob("csv_exports/pedidos_*.csv")
        self.assertTrue(len(csv_files) >= 1)
        latest_csv = max(csv_files, key=os.path.getmtime)
        
        # Read the CSV to verify contents
        rows = []
        with open(latest_csv, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                rows.append(row)
                
        # Clean up exported CSVs
        for f in csv_files:
            try:
                os.remove(f)
            except OSError:
                pass
                
        # Since we removed the header row, the first row should be Juan's order, second should be Maria's order
        self.assertEqual(len(rows), 2) # Exactly 2 rows, 0 header rows
        
        # Row 1: Juan (socio)
        # Columns: order_id, customer_name, order_date, metodo_pago, productos, total_order_price
        self.assertEqual(rows[0][1], "Juan Perez")
        self.assertEqual(rows[0][3], "Efectivo")
        
        # Check products list in JSON
        prod_list = json.loads(rows[0][4])
        self.assertEqual(len(prod_list), 2)
        
        # Pizza Especial unit price should be discounted: 1000 * 0.85 = 850
        self.assertEqual(prod_list[0]["producto"], "Pizza Especial")
        self.assertEqual(prod_list[0]["cantidad"], 1)
        self.assertEqual(prod_list[0]["precio_unitario"], 850.0)
        
        # Fanta 1.5L unit price should be discounted: 380 * 0.85 = 323
        self.assertEqual(prod_list[1]["producto"], "Fanta 1.5L")
        self.assertEqual(prod_list[1]["cantidad"], 2)
        self.assertEqual(prod_list[1]["precio_unitario"], 323.0)
        
        # Total price should be discounted: 850 * 1 + 323 * 2 = 1496.0
        self.assertEqual(float(rows[0][5]), 1496.0)
        
        # Row 2: Maria (non-socio)
        self.assertEqual(rows[1][1], "Maria Lopez")
        self.assertEqual(rows[1][3], "Transferencia")
        
        prod_list2 = json.loads(rows[1][4])
        self.assertEqual(len(prod_list2), 1)
        self.assertEqual(prod_list2[0]["producto"], "Coca Cola 1.5L")
        self.assertEqual(prod_list2[0]["cantidad"], 1)
        self.assertEqual(prod_list2[0]["precio_unitario"], 400.0)
        
        self.assertEqual(float(rows[1][5]), 400.0)
        
        # Ensure database.clear_all_orders was called and completed orders list is empty
        self.assertEqual(len(database.get_orders(status=1)), 0)

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

if __name__ == "__main__":
    unittest.main()
