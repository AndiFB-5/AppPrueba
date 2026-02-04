import customtkinter as ctk
import database
from CTkMessagebox import CTkMessagebox
import os
import csv
from datetime import datetime

class CreateOrderWindow(ctk.CTkToplevel):
    def __init__(self, master, order_data=None):
        super().__init__(master)

        self.master = master
        self.order_data = order_data
        self.is_edit_mode = order_data is not None
        
        # Initialize order items
        self.order_items = {}
        if self.is_edit_mode:
            for item in order_data['items']:
                self.order_items[item['product_id']] = {
                    "name": item['product_name'],
                    "quantity": item['quantity'],
                    "price": item['item_price']
                }
        
        # --- Window Setup ---
        title = f"Editar Pedido #{order_data['id']}" if self.is_edit_mode else "Crear Nuevo Pedido"
        self.title(title)
        self.geometry("800x600")

        # --- Frames ---
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=(10,0))
        
        if not self.is_edit_mode:
            ctk.CTkLabel(top_frame, text="Nombre del Cliente:").pack(side="left", padx=(10,0))
            self.customer_name_entry = ctk.CTkEntry(top_frame, placeholder_text="Nombre")
            self.customer_name_entry.pack(side="left", expand=True, padx=10)
        else:
             ctk.CTkLabel(top_frame, text=f"Cliente: {self.order_data.get('customer_name', 'N/A')}", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        product_list_frame = ctk.CTkScrollableFrame(main_frame, label_text="Productos Disponibles")
        product_list_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        order_summary_frame = ctk.CTkFrame(main_frame, width=300)
        order_summary_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        order_summary_frame.grid_rowconfigure(1, weight=1)

        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(fill="x", padx=10, pady=(0, 10))

        # --- Product List ---
        products = database.get_products()
        self.product_labels = {} # To update quantity labels
        
        for i, product in enumerate(products):
            product_id, name, price, stock = product
            
            product_frame = ctk.CTkFrame(product_list_frame)
            product_frame.pack(fill="x", expand=True, padx=5, pady=5)
            product_frame.grid_columnconfigure(0, weight=1)
            
            ctk.CTkLabel(product_frame, text=name, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")
            
            initial_quantity = self.order_items.get(product_id, {}).get("quantity", 0)
            available_stock = stock + initial_quantity
            ctk.CTkLabel(product_frame, text=f"${price:.2f} (Stock: {available_stock})", font=ctk.CTkFont(size=10)).grid(row=1, column=0, sticky="w")

            quantity_frame = ctk.CTkFrame(product_frame)
            quantity_frame.grid(row=0, column=1, rowspan=2, sticky="e")

            quantity_label = ctk.CTkLabel(quantity_frame, text=str(initial_quantity), width=30)
            quantity_label.pack(side="left", padx=5)
            self.product_labels[product_id] = quantity_label

            def create_callbacks(pid, pname, pprice, pstock, qlabel):
                def increment():
                    current_quantity = self.order_items.get(pid, {}).get("quantity", 0)
                    
                    adjusted_stock = pstock
                    if self.is_edit_mode:
                        for item in self.order_data['items']:
                            if item['product_id'] == pid:
                                adjusted_stock += item['quantity']
                                break
                    
                    if current_quantity < adjusted_stock:
                        if pid not in self.order_items:
                            self.order_items[pid] = {"name": pname, "quantity": 0, "price": pprice}
                        self.order_items[pid]["quantity"] += 1
                        qlabel.configure(text=str(self.order_items[pid]["quantity"]))
                        self.update_order_summary()

                def decrement():
                    if pid in self.order_items and self.order_items[pid]["quantity"] > 0:
                        self.order_items[pid]["quantity"] -= 1
                        qlabel.configure(text=str(self.order_items[pid]["quantity"]))
                        if self.order_items[pid]["quantity"] == 0:
                            del self.order_items[pid]
                        self.update_order_summary()
                return increment, decrement

            increment_callback, decrement_callback = create_callbacks(product_id, name, price, stock, quantity_label)

            ctk.CTkButton(quantity_frame, text="+", width=30, command=increment_callback).pack(side="left")
            ctk.CTkButton(quantity_frame, text="-", width=30, command=decrement_callback).pack(side="left")

        # --- Order Summary ---
        ctk.CTkLabel(order_summary_frame, text="Resumen del Pedido", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        self.summary_text = ctk.CTkTextbox(order_summary_frame, wrap="word", state="disabled")
        self.summary_text.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        self.total_price_label = ctk.CTkLabel(order_summary_frame, text="Total: $0.00", font=ctk.CTkFont(weight="bold"))
        self.total_price_label.grid(row=2, column=0, padx=10, pady=10, sticky="e")

        # --- Buttons ---
        confirm_text = "Confirmar Cambios" if self.is_edit_mode else "Confirmar Pedido"
        ctk.CTkButton(buttons_frame, text=confirm_text, command=self.confirm_action).pack(side="right", padx=5)
        ctk.CTkButton(buttons_frame, text="Cancelar", command=self.close_window).pack(side="right", padx=5)

        self.update_order_summary()
        
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.wait_window(self)

    def update_order_summary(self):
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        
        total_price = 0
        if not self.order_items:
            self.summary_text.insert("1.0", "El pedido está vacío.")
        else:
            for pid, item in self.order_items.items():
                if item['quantity'] > 0:
                    line_total = item["quantity"] * item["price"]
                    total_price += line_total
                    self.summary_text.insert("end", f"{item['name']} x{item['quantity']} - ${line_total:.2f}\n")
        
        self.total_price_label.configure(text=f"Total: ${total_price:.2f}")
        self.summary_text.configure(state="disabled")

    def confirm_action(self):
        product_items_for_db = []
        for pid, item in self.order_items.items():
            product_items_for_db.append((pid, item["quantity"], item["price"]))
        
        success = False
        order_id = None
        if self.is_edit_mode:
            if not product_items_for_db: # Allow empty order in edit mode (means delete)
                # For now, we just close the order. A better implementation might ask for confirmation.
                database.update_order_status(self.order_data['id'], 2) # 2 = cancelled
                success = True
            else:
                success = database.update_order(self.order_data['id'], product_items_for_db, self.order_data)
                if success:
                    CTkMessagebox(master=self.master, title="Éxito", message=f"Pedido #{self.order_data['id']} actualizado con éxito.").get()
                else:
                    CTkMessagebox(master=self, title="Error", message="No se pudo actualizar el pedido.", icon="cancel").get()
        else:
            if not product_items_for_db:
                CTkMessagebox(master=self, title="Error", message="No se puede crear un pedido vacío.", icon="warning").get()
                return
            
            customer_name = self.customer_name_entry.get()
            if not customer_name:
                CTkMessagebox(master=self, title="Error", message="El nombre del cliente no puede estar vacío.", icon="warning").get()
                return
                
            order_id = database.add_order(product_items_for_db, customer_name)
            if order_id:
                CTkMessagebox(master=self.master, title="Éxito", message=f"Pedido #{order_id} creado con éxito.").get()
                success = True
            else:
                CTkMessagebox(master=self, title="Error", message="No se pudo crear el pedido.", icon="cancel").get()
        
        if success:
            self.master.load_orders()
            self.master.load_products()
            self.close_window()
        
    def close_window(self):
        self.grab_release()
        self.destroy()
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Control de Stock")
        self.geometry("1000x700") # Increased size for better layout

        database.init_db() # Initialize the database

        # Configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create sidebar frame with widgets
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Control de Stock", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=20)

        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Productos", command=lambda: self.change_tab("Productos"))
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)
        self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, text="Pedidos", command=lambda: self.change_tab("Pedidos"))
        self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)
        self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, text="Resumen de Ventas", command=lambda: self.change_tab("Resumen de Ventas"))
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)

        # Create tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.tabview.add("Productos")
        self.tabview.add("Pedidos")
        self.tabview.add("Resumen de Ventas")
        self.tabview.tab("Productos").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs
        self.tabview.tab("Pedidos").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Resumen de Ventas").grid_columnconfigure(0, weight=1)

        # =========================================================================================================
        # Productos Tab
        # =========================================================================================================
        self.products_frame = ctk.CTkFrame(self.tabview.tab("Productos"))
        self.products_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Input fields for new product
        self.product_name_label = ctk.CTkLabel(self.products_frame, text="Nombre del Producto:")
        self.product_name_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.product_name_entry = ctk.CTkEntry(self.products_frame, placeholder_text="Nombre")
        self.product_name_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.product_price_label = ctk.CTkLabel(self.products_frame, text="Precio:")
        self.product_price_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.product_price_entry = ctk.CTkEntry(self.products_frame, placeholder_text="0.00")
        self.product_price_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        self.product_stock_label = ctk.CTkLabel(self.products_frame, text="Stock Inicial:")
        self.product_stock_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.product_stock_entry = ctk.CTkEntry(self.products_frame, placeholder_text="0")
        self.product_stock_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        buttons_frame = ctk.CTkFrame(self.products_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.add_product_button = ctk.CTkButton(buttons_frame, text="Agregar Producto", command=self.add_product_event)
        self.add_product_button.pack(side="left", expand=True, padx=5)

        self.save_product_button = ctk.CTkButton(buttons_frame, text="Guardar Cambios", command=self.update_product_event, state="disabled")
        self.save_product_button.pack(side="left", expand=True, padx=5)
        
        self.cancel_edit_button = ctk.CTkButton(buttons_frame, text="Cancelar", command=self.cancel_edit_event, state="disabled")
        self.cancel_edit_button.pack(side="left", expand=True, padx=5)

        self.selected_product_id = None

        # Frame for product list
        self.product_list_frame = ctk.CTkScrollableFrame(self.products_frame, label_text="Lista de Productos")
        self.product_list_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.products_frame.grid_rowconfigure(4, weight=1) # Make the product list frame expand
        self.products_frame.grid_columnconfigure(1, weight=1) # Make the entry fields expand

        # =========================================================================================================
        # Pedidos Tab
        # =========================================================================================================
        self.orders_frame = ctk.CTkFrame(self.tabview.tab("Pedidos"))
        self.orders_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.orders_frame.grid_rowconfigure(1, weight=1) # Make the product list frame expand
        self.orders_frame.grid_columnconfigure(0, weight=1) # Make the entry fields expand

        self.create_order_button = ctk.CTkButton(self.orders_frame, text="Crear Nuevo Pedido", command=self.create_new_order_event)
        self.create_order_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.order_list_frame = ctk.CTkScrollableFrame(self.orders_frame, label_text="Pedidos Pendientes")
        self.order_list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # =========================================================================================================
        # Resumen de Ventas Tab
        # =========================================================================================================
        self.sales_frame = ctk.CTkFrame(self.tabview.tab("Resumen de Ventas"))
        self.sales_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.sales_label = ctk.CTkLabel(self.sales_frame, text="Contenido de Resumen de Ventas")
        self.sales_label.pack(padx=20, pady=20)
        
        self.total_sales_label = ctk.CTkLabel(self.sales_frame, text="Total de Ventas: $0.00", font=ctk.CTkFont(size=24, weight="bold"))
        self.total_sales_label.pack(pady=20)

        self.export_button = ctk.CTkButton(self.sales_frame, text="Exportar y Limpiar Pedidos", command=self.export_and_clear_orders_event)
        self.export_button.pack(pady=10)

        self.load_products() # Load products when app starts
        self.load_orders() # Load orders when app starts
        self.load_sales_summary() # Load sales summary when app starts
    
    def add_product_event(self):
        name = self.product_name_entry.get()
        price_str = self.product_price_entry.get()
        stock_str = self.product_stock_entry.get()

        if not name:
            CTkMessagebox(master=self, title="Error", message="El nombre del producto no puede estar vacío.").get()
            return

        try:
            price = float(price_str)
            if price < 0:
                CTkMessagebox(master=self, title="Error", message="El precio no puede ser negativo.").get()
                return
        except ValueError:
            CTkMessagebox(master=self, title="Error", message="El precio debe ser un número válido.").get()
            return
        
        try:
            stock = int(stock_str)
            if stock < 0:
                CTkMessagebox(master=self, title="Error", message="El stock no puede ser negativo.").get()
                return
        except ValueError:
            CTkMessagebox(master=self, title="Error", message="El stock debe ser un número entero válido.").get()
            return

        if database.add_product(name, price, stock):
            CTkMessagebox(master=self, title="Éxito", message=f"Producto '{name}' agregado con éxito.").get()
            self.product_name_entry.delete(0, ctk.END)
            self.product_price_entry.delete(0, ctk.END)
            self.product_stock_entry.delete(0, ctk.END)
            self.load_products() # Refresh the list
        else:
            CTkMessagebox(master=self, title="Error", message=f"No se pudo agregar el producto '{name}'. Ya existe un producto con ese nombre.").get()

    def update_product_event(self):
        if self.selected_product_id is None:
            return

        name = self.product_name_entry.get()
        price_str = self.product_price_entry.get()
        stock_str = self.product_stock_entry.get()

        if not name:
            CTkMessagebox(master=self, title="Error", message="El nombre del producto no puede estar vacío.").get()
            return

        try:
            price = float(price_str)
            if price < 0:
                CTkMessagebox(master=self, title="Error", message="El precio no puede ser negativo.").get()
                return
        except ValueError:
            CTkMessagebox(master=self, title="Error", message="El precio debe ser un número válido.").get()
            return
        
        try:
            stock = int(stock_str)
            if stock < 0:
                CTkMessagebox(master=self, title="Error", message="El stock no puede ser negativo.").get()
                return
        except ValueError:
            CTkMessagebox(master=self, title="Error", message="El stock debe ser un número entero válido.").get()
            return

        if database.update_product(self.selected_product_id, name, price, stock):
            CTkMessagebox(master=self, title="Éxito", message=f"Producto '{name}' actualizado con éxito.").get()
            self.cancel_edit_event() # Reset the form
            self.load_products() # Refresh the list
        else:
            CTkMessagebox(master=self, title="Error", message=f"No se pudo actualizar el producto '{name}'. Ya existe otro producto con ese nombre.").get()

    def cancel_edit_event(self):
        self.selected_product_id = None
        
        self.product_name_entry.delete(0, ctk.END)
        self.product_price_entry.delete(0, ctk.END)
        self.product_stock_entry.delete(0, ctk.END)
        
        self.add_product_button.configure(state="normal")
        self.save_product_button.configure(state="disabled")
        self.cancel_edit_button.configure(state="disabled")

    def select_product_for_edit(self, product):
        product_id, name, price, stock = product
        
        self.product_name_entry.delete(0, ctk.END)
        self.product_name_entry.insert(0, name)
        
        self.product_price_entry.delete(0, ctk.END)
        self.product_price_entry.insert(0, f"{price:.2f}")
        
        self.product_stock_entry.delete(0, ctk.END)
        self.product_stock_entry.insert(0, stock)
        
        # Store the id of the product being edited
        self.selected_product_id = product_id
        
        # Update buttons
        self.add_product_button.configure(state="disabled")
        self.save_product_button.configure(state="normal")
        self.cancel_edit_button.configure(state="normal")
        
    def load_products(self):
        # Clear existing widgets in the product list frame
        for widget in self.product_list_frame.winfo_children():
            widget.destroy()

        # Add headers to the product list
        ctk.CTkLabel(self.product_list_frame, text="ID", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=2)
        ctk.CTkLabel(self.product_list_frame, text="Nombre", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5, pady=2)
        ctk.CTkLabel(self.product_list_frame, text="Precio", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5, pady=2)
        ctk.CTkLabel(self.product_list_frame, text="Stock", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5, pady=2)
        ctk.CTkLabel(self.product_list_frame, text="Acciones", font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=5, pady=2)
        
        products = database.get_products()
        for i, product in enumerate(products):
            product_id, name, price, stock = product
            ctk.CTkLabel(self.product_list_frame, text=product_id).grid(row=i+1, column=0, padx=5, pady=2)
            ctk.CTkLabel(self.product_list_frame, text=name).grid(row=i+1, column=1, padx=5, pady=2)
            ctk.CTkLabel(self.product_list_frame, text=f"{price:.2f}").grid(row=i+1, column=2, padx=5, pady=2)
            ctk.CTkLabel(self.product_list_frame, text=stock).grid(row=i+1, column=3, padx=5, pady=2)

            edit_button = ctk.CTkButton(self.product_list_frame, text="Editar", command=lambda p=product: self.select_product_for_edit(p))
            edit_button.grid(row=i+1, column=4, padx=5, pady=2)
    
    def edit_order_event(self, order_data):
        # Open a new window for editing an order
        if hasattr(self, 'order_window') and self.order_window.winfo_exists():
            self.order_window.focus() # If it exists, focus it
            return
            
        self.order_window = CreateOrderWindow(self, order_data)

    def create_new_order_event(self):
        # Check if a window is already open
        if hasattr(self, 'order_window') and self.order_window.winfo_exists():
            self.order_window.focus() # If it exists, focus it
            return

        # Open a new window for creating an order
        self.order_window = CreateOrderWindow(self)

    def load_orders(self):
        # This method will be implemented later to load and display pending orders
        # Clear existing widgets in the order list frame
        for widget in self.order_list_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.order_list_frame, text="Cliente", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=2)
        ctk.CTkLabel(self.order_list_frame, text="Items", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5, pady=2)
        ctk.CTkLabel(self.order_list_frame, text="Total", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5, pady=2)
        ctk.CTkLabel(self.order_list_frame, text="Acciones", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5, pady=2)

        orders = database.get_orders(status=0) # Get pending orders
        if not orders:
            ctk.CTkLabel(self.order_list_frame, text="No hay pedidos pendientes.").grid(row=1, column=0, columnspan=4, padx=10, pady=10)
            return

        for i, order in enumerate(orders):
            order_id = order["id"]
            total_price = order["total_price"]

            items_str = ", ".join([f"{item['product_name']} (x{item['quantity']})" for item in order["items"]])

            ctk.CTkLabel(self.order_list_frame, text=order.get("customer_name", "N/A")).grid(row=i+1, column=0, padx=5, pady=2, sticky="w")
            ctk.CTkLabel(self.order_list_frame, text=items_str, wraplength=200, justify="left").grid(row=i+1, column=1, padx=5, pady=2, sticky="w")
            ctk.CTkLabel(self.order_list_frame, text=f"${total_price:.2f}").grid(row=i+1, column=2, padx=5, pady=2, sticky="w")
            
            actions_frame = ctk.CTkFrame(self.order_list_frame)
            actions_frame.grid(row=i+1, column=3, padx=5, pady=2, sticky="ew")

            edit_button = ctk.CTkButton(actions_frame, text="Editar", command=lambda order_data=order: self.edit_order_event(order_data))
            edit_button.pack(side="left", padx=2)

            close_button = ctk.CTkButton(actions_frame, text="Cerrar", command=lambda oid=order_id: self.close_order(oid))
            close_button.pack(side="left", padx=2)

    def close_order(self, order_id):
        database.update_order_status(order_id, 1) # Set status to completed
        CTkMessagebox(master=self, title="Éxito", message=f"Pedido #{order_id} cerrado con éxito.").get()
        self.load_orders() # Refresh pending orders
        self.load_sales_summary() # Refresh sales summary

    def export_and_clear_orders_event(self):
        pending_orders = database.get_orders(status=0)
        if pending_orders:
            CTkMessagebox(master=self, title="Error", message="No se pueden exportar los pedidos mientras haya pedidos pendientes. Por favor, cierre todos los pedidos antes de exportar.", icon="warning").get()
            return

        completed_orders = database.get_orders(status=1)
        if not completed_orders:
            CTkMessagebox(master=self, title="Info", message="No hay pedidos completados para exportar.").get()
            return

        # Create csv directory if it doesn't exist
        csv_dir = "csv_exports"
        os.makedirs(csv_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(csv_dir, f"pedidos_{timestamp}.csv")

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['order_id', 'customer_name', 'order_date', 'product_name', 'quantity', 'item_price', 'total_order_price']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for order in completed_orders:
                    for item in order['items']:
                        writer.writerow({
                            'order_id': order['id'],
                            'customer_name': order.get('customer_name', 'N/A'),
                            'order_date': order['order_date'],
                            'product_name': item['product_name'],
                            'quantity': item['quantity'],
                            'item_price': item['item_price'],
                            'total_order_price': order['total_price']
                        })
            
            # If CSV generation is successful, clear the orders
            if database.clear_all_orders():
                CTkMessagebox(master=self, title="Éxito", message=f"Pedidos exportados a '{filename}' y borrados de la base de datos con éxito.").get()
                self.load_orders()
                self.load_sales_summary()
            else:
                CTkMessagebox(master=self, title="Error", message="Los pedidos fueron exportados, pero no se pudieron borrar de la base de datos.", icon="cancel").get()

        except Exception as e:
            CTkMessagebox(master=self, title="Error", message=f"No se pudo generar el archivo CSV: {e}", icon="cancel").get()


    def load_sales_summary(self):
        total_sales = database.get_total_sales()
        self.total_sales_label.configure(text=f"Total de Ventas: ${total_sales:.2f}")

    def change_tab(self, tab_name):
        self.tabview.set(tab_name)
        if tab_name == "Productos":
            self.load_products()
        elif tab_name == "Pedidos":
            self.load_orders()
        elif tab_name == "Resumen de Ventas":
            self.load_sales_summary()


if __name__ == "__main__":
    app = App()
    app.mainloop()
