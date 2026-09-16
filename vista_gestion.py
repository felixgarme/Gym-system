import tkinter as tk
from tkinter import ttk, messagebox
import os
import cv2
import time
import numpy as np
import sqlite3
import face_recognition
from PIL import Image, ImageTk
import database

imagenes_referencia = []

def setup_tab_gestion(parent_frame, app):
    app.socio_actual_cargado = ""
    app.ultima_revision_fotos = {}

    main_container = ttk.Frame(parent_frame)
    main_container.pack(fill='both', expand=True, padx=15, pady=15)

    frame_busqueda = ttk.Frame(main_container)
    frame_busqueda.pack(fill='x', pady=(0, 10))

    ttk.Label(frame_busqueda, text="Buscar Socio:", font=("Arial", 10, "bold")).pack(side='left', padx=(0, 10))

    entry_buscar = ttk.Entry(frame_busqueda, font=("Arial", 10))
    entry_buscar.pack(side='left', fill='x', expand=True, padx=(0, 10))
    app.buscar_nombre = entry_buscar

    btn_buscar = ttk.Button(frame_busqueda, text="🔍 Buscar", command=lambda: ejecutar_busqueda_completa())
    btn_buscar.pack(side='right')

    listbox_sugerencias = tk.Listbox(main_container, height=5, font=("Arial", 9), selectmode=tk.SINGLE, cursor="hand2")

    ttk.Separator(main_container, orient='horizontal').pack(fill='x', pady=5)

    frame_contenido = ttk.Frame(main_container)
    frame_contenido.pack(fill='both', expand=True, pady=5)

    # LAYOUT RÍGIDO (Proporción 40% datos - 60% fotos)
    frame_contenido.columnconfigure(0, weight=2, uniform="col_principal")
    frame_contenido.columnconfigure(1, weight=3, uniform="col_principal")
    frame_contenido.rowconfigure(0, weight=1)

    frame_datos = ttk.LabelFrame(frame_contenido, text=" Datos de Membresía ", padding=15)
    frame_datos.grid(row=0, column=0, sticky='nsew', padx=(0, 10))

    ttk.Label(frame_datos, text="Fecha Inicio:").grid(row=0, column=0, sticky='w', pady=10)
    act_inicio = ttk.Entry(frame_datos)
    act_inicio.grid(row=0, column=1, sticky='ew', pady=10, padx=(5, 0))

    ttk.Label(frame_datos, text="Fecha Vence:").grid(row=1, column=0, sticky='w', pady=10)
    act_fin = ttk.Entry(frame_datos)
    act_fin.grid(row=1, column=1, sticky='ew', pady=10, padx=(5, 0))

    ttk.Label(frame_datos, text="Medio Pago:").grid(row=2, column=0, sticky='w', pady=10)
    act_pago = ttk.Combobox(frame_datos, values=["Efectivo", "Yape", "Plin", "Tarjeta"], state="readonly")
    act_pago.grid(row=2, column=1, sticky='ew', pady=10, padx=(5, 0))

    frame_datos.columnconfigure(1, weight=1)

    btn_actualizar = ttk.Button(frame_datos, text="💾 Actualizar / Renovar",
                                command=lambda: actualizar_socio(app, entry_buscar, act_inicio, act_fin, act_pago))
    btn_actualizar.grid(row=3, column=0, columnspan=2, pady=(20, 0), sticky='ew')

    frame_fotos_wrapper = ttk.LabelFrame(frame_contenido, text=" Fotografías del Socio ", padding=10)
    frame_fotos_wrapper.grid(row=0, column=1, sticky='nsew', padx=(10, 0))

    frame_fotos = ttk.Frame(frame_fotos_wrapper)
    frame_fotos.pack(fill='both', expand=True, pady=(0, 10))
    frame_fotos.grid_propagate(False) 

    lbl_estado_foto = ttk.Label(frame_fotos, text="Busca un socio para\nver sus fotografías.", justify="center", foreground="gray")
    lbl_estado_foto.grid(row=0, column=0, sticky="nsew")
    frame_fotos.rowconfigure(0, weight=1)
    frame_fotos.columnconfigure(0, weight=1)

    frame_acciones_fotos = ttk.Frame(frame_fotos_wrapper)
    frame_acciones_fotos.pack(fill='x', side='bottom')

    btn_abrir_carpeta = ttk.Button(frame_acciones_fotos, text="📂 Abrir Carpeta",
                                   command=lambda: abrir_carpeta_socio_actual(entry_buscar.get()))
    btn_abrir_carpeta.pack(side='left', fill='x', expand=True, padx=(0, 5))

    btn_tomar_foto = ttk.Button(frame_acciones_fotos, text="📷 Tomar Foto",
                                command=lambda: capturar_foto_socio(app, entry_buscar.get()))
    btn_tomar_foto.pack(side='right', fill='x', expand=True, padx=(5, 0))

    def cargar_fotos(nombre_socio):
        global imagenes_referencia
        imagenes_referencia.clear()
        
        app.socio_actual_cargado = nombre_socio

        frame_fotos.unbind("<Configure>")
        for widget in frame_fotos.winfo_children():
            widget.destroy()

        # REINICIAR LAS COLUMNAS PREVIAS PARA QUE NO QUEDEN ESPACIOS VACÍOS
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

    def filtrar_autocompletado(event):
        if event.keysym in ("Up", "Down", "Return", "Escape"):
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
            listbox_sugerencias.place(in_=frame_busqueda, x=entry_buscar.winfo_x(),
                                      y=entry_buscar.winfo_height() + 2, width=entry_buscar.winfo_width())
            listbox_sugerencias.lift()
        else:
            listbox_sugerencias.place_forget()

    def mover_foco_a_lista(event):
        if listbox_sugerencias.winfo_ismapped() and listbox_sugerencias.size() > 0:
            listbox_sugerencias.focus_set()
            listbox_sugerencias.selection_clear(0, tk.END)
            listbox_sugerencias.selection_set(0)
            listbox_sugerencias.activate(0)

    def seleccionar_sugerencia(event):
        if not listbox_sugerencias.curselection():
            return
        indice = listbox_sugerencias.curselection()[0]
        nombre_seleccionado = listbox_sugerencias.get(indice)
        entry_buscar.delete(0, tk.END)
        entry_buscar.insert(0, nombre_seleccionado)
        listbox_sugerencias.place_forget()
        entry_buscar.focus_set()
        ejecutar_busqueda_completa()

    def ocultar_lista(event):
        listbox_sugerencias.place_forget()
        entry_buscar.focus_set()

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

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Error de Cámara", "No se pudo acceder a la cámara web.")
            return

        messagebox.showinfo("Tomar Foto", "Se abrirá la cámara.\n\n- Presiona ESPACIO para tomar la foto.\n- Presiona ESC para cancelar.")

        foto_guardada = False
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            display_frame = frame.copy()
            cv2.putText(display_frame, "ESPACIO: Tomar Foto | ESC: Salir", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow(f"Tomar Foto - {nombre}", display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 32:
                timestamp = int(time.time())
                ruta_foto = os.path.join(ruta_carpeta, f"foto_{timestamp}.jpg")
                cv2.imwrite(ruta_foto, frame)
                foto_guardada = True
                break
            elif key == 27:
                break

        cap.release()
        cv2.destroyAllWindows()

        if foto_guardada:
            reencodear_y_actualizar_socio(nombre)
            cargar_fotos(nombre)
            messagebox.showinfo("Éxito", f"Nueva foto agregada y perfil facial actualizado para '{nombre}'.")

    entry_buscar.bind('<KeyRelease>', filtrar_autocompletado)
    entry_buscar.bind('<Down>', mover_foco_a_lista)
    entry_buscar.bind('<Return>', ejecutar_busqueda_completa)
    listbox_sugerencias.bind('<<ListboxSelect>>', seleccionar_sugerencia)
    listbox_sugerencias.bind('<Return>', seleccionar_sugerencia)
    listbox_sugerencias.bind('<Escape>', ocultar_lista)

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