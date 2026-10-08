import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import datetime, timedelta
import face_recognition
import sqlite3
import os
import re
import glob
import numpy as np
import cv2
import time
import ctypes
import database

import serial
import serial.tools.list_ports

BAUDIOS = 921600
RESOLUCION = 240
DELAY_LINEA = 0.001
INVERTIR_RGB_BGR = False

ID_INICIAL = 1000
ARCHIVO_CONTADOR_ID = "ultimo_id_socio.txt"
MAX_REINTENTOS_ID = 50

CARACTERES_INVALIDOS_NOMBRE = '<>:"/\\|?*'

def _rutas_posibles_db():
    """Intenta descubrir las rutas de la base de datos SQLite usada por database.py"""
    rutas = []

    for nombre in dir(database):
        try:
            valor = getattr(database, nombre)
        except Exception:
            continue
        if isinstance(valor, str):
            if valor.lower().endswith(('.db', '.sqlite', '.sqlite3')):
                rutas.append(valor)
                try:
                    base = os.path.dirname(os.path.abspath(database.__file__))
                    rutas.append(os.path.join(base, valor))
                except Exception:
                    pass

    try:
        base = os.path.dirname(os.path.abspath(database.__file__))
        for carpeta in {base, os.getcwd()}:
            for ext in ("*.db", "*.sqlite", "*.sqlite3"):
                rutas.extend(glob.glob(os.path.join(carpeta, ext)))
    except Exception:
        pass

    vistas, unicas = set(), []
    for r in rutas:
        ra = os.path.abspath(r)
        if ra not in vistas and os.path.isfile(ra):
            vistas.add(ra)
            unicas.append(ra)
    return unicas

def _leer_ids_existentes():
    """Devuelve lista de socio_id (como str) de la BD, o None si no se pudo leer."""
    for ruta in _rutas_posibles_db():
        try:
            con = sqlite3.connect(ruta, timeout=5)
            try:
                cur = con.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tablas = [t[0] for t in cur.fetchall()]
                for tabla in tablas:
                    cur.execute(f'PRAGMA table_info("{tabla}")')
                    columnas = [c[1] for c in cur.fetchall()]
                    for col in columnas:
                        if col.lower() == "socio_id":
                            cur.execute(f'SELECT "{col}" FROM "{tabla}"')
                            return [str(f[0]) for f in cur.fetchall() if f[0] is not None]
            finally:
                con.close()
        except Exception:
            continue
    return None

def _leer_contador_respaldo():
    try:
        with open(ARCHIVO_CONTADOR_ID, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None

def _guardar_contador_respaldo(valor):
    try:
        with open(ARCHIVO_CONTADOR_ID, "w") as f:
            f.write(str(int(valor)))
    except Exception:
        pass

def obtener_siguiente_id(minimo=None):
    """
    Devuelve el siguiente ID numérico disponible (str).
    Ej.: si el último es 9506 -> "9507". Crece sin límite (9999 -> 10000).
    'minimo' permite forzar que el ID sea al menos ese valor (para reintentos).
    """
    for nombre_fn in ("obtener_siguiente_id", "siguiente_id"):
        fn = getattr(database, nombre_fn, None)
        if callable(fn):
            try:
                valor = fn()
                if valor is not None and str(valor).isdigit():
                    candidato = int(valor)
                    if minimo is not None:
                        candidato = max(candidato, minimo)
                    return str(candidato)
            except Exception:
                pass

    mayor = None
    ids = _leer_ids_existentes()
    if ids:
        numericos = [int(i) for i in ids if re.fullmatch(r"\d+", i.strip())]
        if numericos:
            mayor = max(numericos)

    respaldo = _leer_contador_respaldo()
    if respaldo is not None:
        mayor = respaldo if mayor is None else max(mayor, respaldo)

    siguiente = ID_INICIAL if mayor is None else mayor + 1
    if siguiente < ID_INICIAL:
        siguiente = ID_INICIAL
    if minimo is not None:
        siguiente = max(siguiente, minimo)
    return str(siguiente)

def buscar_esp32():
    """Busca el puerto COM del ESP32 silenciosamente"""
    try:
        puertos = serial.tools.list_ports.comports()
    except Exception:
        return None
    for puerto in puertos:
        if puerto.vid is None:
            continue
        try:
            with serial.Serial(puerto.device, BAUDIOS, timeout=0.5) as ser:
                inicio = time.time()
                while time.time() - inicio < 1.0:
                    if ser.in_waiting > 0:
                        respuesta = ser.readline().decode('utf-8', errors='ignore').strip()
                        if "ESP32_BEACON" in respuesta or "PONG" in respuesta:
                            return puerto.device
        except Exception:
            pass
    return None

def frame_a_rgb565_lineas(frame):
    """Convierte un frame cuadrado a formato RGB565 para la pantalla TFT"""
    frame_red = cv2.resize(frame, (RESOLUCION, RESOLUCION), interpolation=cv2.INTER_AREA)

    idx_b, idx_g, idx_r = (2, 1, 0) if INVERTIR_RGB_BGR else (0, 1, 2)

    B = frame_red[:, :, idx_b].astype(np.uint16)
    G = frame_red[:, :, idx_g].astype(np.uint16)
    R = frame_red[:, :, idx_r].astype(np.uint16)

    R565 = (R & 0xF8) << 8
    G565 = (G & 0xFC) << 3
    B565 = (B >> 3)

    rgb565 = R565 | G565 | B565

    return [rgb565[y, :].tobytes() for y in range(RESOLUCION)]

def obtener_camaras():
    camaras_nombres = []
    try:
        from pygrabber.dshow_graph import FilterGraph
        graph = FilterGraph()
        dispositivos = graph.get_input_devices()
        for i, nombre in enumerate(dispositivos):
            camaras_nombres.append(f"{i}: {nombre}")
    except Exception:
        for i in range(4):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if os.name == 'nt' else cv2.VideoCapture(i)
                if cap.isOpened():
                    camaras_nombres.append(f"Cámara {i}")
                cap.release()
            except Exception:
                pass

    if not camaras_nombres:
        camaras_nombres = ["0: Cámara Predeterminada"]

    return camaras_nombres

def setup_tab_registro(frame, app):
    frame.pack(fill=BOTH, expand=True)

    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=0, minsize=180)
    frame.columnconfigure(2, weight=3, minsize=300)
    frame.columnconfigure(3, weight=1)

    frame.rowconfigure(0, weight=1)
    frame.rowconfigure(14, weight=1)

    def validar_fecha(P):
        if P == "":
            return True
        return all(char.isdigit() or char == '-' for char in P) and len(P) <= 10

    vcmd_fecha = (frame.register(validar_fecha), '%P')

    ttk.Label(frame, text="Registro de Nuevo Socio", font=("Segoe UI", 18, "bold"),
              bootstyle="primary").grid(row=1, column=1, columnspan=2, pady=(0, 5), sticky=W)

    lbl_id = ttk.Label(frame, text="ID a asignar: ...", font=("Segoe UI", 11, "bold"), bootstyle="warning")
    lbl_id.grid(row=1, column=2, sticky=E, pady=(0, 5))

    def refrescar_id():
        try:
            if lbl_id.winfo_exists():
                lbl_id.config(text=f"ID a asignar: {obtener_siguiente_id()}")
        except Exception:
            pass

    refrescar_id()
    frame.refrescar_id = refrescar_id

    ttk.Label(frame, text="Nombre Completo:", font=("Segoe UI", 11)).grid(row=2, column=1, sticky=W, pady=10)
    reg_nombre = ttk.Entry(frame, font=("Segoe UI", 11))
    reg_nombre.grid(row=2, column=2, sticky=EW, pady=10)

    ttk.Label(frame, text="Dispositivo de Video:", font=("Segoe UI", 11)).grid(row=3, column=1, sticky=W, pady=10)

    lista_camaras = obtener_camaras()
    combo_camara = ttk.Combobox(frame, values=lista_camaras, state="readonly", font=("Segoe UI", 11), bootstyle="primary")
    if lista_camaras:
        combo_camara.set(lista_camaras[0])
    combo_camara.grid(row=3, column=2, sticky=EW, pady=10)

    ttk.Label(frame, text="Datos Biométricos:", font=("Segoe UI", 11)).grid(row=4, column=1, sticky=W, pady=10)

    frame_botones = ttk.Frame(frame)
    frame_botones.grid(row=4, column=2, sticky=EW, pady=10)
    frame_botones.columnconfigure(0, weight=0)
    frame_botones.columnconfigure(1, weight=0)
    frame_botones.columnconfigure(2, weight=1)

    btn_tomar = ttk.Button(frame_botones, text="📷 Capturar Rostro", bootstyle="info", cursor="hand2",
                           padding=(12, 6), command=lambda: capturar_foto_nuevo(reg_nombre, combo_camara))
    btn_tomar.grid(row=0, column=0, padx=(0, 10), pady=2, sticky=W)

    btn_abrir = ttk.Button(frame_botones, text="📂 Ver Archivos", bootstyle="secondary-outline", cursor="hand2",
                           padding=(12, 6), command=lambda: abrir_carpeta_fotos(reg_nombre))
    btn_abrir.grid(row=0, column=1, padx=(0, 10), pady=2, sticky=W)

    ttk.Label(frame_botones, text="(1 a 3 fotos requeridas)", font=("Segoe UI", 9, "italic"),
              bootstyle="secondary").grid(row=0, column=2, sticky=W)

    ttk.Label(frame, text="📅 Detalles de Membresía", font=("Segoe UI", 13, "bold"),
              bootstyle="info").grid(row=5, column=1, columnspan=2, pady=(25, 10), sticky=W)

    lbl_duracion = ttk.Label(frame, text="...", font=("Segoe UI", 10, "bold"), bootstyle="success")
    lbl_duracion.grid(row=6, column=2, sticky=W, pady=(0, 5))

    hoy = datetime.now()
    mes_siguiente = hoy + timedelta(days=30)

    ttk.Label(frame, text="Fecha de Inicio:", font=("Segoe UI", 11)).grid(row=7, column=1, sticky=W, pady=8)
    reg_inicio = ttk.DateEntry(frame, startdate=hoy, bootstyle="primary", dateformat="%Y-%m-%d")
    reg_inicio.entry.configure(validate="key", validatecommand=vcmd_fecha, font=("Segoe UI", 11))
    reg_inicio.grid(row=7, column=2, sticky=EW, pady=8)

    ttk.Label(frame, text="Vencimiento:", font=("Segoe UI", 11)).grid(row=8, column=1, sticky=W, pady=8)
    reg_fin = ttk.DateEntry(frame, startdate=mes_siguiente, bootstyle="primary", dateformat="%Y-%m-%d")
    reg_fin.entry.configure(validate="key", validatecommand=vcmd_fecha, font=("Segoe UI", 11))
    reg_fin.grid(row=8, column=2, sticky=EW, pady=8)

    def calcular_duracion():
        try:
            if not lbl_duracion.winfo_exists():
                return
        except Exception:
            return

        try:
            inicio_str = reg_inicio.entry.get().strip()
            fin_str = reg_fin.entry.get().strip()

            d_inicio = datetime.strptime(inicio_str, "%Y-%m-%d")
            d_fin = datetime.strptime(fin_str, "%Y-%m-%d")
            dias = (d_fin - d_inicio).days

            if dias < 0:
                lbl_duracion.config(text="⚠️ La fecha de vencimiento no puede ser menor al inicio", bootstyle="danger")
            elif dias == 0:
                lbl_duracion.config(text="⏳ Duración: Mismo día (0 días)", bootstyle="warning")
            else:
                meses = dias // 30
                if meses >= 1:
                    lbl_duracion.config(text=f"⏱️ Tiempo asignado: {meses} mes(es) ({dias} días en total)", bootstyle="success")
                else:
                    lbl_duracion.config(text=f"⏱️ Tiempo asignado: {dias} días", bootstyle="info")
        except tk.TclError:
            return
        except Exception:
            try:
                lbl_duracion.config(text="Escribiendo fecha...", bootstyle="secondary")
            except Exception:
                return

        try:
            frame.after(500, calcular_duracion)
        except Exception:
            pass

    calcular_duracion()

    ttk.Label(frame, text="Método de Pago:", font=("Segoe UI", 11)).grid(row=9, column=1, sticky=W, pady=8)
    reg_pago = ttk.Combobox(frame, values=["Efectivo", "Yape", "Plin", "Tarjeta", "Transferencia"],
                            state="readonly", font=("Segoe UI", 11), bootstyle="primary")
    reg_pago.set("Efectivo")
    reg_pago.grid(row=9, column=2, sticky=EW, pady=8)

    ttk.Label(frame, text="Nota (Opcional):", font=("Segoe UI", 11)).grid(row=10, column=1, sticky=W, pady=8)
    reg_nota = ttk.Entry(frame, font=("Segoe UI", 11))
    reg_nota.grid(row=10, column=2, sticky=EW, pady=8)

    separator = ttk.Separator(frame, orient=HORIZONTAL)
    separator.grid(row=11, column=1, columnspan=2, sticky=EW, pady=20)

    btn_guardar = ttk.Button(frame, text="💾  Confirmar y Guardar Registro", bootstyle="success", cursor="hand2",
                             padding=(15, 12),
                             command=lambda: guardar_socio(app, reg_nombre, reg_inicio, reg_fin, reg_pago,
                                                           reg_nota, refrescar_id))
    btn_guardar.grid(row=12, column=1, columnspan=2, sticky=EW, pady=(0, 10))

def abrir_carpeta_fotos(entry_nombre):
    nombre = entry_nombre.get().strip()
    if not nombre:
        messagebox.showwarning("Faltan datos", "Por favor, escribe primero el nombre del socio.")
        return
    if any(c in nombre for c in CARACTERES_INVALIDOS_NOMBRE):
        messagebox.showwarning("Nombre inválido", f"El nombre no puede contener: {CARACTERES_INVALIDOS_NOMBRE}")
        return
    try:
        database.abrir_carpeta_socio(nombre)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")

def capturar_foto_nuevo(entry_nombre, combo_camara):
    nombre = entry_nombre.get().strip()
    if not nombre:
        messagebox.showwarning("Atención", "Escribe el nombre del socio primero para crear su carpeta.")
        return

    if any(c in nombre for c in CARACTERES_INVALIDOS_NOMBRE):
        messagebox.showwarning("Nombre inválido", f"El nombre no puede contener: {CARACTERES_INVALIDOS_NOMBRE}")
        return

    seleccion = combo_camara.get()
    try:
        if ":" in seleccion:
            idx_camara = int(seleccion.split(":")[0])
        else:
            idx_camara = int(seleccion.split()[-1])
    except Exception:
        idx_camara = 0

    ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre)
    try:
        os.makedirs(ruta_carpeta, exist_ok=True)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo crear la carpeta del socio: {e}")
        return

    puerto_esp32 = buscar_esp32()
    ser = None
    if puerto_esp32:
        try:
            ser = serial.Serial(puerto_esp32, BAUDIOS, timeout=0.1)
            time.sleep(0.5)
            ser.reset_input_buffer()
            ser.write(b"PING\n")
        except Exception as e:
            print(f"No se pudo iniciar la conexión serial: {e}")
            ser = None

    if os.name == 'nt':
        cap = cv2.VideoCapture(idx_camara, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(idx_camara)

    if not cap.isOpened():
        messagebox.showerror("Error de Cámara", "No se pudo acceder a la cámara seleccionada.")
        try:
            if ser and ser.is_open:
                ser.close()
        except Exception:
            pass
        return

    window_name = f"Capturar Foto - {nombre}"
    fotos_tomadas = 0

    try:
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame = cv2.flip(frame, 1)

            orig_height, orig_width, _ = frame.shape
            min_dim = min(orig_height, orig_width)

            start_x = (orig_width - min_dim) // 2
            start_y = (orig_height - min_dim) // 2

            frame = frame[start_y:start_y + min_dim, start_x:start_x + min_dim]

            if ser and ser.is_open:
                try:
                    lineas = frame_a_rgb565_lineas(frame)
                    ser.reset_input_buffer()
                    ser.write(b"START_VIDEO\n")

                    listo = False
                    t_inicio = time.time()
                    while time.time() - t_inicio < 0.1:
                        if ser.in_waiting > 0:
                            respuesta = ser.readline().decode('utf-8', errors='ignore').strip()
                            if respuesta == "READY_VIDEO":
                                listo = True
                                break

                    if listo:
                        for linea in lineas:
                            ser.write(linea)
                            if DELAY_LINEA > 0:
                                time.sleep(DELAY_LINEA)
                except Exception as e:
                    print(f"Error transmitiendo a ESP32: {e}")
                    try:
                        ser.close()
                    except Exception:
                        pass
                    ser = None

            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break

            display_frame = frame.copy()
            height, width, _ = display_frame.shape

            centro_x, centro_y = width // 2, height // 2
            eje_x, eje_y = int(width * 0.25), int(height * 0.35)

            COLOR_OVAL = (241, 102, 99)
            COLOR_CRUZ = (170, 161, 161)
            COLOR_BARRA = (27, 24, 24)
            COLOR_TEXTO = (250, 250, 250)

            cv2.ellipse(display_frame, (centro_x, centro_y), (eje_x, eje_y), 0, 0, 360, COLOR_OVAL, 2, cv2.LINE_AA)
            cv2.line(display_frame, (centro_x - 12, centro_y), (centro_x + 12, centro_y), COLOR_CRUZ, 1, cv2.LINE_AA)
            cv2.line(display_frame, (centro_x, centro_y - 12), (centro_x, centro_y + 12), COLOR_CRUZ, 1, cv2.LINE_AA)

            overlay = display_frame.copy()
            cv2.rectangle(overlay, (0, 0), (width, 60), COLOR_BARRA, -1)
            cv2.addWeighted(overlay, 0.75, display_frame, 0.25, 0, display_frame)

            cv2.putText(display_frame, f"Fotos: {fotos_tomadas} / 3",
                        (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_OVAL, 2, cv2.LINE_AA)

            cv2.putText(display_frame, "| [ESPACIO] Capturar | [ESC] Salir",
                        (130, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_TEXTO, 1, cv2.LINE_AA)

            cv2.putText(display_frame, "Alinee el rostro dentro del recuadro",
                        (centro_x - 130, height - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_TEXTO, 1, cv2.LINE_AA)

            cv2.imshow(window_name, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 32:
                timestamp = int(time.time() * 1000)
                ruta_foto = os.path.join(ruta_carpeta, f"foto_{timestamp}.jpg")

                if cv2.imwrite(ruta_foto, frame):
                    fotos_tomadas += 1

                flash = np.full_like(frame, 255)
                cv2.imshow(window_name, flash)
                cv2.waitKey(80)

            elif key == 27:
                break
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un problema durante la captura: {e}")
    finally:
        try:
            cap.release()
        except Exception:
            pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        try:
            if ser and ser.is_open:
                ser.close()
        except Exception:
            pass

    if fotos_tomadas > 0:
        messagebox.showinfo("Proceso Completo", f"Se registraron {fotos_tomadas} fotografías correctamente.")

def guardar_socio(app, entry_nombre, entry_inicio, entry_fin, combo_pago, entry_nota, refrescar_id=None):
    nombre = entry_nombre.get().strip()

    inicio = entry_inicio.entry.get().strip() if hasattr(entry_inicio, 'entry') else entry_inicio.get().strip()
    fin = entry_fin.entry.get().strip() if hasattr(entry_fin, 'entry') else entry_fin.get().strip()

    pago = combo_pago.get()
    nota = entry_nota.get().strip()

    if not nombre:
        messagebox.showwarning("Faltan datos", "El nombre es obligatorio.")
        return

    if any(c in nombre for c in CARACTERES_INVALIDOS_NOMBRE):
        messagebox.showwarning("Nombre inválido", f"El nombre no puede contener: {CARACTERES_INVALIDOS_NOMBRE}")
        return

    try:
        d_inicio = datetime.strptime(inicio, "%Y-%m-%d")
        d_fin = datetime.strptime(fin, "%Y-%m-%d")
    except ValueError:
        messagebox.showwarning("Fecha inválida", "Las fechas deben tener el formato AAAA-MM-DD.")
        return

    if d_fin < d_inicio:
        messagebox.showwarning("Fecha inválida", "La fecha de vencimiento no puede ser menor a la de inicio.")
        return

    if not pago:
        messagebox.showwarning("Faltan datos", "Selecciona un método de pago.")
        return

    ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre)

    if not os.path.exists(ruta_carpeta) or not os.listdir(ruta_carpeta):
        messagebox.showwarning("Faltan fotos", f"La carpeta de {nombre} está vacía. Captura fotografías primero.")
        return

    try:
        encodings_lista = []
        archivos = os.listdir(ruta_carpeta)

        for archivo in archivos:
            if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                ruta_imagen = os.path.join(ruta_carpeta, archivo)
                try:
                    imagen = face_recognition.load_image_file(ruta_imagen)
                    encodings = face_recognition.face_encodings(imagen)
                except Exception:
                    continue

                if len(encodings) > 0:
                    encodings_lista.append(encodings[0])

        if len(encodings_lista) == 0:
            messagebox.showerror("Error de Análisis", "No se identificaron rostros en las fotografías tomadas.")
            return

        encoding_promedio = np.mean(encodings_lista, axis=0)
        encoding_bytes = encoding_promedio.tobytes()

        socio_id = obtener_siguiente_id()
        guardado = False
        ultimo_error = None

        for _ in range(MAX_REINTENTOS_ID):
            try:
                database.guardar_socio(socio_id, nombre, encoding_bytes, inicio, fin, pago)
                guardado = True
                break
            except sqlite3.IntegrityError as e:
                ultimo_error = e
                mensaje = str(e).lower()
                if "socio_id" in mensaje or "primary" in mensaje:
                    socio_id = obtener_siguiente_id(minimo=int(socio_id) + 1)
                    continue
                raise

        if not guardado:
            raise ultimo_error if ultimo_error else RuntimeError("No se pudo asignar un ID único.")

        _guardar_contador_respaldo(socio_id)

        messagebox.showinfo("Éxito", f"Socio '{nombre}' registrado correctamente.\nID asignado: {socio_id}")
        entry_nombre.delete(0, END)
        entry_nota.delete(0, END)

        try:
            app.cargar_nombres_socios()
        except Exception:
            pass
        if hasattr(app, 'actualizar_tabla_excel'):
            try:
                app.actualizar_tabla_excel()
            except Exception:
                pass

        if callable(refrescar_id):
            refrescar_id()

    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Ya existe un socio registrado con ese nombre.")
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un problema: {e}")
