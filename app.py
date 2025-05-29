import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px
import numpy as np

# Configuración desde archivo local
# IMPORTANTE: Asegúrate de que INFLUX_URL, INFLUX_TOKEN, ORG y BUCKET en 'config.py'
# sean los correctos para tu proyecto de Microcultivos (BUCKET debería ser "homeiot").
# Si no es así, y no puedes cambiar config.py, deberías redefinir BUCKET aquí:
# BUCKET = "homeiot" # Descomenta y ajusta si es necesario.
from config import INFLUX_URL, INFLUX_TOKEN, ORG, BUCKET

# Consulta simple de un solo campo
def query_data(measurement, field, range_minutes=60):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
    query_api = client.query_api()

    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: -{range_minutes}m)
      |> filter(fn: (r) => r["_measurement"] == "{measurement}" and r["_field"] == "{field}")
      |> sort(columns: ["_time"])
    '''

    result = query_api.query(query)
    data = []

    for table in result:
        for record in table.records:
            # Asegurarse de que el record no sea None y tenga los atributos esperados
            if record and record.get_time() and record.get_value() is not None:
                data.append({"time": record.get_time(), field: record.get_value()})
    
    df = pd.DataFrame(data)
    if not df.empty:
        # Asegurarse de que 'time' sea datetime y esté localizado en UTC
        df["time"] = pd.to_datetime(df["time"])
        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize('UTC') # Asumir UTC si no tiene timezone
        # Puedes convertirlo a tu timezone local para mostrar si lo deseas, ej:
        # df["time"] = df["time"].dt.tz_convert('America/Bogota')  
    return df

# Configuración de la app
st.set_page_config(page_title="🌿 Monitor de Microcultivos Urbanos", layout="wide")
st.title("🌿 Monitor de Microcultivos Urbanos")
st.markdown("Monitorea en tiempo real los datos ambientales de tus microcultivos: temperatura, humedad y radiación UV.")

# Selector de tiempo
range_minutes = st.slider("Selecciona el rango de tiempo (en minutos):", 10, 180, 60)

# Consultas de datos desde InfluxDB
temp_df = query_data("airSensor", "temperature", range_minutes)  
hum_df = query_data("airSensor", "humidity", range_minutes)  
uv_df = query_data("uv_sensor", "uv_index", range_minutes)  

st.subheader("📈 Visualización de Datos Recientes (Streamlit)")

# Visualización de datos con Plotly (Streamlit)
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("##### 🌡️ Temperatura (°C)")
    if not temp_df.empty:
        st.plotly_chart(px.line(temp_df, x="time", y="temperature", title="Temperatura"), use_container_width=True)
    else:
        st.info("Sin datos de temperatura en este rango.")

with col2:
    st.markdown("##### 💧 Humedad (%)")
    if not hum_df.empty:
        st.plotly_chart(px.line(hum_df, x="time", y="humidity", title="Humedad"), use_container_width=True)
    else:
        st.info("Sin datos de humedad en este rango.")

with col3:
    st.markdown("##### ☀️ Índice UV")
    if not uv_df.empty:
        st.plotly_chart(px.line(uv_df, x="time", y="uv_index", title="Índice UV"), use_container_width=True)
    else:
        st.info("Sin datos de UV en este rango.")

# Análisis Estadísticos
st.subheader("📊 Análisis Estadístico (últimos " + str(range_minutes) + " minutos)")  

if not temp_df.empty:
    st.write("Temperatura:")
    col_stats_temp1, col_stats_temp2, col_stats_temp3 = st.columns(3)
    col_stats_temp1.metric("Mínima", f"{temp_df['temperature'].min():.2f} °C")
    col_stats_temp2.metric("Máxima", f"{temp_df['temperature'].max():.2f} °C")
    col_stats_temp3.metric("Promedio", f"{temp_df['temperature'].mean():.2f} °C")
else:
    st.write("Temperatura: Sin datos para análisis.")

if not hum_df.empty:
    st.write("Humedad:")
    col_stats_hum1, col_stats_hum2, col_stats_hum3 = st.columns(3)
    col_stats_hum1.metric("Mínima", f"{hum_df['humidity'].min():.2f} %")
    col_stats_hum2.metric("Máxima", f"{hum_df['humidity'].max():.2f} %")
    col_stats_hum3.metric("Promedio", f"{hum_df['humidity'].mean():.2f} %")
else:
    st.write("Humedad: Sin datos para análisis.")

if not uv_df.empty:
    st.write("Índice UV:")
    col_stats_uv1, col_stats_uv2, col_stats_uv3 = st.columns(3)
    col_stats_uv1.metric("Mínimo", f"{uv_df['uv_index'].min():.2f}")  
    col_stats_uv2.metric("Máximo", f"{uv_df['uv_index'].max():.2f}")
    col_stats_uv3.metric("Promedio", f"{uv_df['uv_index'].mean():.2f}")
else:
    st.write("Índice UV: Sin datos para análisis.")

# Recomendaciones Automatizadas
st.subheader("💡 Recomendaciones Automatizadas")  

# Umbrales (ejemplos, ajusta según el tipo de cultivo)
HUMIDITY_LOW_THRESHOLD = 40
UV_HIGH_THRESHOLD = 6

recommendations = []

if not hum_df.empty:
    last_humidity = hum_df['humidity'].iloc[-1]
    if last_humidity < HUMIDITY_LOW_THRESHOLD:
        recommendations.append(f"💧 Humedad baja ({last_humidity:.1f}%). Considera regar tus cultivos.")  
else:
    recommendations.append("💧 No hay datos recientes de humedad para generar recomendaciones de riego.")

if not uv_df.empty:
    last_uv = uv_df['uv_index'].iloc[-1]
    if last_uv > UV_HIGH_THRESHOLD:
        recommendations.append(f"☀️ Radiación UV alta ({last_uv:.1f}). Considera proteger tus cultivos con sombra.")  
else:
    recommendations.append("☀️ No hay datos recientes de UV para generar recomendaciones de protección solar.")

if recommendations:
    for rec in recommendations:
        if "Humedad baja" in rec or "Radiación UV alta" in rec:
            st.warning(rec)
        else:
            st.info(rec)
else:
    st.info("🌱 Tus cultivos parecen estar en condiciones adecuadas según los datos actuales, o no hay suficientes datos.")

# --- SECCIÓN PARA PANELES ESPECÍFICOS DE GRAFANA ---
st.subheader("🖼️ Visualizaciones Específicas desde Grafana")

# 1. Panel de Grafana: Heat Index
st.markdown("#### Índice de Calor (desde Grafana)")
URL_GRAFANA_HEAT_INDEX_IFRAME = "https://santianchez05.grafana.net/d-solo/09ff8bd6-e9d7-4852-9bc7-c7ae01600f54/humidity-vs-temperature?orgId=1&from=1747325219746&to=1747368419746&timezone=browser&panelId=3&__feature.dashboardSceneSolo=true"
if URL_GRAFANA_HEAT_INDEX_IFRAME != "URL_DE_IFRAME_PARA_HEAT_INDEX_AQUI": # Este es un placeholder, asumo que ya lo has cambiado
    st.components.v1.iframe(URL_GRAFANA_HEAT_INDEX_IFRAME, height=300, scrolling=True)
else:
    st.warning("Por favor, configura la URL del iframe para el panel 'Heat Index' de Grafana.")

# 2. Panel de Grafana: Humidity Heatmap
st.markdown("#### Mapa de Calor de Humedad (desde Grafana)")
URL_GRAFANA_HUMIDITY_HEATMAP_IFRAME = "https://santianchez05.grafana.net/d-solo/09ff8bd6-e9d7-4852-9bc7-c7ae01600f54/humidity-vs-temperature?orgId=1&from=1747325219746&to=1747368419746&timezone=browser&panelId=6&__feature.dashboardSceneSolo=true"
if URL_GRAFANA_HUMIDITY_HEATMAP_IFRAME != "URL_DE_IFRAME_PARA_HUMIDITY_HEATMAP_AQUI": # Este es un placeholder, asumo que ya lo has cambiado
    st.components.v1.iframe(URL_GRAFANA_HUMIDITY_HEATMAP_IFRAME, height=300, scrolling=True)
else:
    st.warning("Por favor, configura la URL del iframe para el panel 'Humidity Heatmap' de Grafana.")

# --- FIN SECCIÓN PANELES GRAFANA ---

# Enlace al Dashboard Completo de Grafana
st.subheader("🔗 Acceso al Dashboard Completo en Grafana")  
st.markdown(
    """
    Para un análisis más detallado y todas las visualizaciones interactivas, puedes acceder al dashboard completo en Grafana.
    [Haz clic aquí para ver el panel completo en Grafana](https://santianchez05.grafana.net/goto/Z3DSlcfNR?orgId=1)
    """,
    unsafe_allow_html=True
)

st.caption("Proyecto Integrador - Computación Física e IoT")
