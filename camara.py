import cv2
import face_recognition
import numpy as np
from datetime import datetime
import os
import database
import socket
import subprocess
import sys
import time

ultimo_estado_enviado = None
proceso_pantalla = None

def iniciar_servidor_pantalla():
    global proceso_pantalla
    print("Iniciando pantalla.py en segundo plano...")
    proceso_pantalla = subprocess.Popen([sys.executable, "pantalla.py"])
    time.sleep(3)

def enviar_orden_pantalla(comando):
    """ Envia la orden al ESP32 solo si el estado ha cambiado """
    global ultimo_estado_enviado
    if comando == ultimo_estado_enviado:
        return

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.05)
            s.connect(('127.0.0.1', 65432))
            s.sendall(comando.encode('utf-8'))
            ultimo_estado_enviado = comando
    except Exception:
        pass

def cerrar_servidor_pantalla():
    print("Cerrando servidor de pantalla...")
    enviar_orden_pantalla("EXIT")
    if proceso_pantalla:
        proceso_pantalla.terminate()

def iniciar_reconocimiento(idx_camara=0):
    iniciar_servidor_pantalla()

    filas = database.obtener_todos_los_socios()

    if not filas:
        raise Exception("No hay socios registrados en la base de datos.")

    rostros_conocidos, ids_conocidos, nombres_conocidos, fechas_vencimiento = [], [], [], []
    for socio_id, nombre, encoding_bytes, fecha_fin in filas:
        rostros_conocidos.append(np.frombuffer(encoding_bytes, dtype=np.float64))
        ids_conocidos.append(socio_id)
        nombres_conocidos.append(nombre)
        fechas_vencimiento.append(fecha_fin)

    asistencias_hoy = set()
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    conteo_confirmaciones = {}

    ultimas_asistencias = []

    if os.name == 'nt':
        video_capture = cv2.VideoCapture(idx_camara, cv2.CAP_DSHOW)
    else:
        video_capture = cv2.VideoCapture(idx_camara)

    if not video_capture.isOpened():
        raise Exception("No se pudo acceder a la cámara seleccionada. Verifica la conexión.")

    window_name = "Control de Acceso Gym - (Presiona Q para salir)"

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    process_this_frame = True

    BG_DARK = (60, 60, 60)
    BG_SURFACE = (85, 85, 85)
    ACCENT_MAIN = (30, 150, 245)
    TEXT_LIGHT = (245, 245, 245)
    TEXT_MUTED = (190, 190, 190)
    COLOR_ACTIVO = (100, 210, 80)
    COLOR_VENCIDO = (60, 60, 230)
    COLOR_VERIF = (30, 180, 255)

    tiempo_ultimo_estado_valido = 0
    estado_retenido = "1"
    TIEMPO_RETENCION = 3.0

    while True:
        ret, frame = video_capture.read()
        if not ret:
            break

        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break

        if process_this_frame:
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            nombres_en_pantalla = []
            estados_en_pantalla = []

            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(rostros_conocidos, face_encoding, tolerance=0.40)
                nombre_detectado = "Desconocido"
                estado = ""

                face_distances = face_recognition.face_distance(rostros_conocidos, face_encoding)

                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)

                    if matches[best_match_index]:
                        socio_id = ids_conocidos[best_match_index]
                        nombre_detectado = nombres_conocidos[best_match_index]
                        fecha_fin_socio = fechas_vencimiento[best_match_index]

                        if socio_id not in conteo_confirmaciones:
                            conteo_confirmaciones[socio_id] = 0

                        if socio_id not in asistencias_hoy:
                            conteo_confirmaciones[socio_id] += 1

                            if conteo_confirmaciones[socio_id] < 3:
                                estado = "Verificando"
                            else:
                                hora_actual = datetime.now().strftime("%H:%M:%S")
                                ahora = f"{hoy_str} {hora_actual}"

                                if fecha_fin_socio >= hoy_str:
                                    estado = "Activo"
                                    database.registrar_asistencia(nombre_detectado, ahora)
                                    print(f"✅ Asistencia registrada: {nombre_detectado}")
                                else:
                                    estado = "Vencido"
                                    print(f"❌ Acceso denegado (Vencido): {nombre_detectado}")

                                asistencias_hoy.add(socio_id)

                                ultimas_asistencias.insert(0, {"hora": hora_actual, "nombre": nombre_detectado, "estado": estado})
                                if len(ultimas_asistencias) > 22:
                                    ultimas_asistencias.pop()

                        else:
                            if fecha_fin_socio >= hoy_str:
                                estado = "Activo"
                            else:
                                estado = "Vencido"

                nombres_en_pantalla.append(nombre_detectado)
                estados_en_pantalla.append(estado)

            tiempo_actual = time.time()

            if len(face_locations) == 0:
                if tiempo_actual - tiempo_ultimo_estado_valido > TIEMPO_RETENCION:
                    estado_retenido = "1"
                enviar_orden_pantalla(estado_retenido)
            else:
                primer_nombre = nombres_en_pantalla[0]
                primer_estado = estados_en_pantalla[0]

                if primer_nombre == "Desconocido":
                    if tiempo_actual - tiempo_ultimo_estado_valido > TIEMPO_RETENCION:
                        estado_retenido = "4"
                else:
                    if primer_estado == "Verificando":
                        estado_retenido = "2"
                    elif primer_estado == "Activo":
                        estado_retenido = "3"
                    elif primer_estado == "Vencido":
                        estado_retenido = "5"

                    tiempo_ultimo_estado_valido = tiempo_actual

                enviar_orden_pantalla(estado_retenido)

        process_this_frame = not process_this_frame

        for (top, right, bottom, left), nombre_detectado, estado in zip(face_locations, nombres_en_pantalla, estados_en_pantalla):
            top *= 4; right *= 4; bottom *= 4; left *= 4

            if nombre_detectado == "Desconocido":
                color = TEXT_MUTED
                texto = nombre_detectado
            elif estado == "Verificando":
                color = COLOR_VERIF
                texto = f"{nombre_detectado} - Verificando..."
            elif estado == "Activo":
                color = COLOR_ACTIVO
                texto = f"{nombre_detectado} - OK"
            else:
                color = COLOR_VENCIDO
                texto = f"{nombre_detectado} - VENCIDO"

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, texto, (left + 8, bottom - 10), cv2.FONT_HERSHEY_DUPLEX, 0.65, TEXT_LIGHT, 1)

        h, w, _ = frame.shape
        ancho_panel = 500

        canvas = np.zeros((h, w + ancho_panel, 3), dtype=np.uint8)
        canvas[0:h, 0:w] = frame
        canvas[0:h, w:w+ancho_panel] = BG_DARK
        cv2.rectangle(canvas, (w, 0), (w + ancho_panel, 80), BG_SURFACE, cv2.FILLED)
        cv2.putText(canvas, "ASISTENCIAS RECIENTES", (w + 25, 50), cv2.FONT_HERSHEY_DUPLEX, 0.85, TEXT_LIGHT, 1)
        cv2.line(canvas, (w, 80), (w + ancho_panel, 80), ACCENT_MAIN, 3)

        y_offset = 110
        for info in ultimas_asistencias:
            color_texto = COLOR_ACTIVO if info["estado"] == "Activo" else COLOR_VENCIDO
            texto_hora = f"[{info['hora']}]"
            texto_nombre = f"{info['nombre']}"
            texto_estado = f"{info['estado']}"

            cv2.putText(canvas, texto_hora, (w + 20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_MUTED, 1)
            cv2.putText(canvas, texto_nombre, (w + 110, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT_LIGHT, 1)
            cv2.putText(canvas, texto_estado, (w + 380, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_texto, 1)

            y_offset += 25

        cv2.imshow(window_name, canvas)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            break

    video_capture.release()
    cv2.destroyAllWindows()
    cerrar_servidor_pantalla()

if __name__ == "__main__":
    iniciar_reconocimiento()
