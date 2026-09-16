import face_recognition
import cv2
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ==========================================
# 1. BASE DE DATOS
# ==========================================
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
    conn.commit()
    conn.close()

# ==========================================
# 2. INTERFAZ GRÁFICA (Tkinter)
# ==========================================
class GymApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Gimnasio - Control de Acceso")
        self.root.geometry("550x450")
        self.root.resizable(False, False)

        inicializar_db()

        # Estilo de las pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, expand=True)

        # Crear los "Frames" (Pestañas)
        self.tab_registro = ttk.Frame(self.notebook, width=500, height=400)
        self.tab_gestion = ttk.Frame(self.notebook, width=500, height=400)
        self.tab_camara = ttk.Frame(self.notebook, width=500, height=400)

        self.tab_registro.pack(fill='both', expand=True)
        self.tab_gestion.pack(fill='both', expand=True)
        self.tab_camara.pack(fill='both', expand=True)

        self.notebook.add(self.tab_registro, text='Nuevo Socio')
        self.notebook.add(self.tab_gestion, text='Buscar / Renovar')
        self.notebook.add(self.tab_camara, text='Control de Acceso')

        self.setup_tab_registro()
        self.setup_tab_gestion()
        self.setup_tab_camara()

    # --- PESTAÑA 1: REGISTRO ---
    def setup_tab_registro(self):
        ttk.Label(self.tab_registro, text="Registrar Nuevo Socio", font=("Arial", 14, "bold")).place(x=150, y=20)

        # Nombre
        ttk.Label(self.tab_registro, text="Nombre:").place(x=50, y=80)
        self.reg_nombre = ttk.Entry(self.tab_registro, width=35)
        self.reg_nombre.place(x=150, y=80)

        # Foto
        ttk.Label(self.tab_registro, text="Foto:").place(x=50, y=120)
        self.reg_ruta_foto = ttk.Entry(self.tab_registro, width=25, state='readonly')
        self.reg_ruta_foto.place(x=150, y=120)
        ttk.Button(self.tab_registro, text="Buscar", command=self.seleccionar_foto).place(x=320, y=118)

        # Fechas por defecto (Hoy y en 30 días)
        hoy = datetime.now()
        mes_siguiente = hoy + timedelta(days=30)

        # Fecha Inicio
        ttk.Label(self.tab_registro, text="Fecha Inicio:").place(x=50, y=160)
        self.reg_inicio = ttk.Entry(self.tab_registro, width=35)
        self.reg_inicio.insert(0, hoy.strftime("%Y-%m-%d"))
        self.reg_inicio.place(x=150, y=160)

        # Fecha Fin
        ttk.Label(self.tab_registro, text="Fecha Vence:").place(x=50, y=200)
        self.reg_fin = ttk.Entry(self.tab_registro, width=35)
        self.reg_fin.insert(0, mes_siguiente.strftime("%Y-%m-%d"))
        self.reg_fin.place(x=150, y=200)

        # Medio de Pago
        ttk.Label(self.tab_registro, text="Medio Pago:").place(x=50, y=240)
        self.reg_pago = ttk.Combobox(self.tab_registro, values=["Efectivo", "Yape", "Plin", "Tarjeta"], width=32, state="readonly")
        self.reg_pago.set("Efectivo")
        self.reg_pago.place(x=150, y=240)

        # Botón Guardar
        ttk.Button(self.tab_registro, text="Guardar Socio", command=self.guardar_socio).place(x=200, y=300)

    def seleccionar_foto(self):
        ruta = filedialog.askopenfilename(title="Seleccionar foto", filetypes=[("Archivos de imagen", "*.jpg *.jpeg *.png")])
        if ruta:
            self.reg_ruta_foto.config(state='normal')
            self.reg_ruta_foto.delete(0, tk.END)
            self.reg_ruta_foto.insert(0, ruta)
            self.reg_ruta_foto.config(state='readonly')

    def guardar_socio(self):
        nombre = self.reg_nombre.get().strip()
        ruta = self.reg_ruta_foto.get()
        inicio = self.reg_inicio.get()
        fin = self.reg_fin.get()
        pago = self.reg_pago.get()

        if not nombre or not ruta:
            messagebox.showwarning("Faltan datos", "El nombre y la foto son obligatorios.")
            return

        try:
            imagen = face_recognition.load_image_file(ruta)
            encodings = face_recognition.face_encodings(imagen)
            
            if len(encodings) == 0:
                messagebox.showerror("Error", "No se detectó ninguna cara en la foto seleccionada.")
                return

            encoding_bytes = encodings[0].tobytes()
            
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO socios (nombre, encoding, fecha_inicio, fecha_fin, medio_pago)
                              VALUES (?, ?, ?, ?, ?)''', (nombre, encoding_bytes, inicio, fin, pago))
            conn.commit()
            conn.close()
            messagebox.showinfo("Éxito", f"Socio '{nombre}' registrado exitosamente.")
            self.reg_nombre.delete(0, tk.END)
            self.reg_ruta_foto.config(state='normal')
            self.reg_ruta_foto.delete(0, tk.END)
            self.reg_ruta_foto.config(state='readonly')
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Ya existe un socio con ese nombre.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un problema: {e}")

    # --- PESTAÑA 2: GESTIÓN Y RENOVACIÓN ---
    def setup_tab_gestion(self):
        ttk.Label(self.tab_gestion, text="Buscar Socio", font=("Arial", 12)).place(x=50, y=30)
        self.buscar_nombre = ttk.Entry(self.tab_gestion, width=25)
        self.buscar_nombre.place(x=160, y=30)
        ttk.Button(self.tab_gestion, text="Buscar", command=self.buscar_socio).place(x=330, y=28)

        # Separador
        ttk.Separator(self.tab_gestion, orient='horizontal').place(x=20, y=70, width=460)

        # Campos de actualización
        ttk.Label(self.tab_gestion, text="Fecha Inicio:").place(x=50, y=100)
        self.act_inicio = ttk.Entry(self.tab_gestion, width=35)
        self.act_inicio.place(x=150, y=100)

        ttk.Label(self.tab_gestion, text="Fecha Vence:").place(x=50, y=140)
        self.act_fin = ttk.Entry(self.tab_gestion, width=35)
        self.act_fin.place(x=150, y=140)

        ttk.Label(self.tab_gestion, text="Medio Pago:").place(x=50, y=180)
        self.act_pago = ttk.Combobox(self.tab_gestion, values=["Efectivo", "Yape", "Plin", "Tarjeta"], width=32, state="readonly")
        self.act_pago.place(x=150, y=180)

        ttk.Button(self.tab_gestion, text="Actualizar Datos (Renovar)", command=self.actualizar_socio).place(x=170, y=250)

    def buscar_socio(self):
        nombre = self.buscar_nombre.get().strip()
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT fecha_inicio, fecha_fin, medio_pago FROM socios WHERE nombre = ?", (nombre,))
        datos = cursor.fetchone()
        conn.close()

        if datos:
            self.act_inicio.delete(0, tk.END)
            self.act_inicio.insert(0, datos[0])
            self.act_fin.delete(0, tk.END)
            self.act_fin.insert(0, datos[1])
            self.act_pago.set(datos[2])
            messagebox.showinfo("Encontrado", f"Datos de {nombre} cargados.")
        else:
            messagebox.showerror("No encontrado", f"El socio '{nombre}' no existe.")

    def actualizar_socio(self):
        nombre = self.buscar_nombre.get().strip()
        inicio = self.act_inicio.get()
        fin = self.act_fin.get()
        pago = self.act_pago.get()

        if not nombre or not inicio or not fin:
            messagebox.showwarning("Cuidado", "Busca a un socio primero para actualizarlo.")
            return

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute('''UPDATE socios SET fecha_inicio = ?, fecha_fin = ?, medio_pago = ? WHERE nombre = ?''', 
                       (inicio, fin, pago, nombre))
        if cursor.rowcount > 0:
            messagebox.showinfo("Éxito", f"Membresía de {nombre} actualizada.")
        else:
            messagebox.showerror("Error", "No se pudo actualizar.")
        conn.commit()
        conn.close()

    # --- PESTAÑA 3: CÁMARA (CONTROL DE ACCESO) ---
    def setup_tab_camara(self):
        ttk.Label(self.tab_camara, text="Control de Acceso Automático", font=("Arial", 14, "bold")).place(x=120, y=50)
        
        texto_info = (
            "Al iniciar la cámara:\n\n"
            "1. La interfaz se ocultará temporalmente.\n"
            "2. El sistema registrará la asistencia automáticamente.\n"
            "3. Cuadro Verde = Mensualidad al día.\n"
            "4. Cuadro Rojo = Mensualidad Vencida.\n\n"
            "Presiona la tecla 'Q' en la cámara para salir."
        )
        ttk.Label(self.tab_camara, text=texto_info, justify="left").place(x=90, y=100)
        
        ttk.Button(self.tab_camara, text="🔴 INICIAR CÁMARA", command=self.lanzar_camara, width=25).place(x=170, y=250)

    def lanzar_camara(self):
        # Ocultar la ventana de Tkinter mientras corre OpenCV
        self.root.withdraw()
        
        try:
            self.iniciar_reconocimiento_facial()
        except Exception as e:
            messagebox.showerror("Error de Cámara", str(e))
        finally:
            # Volver a mostrar la interfaz cuando se cierre la cámara
            self.root.deiconify()

    def iniciar_reconocimiento_facial(self):
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, encoding, fecha_fin FROM socios")
        filas = cursor.fetchall()
        conn.close()

        if not filas:
            raise Exception("No hay socios registrados. Registre al menos uno primero.")

        rostros_conocidos, ids_conocidos, nombres_conocidos, fechas_vencimiento = [], [], [], []
        for socio_id, nombre, encoding_bytes, fecha_fin in filas:
            rostros_conocidos.append(np.frombuffer(encoding_bytes, dtype=np.float64))
            ids_conocidos.append(socio_id)
            nombres_conocidos.append(nombre)
            fechas_vencimiento.append(fecha_fin)

        asistencias_hoy = set()
        hoy_str = datetime.now().strftime("%Y-%m-%d")

        video_capture = cv2.VideoCapture(0)
        process_this_frame = True

        while True:
            ret, frame = video_capture.read()
            if not ret: break

            if process_this_frame:
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                nombres_en_pantalla = []
                estados_en_pantalla = []

                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(rostros_conocidos, face_encoding, tolerance=0.48)
                    nombre = "Desconocido"
                    estado = ""

                    face_distances = face_recognition.face_distance(rostros_conocidos, face_encoding)
                    
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            socio_id = ids_conocidos[best_match_index]
                            nombre = nombres_conocidos[best_match_index]
                            fecha_fin_socio = fechas_vencimiento[best_match_index]
                            
                            if fecha_fin_socio >= hoy_str:
                                estado = "Activo"
                                if socio_id not in asistencias_hoy:
                                    conn = conectar_db()
                                    cursor = conn.cursor()
                                    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    cursor.execute("INSERT INTO asistencias (socio_id, fecha_hora) VALUES (?, ?)", (socio_id, ahora))
                                    conn.commit()
                                    conn.close()
                                    asistencias_hoy.add(socio_id)
                                    print(f"Asistencia registrada en DB: {nombre}")
                            else:
                                estado = "Vencido"

                    nombres_en_pantalla.append(nombre)
                    estados_en_pantalla.append(estado)

            process_this_frame = not process_this_frame

            for (top, right, bottom, left), nombre, estado in zip(face_locations, nombres_en_pantalla, estados_en_pantalla):
                top *= 4; right *= 4; bottom *= 4; left *= 4
                
                if nombre == "Desconocido":
                    color = (150, 150, 150)
                    texto = nombre
                elif estado == "Activo":
                    color = (0, 255, 0)
                    texto = f"{nombre} - OK"
                else:
                    color = (0, 0, 255)
                    texto = f"{nombre} - VENCIDO"

                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, texto, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)

            cv2.imshow('Control de Acceso Gym - (Presiona Q para salir)', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        video_capture.release()
        cv2.destroyAllWindows()

# Inicializar y arrancar la aplicación
if __name__ == "__main__":
    root = tk.Tk()
    app = GymApp(root)
    root.mainloop()
import face_recognition
import cv2
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ==========================================
# 1. BASE DE DATOS
# ==========================================
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
    conn.commit()
    conn.close()

# ==========================================
# 2. INTERFAZ GRÁFICA (Tkinter)
# ==========================================
class GymApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Gimnasio - Control de Acceso")
        self.root.geometry("550x450")
        self.root.resizable(False, False)

        inicializar_db()

        # Estilo de las pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, expand=True)

        # Crear los "Frames" (Pestañas)
        self.tab_registro = ttk.Frame(self.notebook, width=500, height=400)
        self.tab_gestion = ttk.Frame(self.notebook, width=500, height=400)
        self.tab_camara = ttk.Frame(self.notebook, width=500, height=400)

        self.tab_registro.pack(fill='both', expand=True)
        self.tab_gestion.pack(fill='both', expand=True)
        self.tab_camara.pack(fill='both', expand=True)

        self.notebook.add(self.tab_registro, text='Nuevo Socio')
        self.notebook.add(self.tab_gestion, text='Buscar / Renovar')
        self.notebook.add(self.tab_camara, text='Control de Acceso')

        self.setup_tab_registro()
        self.setup_tab_gestion()
        self.setup_tab_camara()

    # --- PESTAÑA 1: REGISTRO ---
    def setup_tab_registro(self):
        ttk.Label(self.tab_registro, text="Registrar Nuevo Socio", font=("Arial", 14, "bold")).place(x=150, y=20)

        # Nombre
        ttk.Label(self.tab_registro, text="Nombre:").place(x=50, y=80)
        self.reg_nombre = ttk.Entry(self.tab_registro, width=35)
        self.reg_nombre.place(x=150, y=80)

        # Foto
        ttk.Label(self.tab_registro, text="Foto:").place(x=50, y=120)
        self.reg_ruta_foto = ttk.Entry(self.tab_registro, width=25, state='readonly')
        self.reg_ruta_foto.place(x=150, y=120)
        ttk.Button(self.tab_registro, text="Buscar", command=self.seleccionar_foto).place(x=320, y=118)

        # Fechas por defecto (Hoy y en 30 días)
        hoy = datetime.now()
        mes_siguiente = hoy + timedelta(days=30)

        # Fecha Inicio
        ttk.Label(self.tab_registro, text="Fecha Inicio:").place(x=50, y=160)
        self.reg_inicio = ttk.Entry(self.tab_registro, width=35)
        self.reg_inicio.insert(0, hoy.strftime("%Y-%m-%d"))
        self.reg_inicio.place(x=150, y=160)

        # Fecha Fin
        ttk.Label(self.tab_registro, text="Fecha Vence:").place(x=50, y=200)
        self.reg_fin = ttk.Entry(self.tab_registro, width=35)
        self.reg_fin.insert(0, mes_siguiente.strftime("%Y-%m-%d"))
        self.reg_fin.place(x=150, y=200)

        # Medio de Pago
        ttk.Label(self.tab_registro, text="Medio Pago:").place(x=50, y=240)
        self.reg_pago = ttk.Combobox(self.tab_registro, values=["Efectivo", "Yape", "Plin", "Tarjeta"], width=32, state="readonly")
        self.reg_pago.set("Efectivo")
        self.reg_pago.place(x=150, y=240)

        # Botón Guardar
        ttk.Button(self.tab_registro, text="Guardar Socio", command=self.guardar_socio).place(x=200, y=300)

    def seleccionar_foto(self):
        ruta = filedialog.askopenfilename(title="Seleccionar foto", filetypes=[("Archivos de imagen", "*.jpg *.jpeg *.png")])
        if ruta:
            self.reg_ruta_foto.config(state='normal')
            self.reg_ruta_foto.delete(0, tk.END)
            self.reg_ruta_foto.insert(0, ruta)
            self.reg_ruta_foto.config(state='readonly')

    def guardar_socio(self):
        nombre = self.reg_nombre.get().strip()
        ruta = self.reg_ruta_foto.get()
        inicio = self.reg_inicio.get()
        fin = self.reg_fin.get()
        pago = self.reg_pago.get()

        if not nombre or not ruta:
            messagebox.showwarning("Faltan datos", "El nombre y la foto son obligatorios.")
            return

        try:
            imagen = face_recognition.load_image_file(ruta)
            encodings = face_recognition.face_encodings(imagen)
            
            if len(encodings) == 0:
                messagebox.showerror("Error", "No se detectó ninguna cara en la foto seleccionada.")
                return

            encoding_bytes = encodings[0].tobytes()
            
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO socios (nombre, encoding, fecha_inicio, fecha_fin, medio_pago)
                              VALUES (?, ?, ?, ?, ?)''', (nombre, encoding_bytes, inicio, fin, pago))
            conn.commit()
            conn.close()
            messagebox.showinfo("Éxito", f"Socio '{nombre}' registrado exitosamente.")
            self.reg_nombre.delete(0, tk.END)
            self.reg_ruta_foto.config(state='normal')
            self.reg_ruta_foto.delete(0, tk.END)
            self.reg_ruta_foto.config(state='readonly')
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Ya existe un socio con ese nombre.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un problema: {e}")

    # --- PESTAÑA 2: GESTIÓN Y RENOVACIÓN ---
    def setup_tab_gestion(self):
        ttk.Label(self.tab_gestion, text="Buscar Socio", font=("Arial", 12)).place(x=50, y=30)
        self.buscar_nombre = ttk.Entry(self.tab_gestion, width=25)
        self.buscar_nombre.place(x=160, y=30)
        ttk.Button(self.tab_gestion, text="Buscar", command=self.buscar_socio).place(x=330, y=28)

        # Separador
        ttk.Separator(self.tab_gestion, orient='horizontal').place(x=20, y=70, width=460)

        # Campos de actualización
        ttk.Label(self.tab_gestion, text="Fecha Inicio:").place(x=50, y=100)
        self.act_inicio = ttk.Entry(self.tab_gestion, width=35)
        self.act_inicio.place(x=150, y=100)

        ttk.Label(self.tab_gestion, text="Fecha Vence:").place(x=50, y=140)
        self.act_fin = ttk.Entry(self.tab_gestion, width=35)
        self.act_fin.place(x=150, y=140)

        ttk.Label(self.tab_gestion, text="Medio Pago:").place(x=50, y=180)
        self.act_pago = ttk.Combobox(self.tab_gestion, values=["Efectivo", "Yape", "Plin", "Tarjeta"], width=32, state="readonly")
        self.act_pago.place(x=150, y=180)

        ttk.Button(self.tab_gestion, text="Actualizar Datos (Renovar)", command=self.actualizar_socio).place(x=170, y=250)

    def buscar_socio(self):
        nombre = self.buscar_nombre.get().strip()
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT fecha_inicio, fecha_fin, medio_pago FROM socios WHERE nombre = ?", (nombre,))
        datos = cursor.fetchone()
        conn.close()

        if datos:
            self.act_inicio.delete(0, tk.END)
            self.act_inicio.insert(0, datos[0])
            self.act_fin.delete(0, tk.END)
            self.act_fin.insert(0, datos[1])
            self.act_pago.set(datos[2])
            messagebox.showinfo("Encontrado", f"Datos de {nombre} cargados.")
        else:
            messagebox.showerror("No encontrado", f"El socio '{nombre}' no existe.")

    def actualizar_socio(self):
        nombre = self.buscar_nombre.get().strip()
        inicio = self.act_inicio.get()
        fin = self.act_fin.get()
        pago = self.act_pago.get()

        if not nombre or not inicio or not fin:
            messagebox.showwarning("Cuidado", "Busca a un socio primero para actualizarlo.")
            return

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute('''UPDATE socios SET fecha_inicio = ?, fecha_fin = ?, medio_pago = ? WHERE nombre = ?''', 
                       (inicio, fin, pago, nombre))
        if cursor.rowcount > 0:
            messagebox.showinfo("Éxito", f"Membresía de {nombre} actualizada.")
        else:
            messagebox.showerror("Error", "No se pudo actualizar.")
        conn.commit()
        conn.close()

    # --- PESTAÑA 3: CÁMARA (CONTROL DE ACCESO) ---
    def setup_tab_camara(self):
        ttk.Label(self.tab_camara, text="Control de Acceso Automático", font=("Arial", 14, "bold")).place(x=120, y=50)
        
        texto_info = (
            "Al iniciar la cámara:\n\n"
            "1. La interfaz se ocultará temporalmente.\n"
            "2. El sistema registrará la asistencia automáticamente.\n"
            "3. Cuadro Verde = Mensualidad al día.\n"
            "4. Cuadro Rojo = Mensualidad Vencida.\n\n"
            "Presiona la tecla 'Q' en la cámara para salir."
        )
        ttk.Label(self.tab_camara, text=texto_info, justify="left").place(x=90, y=100)
        
        ttk.Button(self.tab_camara, text="🔴 INICIAR CÁMARA", command=self.lanzar_camara, width=25).place(x=170, y=250)

    def lanzar_camara(self):
        # Ocultar la ventana de Tkinter mientras corre OpenCV
        self.root.withdraw()
        
        try:
            self.iniciar_reconocimiento_facial()
        except Exception as e:
            messagebox.showerror("Error de Cámara", str(e))
        finally:
            # Volver a mostrar la interfaz cuando se cierre la cámara
            self.root.deiconify()

    def iniciar_reconocimiento_facial(self):
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, encoding, fecha_fin FROM socios")
        filas = cursor.fetchall()
        conn.close()

        if not filas:
            raise Exception("No hay socios registrados. Registre al menos uno primero.")

        rostros_conocidos, ids_conocidos, nombres_conocidos, fechas_vencimiento = [], [], [], []
        for socio_id, nombre, encoding_bytes, fecha_fin in filas:
            rostros_conocidos.append(np.frombuffer(encoding_bytes, dtype=np.float64))
            ids_conocidos.append(socio_id)
            nombres_conocidos.append(nombre)
            fechas_vencimiento.append(fecha_fin)

        asistencias_hoy = set()
        hoy_str = datetime.now().strftime("%Y-%m-%d")

        video_capture = cv2.VideoCapture(0)
        process_this_frame = True

        while True:
            ret, frame = video_capture.read()
            if not ret: break

            if process_this_frame:
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                nombres_en_pantalla = []
                estados_en_pantalla = []

                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(rostros_conocidos, face_encoding, tolerance=0.48)
                    nombre = "Desconocido"
                    estado = ""

                    face_distances = face_recognition.face_distance(rostros_conocidos, face_encoding)
                    
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            socio_id = ids_conocidos[best_match_index]
                            nombre = nombres_conocidos[best_match_index]
                            fecha_fin_socio = fechas_vencimiento[best_match_index]
                            
                            if fecha_fin_socio >= hoy_str:
                                estado = "Activo"
                                if socio_id not in asistencias_hoy:
                                    conn = conectar_db()
                                    cursor = conn.cursor()
                                    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    cursor.execute("INSERT INTO asistencias (socio_id, fecha_hora) VALUES (?, ?)", (socio_id, ahora))
                                    conn.commit()
                                    conn.close()
                                    asistencias_hoy.add(socio_id)
                                    print(f"Asistencia registrada en DB: {nombre}")
                            else:
                                estado = "Vencido"

                    nombres_en_pantalla.append(nombre)
                    estados_en_pantalla.append(estado)

            process_this_frame = not process_this_frame

            for (top, right, bottom, left), nombre, estado in zip(face_locations, nombres_en_pantalla, estados_en_pantalla):
                top *= 4; right *= 4; bottom *= 4; left *= 4
                
                if nombre == "Desconocido":
                    color = (150, 150, 150)
                    texto = nombre
                elif estado == "Activo":
                    color = (0, 255, 0)
                    texto = f"{nombre} - OK"
                else:
                    color = (0, 0, 255)
                    texto = f"{nombre} - VENCIDO"

                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, texto, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)

            cv2.imshow('Control de Acceso Gym - (Presiona Q para salir)', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        video_capture.release()
        cv2.destroyAllWindows()

# Inicializar y arrancar la aplicación
if __name__ == "__main__":
    root = tk.Tk()
    app = GymApp(root)
    root.mainloop()