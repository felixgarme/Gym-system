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
import vista_asistencia

def setup_tab_datos(parent_frame):
    
    # --- CONTENEDORES RESPONSIVOS ---
    # Contenedor superior (Buscador y Botones)
    top_frame = ttk.Frame(parent_frame)
    top_frame.pack(fill=X, pady=(20, 10), padx=40)
    
    # Título Principal
    ttk.Label(top_frame, text="Directorio de Socios", font=("Segoe UI", 18, "bold"), bootstyle="primary").pack(side=LEFT, padx=(0, 25))
    
    # BUSCADOR
    ttk.Label(top_frame, text="🔍 Buscar:", font=("Segoe UI", 11)).pack(side=LEFT)
    entry_buscar = ttk.Entry(top_frame, width=30, font=("Segoe UI", 11))
    entry_buscar.pack(side=LEFT, padx=(10, 10))
    
    # --- FUNCIONES DE LOS BOTONES ---
    def exportar_excel():
        items = tabla.get_children()
        if not items:
            messagebox.showinfo("Exportar", "No hay datos para exportar.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivo Excel (CSV)", "*.csv"), ("Todos los archivos", "*.*")],
            title="Guardar archivo como"
        )

        if not filepath:
            return

        try:
            # utf-8-sig asegura que Excel lea los caracteres especiales y acentos correctamente
            with open(filepath, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';') # Delimitador estándar para Excel en español
                
                # Escribimos las cabeceras (excluyendo "Carpeta" y "Acción")
                headers = ("ID", "Nombre", "Inicio", "Vencimiento", "Pago", "Estado", "Fotos")
                writer.writerow(headers)

                # Iteramos sobre los datos de la tabla
                for item in items:
                    valores = tabla.item(item, "values")
                    writer.writerow(valores[:7])

            messagebox.showinfo("Éxito", f"Datos exportados correctamente a:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un problema al exportar: {e}")

    def resetear_busqueda_y_cargar():
        entry_buscar.delete(0, END)
        cargar_datos()

    def eliminar_seleccion():
        seleccion = tabla.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Por favor, haz clic en un socio de la tabla para seleccionarlo y luego presiona Eliminar.")
            return
            
        item = seleccion[0]
        valores = tabla.item(item, "values")
        nombre_socio = valores[1]
        
        respuesta = messagebox.askyesno("Confirmar Eliminación", 
                                        f"¿Estás totalmente seguro que deseas eliminar a '{nombre_socio}'?\n\n"
                                        "Esto borrará su registro de la base de datos, sus asistencias y toda su carpeta de fotos.\n"
                                        "Esta acción NO se puede deshacer.")
        
        if respuesta:
            try:
                database.eliminar_socio(nombre_socio)

                ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre_socio)
                if os.path.exists(ruta_carpeta):
                    shutil.rmtree(ruta_carpeta)

                messagebox.showinfo("Éxito", f"El socio '{nombre_socio}' ha sido eliminado exitosamente.")
                resetear_busqueda_y_cargar()
                
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un problema al eliminar: {e}")

    # BOTONES SUPERIORES (Estilizados con bootstyle)
    btn_eliminar = ttk.Button(top_frame, text="🗑️ Eliminar Socio", bootstyle="danger", command=eliminar_seleccion)
    btn_eliminar.pack(side=RIGHT, padx=(10, 0))

    btn_actualizar = ttk.Button(top_frame, text="🔄 Actualizar Datos", bootstyle="info", command=resetear_busqueda_y_cargar)
    btn_actualizar.pack(side=RIGHT, padx=5)

    btn_exportar = ttk.Button(top_frame, text="📊 Exportar a Excel", bootstyle="success", command=exportar_excel)
    btn_exportar.pack(side=RIGHT, padx=5)

    # --- TABLA Y SCROLLBAR ---
    table_frame = ttk.Frame(parent_frame)
    table_frame.pack(fill=BOTH, expand=True, padx=40, pady=(0, 30))
    
    columnas = ("ID", "Nombre", "Inicio", "Vence", "Pago", "Estado", "Fotos", "Carpeta", "Acción")
    
    # Tabla moderna (bootstyle="primary" le da toques sutiles de color al seleccionar)
    tabla = ttk.Treeview(table_frame, columns=columnas, show='headings', selectmode="browse", bootstyle="primary")
    
    # Lógica de Ordenamiento al hacer clic en la cabecera
    def ordenar_columna(tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        
        try:
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)
            
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)
            
        tv.heading(col, command=lambda: ordenar_columna(tv, col, not reverse))

    # Cabeceras
    for col in columnas:
        texto = col.replace("Acción", "Asistencia").replace("Vence", "Vencimiento")
        tabla.heading(col, text=texto, command=lambda c=col: ordenar_columna(tabla, c, False))
    
    # Anchos de columnas ajustados
    tabla.column("ID", width=40, anchor=CENTER)
    tabla.column("Nombre", width=180, anchor=W)
    tabla.column("Inicio", width=95, anchor=CENTER)
    tabla.column("Vence", width=95, anchor=CENTER)
    tabla.column("Pago", width=90, anchor=CENTER)
    tabla.column("Estado", width=90, anchor=CENTER)
    tabla.column("Fotos", width=70, anchor=CENTER)
    tabla.column("Carpeta", width=100, anchor=CENTER) 
    tabla.column("Acción", width=120, anchor=CENTER) 
    
    # Scrollbar moderna redondeada
    scrollbar = ttk.Scrollbar(table_frame, orient=VERTICAL, command=tabla.yview, bootstyle="round")
    tabla.configure(yscrollcommand=scrollbar.set)
    
    scrollbar.pack(side=RIGHT, fill=Y)
    tabla.pack(side=LEFT, fill=BOTH, expand=True)
    
    # --- FUNCIONES DE CARGA Y FILTRADO ---
    def cargar_datos(filtro=""):
        for item in tabla.get_children():
            tabla.delete(item)
            
        socios = database.obtener_lista_socios()
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        
        for socio in socios:
            id_socio, nombre, inicio, fin, pago = socio
            
            if filtro and filtro not in str(nombre).lower() and filtro not in str(id_socio):
                continue
                
            estado = "Activo" if fin >= hoy_str else "Vencido"
            
            tiene_fotos = "❌ No"
            ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, str(nombre))
            
            if os.path.exists(ruta_carpeta):
                archivos = [f for f in os.listdir(ruta_carpeta) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                if len(archivos) > 0:
                    tiene_fotos = "✅ Sí"
            
            tabla.insert("", END, values=(id_socio, nombre, inicio, fin, pago, estado, tiene_fotos, "📁 Abrir Carpeta", "📅 Ver Asistencias"))
            
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
                nombre_socio = valores[1] 
                
                # --- Columna 8 (Carpeta) ---
                if columna == "#8":
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
                
                # --- Columna 9 (Asistencia) ---
                elif columna == "#9":
                    vista_asistencia.mostrar_ventana(nombre_socio)

    tabla.bind("<ButtonRelease-1>", al_hacer_clic)
    
    # Carga inicial sin filtros
    cargar_datos()
    return resetear_busqueda_y_cargar