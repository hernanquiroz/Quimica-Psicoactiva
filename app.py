import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Simulador Cromatográfico Pico-molar", layout="wide")
st.title("🧪 Simulador de Análisis Ultra-Traza (Escala Pico-molar)")
st.markdown("Práctica de Química de Sustancias Psicoactivas/Bioactivas - UdeA")

# --- BARRA LATERAL (PARÁMETROS DEL ESTUDIANTE) ---
st.sidebar.header("Parámetros de Simulación")
conc_pM = st.sidebar.slider("Concentración de la sustancia (pM)", 0.0, 100.0, 10.0, 0.1)
ruido_base = st.sidebar.slider("Ruido instrumental (Desv. Est.)", 1.0, 50.0, 10.0, 0.5)
sensibilidad = st.sidebar.slider("Sensibilidad del detector (Área/pM)", 5.0, 50.0, 14.0, 0.5)

# --- CÁLCULOS MATEMÁTICOS ---
# Generar eje X (Tiempo en minutos)
tiempo = np.linspace(0, 10, 1000)

# 1. Generar Ruido Base (Distribución Normal)
ruido = np.random.normal(0, ruido_base, len(tiempo))

# 2. Generar Pico Cromatográfico (Función Gaussiana)
# El área del pico es proporcional a la concentración y la sensibilidad
altura_pico = conc_pM * sensibilidad 
centro_pico = 5.0  # Tiempo de retención fijo
desv_pico = 0.15   # Ancho del pico

pico_gaussiano = altura_pico * np.exp(-((tiempo - centro_pico)**2) / (2 * desv_pico**2))

# 3. Señal Total (Cromatograma)
senal_total = ruido + pico_gaussiano

# 4. Cálculo automático de LOD y LOQ simulados
# Asumiendo que el LOD es cuando la altura del pico es 3.3 veces el ruido
LOD_simulado = (3.3 * ruido_base) / sensibilidad
LOQ_simulado = (10.0 * ruido_base) / sensibilidad

# --- VISUALIZACIÓN EN PANTALLA ---
col1, col2 = st.columns([3, 1])

with col1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tiempo, y=senal_total, mode='lines', name='Señal Total', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=tiempo, y=ruido, mode='lines', name='Ruido Base', line=dict(color='gray', dash='dot')))
    
    fig.update_layout(
        title=f"Cromatograma Simulado (Conc: {conc_pM} pM)",
        xaxis_title="Tiempo de Retención (min)",
        yaxis_title="Respuesta del Detector (Unidades de Área)",
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.metric("LOD Simulado", f"{LOD_simulado:.2f} pM")
    st.metric("LOQ Simulado", f"{LOQ_simulado:.2f} pM")
    
    if conc_pM < LOD_simulado:
        st.error("⚠️ La concentración está por debajo del LOD. El pico se pierde en el ruido.")
    elif conc_pM < LOQ_simulado:
        st.warning("⚠️ La concentración está entre el LOD y el LOQ. Detección posible, pero no cuantificable con precisión.")
    else:
        st.success("✅ Concentración cuantificable (Supera el LOQ).")

st.sidebar.markdown("---")
st.sidebar.info("Desarrollado para el Laboratorio de Química Analítica. Ajuste los parámetros para observar los límites de detección.")
