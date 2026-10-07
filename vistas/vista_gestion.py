import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
import os
import cv2
import time
import numpy as np
import sqlite3
import face_recognition
from PIL import Image, ImageTk
import database

imagenes_referencia = []


def abrir_camara(indice):
    """Abre una cámara por índice (usa DirectShow en Windows para mayor compatibilidad)."""
    if os.name == 'nt':
        return cv2.VideoCapture(indice, cv2.CAP_DSHOW)
    return cv2.VideoCapture(indice)


def detectar_camaras(max_indices=6):
    """Devuelve la lista de índices de cámaras que funcionan."""
    disponibles = []
    for i in range(max_indices):
        cap = abrir_camara(i)
        try:
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    disponibles.append(i)
        finally:
            cap.release()
    return disponibles


def setup_tab_gestion(parent_frame, app):
    app.socio_actual_cargado = ""
    app.ultima_revision_fotos = {}
    app.camara_indice = 0
    app.camaras_disponibles = [0]

    fuente_normal = tkfont.Font(family="Arial", size=10)
    fuente_negrita = tkfont.Font(family="Arial", size=10, weight="bold")
    fuente_lista = tkfont.Font(family="Arial", size=10)

    main_container = ttk.Frame(parent_frame)
    main_container.pack(fill='both', expand=True, padx=12, pady=12)

    frame_busqueda = ttk.Frame(main_container)
    frame_busqueda.pack(fill='x', pady=(0, 10))

    ttk.Label(frame_busqueda, text="Buscar Socio:", font=fuente_negrita).pack(side='left', padx=(0, 10))

    btn_buscar = ttk.Button(frame_busqueda, text="🔍 Buscar", command=lambda: ejecutar_busqueda_completa())
    btn_buscar.pack(side='right')

    entry_buscar = ttk.Entry(frame_busqueda, font=fuente_normal)
    entry_buscar.pack(side='left', fill='x', expand=True, padx=(0, 10))
    app.buscar_nombre = entry_buscar

    listbox_sugerencias = tk.Listbox(
        main_container, height=5, font=fuente_lista,
        selectmode=tk.BROWSE,
        exportselection=False,
        activestyle='none',
        cursor="hand2",
        highlightthickness=1,
        relief='solid', borderwidth=1
    )

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

    btn_actualizar = ttk.Button(frame_datos, text="💾 Actualizar / Renovar",
                                command=lambda: actualizar_socio(app, entry_buscar, act_inicio, act_fin, act_pago))
    btn_actualizar.grid(row=3, column=0, columnspan=2, pady=(16, 0), sticky='ew')

    frame_fotos_wrapper = ttk.LabelFrame(frame_contenido, text=" Fotografías del Socio ", padding=8)
    frame_fotos_wrapper.grid(row=0, column=1, sticky='nsew', padx=(8, 0))

    frame_acciones_fotos = ttk.Frame(frame_fotos_wrapper)
    frame_acciones_fotos.pack(fill='x', side='bottom')

    # ---------- Selector de cámara ----------
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

    btn_abrir_carpeta = ttk.Button(frame_botones_fotos, text="📂 Abrir Carpeta",
                                   command=lambda: abrir_carpeta_socio_actual(entry_buscar.get()))
    btn_abrir_carpeta.pack(side='left', fill='x', expand=True, padx=(0, 5))

    btn_tomar_foto = ttk.Button(frame_botones_fotos, text="📷 Tomar Foto",
                                command=lambda: capturar_foto_socio(app, entry_buscar.get()))
    btn_tomar_foto.pack(side='right', fill='x', expand=True, padx=(5, 0))

    frame_fotos = ttk.Frame(frame_fotos_wrapper)
    frame_fotos.pack(fill='both', expand=True, pady=(0, 8))
    frame_fotos.grid_propagate(False)

    lbl_estado_foto = ttk.Label(frame_fotos, text="Busca un socio para\nver sus fotografías.",
                                justify="center", foreground="gray", font=fuente_normal)
    lbl_estado_foto.grid(row=0, column=0, sticky="nsew")
    frame_fotos.rowconfigure(0, weight=1)
    frame_fotos.columnconfigure(0, weight=1)

    # ---------- Lógica del selector de cámara ----------
    def actualizar_combo_camaras():
        """Rellena el combobox con las cámaras detectadas y conserva la seleccionada."""
        etiquetas = [f"Cámara {i}" for i in app.camaras_disponibles]
        combo_camara.configure(values=etiquetas)
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

    # Detecta las cámaras una vez que la interfaz ya está dibujada
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

    def cargar_fotos(nombre_socio):
        global imagenes_referencia
        imagenes_referencia.clear()

        app.socio_actual_cargado = nombre_socio

        frame_fotos.unbind("<Configure>")
        for widget in frame_fotos.winfo_children():
            widget.destroy()

        cols_actuales, _ = frame_fotos.grid_size()
        for col in range(max(cols_actuales, 5)):
            frame_fotos.columnconfigure(col, weight=0, uniform="")

        ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre_socio)

        if not os.path.exists(ruta_carpeta):
            frame_fotos.columnconfigure(0, weight=1)
            ttk.Label(frame_fotos, text="No tiene carpeta de fotos.", foreground="red").grid(row=0, column=0, sticky="nsew")
            app.ultima_revision_fotos = {}
            return

        archivos = [f for f in os.listdir(ruta_carpeta) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        if not archivos:
            frame_fotos.columnconfigure(0, weight=1)
            ttk.Label(frame_fotos, text="Sin fotos registradas.", foreground="gray").grid(row=0, column=0, sticky="nsew")
            app.ultima_revision_fotos = {}
            return

        archivos.sort(key=lambda x: os.path.getmtime(os.path.join(ruta_carpeta, x)), reverse=True)
        archivos_mostrar = archivos[:3]

        app.ultima_revision_fotos = {f: os.path.getmtime(os.path.join(ruta_carpeta, f)) for f in archivos_mostrar}

        pil_images = []
        labels = []

        frame_fotos.rowconfigure(0, weight=1)

        for i in range(len(archivos_mostrar)):
            frame_fotos.columnconfigure(i, weight=1, uniform="col_foto")

            ruta_img = os.path.join(ruta_carpeta, archivos_mostrar[i])
            try:
                img_pil = Image.open(ruta_img)
                pil_images.append(img_pil)

                lbl_img = ttk.Label(frame_fotos, anchor="center")
                lbl_img.grid(row=0, column=i, sticky="nsew", padx=3, pady=3)
                labels.append(lbl_img)
            except Exception as e:
                print(f"Error abriendo imagen {archivos_mostrar[i]}: {e}")

        app.last_w = 0
        app.last_h = 0

        def redimensionar_fotos(event=None):
            if not pil_images:
                return

            w_frame = frame_fotos.winfo_width()
            h_frame = frame_fotos.winfo_height()

            if w_frame <= 10 or h_frame <= 10:
                return

            if hasattr(app, 'last_w') and hasattr(app, 'last_h'):
                if abs(w_frame - app.last_w) < 5 and abs(h_frame - app.last_h) < 5:
                    return

            app.last_w = w_frame
            app.last_h = h_frame

            num_fotos = len(pil_images)
            w_disponible = max(20, (w_frame // num_fotos) - 10)
            h_disponible = max(20, h_frame - 10)

            imagenes_referencia.clear()
            for img_pil, lbl in zip(pil_images, labels):
                img_copy = img_pil.copy()
                img_copy.thumbnail((w_disponible, h_disponible), Image.Resampling.LANCZOS)
                img_tk = ImageTk.PhotoImage(img_copy)
                imagenes_referencia.append(img_tk)
                lbl.config(image=img_tk)

        frame_fotos.bind("<Configure>", redimensionar_fotos)
        frame_fotos.after(100, redimensionar_fotos)

    def verificar_cambios_fotos():
        nombre = app.socio_actual_cargado
        if nombre:
            ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre)
            if os.path.exists(ruta_carpeta):
                archivos = [f for f in os.listdir(ruta_carpeta) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                archivos.sort(key=lambda x: os.path.getmtime(os.path.join(ruta_carpeta, x)), reverse=True)

                estado_actual = {f: os.path.getmtime(os.path.join(ruta_carpeta, f)) for f in archivos[:3]}

                if estado_actual != app.ultima_revision_fotos:
                    cargar_fotos(nombre)
                    reencodear_y_actualizar_socio(nombre)
            else:
                if app.ultima_revision_fotos != {}:
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
        """Coloca la lista justo debajo del Entry con su mismo ancho."""
        main_container.update_idletasks()
        x = entry_buscar.winfo_rootx() - main_container.winfo_rootx()
        y = entry_buscar.winfo_rooty() - main_container.winfo_rooty() + entry_buscar.winfo_height() + 2
        ancho = max(entry_buscar.winfo_width(), 120)
        listbox_sugerencias.place(x=x, y=y, width=ancho)
        listbox_sugerencias.lift()

    def filtrar_autocompletado(event):
        if event.keysym in ("Up", "Down", "Return", "KP_Enter", "Escape", "Tab",
                            "Shift_L", "Shift_R", "Control_L", "Control_R",
                            "Left", "Right", "Home", "End"):
            return
        texto = entry_buscar.get().strip().lower()
        listbox_sugerencias.delete(0, tk.END)
        if not texto:
            listbox_sugerencias.place_forget()
            return
        coincidencias = [n for n in app.nombres_socios if texto in n.lower()]
        if coincidencias:
            for nombre in coincidencias:
                listbox_sugerencias.insert(tk.END, nombre)
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
        """Flecha abajo en el Entry: pasa el foco a la lista y marca el primero."""
        if lista_visible():
            listbox_sugerencias.focus_set()
            _marcar(0)
            return "break"

    def entry_flecha_arriba(event):
        """Flecha arriba en el Entry: pasa a la lista marcando el último."""
        if lista_visible():
            listbox_sugerencias.focus_set()
            _marcar(listbox_sugerencias.size() - 1)
            return "break"

    def lista_flecha_abajo(event):
        total = listbox_sugerencias.size()
        sel = listbox_sugerencias.curselection()
        actual = sel[0] if sel else -1
        _marcar(min(actual + 1, total - 1))
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
        nombre_seleccionado = listbox_sugerencias.get(sel[0])
        entry_buscar.delete(0, tk.END)
        entry_buscar.insert(0, nombre_seleccionado)
        listbox_sugerencias.place_forget()
        entry_buscar.focus_set()
        entry_buscar.icursor(tk.END)
        ejecutar_busqueda_completa()
        return "break"

    def clic_en_lista(event):
        """El clic marca el elemento bajo el cursor y lo selecciona al soltar."""
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
        """Si se escribe estando en la lista, vuelve al Entry y continúa escribiendo."""
        if event.keysym == "BackSpace":
            entry_buscar.focus_set()
            texto = entry_buscar.get()
            entry_buscar.delete(0, tk.END)
            entry_buscar.insert(0, texto[:-1])
            entry_buscar.icursor(tk.END)
            filtrar_autocompletado(event)
            return "break"
        if event.char and event.char.isprintable() and len(event.char) == 1:
            entry_buscar.focus_set()
            entry_buscar.insert(tk.END, event.char)
            entry_buscar.icursor(tk.END)
            filtrar_autocompletado(event)
            return "break"

    def ocultar_si_clic_fuera(event):
        if not listbox_sugerencias.winfo_ismapped():
            return
        if event.widget in (listbox_sugerencias, entry_buscar):
            return
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
            messagebox.showerror(
                "Error de Cámara",
                f"No se pudo acceder a la cámara {indice_actual}.\n"
                "Prueba seleccionando otra cámara en la lista."
            )
            return

        messagebox.showinfo(
            "Tomar Foto",
            "Se abrirá la cámara.\n\n"
            "- Presiona ESPACIO para tomar la foto.\n"
            "- Presiona C para cambiar de cámara.\n"
            "- Presiona ESC para cancelar."
        )

        titulo_ventana = f"Tomar Foto - {nombre}"
        foto_guardada = False
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            display_frame = frame.copy()
            cv2.putText(display_frame, "ESPACIO: Tomar Foto | C: Cambiar camara | ESC: Salir", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
            cv2.putText(display_frame, f"Camara {indice_actual}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            cv2.imshow(titulo_ventana, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 32:
                timestamp = int(time.time())
                ruta_foto = os.path.join(ruta_carpeta, f"foto_{timestamp}.jpg")
                cv2.imwrite(ruta_foto, frame)
                foto_guardada = True
                break
            elif key == 27:
                break
            elif key in (ord('c'), ord('C')):
                # Cambiar a la siguiente cámara disponible
                lista = app.camaras_disponibles
                if len(lista) > 1:
                    pos = lista.index(indice_actual) if indice_actual in lista else -1
                    siguiente = lista[(pos + 1) % len(lista)]
                    nuevo_cap = abrir_camara(siguiente)
                    if nuevo_cap.isOpened():
                        cap.release()
                        cap = nuevo_cap
                        indice_actual = siguiente
                        app.camara_indice = siguiente
                        if siguiente in lista:
                            combo_camara.current(lista.index(siguiente))
                    else:
                        nuevo_cap.release()

        cap.release()
        cv2.destroyAllWindows()

        if foto_guardada:
            reencodear_y_actualizar_socio(nombre)
            cargar_fotos(nombre)
            messagebox.showinfo("Éxito", f"Nueva foto agregada y perfil facial actualizado para '{nombre}'.")

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


def reencodear_y_actualizar_socio(nombre):
    ruta_carpeta = os.path.join(database.CARPETA_PRINCIPAL, nombre)
    if not os.path.exists(ruta_carpeta):
        return

    encodings_lista = []
    archivos = [f for f in os.listdir(ruta_carpeta) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    for archivo in archivos:
        ruta_img = os.path.join(ruta_carpeta, archivo)
        try:
            imagen = face_recognition.load_image_file(ruta_img)
            encs = face_recognition.face_encodings(imagen)
            if len(encs) > 0:
                encodings_lista.append(encs[0])
        except Exception as e:
            print(f"Error procesando {archivo}: {e}")

    conn = sqlite3.connect(database.DB_NAME)
    cursor = conn.cursor()

    if encodings_lista:
        encoding_promedio = np.mean(encodings_lista, axis=0)
        encoding_bytes = encoding_promedio.tobytes()
        cursor.execute("UPDATE socios SET encoding = ? WHERE nombre = ?", (encoding_bytes, nombre))
    else:
        cursor.execute("UPDATE socios SET encoding = NULL WHERE nombre = ?", (nombre,))

    conn.commit()
    conn.close()


def actualizar_socio(app, entry_buscar, entry_inicio, entry_fin, combo_pago):
    nombre = entry_buscar.get().strip()
    inicio = entry_inicio.get()
    fin = entry_fin.get()
    pago = combo_pago.get()

    if not nombre or not inicio or not fin:
        messagebox.showwarning("Cuidado", "Busca a un socio primero.")
        return

    exito = database.actualizar_socio(nombre, inicio, fin, pago)

    if exito:
        messagebox.showinfo("Éxito", f"Membresía de {nombre} actualizada.")
        if hasattr(app, 'actualizar_tabla_excel'):
            app.actualizar_tabla_excel()
    else:
        messagebox.showerror("Error", "No se pudo actualizar.")