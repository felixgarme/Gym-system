import sqlite3
import numpy as np
import os
import platform
import subprocess

CARPETA_PRINCIPAL = "fotos_socios"

def conectar_db():
    return sqlite3.connect("gimnasio.db")

def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS socios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            encoding BLOB NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            medio_pago TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            socio_id INTEGER,
            fecha_hora TEXT NOT NULL,
            FOREIGN KEY(socio_id) REFERENCES socios(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL,
            fecha_vencimiento TEXT
        )
    ''')

    cursor.execute("PRAGMA table_info(productos)")
    columnas_prod = [columna[1] for columna in cursor.fetchall()]
    if columnas_prod and "fecha_vencimiento" not in columnas_prod:
        cursor.execute("ALTER TABLE productos ADD COLUMN fecha_vencimiento TEXT")

    conn.commit()
    conn.close()

    if not os.path.exists(CARPETA_PRINCIPAL):
        os.makedirs(CARPETA_PRINCIPAL)

def crear_carpeta_socio(nombre):
    ruta = os.path.join(CARPETA_PRINCIPAL, nombre)
    if not os.path.exists(ruta):
        os.makedirs(ruta)
    return ruta

def abrir_carpeta_socio(nombre):
    ruta = crear_carpeta_socio(nombre)

    if platform.system() == "Windows":
        os.startfile(ruta)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", ruta])
    else:
        subprocess.Popen(["xdg-open", ruta])

def guardar_socio(nombre, encoding_bytes, inicio, fin, pago):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO socios (nombre, encoding, fecha_inicio, fecha_fin, medio_pago)
                      VALUES (?, ?, ?, ?, ?)''', (nombre, encoding_bytes, inicio, fin, pago))
    conn.commit()
    conn.close()

def obtener_socio(nombre):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fecha_inicio, fecha_fin, medio_pago FROM socios WHERE nombre = ?", (nombre,))
    datos = cursor.fetchone()
    conn.close()
    return datos

def actualizar_socio(nombre, inicio, fin, pago):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''UPDATE socios SET fecha_inicio = ?, fecha_fin = ?, medio_pago = ? WHERE nombre = ?''',
                   (inicio, fin, pago, nombre))
    filas_afectadas = cursor.rowcount
    conn.commit()
    conn.close()
    return filas_afectadas > 0

def obtener_todos_los_socios():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, encoding, fecha_fin FROM socios")
    filas = cursor.fetchall()
    conn.close()
    return filas

def registrar_asistencia(socio_id, fecha_hora):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO asistencias (socio_id, fecha_hora) VALUES (?, ?)", (socio_id, fecha_hora))
    conn.commit()
    conn.close()

def obtener_lista_socios():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, fecha_inicio, fecha_fin, medio_pago FROM socios")
    filas = cursor.fetchall()
    conn.close()
    return filas

def obtener_asistencias_socio(nombre):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT fecha_hora FROM asistencias WHERE nombre = ? ORDER BY fecha_hora DESC", (nombre,))
        filas = cursor.fetchall()
    except:
        filas = []
    conn.close()
    return filas

def registrar_asistencia(nombre, fecha_hora):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            fecha_hora TEXT
        )
    ''')

    cursor.execute("PRAGMA table_info(asistencias)")
    columnas = [columna[1] for columna in cursor.fetchall()]

    if "nombre" not in columnas:
        cursor.execute("ALTER TABLE asistencias ADD COLUMN nombre TEXT")

    cursor.execute("INSERT INTO asistencias (nombre, fecha_hora) VALUES (?, ?)", (nombre, fecha_hora))
    conn.commit()
    conn.close()

def eliminar_socio(nombre):
    conn = sqlite3.connect("gimnasio.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM socios WHERE nombre = ?", (nombre,))
    try:
        cursor.execute("DELETE FROM asistencias WHERE nombre_socio = ?", (nombre,))
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def registrar_asistencia_manual(nombre, fecha_hora):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            fecha_hora TEXT
        )
    ''')

    cursor.execute("PRAGMA table_info(asistencias)")
    columnas = [columna[1] for columna in cursor.fetchall()]

    if "nombre" not in columnas:
        cursor.execute("ALTER TABLE asistencias ADD COLUMN nombre TEXT")

    cursor.execute("INSERT INTO asistencias (nombre, fecha_hora) VALUES (?, ?)", (nombre, fecha_hora))
    conn.commit()
    conn.close()

def obtener_productos():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos")
    filas = cursor.fetchall()
    conn.close()
    return filas

def agregar_producto(nombre, precio, stock, fecha_vencimiento=""):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO productos (nombre, precio, stock, fecha_vencimiento) VALUES (?, ?, ?, ?)",
                   (nombre, float(precio), int(stock), fecha_vencimiento))
    conn.commit()
    conn.close()

def eliminar_producto_db(id_producto):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id = ?", (id_producto,))
    conn.commit()
    conn.close()

def actualizar_stock(id_producto, nuevo_stock):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (int(nuevo_stock), id_producto))
    conn.commit()
    conn.close()
