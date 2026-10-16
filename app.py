import os
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Gemelo Digital Operativo - Aguas de Cartagena",
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
    "💧 Gemelo Digital SCADA y Proyección Operativa — Aguas de Cartagena S.A. E.S.P."
)
st.markdown(
    "Control integral: PTAP Bosque & Planta El Cerro, análisis de presiones sectorizadas, bandas de caudal y optimización de almacenamiento."
)

# ---------------------------------------------------------
# 1. ARCHIVO HISTÓRICO PERSISTENTE (CSV)
# ---------------------------------------------------------
HISTORICO_FILE = "historico_operativo_v2.csv"


def cargar_historico():
    if os.path.exists(HISTORICO_FILE):
        return pd.read_csv(HISTORICO_FILE)
    else:
        return pd.DataFrame(columns=[
            "Fecha",
            "Hora",
            "Produccion_Planta_m3d",
            "Almacenamiento_Meta_06am_Pct",
            "Caudal_Distribución",
            "Almacenamiento_Bosque_Pct",
            "Volumen_Bosque_m3",
            "EBAP_1_TP_LIT_001.PV",
            "Nivel_Cerro_m",
            "Volumen_Cerro_m3",
            "Pct_Almacenamiento_Cerro",
            "EBAP_1_OO_PIT_001.PV",
            "Presion_Ref_Red_Tk_Colinas",
            "Presion_Sector10_Elevado_Colinas",
            "PresBomb_Znorte_a_TkPzuela",
            "Presion_Ent_ZonaNorte",
            "Presion_Pcanoas",
            "Pres_Blezo",
            "Presion_Chile",
            "Presion_Lomas",
            "Presion_Consulado",
            "Presion_Bgrande",
            "Presion_Bgrande_Kra7",
            "Presion_Alcibia",
            "Presion_Piepopa",
            "Pres_Pic",
            "Presion_FPOPA",
            "Presion_Olaya_Cjust",
            "Presion_Fredonia",
            "Presion_Ref_Bombeo_LaVictoria",
            "Presion_Mop",
            "Presion_Royalco",
            "Presion_Bellavista_Agua_Potable",
            "Estado_Operativo",
        ])


# ---------------------------------------------------------
# 2. PARÁMETROS FÍSICOS Y SECTORIZACIÓN
# ---------------------------------------------------------
FACTORES_BOSQUE = {
    "Nivel_Colinas_Tk2": 0.40,
    "Nivel_Carmelo": 0.15,
    "Nivel_Tk1_Planta": 0.10,
    "Nivel_Tk2_Planta": 0.10,
    "Nivel_TkNar2": 0.15,
    "Nivel_SuccionA_TkColinas": 0.05,
    "Nivel_Tk_Lomas": 0.05,
}

AREA_CERRO_M2 = 1350.0
VOLUMEN_MAX_CERRO_M3 = 6750.0
NIVEL_MAX_CERRO_M = 4.8

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
# 3. PANEL LATERAL: CONFIGURACIÓN Y CARGA DE PLANTILLA .xls / .xlsx
# ---------------------------------------------------------
st.sidebar.header("🎛️ Panel de Control y Carga SCADA")

fecha_actual = st.sidebar.date_input(
    "Fecha de Operación", value=datetime.today()
)

produccion_planta_m3d = st.sidebar.selectbox(
    "Capacidad de Producción Planta (m³/día)",
    options=[253000.0, 255000.0, 270000.0, 272000.0],
    index=1,
)

meta_amanecer_pct = st.sidebar.number_input(
    "Meta de Almacenamiento Amanecer (06:00 a.m. %)",
    min_value=50.0,
    max_value=100.0,
    value=75.0,
    step=0.5,
)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Cargar Plantilla de Consulta (.xls / .xlsx)")
archivo_subido = st.sidebar.file_uploader(
    "Sube tu archivo de consulta", type=["xls", "xlsx", "csv"]
)

if archivo_subido is not None:
    try:
        if archivo_subido.name.endswith(".csv"):
            df_subido = pd.read_csv(archivo_subido)
        else:
            excel_file = pd.ExcelFile(archivo_subido)
            sheet_to_read = (
                "Hoja1"
                if "Hoja1" in excel_file.sheet_names
                else excel_file.sheet_names[0]
            )
            df_subido = pd.read_excel(
                archivo_subido, sheet_name=sheet_to_read
            )

        st.sidebar.success(
            "✅ ¡Plantilla leída con éxito! Haz clic en sincronizar."
        )

        if st.sidebar.button(
            "⚡ Sincronizar y Actualizar Datos al Histórico", type="primary"
        ):
            df_hist = cargar_historico()
            registros_procesados = 0

            if "DateTime" in df_subido.columns or "Fecha" in df_subido.columns:
                col_dt = "DateTime" if "DateTime" in df_subido.columns else "Fecha"
                for idx, row in df_subido.iterrows():
                    dt_val = row.get(col_dt, None)
                    if pd.isna(dt_val) or str(dt_val).strip() in ["", "NaT", "nan"]:
                        continue
                    try:
                        dt_parsed = pd.to_datetime(dt_val)
                        h_num = dt_parsed.hour
                        f_str = dt_parsed.strftime("%Y-%m-%d")
                    except:
                        continue

                    def get_col_val(col_names, default=0.0):
                        for c in col_names:
                            if c in df_subido.columns:
                                v = row.get(c, default)
                                try:
                                    if (
                                        pd.isna(v)
                                        or str(v).strip().lower()
                                        in ["null", "nan", "", "none"]
                                        or float(v) < 0
                                    ):
                                        return default
                                    return float(v)
                                except:
                                    pass
                        return default

                    t1 = get_col_val(["Nivel_Tk1_Planta"], 134.0)
                    t2 = get_col_val(["Nivel_Tk2_Planta"], 141.0)
                    suc = get_col_val(["Nivel_SuccionA_TkColinas"], 162.0)
                    col2 = get_col_val(["Nivel_Colinas_Tk2"], 281.0)
                    tn2 = get_col_val(["Nivel_TkNar2"], 417.0)
                    lom = get_col_val(["Nivel_Tk_Lomas"], 257.0)
                    car = get_col_val(["Nivel_Carmelo"], 285.0)

                    alc_bosque = (
                        min(1.0, col2 / 450.0)
                        * FACTORES_BOSQUE["Nivel_Colinas_Tk2"]
                        + min(1.0, car / 400.0)
                        * FACTORES_BOSQUE["Nivel_Carmelo"]
                        + min(1.0, t1 / 300.0)
                        * FACTORES_BOSQUE["Nivel_Tk1_Planta"]
                        + min(1.0, t2 / 300.0)
                        * FACTORES_BOSQUE["Nivel_Tk2_Planta"]
                        + min(1.0, tn2 / 500.0)
                        * FACTORES_BOSQUE["Nivel_TkNar2"]
                        + min(1.0, suc / 350.0)
                        * FACTORES_BOSQUE["Nivel_SuccionA_TkColinas"]
                        + min(1.0, lom / 400.0)
                        * FACTORES_BOSQUE["Nivel_Tk_Lomas"]
                    ) * 100.0
                    vol_bosque = (alc_bosque / 100.0) * 50000.0

                    nivel_cerro_m = get_col_val(
                        ["EBAP_1_TP_LIT_001.PV", "EBAP_1_TP_LIT_001"], 3.9
                    )
                    vol_cerro = min(
                        VOLUMEN_MAX_CERRO_M3, nivel_cerro_m * AREA_CERRO_M2
                    )
                    pct_cerro = (vol_cerro / VOLUMEN_MAX_CERRO_M3) * 100.0

                    caudal_dist = get_col_val(
                        ["Caudal_Distribución.1", "Caudal_Distribución"], 13500.0
                    )

                    reg_temp = {
                        "Fecha": f_str,
                        "Hora": f"{h_num:02d}:00",
                        "Produccion_Planta_m3d": produccion_planta_m3d,
                        "Almacenamiento_Meta_06am_Pct": meta_amanecer_pct,
                        "Caudal_Distribución": caudal_dist,
                        "Almacenamiento_Bosque_Pct": round(alc_bosque, 1),
                        "Volumen_Bosque_m3": round(vol_bosque, 1),
                        "EBAP_1_TP_LIT_001.PV": nivel_cerro_m,
                        "Nivel_Cerro_m": nivel_cerro_m,
                        "Volumen_Cerro_m3": round(vol_cerro, 1),
                        "Pct_Almacenamiento_Cerro": round(pct_cerro, 1),
                        "EBAP_1_OO_PIT_001.PV": get_col_val(
                            ["EBAP_1_OO_PIT_001.PV"], 5.4
                        ),
                        "Presion_Ref_Red_Tk_Colinas": get_col_val(
                            ["Presion_Ref_Red_Tk_Colinas"], 0.0
                        ),
                        "Presion_Sector10_Elevado_Colinas": get_col_val(
                            ["Presion_Sector10_Elevado_Colinas"], 0.0
                        ),
                        "PresBomb_Znorte_a_TkPzuela": get_col_val(
                            ["PresBomb_Znorte_a_TkPzuela"], 0.0
                        ),
                        "Presion_Ent_ZonaNorte": get_col_val(
                            ["Presion_Ent_ZonaNorte"], 0.0
                        ),
                        "Presion_Pcanoas": get_col_val(
                            ["Presion_Pcanoas"], 0.0
                        ),
                        "Pres_Blezo": get_col_val(["Pres_Blezo"], 0.0),
                        "Presion_Chile": get_col_val(["Presion_Chile"], 0.0),
                        "Presion_Lomas": get_col_val(["Presion_Lomas"], 0.0),
                        "Presion_Consulado": get_col_val(
                            ["Presion_Consulado"], 0.0
                        ),
                        "Presion_Bgrande": get_col_val(
                            ["Presion_Bgrande"], 0.0
                        ),
                        "Presion_Bgrande_Kra7": get_col_val(
                            ["Presion_Bgrande_Kra7"], 0.0
                        ),
                        "Presion_Alcibia": get_col_val(
                            ["Presion_Alcibia"], 0.0
                        ),
                        "Presion_Piepopa": get_col_val(
                            ["Presion_Piepopa"], 0.0
                        ),
                        "Pres_Pic": get_col_val(["Pres_Pic"], 0.0),
                        "Presion_FPOPA": get_col_val(["Presion_FPOPA"], 0.0),
                        "Presion_Olaya_Cjust": get_col_val(
                            ["Presion_Olaya_Cjust"], 0.0
                        ),
                        "Presion_Fredonia": get_col_val(
                            ["Presion_Fredonia"], 0.0
                        ),
                        "Presion_Ref_Bombeo_LaVictoria": get_col_val(
                            ["Presion_Ref_Bombeo_LaVictoria"], 0.0
                        ),
                        "Presion_Mop": get_col_val(["Presion_Mop"], 0.0),
                        "Presion_Royalco": get_col_val(
                            ["Presion_Royalco"], 0.0
                        ),
                        "Presion_Bellavista_Agua_Potable": get_col_val(
                            ["Presion_Bellavista_Agua_Potable"], 0.0
                        ),
                        "Estado_Operativo": "Normal / Seguro",
                    }

                    df_hist = df_hist[
                        ~(
                            (df_hist["Fecha"] == f_str)
                            & (df_hist["Hora"] == f"{h_num:02d}:00")
                        )
                    ]
                    df_hist = pd.concat(
                        [df_hist, pd.DataFrame([reg_temp])], ignore_index=True
                    )
                    registros_procesados += 1
            else:
                col_var = df_subido.columns[0]
                cols_horas = [c for c in df_subido.columns if c != col_var]
                for h_col in cols_horas:
                    h_str = str(h_col).lower()
                    h_num = None
                    for h_i in range(24):
                        if (
                            f"{h_i:02d}:00" in h_str
                            or f"{h_i}:00" in h_str
                            or f"{h_i}h" in h_str
                        ):
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
                        continue
                    dict_raw = dict(
                        zip(
                            df_subido[col_var].astype(str).str.strip(),
                            df_subido[h_col],
                        )
                    )

                    def limpiar_val(k, default=0.0):
                        val = dict_raw.get(k, default)
                        try:
                            if (
                                pd.isna(val)
                                or str(val).strip().lower()
                                in ["null", "nan", "", "none"]
                                or float(val) < 0
                            ):
                                return default
                            return float(val)
                        except:
                            return default

                    t1 = limpiar_val("Nivel_Tk1_Planta", 134.0)
                    t2 = limpiar_val("Nivel_Tk2_Planta", 141.0)
                    suc = limpiar_val("Nivel_SuccionA_TkColinas", 162.0)
                    col2 = limpiar_val("Nivel_Colinas_Tk2", 281.0)
                    tn2 = limpiar_val("Nivel_TkNar2", 417.0)
                    lom = limpiar_val("Nivel_Tk_Lomas", 257.0)
                    car = limpiar_val("Nivel_Carmelo", 285.0)

                    alc_bosque = (
                        min(1.0, col2 / 450.0)
                        * FACTORES_BOSQUE["Nivel_Colinas_Tk2"]
                        + min(1.0, car / 400.0)
                        * FACTORES_BOSQUE["Nivel_Carmelo"]
                        + min(1.0, t1 / 300.0)
                        * FACTORES_BOSQUE["Nivel_Tk1_Planta"]
                        + min(1.0, t2 / 300.0)
                        * FACTORES_BOSQUE["Nivel_Tk2_Planta"]
                        + min(1.0, tn2 / 500.0)
                        * FACTORES_BOSQUE["Nivel_TkNar2"]
                        + min(1.0, suc / 350.0)
                        * FACTORES_BOSQUE["Nivel_SuccionA_TkColinas"]
                        + min(1.0, lom / 400.0)
                        * FACTORES_BOSQUE["Nivel_Tk_Lomas"]
                    ) * 100.0
                    vol_bosque = (alc_bosque / 100.0) * 50000.0

                    nivel_cerro_m = limpiar_val("EBAP_1_TP_LIT_001.PV", 3.9)
                    vol_cerro = min(
                        VOLUMEN_MAX_CERRO_M3, nivel_cerro_m * AREA_CERRO_M2
                    )
                    pct_cerro = (vol_cerro / VOLUMEN_MAX_CERRO_M3) * 100.0
                    caudal_dist = limpiar_val("Caudal_Distribución", 13500.0)

                    reg_temp = {
                        "Fecha": str(fecha_actual),
                        "Hora": f"{h_num:02d}:00",
                        "Produccion_Planta_m3d": produccion_planta_m3d,
                        "Almacenamiento_Meta_06am_Pct": meta_amanecer_pct,
                        "Caudal_Distribución": caudal_dist,
                        "Almacenamiento_Bosque_Pct": round(alc_bosque, 1),
                        "Volumen_Bosque_m3": round(vol_bosque, 1),
                        "EBAP_1_TP_LIT_001.PV": nivel_cerro_m,
                        "Nivel_Cerro_m": nivel_cerro_m,
                        "Volumen_Cerro_m3": round(vol_cerro, 1),
                        "Pct_Almacenamiento_Cerro": round(pct_cerro, 1),
                        "EBAP_1_OO_PIT_001.PV": limpiar_val(
                            "EBAP_1_OO_PIT_001.PV", 5.4
                        ),
                        "Presion_Ref_Red_Tk_Colinas": limpiar_val(
                            "Presion_Ref_Red_Tk_Colinas", 0.0
                        ),
                        "Presion_Sector10_Elevado_Colinas": limpiar_val(
                            "Presion_Sector10_Elevado_Colinas", 0.0
                        ),
                        "PresBomb_Znorte_a_TkPzuela": limpiar_val(
                            "PresBomb_Znorte_a_TkPzuela", 0.0
                        ),
                        "Presion_Ent_ZonaNorte": limpiar_val(
                            "Presion_Ent_ZonaNorte", 0.0
                        ),
                        "Presion_Pcanoas": limpiar_val("Presion_Pcanoas", 0.0),
                        "Pres_Blezo": limpiar_val("Pres_Blezo", 0.0),
                        "Presion_Chile": limpiar_val("Presion_Chile", 0.0),
                        "Presion_Lomas": limpiar_val("Presion_Lomas", 0.0),
                        "Presion_Consulado": limpiar_val(
                            "Presion_Consulado", 0.0
                        ),
                        "Presion_Bgrande": limpiar_val("Presion_Bgrande", 0.0),
                        "Presion_Bgrande_Kra7": limpiar_val(
                            "Presion_Bgrande_Kra7", 0.0
                        ),
                        "Presion_Alcibia": limpiar_val(
                            "Presion_Alcibia", 0.0
                        ),
                        "Presion_Piepopa": limpiar_val(
                            "Presion_Piepopa", 0.0
                        ),
                        "Pres_Pic": limpiar_val("Pres_Pic", 0.0),
                        "Presion_FPOPA": limpiar_val("Presion_FPOPA", 0.0),
                        "Presion_Olaya_Cjust": limpiar_val(
                            "Presion_Olaya_Cjust", 0.0
                        ),
                        "Presion_Fredonia": limpiar_val(
                            "Presion_Fredonia", 0.0
                        ),
                        "Presion_Ref_Bombeo_LaVictoria": limpiar_val(
                            "Presion_Ref_Bombeo_LaVictoria", 0.0
                        ),
                        "Presion_Mop": limpiar_val("Presion_Mop", 0.0),
                        "Presion_Royalco": limpiar_val(
                            "Presion_Royalco", 0.0
                        ),
                        "Presion_Bellavista_Agua_Potable": limpiar_val(
                            "Presion_Bellavista_Agua_Potable", 0.0
                        ),
                        "Estado_Operativo": "Normal / Seguro",
                    }
                    df_hist = df_hist[
                        ~(
                            (df_hist["Fecha"] == str(fecha_actual))
                            & (df_hist["Hora"] == f"{h_num:02d}:00")
                        )
                    ]
                    df_hist = pd.concat(
                        [df_hist, pd.DataFrame([reg_temp])], ignore_index=True
                    )
                    registros_procesados += 1

            df_hist.to_csv(HISTORICO_FILE, index=False)
            st.sidebar.success(
                f"🚀 ¡Sincronización exitosa! Se actualizaron {registros_procesados} horas."
            )
    except Exception as e:
        st.sidebar.error(f"Error al procesar la plantilla: {e}")

# ---------------------------------------------------------
# 4. GENERACIÓN DE CURVAS BASE Y BANDA DE CAUDALES
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
    meta_amanecer_pct,
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
    meta_amanecer_pct,
]

df_curva_base = pd.DataFrame({
    "Hora": horas_dia,
    "Almacenamiento_Ideal_Pct": almacenamiento_ideal_ref,
    "Caudal_Min": caudal_min_ref,
    "Caudal_Prom": caudal_prom_ref,
    "Caudal_Max": caudal_max_ref,
})

# ---------------------------------------------------------
# 5. CARGAR HISTÓRICO Y FILTRAR DÍA ACTUAL
# ---------------------------------------------------------
df_hist_global = cargar_historico()
df_dia_actual = df_hist_global[df_hist_global["Fecha"] == str(fecha_actual)]

# ---------------------------------------------------------
# 6. RECOMENDACIÓN INTELIGENTE DE AJUSTE DE CAUDAL
# ---------------------------------------------------------
recomendacion_texto = "🟢 Sistema operando dentro de los parámetros esperados para cumplir la meta de almacenamiento."
delta_caudal = 0.0

if not df_dia_actual.empty:
    df_dia_ord = df_dia_actual.copy()
    df_dia_ord["Hora_Int"] = df_dia_ord["Hora"].apply(lambda x: int(x.split(":")[0]))
    df_dia_ord = df_dia_ord.sort_values("Hora_Int")

    ultimo_reg = df_dia_ord.iloc[-1]
    ultima_H = int(ultimo_reg["Hora_Int"])
    alm_actual = float(ultimo_reg["Almacenamiento_Bosque_Pct"])

    meta_h = df_curva_base[df_curva_base["Hora"] == ultima_H]["Almacenamiento_Ideal_Pct"].values[0]

    if alm_actual < meta_h - 1.0:
        deficit = meta_h - alm_actual
        horas_restantes = max(1, 23 - ultima_H)
        vol_faltante = (deficit / 100.0) * 50000.0
        delta_caudal = vol_faltante / horas_restantes
        recomendacion_texto = f"⚠️ **Alerta Operativa (Corte {horas_format[ultima_H]}):** El almacenamiento está {deficit:.1f}% por debajo de la meta. Se recomienda **reducir el caudal de distribución en aprox. {delta_caudal:,.0f} m³/h** durante las próximas {horas_restantes} horas para asegurar la meta del {meta_amanecer_pct}% al amanecer."
    elif alm_actual > meta_h + 1.5:
        exceso = alm_actual - meta_h
        horas_restantes = max(1, 23 - ultima_H)
        vol_exceso = (exceso / 100.0) * 50000.0
        delta_caudal = vol_exceso / horas_restantes
        recomendacion_texto = f"ℹ️ **Aviso Operativo (Corte {horas_format[ultima_H]}):** El almacenamiento está {exceso:.1f}% por encima de la meta. Puede **incrementar el caudal de distribución hasta en {delta_caudal:,.0f} m³/h** de forma segura."

# ---------------------------------------------------------
# 7. DASHBOARD DE KPIS EJECUTIVOS
# ---------------------------------------------------------
st.divider()
st.subheader(f"📊 Tablero Ejecutivo y Toma de Decisiones — Fecha: {fecha_actual}")
st.info(recomendacion_texto)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        label="🌅 Meta Amanecer Bosque",
        value=f"≥ {meta_amanecer_pct:.1f}%",
        delta=f"Producción: {produccion_planta_m3d:,.0f} m³/d",
    )

with kpi2:
    alm_val = (
        float(df_dia_ord.iloc[-1]["Almacenamiento_Bosque_Pct"])
        if not df_dia_actual.empty
        else 55.0
    )
    st.metric(
        label="💧 % Almacenamiento Bosque Actual",
        value=f"{alm_val:.1f}%",
        delta="PTAP Bosque",
    )

with kpi3:
    cerro_val = (
        float(df_dia_ord.iloc[-1]["Pct_Almacenamiento_Cerro"])
        if not df_dia_actual.empty
        else 80.0
    )
    st.metric(
        label="⛰️ % Almacenamiento Planta Cerro",
        value=f"{cerro_val:.1f}%",
        delta="Área 1,350 m²",
    )

with kpi4:
    caudal_val = (
        float(df_dia_ord.iloc[-1]["Caudal_Distribución"])
        if not df_dia_actual.empty
        else 13500.0
    )
    st.metric(
        label="⚡ Caudal Distribución Actual", value=f"{caudal_val:,.0f} m³/h"
    )

# ---------------------------------------------------------
# 8. DASHBOARDS GRÁFICOS INTERACTIVOS (DECLARACIÓN DE TABS PRIMERO)
# ---------------------------------------------------------
st.divider()
st.subheader("📈 Dashboard Gráfico: Tendencias Suavizadas y Proyecciones")

tab1, tab2, tab3, tab4 = st.tabs([
    "💧 Almacenamiento PTAP Bosque",
    "⚡ Bandas y Tendencia Caudal",
    "⛰️ Planta El Cerro (Nivel y Almacenamiento)",
    "🗜️ Presiones Últimas 6 Horas",
])

with tab1:
    fig_s = go.Figure()
    fig_s.add_trace(
        go.Scatter(
            x=df_curva_base["Hora"],
            y=df_curva_base["Almacenamiento_Ideal_Pct"],
            mode="lines",
            name="Curva Meta Almacenamiento (%)",
            line=dict(color="#2980b9", width=2, dash="dash", shape="spline"),
        )
    )

    if not df_dia_actual.empty:
        fig_s.add_trace(
            go.Scatter(
                x=df_dia_ord["Hora_Int"],
                y=df_dia_ord["Almacenamiento_Bosque_Pct"],
                mode="lines+markers",
                name="Almacenamiento Real (Transcurrido)",
                line=dict(color="#27ae60", width=3, shape="spline"),
                marker=dict(size=8),
            )
        )

        ultima_h = df_dia_ord["Hora_Int"].max()
        if ultima_h < 23:
            horas_p = list(range(int(ultima_h), 24))
            ultimo_a = float(
                df_dia_ord[df_dia_ord["Hora_Int"] == ultima_h][
                    "Almacenamiento_Bosque_Pct"
                ].values[0]
            )
            proy_a = np.linspace(ultimo_a, meta_amanecer_pct, len(horas_p))
            fig_s.add_trace(
                go.Scatter(
                    x=horas_p,
                    y=proy_a,
                    mode="lines",
                    name="Proyección Resto del Día",
                    line=dict(
                        color="#e67e22", width=3, dash="dot", shape="spline"
                    ),
                )
            )

    fig_s.add_hline(
        y=meta_amanecer_pct,
        line_dash="dot",
        line_color="red",
    )
    fig_s.add_annotation(
        x=0.01,
        y=meta_amanecer_pct + 3.0,
        xref="paper",
        yref="y",
        text=f"<b>Meta Amanecer {meta_amanecer_pct}%</b>",
        showarrow=False,
        font=dict(color="red", size=12),
        align="left",
    )

    fig_s.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=horas_dia,
            ticktext=[horas_format[h] for h in horas_dia],
        ),
        xaxis_title="Hora del Día",
        yaxis_title="Almacenamiento PTAP Bosque (%)",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(t=40),
    )
    st.plotly_chart(fig_s, use_container_width=True)

with tab2:
    fig_c = go.Figure()
    fig_c.add_trace(
        go.Scatter(
            x=horas_dia + horas_dia[::-1],
            y=list(df_curva_base["Caudal_Max"])
            + list(df_curva_base["Caudal_Min"])[::-1],
            fill="toself",
            fillcolor="rgba(11, 60, 93, 0.1)",
            line=dict(color="rgba(255,255,255,0)"),
            name="Banda Permitida (Máx - Mín)",
        )
    )
    fig_c.add_trace(
        go.Scatter(
            x=df_curva_base["Hora"],
            y=df_curva_base["Caudal_Prom"],
            mode="lines",
            name="Caudal Objetivo (Meta)",
            line=dict(color="#0b3c5d", width=2, dash="dash", shape="spline"),
        )
    )

    if not df_dia_actual.empty:
        fig_c.add_trace(
            go.Scatter(
                x=df_dia_ord["Hora_Int"],
                y=df_dia_ord["Caudal_Distribución"],
                mode="lines+markers",
                name="Caudal Real Transcurrido",
                line=dict(color="#27ae60", width=3, shape="spline"),
                marker=dict(size=8),
            )
        )

        ultima_h = df_dia_ord["Hora_Int"].max()
        if ultima_h < 23:
            horas_p = list(range(int(ultima_h), 24))
            ultimo_c = float(
                df_dia_ord[df_dia_ord["Hora_Int"] == ultima_h][
                    "Caudal_Distribución"
                ].values[0]
            )
            val_final = df_curva_base[df_curva_base["Hora"] == 23][
                "Caudal_Prom"
            ].values[0]
            proy_c = np.linspace(ultimo_c, val_final, len(horas_p))
            fig_c.add_trace(
                go.Scatter(
                    x=horas_p,
                    y=proy_c,
                    mode="lines",
                    name="Proyección Caudal Resto del Día",
                    line=dict(
                        color="#e67e22", width=3, dash="dot", shape="spline"
                    ),
                )
            )

    fig_c.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=horas_dia,
            ticktext=[horas_format[h] for h in horas_dia],
        ),
        xaxis_title="Hora del Día",
        yaxis_title="Caudal Distribución (m³/h)",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(t=40),
    )
    st.plotly_chart(fig_c, use_container_width=True)

with tab3:
    st.markdown(
        "### ⛰️ Comportamiento Planta El Cerro (Nivel en Metros y Almacenamiento)"
    )
    if not df_dia_actual.empty:
        fig_cerro = go.Figure()
        fig_cerro.add_trace(
            go.Scatter(
                x=df_dia_ord["Hora_Int"],
                y=df_dia_ord["Pct_Almacenamiento_Cerro"],
                mode="lines+markers",
                name="% Almacenamiento Cerro (Real)",
                line=dict(color="#8e44ad", width=3, shape="spline"),
            )
        )
        fig_cerro.add_trace(
            go.Scatter(
                x=df_dia_ord["Hora_Int"],
                y=df_dia_ord["Nivel_Cerro_m"],
                mode="lines+markers",
                name="Nivel Planta Cerro (m)",
                yaxis="y2",
                line=dict(color="#2980b9", width=2, dash="dash", shape="spline"),
            )
        )
        fig_cerro.update_layout(
            xaxis=dict(
                tickmode="array",
                tickvals=horas_dia,
                ticktext=[horas_format[h] for h in horas_dia],
            ),
            xaxis_title="Hora del Día",
            yaxis=dict(title="Almacenamiento Cerro (%)", range=[0, 100]),
            yaxis2=dict(
                title="Nivel (m)", overlaying="y", side="right", range=[0, 5.0]
            ),
            template="plotly_white",
            legend=dict(x=0.01, y=0.99),
            margin=dict(t=40),
        )
        st.plotly_chart(fig_cerro, use_container_width=True)
    else:
        st.info("Carga tu plantilla para visualizar las curvas de Planta El Cerro.")

with tab4:
    st.markdown("### 🗜️ Consulta de Presiones (Últimas 6 Horas)")
    if not df_dia_actual.empty:
        df_ultimas_6 = df_dia_ord.tail(6)
        cols_presiones = [
            c
            for c in df_ultimas_6.columns
            if "Pres" in c or "EBAP" in c or "Presión" in c
        ]
        df_presiones_transp = df_ultimas_6[["Hora"] + cols_presiones].set_index("Hora").T
        st.dataframe(df_presiones_transp, use_container_width=True)
    else:
        st.info("Carga tu plantilla para consultar las presiones sectorizadas.")

# ---------------------------------------------------------
# 9. CALENDARIO HISTÓRICO DE CONSULTA
# ---------------------------------------------------------
st.divider()
st.subheader("📅 Auditoría y Consulta Histórica por Calendario")
if not df_hist_global.empty:
    fechas_unicas = sorted(df_hist_global["Fecha"].unique())
    fecha_sel = st.selectbox(
        "Seleccione la fecha histórica a consultar",
        options=fechas_unicas,
        index=len(fechas_unicas) - 1,
    )
    df_f_sel = df_hist_global[df_hist_global["Fecha"] == fecha_sel]
    st.dataframe(df_f_sel, use_container_width=True)
else:
    st.info("Aún no hay registros en el archivo histórico.")
