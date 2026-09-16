import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sqlite3
from datetime import datetime

DB_NAME = "gimnasio.db"

def inicializar_db_stock():
    """Crea la tabla de productos si no existe y actualiza campos."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL,
            fecha_vencimiento TEXT,
            nota TEXT
        )
    ''')

    cursor.execute("PRAGMA table_info(productos)")
    columnas = [col[1] for col in cursor.fetchall()]

    if "fecha_vencimiento" not in columnas:
        cursor.execute("ALTER TABLE productos ADD COLUMN fecha_vencimiento TEXT")
    if "nota" not in columnas:
        cursor.execute("ALTER TABLE productos ADD COLUMN nota TEXT")

    conn.commit()
    conn.close()

def setup_tab_stock(frame_padre, app):
    inicializar_db_stock()

    def validar_entero(P):
        if P == "": return True
        return P.isdigit()

    def validar_decimal(P):
        if P == "": return True
        if P == ".": return True
        try:
            float(P)
            return True
        except ValueError:
            return False

    vcmd_entero = (frame_padre.register(validar_entero), '%P')
    vcmd_decimal = (frame_padre.register(validar_decimal), '%P')

    frame_padre.columnconfigure(0, weight=1, minsize=300)
    frame_padre.columnconfigure(1, weight=3)
    frame_padre.rowconfigure(0, weight=1)

    panel_izq = ttk.Frame(frame_padre, padding=20)
    panel_izq.grid(row=0, column=0, sticky=NSEW)

    ttk.Label(panel_izq, text="🛒 Registrar Producto", font=("Segoe UI", 16, "bold"), bootstyle="primary").pack(pady=(0, 20), anchor=W)

    ttk.Label(panel_izq, text="Nombre del Producto:", font=("Segoe UI", 10)).pack(anchor=W, pady=(5, 2))
    entry_nombre = ttk.Entry(panel_izq, font=("Segoe UI", 10))
    entry_nombre.pack(fill=X)

    ttk.Label(panel_izq, text="Precio de Venta (S/):", font=("Segoe UI", 10)).pack(anchor=W, pady=(15, 2))
    entry_precio = ttk.Entry(panel_izq, font=("Segoe UI", 10), validate="key", validatecommand=vcmd_decimal)
    entry_precio.pack(fill=X)

    ttk.Label(panel_izq, text="Cantidad en Stock:", font=("Segoe UI", 10)).pack(anchor=W, pady=(15, 2))
    entry_stock = ttk.Entry(panel_izq, font=("Segoe UI", 10), validate="key", validatecommand=vcmd_entero)
    entry_stock.pack(fill=X)

    frame_venc = ttk.Frame(panel_izq)
    frame_venc.pack(fill=X, pady=(15, 5))

    var_tiene_venc = tk.BooleanVar(value=False)

    def toggle_fecha():
        if var_tiene_venc.get():
            date_vencimiento.pack(fill=X, pady=(5, 0))
        else:
            date_vencimiento.pack_forget()

    chk_venc = ttk.Checkbutton(
        frame_venc,
        text=" ¿Tiene fecha de vencimiento?",
        variable=var_tiene_venc,
        command=toggle_fecha,
        bootstyle="round-toggle-info"
    )
    chk_venc.pack(anchor=W)

    date_vencimiento = ttk.DateEntry(frame_venc, bootstyle="info", dateformat="%Y-%m-%d")

    ttk.Label(panel_izq, text="Nota u Observación (Opcional):", font=("Segoe UI", 10)).pack(anchor=W, pady=(15, 2))
    entry_nota = ttk.Entry(panel_izq, font=("Segoe UI", 10))
    entry_nota.pack(fill=X)

    frame_botones = ttk.Frame(panel_izq)
    frame_botones.pack(fill=X, pady=25)
    ttk.Button(frame_botones, text="➕ Agregar Producto", bootstyle="success", command=lambda: guardar_producto(), padding=10).pack(fill=X)

    panel_der = ttk.Frame(frame_padre, padding=20)
    panel_der.grid(row=0, column=1, sticky=NSEW)

    frame_header_der = ttk.Frame(panel_der)
    frame_header_der.pack(fill=X, pady=(0, 10))

    ttk.Label(frame_header_der, text="📦 Inventario Actual", font=("Segoe UI", 16, "bold"), bootstyle="info").pack(side=LEFT)

    frame_leyenda = ttk.Frame(frame_header_der)
    frame_leyenda.pack(side=RIGHT)

    tk.Label(frame_leyenda, text="  Vencido  ", bg="#6b1a1a", fg="white", font=("Segoe UI", 9)).pack(side=LEFT, padx=3)
    tk.Label(frame_leyenda, text="  ≤ 15 días  ", bg="#8a4d10", fg="white", font=("Segoe UI", 9)).pack(side=LEFT, padx=3)
    tk.Label(frame_leyenda, text="  ≤ 30 días  ", bg="#75701a", fg="white", font=("Segoe UI", 9)).pack(side=LEFT, padx=3)

    columnas = ("id", "nombre", "precio", "stock", "fecha_vencimiento", "nota")
    tabla = ttk.Treeview(panel_der, columns=columnas, show="headings", bootstyle="info")
    tabla.heading("id", text="ID")
    tabla.heading("nombre", text="Producto")
    tabla.heading("precio", text="Precio (S/)")
    tabla.heading("stock", text="Stock")
    tabla.heading("fecha_vencimiento", text="Vencimiento")
    tabla.heading("nota", text="Nota")

    tabla.column("id", width=40, anchor=CENTER, stretch=False)
    tabla.column("nombre", width=180, anchor=W, stretch=True)
    tabla.column("precio", width=80, anchor=CENTER, stretch=False)
    tabla.column("stock", width=80, anchor=CENTER, stretch=False)
    tabla.column("fecha_vencimiento", width=100, anchor=CENTER, stretch=False)
    tabla.column("nota", width=150, anchor=W, stretch=True)

    tabla.tag_configure("vencido", background="#6b1a1a", foreground="white")
    tabla.tag_configure("naranja", background="#8a4d10", foreground="white")
    tabla.tag_configure("amarillo", background="#75701a", foreground="white")
    tabla.tag_configure("normal", background="", foreground="")

    scrollbar = ttk.Scrollbar(panel_der, orient=VERTICAL, command=tabla.yview)
    tabla.configure(yscroll=scrollbar.set)
    scrollbar.pack(side=RIGHT, fill=Y)
    tabla.pack(side=LEFT, fill=BOTH, expand=True)

    panel_acciones = ttk.Frame(panel_der)
    panel_acciones.pack(fill=X, pady=10, side=BOTTOM)

    def cargar_datos():
        for item in tabla.get_children():
            tabla.delete(item)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos")
        filas = cursor.fetchall()

        hoy = datetime.now().date()

        for fila in filas:
            fila_lista = list(fila)
            tag = "normal"
            fecha_str = fila_lista[4]

            if len(fila_lista) > 5:
                if not fila_lista[5] or str(fila_lista[5]).strip() == "":
                    fila_lista[5] = "-"
            else:
                fila_lista.append("-")

            if fecha_str and fecha_str != "-":
                try:
                    fecha_venc = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                    dias_restantes = (fecha_venc - hoy).days

                    if dias_restantes <= 0:
                        tag = "vencido"
                    elif dias_restantes <= 15:
                        tag = "naranja"
                    elif dias_restantes <= 30:
                        tag = "amarillo"

                except ValueError:
                    pass

            if not fecha_str or str(fecha_str).strip() == "":
                fila_lista[4] = "-"

            tabla.insert("", END, values=fila_lista, tags=(tag,))

        conn.close()

    def guardar_producto():
        nombre = entry_nombre.get().strip()
        precio = entry_precio.get().strip()
        stock = entry_stock.get().strip()
        nota = entry_nota.get().strip()

        if var_tiene_venc.get():
            fecha_vencimiento = date_vencimiento.entry.get().strip()
        else:
            fecha_vencimiento = "-"

        if not nombre or not precio or not stock:
            messagebox.showwarning("Campos vacíos", "Por favor completa el Nombre, Precio y Stock.")
            return

        try:
            precio_float = float(precio)
            stock_int = int(stock)
        except ValueError:
            messagebox.showerror("Error", "El precio y el stock deben ser números válidos.")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO productos (nombre, precio, stock, fecha_vencimiento, nota)
            VALUES (?, ?, ?, ?, ?)
        ''', (nombre, precio_float, stock_int, fecha_vencimiento, nota))

        conn.commit()
        conn.close()

        messagebox.showinfo("Éxito", "Producto agregado correctamente.")

        entry_nombre.delete(0, END)
        entry_precio.delete(0, END)
        entry_stock.delete(0, END)
        entry_nota.delete(0, END)
        var_tiene_venc.set(False)
        toggle_fecha()

        cargar_datos()

    def eliminar_producto():
        seleccion = tabla.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Por favor selecciona un producto de la tabla.")
            return

        if messagebox.askyesno("Confirmar", "¿Estás seguro de eliminar este producto?"):
            item = tabla.item(seleccion[0])
            id_prod = item['values'][0]

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM productos WHERE id = ?", (id_prod,))
            conn.commit()
            conn.close()
            cargar_datos()

    def modificar_stock(cantidad_cambio):
        seleccion = tabla.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Por favor selecciona un producto de la tabla.")
            return

        item = tabla.item(seleccion[0])
        id_prod = item['values'][0]
        stock_actual = int(item['values'][3])

        nuevo_stock = stock_actual + cantidad_cambio
        if nuevo_stock < 0:
            messagebox.showwarning("Límite de Stock", "El stock no puede ser menor a 0.")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo_stock, id_prod))
        conn.commit()
        conn.close()
        cargar_datos()

    ttk.Button(panel_acciones, text="🗑️ Eliminar Producto", bootstyle="danger-outline", command=eliminar_producto).pack(side=RIGHT, padx=5)
    ttk.Button(panel_acciones, text="➖ Vender (-1)", bootstyle="warning", command=lambda: modificar_stock(-1)).pack(side=RIGHT, padx=5)
    ttk.Button(panel_acciones, text="➕ Añadir Stock (+1)", bootstyle="info", command=lambda: modificar_stock(1)).pack(side=RIGHT, padx=5)

    cargar_datos()
