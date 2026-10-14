import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Proyección y Control de Demanda - Acueducto",
    page_icon="💧",
    layout="wide",
)

st.title("💧 Sistema Inteligente de Proyección y Control de Tanques")
st.markdown(
    "Monitoreo operativo de niveles, validación de bandas de caudal según almacenamiento a las 06:00 a.m. y curva de recuperación."
)

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE TANQUES Y CAPACIDADES
# ---------------------------------------------------------
CAPACIDADES_TANQUES = {
    "Nivel_Colinas": 18000.0,
    "Nivel_Carmelo": 4500.0,
    "Nivel_Tk1_Planta": 4000.0,
    "Nivel_Tk2_Planta": 4000.0,
    "Nivel_TkNar2": 5000.0,
    "Nivel_SuccionA_TkColinas": 2500.0,
    "Nivel_Tk_Lomas": 3500.0,
}

VOLUMEN_TOTAL_SISTEMA = sum(CAPACIDADES_TANQUES.values())
META_AMANECER_PCT = 75.0  # Meta objetivo estricta

# Horas del día (00:00 a 23:00)
horas_dia = list(range(24))

# Curvas de referencia base (Ideal, Caudal Mínimo, Caudal Promedio/Objetivo, Caudal Máximo)
almacenamiento_ideal_ref = [
    75,
    78,
    82,
    85,
    88,
    85,
    75,
    60,
    50,
    45,
    48,
    52,
    55,
    58,
    55,
    50,
    48,
    52,
    60,
    65,
    70,
    72,
    74,
    75,
]
caudal_min_ref = [
    20,
    18,
    15,
    15,
    18,
    30,
    55,
    70,
    75,
    65,
    60,
    55,
    55,
    58,
    65,
    70,
    75,
    70,
    55,
    45,
    38,
    30,
    25,
    20,
]
caudal_prom_ref = [
    30,
    25,
    20,
    20,
    25,
    40,
    70,
    85,
    90,
    80,
    75,
    70,
    70,
    72,
    80,
    85,
    90,
    85,
    70,
    60,
    50,
    40,
    35,
    30,
]
caudal_max_ref = [
    40,
    32,
    28,
    28,
    32,
    50,
    85,
    100,
    105,
    95,
    90,
    85,
    85,
    88,
    95,
    100,
    105,
    100,
    85,
    75,
    62,
    50,
    45,
    40,
]

df_curva_base = pd.DataFrame({
    "Hora": horas_dia,
    "Almacenamiento_Ideal_Pct": almacenamiento_ideal_ref,
    "Caudal_Min": caudal_min_ref,
    "Caudal_Prom": caudal_prom_ref,
    "Caudal_Max": caudal_max_ref,
})

# ---------------------------------------------------------
# 2. PANEL LATERAL: ENTRADA DE DATOS OPERATIVOS
# ---------------------------------------------------------
st.sidebar.header("🎛️ Panel de Control Operativo")

# 1. Dato clave exigido: Almacenamiento real a las 06:00 a.m.
st.sidebar.subheader("🌅 Validación Matutina (06:00 a.m.)")
almacenamiento_06am_pct = st.sidebar.number_input(
    "% Almacenamiento real a las 06:00 a.m.",
    min_value=0.0,
    max_value=100.0,
    value=72.0,
    step=0.5,
    help="Porcentaje de almacenamiento con el que amaneció el sistema hoy.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ Monitoreo Turno Actual")
hora_actual = st.sidebar.selectbox(
    "Seleccione la Hora Actual de Corte", options=horas_dia, index=8
)

niveles_actuales_ingresados = {}
for tanque, cap_max in CAPACIDADES_TANQUES.items():
    val_def = (
        df_curva_base[df_curva_base["Hora"] == hora_actual][
            "Almacenamiento_Ideal_Pct"
        ].values[0]
        / 100.0
        * cap_max
        * 0.9
    )
    niveles_actuales_ingresados[tanque] = st.sidebar.number_input(
        f"{tanque} (m³)",
        min_value=0.0,
        max_value=cap_max * 1.2,
        value=float(val_def),
        step=100.0,
    )

caudal_distribucion_actual = st.sidebar.number_input(
    "Caudal de Distribución Real Actual (L/s)",
    min_value=0.0,
    max_value=200.0,
    value=88.0,
)

# ---------------------------------------------------------
# 3. LÓGICA DE FACTOR DE AJUSTE SEGÚN LAS 06:00 AM
# ---------------------------------------------------------
# Si amaneció por debajo del 75%, calculamos un factor restrictivo de caudal (< 1.0)
# para obligar a la red a restringir caudal y recuperar nivel.
factor_condicion_matutina = 1.0
if almacenamiento_06am_pct < META_AMANECER_PCT:
    # Factor proporcional al déficit matutino
    factor_condicion_matutina = max(
        0.75, almacenamiento_06am_pct / META_AMANECER_PCT
    )

# Aplicar el factor a las bandas de caudal objetivo del día
df_curva_base["Caudal_Min_Ajustado"] = (
    df_curva_base["Caudal_Min"] * factor_condicion_matutina
)
df_curva_base["Caudal_Prom_Ajustado"] = (
    df_curva_base["Caudal_Prom"] * factor_condicion_matutina
)
df_curva_base["Caudal_Max_Ajustado"] = (
    df_curva_base["Caudal_Max"] * factor_condicion_matutina
)

# Extraer los rangos teóricos ajustados para la hora actual
fila_ref = df_curva_base[df_curva_base["Hora"] == hora_actual].iloc[0]
c_min_permitido = fila_ref["Caudal_Min_Ajustado"]
c_max_permitido = fila_ref["Caudal_Max_Ajustado"]
c_obj_esperado = fila_ref["Caudal_Prom_Ajustado"]

# Validar si el caudal actual está dentro del rango permitido
caudal_en_rango = (c_min_permitido <= caudal_distribucion_actual) and (
    caudal_distribucion_actual <= c_max_permitido
)

# Cálculos de volumen actual
volumen_almacenado_actual = sum(niveles_actuales_ingresados.values())
pct_almacenamiento_actual = (
    volumen_almacenado_actual / VOLUMEN_TOTAL_SISTEMA
) * 100.0

# ---------------------------------------------------------
# 4. DASHBOARD EJECUTIVO PRINCIPAL
# ---------------------------------------------------------
st.subheader(
    f"📊 Tablero de Control y Validación — Corte Hora: {hora_actual:02d}:00 hrs"
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🌅 Almacenamiento a las 06:00 a.m.",
        value=f"{almacenamiento_06am_pct:.1f}%",
        delta=(
            "Cumple Meta (≥ 75%)"
            if almacenamiento_06am_pct >= META_AMANECER_PCT
            else "Déficit Matutino"
        ),
        delta_value=(
            "normal"
            if almacenamiento_06am_pct >= META_AMANECER_PCT
            else "inverse"
        ),
    )

with col2:
    st.metric(
        label="💧 Almacenamiento Actual",
        value=f"{pct_almacenamiento_actual:.1f}%",
        delta=f"Volumen: {volumen_almacenado_actual:,.0f} m³",
    )

with col3:
    estado_caudal_txt = (
        "🟢 Dentro de Rango" if caudal_en_rango else "🔴 Fuera de Rango"
    )
    st.metric(
        label="⚡ Caudal de Distribución Actual",
        value=f"{caudal_distribucion_actual:.1f} L/s",
        delta=f"Rango: [{c_min_permitido:.1f} - {c_max_permitido:.1f}] L/s",
        delta_value="normal" if caudal_en_rango else "inverse",
    )

with col4:
    if almacenamiento_06am_pct >= META_AMANECER_PCT and caudal_en_rango:
        st.metric(label="Estado Operativo", value="🟢 Operación Normal")
    else:
        st.metric(label="Estado Operativo", value="🟠 Requiere Restricción")

st.divider()

# ---------------------------------------------------------
# 5. ANÁLISIS DE RANGOS Y ALERTA DE CAUDAL
# ---------------------------------------------------------
if not caudal_en_rango:
    if caudal_distribucion_actual > c_max_permitido:
        st.error(
            f"⚠️ **Alerta de Sobredistribución:** El caudal actual ({caudal_distribucion_actual} L/s) está **por encima del límite máximo permitido ({c_max_permitido:.1f} L/s)** "
            f"para las condiciones de almacenamiento de hoy. Debes reducir la apertura de válvulas para evitar vaciamiento crítico."
        )
    else:
        st.info(
            f"ℹ️ **Subdistribución:** El caudal actual ({caudal_distribucion_actual} L/s) está por debajo del mínimo de la banda ({c_min_permitido:.1f} L/s)."
        )
else:
    st.success(
        "✅ El caudal de distribución actual se encuentra perfectamente dentro de la banda operativa recomendada según el balance matutino."
    )

# ---------------------------------------------------------
# 6. GRÁFICO DE BANDAS DE CAUDAL Y CURVA OBJETIVO
# ---------------------------------------------------------
st.subheader(
    "📈 Bandas Operativas de Caudal (Ajustadas por la Condición de las 06:00 a.m.)"
)

fig = go.Figure()

# Banda sombreada de operación permitida (Min - Max)
fig.add_trace(
    go.Scatter(
        x=horas_dia + horas_dia[::-1],
        y=list(df_curva_base["Caudal_Max_Ajustado"])
        + list(df_curva_base["Caudal_Min_Ajustado"])[::-1],
        fill="toself",
        fillcolor="rgba(0, 100, 255, 0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="Banda Operativa Permitida",
    )
)

# Línea del caudal objetivo ajustado
fig.add_trace(
    go.Scatter(
        x=df_curva_base["Hora"],
        y=df_curva_base["Caudal_Prom_Ajustado"],
        mode="lines+markers",
        name="Caudal Objetivo Ajustado (L/s)",
        line=dict(color="blue", width=2),
    )
)

# Punto de la hora actual real
fig.add_trace(
    go.Scatter(
        x=[hora_actual],
        y=[caudal_distribucion_actual],
        mode="markers",
        name="Caudal Real Operando",
        marker=dict(
            color="red" if not caudal_en_rango else "green", size=14, symbol="star"
        ),
    )
)

fig.update_layout(
    xaxis_title="Hora del Día (Hrs)",
    yaxis_title="Caudal de Distribución (L/s)",
    template="plotly_white",
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 7. TABLA DE CONSIGNAS HORARIAS
# ---------------------------------------------------------
st.subheader("📋 Consignas de Caudal Permitido para el Resto del Día")
st.dataframe(
    df_curva_base[df_curva_base["Hora"] >= hora_actual][
        [
            "Hora",
            "Caudal_Min_Ajustado",
            "Caudal_Prom_Ajustado",
            "Caudal_Max_Ajustado",
        ]
    ].rename(
        columns={
            "Caudal_Min_Ajustado": "Caudal Mínimo (L/s)",
            "Caudal_Prom_Ajustado": "Caudal Objetivo (L/s)",
            "Caudal_Max_Ajustado": "Caudal Máximo (L/s)",
        }
    ),
    use_container_width=True,
)
