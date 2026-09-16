import face_recognition
import cv2
import numpy as np
import os  # ¡Nuevo! Necesario para leer las carpetas y archivos

# 1. CONFIGURACIÓN DE CARPETAS
# Nombre de la carpeta principal donde están las subcarpetas de cada persona
CARPETA_PRINCIPAL = "dataset" 

rostros_conocidos = []
nombres_conocidos = []

print("Cargando imágenes desde las carpetas...")

# 2. LEER CARPETAS AUTOMÁTICAMENTE
# Recorremos cada elemento dentro de la carpeta principal
for nombre_persona in os.listdir(CARPETA_PRINCIPAL):
    ruta_persona = os.path.join(CARPETA_PRINCIPAL, nombre_persona)
    
    # Verificamos que sea una carpeta y no un archivo suelto
    if os.path.isdir(ruta_persona):
        # Recorremos cada foto dentro de la carpeta de la persona
        for nombre_foto in os.listdir(ruta_persona):
            ruta_foto = os.path.join(ruta_persona, nombre_foto)
            
            try:
                # Cargamos la foto y extraemos las características
                imagen = face_recognition.load_image_file(ruta_foto)
                encodings = face_recognition.face_encodings(imagen)
                
                # Verificamos si se detectó al menos una cara en la foto
                if len(encodings) > 0:
                    rostros_conocidos.append(encodings[0])
                    nombres_conocidos.append(nombre_persona) # El nombre de la carpeta
                else:
                    print(f"⚠️ Advertencia: No se detectó ninguna cara en la foto {ruta_foto}")
            except Exception as e:
                print(f"❌ No se pudo leer el archivo {ruta_foto}. Error: {e}")

print(f"✅ ¡Listo! Se cargaron {len(rostros_conocidos)} rostros en total.")

# 3. INICIALIZAR CÁMARA
video_capture = cv2.VideoCapture(0)

print("Iniciando cámara... Presiona 'q' para salir.")

while True:
    ret, frame = video_capture.read()
    if not ret:
        break

    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        # tolerance=0.5 hace que el filtro sea más estricto (por defecto es 0.6)
        matches = face_recognition.compare_faces(rostros_conocidos, face_encoding, tolerance=0.45)
        nombre = "Desconocido"

        # Calculamos la distancia de la cara detectada con todas las caras conocidas
        face_distances = face_recognition.face_distance(rostros_conocidos, face_encoding)
        
        if len(face_distances) > 0:
            # Elegimos el índice de la cara que tenga la distancia MENOR (la más parecida)
            best_match_index = np.argmin(face_distances)

            # Si esa mejor coincidencia es válida, asignamos el nombre de la carpeta
            if matches[best_match_index]:
                nombre = nombres_conocidos[best_match_index]

        # Dibujar recuadro
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, nombre, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    cv2.imshow('Reconocimiento Facial', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()