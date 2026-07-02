import streamlit as st
import pandas as pd
import plotly.express as px
import json
import requests

# ==========================================
# VARIABLES
# ==========================================
# URL cruda de tu archivo JSON en GitHub (Cámbiala por la tuya)
# IMPORTANTE: Si tu repo es privado, deberás usar un Token de GitHub aquí.
URL_DATOS_GITHUB = "https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/datos.json"
SEGUNDOS_EN_UN_DIA = 24 * 60 * 60

@st.cache_data(ttl=300) # Cache de 5 minutos
def cargar_datos():
    try:
        response = requests.get(URL_DATOS_GITHUB)
        response.raise_for_status()
        data = json.loads(response.text)
        df = pd.DataFrame(data)
        # Convertir strings ISO de vuelta a datetime
        df['inicio_utc'] = pd.to_datetime(df['inicio_utc'])
        df['fin_utc'] = pd.to_datetime(df['fin_utc'])
        df['fecha_dia'] = pd.to_datetime(df['fecha_dia']).dt.date
        return df
    except Exception as e:
        st.error(f"Error al cargar datos desde GitHub: {e}")
        return pd.DataFrame()

# ==========================================
# INTERFAZ (El mismo código de antes, pero sin leer archivos locales)
# ==========================================
st.set_page_config(page_title="Monitor Grabaciones", layout="wide")
st.title("🎙️ Dashboard de Grabaciones (Live)")

df = cargar_datos()

if df.empty:
    st.warning("Esperando datos del servidor FTP...")
else:
    # --- FILTROS ---
    with st.sidebar:
        st.header("Filtros")
        fecha_min = df['fecha_dia'].min()
        fecha_max = df['fecha_dia'].max()
        
        fechas_sel = st.date_input("Rango de fechas:", value=(fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max)
        fuentes_sel = st.multiselect("Fuentes:", opciones=sorted(df['fuente'].unique()), default=sorted(df['fuente'].unique()))
        equipos_sel = st.multiselect("Equipos:", opciones=sorted(df['equipo'].unique()), default=sorted(df['equipo'].unique()))

    # Filtrar
    mask = (
        (df['fecha_dia'] >= fechas_sel[0]) & (df['fecha_dia'] <= fechas_sel[1]) &
        (df['fuente'].isin(fuentes_sel)) & (df['equipo'].isin(equipos_sel))
    )
    df_filtrado = df[mask].copy()

    # Calcular porcentajes
    df_porcentaje = df_filtrado.groupby(['fuente', 'fecha_dia'])['duracion_seg'].sum().reset_index()
    df_porcentaje['porcentaje'] = (df_porcentaje['duracion_seg'] / SEGUNDOS_EN_UN_DIA) * 100
    df_porcentaje['fecha_str'] = df_porcentaje['fecha_dia'].astype(str)

    # --- GRÁFICOS ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Bloques Horarios (Gantt)")
        fig_gantt = px.timeline(
            df_filtrado.sort_values(by=['fuente', 'inicio_utc']),
            x_start="inicio_utc", x_end="fin_utc", y="fuente",
            color="fuente", facet_col="fecha_dia", height=600, hover_data=["equipo"]
        )
        fig_gantt.update_layout(xaxis_title="Hora (UTC)", yaxis_title="", showlegend=False)
        fig_gantt.update_xaxes(tickformat="%H:%M")
        fig_gantt.update_yaxes(matches=None)
        st.plotly_chart(fig_gantt, use_container_width=True)

    with col2:
        st.subheader("% de Tiempo Grabado")
        fig_pct = px.bar(df_porcentaje, x="fecha_str", y="porcentaje", color="fuente", text_auto=".2f", height=600)
        fig_pct.update_layout(xaxis_title="Fecha", yaxis_title="Porcentaje (%)", yaxis_range=[0, 100])
        st.plotly_chart(fig_pct, use_container_width=True)
        
    # Tabla
    st.subheader("Tabla de Porcentajes")
    tabla_resumen = df_porcentaje.pivot(index='fuente', columns='fecha_dia', values='porcentaje')
    st.dataframe(tabla_resumen.style.format("{:.2f}%").background_gradient(cmap='Greens'), use_container_width=True)
