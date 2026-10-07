import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from datetime import datetime, timedelta
import face_recognition
import sqlite3
import os
import numpy as np
import cv2
import time
import ctypes
import database

# --- NUEVAS LIBRERÍAS Y CONSTANTES PARA EL ESP32 ---
import serial
import serial.tools.list_ports

BAUDIOS = 921600
RESOLUCION = 240
DELAY_LINEA = 0.001 
INVERTIR_RGB_BGR = False
# ---------------------------------------------------

def buscar_esp32():
    """Busca el puerto COM del ESP32 silenciosamente"""
    puertos = serial.tools.list_ports.comports()
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
    # Redimensionar a 240x240
    frame_red = cv2.resize(frame, (RESOLUCION, RESOLUCION), interpolation=cv2.INTER_AREA)

    # Seleccionar el orden de los colores (OpenCV usa BGR por defecto)
    idx_b, idx_g, idx_r = (2, 1, 0) if INVERTIR_RGB_BGR else (0, 1, 2)
    
    B = frame_red[:, :, idx_b].astype(np.uint16)
    G = frame_red[:, :, idx_g].astype(np.uint16)
    R = frame_red[:, :, idx_r].astype(np.uint16)

    # Empaquetar a RGB565
    R565 = (R & 0xF8) << 8
    G565 = (G & 0xFC) << 3
    B565 = (B >> 3)
    
    rgb565 = R565 | G565 | B565

    # Devolver array de líneas
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
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) if os.name == 'nt' else cv2.VideoCapture(i)
            if cap.isOpened():
                camaras_nombres.append(f"Cámara {i}")
                cap.release()

    if not camaras_nombres:
        camaras_nombres = ["0: Cámara Predeterminada"]

    return camaras_nombres

def setup_tab_registro(frame, app):
    frame.pack(fill=BOTH, expand=True)

    frame.columnconfigure(0, weight=1)
    frame.columnconfigure(1, weight=0, minsize=180)
    frame.columnconfigure(2, weight=2, minsize=350)
    frame.columnconfigure(3, weight=1)

    frame.rowconfigure(0, weight=1)
    frame.rowconfigure(14, weight=1)

    def validar_fecha(P):
        if P == "": return True
        return all(char.isdigit() or char == '-' for char in P) and len(P) <= 10

    vcmd_fecha = (frame.register(validar_fecha), '%P')

    ttk.Label(frame, text="Registro de Nuevo Socio", font=("Segoe UI", 18, "bold"), bootstyle="primary").grid(row=1, column=1, columnspan=2, pady=(0, 20), sticky=W)

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

    btn_tomar = ttk.Button(frame_botones, text="📷 Capturar Rostro", bootstyle="info", cursor="hand2", padding=(12, 6), command=lambda: capturar_foto_nuevo(reg_nombre, combo_camara))
    btn_tomar.pack(side=LEFT, padx=(0, 10))

    btn_abrir = ttk.Button(frame_botones, text="📂 Ver Archivos", bootstyle="secondary-outline", cursor="hand2", padding=(12, 6), command=lambda: abrir_carpeta_fotos(reg_nombre))
    btn_abrir.pack(side=LEFT, padx=(0, 10))

    ttk.Label(frame_botones, text="(1 a 3 fotos requeridas)", font=("Segoe UI", 9, "italic"), bootstyle="secondary").pack(side=LEFT)

    ttk.Label(frame, text="📅 Detalles de Membresía", font=("Segoe UI", 13, "bold"), bootstyle="info").grid(row=5, column=1, columnspan=2, pady=(25, 10), sticky=W)

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
        if not lbl_duracion.winfo_exists():
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
        except Exception:
            lbl_duracion.config(text="Escribiendo fecha...", bootstyle="secondary")

        frame.after(500, calcular_duracion)

    calcular_duracion()

    ttk.Label(frame, text="Método de Pago:", font=("Segoe UI", 11)).grid(row=9, column=1, sticky=W, pady=8)
    reg_pago = ttk.Combobox(frame, values=["Efectivo", "Yape", "Plin", "Tarjeta", "Transferencia"], state="readonly", font=("Segoe UI", 11), bootstyle="primary")
    reg_pago.set("Efectivo")
    reg_pago.grid(row=9, column=2, sticky=EW, pady=8)

    ttk.Label(frame, text="Nota (Opcional):", font=("Segoe UI", 11)).grid(row=10, column=1, sticky=W, pady=8)
    reg_nota = ttk.Entry(frame, font=("Segoe UI", 11))
    reg_nota.grid(row=10, column=2, sticky=EW, pady=8)

    separator = ttk.Separator(frame, orient=HORIZONTAL)
    separator.grid(row=11, column=1, columnspan=2, sticky=EW, pady=20)

    btn_guardar = ttk.Button(frame, text="💾  Confirmar y Guardar Registro", bootstyle="success", cursor="hand2", padding=(15, 12), command=lambda: guardar_socio(app, reg_nombre, reg_inicio, reg_fin, reg_pago, reg_nota))
    btn_guardar.grid(row=12, column=1, columnspan=2, sticky=EW, pady=(0, 10))

def abrir_carpeta_fotos(entry_nombre):
    nombre = entry_nombre.get().strip()
    if not nombre:
        messagebox.showwarning("Faltan datos", "Por favor, escribe primero el nombre del socio.")
        return
    database.abrir_carpeta_socio(nombre)

def capturar_foto_nuevo(entry_nombre, combo_camara):
    nombre = entry_nombre.get().strip()
    if not nombre:
        messagebox.showwarning("Atención", "Escribe el nombre del socio primero para crear su carpeta.")
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
    os.makedirs(ruta_carpeta, exist_ok=True)

    # --- INICIO LÓGICA ESP32 ---
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
    # ---------------------------

    if os.name == 'nt':
        cap = cv2.VideoCapture(idx_camara, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(idx_camara)

    if not cap.isOpened():
        messagebox.showerror("Error de Cámara", "No se pudo acceder a la cámara seleccionada.")
        if ser and ser.is_open: ser.close()
        return

    window_name = f"Capturar Foto - {nombre}"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    fotos_tomadas = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        orig_height, orig_width, _ = frame.shape
        min_dim = min(orig_height, orig_width)

        start_x = (orig_width - min_dim) // 2
        start_y = (orig_height - min_dim) // 2

        # Recortamos a cuadrado puro
        frame = frame[start_y:start_y+min_dim, start_x:start_x+min_dim]

        # --- TRANSMISIÓN DE VIDEO AL ESP32 ---
        if ser and ser.is_open:
            try:
                # Enviamos el frame limpio al ESP32 ANTES de dibujarle los gráficos encima
                lineas = frame_a_rgb565_lineas(frame)
                ser.reset_input_buffer()
                ser.write(b"START_VIDEO\n")

                # Timeout ultra rápido (0.1s) para no congelar la cámara de la PC
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
                ser.close()
                ser = None
        # -------------------------------------

        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break

        # A partir de aquí dibujamos la interfaz sobre la ventana de la PC
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
        if key == 32: # ESPACIO
            timestamp = int(time.time())
            ruta_foto = os.path.join(ruta_carpeta, f"foto_{timestamp}.jpg")

            cv2.imwrite(ruta_foto, frame)
            fotos_tomadas += 1

            flash = np.full_like(frame, 255)
            cv2.imshow(window_name, flash)
            cv2.waitKey(80)

        elif key == 27: # ESC
            break

    cap.release()
    cv2.destroyAllWindows()
    
    # Cerrar conexión al ESP32 de manera segura
    if ser and ser.is_open:
        ser.close()

    if fotos_tomadas > 0:
        messagebox.showinfo("Proceso Completo", f"Se registraron {fotos_tomadas} fotografías correctamente.")

def guardar_socio(app, entry_nombre, entry_inicio, entry_fin, combo_pago, entry_nota):
    nombre = entry_nombre.get().strip()

    inicio = entry_inicio.entry.get().strip() if hasattr(entry_inicio, 'entry') else entry_inicio.get().strip()
    fin = entry_fin.entry.get().strip() if hasattr(entry_fin, 'entry') else entry_fin.get().strip()

    pago = combo_pago.get()
    nota = entry_nota.get().strip()

    if not nombre:
        messagebox.showwarning("Faltan datos", "El nombre es obligatorio.")
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
                imagen = face_recognition.load_image_file(ruta_imagen)
                encodings = face_recognition.face_encodings(imagen)

                if len(encodings) > 0:
                    encodings_lista.append(encodings[0])

        if len(encodings_lista) == 0:
            messagebox.showerror("Error de Análisis", "No se identificaron rostros en las fotografías tomadas.")
            return

        encoding_promedio = np.mean(encodings_lista, axis=0)
        encoding_bytes = encoding_promedio.tobytes()

        try:
            database.guardar_socio(nombre, encoding_bytes, inicio, fin, pago, nota)
        except TypeError:
            database.guardar_socio(nombre, encoding_bytes, inicio, fin, pago)

        messagebox.showinfo("Éxito", f"Socio '{nombre}' registrado correctamente.")
        entry_nombre.delete(0, END)
        entry_nota.delete(0, END)

        app.cargar_nombres_socios()
        if hasattr(app, 'actualizar_tabla_excel'):
            app.actualizar_tabla_excel()

    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Ya existe un socio registrado con ese nombre.")
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un problema: {e}")