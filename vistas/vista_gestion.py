import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
import os
import cv2
import time
import threading
import numpy as np
import face_recognition
from PIL import Image, ImageTk
import database

imagenes_referencia = []
EXTENSIONES = ('.png', '.jpg', '.jpeg')

def abrir_camara(indice):
    """Abre una cámara por índice (DirectShow en Windows) con buffer mínimo."""
    cap = cv2.VideoCapture(indice, cv2.CAP_DSHOW) if os.name == 'nt' else cv2.VideoCapture(indice)
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass
    return cap

def detectar_camaras(max_indices=6):
    """Devuelve la lista de índices de cámaras que funcionan."""
    disponibles = []
    for i in range(max_indices):
        cap = abrir_camara(i)
        try:
            if cap.isOpened() and cap.read()[0]:
                disponibles.append(i)
        finally:
            cap.release()
    return disponibles

def listar_imagenes(ruta):
    """Imágenes de una carpeta ordenadas de la más reciente a la más antigua."""
    archivos = [f for f in os.listdir(ruta) if f.lower().endswith(EXTENSIONES)]
    archivos.sort(key=lambda x: os.path.getmtime(os.path.join(ruta, x)), reverse=True)
    return archivos

def dibujar_guia(frame, estado):
    """Dibuja textos, círculo rojo guía y botón X sobre el frame de vista previa."""
    h, w = frame.shape[:2]
    if estado["guia"]:
        centro = (w // 2, h // 2)
        radio = int(min(w, h) * 0.40)
        cv2.circle(frame, centro, radio, (0, 0, 255), 4)
        cv2.putText(frame, "Coloca tu cara dentro del circulo", (centro[0] - 170, centro[1] + radio + 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        x1, y1, x2, y2 = w - 42, 10, w - 10, 42
        estado["boton_x"] = (x1, y1, x2, y2)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), -1)
        cv2.line(frame, (x1 + 8, y1 + 8), (x2 - 8, y2 - 8), (255, 255, 255), 2)
        cv2.line(frame, (x1 + 8, y2 - 8), (x2 - 8, y1 + 8), (255, 255, 255), 2)
    else:
        estado["boton_x"] = None
    return frame

def reencodear_y_actualizar_socio(nombre):
    """Recalcula el perfil facial promedio del socio (solo reduce la copia usada para el reconocimiento)."""
    ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre)
    if not os.path.exists(ruta_carpeta):
        return

    encodings_lista = []
    for archivo in listar_imagenes(ruta_carpeta):
        try:
            img = cv2.imread(os.path.join(ruta_carpeta, archivo))
            if img is None:
                continue
            h, w = img.shape[:2]
            escala = 800 / max(h, w)
            if escala < 1:
                img = cv2.resize(img, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
            encs = face_recognition.face_encodings(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            if encs:
                encodings_lista.append(encs[0])
        except Exception as e:
            print(f"Error procesando {archivo}: {e}")

    conn = database.conectar_db()
    try:
        valor = np.mean(encodings_lista, axis=0).tobytes() if encodings_lista else None
        conn.execute("UPDATE socios SET encoding = ? WHERE nombre = ?", (valor, nombre))
        conn.commit()
    finally:
        conn.close()

def reencodear_async(widget, nombre, al_terminar=None):
    """Ejecuta el re-encoding en un hilo para no congelar la interfaz."""
    hecho = threading.Event()

    def tarea():
        try:
            reencodear_y_actualizar_socio(nombre)
        except Exception as e:
            print(f"Error re-encodeando {nombre}: {e}")
        finally:
            hecho.set()

    def sondear():
        if hecho.is_set():
            if al_terminar:
                al_terminar()
        else:
            widget.after(150, sondear)

    threading.Thread(target=tarea, daemon=True).start()
    sondear()

def setup_tab_gestion(parent_frame, app):
    app.socio_actual_cargado = ""
    app.ultima_revision_fotos = {}
    app.camara_indice = 0
    app.camaras_disponibles = [0]
    app.reencodeando = False

    fuente_normal = tkfont.Font(family="Arial", size=10)
    fuente_negrita = tkfont.Font(family="Arial", size=10, weight="bold")
    fuente_lista = tkfont.Font(family="Arial", size=10)

    main_container = ttk.Frame(parent_frame)
    main_container.pack(fill='both', expand=True, padx=12, pady=12)

    frame_busqueda = ttk.Frame(main_container)
    frame_busqueda.pack(fill='x', pady=(0, 10))
    ttk.Label(frame_busqueda, text="Buscar Socio:", font=fuente_negrita).pack(side='left', padx=(0, 10))
    ttk.Button(frame_busqueda, text="🔍 Buscar",
               command=lambda: ejecutar_busqueda_completa()).pack(side='right')

    entry_buscar = ttk.Entry(frame_busqueda, font=fuente_normal)
    entry_buscar.pack(side='left', fill='x', expand=True, padx=(0, 10))
    app.buscar_nombre = entry_buscar

    listbox_sugerencias = tk.Listbox(
        main_container, height=5, font=fuente_lista, selectmode=tk.BROWSE,
        exportselection=False, activestyle='none', cursor="hand2",
        highlightthickness=1, relief='solid', borderwidth=1)

    ttk.Separator(main_container, orient='horizontal').pack(fill='x', pady=5)

    frame_contenido = ttk.Frame(main_container)
    frame_contenido.pack(fill='both', expand=True, pady=5)
    frame_contenido.columnconfigure(0, weight=2, uniform="col_principal", minsize=220)
    frame_contenido.columnconfigure(1, weight=3, uniform="col_principal", minsize=280)
    frame_contenido.rowconfigure(0, weight=1)

    frame_datos = ttk.LabelFrame(frame_contenido, text=" Datos de Membresía ", padding=12)
    frame_datos.grid(row=0, column=0, sticky='nsew', padx=(0, 8))

    ttk.Label(frame_datos, text="Fecha Inicio:", font=fuente_normal).grid(row=0, column=0, sticky='w', pady=8)
    act_inicio = ttk.Entry(frame_datos, font=fuente_normal)
    act_inicio.grid(row=0, column=1, sticky='ew', pady=8, padx=(5, 0))

    ttk.Label(frame_datos, text="Fecha Vence:", font=fuente_normal).grid(row=1, column=0, sticky='w', pady=8)
    act_fin = ttk.Entry(frame_datos, font=fuente_normal)
    act_fin.grid(row=1, column=1, sticky='ew', pady=8, padx=(5, 0))

    ttk.Label(frame_datos, text="Medio Pago:", font=fuente_normal).grid(row=2, column=0, sticky='w', pady=8)
    act_pago = ttk.Combobox(frame_datos, values=["Efectivo", "Yape", "Plin", "Tarjeta"],
                            state="readonly", font=fuente_normal)
    act_pago.grid(row=2, column=1, sticky='ew', pady=8, padx=(5, 0))

    frame_datos.columnconfigure(1, weight=1)
    frame_datos.rowconfigure(4, weight=1)

    ttk.Button(frame_datos, text="💾 Actualizar / Renovar",
               command=lambda: actualizar_socio(app, entry_buscar, act_inicio, act_fin, act_pago)
               ).grid(row=3, column=0, columnspan=2, pady=(16, 0), sticky='ew')

    frame_fotos_wrapper = ttk.LabelFrame(frame_contenido, text=" Fotografías del Socio ", padding=8)
    frame_fotos_wrapper.grid(row=0, column=1, sticky='nsew', padx=(8, 0))

    frame_acciones_fotos = ttk.Frame(frame_fotos_wrapper)
    frame_acciones_fotos.pack(fill='x', side='bottom')

    frame_camara = ttk.Frame(frame_acciones_fotos)
    frame_camara.pack(fill='x', pady=(0, 6))
    ttk.Label(frame_camara, text="Cámara:", font=fuente_normal).pack(side='left', padx=(0, 5))

    combo_camara = ttk.Combobox(frame_camara, values=["Cámara 0"], state="readonly", font=fuente_normal)
    combo_camara.current(0)
    combo_camara.pack(side='left', fill='x', expand=True, padx=(0, 5))

    btn_refrescar_camaras = ttk.Button(frame_camara, text="🔄", width=3,
                                       command=lambda: refrescar_camaras())
    btn_refrescar_camaras.pack(side='right')

    frame_botones_fotos = ttk.Frame(frame_acciones_fotos)
    frame_botones_fotos.pack(fill='x')
    ttk.Button(frame_botones_fotos, text="📂 Abrir Carpeta",
               command=lambda: abrir_carpeta_socio_actual(entry_buscar.get())
               ).pack(side='left', fill='x', expand=True, padx=(0, 5))
    ttk.Button(frame_botones_fotos, text="📷 Tomar Foto",
               command=lambda: capturar_foto_socio(app, entry_buscar.get())
               ).pack(side='right', fill='x', expand=True, padx=(5, 0))

    frame_fotos = ttk.Frame(frame_fotos_wrapper)
    frame_fotos.pack(fill='both', expand=True, pady=(0, 8))
    frame_fotos.grid_propagate(False)
    ttk.Label(frame_fotos, text="Busca un socio para\nver sus fotografías.",
              justify="center", foreground="gray", font=fuente_normal).grid(row=0, column=0, sticky="nsew")
    frame_fotos.rowconfigure(0, weight=1)
    frame_fotos.columnconfigure(0, weight=1)

    def actualizar_combo_camaras():
        combo_camara.configure(values=[f"Cámara {i}" for i in app.camaras_disponibles])
        if app.camara_indice in app.camaras_disponibles:
            combo_camara.current(app.camaras_disponibles.index(app.camara_indice))
        else:
            app.camara_indice = app.camaras_disponibles[0]
            combo_camara.current(0)

    def refrescar_camaras():
        btn_refrescar_camaras.configure(state='disabled')
        combo_camara.configure(state='disabled')
        main_container.update_idletasks()
        try:
            encontradas = detectar_camaras()
        finally:
            btn_refrescar_camaras.configure(state='normal')
            combo_camara.configure(state='readonly')

        if not encontradas:
            messagebox.showwarning("Cámaras", "No se detectó ninguna cámara conectada.")
            encontradas = [0]
        app.camaras_disponibles = encontradas
        actualizar_combo_camaras()

    def al_cambiar_camara(event=None):
        pos = combo_camara.current()
        if 0 <= pos < len(app.camaras_disponibles):
            app.camara_indice = app.camaras_disponibles[pos]

    combo_camara.bind("<<ComboboxSelected>>", al_cambiar_camara)
    main_container.after(300, refrescar_camaras)

    def ajustar_tamanos(event=None):
        ancho = main_container.winfo_width()
        if ancho <= 1:
            return
        tam = max(9, min(14, ancho // 85))
        if fuente_normal.cget("size") != tam:
            fuente_normal.configure(size=tam)
            fuente_negrita.configure(size=tam)
            fuente_lista.configure(size=max(9, tam - 1))
        if listbox_sugerencias.winfo_ismapped():
            posicionar_lista()

    main_container.bind("<Configure>", ajustar_tamanos)

    def mostrar_mensaje_frame(texto, color):
        frame_fotos.columnconfigure(0, weight=1)
        ttk.Label(frame_fotos, text=texto, foreground=color).grid(row=0, column=0, sticky="nsew")
        app.ultima_revision_fotos = {}

    def cargar_fotos(nombre_socio):
        imagenes_referencia.clear()
        app.socio_actual_cargado = nombre_socio

        frame_fotos.unbind("<Configure>")
        for widget in frame_fotos.winfo_children():
            widget.destroy()
        for col in range(max(frame_fotos.grid_size()[0], 5)):
            frame_fotos.columnconfigure(col, weight=0, uniform="")

        ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre_socio)
        if not os.path.exists(ruta_carpeta):
            return mostrar_mensaje_frame("No tiene carpeta de fotos.", "red")

        archivos_mostrar = listar_imagenes(ruta_carpeta)[:3]
        if not archivos_mostrar:
            return mostrar_mensaje_frame("Sin fotos registradas.", "gray")

        app.ultima_revision_fotos = {f: os.path.getmtime(os.path.join(ruta_carpeta, f))
                                     for f in archivos_mostrar}

        pil_images, labels = [], []
        frame_fotos.rowconfigure(0, weight=1)

        for i, archivo in enumerate(archivos_mostrar):
            frame_fotos.columnconfigure(i, weight=1, uniform="col_foto")
            try:
                img_pil = Image.open(os.path.join(ruta_carpeta, archivo))
                img_pil.draft("RGB", (800, 800))
                img_pil.load()
                pil_images.append(img_pil)
                lbl = ttk.Label(frame_fotos, anchor="center")
                lbl.grid(row=0, column=i, sticky="nsew", padx=3, pady=3)
                labels.append(lbl)
            except Exception as e:
                print(f"Error abriendo imagen {archivo}: {e}")

        app.last_w = app.last_h = 0

        def redimensionar_fotos(event=None):
            if not pil_images:
                return
            w_frame, h_frame = frame_fotos.winfo_width(), frame_fotos.winfo_height()
            if w_frame <= 10 or h_frame <= 10:
                return
            if abs(w_frame - app.last_w) < 5 and abs(h_frame - app.last_h) < 5:
                return
            app.last_w, app.last_h = w_frame, h_frame

            w_disp = max(20, (w_frame // len(pil_images)) - 10)
            h_disp = max(20, h_frame - 10)

            imagenes_referencia.clear()
            for img_pil, lbl in zip(pil_images, labels):
                img_copy = img_pil.copy()
                img_copy.thumbnail((w_disp, h_disp), Image.Resampling.LANCZOS)
                img_tk = ImageTk.PhotoImage(img_copy)
                imagenes_referencia.append(img_tk)
                lbl.config(image=img_tk)

        frame_fotos.bind("<Configure>", redimensionar_fotos)
        frame_fotos.after(100, redimensionar_fotos)

    def reencodear_seguro(nombre, al_terminar=None):
        """Re-encodea en segundo plano evitando ejecuciones simultáneas."""
        if app.reencodeando:
            return
        app.reencodeando = True

        def fin():
            app.reencodeando = False
            if al_terminar:
                al_terminar()

        reencodear_async(main_container, nombre, fin)

    def verificar_cambios_fotos():
        nombre = app.socio_actual_cargado
        if nombre:
            ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre)
            if os.path.exists(ruta_carpeta):
                estado_actual = {f: os.path.getmtime(os.path.join(ruta_carpeta, f))
                                 for f in listar_imagenes(ruta_carpeta)[:3]}
                if estado_actual != app.ultima_revision_fotos and not app.reencodeando:
                    cargar_fotos(nombre)
                    reencodear_seguro(nombre)
            elif app.ultima_revision_fotos != {}:
                cargar_fotos(nombre)

        main_container.after(2000, verificar_cambios_fotos)

    verificar_cambios_fotos()

    def ejecutar_busqueda_completa(event=None):
        nombre = entry_buscar.get().strip()
        listbox_sugerencias.place_forget()
        if not nombre:
            return

        datos = database.obtener_socio(nombre)
        if datos:
            act_inicio.delete(0, tk.END)
            act_inicio.insert(0, datos[0])
            act_fin.delete(0, tk.END)
            act_fin.insert(0, datos[1])
            act_pago.set(datos[2])
            cargar_fotos(nombre)
        else:
            messagebox.showerror("No encontrado", f"El socio '{nombre}' no existe.")

    def posicionar_lista():
        main_container.update_idletasks()
        x = entry_buscar.winfo_rootx() - main_container.winfo_rootx()
        y = entry_buscar.winfo_rooty() - main_container.winfo_rooty() + entry_buscar.winfo_height() + 2
        listbox_sugerencias.place(x=x, y=y, width=max(entry_buscar.winfo_width(), 120))
        listbox_sugerencias.lift()

    def filtrar_autocompletado(event):
        if event.keysym in ("Up", "Down", "Return", "KP_Enter", "Escape", "Tab", "Shift_L", "Shift_R",
                            "Control_L", "Control_R", "Left", "Right", "Home", "End"):
            return

        texto = entry_buscar.get().strip().lower()
        listbox_sugerencias.delete(0, tk.END)
        if not texto:
            listbox_sugerencias.place_forget()
            return

        try:
            nombres = [s[1] for s in database.obtener_todos_los_socios() if s[1]]
        except Exception as e:
            print(f"Error al obtener socios para autocompletado: {e}")
            nombres = []

        coincidencias = [n for n in nombres if texto in n.lower()]
        if coincidencias:
            for n in coincidencias:
                listbox_sugerencias.insert(tk.END, n)
            listbox_sugerencias.configure(height=min(len(coincidencias), 6))
            posicionar_lista()
        else:
            listbox_sugerencias.place_forget()

    def lista_visible():
        return listbox_sugerencias.winfo_ismapped() and listbox_sugerencias.size() > 0

    def _marcar(indice):
        listbox_sugerencias.selection_clear(0, tk.END)
        listbox_sugerencias.selection_set(indice)
        listbox_sugerencias.activate(indice)
        listbox_sugerencias.see(indice)

    def entry_flecha_abajo(event):
        if lista_visible():
            listbox_sugerencias.focus_set()
            _marcar(0)
            return "break"

    def entry_flecha_arriba(event):
        if lista_visible():
            listbox_sugerencias.focus_set()
            _marcar(listbox_sugerencias.size() - 1)
            return "break"

    def lista_flecha_abajo(event):
        sel = listbox_sugerencias.curselection()
        _marcar(min((sel[0] if sel else -1) + 1, listbox_sugerencias.size() - 1))
        return "break"

    def lista_flecha_arriba(event):
        sel = listbox_sugerencias.curselection()
        actual = sel[0] if sel else 0
        if actual <= 0:
            entry_buscar.focus_set()
            entry_buscar.icursor(tk.END)
        else:
            _marcar(actual - 1)
        return "break"

    def seleccionar_sugerencia(event=None):
        sel = listbox_sugerencias.curselection()
        if not sel:
            return "break"
        entry_buscar.delete(0, tk.END)
        entry_buscar.insert(0, listbox_sugerencias.get(sel[0]))
        listbox_sugerencias.place_forget()
        entry_buscar.focus_set()
        entry_buscar.icursor(tk.END)
        ejecutar_busqueda_completa()
        return "break"

    def clic_en_lista(event):
        indice = listbox_sugerencias.nearest(event.y)
        if indice >= 0:
            _marcar(indice)
            seleccionar_sugerencia()
        return "break"

    def ocultar_lista(event=None):
        listbox_sugerencias.place_forget()
        entry_buscar.focus_set()
        return "break"

    def escribir_desde_lista(event):
        if event.keysym == "BackSpace":
            entry_buscar.focus_set()
            texto = entry_buscar.get()
            entry_buscar.delete(0, tk.END)
            entry_buscar.insert(0, texto[:-1])
            entry_buscar.icursor(tk.END)
            filtrar_autocompletado(event)
            return "break"
        if event.char and len(event.char) == 1 and event.char.isprintable():
            entry_buscar.focus_set()
            entry_buscar.insert(tk.END, event.char)
            entry_buscar.icursor(tk.END)
            filtrar_autocompletado(event)
            return "break"

    def ocultar_si_clic_fuera(event):
        if listbox_sugerencias.winfo_ismapped() and event.widget not in (listbox_sugerencias, entry_buscar):
            listbox_sugerencias.place_forget()

    def abrir_carpeta_socio_actual(nombre):
        nombre = nombre.strip()
        if not nombre:
            messagebox.showwarning("Atención", "Escribe o busca un socio primero.")
            return
        database.abrir_carpeta_socio(nombre)

    def capturar_foto_socio(app, nombre):
        nombre = nombre.strip()
        if not nombre:
            messagebox.showwarning("Atención", "Busca o selecciona un socio primero.")
            return

        ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre)
        os.makedirs(ruta_carpeta, exist_ok=True)

        indice_actual = app.camara_indice
        cap = abrir_camara(indice_actual)
        if not cap.isOpened():
            cap.release()
            messagebox.showerror("Error de Cámara",
                                 f"No se pudo acceder a la cámara {indice_actual}.\n"
                                 "Prueba seleccionando otra cámara en la lista.")
            return

        messagebox.showinfo("Tomar Foto",
                            "Se abrirá la cámara.\n\n"
                            "- ESPACIO: tomar la foto\n"
                            "- X (o clic en la X roja): cerrar el círculo guía\n"
                            "- G: mostrar el círculo guía\n"
                            "- C: cambiar de cámara\n"
                            "- ESC: cancelar")

        titulo = f"Tomar Foto - {nombre}"
        estado = {"guia": True, "boton_x": None}

        def clic_raton(evento, x, y, flags, param):
            if evento == cv2.EVENT_LBUTTONDOWN and param["boton_x"]:
                x1, y1, x2, y2 = param["boton_x"]
                if x1 <= x <= x2 and y1 <= y <= y2:
                    param["guia"] = False

        cv2.namedWindow(titulo, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(titulo, clic_raton, estado)

        foto_guardada = False
        fallos = 0
        try:
            for _ in range(5):
                cap.read()

            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    fallos += 1
                    if fallos > 30:
                        break
                    cv2.waitKey(30)
                    continue
                fallos = 0

                h, w = frame.shape[:2]
                escala = min(1.0, 960 / w)
                if escala < 1.0:
                    vista = cv2.resize(frame, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
                else:
                    vista = frame.copy()

                dibujar_guia(vista, estado)
                cv2.putText(vista, "ESPACIO: Foto | X: Ocultar guia | G: Guia | C: Camara | ESC: Salir",
                            (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(vista, f"Camara {indice_actual}", (10, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                cv2.imshow(titulo, vista)

                key = cv2.waitKey(10) & 0xFF

                if cv2.getWindowProperty(titulo, cv2.WND_PROP_VISIBLE) < 1:
                    break

                if key == 32:
                    ruta_foto = os.path.join(ruta_carpeta, f"foto_{int(time.time())}.jpg")
                    foto_guardada = bool(cv2.imwrite(ruta_foto, frame))
                    break
                elif key == 27:
                    break
                elif key in (ord('x'), ord('X')):
                    estado["guia"] = False
                elif key in (ord('g'), ord('G')):
                    estado["guia"] = True
                elif key in (ord('c'), ord('C')):
                    lista = app.camaras_disponibles
                    if len(lista) > 1:
                        pos = lista.index(indice_actual) if indice_actual in lista else -1
                        siguiente = lista[(pos + 1) % len(lista)]
                        nuevo_cap = abrir_camara(siguiente)
                        if nuevo_cap.isOpened():
                            cap.release()
                            cap = nuevo_cap
                            indice_actual = app.camara_indice = siguiente
                            combo_camara.current(lista.index(siguiente))
                        else:
                            nuevo_cap.release()
        finally:
            cap.release()
            try:
                cv2.destroyWindow(titulo)
            except cv2.error:
                pass
            for _ in range(4):
                cv2.waitKey(1)

        if foto_guardada:
            cargar_fotos(nombre)
            app.reencodeando = False
            reencodear_seguro(nombre, lambda: messagebox.showinfo(
                "Éxito", f"Nueva foto agregada y perfil facial actualizado para '{nombre}'."))
        elif not ret_ok(fallos):
            messagebox.showerror("Error de Cámara", "La cámara dejó de responder.")

    def ret_ok(fallos):
        return fallos <= 30

    entry_buscar.bind('<KeyRelease>', filtrar_autocompletado)
    entry_buscar.bind('<Down>', entry_flecha_abajo)
    entry_buscar.bind('<Up>', entry_flecha_arriba)
    entry_buscar.bind('<Return>', ejecutar_busqueda_completa)
    entry_buscar.bind('<KP_Enter>', ejecutar_busqueda_completa)
    entry_buscar.bind('<Escape>', ocultar_lista)

    listbox_sugerencias.bind('<Down>', lista_flecha_abajo)
    listbox_sugerencias.bind('<Up>', lista_flecha_arriba)
    listbox_sugerencias.bind('<Return>', seleccionar_sugerencia)
    listbox_sugerencias.bind('<KP_Enter>', seleccionar_sugerencia)
    listbox_sugerencias.bind('<Escape>', ocultar_lista)
    listbox_sugerencias.bind('<ButtonRelease-1>', clic_en_lista)
    listbox_sugerencias.bind('<Key>', escribir_desde_lista, add='+')

    parent_frame.winfo_toplevel().bind('<Button-1>', ocultar_si_clic_fuera, add='+')

def actualizar_socio(app, entry_buscar, entry_inicio, entry_fin, combo_pago):
    nombre = entry_buscar.get().strip()
    inicio, fin, pago = entry_inicio.get(), entry_fin.get(), combo_pago.get()

    if not nombre or not inicio or not fin:
        messagebox.showwarning("Cuidado", "Busca a un socio primero.")
        return

    if database.actualizar_socio(nombre, inicio, fin, pago):
        messagebox.showinfo("Éxito", f"Membresía de {nombre} actualizada.")
        if hasattr(app, 'actualizar_tabla_excel'):
            app.actualizar_tabla_excel()
    else:
        messagebox.showerror("Error", "No se pudo actualizar.")
