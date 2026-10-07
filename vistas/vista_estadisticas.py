import sqlite3
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta

def obtener_datos(query, params=()):
    """Función auxiliar para ejecutar consultas de solo lectura en la BD."""
    try:
        conn = sqlite3.connect("gimnasio.db")
        cursor = conn.cursor()
        cursor.execute(query, params)
        datos = cursor.fetchall()
        conn.close()
        return datos
    except sqlite3.Error as e:
        print(f"Error de base de datos: {e}")
        return []

def aplicar_tema_oscuro(fig, axes):
    """Aplica colores oscuros a las gráficas para que combinen con el tema 'darkly'."""
    fig.patch.set_facecolor('#222222')
    for ax in axes:
        ax.set_facecolor('#2b2b2b')
        ax.tick_params(colors='white', which='both')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        for spine in ax.spines.values():
            spine.set_edgecolor('#555555')

def setup_tab_historial(parent):
    """Configura la pestaña y dibuja las gráficas leyendo la base de datos."""
    frame_principal = ttk.Frame(parent, padding=10)
    frame_principal.pack(fill=BOTH, expand=YES)

    titulo = ttk.Label(frame_principal, text="Panel de Estadísticas del Gimnasio", font=("Helvetica", 16, "bold"))
    titulo.pack(pady=(0, 10))

    hoy_dt = datetime.now()
    hoy = hoy_dt.strftime("%Y-%m-%d")
    proxima_semana = (hoy_dt + timedelta(days=7)).strftime("%Y-%m-%d")

    estado_socios = obtener_datos('''
        SELECT
            SUM(CASE WHEN fecha_fin > ? THEN 1 ELSE 0 END) as activos,
            SUM(CASE WHEN fecha_fin >= ? AND fecha_fin <= ? THEN 1 ELSE 0 END) as por_vencer
        FROM socios
    ''', (proxima_semana, hoy, proxima_semana))

    activos = 0
    por_vencer = 0

    if estado_socios and estado_socios[0]:
        activos = estado_socios[0][0] if estado_socios[0][0] is not None else 0
        por_vencer = estado_socios[0][1] if estado_socios[0][1] is not None else 0

    frame_kpis = ttk.Frame(frame_principal)
    frame_kpis.pack(fill=X, pady=(0, 15))

    lbl_activos = ttk.Label(
        frame_kpis,
        text=f"🏋️ Miembros Actuales (Activos): {activos}",
        font=("Helvetica", 14, "bold"),
        bootstyle="success"
    )
    lbl_activos.pack(side=LEFT, padx=(20, 40))

    lbl_por_vencer = ttk.Label(
        frame_kpis,
        text=f"⚠️ Miembros por Vencer (Próximos 7 días): {por_vencer}",
        font=("Helvetica", 14, "bold"),
        bootstyle="warning"
    )
    lbl_por_vencer.pack(side=LEFT, padx=20)

    fig = Figure(figsize=(11, 8), dpi=100)
    fig.subplots_adjust(hspace=0.6, wspace=0.3, bottom=0.15, top=0.9)

    ax1 = fig.add_subplot(221)
    ax2 = fig.add_subplot(222)
    ax3 = fig.add_subplot(223)
    ax4 = fig.add_subplot(224)

    aplicar_tema_oscuro(fig, [ax1, ax2, ax3, ax4])

    asistencias = obtener_datos('''
        SELECT substr(fecha_hora, 1, 10) as fecha, COUNT(*)
        FROM asistencias
        GROUP BY fecha ORDER BY fecha DESC LIMIT 7
    ''')
    if asistencias:
        fechas = [row[0][-5:] for row in reversed(asistencias)]
        cantidades = [row[1] for row in reversed(asistencias)]
        ax1.plot(fechas, cantidades, marker='o', color='#3498db', linewidth=2, markersize=8)
        ax1.fill_between(fechas, cantidades, color='#3498db', alpha=0.3)
        ax1.set_title("Flujo de Asistencias (Últimos 7 días)")
        ax1.set_ylabel("Personas")
    else:
        ax1.text(0.5, 0.5, "Sin datos de asistencia", color='white', ha='center', va='center')
        ax1.set_title("Flujo de Asistencias")

    horarios = obtener_datos('''
        SELECT substr(fecha_hora, 12, 2) as hora, COUNT(*)
        FROM asistencias
        WHERE fecha_hora IS NOT NULL AND length(fecha_hora) >= 13
        GROUP BY hora ORDER BY hora ASC
    ''')
    if horarios:
        horas = [f"{row[0]}:00" for row in horarios]
        cant_horas = [row[1] for row in horarios]
        ax2.bar(horas, cant_horas, color='#9b59b6')
        ax2.set_title("Horarios Pico (Histórico)")
        ax2.tick_params(axis='x', rotation=45)
    else:
        ax2.text(0.5, 0.5, "Sin datos de horarios", color='white', ha='center', va='center')
        ax2.set_title("Horarios Pico")

    inscripciones = obtener_datos('''
        SELECT substr(fecha_inicio, 1, 7) as mes, COUNT(*)
        FROM socios
        WHERE fecha_inicio IS NOT NULL AND fecha_inicio != ''
        GROUP BY mes ORDER BY mes DESC LIMIT 6
    ''')
    if inscripciones:
        meses = [row[0] for row in reversed(inscripciones)]
        cantidades = [row[1] for row in reversed(inscripciones)]
        ax3.bar(meses, cantidades, color='#f39c12')
        ax3.set_title("Crecimiento: Nuevas Inscripciones por mes")
        ax3.set_ylabel("Nuevos Socios")
        ax3.tick_params(axis='x', rotation=45)
    else:
        ax3.text(0.5, 0.5, "Sin datos de inscripciones", color='white', ha='center', va='center')
        ax3.set_title("Nuevas Inscripciones")

    valores = []
    etiquetas = []
    colores = []

    if activos > 0:
        valores.append(activos)
        etiquetas.append("Activos")
        colores.append('#2ecc71')

    if por_vencer > 0:
        valores.append(por_vencer)
        etiquetas.append("Por vencer (7d)")
        colores.append('#e67e22')

    if valores:
        ax4.pie(valores, labels=etiquetas, autopct='%1.1f%%', textprops={'color': "white"}, colors=colores, startangle=90)
        ax4.set_title("Estado de Membresías")
    else:
        ax4.text(0.5, 0.5, "Socios sin fechas registradas", color='white', ha='center', va='center')
        ax4.set_title("Estado de Membresías")

    canvas = FigureCanvasTkAgg(fig, master=frame_principal)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=BOTH, expand=YES)

if __name__ == "__main__":
    app = ttk.Window(title="Panel Administrativo del Gimnasio", themename="darkly")
    app.geometry("1000x800")

    setup_tab_historial(app)

    app.mainloop()
