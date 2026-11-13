import streamlit as st
import numpy as np
import plotly.graph_objects as go
from utils import generar_pico_gaussiano, generar_ruido, calcular_lod_loq, regresion_lineal

st.set_page_config(page_title="Laboratorio Virtual Pico-molar", layout="wide")

# ============================================================
# 1. ESTADO INICIAL (el "cerebro" del laboratorio)
# ============================================================
if "paso" not in st.session_state:
    st.session_state.paso = 0
if "acciones" not in st.session_state:
    st.session_state.acciones = {
        "estandar": False, "espiqueo": False, "acondicionado": False,
        "cargado": False, "lavado": False, "eluido": False,
        "reconstituido": False, "inyectado": False
    }

PASOS = [
    "1. Preparar estándares en matraz aforado",
    "2. Espikear la matriz acuosa (beaker)",
    "3. Acondicionar columna SPE (MeOH → H2O)",
    "4. Cargar la muestra sobre la columna",
    "5. Lavar interferentes con agua",
    "6. Eluir analito con metanol",
    "7. Evaporar y reconstituir en vial",
    "8. Inyectar al HPLC y leer cromatograma",
]

# ============================================================
# 2. COMPONENTES SVG DEL LABORATORIO (vidriería animada)
# ============================================================
def svg_beaker(nivel=0.0, color="#4fc3f7", etiqueta="Beaker 250 mL", anim=False):
    """Vaso de precipitados con líquido que sube según 'nivel' (0..1)."""
    h = 120 * nivel
    y_liquid = 180 - h
    wave = '<animate attributeName="d" dur="2s" repeatCount="indefinite" values="..."/>' if anim else ""
    return f"""
    <svg viewBox="0 0 160 220" width="150">
      <defs><linearGradient id="g{color}" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="{color}"/><stop offset="1" stop-color="#0288d1"/>
      </linearGradient></defs>
      <rect x="30" y="40" width="100" height="150" rx="6" fill="#e3f2fd" opacity="0.35" stroke="#37474f" stroke-width="3"/>
      <rect x="32" y="{y_liquid}" width="96" height="{h}" fill="url(#g{color})" opacity="0.85"/>
      <path d="M32,{y_liquid} Q56,{y_liquid-6} 80,{y_liquid} T128,{y_liquid}" fill="none" stroke="#01579b" stroke-width="2"/>
      <line x1="30" y1="40" x2="20" y2="40" stroke="#37474f" stroke-width="3"/>
      <text x="80" y="210" font-size="11" text-anchor="middle" fill="#263238">{etiqueta}</text>
    </svg>"""

def svg_matraz(nivel=0.0, etiqueta="Matraz 100 mL"):
    """Matraz aforado (forma de pera) con menisco en la marca."""
    h = 40 * nivel
    return f"""
    <svg viewBox="0 0 160 220" width="150">
      <path d="M70,30 h20 v60 q35,15 35,75 a45,45 0 0 1 -90,0 q0,-60 35,-75 z" fill="#e3f2fd" opacity="0.35" stroke="#37474f" stroke-width="3"/>
      <path d="M50,140 q30,40 60,0 l0,30 a40,40 0 0 1 -60,0 z" fill="#4fc3f7" opacity="0.85" transform="scale(1,{nivel}) translate(0,{(1-nivel)*160})"/>
      <line x1="60" y1="95" x2="100" y2="95" stroke="#d32f2f" stroke-width="2"/>
      <text x="80" y="210" font-size="11" text-anchor="middle" fill="#263238">{etiqueta}</text>
    </svg>"""

def svg_pipeta(goteando=False, etiqueta="Pipeta 5 mL"):
    """Pipeta con gota animada cayendo."""
    gota = '<circle cx="80" cy="150" r="5" fill="#4fc3f7"><animate attributeName="cy" from="150" to="200" dur="1s" repeatCount="indefinite"/></circle>' if goteando else ""
    return f"""
    <svg viewBox="0 0 160 220" width="120">
      <rect x="76" y="20" width="8" height="120" rx="3" fill="#eceff1" stroke="#37474f" stroke-width="2"/>
      <path d="M76,140 q4,12 8,0" fill="#eceff1" stroke="#37474f" stroke-width="2"/>
      <rect x="74" y="20" width="12" height="10" fill="#1565c0"/>
      {gota}
      <text x="80" y="215" font-size="11" text-anchor="middle" fill="#263238">{etiqueta}</text>
    </svg>"""

def svg_columna_spe(fase="vacia", etiqueta="Cartucho SPE C18"):
    """Columna SPE: lecho C18 gris + líquido según fase."""
    colores = {"vacia": "#cfd8dc", "acond": "#4fc3f7", "carga": "#81d4fa", "lavar": "#b3e5fc", "eluir": "#ffeb3b"}
    c = colores.get(fase, "#cfd8dc")
    gotas = '<circle cx="80" cy="195" r="4" fill="#ffeb3b"><animate attributeName="cy" from="185" to="210" dur="0.8s" repeatCount="indefinite"/></circle>' if fase == "eluir" else ""
    return f"""
    <svg viewBox="0 0 160 230" width="110">
      <rect x="60" y="30" width="40" height="150" rx="6" fill="#eceff1" stroke="#37474f" stroke-width="3"/>
      <rect x="62" y="110" width="36" height="35" fill="#90a4ae"/>
      <rect x="62" y="32" width="36" height="78" fill="{c}" opacity="0.85"/>
      <path d="M60,180 l20,25 l20,-25" fill="#eceff1" stroke="#37474f" stroke-width="2"/>
      {gotas}
      <text x="80" y="225" font-size="10" text-anchor="middle" fill="#263238">{etiqueta}</text>
    </svg>"""

def svg_vial(etiqueta="Vial HPLC 2 mL"):
    return f"""
    <svg viewBox="0 0 160 220" width="90">
      <rect x="55" y="60" width="50" height="120" rx="6" fill="#e3f2fd" opacity="0.4" stroke="#37474f" stroke-width="3"/>
      <rect x="55" y="120" width="50" height="60" fill="#4fc3f7" opacity="0.85"/>
      <rect x="50" y="45" width="60" height="18" rx="3" fill="#455a64"/>
      <text x="80" y="210" font-size="10" text-anchor="middle" fill="#263238">{etiqueta}</text>
    </svg>"""

def render_banco(p, act):
    """Arma la 'mesa' de vidrio según el paso y las acciones."""
    nivel_beaker = 0.7 if act["espiqueo"] else 0.0
    fase_col = ("eluir" if p == 6 else "lavar" if p == 5 else "carga" if p == 4
                else "acond" if act["acondicionado"] else "vacia")
    fila = ""
    if p in (0,1): fila += svg_matraz(1.0 if act["estandar"] else 0.0)
    if p in (1,2): fila += svg_beaker(nivel_beaker, anim=act["espiqueo"])
    if p in (2,3,4,5,6): fila += svg_columna_spe(fase_col)
    if p in (0,1): fila += svg_pipeta(goteando=(p==1))
    if p in (6,7): fila += svg_vial()
    return f'<div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;background:#fafafa;padding:15px;border-radius:12px;border:1px solid #e0e0e0;">{fila}</div>'

# ============================================================
# 3. LÓGICA QUÍMICA: recuperación → área del pico → LOD
# ============================================================
def calcular_recuperacion(act, vol_elucion):
    """El estudiante 'comete errores' y la química lo penaliza (real)."""
    rec = 0.95
    if not act["acondicionado"]: rec *= 0.42   # lecho seco → analito pasa de largo
    if not act["lavado"]:        ruido_extra = True
    else:                        ruido_extra = False
    if vol_elucion < 1.5:        rec *= vol_elucion / 2.0  # elución incompleta
    return max(0.05, rec), ruido_extra

# ============================================================
# 4. UI PRINCIPAL CON PESTAÑAS
# ============================================================
st.title("🧪 Laboratorio Virtual — Sustancias Picoactivas (Escala pM)")
st.caption("UdeA · Pregrado y Posgrado · Química Analítica")

tab_teoria, tab_lab, tab_croma, tab_calc = st.tabs(
    ["📖 Teoría", "🔬 Laboratorio Virtual", "📈 Cromatograma", "🧮 Cálculos LOD/LOQ"]
)

with tab_teoria:
    st.markdown(PASOS[st.session_state.paso] + "  \n\n" +
                "Siga el procedimiento en la pestaña **Laboratorio Virtual**. "
                "Cada acción tiene una consecuencia química real en el cromatograma final.")

with tab_lab:
    p = st.session_state.paso
    st.subheader(PASOS[p])
    st.markdown(render_banco(p, st.session_state.acciones), unsafe_allow_html=True)

    # Sliders de parámetros de la práctica real
    col1, col2 = st.columns(2)
    with col1:
        conc = st.slider("Concentración de espiqueo (pM)", 10, 1000, 100)
        vol_elu = st.slider("Volumen de elución (mL)", 0.5, 3.0, 2.0, 0.1)
    with col2:
        st.info(f"Paso {p+1}/8 · Recuperación estimada: "
                f"{calcular_recuperacion(st.session_state.acciones, vol_elu)[0]*100:.0f}%")

    b1, b2, b3 = st.columns(3)
    if b1.button("▶ Ejecutar paso", use_container_width=True):
        claves = ["estandar","espiqueo","acondicionado","cargado","lavado","eluido","reconstituido","inyectado"]
        st.session_state.acciones[claves[p]] = True
        if p < 7: st.session_state.paso += 1
        st.rerun()
    if b2.button("⏭ Saltar", use_container_width=True):
        if p < 7: st.session_state.paso += 1
        st.rerun()
    if b3.button("🔄 Reiniciar", use_container_width=True):
        st.session_state.paso = 0
        st.session_state.acciones = {k:False for k in st.session_state.acciones}
        st.rerun()

    # Advertencias pedagógicas (errores reales)
    if p >= 3 and not st.session_state.acciones["acondicionado"]:
        st.error("⚠️ La columna SPE está SECA. El analito no se retiene → recuperación ~40%. "
                 "Vuelva al paso 3 y ejecute el acondicionamiento.")
    if p >= 5 and not st.session_state.acciones["lavado"]:
        st.warning("⚠️ No lavó interferentes → la línea base del HPLC tendrá ruido alto.")

with tab_croma:
    # El cromatograma se construye con la recuperación REAL del estudiante
    rec, ruido_extra = calcular_recuperacion(st.session_state.acciones, vol_elu)
    tiempo = np.linspace(0, 10, 1000)
    sigma = 35 if ruido_extra else 12.5
    ruido = generar_ruido(len(tiempo), sigma)
    altura = conc * 14.03 * rec          # sensibilidad × concentración × recuperación
    pico = generar_pico_gaussiano(tiempo, altura, 5.0, 0.15)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tiempo, y=ruido+pico, name="Señal", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=tiempo, y=ruido, name="Ruido base", line=dict(color="gray", dash="dot")))
    fig.update_layout(template="plotly_white", xaxis_title="Tiempo (min)",
                      yaxis_title="Área (u.A.)", title=f"Cromatograma · Recuperación {rec*100:.0f}%")
    st.plotly_chart(fig, use_container_width=True)

with tab_calc:
    st.subheader("LOD / LOQ resultantes de SU práctica virtual")
    S = 14.03
    lod, loq = calcular_lod_loq(S, sigma)
    c1, c2, c3 = st.columns(3)
    c1.metric("Pendiente S", f"{S}")
    c2.metric("LOD", f"{lod:.2f} pM")
    c3.metric("LOQ", f"{loq:.2f} pM")
    st.code(f"""# Ejemplo numérico (su muestra virtual)
σ (ruido)        = {sigma} u.A.   {'← alto por NO lavar' if ruido_extra else '← blanco correcto'}
S (pendiente)    = 14.03
LOD = 3.3·σ / S  = 3.3·{sigma}/14.03 = {lod:.2f} pM
LOQ = 10·σ / S   = 10·{sigma}/14.03  = {loq:.2f} pM
Recuperación    = {rec*100:.0f}%   →  Área pico = {altura:.0f} u.A.""")
