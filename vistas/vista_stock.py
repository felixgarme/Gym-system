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

    frame_padre.columnconfigure(0, weight=1, minsize=320)
    frame_padre.columnconfigure(1, weight=3)
    frame_padre.rowconfigure(0, weight=1)

    panel_izq = ttk.Frame(frame_padre, padding=20)
    panel_izq.grid(row=0, column=0, sticky=NSEW)
    panel_izq.columnconfigure(0, weight=1)

    ttk.Label(panel_izq, text="🛒 Registrar Producto", font=("Segoe UI", 16, "bold"), bootstyle="primary").grid(row=0, column=0, sticky=W, pady=(0, 20))

    ttk.Label(panel_izq, text="Nombre del Producto:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky=W, pady=(5, 2))
    entry_nombre = ttk.Entry(panel_izq, font=("Segoe UI", 10))
    entry_nombre.grid(row=2, column=0, sticky=EW)

    ttk.Label(panel_izq, text="Precio de Venta (S/):", font=("Segoe UI", 10)).grid(row=3, column=0, sticky=W, pady=(15, 2))
    entry_precio = ttk.Entry(panel_izq, font=("Segoe UI", 10), validate="key", validatecommand=vcmd_decimal)
    entry_precio.grid(row=4, column=0, sticky=EW)

    ttk.Label(panel_izq, text="Cantidad en Stock:", font=("Segoe UI", 10)).grid(row=5, column=0, sticky=W, pady=(15, 2))
    entry_stock = ttk.Entry(panel_izq, font=("Segoe UI", 10), validate="key", validatecommand=vcmd_entero)
    entry_stock.grid(row=6, column=0, sticky=EW)

    var_tiene_venc = tk.BooleanVar(value=False)

    def toggle_fecha():
        if var_tiene_venc.get():
            date_vencimiento.grid(row=9, column=0, sticky=EW, pady=(0, 5))
        else:
            date_vencimiento.grid_remove()

    chk_venc = ttk.Checkbutton(
        panel_izq,
        text=" ¿Tiene fecha de vencimiento?",
        variable=var_tiene_venc,
        command=toggle_fecha,
        bootstyle="round-toggle-info"
    )
    chk_venc.grid(row=7, column=0, sticky=W, pady=(15, 5))

    date_vencimiento = ttk.DateEntry(panel_izq, bootstyle="info", dateformat="%Y-%m-%d")
    date_vencimiento.grid(row=8, column=0, sticky=EW, pady=(0, 5))
    date_vencimiento.grid_remove()

    ttk.Label(panel_izq, text="Nota u Observación (Opcional):", font=("Segoe UI", 10)).grid(row=10, column=0, sticky=W, pady=(15, 2))
    entry_nota = ttk.Entry(panel_izq, font=("Segoe UI", 10))
    entry_nota.grid(row=11, column=0, sticky=EW)

    ttk.Button(panel_izq, text="➕ Agregar Producto", bootstyle="success", command=lambda: guardar_producto(), padding=10).grid(row=12, column=0, sticky=EW, pady=25)

    panel_der = ttk.Frame(frame_padre, padding=20)
    panel_der.grid(row=0, column=1, sticky=NSEW)
    panel_der.columnconfigure(0, weight=1)
    panel_der.rowconfigure(1, weight=1)

    frame_header_der = ttk.Frame(panel_der)
    frame_header_der.grid(row=0, column=0, sticky=EW, pady=(0, 10))

    ttk.Label(frame_header_der, text="📦 Inventario Actual", font=("Segoe UI", 16, "bold"), bootstyle="info").pack(side=LEFT)

    frame_leyenda = ttk.Frame(frame_header_der)
    frame_leyenda.pack(side=RIGHT)

    tk.Label(frame_leyenda, text="  Vencido  ", bg="#6b1a1a", fg="white", font=("Segoe UI", 9)).pack(side=LEFT, padx=3)
    tk.Label(frame_leyenda, text="  ≤ 15 días  ", bg="#8a4d10", fg="white", font=("Segoe UI", 9)).pack(side=LEFT, padx=3)
    tk.Label(frame_leyenda, text="  ≤ 30 días  ", bg="#75701a", fg="white", font=("Segoe UI", 9)).pack(side=LEFT, padx=3)

    columnas = ("sel", "id", "nombre", "precio", "stock", "fecha_vencimiento", "nota")

    frame_tabla = ttk.Frame(panel_der)
    frame_tabla.grid(row=1, column=0, sticky=NSEW)

    tabla = ttk.Treeview(frame_tabla, columns=columnas, show="headings", bootstyle="info", selectmode="browse")
    tabla.heading("sel", text="✔")
    tabla.heading("id", text="ID")
    tabla.heading("nombre", text="Producto")
    tabla.heading("precio", text="Precio (S/)")
    tabla.heading("stock", text="Stock")
    tabla.heading("fecha_vencimiento", text="Vencimiento")
    tabla.heading("nota", text="Nota")

    tabla.column("sel", width=40, anchor=CENTER, stretch=False)
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

    scrollbar = ttk.Scrollbar(frame_tabla, orient=VERTICAL, command=tabla.yview)
    tabla.configure(yscroll=scrollbar.set)
    scrollbar.pack(side=RIGHT, fill=Y)
    tabla.pack(side=LEFT, fill=BOTH, expand=True)

    def al_seleccionar_fila(event):
        seleccionado = tabla.selection()
        for child in tabla.get_children():
            vals = list(tabla.item(child, "values"))
            es_seleccionado = child in seleccionado
            marcador = "☑" if es_seleccionado else "☐"

            if vals[0] != marcador:
                vals[0] = marcador
                tabla.item(child, values=vals)

    tabla.bind("<<TreeviewSelect>>", al_seleccionar_fila)

    panel_acciones = ttk.Frame(panel_der)
    panel_acciones.grid(row=2, column=0, sticky=EW, pady=(15, 0))

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

            while len(fila_lista) < 6:
                fila_lista.append("-")

            if not fila_lista[4] or str(fila_lista[4]).strip() == "":
                fila_lista[4] = "-"
            if not fila_lista[5] or str(fila_lista[5]).strip() == "":
                fila_lista[5] = "-"

            tag = "normal"
            fecha_str = fila_lista[4]

            if fecha_str != "-":
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

            fila_display = ["☐"] + fila_lista
            tabla.insert("", END, values=fila_display, tags=(tag,))

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
            messagebox.showwarning("Selección", "Selecciona marcando la casilla de un producto en la tabla.")
            return

        if messagebox.askyesno("Confirmar", "¿Estás seguro de eliminar este producto?"):
            item = tabla.item(seleccion[0])
            id_prod = item['values'][1]

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM productos WHERE id = ?", (id_prod,))
            conn.commit()
            conn.close()
            cargar_datos()

    def modificar_stock(cantidad_cambio):
        seleccion = tabla.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Selecciona marcando la casilla de un producto en la tabla.")
            return

        item = tabla.item(seleccion[0])
        id_prod = item['values'][1]
        stock_actual = int(item['values'][4])

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

    def editar_producto():
        seleccion = tabla.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Selecciona marcando la casilla de un producto para editar.")
            return

        item = tabla.item(seleccion[0])
        valores = item['values']

        id_prod = valores[1]
        nombre_actual = valores[2]
        precio_actual = valores[3]
        stock_actual = valores[4]
        fecha_actual = valores[5]
        nota_actual = valores[6] if valores[6] != "-" else ""

        top = ttk.Toplevel(frame_padre)
        top.title("Editar Producto")
        top.geometry("400x550")
        try: top.position_center()
        except: pass
        top.transient(frame_padre.winfo_toplevel())
        top.grab_set()

        pad_config = {"padx": 20, "pady": 10}

        ttk.Label(top, text="✏️ Editar Producto", font=("Segoe UI", 16, "bold"), bootstyle="primary").pack(pady=15)

        ttk.Label(top, text="Nombre del Producto:").pack(anchor=W, padx=20)
        ent_nom = ttk.Entry(top)
        ent_nom.pack(fill=X, **pad_config)
        ent_nom.insert(0, nombre_actual)

        ttk.Label(top, text="Precio (S/):").pack(anchor=W, padx=20)
        ent_pre = ttk.Entry(top, validate="key", validatecommand=vcmd_decimal)
        ent_pre.pack(fill=X, **pad_config)
        ent_pre.insert(0, precio_actual)

        ttk.Label(top, text="Cantidad en Stock:").pack(anchor=W, padx=20)
        ent_stk = ttk.Entry(top, validate="key", validatecommand=vcmd_entero)
        ent_stk.pack(fill=X, **pad_config)
        ent_stk.insert(0, stock_actual)

        var_venc_edit = tk.BooleanVar(value=(fecha_actual != "-"))
        frame_venc_edit = ttk.Frame(top)
        frame_venc_edit.pack(fill=X, padx=20, pady=5)

        date_venc_edit = ttk.DateEntry(frame_venc_edit, bootstyle="info", dateformat="%Y-%m-%d")

        def toggle_fecha_edit():
            if var_venc_edit.get():
                date_venc_edit.pack(fill=X, pady=(5, 0))
            else:
                date_venc_edit.pack_forget()

        chk_venc_edit = ttk.Checkbutton(
            frame_venc_edit,
            text=" ¿Tiene fecha de vencimiento?",
            variable=var_venc_edit,
            command=toggle_fecha_edit,
            bootstyle="round-toggle-info"
        )
        chk_venc_edit.pack(anchor=W)

        if fecha_actual != "-":
            try:
                date_venc_edit.entry.delete(0, END)
                date_venc_edit.entry.insert(0, fecha_actual)
            except: pass
        toggle_fecha_edit()

        ttk.Label(top, text="Nota u Observación:").pack(anchor=W, padx=20)
        ent_nota = ttk.Entry(top)
        ent_nota.pack(fill=X, **pad_config)
        ent_nota.insert(0, nota_actual)

        def guardar_edicion():
            n_nom = ent_nom.get().strip()
            n_pre = ent_pre.get().strip()
            n_stk = ent_stk.get().strip()
            n_nota = ent_nota.get().strip()
            n_fec = date_venc_edit.entry.get().strip() if var_venc_edit.get() else "-"

            if not n_nom or not n_pre or not n_stk:
                messagebox.showwarning("Campos vacíos", "Nombre, Precio y Stock son obligatorios.", parent=top)
                return

            try:
                p_val = float(n_pre)
                s_val = int(n_stk)
            except ValueError:
                messagebox.showerror("Error", "Precio y stock deben ser números válidos.", parent=top)
                return

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE productos
                SET nombre = ?, precio = ?, stock = ?, fecha_vencimiento = ?, nota = ?
                WHERE id = ?
            ''', (n_nom, p_val, s_val, n_fec, n_nota, id_prod))
            conn.commit()
            conn.close()

            messagebox.showinfo("Éxito", "Producto actualizado correctamente.", parent=top)
            top.destroy()
            cargar_datos()

        ttk.Button(top, text="💾 Guardar Cambios", bootstyle="success", command=guardar_edicion).pack(pady=20, padx=20, fill=X)

    ttk.Button(panel_acciones, text="🗑️ Eliminar", bootstyle="danger-outline", command=eliminar_producto).pack(side=RIGHT, padx=5)
    ttk.Button(panel_acciones, text="✏️ Editar", bootstyle="primary", command=editar_producto).pack(side=RIGHT, padx=5)
    ttk.Button(panel_acciones, text="➖ Vender (-1)", bootstyle="warning", command=lambda: modificar_stock(-1)).pack(side=RIGHT, padx=5)
    ttk.Button(panel_acciones, text="➕ Stock (+1)", bootstyle="info", command=lambda: modificar_stock(1)).pack(side=RIGHT, padx=5)

    cargar_datos()
