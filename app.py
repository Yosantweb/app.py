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
    "Monitoreo avanzado, integración directa de tu consulta SCADA, curvas suavizadas y recomendación de ajuste operativo."
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
            "Presion_AA_Pozon",
            "Presion_Sal_Booster_Asturias",
            "PresBomb_Znorte_a_TkPzuela",
            "Presion_Ent_ZonaNorte",
            "Presion_Pcanoas",
            "Pres_Blezo",
            "Presion_Chile",
            "Presion_Lomas",
            "Pres_Consulado",
            "Presion_Bgrande",
            "Presion_Bgrande_Kra7",
            "Presion_Alcibia",
            "Presion_Piepopa",
            "Presion_Centro",
            "Pres_Pic",
            "Presion_FPOPA",
            "Presion_Olaya_Cjust",
            "Presion_Fredonia",
            "Pres_Ref_Bombeo_LaVictoria",
            "Presion_Mop",
            "Presion_Royalco",
            "Presion_Bellavista_Agua_Potable",
            "Presion_Ent_Booster",
            "EBAP_1_OO_PIT_001.PV",
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
# 3. PANEL LATERAL: PARÁMETROS Y CARGA DE PLANTILLA
# ---------------------------------------------------------
st.sidebar.header("🎛️ Parámetros y Carga de Plantilla SCADA")

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
st.sidebar.subheader("📂 Cargar Plantilla de Consulta (Excel / CSV)")
archivo_subido = st.sidebar.file_uploader(
    "Sube tu archivo con filas por hora y columnas por variable",
    type=["xlsx", "csv"],
)

if archivo_subido is not None:
    try:
        if archivo_subido.name.endswith(".csv"):
            df_subido = pd.read_csv(archivo_subido)
        else:
            df_subido = pd.read_excel(archivo_subido, sheet_name=0)

        st.sidebar.success(
            "✅ ¡Plantilla leída con éxito! Haz clic en sincronizar."
        )

        if st.sidebar.button(
            "⚡ Sincronizar Plantilla al Histórico del Día", type="primary"
        ):
            df_hist = cargar_historico()

            for idx, row in df_subido.iterrows():
                dt_val = row.get("DateTime", row.get("Fecha", None))
                if pd.notna(dt_val):
                    try:
                        dt_parsed = pd.to_datetime(dt_val)
                        h_num = dt_parsed.hour
                        f_str = dt_parsed.strftime("%Y-%m-%d")
                    except:
                        h_num = idx % 24
                        f_str = str(fecha_actual)
                else:
                    h_num = idx % 24
                    f_str = str(fecha_actual)

                # Extraer caudal de la columna correspondiente de tu consulta
                val_caudal = row.get(
                    "Caudal_Distribución.1",
                    row.get(
                        "Caudal_Real_m3h",
                        row.get("Caudal_Distribución", 12000.0),
                    ),
                )
                try:
                    val_caudal = float(val_caudal)
                except:
                    val_caudal = 12000.0

                # Extraer niveles reales de tanques de tu plantilla
                n_t1 = float(row.get("Nivel_Tk1_Planta", 200.0))
                n_t2 = float(row.get("Nivel_Tk2_Planta", 200.0))
                n_suc = float(row.get("Nivel_SuccionA_TkColinas", 250.0))
                n_col = float(row.get("Nivel_Colinas_Tk2", 300.0))
                n_tn2 = float(row.get("Nivel_TkNar2", 350.0))
                n_lom = float(row.get("Nivel_Tk_Lomas", 300.0))
                n_car = float(row.get("Nivel_Carmelo", 250.0))

                # Cálculo real del almacenamiento del sistema en base a los tanques
                alc_sys = (
                    min(1.0, n_col / ALTURAS_MAXIMAS_TANQUES["Nivel_Colinas"])
                    * FACTORES_PONDERACION["Nivel_Colinas"]
                    + min(
                        1.0, n_car / ALTURAS_MAXIMAS_TANQUES["Nivel_Carmelo"]
                    )
                    * FACTORES_PONDERACION["Nivel_Carmelo"]
                    + min(
                        1.0, n_t1 / ALTURAS_MAXIMAS_TANQUES["Nivel_Tk1_Planta"]
                    )
                    * FACTORES_PONDERACION["Nivel_Tk1_Planta"]
                    + min(
                        1.0, n_t2 / ALTURAS_MAXIMAS_TANQUES["Nivel_Tk2_Planta"]
                    )
                    * FACTORES_PONDERACION["Nivel_Tk2_Planta"]
                    + min(
                        1.0, n_tn2 / ALTURAS_MAXIMAS_TANQUES["Nivel_TkNar2"]
                    )
                    * FACTORES_PONDERACION["Nivel_TkNar2"]
                    + min(
                        1.0,
                        n_suc
                        / ALTURAS_MAXIMAS_TANQUES["Nivel_SuccionA_TkColinas"],
                    )
                    * FACTORES_PONDERACION["Nivel_SuccionA_TkColinas"]
                    + min(1.0, n_lom / ALTURAS_MAXIMAS_TANQUES["Nivel_Tk_Lomas"])
                    * FACTORES_PONDERACION["Nivel_Tk_Lomas"]
                ) * 100.0

                reg_temp = {
                    "Fecha": f_str,
                    "Hora": f"{h_num:02d}:00",
                    "Produccion_Planta_m3d": produccion_planta_m3d,
                    "Almacenamiento_06am_Pct": almacenamiento_06am_pct,
                    "Nivel_Colinas_cm": n_col,
                    "Nivel_Carmelo_cm": n_car,
                    "Nivel_Tk1_Planta_cm": n_t1,
                    "Nivel_Tk2_Planta_cm": n_t2,
                    "Nivel_TkNar2_cm": n_tn2,
                    "Nivel_SuccionA_TkColinas_cm": n_suc,
                    "Nivel_Tk_Lomas_cm": n_lom,
                    "Caudal_Real_m3h": val_caudal,
                    # Presiones exactas de tu plantilla
                    "Presion_Ref_Red_Tk_Colinas": float(
                        row.get("Presion_Ref_Red_Tk_Colinas", 0.0)
                    ),
                    "Presion_Sector10_Elevado_Colinas": float(
                        row.get("Presion_Sector10_Elevado_Colinas", 0.0)
                    ),
                    "Presion_AA_Pozon": float(
                        row.get("Presion_AA_Pozon", 0.0)
                    ),
                    "Presion_Sal_Booster_Asturias": float(
                        row.get("Presion_Sal_Booster_Asturias", 0.0)
                    ),
                    "PresBomb_Znorte_a_TkPzuela": float(
                        row.get("PresBomb_Znorte_a_TkPzuela", 0.0)
                    ),
                    "Presion_Ent_ZonaNorte": float(
                        row.get("Presion_Ent_ZonaNorte", 0.0)
                    ),
                    "Presion_Pcanoas": float(
                        row.get("Presion_Pcanoas", 0.0)
                    ),
                    "Pres_Blezo": float(row.get("Pres_Blezo", 0.0)),
                    "Presion_Chile": float(row.get("Presion_Chile", 0.0)),
                    "Presion_Lomas": float(
                        row.get("Presion_Lomas", 0.0)
                    ),  # <--- Sector Tanque Lomas
                    "Pres_Consulado": float(row.get("Pres_Consulado", 0.0)),
                    "Presion_Bgrande": float(row.get("Presion_Bgrande", 0.0)),
                    "Presion_Bgrande_Kra7": float(
                        row.get("Presion_Bgrande_Kra7", 0.0)
                    ),
                    "Presion_Alcibia": float(row.get("Presion_Alcibia", 0.0)),
                    "Presion_Piepopa": float(row.get("Presion_Piepopa", 0.0)),
                    "Presion_Centro": float(row.get("Presion_Centro", 0.0)),
                    "Pres_Pic": float(row.get("Pres_Pic", 0.0)),
                    "Presion_FPOPA": float(row.get("Presion_FPOPA", 0.0)),
                    "Presion_Olaya_Cjust": float(
                        row.get("Presion_Olaya_Cjust", 0.0)
                    ),
                    "Presion_Fredonia": float(
                        row.get("Presion_Fredonia", 0.0)
                    ),
                    "Pres_Ref_Bombeo_LaVictoria": float(
                        row.get("Pres_Ref_Bombeo_LaVictoria", 0.0)
                    ),
                    "Pres_Mop": float(row.get("Pres_Mop", 0.0)),
                    "Pres_Royalco": float(row.get("Pres_Royalco", 0.0)),
                    "Presion_Bellavista_Agua_Potable": float(
                        row.get("Presion_Bellavista_Agua_Potable", 0.0)
                    ),
                    "Presion_Ent_Booster": float(
                        row.get("Presion_Ent_Booster", 0.0)
                    ),
                    "EBAP_1_OO_PIT_001.PV": float(
                        row.get("EBAP_1_OO_PIT_001.PV", 0.0)
                    ),
                    "Almacenamiento_Sistema_Pct": round(alc_sys, 2),
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

            df_hist.to_csv(HISTORICO_FILE, index=False)
            st.sidebar.success(
                "🚀 ¡Plantilla de consulta sincronizada con éxito al histórico!"
            )
    except Exception as e:
        st.sidebar.error(f"Error al leer tu plantilla: {e}")

st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ Hora de Consulta Actual (Modo Manual)")
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
# 5. MÓDULO DE INGRESO MANUAL
# ---------------------------------------------------------
st.markdown(
    f"### 📥 Registro Operativo — Fecha: {fecha_actual} | Hora: {horas_format[hora_actual]}"
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

    with st.expander(
        "Desplegar Variables de Presión de la Consulta", expanded=False
    ):
        p_colinas = st.number_input("Presion_Ref_Red_Tk_Colinas", value=0.0)
        p_sec10 = st.number_input("Presion_Sector10_Elevado_Colinas", value=0.0)
        p_apozon = st.number_input("Presion_AA_Pozon", value=0.0)
        p_bast = st.number_input("Presion_Sal_Booster_Asturias", value=0.0)
        p_pzuela = st.number_input("PresBomb_Znorte_a_TkPzuela", value=0.0)
        p_znorte = st.number_input("Presion_Ent_ZonaNorte", value=0.0)
        p_pcanoas = st.number_input("Presion_Pcanoas", value=0.0)
        p_blezo = st.number_input("Pres_Blezo", value=0.0)
        p_chile = st.number_input("Presion_Chile", value=0.0)
        p_lomas = st.number_input(
            "Presion_Lomas", value=0.0
        )  # <--- Tanque Lomas
        p_consulado = st.number_input("Pres_Consulado", value=0.0)
        p_bgrande = st.number_input("Presion_Bgrande", value=0.0)
        p_bgrande7 = st.number_input("Presion_Bgrande_Kra7", value=0.0)
        p_alcibia = st.number_input("Presion_Alcibia", value=0.0)
        p_piepopa = st.number_input("Presion_Piepopa", value=0.0)
        p_centro = st.number_input("Presion_Centro", value=0.0)
        p_pic = st.number_input("Pres_Pic", value=0.0)
        p_fpopa = st.number_input("Pres_FPOPA", value=0.0)
        p_olaya = st.number_input("Presion_Olaya_Cjust", value=0.0)
        p_fredonia = st.number_input("Presion_Fredonia", value=0.0)
        p_victoria = st.number_input("Pres_Ref_Bombeo_LaVictoria", value=0.0)
        p_mop = st.number_input("Pres_Mop", value=0.0)
        p_royalco = st.number_input("Pres_Royalco", value=0.0)
        p_bellavista = st.number_input(
            "Presion_Bellavista_Agua_Potable", value=0.0
        )
        p_ebooster = st.number_input("Presion_Ent_Booster", value=0.0)
        p_cerro = st.number_input("EBAP_1_OO_PIT_001.PV", value=0.0)

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
        "Presion_AA_Pozon": p_apozon,
        "Presion_Sal_Booster_Asturias": p_bast,
        "PresBomb_Znorte_a_TkPzuela": p_pzuela,
        "Presion_Ent_ZonaNorte": p_znorte,
        "Presion_Pcanoas": p_pcanoas,
        "Pres_Blezo": p_blezo,
        "Presion_Chile": p_chile,
        "Presion_Lomas": p_lomas,
        "Pres_Consulado": p_consulado,
        "Presion_Bgrande": p_bgrande,
        "Presion_Bgrande_Kra7": p_bgrande7,
        "Presion_Alcibia": p_alcibia,
        "Presion_Piepopa": p_piepopa,
        "Presion_Centro": p_centro,
        "Pres_Pic": p_pic,
        "Presion_FPOPA": p_fpopa,
        "Presion_Olaya_Cjust": p_olaya,
        "Presion_Fredonia": p_fredonia,
        "Pres_Ref_Bombeo_LaVictoria": p_victoria,
        "Pres_Mop": p_mop,
        "Pres_Royalco": p_royalco,
        "Presion_Bellavista_Agua_Potable": p_bellavista,
        "Presion_Ent_Booster": p_ebooster,
        "EBAP_1_OO_PIT_001.PV": p_cerro,
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
# 7. CARGAR HISTÓRICO Y FILTRAR DÍA ACTUAL
# ---------------------------------------------------------
df_hist_global = cargar_historico()
df_dia_actual = df_hist_global[df_hist_global["Fecha"] == str(fecha_actual)]

# ---------------------------------------------------------
# 8. CÁLCULO INTELIGENTE DE RECOMENDACIÓN DE AJUSTE DE CAUDAL
# ---------------------------------------------------------
recomendacion_ajuste_texto = "🟢 Sistema operando dentro de los parámetros esperados para cumplir la meta del día."
delta_caudal_sugerido = 0.0

if not df_dia_actual.empty:
    df_dia_ordenado = df_dia_actual.copy()
    df_dia_ordenado["Hora_Int"] = df_dia_ordenado["Hora"].apply(
        lambda x: int(x.split(":")[0])
    )
    df_dia_ordenado = df_dia_ordenado.sort_values("Hora_Int")

    ultimo_reg = df_dia_ordenado.iloc[-1]
    ultima_H = int(ultimo_reg["Hora_Int"])
    alm_actual_reg = ultimo_reg["Almacenamiento_Sistema_Pct"]

    meta_h_ideal = df_curva_base[df_curva_base["Hora"] == ultima_H][
        "Almacenamiento_Ideal_Pct"
    ].values[0]

    if alm_actual_reg < meta_h_ideal - 1.0:
        deficit_pct = meta_h_ideal - alm_actual_reg
        horas_restantes = max(1, 23 - ultima_H)
        volumen_faltante_m3 = (deficit_pct / 100.0) * 50000.0
        delta_caudal_sugerido = volumen_faltante_m3 / horas_restantes
        recomendacion_ajuste_texto = f"⚠️ **Alerta Operativa (Corte {horas_format[ultima_H]}):** El almacenamiento está {deficit_pct:.1f}% por debajo de la meta. Se recomienda **reducir el caudal de distribución en aprox. {delta_caudal_sugerido:,.0f} m³/h** durante las próximas {horas_restantes} horas para recuperar la meta del 75% al amanecer."
    elif alm_actual_reg > meta_h_ideal + 1.5:
        exceso_pct = alm_actual_reg - meta_h_ideal
        horas_restantes = max(1, 23 - ultima_H)
        volumen_exceso_m3 = (exceso_pct / 100.0) * 50000.0
        delta_caudal_sugerido = volumen_exceso_m3 / horas_restantes
        recomendacion_ajuste_texto = f"ℹ️ **Aviso Operativo (Corte {horas_format[ultima_H]}):** El almacenamiento está {exceso_pct:.1f}% por encima de la meta. Puede **incrementar el caudal de distribución hasta en {delta_caudal_sugerido:,.0f} m³/h** de forma segura."

# ---------------------------------------------------------
# 9. KPI'S Y RECOMENDACIÓN EJECUTIVA
# ---------------------------------------------------------
st.divider()
st.subheader(
    f"📊 Indicadores de Contraste y Recomendación Operativa — Fecha: {fecha_actual}"
)

st.info(recomendacion_ajuste_texto)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        label="🌅 Almacenamiento 06:00 a.m.",
        value=f"{almacenamiento_06am_pct:.1f}%",
        delta="Meta ≥ 75%",
    )

with kpi2:
    ultimo_alm_val = (
        df_dia_ordenado.iloc[-1]["Almacenamiento_Sistema_Pct"]
        if not df_dia_actual.empty
        else pct_almacenamiento_actual
    )
    st.metric(
        label="💧 Almacenamiento Actual",
        value=f"{ultimo_alm_val:.1f}%",
        delta=f"Producción: {produccion_planta_m3d:,.0f} m³/d",
    )

with kpi3:
    ultimo_caudal_val = (
        df_dia_ordenado.iloc[-1]["Caudal_Real_m3h"]
        if not df_dia_actual.empty
        else caudal_distribucion_actual
    )
    st.metric(
        label="⚡ Caudal Operando",
        value=f"{ultimo_caudal_val:,.1f} m³/h",
    )

with kpi4:
    st.metric(
        label="Estado Operativo",
        value=(
            "🟢 Normal" if "Alerta" not in recomendacion_ajuste_texto else "🟠 Ajuste"
        ),
    )

# ---------------------------------------------------------
# 10. DASHBOARD GRÁFICO DINÁMICO
# ---------------------------------------------------------
st.divider()
st.subheader(
    "📈 Dashboard Gráfico: Tendencias Dinámicas, Contraste y Proyección"
)

tab_g1, tab_g2, tab_g3, tab_g4 = st.tabs([
    "⚡ Tendencia y Proyección Caudal",
    "💧 Tendencia y Proyección Almacenamiento",
    "🗜️ Tendencia de Presiones (Consulta SCADA)",
    "📅 Calendario Histórico",
])

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
    st.markdown("### 🗜️ Tendencia Horaria de Presiones (Consulta SCADA)")
    if not df_dia_actual.empty:
        fig_p = go.Figure()
        df_p_ord = df_dia_actual.copy()
        df_p_ord["Hora_Int"] = df_p_ord["Hora"].apply(
            lambda x: int(x.split(":")[0])
        )
        df_p_ord = df_p_ord.sort_values("Hora_Int")

        columnas_presiones = [
            c
            for c in df_p_ord.columns
            if "Pres" in c or "EBAP" in c or "Presión" in c
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
        st.info("Carga tu plantilla para visualizar las curvas de presión.")

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
# 11. DETALLE DE TANQUES
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
