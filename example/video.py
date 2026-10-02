import serial
import serial.tools.list_ports
import cv2
import numpy as np
import time

BAUDIOS = 921600
RESOLUCION = 240
# Delay entre líneas para no saturar el buffer del ESP32. 
# Si el video va lento, ponlo en 0.0005. Si la pantalla se congela, súbelo a 0.002.
DELAY_LINEA = 0.001 
INVERTIR_RGB_BGR = False

def buscar_esp32():
    print("Buscando puerto del ESP32 automáticamente...")
    puertos = serial.tools.list_ports.comports()
    for puerto in puertos:
        if puerto.vid is None:
            continue
        print(f"-> Escuchando en {puerto.device}...")
        try:
            with serial.Serial(puerto.device, BAUDIOS, timeout=1.5) as ser:
                inicio = time.time()
                while time.time() - inicio < 2:
                    if ser.in_waiting > 0:
                        respuesta = ser.readline().decode('utf-8', errors='ignore').strip()
                        if "ESP32_BEACON" in respuesta or "PONG" in respuesta:
                            print(f"¡ESP32 encontrado en el puerto {puerto.device}!\n")
                            return puerto.device
        except Exception:
            pass
    return None

def frame_a_rgb565_lineas(frame):
    """Convierte el frame a RGB565 ultrarrápido usando Numpy a nivel de bits."""
    # 1. Recortar al centro de la cámara
    h, w, _ = frame.shape
    min_dim = min(h, w)
    start_x = w // 2 - min_dim // 2
    start_y = h // 2 - min_dim // 2
    frame_cuadrado = frame[start_y:start_y+min_dim, start_x:start_x+min_dim]
    
    # 2. Redimensionar a 240x240
    frame_red = cv2.resize(frame_cuadrado, (RESOLUCION, RESOLUCION), interpolation=cv2.INTER_AREA)

    # 3. Seleccionar el orden de los colores dinámicamente (OpenCV usa BGR por defecto: 0, 1, 2)
    idx_b, idx_g, idx_r = (2, 1, 0) if INVERTIR_RGB_BGR else (0, 1, 2)
    
    # Extraer canales
    B = frame_red[:, :, idx_b].astype(np.uint16)
    G = frame_red[:, :, idx_g].astype(np.uint16)
    R = frame_red[:, :, idx_r].astype(np.uint16)

    # 4. Empaquetar a RGB565
    R565 = (R & 0xF8) << 8
    G565 = (G & 0xFC) << 3
    B565 = (B >> 3)
    
    rgb565 = R565 | G565 | B565

    # 5. Separar en líneas y devolverlas usando compresión de listas (más rápido)
    return [rgb565[y, :].tobytes() for y in range(RESOLUCION)]

def iniciar_transmision():
    puerto_correcto = buscar_esp32()
    
    if not puerto_correcto:
        print("No se encontró ningún ESP32. Revisa la conexión USB.")
        return

    try:
        # Abrimos la conexión de forma segura (como en tu código original)
        with serial.Serial(puerto_correcto, BAUDIOS, timeout=1) as ser:
            time.sleep(1)
            ser.reset_input_buffer()
            print(f"Conectado exitosamente a {puerto_correcto}.")
            
            print("Despertando pantalla...")
            ser.write(b"PING\n")
            time.sleep(1)

            # Iniciar cámara
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("❌ Error: No se pudo abrir la cámara web.")
                return

            print("🎥 Iniciando transmisión de video... Presiona 'q' en la ventana para salir.")

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Voltear como espejo para que se sienta natural
                frame = cv2.flip(frame, 1)
                
                # Mostrar lo que enviamos en la PC
                cv2.imshow('Transmitiendo a ESP32', frame)

                # Convertir a líneas usando Numpy
                lineas = frame_a_rgb565_lineas(frame)

                ser.reset_input_buffer()
                ser.write(b"START_VIDEO\n")

                # Esperar READY_VIDEO (Timeout rápido)
                listo = False
                t_inicio = time.time()
                while time.time() - t_inicio < 1.0:
                    if ser.in_waiting > 0:
                        respuesta = ser.readline().decode('utf-8', errors='ignore').strip()
                        if respuesta == "READY_VIDEO":
                            listo = True
                            break
                
                if not listo:
                    # Si no responde, evitamos crashear y volvemos a intentarlo en el siguiente frame
                    continue

                # Volcar las 240 líneas al ESP32
                for linea in lineas:
                    ser.write(linea)
                    if DELAY_LINEA > 0:
                        time.sleep(DELAY_LINEA)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except serial.SerialException as e:
        print(f"Error en la comunicación serial: {e}")
    except KeyboardInterrupt:
        print("\nTransmisión detenida por el usuario.")
    finally:
        if 'cap' in locals():
            cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    iniciar_transmision()