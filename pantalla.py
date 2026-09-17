import serial
import serial.tools.list_ports
import time
import struct
import os
import socket
from PIL import Image

BAUDIOS = 921600

INVERTIR_RGB_BGR = False
VOLTEAR_VERTICAL = False
VOLTEAR_ESPEJO = False

HOST = '127.0.0.1'
PORT = 65432

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
                        if respuesta == "ESP32_BEACON":
                            print(f"¡ESP32 encontrado en el puerto {puerto.device}!\n")
                            return puerto.device
        except Exception:
            pass
    return None

def rgb_to_rgb565(r, g, b):
    if INVERTIR_RGB_BGR:
        r, b = b, r
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def enviar_comando_ping(ser):
    ser.write(b"PING\n")
    respuesta = ser.readline().decode('utf-8', errors='ignore').strip()
    return respuesta == "PONG"

def enviar_imagen(ser, ruta_imagen):
    if not os.path.exists(ruta_imagen):
        print(f"ERROR: El archivo '{ruta_imagen}' no existe en esta carpeta.")
        return
    try:
        img = Image.open(ruta_imagen).convert('RGB').resize((240, 240))
        if VOLTEAR_VERTICAL:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        if VOLTEAR_ESPEJO:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
    except Exception as e:
        print(f"ERROR al intentar abrir la imagen: {e}")
        return

    print(f"Preparando ESP32 para recibir imagen: {ruta_imagen}...")
    ser.write(b"START_IMG\n")

    listo = False
    inicio = time.time()
    while time.time() - inicio < 2.0:
        respuesta = ser.readline().decode('utf-8', errors='ignore').strip()
        if respuesta == "READY":
            listo = True
            break

    if not listo:
        print("Error: El ESP32 no respondió READY a tiempo.")
        return

    print("Enviando datos a la pantalla...")
    for y in range(240):
        buffer_linea = bytearray()
        for x in range(240):
            r, g, b = img.getpixel((x, y))
            color565 = rgb_to_rgb565(r, g, b)
            buffer_linea.extend(struct.pack('<H', color565))

        ser.write(buffer_linea)
        time.sleep(0.002)
    print("¡Imagen enviada y dibujada con éxito!")

def main():
    puerto_correcto = buscar_esp32()

    if not puerto_correcto:
        print("No se encontró ningún ESP32. Revisa la conexión USB.")
        return

    try:
        with serial.Serial(puerto_correcto, BAUDIOS, timeout=1) as ser:
            time.sleep(1)
            ser.reset_input_buffer()

            print(f"Conectado exitosamente a {puerto_correcto}.")
            print("Despertando pantalla...")
            enviar_comando_ping(ser)
            time.sleep(1)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((HOST, PORT))
                s.listen()

                print("\n" + "="*45)
                print(f" ESPERANDO ÓRDENES EN EL PUERTO {PORT}...")
                print("="*45)

                while True:
                    conn, addr = s.accept()
                    with conn:
                        data = conn.recv(1024).decode('utf-8').strip()
                        if not data:
                            continue

                        print(f"-> Orden recibida: {data}")

                        if data == '1' or data == 'BUSCANDO':
                            ser.write(b"SET_BUSCANDO\n")
                        elif data == '2' or data == 'RECONOCIENDO':
                            ser.write(b"SET_RECONOCIENDO\n")
                        elif data == '3' or data == 'VERIFICADO':
                            ser.write(b"SET_VERIFICADO\n")
                        elif data == '4' or data == 'NO_ENCONTRADO':
                            ser.write(b"SET_NO_ENCONTRADO\n")
                        elif data == '5' or data == 'VENCIDO':
                            ser.write(b"SET_VENCIDO\n")
                        elif data.startswith('IMG:'):
                            ruta = data.split('IMG:')[1].strip()
                            enviar_imagen(ser, ruta)
                        elif data == 'EXIT':
                            print("Cerrando servidor por orden remota...")
                            conn.sendall(b"CERRANDO\n")
                            break
                        else:
                            print("Comando no reconocido.")
                            conn.sendall(b"ERROR\n")
                            continue

                        conn.sendall(b"OK\n")

    except serial.SerialException as e:
        print(f"Error al intentar usar el puerto: {e}")
    except KeyboardInterrupt:
        print("\nPrograma terminado por el usuario.")

if __name__ == '__main__':
    main()
