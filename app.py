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
    "Gemelo Digital Operativo: PTAP Bosque & Planta El Cerro, control acumulativo por horas y toma de decisiones."
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
            # Niveles tanques Bosque (cm)
            "Nivel_Tk1_Planta",
            "Nivel_Tk2_Planta",
            "Nivel_SuccionA_TkColinas",
            "Nivel_Colinas_Tk2",
            "Nivel_TkNar2",
            "Nivel_Tk_Lomas",
            "Nivel_Carmelo",
            # Planta El Cerro
            "EBAP_1_TP_LIT_001.PV",  # Nivel en metros
            "EBAP_1_OO_PIT_001.PV",  # Presión salida Cerro
            "Volumen_Cerro_m3",
            "Pct_Almacenamiento_Cerro",
            # Operación de red
            "Caudal_Distribución",
            "Almacenamiento_Sistema_Pct",  # PTAP Bosque %
            "Volumen_Total_Bosque_m3",
            "Estado_Operativo",
        ])


# ---------------------------------------------------------
# 2. PARÁMETROS FÍSICOS DE TANQUES Y PLANTA EL CERRO
# ---------------------------------------------------------
# Capacidades máximas aproximadas en m3 para PTAP Bosque (Total efectivo ~50,000 m3)
CAPACIDADES_MAXIMAS_BOSQUE = {
    "Nivel_Tk1_Planta": 3000.0,
    "Nivel_Tk2_Planta": 3000.0,
    "Nivel_SuccionA_TkColinas": 5000.0,
    "Nivel_Colinas_Tk2": 15000.0,
    "Nivel_TkNar2": 10000.0,
    "Nivel_Tk_Lomas": 7000.0,
    "Nivel_Carmelo": 7000.0,
}

FACTORES_PONDERACION_BOSQUE = {
    "Nivel_Tk1_Planta": 0.10,
    "Nivel_Tk2_Planta": 0.10,
    "Nivel_SuccionA_TkColinas": 0.05,
    "Nivel_Colinas_Tk2": 0.40,
    "Nivel_TkNar2": 0.15,
    "Nivel_Tk_Lomas": 0.05,
    "Nivel_Carmelo": 0.15,
}

# Parámetros Planta El Cerro
AREA_CERRO_M2 = 1350.0
VOLUMEN_MAX_CERRO_M3 = 6750.0
NIVEL_MAX_CERRO_M = 4.8

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
# 3. PANEL LATERAL: PARÁMETROS Y CARGA DE PLANTILLA MATRICIAL (.xls / .xlsx)
# ---------------------------------------------------------
st.sidebar.header("🎛️ Parámetros y Carga de Consulta")

fecha_actual = st.sidebar.date_input(
    "Fecha de Operación", value=datetime.today()
)

produccion_planta_m3d = st.sidebar.selectbox(
    "Producción Diaria de Planta (m³/día)",
    options=[253000.0, 255000.0, 272000.0],
    index=1,
)

almacenamiento_06am_pct = st.sidebar.number_input(
    "% Almacenamiento real PTAP Bosque (06:00 a.m.)",
    min_value=0.0,
    max_value=100.0,
    value=72.0,
    step=0.5,
)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Cargar Archivo de Consulta (Plantilla de carga)")
archivo_subido = st.sidebar.file_uploader(
    "Sube tu archivo .xls o .xlsx (Variables en filas, Horas en columnas)",
    type=["xls", "xlsx", "csv"],
)

if archivo_subido is not None:
    try:
        # Lectura robusta de Excel (.xls / .xlsx) o CSV
        if archivo_subido.name.endswith(".csv"):
            df_subido = pd.read_csv(archivo_subido)
        else:
            df_subido = pd.read_excel(archivo_subido, sheet_name=0)

        st.sidebar.success(
            "✅ ¡Plantilla leída con éxito! Haz clic en sincronizar."
        )

        if st.sidebar.button(
            "⚡ Sincronizar y Actualizar Histórico", type="primary"
        ):
            # El archivo tiene la Columna 0 con los nombres de las variables y de la Columna 1 en adelante las horas
            col_var = df_subido.columns[0]
            cols_horas = [c for c in df_subido.columns if c != col_var]

            df_hist = cargar_historico()
            registros_actualizados = 0

            for h_col in cols_horas:
                # Extraer la hora numérica de la columna (ej. "10:00:00 a. m." o "10:00 a. m.")
                h_str = str(h_col).lower()
                h_num = None
                for h_i in range(24):
                    if (
                        f"{h_i:02d}:00" in h_str
                        or f"{h_i}:00" in h_str
                        or f"{h_i}h" in h_str
                    ):
                        # Validar si es PM y no es 12
                        if (
                            ("p. m." in h_str or "pm" in h_str)
                            and h_i < 12
                            and h_i != 0
                        ):
                            h_num = h_i + 12
                        elif (
                            ("a. m." in h_str or "am" in h_str)
                            and h_i == 12
                        ):
                            h_num = 0
                        else:
                            h_num = h_i
                        break

                if h_num is None:
                    # Intento alternativo de extracción por posición o texto
                    continue

                # Mapear diccionario de la columna de esta hora
                dict_vals = dict(
                    zip(df_subido[col_var].astype(str).str.strip(), df_subido[h_col])
                )

                def get_val(k, default=0.0):
                    v = dict_vals.get(k, default)
                    try:
                        if pd.isna(v) or str(v).lower() in ["null", "nan", ""]:
                            return default
                        return float(v)
                    except:
                        return default

                # Extraer niveles tanques Bosque
                t1 = get_val("Nivel_Tk1_Planta", 134.0)
                t2 = get_val("Nivel_Tk2_Planta", 141.0)
                suc = get_val("Nivel_SuccionA_TkColinas", 162.0)
                col2 = get_val("Nivel_Colinas_Tk2", 281.0)
                tn2 = get_val("Nivel_TkNar2", 417.0)
                lom = get_val("Nivel_Tk_Lomas", 257.0)
                car = get_val("Nivel_Carmelo", 285.0)

                # Cálculo Almacenamiento PTAP Bosque (%)
                # Asumiendo proporciones de ocupación respecto a niveles típicos o máximos
                alc_bosque = (
                    min(1.0, col2 / 450.0) * FACTORES_PONDERACION_BOSQUE["Nivel_Colinas_Tk2"]
                    + min(1.0, car / 400.0) * FACTORES_PONDERACION_BOSQUE["Nivel_Carmelo"]
                    + min(1.0, t1 / 300.0) * FACTORES_PONDERACION_BOSQUE["Nivel_Tk1_Planta"]
                    + min(1.0, t2 / 300.0) * FACTORES_PONDERACION_BOSQUE["Nivel_Tk2_Planta"]
                    + min(1.0, tn2 / 500.0) * FACTORES_PONDERACION_BOSQUE["Nivel_TkNar2"]
                    + min(1.0, suc / 350.0) * FACTORES_PONDERACION_BOSQUE["Nivel_SuccionA_TkColinas"]
                    + min(1.0, lom / 400.0) * FACTORES_PONDERACION_BOSQUE["Nivel_Tk_Lomas"]
                ) * 100.0

                vol_bosque_m3 = (alc_bosque / 100.0) * 50000.0

                # Planta El Cerro (Nivel en metros)
                nivel_cerro_m = get_val("EBAP_1_TP_LIT_001.PV", 3.9)
                # Volumen Cerro = Área (1350) * Nivel (m) [limitado al max]
                vol_cerro = min(VOLUMEN_MAX_CERRO_M3, nivel_cerro_m * AREA_CERRO_M2)
                pct_cerro = (vol_cerro / VOLUMEN_MAX_CERRO_M3) * 100.0

                caudal_dist = get_val("Caudal_Distribución", 13531.0)

                reg_temp = {
                    "Fecha": str(fecha_actual),
                    "Hora": f"{h_num:02d}:00",
                    "Produccion_Planta_m3d": produccion_planta_m3d,
                    "Almacenamiento_06am_Pct": almacenamiento_06am_pct,
                    "Nivel_Tk1_Planta": t1,
                    "Nivel_Tk2_Planta": t2,
                    "Nivel_SuccionA_TkColinas": suc,
                    "Nivel_Colinas_Tk2": col2,
                    "Nivel_TkNar2": tn2,
                    "Nivel_Tk_Lomas": lom,
                    "Nivel_Carmelo": car,
                    "EBAP_1_TP_LIT_001.PV": nivel_cerro_m,
                    "EBAP_1_OO_PIT_001.PV": get_val("EBAP_1_OO_PIT_001.PV", 5.4),
                    "Volumen_Cerro_m3": round(vol_cerro, 1),
                    "Pct_Almacenamiento_Cerro": round(pct_cerro, 1),
                    "Caudal_Distribución": caudal_dist,
                    "Almacenamiento_Sistema_Pct": round(alc_bosque, 1),
                    "Volumen_Total_Bosque_m3": round(vol_bosque_m3, 1),
                    "Estado_Operativo": "Normal / Seguro",
                }

                # Guardar en histórico
                df_hist = df_hist[
                    ~(
                        (df_hist["Fecha"] == str(fecha_actual))
                        & (df_hist["Hora"] == f"{h_num:02d}:00")
                    )
                ]
                df_hist = pd.concat(
                    [df_hist, pd.DataFrame([reg_temp])], ignore_index=True
                )
                registros_actualizados += 1

            df_hist.to_csv(HISTORICO_FILE, index=False)
            st.sidebar.success(
                f"🚀 ¡Sincronización completa! Se actualizaron {registros_actualizados} horas desde la plantilla."
            )
    except Exception as e:
        st.sidebar.error(f"Error al procesar la plantilla: {e}")

# ---------------------------------------------------------
# 4. CURVAS BASE Y MODELO DE PROYECCIÓN
# ---------------------------------------------------------
perfil_horario_prom = [
    0.024, 0.022, 0.020, 0.020, 0.022, 0.030,
    0.042, 0.050, 0.054, 0.048, 0.044, 0.042,
    0.042, 0.044, 0.050, 0.054, 0.057, 0.053,
    0.044, 0.038, 0.032, 0.028, 0.025, 0.023,
]
caudal_prom_ref = [p * produccion_planta_m3d for p in perfil_horario_prom]
caudal_min_ref = [c * 0.85 for c in caudal_prom_ref]
caudal_max_ref = [c * 1.15 for c in caudal_prom_ref]
almacenamiento_ideal_ref = [
    75, 78, 82, 85, 88, 85, 75, 60, 50, 45,
    48, 52, 55, 58, 55, 50, 48, 52, 60, 65,
    70, 72, 74, 75,
]

df_curva_base = pd.DataFrame({
    "Hora": horas_dia,
    "Almacenamiento_Ideal_Pct": almacenamiento_ideal_ref,
    "Caudal_Min": caudal_min_ref,
    "Caudal_Prom": caudal_prom_ref,
    "Caudal_Max": caudal_max_ref,
})

factor_matutino = 1.0
if almacenamiento_06am_pct < META_AMANECER_PCT:
    factor_matutino = max(0.75, almacenamiento_06am_pct / META_AMANECER_PCT)

df_curva_base["Caudal_Min_Ajustado"] = df_curva_base["Caudal_Min"] * factor_matutino
df_curva_base["Caudal_Prom_Ajustado"] = df_curva_base["Caudal_Prom"] * factor_matutino
df_curva_base["Caudal_Max_Ajustado"] = df_curva_base["Caudal_Max"] * factor_matutino

# ---------------------------------------------------------
# 5. CARGAR HISTÓRICO Y FILTRAR DÍA ACTUAL
# ---------------------------------------------------------
df_hist_global = cargar_historico()
df_dia_actual = df_hist_global[df_hist_global["Fecha"] == str(fecha_actual)]

# ---------------------------------------------------------
# 6. RECOMENDACIÓN INTELIGENTE DE AJUSTE DE CAUDAL
# ---------------------------------------------------------
recomendacion_texto = "🟢 PTAP Bosque operando dentro de los parámetros esperados para cumplir la meta del 75% al amanecer."
delta_caudal = 0.0

if not df_dia_actual.empty:
    df_dia_ord = df_dia_actual.copy()
    df_dia_ord["Hora_Int"] = df_dia_ord["Hora"].apply(lambda x: int(x.split(":")[0]))
    df_dia_ord = df_dia_ord.sort_values("Hora_Int")

    ultimo_reg = df_dia_ord.iloc[-1]
    ultima_H = int(ultimo_reg["Hora_Int"])
    alm_actual = ultimo_reg["Almacenamiento_Sistema_Pct"]

    meta_h = df_curva_base[df_curva_base["Hora"] == ultima_H]["Almacenamiento_Ideal_Pct"].values[0]

    if alm_actual < meta_h - 1.0:
        deficit = meta_h - alm_actual
        horas_restantes = max(1, 23 - ultima_H)
        vol_faltante = (deficit / 100.0) * 50000.0
        delta_caudal = vol_faltante / horas_restantes
        recomendacion_texto = f"⚠️ **Alerta Operativa (Corte {horas_format[ultima_H]}):** El almacenamiento de PTAP Bosque está {deficit:.1f}% por debajo de la meta. Se recomienda **reducir el caudal de distribución en aprox. {delta_caudal:,.0f} m³/h** durante las próximas {horas_restantes} horas para asegurar el 75% al amanecer."
    elif alm_actual > meta_h + 1.5:
        exceso = alm_actual - meta_h
        horas_restantes = max(1, 23 - ultima_H)
        vol_exceso = (exceso / 100.0) * 50000.0
        delta_caudal = vol_exceso / horas_restantes
        recomendacion_texto = f"ℹ️ **Aviso Operativo (Corte {horas_format[ultima_H]}):** El almacenamiento está {exceso:.1f}% por encima de la meta. Puede **incrementar el caudal de distribución hasta en {delta_caudal:,.0f} m³/h** de forma segura."

# ---------------------------------------------------------
# 7. TABLERO DE KPIS EJECUTIVOS
# ---------------------------------------------------------
st.divider()
st.subheader(f"📊 Tablero Ejecutivo y Toma de Decisiones — Fecha: {fecha_actual}")
st.info(recomendacion_texto)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(label="🌅 Meta Amanecer Bosque", value="≥ 75.0%", delta=f"Base: {almacenamiento_06am_pct:.1f}%")

with kpi2:
    alm_val = df_dia_ord.iloc[-1]["Almacenamiento_Sistema_Pct"] if not df_dia_actual.empty else 55.0
    st.metric(label="💧 % Almacenamiento Bosque Actual", value=f"{alm_val:.1f}%", delta=f"Meta Hora: {meta_h}%" if not df_dia_actual.empty else "Esperando datos")

with kpi3:
    cerro_val = df_dia_ord.iloc[-1]["Pct_Almacenamiento_Cerro"] if not df_dia_actual.empty else 80.0
    st.metric(label="⛰️ % Almacenamiento Planta Cerro", value=f"{cerro_val:.1f}%", delta="Independiente (Área 1,350 m²)")

with kpi4:
    caudal_val = df_dia_ord.iloc[-1]["Caudal_Distribución"] if not df_dia_actual.empty else 13500.0
    st.metric(label="⚡ Caudal Distribución Actual", value=f"{caudal_val:,.0f} m³/h")

# ---------------------------------------------------------
# 8. DASHBOARD GRÁFICO CON TENDENCIAS Y PROYECCIONES
# ---------------------------------------------------------
st.divider()
st.subheader("📈 Dashboard Gráfico: Tendencias, Contraste y Proyección")

tab1, tab2, tab3 = st.tabs([
    "💧 Tendencia y Proyección Almacenamiento (Bosque)",
    "⚡ Tendencia y Proyección Caudal Distribución",
    "⛰️ Estado Planta El Cerro (Nivel y Almacenamiento)",
])

with tab1:
    fig_s = go.Figure()
    fig_s.add_trace(go.Scatter(
        x=df_curva_base["Hora"], y=df_curva_base["Almacenamiento_Ideal_Pct"],
        mode="lines", name="Curva Meta Almacenamiento (%)", line=dict(color="#2980b9", width=3, shape="spline")
    ))

    if not df_dia_actual.empty:
        fig_s.add_trace(go.Scatter(
            x=df_dia_ord["Hora_Int"], y=df_dia_ord["Almacenamiento_Sistema_Pct"],
            mode="lines+markers", name="Almacenamiento Real Acumulado", line=dict(color="#27ae60", width=3, shape="spline"), marker=dict(size=8)
        ))

        ultima_h = df_dia_ord["Hora_Int"].max()
        if ultima_h < 23:
            horas_p = list(range(int(ultima_h), 24))
            ultimo_a = df_dia_ord[df_dia_ord["Hora_Int"] == ultima_h]["Almacenamiento_Sistema_Pct"].values[0]
            proy_a = np.linspace(ultimo_a, 75.0, len(horas_p))
            fig_s.add_trace(go.Scatter(
                x=horas_p, y=proy_a, mode="lines", name="Proyección Resto del Día (Hacia 75%)", line=dict(color="#e67e22", width=3, dash="dot", shape="spline")
            ))

    fig_s.add_hline(y=75.0, line_dash="dot", line_color="red", annotation_text="Meta Amanecer 75%")
    fig_s.update_layout(xaxis=dict(tickmode="array", tickvals=horas_dia, ticktext=[horas_format[h] for h in horas_dia]), xaxis_title="Hora del Día", yaxis_title="Almacenamiento PTAP Bosque (%)", template="plotly_white")
    st.plotly_chart(fig_s, use_container_width=True)

with tab2:
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(
        x=horas_dia + horas_dia[::-1],
        y=list(df_curva_base["Caudal_Max_Ajustado"]) + list(df_curva_base["Caudal_Min_Ajustado"])[::-1],
        fill="toself", fillcolor="rgba(11, 60, 93, 0.1)", line=dict(color="rgba(255,255,255,0)"), name="Banda Permitida"
    ))
    fig_c.add_trace(go.Scatter(
        x=df_curva_base["Hora"], y=df_curva_base["Caudal_Prom_Ajustado"],
        mode="lines", name="Caudal Objetivo (Meta)", line=dict(color="#0b3c5d", width=2, dash="dash", shape="spline")
    ))

    if not df_dia_actual.empty:
        fig_c.add_trace(go.Scatter(
            x=df_dia_ord["Hora_Int"], y=df_dia_ord["Caudal_Distribución"],
            mode="lines+markers", name="Caudal Real Transcurrido", line=dict(color="#27ae60", width=3, shape="spline"), marker=dict(size=8)
        ))

        ultima_h = df_dia_ord["Hora_Int"].max()
        if ultima_h < 23:
            horas_p = list(range(int(ultima_h), 24))
            ultimo_c = df_dia_ord[df_dia_ord["Hora_Int"] == ultima_h]["Caudal_Distribución"].values[0]
            val_final = df_curva_base[df_curva_base["Hora"] == 23]["Caudal_Prom_Ajustado"].values[0]
            proy_c = np.linspace(ultimo_c, val_final, len(horas_p))
            fig_c.add_trace(go.Scatter(
                x=horas_p, y=proy_c, mode="lines", name="Proyección Caudal Resto del Día", line=dict(color="#e67e22", width=3, dash="dot", shape="spline")
            ))

    fig_c.update_layout(xaxis=dict(tickmode="array", tickvals=horas_dia, ticktext=[horas_format[h] for h in horas_dia]), xaxis_title="Hora del Día", yaxis_title="Caudal Distribución (m³/h)", template="plotly_white")
    st.plotly_chart(fig_c, use_container_width=True)

with tab3:
    st.markdown("### ⛰️ Comportamiento Planta El Cerro (Nivel y Almacenamiento)")
    if not df_dia_actual.empty:
        fig_cerro = go.Figure()
        fig_cerro.add_trace(go.Scatter(
            x=df_dia_ord["Hora_Int"], y=df_dia_ord["Pct_Almacenamiento_Cerro"],
            mode="lines+markers", name="% Almacenamiento Cerro", line=dict(color="#8e44ad", width=3, shape="spline")
        ))
        fig_cerro.add_trace(go.Scatter(
            x=df_dia_ord["Hora_Int"], y=df_dia_ord["EBAP_1_TP_LIT_001.PV"],
            mode="lines+markers", name="Nivel Planta Cerro (m)", yaxis="y2", line=dict(color="#2980b9", width=2, dash="dash", shape="spline")
        ))
        fig_cerro.update_layout(
            xaxis=dict(tickmode="array", tickvals=horas_dia, ticktext=[horas_format[h] for h in horas_dia]),
            xaxis_title="Hora del Día",
            yaxis=dict(title="Almacenamiento Cerro (%)", range=[0, 100]),
            yaxis2=dict(title="Nivel (m)", overlaying="y", side="right", range=[0, 5.0]),
            template="plotly_white",
            legend=dict(x=0.01, y=0.99)
        )
        st.plotly_chart(fig_cerro, use_container_width=True)
    else:
        st.info("Carga tu plantilla para visualizar las curvas de Planta El Cerro.")

# ---------------------------------------------------------
# 9. TABLA HISTÓRICA ACUMULADA DEL DÍA
# ---------------------------------------------------------
st.divider()
st.subheader("📋 Registro Horario Acumulado del Día (Reporte Operativo)")
if not df_dia_actual.empty:
    st.dataframe(df_dia_ord.drop(columns=["Hora_Int"]), use_container_width=True)
else:
    st.info("Sube tu archivo de consulta en el panel lateral para poblar el turno de hoy.")
