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
    "💧 Sistema SCADA Operativo y Proyección — Aguas de Cartagena S.A. E.S.P."
)
st.markdown(
    "Monitoreo avanzado, carga externa de plantillas, curvas suavizadas, calendario histórico y control de presiones por horas."
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
            "Produccion_Planta_m3d",
            "Almacenamiento_06am_Pct",
            "Nivel_Colinas_cm",
            "Nivel_Carmelo_cm",
            "Nivel_Tk1_Planta_cm",
            "Nivel_Tk2_Planta_cm",
            "Nivel_TkNar2_cm",
            "Nivel_SuccionA_TkColinas_cm",
            "Nivel_Tk_Lomas_cm",
            "Caudal_Real_m3h",
            "Presion_Ref_Red_Tk_Colinas",
            "Presion_Sector10_Elevado_Colinas",
            "PresBomb_Znnorte_a_TkPzuela",
            "Presion_Ent_ZonaNorte",
            "Presion_Pcanoas",
            "Pres_Blezo",
            "Presion_Chile",
            "Pres_Consulado",
            "Presion_Bgrande",
            "Presion_Bgrande_Kra7",
            "Presion_Alcibia",
            "Presion_Piepopa",
            "Pres_Pic",
            "Pres_FPOPA",
            "Presion_Olaya_Cjust",
            "Presion_Fredonia",
            "Pres_Ref_Bombeo_LaVictoria",
            "Pres_Mop",
            "Pres_Royalco",
            "Presion_Bellavista_Agua_Potable",
            "Presión_Salida_EBAP_CERRO",
            "Almacenamiento_Sistema_Pct",
            "Estado_Operativo",
        ])


# ---------------------------------------------------------
# 2. CONFIGURACIÓN DE TANQUES Y NIVELES MÁXIMOS
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

horas_format = {
    h: (
        f"{h if h<=12 else h-12:02d}:00 "
        f"{'a. m.' if h<12 else 'p. m.'}"
        if h != 0
        else "12:00 a. m."
    )
    for h in horas_dia
}

# ---------------------------------------------------------
# 3. PANEL LATERAL: PARÁMETROS Y CARGA DE DOCUMENTO EXTERNO
# ---------------------------------------------------------
st.sidebar.header("🎛️ Parámetros y Carga Externa")

fecha_actual = st.sidebar.date_input(
    "Fecha de Operación", value=datetime.today()
)

produccion_planta_m3d = st.sidebar.selectbox(
    "Producción Diaria de Planta (m³/día)",
    options=[253000.0, 255000.0, 272000.0],
    index=1,
)

almacenamiento_06am_pct = st.sidebar.number_input(
    "% Almacenamiento real (06:00 a.m.)",
    min_value=0.0,
    max_value=100.0,
    value=72.0,
    step=0.5,
)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Cargar Plantilla Externa (Excel / CSV)")
archivo_subido = st.sidebar.file_uploader(
    "Sube tu archivo con los datos del día", type=["csv", "xlsx"]
)

# Procesar archivo externo si se carga
df_externo = None
if archivo_subido is not None:
    try:
        if archivo_subido.name.endswith(".csv"):
            df_externo = pd.read_csv(archivo_subido)
        else:
            df_externo = pd.read_excel(archivo_subido)
        st.sidebar.success(
            "✅ ¡Plantilla externa cargada con éxito! Puedes sincronizarla abajo."
        )
    except Exception as e:
        st.sidebar.error(f"Error al leer el archivo: {e}")

st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ Hora de Consulta Actual")
hora_actual = st.sidebar.selectbox(
    "Seleccione la hora del turno a registrar",
    options=horas_dia,
    format_func=lambda x: horas_format[x],
    index=7,
)

# ---------------------------------------------------------
# 4. GENERACIÓN DE CURVAS BASE DINÁMICAS
# ---------------------------------------------------------
perfil_horario_prom = [
    0.024,
    0.022,
    0.020,
    0.020,
    0.022,
    0.030,
    0.042,
    0.050,
    0.054,
    0.048,
    0.044,
    0.042,
    0.042,
    0.044,
    0.050,
    0.054,
    0.057,
    0.053,
    0.044,
    0.038,
    0.032,
    0.028,
    0.025,
    0.023,
]
caudal_prom_ref = [p * produccion_planta_m3d for p in perfil_horario_prom]
caudal_min_ref = [c * 0.85 for c in caudal_prom_ref]
caudal_max_ref = [c * 1.15 for c in caudal_prom_ref]
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

df_curva_base = pd.DataFrame({
    "Hora": horas_dia,
    "Almacenamiento_Ideal_Pct": almacenamiento_ideal_ref,
    "Caudal_Min": caudal_min_ref,
    "Caudal_Prom": caudal_prom_ref,
    "Caudal_Max": caudal_max_ref,
})

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

# ---------------------------------------------------------
# 5. MÓDULO DE INGRESO OPERATIVO (MANUAL O CARGA EXTERNA MASIVA)
# ---------------------------------------------------------
st.markdown(
    f"### 📥 Registro Operativo — Fecha: {fecha_actual} | Hora: {horas_format[hora_actual]}"
)

# Opción de volcado masivo si hay archivo externo cargado
if df_externo is not None:
    if st.button(
        "⚡ Volcar y Sincronizar Todo el Archivo Externo al Histórico del Día",
        type="secondary",
    ):
        try:
            df_hist = cargar_historico()
            # Aseguramos formato estándar en las columnas del archivo externo antes de volcarlo
            df_hist = pd.concat(
                [df_hist, df_externo], ignore_index=True
            ).drop_duplicates(subset=["Fecha", "Hora"], keep="last")
            df_hist.to_csv(HISTORICO_FILE, index=False)
            st.success(
                "✅ ¡Todos los registros del archivo externo fueron volcados e integrados al histórico exitosamente!"
            )
        except Exception as e:
            st.error(
                f"Error al procesar el volcado masivo. Verifica que las columnas coincidan: {e}"
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
        max_value=30000.0,
        value=float(
            df_curva_base[df_curva_base["Hora"] == hora_actual][
                "Caudal_Prom_Ajustado"
            ].values[0]
        ),
        step=100.0,
        key="input_caudal_real",
    )

    st.markdown(
        f"##### 🗜️ Control de Presiones (mca) — {horas_format[hora_actual]}"
    )
    with st.expander(
        "Desplegar Variables de Presión por Sistema", expanded=True
    ):
        p_colinas = st.number_input(
            "Presion_Ref_Red_Tk_Colinas",
            min_value=0.0,
            max_value=50.0,
            value=0.9,
            step=0.1,
        )
        p_sec10 = st.number_input(
            "Presion_Sector10_Elevado_Colinas",
            min_value=0.0,
            max_value=50.0,
            value=1.6,
            step=0.1,
        )
        p_pzuela = st.number_input(
            "PresBomb_Znnorte_a_TkPzuela",
            min_value=0.0,
            max_value=50.0,
            value=7.4,
            step=0.1,
        )
        p_znorte = st.number_input(
            "Presion_Ent_ZonaNorte",
            min_value=0.0,
            max_value=50.0,
            value=1.4,
            step=0.1,
        )
        p_pcanoas = st.number_input(
            "Presion_Pcanoas",
            min_value=0.0,
            max_value=50.0,
            value=2.2,
            step=0.1,
        )
        p_blezo = st.number_input(
            "Pres_Blezo", min_value=0.0, max_value=50.0, value=3.0, step=0.1
        )
        p_chile = st.number_input(
            "Presion_Chile", min_value=0.0, max_value=50.0, value=1.4, step=0.1
        )
        p_consulado = st.number_input(
            "Pres_Consulado",
            min_value=0.0,
            max_value=50.0,
            value=1.9,
            step=0.1,
        )
        p_bgrande = st.number_input(
            "Presion_Bgrande",
            min_value=0.0,
            max_value=50.0,
            value=1.4,
            step=0.1,
        )
        p_bgrande7 = st.number_input(
            "Presion_Bgrande_Kra7",
            min_value=0.0,
            max_value=50.0,
            value=1.4,
            step=0.1,
        )
        p_alcibia = st.number_input(
            "Presion_Alcibia",
            min_value=0.0,
            max_value=50.0,
            value=1.4,
            step=0.1,
        )
        p_piepopa = st.number_input(
            "Presion_Piepopa",
            min_value=0.0,
            max_value=50.0,
            value=1.7,
            step=0.1,
        )
        p_pic = st.number_input(
            "Pres_Pic", min_value=0.0, max_value=50.0, value=1.8, step=0.1
        )
        p_fpopa = st.number_input(
            "Pres_FPOPA", min_value=0.0, max_value=50.0, value=7.8, step=0.1
        )
        p_olaya = st.number_input(
            "Presion_Olaya_Cjust",
            min_value=0.0,
            max_value=50.0,
            value=2.6,
            step=0.1,
        )
        p_fredonia = st.number_input(
            "Presion_Fredonia",
            min_value=0.0,
            max_value=50.0,
            value=1.0,
            step=0.1,
        )
        p_victoria = st.number_input(
            "Pres_Ref_Bombeo_LaVictoria",
            min_value=0.0,
            max_value=50.0,
            value=2.4,
            step=0.1,
        )
        p_mop = st.number_input(
            "Pres_Mop", min_value=0.0, max_value=50.0, value=1.9, step=0.1
        )
        p_royalco = st.number_input(
            "Pres_Royalco", min_value=0.0, max_value=50.0, value=2.7, step=0.1
        )
        p_bellavista = st.number_input(
            "Presion_Bellavista_Agua_Potable",
            min_value=0.0,
            max_value=50.0,
            value=1.5,
            step=0.1,
        )
        p_cerro = st.number_input(
            "Presión Salida EBAP CERRO",
            min_value=0.0,
            max_value=50.0,
            value=5.4,
            step=0.1,
        )

    guardar_registro = st.button(
        "💾 Guardar / Registrar Hora en Histórico", type="primary"
    )

# ---------------------------------------------------------
# 6. CÁLCULOS TÉCNICOS Y VALIDACIÓN
# ---------------------------------------------------------
pct_almacenamiento_actual = 0.0
for tanque, cm_val in niveles_cm_ingresados.items():
    alt_max = ALTURAS_MAXIMAS_TANQUES[tanque]
    peso = FACTORES_PONDERACION[tanque]
    fraccion_tanque = min(1.0, cm_val / alt_max)
    pct_almacenamiento_actual += fraccion_tanque * peso * 100.0

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
        "Produccion_Planta_m3d": produccion_planta_m3d,
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
        "Presion_Ref_Red_Tk_Colinas": p_colinas,
        "Presion_Sector10_Elevado_Colinas": p_sec10,
        "PresBomb_Znnorte_a_TkPzuela": p_pzuela,
        "Presion_Ent_ZonaNorte": p_znorte,
        "Presion_Pcanoas": p_pcanoas,
        "Pres_Blezo": p_blezo,
        "Presion_Chile": p_chile,
        "Pres_Consulado": p_consulado,
        "Presion_Bgrande": p_bgrande,
        "Presion_Bgrande_Kra7": p_bgrande7,
        "Presion_Alcibia": p_alcibia,
        "Presion_Piepopa": p_piepopa,
        "Pres_Pic": p_pic,
        "Pres_FPOPA": p_fpopa,
        "Presion_Olaya_Cjust": p_olaya,
        "Presion_Fredonia": p_fredonia,
        "Pres_Ref_Bombeo_LaVictoria": p_victoria,
        "Pres_Mop": p_mop,
        "Pres_Royalco": p_royalco,
        "Presion_Bellavista_Agua_Potable": p_bellavista,
        "Presión_Salida_EBAP_CERRO": p_cerro,
        "Almacenamiento_Sistema_Pct": round(pct_almacenamiento_actual, 2),
        "Estado_Operativo": estado_op_str,
    }
    df_hist = df_hist[
        ~(
            (df_hist["Fecha"] == str(fecha_actual))
            & (df_hist["Hora"] == f"{hora_actual:02d}:00")
        )
    ]
    df_hist = pd.concat(
        [df_hist, pd.DataFrame([nuevo_registro])], ignore_index=True
    )
    df_hist.to_csv(HISTORICO_FILE, index=False)
    st.success(
        f"✅ ¡Registro guardado exitosamente en el histórico para el {fecha_actual} a las {horas_format[hora_actual]}!"
    )

# ---------------------------------------------------------
# 7. TABLERO DE CONTROL EJECUTIVO (KPIs)
# ---------------------------------------------------------
st.divider()
st.subheader(
    f"📊 Indicadores de Contraste — Corte {horas_format[hora_actual]}"
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
    prom_presion = np.mean(
        [p_colinas, p_sec10, p_pzuela, p_blezo, p_pic, p_cerro]
    )
    st.metric(
        label="🗜️ Presión Promedio Red",
        value=f"{prom_presion:.1f} mca",
        delta="Sensores Activos OK",
    )

# ---------------------------------------------------------
# 8. DASHBOARD GRÁFICO CON CURVAS SUAVIZADAS Y CALENDARIO
# ---------------------------------------------------------
st.divider()
st.subheader(
    "📈 Dashboard Gráfico: Tendencias Suavizadas, Contraste y Proyección"
)

tab_g1, tab_g2, tab_g3, tab_g4 = st.tabs([
    "⚡ Tendencia y Proyección Caudal",
    "💧 Tendencia y Proyección Almacenamiento",
    "🗜️ Tendencia de Presiones (Plantilla SCADA)",
    "📅 Calendario Histórico",
])

df_hist_global = cargar_historico()
df_dia_actual = df_hist_global[df_hist_global["Fecha"] == str(fecha_actual)]

with tab_g1:
    fig_c = go.Figure()
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
    fig_c.add_trace(
        go.Scatter(
            x=df_curva_base["Hora"],
            y=df_curva_base["Caudal_Prom_Ajustado"],
            mode="lines",
            name="Caudal Objetivo (Meta)",
            line=dict(color="#0b3c5d", width=2, dash="dash", shape="spline"),
        )
    )

    if not df_dia_actual.empty:
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
                line=dict(color="#27ae60", width=3, shape="spline"),
                marker=dict(size=8),
            )
        )

        ultima_hora_reg = df_dia_ordenado["Hora_Int"].max()
        if ultima_hora_reg < 23:
            horas_proy = list(range(int(ultima_hora_reg), 24))
            ultimo_caudal = df_dia_ordenado[
                df_dia_ordenado["Hora_Int"] == ultima_hora_reg
            ]["Caudal_Real_m3h"].values[0]
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
                    line=dict(
                        color="#e67e22", width=3, dash="dot", shape="spline"
                    ),
                )
            )
    else:
        fig_c.add_trace(
            go.Scatter(
                x=[hora_actual],
                y=[caudal_distribucion_actual],
                mode="markers+text",
                name="Caudal Operando (Actual)",
                text=[f"{caudal_distribucion_actual:,.0f} m³/h"],
                textposition="top center",
                marker=dict(color="#2ecc71", size=14, symbol="diamond"),
            )
        )

    fig_c.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=horas_dia,
            ticktext=[horas_format[h] for h in horas_dia],
        ),
        xaxis_title="Hora del Día",
        yaxis_title="Caudal (m³/h)",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig_c, use_container_width=True)

with tab_g2:
    fig_s = go.Figure()
    fig_s.add_trace(
        go.Scatter(
            x=df_curva_base["Hora"],
            y=df_curva_base["Almacenamiento_Ideal_Pct"],
            mode="lines",
            name="Curva Meta Almacenamiento (%)",
            line=dict(color="#2980b9", width=3, shape="spline"),
        )
    )

    if not df_dia_actual.empty:
        df_dia_ordenado = df_dia_actual.copy()
        df_dia_ordenado["Hora_Int"] = df_dia_ordenado["Hora"].apply(
            lambda x: int(x.split(":")[0])
        )
        df_dia_ordenado = df_dia_ordenado.sort_values("Hora_Int")

        fig_s.add_trace(
            go.Scatter(
                x=df_dia_ordenado["Hora_Int"],
                y=df_dia_ordenado["Almacenamiento_Sistema_Pct"],
                mode="lines+markers",
                name="Almacenamiento Real Transcurrido",
                line=dict(color="#27ae60", width=3, shape="spline"),
                marker=dict(size=8),
            )
        )

        ultima_hora_reg = df_dia_ordenado["Hora_Int"].max()
        if ultima_hora_reg < 23:
            horas_proy = list(range(int(ultima_hora_reg), 24))
            ultimo_alm = df_dia_ordenado[
                df_dia_ordenado["Hora_Int"] == ultima_hora_reg
            ]["Almacenamiento_Sistema_Pct"].values[0]
            meta_final_dia = 75.0

            almacenamientos_proyectados = np.linspace(
                ultimo_alm, meta_final_dia, len(horas_proy)
            )

            fig_s.add_trace(
                go.Scatter(
                    x=horas_proy,
                    y=almacenamientos_proyectados,
                    mode="lines",
                    name="Proyección Resto del Día (Hacia Meta 75%)",
                    line=dict(
                        color="#e67e22", width=3, dash="dot", shape="spline"
                    ),
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
        xaxis=dict(
            tickmode="array",
            tickvals=horas_dia,
            ticktext=[horas_format[h] for h in horas_dia],
        ),
        xaxis_title="Hora del Día",
        yaxis_title="Almacenamiento Sistema (%)",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig_s, use_container_width=True)

with tab_g3:
    st.markdown(
        "### 🗜️ Tendencia Horaria de Presiones (Plantilla SCADA - mca)"
    )
    if not df_dia_actual.empty:
        fig_p = go.Figure()
        df_p_ord = df_dia_actual.copy()
        df_p_ord["Hora_Int"] = df_p_ord["Hora"].apply(
            lambda x: int(x.split(":")[0])
        )
        df_p_ord = df_p_ord.sort_values("Hora_Int")

        columnas_presiones = [
            c for c in df_p_ord.columns if "Pres" in c or "Presión" in c
        ]
        for col_p in columnas_presiones:
            fig_p.add_trace(
                go.Scatter(
                    x=df_p_ord["Hora_Int"],
                    y=df_p_ord[col_p],
                    mode="lines+markers",
                    name=col_p,
                    line=dict(width=2, shape="spline"),
                )
            )

        fig_p.update_layout(
            xaxis=dict(
                tickmode="array",
                tickvals=horas_dia,
                ticktext=[horas_format[h] for h in horas_dia],
            ),
            xaxis_title="Hora del Día",
            yaxis_title="Presión (mca)",
            template="plotly_white",
        )
        st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.info(
            "Registra al menos una hora en el histórico para visualizar las curvas de presión de la plantilla."
        )

with tab_g4:
    st.markdown("### 📅 Calendario Histórico de Operación")
    if not df_hist_global.empty:
        fechas_unicas = sorted(df_hist_global["Fecha"].unique())
        fecha_calendario = st.selectbox(
            "Seleccione la fecha a consultar en el histórico",
            options=fechas_unicas,
            index=len(fechas_unicas) - 1,
        )

        df_fecha_sel = df_hist_global[
            df_hist_global["Fecha"] == fecha_calendario
        ]
        st.markdown(f"**Registros para la fecha: {fecha_calendario}**")
        st.dataframe(df_fecha_sel, use_container_width=True)
    else:
        st.info("Aún no hay fechas registradas en el archivo histórico.")

# ---------------------------------------------------------
# 10. DETALLE DE TANQUES
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
