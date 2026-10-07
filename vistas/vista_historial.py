import sqlite3
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import datetime

def conectar_db():
    return sqlite3.connect("gimnasio.db")

def obtener_asistencias_hoy():
    conn = conectar_db()
    cursor = conn.cursor()

    hoy = datetime.now().strftime("%Y-%m-%d")

    try:
        cursor.execute('''
            SELECT nombre, fecha_hora
            FROM asistencias
            WHERE fecha_hora LIKE ?
            ORDER BY fecha_hora DESC
        ''', (f"{hoy}%",))
        filas = cursor.fetchall()
    except sqlite3.Error:
        filas = []
    finally:
        conn.close()

    return filas

def actualizar_tabla(tree, label_total):
    for item in tree.get_children():
        tree.delete(item)

    datos = obtener_asistencias_hoy()

    for fila in datos:
        nombre = fila[0] if fila[0] else "Socio Desconocido"
        fecha_hora = fila[1] if fila[1] else ""

        if " " in fecha_hora:
            hora = fecha_hora.split(" ")[1]
        else:
            hora = fecha_hora

        tree.insert("", END, values=(hora, nombre))

    label_total.config(text=f"Total de asistencias hoy: {len(datos)}")

def setup_tab_historial(parent):
    """Función de montaje para integrarse dentro del Notebook principal."""
    main_frame = ttk.Frame(parent, padding=20)
    main_frame.pack(fill=BOTH, expand=True)

    hoy_str = datetime.now().strftime("%d/%m/%Y")
    lbl_titulo = ttk.Label(
        main_frame,
        text=f"🕒 Historial de Asistencias — {hoy_str}",
        font=("Segoe UI", 16, "bold"),
        bootstyle="primary"
    )
    lbl_titulo.pack(pady=(0, 5))

    label_total = ttk.Label(
        main_frame,
        text="Total de asistencias hoy: 0",
        font=("Segoe UI", 11),
        bootstyle="secondary"
    )
    label_total.pack(pady=(0, 15))

    btn_actualizar = ttk.Button(
        main_frame,
        text="🔄 Actualizar Lista",
        bootstyle="primary",
        command=lambda: actualizar_tabla(tabla, label_total)
    )
    btn_actualizar.pack(pady=(0, 15), fill=X)

    frame_tabla = ttk.Frame(main_frame)
    frame_tabla.pack(fill=BOTH, expand=True)

    scroll_y = ttk.Scrollbar(frame_tabla, orient=VERTICAL, bootstyle="round")
    scroll_y.pack(side=RIGHT, fill=Y)

    columnas = ("Hora", "Socio")
    tabla = ttk.Treeview(
        frame_tabla,
        columns=columnas,
        show="headings",
        yscrollcommand=scroll_y.set,
        bootstyle="dark"
    )

    tabla.heading("Hora", text="Hora de Ingreso")
    tabla.heading("Socio", text="Nombre del Socio")

    tabla.column("Hora", width=140, anchor=CENTER)
    tabla.column("Socio", width=300, anchor=W)

    tabla.pack(side=LEFT, fill=BOTH, expand=True)
    scroll_y.config(command=tabla.yview)

    def auto_actualizar():
        actualizar_tabla(tabla, label_total)
        parent.after(5000, auto_actualizar)

    auto_actualizar()

if __name__ == "__main__":
    app = ttk.Window(title="Historial de Asistencias - Hoy", themename="darkly")
    app.geometry("500x650")
    setup_tab_historial(app)
    app.mainloop()
