import os
from datetime import datetime
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
    "💧 Sistema de Control, Históricos y Proyección — Aguas de Cartagena S.A. E.S.P."
)
st.markdown(
    "Monitoreo de tanques en centímetros, bandas de caudal en **$m^3/h$**, trazabilidad de tendencia real y proyección operativa."
)

# ---------------------------------------------------------
# 1. ARCHIVO HISTÓRICO PERSISTENTE (CSV)
# ---------------------------------------------------------
HISTORICO_FILE = "historico_operativo.csv"


def cargar_historico():
    if os.path.exists(HISTORICO_FILE):
        return pd.read_csv(HISTORICO_FILE)
    else:
        return pd.DataFrame(columns=[
            "Fecha",
            "Hora",
            "Almacenamiento_06am_Pct",
            "Nivel_Colinas_cm",
            "Nivel_Carmelo_cm",
            "Nivel_Tk1_Planta_cm",
            "Nivel_Tk2_Planta_cm",
            "Nivel_TkNar2_cm",
            "Nivel_SuccionA_TkColinas_cm",
            "Nivel_Tk_Lomas_cm",
            "Caudal_Real_m3h",
            "Almacenamiento_Sistema_Pct",
            "Estado_Operativo",
        ])


# ---------------------------------------------------------
# 2. CONFIGURACIÓN DE TANQUES Y NIVELES MÁXIMOS (en centímetros)
# ---------------------------------------------------------
ALTURAS_MAXIMAS_TANQUES = {
    "Nivel_Colinas": 450.0,
    "Nivel_Carmelo": 400.0,
    "Nivel_Tk1_Planta": 300.0,
    "Nivel_Tk2_Planta": 300.0,
    "Nivel_TkNar2": 500.0,
    "Nivel_SuccionA_TkColinas": 350.0,
    "Nivel_Tk_Lomas": 400.0,
}

FACTORES_PONDERACION = {
    "Nivel_Colinas": 0.40,
    "Nivel_Carmelo": 0.15,
    "Nivel_Tk1_Planta": 0.10,
    "Nivel_Tk2_Planta": 0.10,
    "Nivel_TkNar2": 0.15,
    "Nivel_SuccionA_TkColinas": 0.05,
    "Nivel_Tk_Lomas": 0.05,
}

META_AMANECER_PCT = 75.0
horas_dia = list(range(24))

# Curvas de referencia teóricas base del día (Escala real del sistema hasta ~14,500 m3/h)
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
    5000,
    4500,
    4000,
    4000,
    4500,
    6000,
    9000,
    11000,
    12000,
    10500,
    9500,
    9000,
    9000,
    9500,
    11000,
    12000,
    12500,
    11500,
    9500,
    8000,
    6500,
    5500,
    5000,
    4500,
]
caudal_prom_ref = [
    6000,
    5500,
    5000,
    5000,
    5500,
    7500,
    11000,
    13000,
    14000,
    12500,
    11500,
    11000,
    11000,
    11500,
    13000,
    14000,
    14500,
    13500,
    11000,
    9500,
    8000,
    7000,
    6500,
    6000,
]
caudal_max_ref = [
    7000,
    6500,
    6000,
    6000,
    6500,
    9000,
    13000,
    15000,
    16000,
    14500,
    13500,
    13000,
    13000,
    13500,
    15000,
    16000,
    16500,
    15500,
    13000,
    11000,
    9500,
    8500,
    7500,
    7000,
]

df_curva_base = pd.DataFrame({
    "Hora": horas_dia,
    "Almacenamiento_Ideal_Pct": almacenamiento_ideal_ref,
    "Caudal_Min": caudal_min_ref,
    "Caudal_Prom": caudal_prom_ref,
    "Caudal_Max": caudal_max_ref,
})

# ---------------------------------------------------------
# 3. PANEL LATERAL: CONFIGURACIÓN GENERAL DEL TURNO
# ---------------------------------------------------------
st.sidebar.header("🎛️ Parámetros del Turno y Fecha")

fecha_actual = st.sidebar.date_input(
    "Fecha de Operación", value=datetime.today()
)

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
# 4. MÓDULO DE ACTUALIZACIÓN DE NIVELES (CM desde 0) Y CAUDAL (M3/H)
# ---------------------------------------------------------
st.markdown(
    f"### 📥 Registro Operativo — Fecha: {fecha_actual} | Hora: {hora_actual:02d}:00 hrs"
)

col_ingreso1, col_ingreso2 = st.columns([2, 1])

niveles_cm_ingresados = {}

with col_ingreso1:
    st.markdown("##### 📏 Lectura de Niveles en Tanques (cm)")
    t_cols = st.columns(2)
    idx = 0
    for tanque, alt_max in ALTURAS_MAXIMAS_TANQUES.items():
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
                key=f"input_{tanque}",
            )
        idx += 1

with col_ingreso2:
    st.markdown("##### ⚡ Operación de Red")
    caudal_distribucion_actual = st.number_input(
        "Caudal Distribución Real ($m^3/h$)",
        min_value=0.0,
        max_value=20000.0,
        value=12000.0,
        step=100.0,
        key="input_caudal_real",
    )

    guardar_registro = st.button(
        "💾 Guardar / Registrar Hora en Histórico", type="primary"
    )

# ---------------------------------------------------------
# 5. CÁLCULOS TÉCNICOS Y VALIDACIÓN
# ---------------------------------------------------------
pct_almacenamiento_actual = 0.0
for tanque, cm_val in niveles_cm_ingresados.items():
    alt_max = ALTURAS_MAXIMAS_TANQUES[tanque]
    peso = FACTORES_PONDERACION[tanque]
    fraccion_tanque = min(1.0, cm_val / alt_max)
    pct_almacenamiento_actual += fraccion_tanque * peso * 100.0

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
almacenamiento_meta_hora = fila_ref["Almacenamiento_Ideal_Pct"]

caudal_en_rango = (c_min_permitido <= caudal_distribucion_actual) and (
    caudal_distribucion_actual <= c_max_permitido
)
estado_op_str = (
    "Normal / Seguro"
    if (almacenamiento_06am_pct >= META_AMANECER_PCT and caudal_en_rango)
    else "Requiere Ajuste"
)

if guardar_registro:
    df_hist = cargar_historico()
    nuevo_registro = {
        "Fecha": str(fecha_actual),
        "Hora": f"{hora_actual:02d}:00",
        "Almacenamiento_06am_Pct": almacenamiento_06am_pct,
        "Nivel_Colinas_cm": niveles_cm_ingresados["Nivel_Colinas"],
        "Nivel_Carmelo_cm": niveles_cm_ingresados["Nivel_Carmelo"],
        "Nivel_Tk1_Planta_cm": niveles_cm_ingresados["Nivel_Tk1_Planta"],
        "Nivel_Tk2_Planta_cm": niveles_cm_ingresados["Nivel_Tk2_Planta"],
        "Nivel_TkNar2_cm": niveles_cm_ingresados["Nivel_TkNar2"],
        "Nivel_SuccionA_TkColinas_cm": niveles_cm_ingresados[
            "Nivel_SuccionA_TkColinas"
        ],
        "Nivel_Tk_Lomas_cm": niveles_cm_ingresados["Nivel_Tk_Lomas"],
        "Caudal_Real_m3h": caudal_distribucion_actual,
        "Almacenamiento_Sistema_Pct": round(pct_almacenamiento_actual, 2),
        "Estado_Operativo": estado_op_str,
    }
    df_hist = df_hist[
        ~((df_hist["Fecha"] == str(fecha_actual)) & (df_hist["Hora"] == f"{hora_actual:02d}:00"))
    ]
    df_hist = pd.concat(
        [df_hist, pd.DataFrame([nuevo_registro])], ignore_index=True
    )
    df_hist.to_csv(HISTORICO_FILE, index=False)
    st.success(
        f"✅ ¡Registro guardado exitosamente en el histórico para el {fecha_actual} a las {hora_actual:02d}:00 hrs!"
    )

# ---------------------------------------------------------
# 6. TABLERO DE CONTROL EJECUTIVO (KPIs)
# ---------------------------------------------------------
st.divider()
st.subheader(
    f"📊 Indicadores de Contraste — Corte {hora_actual:02d}:00 hrs"
)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        label="🌅 Almacenamiento 06:00 a.m.",
        value=f"{almacenamiento_06am_pct:.1f}%",
        delta="Meta ≥ 75%",
    )

with kpi2:
    delta_alm = pct_almacenamiento_actual - almacenamiento_meta_hora
    st.metric(
        label="💧 Almacenamiento Sistema",
        value=f"{pct_almacenamiento_actual:.1f}%",
        delta=f"{delta_alm:+.1f}% vs Meta ({almacenamiento_meta_hora}%)",
    )

with kpi3:
    st.metric(
        label="⚡ Caudal Operando",
        value=f"{caudal_distribucion_actual:,.1f} m³/h",
        delta=f"Rango: [{c_min_permitido:,.1f} - {c_max_permitido:,.1f}] m³/h",
    )

with kpi4:
    st.metric(
        label="Estado Operativo",
        value=(
            "🟢 Normal" if estado_op_str == "Normal / Seguro" else "🟠 Ajuste"
        ),
    )

# ---------------------------------------------------------
# 7. DASHBOARD GRÁFICO: LÍNEAS DE TENDENCIA Y PROYECCIÓN
# ---------------------------------------------------------
st.divider()
st.subheader(
    "📈 Dashboard Gráfico: Tendencia Operativa, Contraste y Proyección del Día"
)

tab_g1, tab_g2, tab_g3 = st.tabs([
    "⚡ Tendencia y Proyección de Caudal",
    "💧 Tendencia y Proyección de Almacenamiento",
    "📊 Histórico Operativo del Día",
])

# Cargar histórico actual para la fecha seleccionada
df_hist_global = cargar_historico()
df_dia_actual = df_hist_global[df_hist_global["Fecha"] == str(fecha_actual)]

with tab_g1:
    fig_c = go.Figure()
    # 1. Banda permitida
    fig_c.add_trace(
        go.Scatter(
            x=horas_dia + horas_dia[::-1],
            y=list(df_curva_base["Caudal_Max_Ajustado"])
            + list(df_curva_base["Caudal_Min_Ajustado"])[::-1],
            fill="toself",
            fillcolor="rgba(11, 60, 93, 0.1)",
            line=dict(color="rgba(255,255,255,0)"),
            name="Banda Permitida",
        )
    )
    # 2. Curva objetivo
    fig_c.add_trace(
        go.Scatter(
            x=df_curva_base["Hora"],
            y=df_curva_base["Caudal_Prom_Ajustado"],
            mode="lines",
            name="Caudal Objetivo (Meta)",
            line=dict(color="#0b3c5d", width=2, dash="dash"),
        )
    )

    # Si hay datos históricos guardados en el día, dibujamos la línea real transcurrida
    if not df_dia_actual.empty:
        # Ordenar por hora
        df_dia_ordenado = df_dia_actual.copy()
        df_dia_ordenado["Hora_Int"] = df_dia_ordenado["Hora"].apply(
            lambda x: int(x.split(":")[0])
        )
        df_dia_ordenado = df_dia_ordenado.sort_values("Hora_Int")

        fig_c.add_trace(
            go.Scatter(
                x=df_dia_ordenado["Hora_Int"],
                y=df_dia_ordenado["Caudal_Real_m3h"],
                mode="lines+markers",
                name="Tendencia Real Transcurrida",
                line=dict(color="#27ae60", width=3),
                marker=dict(size=8),
            )
        )

        # Proyección para el resto del día basada en el último dato registrado o actual
        ultima_hora_reg = df_dia_ordenado["Hora_Int"].max()
        if ultima_hora_reg < 23:
            horas_proy = list(
                range(int(ultima_hora_reg), 24)
            )  # Conectar desde el último punto
            ultimo_caudal = df_dia_ordenado[
                df_dia_ordenado["Hora_Int"] == ultima_hora_reg
            ]["Caudal_Real_m3h"].values[0]
            # Curva de proyección estimada hacia el objetivo del resto del día
            val_meta_final = df_curva_base[df_curva_base["Hora"] == 23][
                "Caudal_Prom_Ajustado"
            ].values[0]
            caudales_proyectados = np.linspace(
                ultimo_caudal, val_meta_final, len(horas_proy)
            )

            fig_c.add_trace(
                go.Scatter(
                    x=horas_proy,
                    y=caudales_proyectados,
                    mode="lines",
                    name="Proyección Resto del Día",
                    line=dict(color="#e67e22", width=3, dash="dot"),
                )
            )
    else:
        # Si no hay registros guardados aún, mostramos el punto actual interactivo
        fig_c.add_trace(
            go.Scatter(
                x=[hora_actual],
                y=[caudal_distribucion_actual],
                mode="markers+text",
                name="Caudal Operando (Actual)",
                text=[f"{caudal_distribucion_actual:,.0f} m³/h"],
                textposition="top center",
                marker=dict(
                    color="#2ecc71" if caudal_en_rango else "#e74c3c",
                    size=14,
                    symbol="diamond",
                ),
            )
        )

    fig_c.update_layout(
        xaxis_title="Hora del Día",
        yaxis_title="Caudal (m³/h)",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig_c, use_container_width=True)

with tab_g2:
    fig_s = go.Figure()
    # Curva meta de almacenamiento
    fig_s.add_trace(
        go.Scatter(
            x=df_curva_base["Hora"],
            y=df_curva_base["Almacenamiento_Ideal_Pct"],
            mode="lines",
            name="Curva Meta Almacenamiento (%)",
            line=dict(color="#2980b9", width=3),
        )
    )

    if not df_dia_actual.empty:
        df_dia_ordenado = df_dia_actual.copy()
        df_dia_ordenado["Hora_Int"] = df_dia_ordenado["Hora"].apply(
            lambda x: int(x.split(":")[0])
        )
        df_dia_ordenado = df_dia_ordenado.sort_values("Hora_Int")

        # Línea continua real transcurrida
        fig_s.add_trace(
            go.Scatter(
                x=df_dia_ordenado["Hora_Int"],
                y=df_dia_ordenado["Almacenamiento_Sistema_Pct"],
                mode="lines+markers",
                name="Almacenamiento Real Transcurrido",
                line=dict(color="#27ae60", width=3),
                marker=dict(size=8),
            )
        )

        # Proyección de almacenamiento para el resto del día hacia la meta del amanecer siguiente (75%)
        ultima_hora_reg = df_dia_ordenado["Hora_Int"].max()
        if ultima_hora_reg < 23:
            horas_proy = list(range(int(ultima_hora_reg), 24))
            ultimo_alm = df_dia_ordenado[
                df_dia_ordenado["Hora_Int"] == ultima_hora_reg
            ]["Almacenamiento_Sistema_Pct"].values[0]
            meta_final_dia = 75.0  # Meta del siguiente amanecer

            almacenamientos_proyectados = np.linspace(
                ultimo_alm, meta_final_dia, len(horas_proy)
            )

            fig_s.add_trace(
                go.Scatter(
                    x=horas_proy,
                    y=almacenamientos_proyectados,
                    mode="lines",
                    name="Proyección Resto del Día (Hacia Meta 75%)",
                    line=dict(color="#e67e22", width=3, dash="dot"),
                )
            )
    else:
        fig_s.add_trace(
            go.Scatter(
                x=[hora_actual],
                y=[pct_almacenamiento_actual],
                mode="markers+text",
                name="Almacenamiento Actual",
                text=[f"{pct_almacenamiento_actual:.1f}%"],
                textposition="top center",
                marker=dict(color="#e67e22", size=14, symbol="star"),
            )
        )

    fig_s.add_hline(
        y=META_AMANECER_PCT,
        line_dash="dot",
        line_color="red",
        annotation_text="Meta Amanecer 75%",
    )
    fig_s.update_layout(
        xaxis_title="Hora del Día",
        yaxis_title="Almacenamiento Sistema (%)",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig_s, use_container_width=True)

with tab_g3:
    st.markdown(
        f"### 🗂️ Trazabilidad y Comportamiento del Día: {fecha_actual}"
    )
    if not df_dia_actual.empty:
        st.dataframe(df_dia_actual, use_container_width=True)
    else:
        st.info(
            f"No hay registros guardados aún para la fecha {fecha_actual}. Usa el botón 'Guardar / Registrar Hora en Histórico' para acumular la tendencia horaria."
        )

# ---------------------------------------------------------
# 8. DETALLE DE TANQUES
# ---------------------------------------------------------
st.divider()
st.subheader("📋 Estado Actual de Niveles por Tanque (cm)")
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
