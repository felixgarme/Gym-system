import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import pandas as pd
import numpy as np
import database
from datetime import datetime
import threading
import time

def setup_tab_importar(frame_padre, app):
    main_container = ttk.Frame(frame_padre)
    main_container.pack(expand=True, fill=BOTH)

    card_container = ttk.Frame(main_container, padding=40)
    card_container.pack(expand=True)

    ttk.Label(
        card_container,
        text="Importar Base de Datos 'DG Madrid'",
        font=("Segoe UI", 18, "bold"),
        bootstyle="primary"
    ).pack(pady=(0, 20))

    instrucciones = (
        "Sube un archivo Excel (.xlsx) con el siguiente orden de columnas:\n"
        "Col 1: Nombre\n"
        "Col 4: Medio de Pago\n"
        "Col 5: ANC (ID del socio)\n"
        "Col 7: Fecha de Inicio (M/D/AAAA)\n"
        "Col 8: Fecha de Cierre (M/D/AAAA)\n\n"
        "Atención: Los socios cuya fecha de cierre ya haya pasado también serán importados (como vencidos).\n"
        "Nota: Los socios se guardarán sin foto facial. Deberás actualizarla luego."
    )
    ttk.Label(
        card_container,
        text=instrucciones,
        justify=CENTER,
        font=("Segoe UI", 11),
        bootstyle="secondary"
    ).pack(pady=(0, 25))

    btn_importar = ttk.Button(
        card_container,
        text="Seleccionar Archivo Excel",
        bootstyle="primary",
        padding=10
    )
    btn_importar.pack(fill=X)

    progress_bar = ttk.Progressbar(
        card_container,
        orient=HORIZONTAL,
        mode="determinate",
        bootstyle="success-striped"
    )

    lbl_resultado = ttk.Label(
        card_container,
        text="",
        justify=CENTER,
        font=("Segoe UI", 11, "bold")
    )
    lbl_resultado.pack(pady=15)

    def formatear_tiempo(segundos):
        if segundos <= 0:
            return "00:00"
        m, s = divmod(int(segundos), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def ejecutar_importacion():
        ruta = filedialog.askopenfilename(
            title="Seleccionar Excel de DG Madrid",
            filetypes=[("Archivos Excel", "*.xlsx *.xls")]
        )
        if not ruta:
            return

        btn_importar.config(state=DISABLED)
        lbl_resultado.config(text="Procesando datos del Excel... Por favor espera.", bootstyle="info")
        progress_bar.pack(fill=X, pady=(15, 0), before=lbl_resultado)
        progress_bar['value'] = 0

        estado = {
            "fase": "leyendo",
            "total": 0,
            "procesados": 0,
            "exitos": 0,
            "vencidos": 0,
            "errores": 0,
            "tiempo_estimado": "Calculando...",
            "mensaje_error": ""
        }

        def worker():
            try:
                df = pd.read_excel(ruta)
                total_filas = len(df)
                if total_filas == 0:
                    raise ValueError("El archivo Excel está vacío.")
                if len(df.columns) < 8:
                    raise ValueError("El archivo Excel no tiene al menos 8 columnas requeridas.")

                estado["total"] = total_filas
                estado["fase"] = "procesando"

                df['nombre_clean'] = df.iloc[:, 0].astype(str).str.strip()
                df['medio_pago_clean'] = df.iloc[:, 3].astype(str).str.strip()

                df['fecha_inicio_dt'] = pd.to_datetime(df.iloc[:, 6], errors='coerce')
                df['fecha_fin_dt'] = pd.to_datetime(df.iloc[:, 7], errors='coerce')

                mask_errores = (
                    df['nombre_clean'].isin(['nan', 'None', '']) |
                    df['nombre_clean'].isna() |
                    df['fecha_inicio_dt'].isna() |
                    df['fecha_fin_dt'].isna()
                )

                estado["errores"] = int(mask_errores.sum())
                df_validos = df[~mask_errores].copy()

                def parse_anc(val):
                    if pd.isna(val): return ""
                    if isinstance(val, (float, int)): return str(int(val))
                    return str(val).strip()
                df_validos['socio_id'] = df_validos.iloc[:, 4].apply(parse_anc)

                fecha_actual = datetime.now().date()
                df_validos['is_active'] = df_validos['fecha_fin_dt'].dt.date >= fecha_actual

                df_validos = df_validos.sort_values(by='is_active', ascending=False)

                df_validos['fecha_inicio_str'] = df_validos['fecha_inicio_dt'].dt.strftime('%Y-%m-%d')
                df_validos['fecha_fin_str'] = df_validos['fecha_fin_dt'].dt.strftime('%Y-%m-%d')

                exitos = 0
                vencidos_importados = 0
                encoding_dummy = np.zeros(128).tobytes()

                df_insertar = df_validos[['socio_id', 'nombre_clean', 'fecha_inicio_str', 'fecha_fin_str', 'medio_pago_clean', 'is_active']]
                time_start = time.time()

                if hasattr(database, 'guardar_socios_masivo'):
                    lista_tuplas = [
                        (r.socio_id, r.nombre_clean, encoding_dummy, r.fecha_inicio_str, r.fecha_fin_str, r.medio_pago_clean)
                        for r in df_insertar.itertuples(index=False)
                    ]
                    try:
                        database.guardar_socios_masivo(lista_tuplas)
                        exitos = len(lista_tuplas)
                        vencidos_importados = int((~df_insertar['is_active']).sum())
                        estado["procesados"] = total_filas
                        estado["exitos"] = exitos
                        estado["vencidos"] = vencidos_importados
                    except Exception:
                        pass

                if exitos == 0:
                    for row in df_insertar.itertuples(index=False):
                        try:
                            database.guardar_socio(
                                row.socio_id,
                                row.nombre_clean,
                                encoding_dummy,
                                row.fecha_inicio_str,
                                row.fecha_fin_str,
                                row.medio_pago_clean
                            )
                            exitos += 1
                            if not row.is_active:
                                vencidos_importados += 1
                        except Exception:
                            estado["errores"] += 1

                        procesados = estado["errores"] + exitos
                        estado["procesados"] = procesados
                        estado["exitos"] = exitos
                        estado["vencidos"] = vencidos_importados

                        elapsed = time.time() - time_start
                        if procesados >= 5 and elapsed > 0:
                            velocidad = procesados / elapsed
                            restantes = total_filas - procesados
                            segundos_restantes = restantes / velocidad
                            estado["tiempo_estimado"] = formatear_tiempo(segundos_restantes)

                estado["procesados"] = total_filas
                estado["fase"] = "finalizado"

            except Exception as e:
                estado["fase"] = "error"
                estado["mensaje_error"] = str(e)

        def actualizar_ui():
            fase = estado["fase"]

            if fase == "leyendo":
                lbl_resultado.config(text="Preprocesando archivo Excel...", bootstyle="info")
                app.root.after(100, actualizar_ui)

            elif fase == "procesando":
                total = estado["total"]
                proc = estado["procesados"]
                porcentaje = (proc / total * 100) if total > 0 else 0

                progress_bar['maximum'] = total
                progress_bar['value'] = proc

                lbl_resultado.config(
                    text=f"Guardando en BD: {proc} / {total} registros ({porcentaje:.1f}%)\n"
                         f"Tiempo estimado restante: {estado['tiempo_estimado']}",
                    bootstyle="info"
                )
                app.root.after(100, actualizar_ui)

            elif fase == "finalizado":
                progress_bar['value'] = estado["total"]
                mensaje = (
                    f"Importación finalizada exitosamente.\n\n"
                    f"Registros agregados (Total): {estado['exitos']}\n"
                    f"De los cuales están vencidos: {estado['vencidos']}\n"
                    f"Omitidos (Errores / Duplicados / Vacíos): {estado['errores']}"
                )
                lbl_resultado.config(text=mensaje, bootstyle="success")
                btn_importar.config(state=NORMAL)

                if hasattr(app, 'actualizar_tabla_excel') and callable(app.actualizar_tabla_excel):
                    app.actualizar_tabla_excel()
                app.cargar_nombres_socios()

            elif fase == "error":
                lbl_resultado.config(text=f"Error crítico: {estado['mensaje_error']}", bootstyle="danger")
                btn_importar.config(state=NORMAL)

        threading.Thread(target=worker, daemon=True).start()
        actualizar_ui()

    btn_importar.config(command=ejecutar_importacion)
