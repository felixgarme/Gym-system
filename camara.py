import cv2
import face_recognition
import numpy as np
from datetime import datetime
import os
import database

def iniciar_reconocimiento(idx_camara=0):
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
    
    # LISTA PARA EL PANEL LATERAL (Guarda las últimas asistencias)
    ultimas_asistencias = []

    # Inicializar la cámara según el índice seleccionado
    if os.name == 'nt':
        video_capture = cv2.VideoCapture(idx_camara, cv2.CAP_DSHOW)
    else:
        video_capture = cv2.VideoCapture(idx_camara)

    if not video_capture.isOpened():
        raise Exception("No se pudo acceder a la cámara seleccionada. Verifica la conexión.")

    window_name = "Control de Acceso Gym - (Presiona Q para salir)"
    
    # CONFIGURACIÓN RESPONSIVE SIN PANTALLA COMPLETA
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)  # Tamaño de ventana inicial adaptable

    process_this_frame = True

    # --- PALETA TITANIO Y CÁLIDA (Sin azul ni negro, formato BGR) ---
    BG_DARK = (60, 60, 60)         # Gris titanio neutro medio
    BG_SURFACE = (85, 85, 85)      # Gris pizarra claro para cabecera y relieve
    ACCENT_MAIN = (30, 150, 245)   # Naranja / Ámbar cálido (BGR)
    TEXT_LIGHT = (245, 245, 245)   # Blanco limpio
    TEXT_MUTED = (190, 190, 190)   # Gris claro para texto secundario
    COLOR_ACTIVO = (100, 210, 80)  # Verde Esmeralda brillante (BGR)
    COLOR_VENCIDO = (60, 60, 230)  # Rojo carmesí (BGR)
    COLOR_VERIF = (30, 180, 255)   # Amarillo brillante (BGR)

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
                                
                                # AGREGAR AL HISTORIAL DEL PANEL LATERAL
                                ultimas_asistencias.insert(0, {"hora": hora_actual, "nombre": nombre_detectado, "estado": estado})
                                # Aumentamos un poco la capacidad de la lista visible ya que ahora están más pegados
                                if len(ultimas_asistencias) > 22:
                                    ultimas_asistencias.pop()
                                    
                        else:
                            if fecha_fin_socio >= hoy_str:
                                estado = "Activo"
                            else:
                                estado = "Vencido"

                nombres_en_pantalla.append(nombre_detectado)
                estados_en_pantalla.append(estado)

        process_this_frame = not process_this_frame

        # DIBUJAR CUADROS EN LA CÁMARA
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

        # ---------------------------------------------------------
        # CREACIÓN DEL LIENZO (CANVAS) EN GRIS TITANIO Y AMBAR
        # ---------------------------------------------------------
        h, w, _ = frame.shape
        ancho_panel = 500  
        
        # Lienzo general
        canvas = np.zeros((h, w + ancho_panel, 3), dtype=np.uint8)
        
        # Pegar imagen de la cámara en el lado izquierdo
        canvas[0:h, 0:w] = frame
        
        # Colorear panel derecho en Gris Titanio (Sin negro / Sin azul)
        canvas[0:h, w:w+ancho_panel] = BG_DARK
        
        # Cabecera del Panel (Gris Pizarra Claro)
        cv2.rectangle(canvas, (w, 0), (w + ancho_panel, 80), BG_SURFACE, cv2.FILLED)
        
        # Título
        cv2.putText(canvas, "ASISTENCIAS RECIENTES", (w + 25, 50), cv2.FONT_HERSHEY_DUPLEX, 0.85, TEXT_LIGHT, 1)
        
        # Línea divisoria en Naranja / Ámbar Cálido
        cv2.line(canvas, (w, 80), (w + ancho_panel, 80), ACCENT_MAIN, 3)
        
        # Historial de asistencias
        y_offset = 110 # Ajustado para empezar un poco más arriba
        for info in ultimas_asistencias:
            color_texto = COLOR_ACTIVO if info["estado"] == "Activo" else COLOR_VENCIDO

            texto_hora = f"[{info['hora']}]"
            texto_nombre = f"{info['nombre']}"
            texto_estado = f"{info['estado']}"

            # Escala de texto reducida a 0.5 y 0.55, grosor ajustado a 1
            cv2.putText(canvas, texto_hora, (w + 20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_MUTED, 1)
            cv2.putText(canvas, texto_nombre, (w + 110, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.55, TEXT_LIGHT, 1)
            cv2.putText(canvas, texto_estado, (w + 380, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_texto, 1)

            # Incremento reducido de 45 a 25 para que estén más pegados
            y_offset += 25

        cv2.imshow(window_name, canvas)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            break

    video_capture.release()
    cv2.destroyAllWindows()