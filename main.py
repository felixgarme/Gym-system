import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import ctypes
import os
import sys

# Tus módulos locales
import database
import camara
import vista_datos
import vista_gestion
import vista_registro
import vista_importar
import vista_stock  # <--- NUEVO MÓDULO IMPORTADO

def obtener_ruta_recurso(ruta_relativa):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, ruta_relativa)
    return os.path.join(os.path.abspath('.'), ruta_relativa)

class GymApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Gimnasio - Control de Acceso")

        ruta_icono = obtener_ruta_recurso('icono.ico')
        if os.path.exists(ruta_icono):
            self.root.iconbitmap(ruta_icono)

        try:
            self.root.state('zoomed')
        except Exception:
            self.root.attributes('-zoomed', True)

        self.root.minsize(800, 600)

        # Inicializar BD
        database.inicializar_db()

        # Notebook (Pestañas) modernas
        self.notebook = ttk.Notebook(self.root, bootstyle="dark")
        self.notebook.pack(pady=15, fill=BOTH, expand=True, padx=15)

        # Crear los contenedores de las pestañas
        self.tab_camara = ttk.Frame(self.notebook)
        self.tab_registro = ttk.Frame(self.notebook)
        self.tab_gestion = ttk.Frame(self.notebook)
        self.tab_datos = ttk.Frame(self.notebook)
        self.tab_stock = ttk.Frame(self.notebook) # <--- NUEVA PESTAÑA CREADA
        self.tab_importar = ttk.Frame(self.notebook)

        # --- ORDEN DE PESTAÑAS (Control de acceso sigue primero) ---
        self.notebook.add(self.tab_camara, text=' 📷  Control de Acceso ')
        self.notebook.add(self.tab_registro, text=' 👤  Nuevo Socio ')
        self.notebook.add(self.tab_gestion, text=' 🔍  Buscar / Renovar ')
        self.notebook.add(self.tab_datos, text=' 📋  Directorio ')
        self.notebook.add(self.tab_stock, text=' 🛒  Stock de Productos ') # <--- PESTAÑA AÑADIDA AL MENÚ
        self.notebook.add(self.tab_importar, text=' 📥  Importar DG Madrid ')
        # ----------------------------------------

        self.frame_reg = ttk.Frame(self.tab_registro)
        self.frame_reg.pack(expand=True, fill=BOTH, padx=20, pady=20)
        
        self.frame_cam = ttk.Frame(self.tab_camara)
        self.frame_cam.pack(expand=True, fill=BOTH)

        self.nombres_socios = []

        # Cargar las vistas externas (estas heredarán el diseño moderno automáticamente)
        vista_registro.setup_tab_registro(self.frame_reg, self)
        vista_gestion.setup_tab_gestion(self.tab_gestion, self)
        vista_importar.setup_tab_importar(self.tab_importar, self)
        vista_stock.setup_tab_stock(self.tab_stock, self)  # <--- CONFIGURACIÓN DE LA NUEVA PESTAÑA

        self.setup_tab_camara()
        self.actualizar_tabla_excel = vista_datos.setup_tab_datos(self.tab_datos)
        self.cargar_nombres_socios()

    def cargar_nombres_socios(self):
        socios = database.obtener_todos_los_socios()
        self.nombres_socios = [socio[1] for socio in socios]

    def setup_tab_camara(self):
        # Contenedor central
        card_container = ttk.Frame(self.frame_cam, padding=40)
        card_container.place(relx=0.5, rely=0.5, anchor=CENTER)

        ttk.Label(card_container, text="Control de Acceso Automático", font=("Segoe UI", 20, "bold")).pack(pady=(0, 25))

        frame_selector = ttk.Frame(card_container)
        frame_selector.pack(pady=10, fill=X)

        ttk.Label(frame_selector, text="📷 Seleccionar Cámara:", font=("Segoe UI", 11)).pack(side=LEFT, padx=(0, 10))

        lista_camaras = vista_registro.obtener_camaras()
        self.combo_camara_acceso = ttk.Combobox(frame_selector, values=lista_camaras, state="readonly", width=30, font=("Segoe UI", 10))
        if lista_camaras:
            self.combo_camara_acceso.set(lista_camaras[0])
        self.combo_camara_acceso.pack(side=LEFT)

        frame_info = ttk.Frame(card_container)
        frame_info.pack(pady=20, fill=X)

        texto_info = (
            "• La interfaz principal se ocultará temporalmente mientras el escáner esté activo.\n"
            "• El sistema registrará la asistencia automáticamente al reconocer al socio.\n"
            "• Cuadro Verde = Mensualidad al día (Acceso Permitido).\n"
            "• Cuadro Rojo = Mensualidad Vencida (Acceso Denegado).\n\n"
            "Presiona 'Q', 'ESC' o el botón 'X' de la ventana de la cámara para finalizar."
        )

        ttk.Label(frame_info, text=texto_info, justify=LEFT, bootstyle="secondary", font=("Segoe UI", 10)).pack()

        # Botón moderno con color de acento rojo (bootstyle danger)
        ttk.Button(card_container, text="🔴 INICIAR CÁMARA", command=self.lanzar_camara, bootstyle="danger", padding=15).pack(pady=(20, 0), fill=X)

    def lanzar_camara(self):
        seleccion = self.combo_camara_acceso.get()
        try:
            if ":" in seleccion:
                idx_camara = int(seleccion.split(":")[0])
            else:
                idx_camara = int(seleccion.split()[-1])
        except Exception:
            idx_camara = 0

        self.root.withdraw()
        try:
            camara.iniciar_reconocimiento(idx_camara)
        except Exception as e:
            messagebox.showerror("Error de Cámara", str(e))
        finally:
            self.root.deiconify()

def iniciar_con_pantalla_carga():
    # Inicializar ventana principal usando ttkbootstrap (Temas recomendados: darkly, superhero, cyborg)
    root = ttk.Window(themename="darkly") 
    root.withdraw()

    splash = tk.Toplevel(root)
    splash.overrideredirect(True)

    ancho_splash = 500
    alto_splash = 250
    pantalla_ancho = root.winfo_screenwidth()
    pantalla_alto = root.winfo_screenheight()
    x = (pantalla_ancho // 2) - (ancho_splash // 2)
    y = (pantalla_alto // 2) - (alto_splash // 2)
    splash.geometry(f"{ancho_splash}x{alto_splash}+{x}+{y}")

    splash.configure(bg="#1E1E1E")

    lbl_titulo = tk.Label(splash, text="SISTEMA DE GIMNASIO", font=("Segoe UI", 22, "bold"), bg="#1E1E1E", fg="#FFFFFF")
    lbl_titulo.pack(pady=(50, 10))

    lbl_estado = tk.Label(splash, text="Cargando base de datos e interfaz...", font=("Segoe UI", 10), bg="#1E1E1E", fg="#9CA3AF")
    lbl_estado.pack(pady=(0, 20))

    # Barra de progreso animada de ttkbootstrap
    progreso = ttk.Progressbar(splash, bootstyle="success-striped", orient=HORIZONTAL, length=350, mode="indeterminate")
    progreso.pack(pady=10)
    progreso.start(15)

    def cargar_app_principal():
        app = GymApp(root)
        splash.destroy()
        root.deiconify()

    root.after(2000, cargar_app_principal)
    root.mainloop()

if __name__ == "__main__":
    try:
        if os.name == 'nt':
            mi_app_id = 'mi_empresa.sistema_gimnasio.version1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(mi_app_id)
    except Exception:
        pass

    iniciar_con_pantalla_carga()