import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pandas as pd
import numpy as np
import database
from datetime import datetime  # <--- IMPORTACIÓN NECESARIA PARA COMPARAR FECHAS

def setup_tab_importar(frame_padre, app):
    # Contenedor principal centrado
    card_container = ttk.Frame(frame_padre, padding=40)
    card_container.place(relx=0.5, rely=0.5, anchor=CENTER)

    # Título principal estilizado
    ttk.Label(
        card_container, 
        text="Importar Base de Datos 'DG Madrid'", 
        font=("Segoe UI", 18, "bold"), 
        bootstyle="primary"
    ).pack(pady=(0, 20))
    
    # Instrucciones claras en tono secundario (grisáceo automático)
    instrucciones = (
        "Sube un archivo Excel (.xlsx) con el siguiente orden de columnas:\n"
        "Col 1: Nombre\n"
        "Col 4: Medio de Pago\n"
        "Col 7: Fecha de Inicio (M/D/AAAA)\n"
        "Col 8: Fecha de Cierre (M/D/AAAA)\n\n"
        "⚠️ Los socios cuya fecha de cierre ya haya pasado serán ignorados automáticamente.\n"
        "Nota: Los socios se guardarán sin foto facial. Deberás actualizarla luego."
    )
    ttk.Label(
        card_container, 
        text=instrucciones, 
        justify=CENTER, 
        font=("Segoe UI", 11), 
        bootstyle="secondary"
    ).pack(pady=(0, 25))

    # Botón de importación moderno
    btn_importar = ttk.Button(
        card_container, 
        text="📂 Seleccionar Archivo Excel", 
        bootstyle="primary", 
        padding=10
    )
    btn_importar.pack(fill=X)
    
    # --- Barra de Progreso (estilo rayado y animado de ttkbootstrap) ---
    progress_bar = ttk.Progressbar(
        card_container, 
        orient=HORIZONTAL, 
        mode="determinate", 
        bootstyle="success-striped"
    )
    
    # Etiqueta de resultados (se actualiza dinámicamente)
    lbl_resultado = ttk.Label(
        card_container, 
        text="", 
        justify=CENTER, 
        font=("Segoe UI", 11, "bold")
    )
    lbl_resultado.pack(pady=15)

    def ejecutar_importacion():
        ruta = filedialog.askopenfilename(
            title="Seleccionar Excel de DG Madrid",
            filetypes=[("Archivos Excel", "*.xlsx *.xls")]
        )
        if not ruta:
            return
            
        try:
            # Desactivar botón durante la carga
            btn_importar.config(state=DISABLED)
            lbl_resultado.config(text="Leyendo archivo Excel...", bootstyle="info")
            
            # Mostrar la barra de progreso
            progress_bar.pack(fill=X, pady=(15, 0), before=lbl_resultado)
            progress_bar['value'] = 0
            app.root.update()

            df = pd.read_excel(ruta)
            total_filas = len(df)
            progress_bar['maximum'] = total_filas
            
            # Contadores
            exitos = 0
            errores = 0
            vencidos_omitidos = 0  # <--- NUEVO CONTADOR
            
            # Fecha actual (solo el día, sin hora) para comparar
            fecha_actual = datetime.now().date()
            
            # Vector falso de 128 dimensiones
            encoding_dummy = np.zeros(128).tobytes()

            for i, (indice, fila) in enumerate(df.iterrows()):
                try:
                    nombre = str(fila.iloc[0]).strip()
                    if pd.isna(fila.iloc[0]) or not nombre or nombre.lower() == 'nan':
                        errores += 1
                        continue
                    
                    medio_pago = str(fila.iloc[3]).strip()
                    
                    # Convertimos las fechas a objetos datetime de Pandas
                    fecha_inicio_dt = pd.to_datetime(fila.iloc[6])
                    fecha_fin_dt = pd.to_datetime(fila.iloc[7])
                    
                    # Si alguna fecha viene vacía/inválida en el Excel
                    if pd.isna(fecha_inicio_dt) or pd.isna(fecha_fin_dt):
                        errores += 1
                        continue

                    # --- NUEVA VALIDACIÓN: DESCARTAR VENCIDOS ---
                    # Extraemos el date() y lo comparamos con la fecha de hoy
                    if fecha_fin_dt.date() < fecha_actual:
                        vencidos_omitidos += 1
                        continue  # Salta a la siguiente fila, no guarda este socio
                        
                    # Formateamos para la base de datos
                    fecha_inicio = fecha_inicio_dt.strftime('%Y-%m-%d')
                    fecha_fin = fecha_fin_dt.strftime('%Y-%m-%d')
                    
                    try:
                        database.guardar_socio(nombre, encoding_dummy, fecha_inicio, fecha_fin, medio_pago)
                        exitos += 1
                    except Exception:
                        # Error de DB (ej. nombre duplicado)
                        errores += 1
                except Exception:
                    # Error procesando la fila
                    errores += 1
                
                # Actualizar barra de progreso
                progress_bar['value'] = i + 1
                
                if i % 5 == 0 or i == total_filas - 1:
                    lbl_resultado.config(text=f"Procesando: {i + 1} / {total_filas} registros...")
                    app.root.update_idletasks()

            # Resumen detallado final
            mensaje = (
                f"✅ Importación finalizada.\n\n"
                f"✔️ Registros agregados (Vigentes): {exitos}\n"
                f"⚠️ Omitidos (Ya vencidos): {vencidos_omitidos}\n"
                f"❌ Omitidos (Errores / Duplicados): {errores}"
            )
            # Cambiamos el bootstyle a success (Verde nativo de ttkbootstrap)
            lbl_resultado.config(text=mensaje, bootstyle="success") 

            # Refrescar los datos en el resto de la App
            if hasattr(app, 'actualizar_tabla_excel') and callable(app.actualizar_tabla_excel):
                app.actualizar_tabla_excel()
            app.cargar_nombres_socios()
            
        except Exception as e:
            # Cambiamos el bootstyle a danger (Rojo nativo de ttkbootstrap)
            lbl_resultado.config(text=f"❌ Error crítico: {str(e)}", bootstyle="danger")
        finally:
            btn_importar.config(state=NORMAL)
            app.root.update_idletasks()

    btn_importar.config(command=ejecutar_importacion)