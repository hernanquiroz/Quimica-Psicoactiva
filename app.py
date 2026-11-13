import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import plotly.graph_objects as go
from utils import (generar_pico_gaussiano, generar_ruido,
                   calcular_lod_loq, regresion_lineal, cargar_datos_calibracion)

st.set_page_config(page_title="Laboratorio Virtual Pico-molar", layout="wide")

# ============================================================
# ESTADO DEL LABORATORIO
# ============================================================
if "paso" not in st.session_state:
    st.session_state.paso = 0
if "act" not in st.session_state:
    st.session_state.act = {k: False for k in
        ["estandar", "espiqueo", "acondicionado", "cargado",
         "lavado", "eluido", "reconstituido", "inyectado"]}

PASOS = [
    "1. Preparar estándares en matraz aforado",
    "2. Espiquear la matriz acuosa (beaker)",
    "3. Acondicionar columna SPE (MeOH → H2O)",
    "4. Cargar la muestra sobre la columna",
    "5. Lavar interferentes con agua",
    "6. Eluir analito con metanol",
    "7. Evaporar y reconstituir en vial",
    "8. Inyectar al HPLC y leer cromatograma",
]
CLAVES = ["estandar", "espiqueo", "acondicionado", "cargado",
          "lavado", "eluido", "reconstituido", "inyectado"]

# ============================================================
# LÓGICA QUÍMICA (el error tiene consecuencia real)
# ============================================================
def recuperacion(act, vol_elu):
    rec = 0.95
    ruido_extra = False
    if not act["acondicionado"]:
        rec *= 0.42
    if not act["lavado"]:
        ruido_extra = True
    if vol_elu < 1.5:
        rec *= vol_elu / 2.0
    return max(0.05, rec), ruido_extra

# ============================================================
# ESCENA SVG DEL LABORATORIO (vidriería realista)
# ============================================================
DEFS = """
<defs>
  <linearGradient id="vidrio" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#ffffff" stop-opacity="0.9"/>
    <stop offset="0.5" stop-color="#cfe8ff" stop-opacity="0.55"/>
    <stop offset="1" stop-color="#9ec9f0" stop-opacity="0.75"/>
  </linearGradient>
  <linearGradient id="agua" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#7fd4ff"/><stop offset="1" stop-color="#2196f3"/>
  </linearGradient>
  <linearGradient id="metanol" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff59d"/><stop offset="1" stop-color="#fbc02d"/>
  </linearGradient>
  <linearGradient id="analito" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ff8a65"/><stop offset="1" stop-color="#e64a19"/>
  </linearGradient>
  <linearGradient id="mesa" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#5d4037"/><stop offset="1" stop-color="#3e2723"/>
  </linearGradient>
  <filter id="sombra" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="2" dy="3" stdDeviation="2" flood-color="#000" flood-opacity="0.25"/>
  </filter>
</defs>
"""

CSS = """
<style>
  .drop{animation:caer 1.1s linear infinite}
  @keyframes caer{0%{transform:translateY(0);opacity:1}100%{transform:translateY(38px);opacity:0}}
  .spin{transform-origin:735px 250px;animation:girar 2.4s linear infinite}
  @keyframes girar{from{transform:rotate(0)}to{transform:rotate(360deg)}}
  .bub{animation:burb 1.6s ease-in infinite}
  @keyframes burb{0%{transform:translateY(0);opacity:0}30%{opacity:1}100%{transform:translateY(-22px);opacity:0}}
  .shine{opacity:.55}
  svg{display:block;margin:auto}
</style>
"""

def g_matraz(x, lleno):
    y_liq = 300 - (60 if lleno else 0)
    liq = (f'<path d="M{x-38},300 q38,-12 76,0 l0,40 a38,30 0 0 1 -76,0 z" fill="url(#agua)" opacity="0.85"/>' if lleno else "")
    return f"""<g filter="url(#sombra)">
      <path d="M{x-7},150 h14 v70 q40,18 40,80 a47,47 0 0 1 -94,0 q0,-62 40,-80 z" fill="url(#vidrio)" stroke="#455a64" stroke-width="3"/>
      {liq}
      <line x1="{x-12}" y1="178" x2="{x+12}" y2="178" stroke="#d32f2f" stroke-width="2"/>
      <rect x="{x-9}" y="138" width="18" height="14" rx="3" fill="#90a4ae"/>
      <path class="shine" d="M{x-30},210 q6,60 14,80" stroke="#fff" stroke-width="3" fill="none"/>
      <text x="{x}" y="360" font-size="12" text-anchor="middle" fill="#263238">Matraz 100 mL</text></g>"""

def g_beaker(x, nivel, color="agua"):
    h = 110 * nivel
    y_liq = 300 - h
    liq = f'<rect x="{x-46}" y="{y_liq}" width="92" height="{h}" fill="url(#{color})" opacity="0.85"/>' if nivel > 0 else ""
    men = f'<path d="M{x-46},{y_liq} q23,-7 46,0 t46,0" fill="none" stroke="#01579b" stroke-width="2"/>' if nivel > 0 else ""
    return f"""<g filter="url(#sombra)">
      <rect x="{x-50}" y="180" width="100" height="130" rx="6" fill="url(#vidrio)" stroke="#455a64" stroke-width="3"/>
      {liq}{men}
      <path d="M{x-50},180 l-12,0" stroke="#455a64" stroke-width="3"/>
      <path class="shine" d="M{x-40},190 v110" stroke="#fff" stroke-width="3" fill="none"/>
      <text x="{x}" y="360" font-size="12" text-anchor="middle" fill="#263238">Beaker 250 mL</text></g>"""

def g_pipeta(x, goteando):
    gota = f'<circle class="drop" cx="{x}" cy="300" r="4" fill="url(#agua)"/>' if goteando else ""
    return f"""<g filter="url(#sombra)">
      <ellipse cx="{x}" cy="150" rx="14" ry="20" fill="#b0bec5" stroke="#455a64" stroke-width="2"/>
      <rect x="{x-4}" y="168" width="8" height="120" rx="3" fill="url(#vidrio)" stroke="#455a64" stroke-width="2"/>
      <path d="M{x-4},288 q4,14 8,0" fill="url(#vidrio)" stroke="#455a64" stroke-width="2"/>
      {gota}<text x="{x}" y="360" font-size="12" text-anchor="middle" fill="#263238">Pipeta 5 mL</text></g>"""

def g_columna(x, fase):
    col = {"vacia": "#cfd8dc", "acond": "#7fd4ff", "carga": "#ff8a65", "lavar": "#b3e5fc", "eluir": "#fff59d"}.get(fase, "#cfd8dc")
    gotas = f'<circle class="drop" cx="{x}" cy="300" r="4" fill="url(#metanol)"/>' if fase == "eluir" else ""
    return f"""<g filter="url(#sombra)">
      <rect x="{x-22}" y="150" width="44" height="150" rx="6" fill="url(#vidrio)" stroke="#455a64" stroke-width="3"/>
      <rect x="{x-20}" y="232" width="40" height="34" fill="#90a4ae"/>
      <line x1="{x-20}" y1="232" x2="{x+20}" y2="232" stroke="#616161" stroke-width="2"/>
      <line x1="{x-20}" y1="266" x2="{x+20}" y2="266" stroke="#616161" stroke-width="2"/>
      <rect x="{x-20}" y="152" width="40" height="80" fill="{col}" opacity="0.85"/>
      <path d="M{x-22},300 l22,26 l22,-26" fill="url(#vidrio)" stroke="#455a64" stroke-width="2"/>
      {gotas}<text x="{x}" y="360" font-size="11" text-anchor="middle" fill="#263238">Cartucho SPE C18</text></g>"""

def g_rotavap(x):
    return f"""<g filter="url(#sombra)">
      <rect x="{x-50}" y="200" width="100" height="70" rx="8" fill="#455a64"/>
      <circle class="spin" cx="735" cy="250" r="26" fill="url(#agua)" stroke="#455a64" stroke-width="3"/>
      <rect x="{x-3}" y="150" width="6" height="60" fill="#90a4ae"/>
      <text x="{x}" y="360" font-size="12" text-anchor="middle" fill="#263238">Rotavapor</text></g>"""

def g_vial(x, lleno):
    liq = f'<rect x="{x-20}" y="250" width="40" height="40" fill="url(#analito)" opacity="0.9"/>' if lleno else ""
    return f"""<g filter="url(#sombra)">
      <rect x="{x-24}" y="210" width="48" height="90" rx="6" fill="url(#vidrio)" stroke="#455a64" stroke-width="3"/>
      {liq}
      <rect x="{x-26}" y="196" width="52" height="16" rx="3" fill="#37474f"/>
      <rect x="{x-18}" y="190" width="36" height="8" rx="2" fill="#ffeb3b"/>
      <text x="{x}" y="360" font-size="12" text-anchor="middle" fill="#263238">Vial HPLC 2 mL</text></g>"""

def g_hplc(x):
    return f"""<g filter="url(#sombra)">
      <rect x="{x-90}" y="150" width="180" height="150" rx="10" fill="#eceff1" stroke="#455a64" stroke-width="3"/>
      <rect x="{x-70}" y="170" width="90" height="50" rx="4" fill="#0d47a1"/>
      <polyline points="{x-66},210 {x-50},195 {x-38},200 {x-26},185 {x-14},205 {x-4},192"
        fill="none" stroke="#4fc3f7" stroke-width="2"/>
      <rect x="{x+24}" y="170" width="50" height="50" rx="4" fill="#cfd8dc"/>
      <circle cx="{x+49}" cy="195" r="14" fill="#90a4ae"/>
      <rect x="{x-70}" y="240" width="140" height="40" rx="4" fill="#b0bec5"/>
      <text x="{x}" y="360" font-size="12" text-anchor="middle" fill="#263238">HPLC-UV</text></g>"""

def escena(p, act):
    fase = ("eluir" if p == 6 else "lavar" if p == 5 else "carga" if p == 4
            else "acond" if act["acondicionado"] else "vacia")
    nivel_beaker = 0.7 if act["espiqueo"] else 0.0
    g = [g_matraz(90, act["estandar"])]
    g.append(g_beaker(260, nivel_beaker, "agua"))
    g.append(g_pipeta(410, p == 1))
    g.append(g_columna(560, fase))
    if p >= 6:
        g.append(g_rotavap(735))
    g.append(g_vial(880, act["reconstituido"]))
    if p >= 7:
        g.append(g_hplc(1060))
    mesa = '<rect x="0" y="300" width="1200" height="22" fill="url(#mesa)"/><rect x="40" y="322" width="14" height="120" fill="#3e2723"/><rect x="1146" y="322" width="14" height="120" fill="#3e2723"/>'
    return (f'<svg viewBox="0 0 1200 470" width="100%">{DEFS}'
            f'<rect x="0" y="0" width="1200" height="470" fill="#fafafa"/>{mesa}{"".join(g)}</svg>')

# ============================================================
# UI
# ============================================================
st.title("🧪 Laboratorio Virtual — Sustancias Picoactivas (Escala pM)")
st.caption("UdeA · Pregrado y Posgrado · Química Analítica")
tab_t, tab_l, tab_c, tab_x = st.tabs(["📖 Teoría", "🔬 Lab Virtual", "📈 Cromatograma", "🧮 LOD/LOQ"])

with tab_t:
    st.markdown(f"**{PASOS[st.session_state.paso]}**\n\nSiga el procedimiento en *Lab Virtual*. Cada acción tiene una consecuencia química real en el cromatograma final.")

with tab_l:
    p = st.session_state.paso
    st.subheader(PASOS[p])
    vol_elu = st.slider("Volumen de elución (mL)", 0.5, 3.0, 2.0, 0.1)
    conc = st.slider("Concentración de espiqueo (pM)", 10, 1000, 100)
    rec, ruido_extra = recuperacion(st.session_state.act, vol_elu)
    st.progress(rec, text=f"Recuperación estimada: {rec*100:.0f}%")
    components.html(CSS + escena(p, st.session_state.act), height=520)

    b1, b2, b3 = st.columns(3)
    if b1.button("▶ Ejecutar paso", use_container_width=True):
        st.session_state.act[CLAVES[p]] = True
        if p < 7: st.session_state.paso += 1
        st.rerun()
    if b2.button("⏭ Saltar", use_container_width=True):
        if p < 7: st.session_state.paso += 1
        st.rerun()
    if b3.button("🔄 Reiniciar", use_container_width=True):
        st.session_state.paso = 0
        st.session_state.act = {k: False for k in CLAVES}
        st.rerun()

    if p >= 3 and not st.session_state.act["acondicionado"]:
        st.error("⚠️ Columna SPE SECA: el analito no se retiene (recuperación ~40%). Vuelva al paso 3.")
    if p >= 5 and not st.session_state.act["lavado"]:
        st.warning("⚠️ Sin lavado: línea base con ruido alto en el HPLC.")

with tab_c:
    tiempo = np.linspace(0, 10, 1000)
    sigma = 35 if ruido_extra else 12.5
    ruido = generar_ruido(len(tiempo), sigma)
    altura = conc * 14.03 * rec
    pico = generar_pico_gaussiano(tiempo, altura, 5.0, 0.15)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tiempo, y=ruido + pico, name="Señal", line=dict(color="#1565c0")))
    fig.add_trace(go.Scatter(x=tiempo, y=ruido, name="Ruido base", line=dict(color="gray", dash="dot")))
    fig.update_layout(template="plotly_white", xaxis_title="Tiempo (min)",
                      yaxis_title="Área (u.A.)", title=f"Cromatograma · Recuperación {rec*100:.0f}%")
    st.plotly_chart(fig, use_container_width=True)

with tab_x:
    S = 14.03
    lod, loq = calcular_lod_loq(S, sigma)
    c1, c2, c3 = st.columns(3)
    c1.metric("Pendiente S", f"{S}")
    c2.metric("LOD", f"{lod:.2f} pM")
    c3.metric("LOQ", f"{loq:.2f} pM")
    try:
        x, y = cargar_datos_calibracion("data/ejemplo_calibracion.csv")
        r = regresion_lineal(x, y)
        st.write(f"**Curva real CSV:** S={r['pendiente']:.2f}, R²={r['r_cuadrado']:.4f}")
    except Exception as e:
        st.info(f"CSV no cargado: {e}")
    st.code(f"σ={sigma} u.A. {'(alto, sin lavar)' if ruido_extra else '(blanco OK)'}\n"
            f"LOD=3.3·σ/S={lod:.2f} pM\nLOQ=10·σ/S={loq:.2f} pM\n"
            f"Recuperación={rec*100:.0f}% → Área pico={altura:.0f} u.A.")
