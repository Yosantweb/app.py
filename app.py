import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Control Operativo - Aguas de Cartagena",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilo corporativo sobrio
st.markdown(
    """
    <style>
        .reportview-container { background: #f0f2f6; }
        .sidebar .sidebar-content { background: #f8f9fa; }
        h1, h2, h3 { color: #0b3c5d; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title(
    "💧 Sistema de Control y Proyección de Niveles — Aguas de Cartagena S.A. E.S.P."
)
st.markdown(
    "Monitoreo de tanques estratégicos en centímetros, validación de bandas de caudal según almacenamiento a las 06:00 a.m. y control operativo."
)

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE TANQUES Y NIVELES MÁXIMOS (en centímetros)
# ---------------------------------------------------------
# Basado en las capacidades/alturas máximas operativas habituales de la red
ALTURAS_MAXIMAS_TANQUES = {
    "Nivel_Colinas": 450.0,  # cm
    "Nivel_Carmelo": 400.0,  # cm
    "Nivel_Tk1_Planta": 300.0,  # cm
    "Nivel_Tk2_Planta": 300.0,  # cm
    "Nivel_TkNar2": 500.0,  # cm
    "Nivel_SuccionA_TkColinas": 350.0,  # cm
    "Nivel_Tk_Lomas": 400.0,  # cm
}

# Pesos o capacidades relativas para estimar el porcentaje global del sistema a partir de los niveles en cm
# (Equivalente al consolidado de almacenamiento)
FACTORES_PONDERACION = {
    "Nivel_Colinas": 0.40,
    "Nivel_Carmelo": 0.15,
    "Nivel_Tk1_Planta": 0.10,
    "Nivel_Tk2_Planta": 0.10,
    "Nivel_TkNar2": 0.15,
    "Nivel_SuccionA_TkColinas": 0.05,
    "Nivel_Tk_Lomas": 0.05,
}

META_AMANECER_PCT = 75.0  # Regla de oro: 75% a las 06:00 a.m.

# Horas del día (00:00 a 23:00)
horas_dia = list(range(24))

# Curvas de referencia base del sistema (Ideal y Bandas de Caudal)
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
# 2. PANEL LATERAL: CONFIGURACIÓN GENERAL DEL TURNO
# ---------------------------------------------------------
st.sidebar.header("🎛️ Parámetros del Turno")

# Validación Matutina Obligatoria
st.sidebar.subheader("🌅 Condición a las 06:00 a.m.")
almacenamiento_06am_pct = st.sidebar.number_input(
    "% Almacenamiento real (06:00 a.m.)",
    min_value=0.0,
    max_value=100.0,
    value=72.0,
    step=0.5,
)

st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ Hora de Consulta Actual")
hora_actual = st.sidebar.selectbox(
    "Seleccione la hora del turno a registrar", options=horas_dia, index=8
)

# ---------------------------------------------------------
# 3. MÓDULO DE ACTUALIZACIÓN DE NIVELES EN CENTÍMETROS POR HORA
# ---------------------------------------------------------
st.subheader(
    f"📥 Registro de Niveles (cm) y Caudal — Hora de Corte: {hora_actual:02d}:00 hrs"
)
st.markdown(
    "Ingrese los niveles leídos en pantalla en **centímetros (cm)** para cada tanque y el caudal de distribución real:"
)

col_ingreso1, col_ingreso2 = st.columns([2, 1])

niveles_cm_ingresados = {}

with col_ingreso1:
    st.markdown("##### 📏 Lectura de Niveles en Tanques (cm)")
    t_cols = st.columns(2)
    idx = 0
    for tanque, alt_max in ALTURAS_MAXIMAS_TANQUES.items():
        # Valor sugerido basado en la curva ideal teórica convertida a cm
        pct_sugerido = (
            df_curva_base[df_curva_base["Hora"] == hora_actual][
                "Almacenamiento_Ideal_Pct"
            ].values[0]
            / 100.0
        )
        val_cm_sugerido = alt_max * pct_sugerido * 0.9

        with t_cols[idx % 2]:
            niveles_cm_ingresados[tanque] = st.number_input(
                f"{tanque.replace('Nivel_', '')} (Máx: {alt_max:,.0f} cm)",
                min_value=0.0,
                max_value=alt_max * 1.1,
                value=float(val_cm_sugerido),
                step=1.0,
            )
        idx += 1

with col_ingreso2:
    st.markdown("##### ⚡ Operación de Red")
    caudal_distribucion_actual = st.number_input(
        "Caudal Distribución Real (L/s)",
        min_value=0.0,
        max_value=200.0,
        value=85.0,
        step=1.0,
    )
    st.info(
        "💡 El caudal se evalúa frente a los rangos permitidos según el almacenamiento matutino."
    )

# ---------------------------------------------------------
# 4. LÓGICA Y CÁLCULOS TÉCNICOS (CONVERSIÓN DE CM A %)
# ---------------------------------------------------------
# Calcular el porcentaje de almacenamiento global ponderado a partir de los centímetros de cada tanque
pct_almacenamiento_actual = 0.0
for tanque, cm_val in niveles_cm_ingresados.items():
    alt_max = ALTURAS_MAXIMAS_TANQUES[tanque]
    peso = FACTORES_PONDERACION[tanque]
    # Ocupación fraccional del tanque
    fraccion_tanque = min(1.0, cm_val / alt_max)
    pct_almacenamiento_actual += fraccion_tanque * peso * 100.0

# Factor de ajuste según el almacenamiento a las 06:00 a.m.
factor_condicion_matutina = 1.0
if almacenamiento_06am_pct < META_AMANECER_PCT:
    factor_condicion_matutina = max(
        0.75, almacenamiento_06am_pct / META_AMANECER_PCT
    )

df_curva_base["Caudal_Min_Ajustado"] = (
    df_curva_base["Caudal_Min"] * factor_condicion_matutina
)
df_curva_base["Caudal_Prom_Ajustado"] = (
    df_curva_base["Caudal_Prom"] * factor_condicion_matutina
)
df_curva_base["Caudal_Max_Ajustado"] = (
    df_curva_base["Caudal_Max"] * factor_condicion_matutina
)

fila_ref = df_curva_base[df_curva_base["Hora"] == hora_actual].iloc[0]
c_min_permitido = fila_ref["Caudal_Min_Ajustado"]
c_max_permitido = fila_ref["Caudal_Max_Ajustado"]

caudal_en_rango = (c_min_permitido <= caudal_distribucion_actual) and (
    caudal_distribucion_actual <= c_max_permitido
)

# ---------------------------------------------------------
# 5. TABLERO DE CONTROL EJECUTIVO (KPIs)
# ---------------------------------------------------------
st.divider()
st.subheader(
    f"📊 Indicadores de Gestión del Sistema — Corte {hora_actual:02d}:00 hrs"
)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    delta_am_txt = (
        "Cumple Meta (≥ 75%)"
        if almacenamiento_06am_pct >= META_AMANECER_PCT
        else "Déficit Matutino"
    )
    col_am = "normal" if almacenamiento_06am_pct >= META_AMANECER_PCT else "inverse"
    st.metric(
        label="🌅 Almacenamiento 06:00 a.m.",
        value=f"{almacenamiento_06am_pct:.1f}%",
        delta=delta_am_txt,
        delta_color=col_am,
    )

with kpi2:
    st.metric(
        label="💧 Almacenamiento Sistema",
        value=f"{pct_almacenamiento_actual:.1f}%",
        delta="Calculado por Niveles (cm)",
    )

with kpi3:
    col_cau = "normal" if caudal_en_rango else "inverse"
    st.metric(
        label="⚡ Caudal Operando",
        value=f"{caudal_distribucion_actual:.1f} L/s",
        delta=f"Rango: [{c_min_permitido:.1f} - {c_max_permitido:.1f}] L/s",
        delta_color=col_cau,
    )

with kpi4:
    estado_op = (
        "🟢 Normal / Seguro"
        if (almacenamiento_06am_pct >= META_AMANECER_PCT and caudal_en_rango)
        else "🟠 Requiere Ajuste"
    )
    st.metric(label="Estado Operativo", value=estado_op)

# ---------------------------------------------------------
# 6. GRÁFICO DE CONTROL DE CAUDAL Y COMPARACIÓN
# ---------------------------------------------------------
st.divider()
st.subheader(
    "📈 Validación de Caudal Real vs. Bandas Operativas del Día (Ajustadas)"
)

fig = go.Figure()

# Banda operativa permitida
fig.add_trace(
    go.Scatter(
        x=horas_dia + horas_dia[::-1],
        y=list(df_curva_base["Caudal_Max_Ajustado"])
        + list(df_curva_base["Caudal_Min_Ajustado"])[::-1],
        fill="toself",
        fillcolor="rgba(11, 60, 93, 0.1)",
        line=dict(color="rgba(255,255,255,0)"),
        name="Banda Operativa Permitida",
    )
)

# Caudal objetivo
fig.add_trace(
    go.Scatter(
        x=df_curva_base["Hora"],
        y=df_curva_base["Caudal_Prom_Ajustado"],
        mode="lines",
        name="Caudal Objetivo (Promedio)",
        line=dict(color="#0b3c5d", width=2, dash="dash"),
    )
)

# Punto registrado por el operador en la hora actual
fig.add_trace(
    go.Scatter(
        x=[hora_actual],
        y=[caudal_distribucion_actual],
        mode="markers+text",
        name="Caudal Registrado (Turno)",
        text=[f"{caudal_distribucion_actual} L/s"],
        textposition="top center",
        marker=dict(
            color="#2ecc71" if caudal_en_rango else "#e74c3c",
            size=16,
            symbol="diamond",
        ),
    )
)

fig.update_layout(
    xaxis_title="Hora del Día (Hrs)",
    yaxis_title="Caudal de Distribución (L/s)",
    template="plotly_white",
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 7. RESUMEN DETALLADO POR TANQUE (EN CM)
# ---------------------------------------------------------
st.subheader("📋 Estado Detallado por Estación de Tanques (Niveles en cm)")
df_resumen_tanques = pd.DataFrame({
    "Estación / Tanque": list(ALTURAS_MAXIMAS_TANQUES.keys()),
    "Altura Máxima (cm)": list(ALTURAS_MAXIMAS_TANQUES.values()),
    "Nivel Registrado (cm)": list(niveles_cm_ingresados.values()),
})
df_resumen_tanques["% Ocupación"] = (
    df_resumen_tanques["Nivel Registrado (cm)"]
    / df_resumen_tanques["Altura Máxima (cm)"]
) * 100.0

st.dataframe(
    df_resumen_tanques.style.format({
        "Altura Máxima (cm)": "{:,.1f}",
        "Nivel Registrado (cm)": "{:,.1f}",
        "% Ocupación": "{:.1f}%",
    }),
    use_container_width=True,
)
