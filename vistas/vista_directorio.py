import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import datetime
import os
import shutil
import platform
import subprocess
import csv

import database
from vistas import vista_asistencia

CHECK_OFF = "☐"
CHECK_ON = "☑"

def setup_tab_datos(parent_frame):

    # Usamos un conjunto (set) basado en 'nombre' porque en tu BD el nombre es UNIQUE.
    # Esto evita problemas de selección si hay socios con el id_socio vacío.
    marcados = set()

    top_frame = ttk.Frame(parent_frame)
    top_frame.pack(fill=X, pady=(20, 10), padx=40)

    ttk.Label(top_frame, text="Directorio de Socios", font=("Segoe UI", 18, "bold"), bootstyle="primary").pack(side=LEFT, padx=(0, 25))

    ttk.Label(top_frame, text="🔍 Buscar:", font=("Segoe UI", 11)).pack(side=LEFT)
    entry_buscar = ttk.Entry(top_frame, width=30, font=("Segoe UI", 11))
    entry_buscar.pack(side=LEFT, padx=(10, 10))

    lbl_contador = ttk.Label(top_frame, text="Marcados: 0", font=("Segoe UI", 10, "bold"), bootstyle="secondary")
    lbl_contador.pack(side=LEFT, padx=(10, 0))

    def obtener_marcados_visibles():
        """Devuelve [(id, nombre), ...] de las filas visibles que están marcadas."""
        resultado = []
        for item in tabla.get_children():
            valores = tabla.item(item, "values")
            if valores[0] == CHECK_ON:
                resultado.append((str(valores[1]), valores[2]))
        return resultado

    def actualizar_contador():
        visibles = obtener_marcados_visibles()
        lbl_contador.config(text=f"Marcados: {len(visibles)}")

        items = tabla.get_children()
        todos = len(items) > 0 and len(visibles) == len(items)
        tabla.heading("Sel", text=CHECK_ON if todos else CHECK_OFF)

    def alternar_fila(item):
        valores = tabla.item(item, "values")
        nombre = valores[2]

        if valores[0] == CHECK_ON:
            tabla.set(item, "Sel", CHECK_OFF)
            marcados.discard(nombre)
        else:
            tabla.set(item, "Sel", CHECK_ON)
            marcados.add(nombre)

        actualizar_contador()

    def alternar_todos():
        items = tabla.get_children()
        if not items:
            return

        todos_marcados = all(tabla.item(i, "values")[0] == CHECK_ON for i in items)

        for item in items:
            valores = tabla.item(item, "values")
            nombre = valores[2]
            if todos_marcados:
                tabla.set(item, "Sel", CHECK_OFF)
                marcados.discard(nombre)
            else:
                tabla.set(item, "Sel", CHECK_ON)
                marcados.add(nombre)

        actualizar_contador()

    def exportar_excel():
        items = tabla.get_children()
        if not items:
            messagebox.showinfo("Exportar", "No hay datos para exportar.")
            return

        items_marcados = [i for i in items if tabla.item(i, "values")[0] == CHECK_ON]
        items_a_exportar = items_marcados if items_marcados else items

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivo Excel (CSV)", "*.csv"), ("Todos los archivos", "*.*")],
            title="Guardar archivo como"
        )

        if not filepath:
            return

        try:
            with open(filepath, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')

                headers = ("ID", "Nombre", "Inicio", "Vencimiento", "Pago", "Estado", "Fotos")
                writer.writerow(headers)

                for item in items_a_exportar:
                    valores = tabla.item(item, "values")
                    writer.writerow(valores[1:8])

            messagebox.showinfo("Éxito", f"Datos exportados correctamente a:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un problema al exportar: {e}")

    def resetear_busqueda_y_cargar():
        entry_buscar.delete(0, END)
        cargar_datos()

    def eliminar_seleccion():
        lista_eliminar = obtener_marcados_visibles()

        if not lista_eliminar:
            seleccion = tabla.selection()
            if not seleccion:
                messagebox.showwarning(
                    "Atención",
                    "Marca la casilla ☐ de uno o varios socios (o selecciona uno en la tabla) y luego presiona Eliminar."
                )
                return
            for item in seleccion:
                valores = tabla.item(item, "values")
                lista_eliminar.append((str(valores[1]), valores[2]))

        if len(lista_eliminar) == 1:
            texto = f"¿Estás totalmente seguro que deseas eliminar a '{lista_eliminar[0][1]}'?\n\n"
        else:
            nombres = "\n".join(f"  • {n}" for _, n in lista_eliminar[:10])
            if len(lista_eliminar) > 10:
                nombres += f"\n  ... y {len(lista_eliminar) - 10} más"
            texto = f"¿Estás totalmente seguro que deseas eliminar a estos {len(lista_eliminar)} socios?\n\n{nombres}\n\n"

        respuesta = messagebox.askyesno(
            "Confirmar Eliminación",
            texto +
            "Esto borrará su registro de la base de datos, sus asistencias y toda su carpeta de fotos.\n"
            "Esta acción NO se puede deshacer."
        )

        if not respuesta:
            return

        eliminados = 0
        errores = []

        for id_socio, nombre_socio in lista_eliminar:
            try:
                database.eliminar_socio(nombre_socio)

                ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre_socio)
                if os.path.exists(ruta_carpeta):
                    shutil.rmtree(ruta_carpeta)

                marcados.discard(nombre_socio)
                eliminados += 1
            except Exception as e:
                errores.append(f"{nombre_socio}: {e}")

        if errores:
            messagebox.showerror(
                "Error",
                f"Se eliminaron {eliminados} socio(s), pero ocurrieron problemas con:\n\n" + "\n".join(errores)
            )
        else:
            if eliminados == 1:
                messagebox.showinfo("Éxito", f"El socio '{lista_eliminar[0][1]}' ha sido eliminado exitosamente.")
            else:
                messagebox.showinfo("Éxito", f"Se eliminaron {eliminados} socios exitosamente.")

        resetear_busqueda_y_cargar()

    btn_eliminar = ttk.Button(top_frame, text=" Eliminar Socio", bootstyle="danger", command=eliminar_seleccion)
    btn_eliminar.pack(side=RIGHT, padx=(10, 0))

    btn_actualizar = ttk.Button(top_frame, text="🔄 Actualizar Datos", bootstyle="info", command=resetear_busqueda_y_cargar)
    btn_actualizar.pack(side=RIGHT, padx=5)

    btn_exportar = ttk.Button(top_frame, text="📊 Exportar a Excel", bootstyle="success", command=exportar_excel)
    btn_exportar.pack(side=RIGHT, padx=5)

    table_frame = ttk.Frame(parent_frame)
    table_frame.pack(fill=BOTH, expand=True, padx=40, pady=(0, 30))

    columnas = ("Sel", "ID", "Nombre", "Inicio", "Vence", "Pago", "Estado", "Fotos", "Carpeta", "Acción")

    tabla = ttk.Treeview(table_frame, columns=columnas, show='headings', selectmode="extended", bootstyle="primary")

    tabla.tag_configure("vencido", foreground="gray")

    def ordenar_columna(tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]

        try:
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        tv.heading(col, command=lambda: ordenar_columna(tv, col, not reverse))

    for col in columnas:
        if col == "Sel":
            tabla.heading(col, text=CHECK_OFF, command=alternar_todos)
            continue
        texto = col.replace("Acción", "Asistencia").replace("Vence", "Vencimiento")
        tabla.heading(col, text=texto, command=lambda c=col: ordenar_columna(tabla, c, False))

    tabla.column("Sel", width=40, anchor=CENTER, stretch=False)
    tabla.column("ID", width=80, anchor=CENTER)
    tabla.column("Nombre", width=180, anchor=W)
    tabla.column("Inicio", width=95, anchor=CENTER)
    tabla.column("Vence", width=95, anchor=CENTER)
    tabla.column("Pago", width=90, anchor=CENTER)
    tabla.column("Estado", width=90, anchor=CENTER)
    tabla.column("Fotos", width=70, anchor=CENTER)
    tabla.column("Carpeta", width=100, anchor=CENTER)
    tabla.column("Acción", width=120, anchor=CENTER)

    scrollbar = ttk.Scrollbar(table_frame, orient=VERTICAL, command=tabla.yview, bootstyle="round")
    tabla.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side=RIGHT, fill=Y)
    tabla.pack(side=LEFT, fill=BOTH, expand=True)

    def cargar_datos(filtro=""):
        for item in tabla.get_children():
            tabla.delete(item)

        socios = database.obtener_lista_socios()
        hoy_str = datetime.now().strftime("%Y-%m-%d")

        nombres_existentes = set()

        for socio in socios:
            # Si retorna 6 elementos (nuevo modelo con socio_id)
            if len(socio) == 6:
                id_interno, id_socio, nombre, inicio, fin, pago = socio
            # Si retorna 5 (modelo viejo), NUNCA usamos el id_interno como id_socio
            else:
                id_interno, nombre, inicio, fin, pago = socio
                id_socio = ""

            # Garantizamos que el ID correcto se vea limpio o vacío
            id_socio = str(id_socio) if id_socio is not None and str(id_socio).strip() != "None" else ""

            nombres_existentes.add(nombre)

            if filtro and filtro not in str(nombre).lower() and filtro not in id_socio.lower():
                continue

            estado = "Activo" if fin >= hoy_str else "Vencido"

            fila_tags = ("vencido",) if estado == "Vencido" else ()

            tiene_fotos = "❌ No"
            ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, str(nombre))

            if os.path.exists(ruta_carpeta):
                archivos = [f for f in os.listdir(ruta_carpeta) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                if len(archivos) > 0:
                    tiene_fotos = "✅ Sí"

            casilla = CHECK_ON if nombre in marcados else CHECK_OFF

            tabla.insert("", END, values=(casilla, id_socio, nombre, inicio, fin, pago, estado, tiene_fotos, "📁 Abrir Carpeta", "📅 Ver Asistencias"), tags=fila_tags)

        # Limpiamos los marcados que ya no existan en la BD
        marcados.intersection_update(nombres_existentes)

        actualizar_contador()

    def buscar_en_tiempo_real(event):
        query = entry_buscar.get().lower().strip()
        cargar_datos(filtro=query)

    entry_buscar.bind('<KeyRelease>', buscar_en_tiempo_real)

    def al_hacer_clic(event):
        region = tabla.identify_region(event.x, event.y)
        if region == "cell":
            columna = tabla.identify_column(event.x)
            fila_seleccionada = tabla.identify_row(event.y)

            if fila_seleccionada:
                valores = tabla.item(fila_seleccionada, "values")
                nombre_socio = valores[2]

                if columna == "#1":
                    alternar_fila(fila_seleccionada)

                elif columna == "#9":
                    ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre_socio)

                    if not os.path.exists(ruta_carpeta):
                        os.makedirs(ruta_carpeta, exist_ok=True)
                        cargar_datos(entry_buscar.get().lower().strip())

                    if platform.system() == "Windows":
                        os.startfile(ruta_carpeta)
                    elif platform.system() == "Darwin":
                        subprocess.Popen(["open", ruta_carpeta])
                    else:
                        subprocess.Popen(["xdg-open", ruta_carpeta])

                elif columna == "#10":
                    vista_asistencia.mostrar_ventana(nombre_socio)

    tabla.bind("<ButtonRelease-1>", al_hacer_clic)

    cargar_datos()
    return resetear_busqueda_y_cargar