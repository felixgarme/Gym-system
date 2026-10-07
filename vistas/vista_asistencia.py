import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import datetime
import database

def mostrar_ventana(nombre_socio):
    ventana = ttk.Toplevel(title=f"Historial de Asistencia - {nombre_socio}")
    ventana.geometry("520x620")
    ventana.minsize(450, 500)
    ventana.grab_set()

    ttk.Label(ventana, text="Historial de Asistencias de:", font=("Segoe UI", 11), bootstyle="secondary").pack(pady=(30, 5))
    ttk.Label(ventana, text=nombre_socio, font=("Segoe UI", 18, "bold"), bootstyle="primary").pack(pady=(0, 20))

    frame_tabla = ttk.Frame(ventana)
    frame_tabla.pack(fill=BOTH, expand=True, padx=35, pady=(0, 15))

    columnas = ("N°", "Fecha", "Hora")

    tabla = ttk.Treeview(frame_tabla, columns=columnas, show='headings', selectmode="browse", bootstyle="info")

    tabla.heading("N°", text="N°")
    tabla.heading("Fecha", text="Fecha de Ingreso")
    tabla.heading("Hora", text="Hora")

    tabla.column("N°", width=60, anchor=CENTER)
    tabla.column("Fecha", width=180, anchor=CENTER)
    tabla.column("Hora", width=150, anchor=CENTER)

    scrollbar = ttk.Scrollbar(frame_tabla, orient=VERTICAL, command=tabla.yview, bootstyle="round")
    tabla.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side=RIGHT, fill=Y, padx=(5, 0))
    tabla.pack(side=LEFT, fill=BOTH, expand=True)

    frame_inferior = ttk.Frame(ventana)
    frame_inferior.pack(fill=X, pady=(5, 10), padx=35)

    lbl_total = ttk.Label(frame_inferior, text="Total de ingresos: 0", font=("Segoe UI", 11, "bold"), bootstyle="light")
    lbl_total.pack(side=LEFT)

    frame_botones = ttk.Frame(ventana)
    frame_botones.pack(fill=X, pady=(0, 30), padx=35)

    def cargar_datos():
        for item in tabla.get_children():
            tabla.delete(item)

        asistencias = database.obtener_asistencias_socio(nombre_socio)

        if not asistencias:
            tabla.insert("", END, values=("-", "No hay asistencias aún", "-"))
            lbl_total.config(text="Total de ingresos: 0")
        else:
            for i, asis in enumerate(asistencias, start=1):
                fecha_hora_str = asis[0]
                try:
                    fecha, hora = fecha_hora_str.split(" ")
                except ValueError:
                    fecha = fecha_hora_str
                    hora = "-"
                tabla.insert("", END, values=(i, fecha, hora))

            lbl_total.config(text=f"Total de ingresos: {len(asistencias)}")

    def ventana_agregar_manual():
        add_win = ttk.Toplevel(title="Agregar Manual")
        add_win.geometry("350x320")
        add_win.grab_set()

        ttk.Label(add_win, text="Nueva Asistencia", font=("Segoe UI", 15, "bold"), bootstyle="primary").pack(pady=(25, 20))

        frame_inputs = ttk.Frame(add_win)
        frame_inputs.pack(fill=X, padx=40)

        ttk.Label(frame_inputs, text="Fecha (YYYY-MM-DD):", font=("Segoe UI", 10), bootstyle="secondary").pack(anchor=W)
        entry_fecha = ttk.Entry(frame_inputs, font=("Segoe UI", 11))
        entry_fecha.pack(fill=X, pady=(5, 15))
        entry_fecha.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ttk.Label(frame_inputs, text="Hora (HH:MM:SS):", font=("Segoe UI", 10), bootstyle="secondary").pack(anchor=W)
        entry_hora = ttk.Entry(frame_inputs, font=("Segoe UI", 11))
        entry_hora.pack(fill=X, pady=(5, 20))
        entry_hora.insert(0, datetime.now().strftime("%H:%M:%S"))

        def guardar_manual():
            fecha = entry_fecha.get().strip()
            hora = entry_hora.get().strip()
            fecha_hora_completa = f"{fecha} {hora}"

            try:
                database.registrar_asistencia_manual(nombre_socio, fecha_hora_completa)
                messagebox.showinfo("Éxito", "Asistencia agregada correctamente.", parent=add_win)
                cargar_datos()
                add_win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {e}", parent=add_win)

        ttk.Button(add_win, text="✓ Guardar Asistencia", bootstyle="success", padding=10, command=guardar_manual).pack(pady=10)

    ttk.Button(frame_botones, text="➕ Agregar Manual", bootstyle="success", padding=8, command=ventana_agregar_manual).pack(side=LEFT)

    ttk.Button(frame_botones, text="Cerrar", bootstyle="secondary-outline", padding=8, command=ventana.destroy).pack(side=RIGHT)

    cargar_datos()
