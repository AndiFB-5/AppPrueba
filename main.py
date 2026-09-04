import customtkinter as ctk
import database

import os
import csv
from datetime import datetime
import platform
import subprocess
from PIL import Image
from tkinter import messagebox

class PaymentMethodDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)

        self.title("Seleccionar Método de Pago")
        self.geometry("300x200")
        self.master = master
        self.result = None

        self.label = ctk.CTkLabel(self, text="Seleccione el método de pago:")
        self.label.pack(pady=10)

        self.payment_method_var = ctk.StringVar(value="Efectivo")

        self.radio_cash = ctk.CTkRadioButton(self, text="Efectivo", variable=self.payment_method_var, value="Efectivo")
        self.radio_cash.pack(pady=5)

        self.radio_transfer = ctk.CTkRadioButton(self, text="Transferencia", variable=self.payment_method_var, value="Transferencia")
        self.radio_transfer.pack(pady=5)

        self.radio_300 = ctk.CTkRadioButton(self, text="300", variable=self.payment_method_var, value="300")
        self.radio_300.pack(pady=5)

        self.ok_button = ctk.CTkButton(self, text="Aceptar", command=self.ok_event)
        self.ok_button.pack(pady=10)
        
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.cancel_event)
        self.wait_window(self)

    def ok_event(self):
        self.result = self.payment_method_var.get()
        self.destroy()

    def cancel_event(self):
        self.result = None
        self.destroy()

    def get_input(self):
        return self.result

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
        
        # --- Common variables ---
        initial_payment = ""
        if self.is_edit_mode:
            initial_payment = self.order_data.get('metodo_pago', '')
            if initial_payment is None:
                initial_payment = ""
        self.payment_method_var = ctk.StringVar(value=initial_payment)

        if not self.is_edit_mode:
            ctk.CTkLabel(top_frame, text="Nombre del Cliente:").pack(side="left", padx=(10,0))
            self.customer_name_entry = ctk.CTkEntry(top_frame, placeholder_text="Nombre", width=140)
            self.customer_name_entry.pack(side="left", padx=10)
            
            self.es_socio_var = ctk.IntVar()
            self.socio_checkbox = ctk.CTkCheckBox(top_frame, text="Socio", variable=self.es_socio_var, command=self.update_order_summary)
            self.socio_checkbox.pack(side="left", padx=10)

            self.es_barra_var = ctk.IntVar()
            self.barra_checkbox = ctk.CTkCheckBox(top_frame, text="Es Barra", variable=self.es_barra_var, command=self.toggle_barra_event)
            self.barra_checkbox.pack(side="left", padx=10)
        else:
            ctk.CTkLabel(top_frame, text=f"Cliente: {self.order_data.get('customer_name', 'N/A')}", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
            self.es_socio_var = ctk.IntVar(value=self.order_data.get('es_socio', 0))
            self.socio_checkbox = ctk.CTkCheckBox(top_frame, text="Socio", variable=self.es_socio_var, command=self.update_order_summary)
            self.socio_checkbox.pack(side="left", padx=10)

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=3) # Product list gets more space
        main_frame.grid_columnconfigure(1, weight=1) # Summary is narrower
        main_frame.grid_rowconfigure(0, weight=1)

        product_list_frame = ctk.CTkScrollableFrame(main_frame, label_text="Productos Disponibles")
        product_list_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        order_summary_frame = ctk.CTkFrame(main_frame, width=250) # Reduced width
        order_summary_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        order_summary_frame.grid_rowconfigure(1, weight=1)
        order_summary_frame.grid_propagate(False) # Force width constraint

        buttons_frame = ctk.CTkFrame(self)
        buttons_frame.pack(fill="x", padx=10, pady=(0, 10))

        # --- Payment Method Selection (Integrated at bottom-left) ---
        self.payment_frame = ctk.CTkFrame(buttons_frame, fg_color="transparent")
        self.payment_frame.pack(side="left", padx=10)
        
        ctk.CTkLabel(self.payment_frame, text="Pago:").pack(side="left", padx=5)
        self.radio_cash = ctk.CTkRadioButton(self.payment_frame, text="Efectivo", variable=self.payment_method_var, value="Efectivo")
        self.radio_cash.pack(side="left", padx=5)
        self.radio_transfer = ctk.CTkRadioButton(self.payment_frame, text="Transf.", variable=self.payment_method_var, value="Transferencia")
        self.radio_transfer.pack(side="left", padx=5)
        self.radio_300 = ctk.CTkRadioButton(self.payment_frame, text="300", variable=self.payment_method_var, value="300")
        self.radio_300.pack(side="left", padx=5)

        # --- Product List ---
        products = database.get_products()
        self.product_labels = {} # To update quantity labels
        self.product_name_labels = {} # To update name/stock labels
        
        # Group products by category
        categories = {}
        for product in products:
            category = product[4] or "Sin Categoría"
            if category not in categories:
                categories[category] = []
            categories[category].append(product)

        for category_name, category_products in categories.items():
            # Category Header
            category_label = ctk.CTkLabel(product_list_frame, text=category_name, font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
            category_label.pack(fill="x", padx=10, pady=(8, 2))
            
            # Grid frame for products in this category (3 columns)
            cat_grid_frame = ctk.CTkFrame(product_list_frame, fg_color="transparent")
            cat_grid_frame.pack(fill="x", padx=5, pady=2)
            cat_grid_frame.grid_columnconfigure((0, 1, 2), weight=1)

            for idx, product in enumerate(category_products):
                product_id, name, price, stock, category = product
                
                # Use grid for 3 columns
                row_idx = idx // 3
                col_idx = idx % 3
                
                product_frame = ctk.CTkFrame(cat_grid_frame)
                product_frame.grid(row=row_idx, column=col_idx, padx=2, pady=1, sticky="nsew")
                product_frame.grid_columnconfigure(0, weight=1)
                
                initial_quantity = self.order_items.get(product_id, {}).get("quantity", 0)
                total_pool = stock + initial_quantity # Total available for this session

                # Only show the name, very compact
                display_text = f"{name} ({stock})" if stock < 5 else name
                text_color = "red" if stock < 5 else None
                name_label = ctk.CTkLabel(product_frame, text=display_text, font=ctk.CTkFont(size=11, weight="bold"), anchor="w", text_color=text_color)
                name_label.grid(row=0, column=0, sticky="w", padx=4, pady=2)
                self.product_name_labels[product_id] = name_label

                quantity_frame = ctk.CTkFrame(product_frame, fg_color="transparent")
                quantity_frame.grid(row=0, column=1, sticky="e", padx=2)

                def create_callbacks(pid, pname, pprice, ptotal_pool, qlabel, nlabel):
                    # Get the default text color based on the current theme
                    default_color = nlabel.cget("text_color")
                    
                    def update_product_display():
                        current_qty = self.order_items.get(pid, {}).get("quantity", 0)
                        remaining = ptotal_pool - current_qty
                        if remaining < 5:
                            nlabel.configure(text=f"{pname} ({remaining})", text_color="red")
                        else:
                            nlabel.configure(text=pname, text_color=default_color)
                        qlabel.configure(text=str(current_qty))

                    def increment(event=None):
                        current_quantity = self.order_items.get(pid, {}).get("quantity", 0)
                        if current_quantity < ptotal_pool:
                            if pid not in self.order_items:
                                self.order_items[pid] = {"name": pname, "quantity": 0, "price": pprice}
                            self.order_items[pid]["quantity"] += 1
                            update_product_display()
                            self.update_order_summary()

                    def decrement(event=None):
                        if pid in self.order_items and self.order_items[pid]["quantity"] > 0:
                            self.order_items[pid]["quantity"] -= 1
                            if self.order_items[pid]["quantity"] == 0:
                                del self.order_items[pid]
                            update_product_display()
                            self.update_order_summary()
                    return increment, decrement

                quantity_label = ctk.CTkLabel(quantity_frame, text=str(initial_quantity), width=20, font=ctk.CTkFont(size=11, weight="bold"))
                self.product_labels[product_id] = quantity_label
                
                increment_callback, decrement_callback = create_callbacks(product_id, name, price, total_pool, quantity_label, name_label)

                # Bind events to every part of the card
                for widget in [product_frame, name_label, quantity_frame, quantity_label]:
                    widget.bind("<Button-1>", increment_callback)
                    widget.bind("<Button-2>", decrement_callback)
                    widget.bind("<Button-3>", decrement_callback)

                quantity_label.pack(padx=2)

        # --- Order Summary ---
        ctk.CTkLabel(order_summary_frame, text="Resumen del Pedido", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        self.summary_text = ctk.CTkTextbox(order_summary_frame, wrap="word", state="disabled")
        self.summary_text.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        self.total_price_label = ctk.CTkLabel(order_summary_frame, text="Total: $0.00", font=ctk.CTkFont(weight="bold"))
        self.total_price_label.grid(row=2, column=0, padx=10, pady=10, sticky="e")

        # --- Buttons ---
        confirm_text = "Confirmar Cambios" if self.is_edit_mode else "Confirmar Pedido"
        ctk.CTkButton(buttons_frame, text=confirm_text, command=self.confirm_action).pack(side="right", padx=2)
        ctk.CTkButton(buttons_frame, text="Confirmar y Cerrar", command=lambda: self.confirm_action(close_order=True), fg_color="green", hover_color="#228b22").pack(side="right", padx=2)
        ctk.CTkButton(buttons_frame, text="Cancelar", command=self.close_window).pack(side="right", padx=2)

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
        
        if self.es_socio_var.get() == 1:
            discount = total_price * 0.15
            total_price *= 0.85
            self.summary_text.insert("end", f"\nDescuento Socio (15%): -${discount:.2f}\n")

        self.total_price_label.configure(text=f"Total: ${total_price:.2f}")
        self.summary_text.configure(state="disabled")

    def confirm_action(self, close_order=False):
        product_items_for_db = []
        for pid, item in self.order_items.items():
            if item["quantity"] > 0:
                product_items_for_db.append((pid, item["quantity"], item["price"]))
        
        success = False
        es_socio = self.es_socio_var.get()
        payment_method = self.payment_method_var.get()
        
        # Reset visual feedback
        if not self.is_edit_mode:
            self.customer_name_entry.configure(border_color=["#979DA2", "#565B5E"]) # Default colors
        self.payment_frame.configure(fg_color="transparent")

        if self.is_edit_mode:
            valid = True
            if close_order and not payment_method:
                self.payment_frame.configure(fg_color="#3B0000") # Dark red background for feedback
                valid = False
                
            if valid:
                if not product_items_for_db:
                    database.update_order_status_and_payment_method(self.order_data['id'], 2, None) # 2 = cancelled
                    success = True
                else:
                    success = database.update_order(self.order_data['id'], product_items_for_db, self.order_data, es_socio)
                    if success and close_order:
                        database.update_order_status_and_payment_method(self.order_data['id'], 1, payment_method)
        else:
            customer_name = self.customer_name_entry.get()
            
            # Validation with visual feedback
            valid = True
            if not customer_name:
                self.customer_name_entry.configure(border_color="red")
                valid = False
            
            if not product_items_for_db:
                # We could highlight the product list frame, but just preventing action is usually enough
                # for now let's just focus on the name entry which is the most common miss
                valid = False

            status = 0
            
            if close_order:
                if not payment_method:
                    # Highlight payment selection if missing
                    self.payment_frame.configure(fg_color="#3B0000") # Dark red background for feedback
                    valid = False
                else:
                    status = 1

            if valid:
                order_id = database.add_order(product_items_for_db, customer_name, es_socio, status, payment_method)
                if order_id is not None:
                    success = True
        
        if success:
            # Mark all tabs as needing refresh
            for tab in self.master.needs_refresh:
                self.master.needs_refresh[tab] = True
            
            # Only refresh the CURRENTLY VISIBLE tab to keep response fast
            self.master.on_tab_change()
            
            self.close_window()
        
    def close_window(self):
        self.grab_release()
        self.destroy()

    def toggle_barra_event(self):
        if self.es_barra_var.get() == 1:
            self.customer_name_entry.delete(0, ctk.END)
            self.customer_name_entry.insert(0, "Barra")
            self.customer_name_entry.configure(state="disabled")
        else:
            self.customer_name_entry.configure(state="normal")
            self.customer_name_entry.delete(0, ctk.END)
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
        self.sidebar_frame.grid(row=0, column=0, rowspan=6, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Control de Stock", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=20)

        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Productos", command=lambda: self.change_tab("Productos"))
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)
        self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, text="Pedidos", command=lambda: self.change_tab("Pedidos"))
        self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)
        self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, text="Resumen de Ventas", command=lambda: self.change_tab("Resumen de Ventas"))
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)

        # Add image to sidebar
        self.sidebar_image = ctk.CTkImage(Image.open("icon.png"), size=(160, 200))
        self.sidebar_image_label = ctk.CTkLabel(self.sidebar_frame, text="", image=self.sidebar_image)
        self.sidebar_image_label.grid(row=4, column=0, pady=(30, 0), sticky="n") # Adjust row and pady as needed

        # Performance optimization: Refresh flags
        self.needs_refresh = {
            "Productos": True,
            "Pedidos": True,
            "Resumen de Ventas": True
        }

        # Create tabview
        self.tabview = ctk.CTkTabview(self, command=self.on_tab_change)
        self.tabview.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.tabview.add("Productos")
        self.tabview.add("Pedidos")
        self.tabview.add("Resumen de Ventas")
        self.tabview.tab("Productos").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs
        self.tabview.tab("Pedidos").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Resumen de Ventas").grid_columnconfigure(0, weight=1)

        # Trigger initial tab build
        self.on_tab_change()

    def build_products_tab(self):
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

        self.product_category_label = ctk.CTkLabel(self.products_frame, text="Categoría:")
        self.product_category_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.product_categories = ["Pizzas", "Empanadas", "Bebidas"]
        self.product_category_option = ctk.CTkOptionMenu(self.products_frame, values=self.product_categories)
        self.product_category_option.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        self.product_category_option.set("Pizzas") # Default value

        buttons_frame = ctk.CTkFrame(self.products_frame)
        buttons_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.add_product_button = ctk.CTkButton(buttons_frame, text="Agregar Producto", command=self.add_product_event)
        self.add_product_button.pack(side="left", expand=True, padx=5)

        self.save_product_button = ctk.CTkButton(buttons_frame, text="Guardar Cambios", command=self.update_product_event, state="disabled")
        self.save_product_button.pack(side="left", expand=True, padx=5)
        
        self.cancel_edit_button = ctk.CTkButton(buttons_frame, text="Cancelar", command=self.cancel_edit_event, state="disabled")
        self.cancel_edit_button.pack(side="left", expand=True, padx=5)

        self.selected_product_id = None

        # Frame de ordenamiento
        sorting_frame = ctk.CTkFrame(self.products_frame, fg_color="transparent")
        sorting_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=(5, 0), sticky="ew")
        
        ctk.CTkLabel(sorting_frame, text="Ordenar por:", font=ctk.CTkFont(size=12)).pack(side="left", padx=5)
        self.product_sort_options = [
            "Categoría",
            "Nombre",
            "Precio (Menor a Mayor)",
            "Precio (Mayor a Menor)",
            "Stock (Menor a Mayor)"
        ]
        self.product_sort_option = ctk.CTkOptionMenu(
            sorting_frame, 
            values=self.product_sort_options, 
            command=lambda val: self.load_products()
        )
        self.product_sort_option.pack(side="left", padx=5)
        self.product_sort_option.set("Categoría") # Default sorting

        # Frame for product list
        self.product_list_frame = ctk.CTkScrollableFrame(self.products_frame, label_text="Lista de Productos")
        self.product_list_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.products_frame.grid_rowconfigure(6, weight=1) # Make the product list frame expand
        self.products_frame.grid_columnconfigure(1, weight=1) # Make the entry fields expand

        self.load_products()

    def build_orders_tab(self):
        self.orders_frame = ctk.CTkFrame(self.tabview.tab("Pedidos"))
        self.orders_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.orders_frame.grid_rowconfigure(1, weight=1) # Make the product list frame expand
        self.orders_frame.grid_columnconfigure(0, weight=1) # Make the entry fields expand

        self.create_order_button = ctk.CTkButton(self.orders_frame, text="Crear Nuevo Pedido", command=self.create_new_order_event)
        self.create_order_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.order_list_frame = ctk.CTkScrollableFrame(self.orders_frame, label_text="Pedidos Pendientes")
        self.order_list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.load_orders()

    def build_sales_tab(self):
        self.sales_frame = ctk.CTkFrame(self.tabview.tab("Resumen de Ventas"))
        self.sales_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.sales_label = ctk.CTkLabel(self.sales_frame, text="Contenido de Resumen de Ventas")
        self.sales_label.pack(padx=20, pady=20)
        
        self.total_sales_label = ctk.CTkLabel(self.sales_frame, text="Total de Ventas: $0.00", font=ctk.CTkFont(size=24, weight="bold"))
        self.total_sales_label.pack(pady=20)

        self.total_cash_sales_label = ctk.CTkLabel(self.sales_frame, text="Total en Efectivo: $0.00", font=ctk.CTkFont(size=20))
        self.total_cash_sales_label.pack(pady=10)

        self.total_transfer_sales_label = ctk.CTkLabel(self.sales_frame, text="Total Transferencias: $0.00", font=ctk.CTkFont(size=20))
        self.total_transfer_sales_label.pack(pady=10)

        self.total_300_sales_label = ctk.CTkLabel(self.sales_frame, text="Total en 300: $0.00", font=ctk.CTkFont(size=20))
        self.total_300_sales_label.pack(pady=10)

        self.export_button = ctk.CTkButton(self.sales_frame, text="Exportar y Limpiar Pedidos", command=self.export_and_clear_orders_event)
        self.export_button.pack(pady=10)

        self.open_csv_folder_button = ctk.CTkButton(self.sales_frame, text="Abrir Carpeta de CSVs", command=self.open_csv_folder)
        self.open_csv_folder_button.pack(pady=10)

        self.load_sales_summary()
    
    def add_product_event(self):
        name = self.product_name_entry.get()
        price_str = self.product_price_entry.get()
        stock_str = self.product_stock_entry.get()
        category = self.product_category_option.get()

        # Reset colors
        self.product_name_entry.configure(border_color=["#979DA2", "#565B5E"])
        self.product_price_entry.configure(border_color=["#979DA2", "#565B5E"])
        self.product_stock_entry.configure(border_color=["#979DA2", "#565B5E"])

        valid = True
        if not name:
            self.product_name_entry.configure(border_color="red")
            valid = False

        try:
            price = float(price_str)
            if price < 0:
                self.product_price_entry.configure(border_color="red")
                valid = False
        except ValueError:
            self.product_price_entry.configure(border_color="red")
            valid = False
        
        try:
            stock = int(stock_str)
            if stock < 0:
                self.product_stock_entry.configure(border_color="red")
                valid = False
        except ValueError:
            self.product_stock_entry.configure(border_color="red")
            valid = False

        if not valid:
            return

        if database.add_product(name, price, stock, category):
            self.product_name_entry.delete(0, ctk.END)
            self.product_price_entry.delete(0, ctk.END)
            self.product_stock_entry.delete(0, ctk.END)
            self.product_category_option.set("Pizzas") # Reset to default
            self.load_products() # Refresh the list

    def update_product_event(self):
        if self.selected_product_id is None:
            return

        name = self.product_name_entry.get()
        price_str = self.product_price_entry.get()
        stock_str = self.product_stock_entry.get()
        category = self.product_category_option.get()

        # Reset colors
        self.product_name_entry.configure(border_color=["#979DA2", "#565B5E"])
        self.product_price_entry.configure(border_color=["#979DA2", "#565B5E"])
        self.product_stock_entry.configure(border_color=["#979DA2", "#565B5E"])

        valid = True
        if not name:
            self.product_name_entry.configure(border_color="red")
            valid = False

        try:
            price = float(price_str)
            if price < 0:
                self.product_price_entry.configure(border_color="red")
                valid = False
        except ValueError:
            self.product_price_entry.configure(border_color="red")
            valid = False
        
        try:
            stock = int(stock_str)
            if stock < 0:
                self.product_stock_entry.configure(border_color="red")
                valid = False
        except ValueError:
            self.product_stock_entry.configure(border_color="red")
            valid = False

        if not valid:
            return

        if database.update_product(self.selected_product_id, name, price, stock, category):
            self.cancel_edit_event() # Reset the form
            self.load_products() # Refresh the list

    def cancel_edit_event(self):
        self.selected_product_id = None
        
        self.product_name_entry.delete(0, ctk.END)
        self.product_price_entry.delete(0, ctk.END)
        self.product_stock_entry.delete(0, ctk.END)
        self.product_category_option.set("Pizzas") # Reset to default
        
        self.add_product_button.configure(state="normal")
        self.save_product_button.configure(state="disabled")
        self.cancel_edit_button.configure(state="disabled")

    def select_product_for_edit(self, product):
        product_id, name, price, stock, category = product
        
        self.product_name_entry.delete(0, ctk.END)
        self.product_name_entry.insert(0, name)
        
        self.product_price_entry.delete(0, ctk.END)
        self.product_price_entry.insert(0, f"{price:.2f}")
        
        self.product_stock_entry.delete(0, ctk.END)
        self.product_stock_entry.insert(0, stock)

        # Set dropdown value
        if category in self.product_categories:
            self.product_category_option.set(category)
        else:
            self.product_category_option.set("Pizzas") # Fallback to Pizzas if something else is in the DB
        
        # Store the id of the product being edited
        self.selected_product_id = product_id
        
        # Update buttons
        self.add_product_button.configure(state="disabled")
        self.save_product_button.configure(state="normal")
        self.cancel_edit_button.configure(state="normal")
        
    def load_products(self):
        if not hasattr(self, 'product_list_frame') or not self.product_list_frame.winfo_exists():
            return
        # Clear existing widgets in the product list frame
        for widget in self.product_list_frame.winfo_children():
            widget.destroy()

        # Add headers to the product list
        ctk.CTkLabel(self.product_list_frame, text="ID", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=2)
        ctk.CTkLabel(self.product_list_frame, text="Nombre", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5, pady=2)
        ctk.CTkLabel(self.product_list_frame, text="Categoría", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5, pady=2)
        ctk.CTkLabel(self.product_list_frame, text="Precio", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5, pady=2)
        ctk.CTkLabel(self.product_list_frame, text="Stock", font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=5, pady=2)
        ctk.CTkLabel(self.product_list_frame, text="Acciones", font=ctk.CTkFont(weight="bold")).grid(row=0, column=5, padx=5, pady=2)
        
        sort_by = "Categoría"
        if hasattr(self, 'product_sort_option'):
            sort_by = self.product_sort_option.get()

        products = database.get_products(order_by=sort_by)
        for i, product in enumerate(products):
            product_id, name, price, stock, category = product
            ctk.CTkLabel(self.product_list_frame, text=product_id).grid(row=i+1, column=0, padx=5, pady=2)
            ctk.CTkLabel(self.product_list_frame, text=name).grid(row=i+1, column=1, padx=5, pady=2)
            ctk.CTkLabel(self.product_list_frame, text=category if category else "Sin Categoría").grid(row=i+1, column=2, padx=5, pady=2)
            ctk.CTkLabel(self.product_list_frame, text=f"{price:.2f}").grid(row=i+1, column=3, padx=5, pady=2)
            ctk.CTkLabel(self.product_list_frame, text=stock).grid(row=i+1, column=4, padx=5, pady=2)

            edit_button = ctk.CTkButton(self.product_list_frame, text="Editar", command=lambda p=product: self.select_product_for_edit(p))
            edit_button.grid(row=i+1, column=5, padx=5, pady=2)
    
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
        if not hasattr(self, 'order_list_frame') or not self.order_list_frame.winfo_exists():
            return
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
            if order.get("es_socio") == 1:
                total_price *= 0.85

            items_str = ", ".join([f"{item['product_name']} (x{item['quantity']})" for item in order["items"]])

            ctk.CTkLabel(self.order_list_frame, text=order.get("customer_name", "N/A")).grid(row=i+1, column=0, padx=5, pady=2, sticky="w")
            ctk.CTkLabel(self.order_list_frame, text=items_str, wraplength=200, justify="left").grid(row=i+1, column=1, padx=5, pady=2, sticky="w")
            ctk.CTkLabel(self.order_list_frame, text=f"${total_price:.2f}").grid(row=i+1, column=2, padx=5, pady=2, sticky="w")
            
            actions_frame = ctk.CTkFrame(self.order_list_frame, fg_color="transparent")
            actions_frame.grid(row=i+1, column=3, padx=5, pady=2, sticky="ew")

            edit_button = ctk.CTkButton(actions_frame, text="Editar", command=lambda order_data=order: self.edit_order_event(order_data))
            edit_button.pack(side="left", padx=2)

            close_button = ctk.CTkButton(actions_frame, text="Cerrar", command=lambda oid=order_id: self.close_order(oid))
            close_button.pack(side="left", padx=2)

    def close_order(self, order_id):
        dialog = PaymentMethodDialog(self)
        payment_method = dialog.get_input()
        
        if payment_method:
            database.update_order_status_and_payment_method(order_id, 1, payment_method) # Set status to completed
            self.load_orders() # Refresh pending orders
            self.load_sales_summary() # Refresh sales summary

    def open_csv_folder(self):
        csv_dir = "csv_exports"
        # Create directory if it doesn't exist
        os.makedirs(csv_dir, exist_ok=True)
        
        system = platform.system()
        if system == "Windows":
            subprocess.run(["start", csv_dir], shell=True)
        elif system == "Darwin": # macOS
            subprocess.run(["open", csv_dir])
        else: # Linux
            subprocess.run(["xdg-open", csv_dir])

    def export_and_clear_orders_event(self):
        pending_orders = database.get_orders(status=0)
        if pending_orders:
            messagebox.showwarning("Atención", "No se puede exportar: Todavía hay pedidos PENDIENTES. Ciérralos o cancélalos antes de limpiar la caja.")
            return

        completed_orders = database.get_orders(status=1)
        if not completed_orders:
            messagebox.showinfo("Info", "No hay pedidos completados para exportar hoy.")
            return

        # Create csv directory if it doesn't exist
        csv_dir = "csv_exports"
        os.makedirs(csv_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(csv_dir, f"pedidos_{timestamp}.csv")

        import json

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['order_id', 'customer_name', 'order_date', 'metodo_pago', 'productos', 'total_order_price']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # No header row printed per user requirement
                for order in completed_orders:
                    es_socio = order.get('es_socio') == 1
                    
                    productos_list = []
                    total_calculated = 0.0
                    
                    for item in order['items']:
                        unit_price = item['item_price']
                        if es_socio:
                            unit_price = round(unit_price * 0.85, 2)
                        
                        line_total = round(item['quantity'] * unit_price, 2)
                        total_calculated += line_total
                        
                        productos_list.append({
                            'producto': item['product_name'],
                            'cantidad': item['quantity'],
                            'precio_unitario': unit_price
                        })
                    
                    # Round final total to 2 decimal places
                    total_calculated = round(total_calculated, 2)
                    
                    writer.writerow({
                        'order_id': order['id'],
                        'customer_name': order.get('customer_name', 'N/A'),
                        'order_date': order['order_date'],
                        'metodo_pago': order.get('metodo_pago', 'N/A'),
                        'productos': json.dumps(productos_list, ensure_ascii=False),
                        'total_order_price': total_calculated
                    })
            
            # If CSV generation is successful, clear the orders
            if database.clear_all_orders():
                # Mark all tabs as needing refresh
                for tab in self.needs_refresh:
                    self.needs_refresh[tab] = True
                
                # Update current visible tab
                self.on_tab_change()
                print(f"[SUCCESS] Pedidos exportados a {filename} y base de datos limpiada.")

        except Exception as e:
            print(f"Error: {e}")


    def load_sales_summary(self):
        if not hasattr(self, 'total_sales_label') or not self.total_sales_label.winfo_exists():
            return
        total_sales = database.get_total_sales()
        total_cash_sales = database.get_total_sales_by_payment_method("Efectivo")
        total_transfer_sales = database.get_total_sales_by_payment_method("Transferencia")
        total_300_sales = database.get_total_sales_by_payment_method("300")
        
        self.total_sales_label.configure(text=f"Total de Ventas: ${total_sales:.2f}")
        self.total_cash_sales_label.configure(text=f"Total en Efectivo: ${total_cash_sales:.2f}")
        self.total_transfer_sales_label.configure(text=f"Total Transferencias: ${total_transfer_sales:.2f}")
        self.total_300_sales_label.configure(text=f"Total en 300: ${total_300_sales:.2f}")

    def on_tab_change(self):
        tab_name = self.tabview.get()
        
        # Destroy all existing widgets inside the tabs to prevent rendering issues on macOS
        for child in self.tabview.tab("Productos").winfo_children():
            child.destroy()
        for child in self.tabview.tab("Pedidos").winfo_children():
            child.destroy()
        for child in self.tabview.tab("Resumen de Ventas").winfo_children():
            child.destroy()
            
        if tab_name == "Productos":
            self.build_products_tab()
        elif tab_name == "Pedidos":
            self.build_orders_tab()
        elif tab_name == "Resumen de Ventas":
            self.build_sales_tab()
        
        # Force a complete layout and repaint refresh on macOS
        # A tiny, invisible 1-pixel change triggers a Cocoa/Tkinter <Configure> event,
        # which forces the macOS window server to correctly redraw all canvas elements.
        try:
            w = self.winfo_width()
            h = self.winfo_height()
            x = self.winfo_x()
            y = self.winfo_y()
            if w > 1 and h > 1:
                self.geometry(f"{w}x{h+1}+{x}+{y}")
                self.update_idletasks()
                self.geometry(f"{w}x{h}+{x}+{y}")
                self.update_idletasks()
        except Exception:
            # Fallback to standard updates if geometries cannot be parsed yet
            self.update_idletasks()
            self.update()

    def change_tab(self, tab_name):
        self.tabview.set(tab_name)
        self.on_tab_change()


if __name__ == "__main__":
    app = App()
    app.mainloop()
