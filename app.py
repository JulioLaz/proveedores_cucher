import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import bigquery

# === CONFIGURACION DE PAGINA ===
st.set_page_config(page_title="📦 Dashboard Proveedores", layout="wide")
st.title(":package: Dashboard de Análisis por Proveedor")

# === DETECTAR ENTORNO ===
IS_CLOUD = "gcp_service_account" in st.secrets

# === OBTENER VARIABLES ===
if IS_CLOUD:
    credentials_dict = dict(st.secrets["gcp_service_account"])
    sheet_id = st.secrets["google_sheets"]["sheet_id"]
    sheet_name = st.secrets["google_sheets"]["sheet_name"]
    project_id = st.secrets["project_id"]
    bigquery_table = st.secrets["bigquery_table"]

    with open("temp_credentials.json", "w") as f:
        json.dump(credentials_dict, f)
    CREDENTIALS_PATH = "temp_credentials.json"

else:
    load_dotenv()
    CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
    BQ_CREDENTIALS_PATH = os.getenv("BIGQUERY_CREDENTIALS_PATH")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    sheet_name = "proveedores_all"
    project_id = "youtube-analysis-24"
    bigquery_table = "tickets.tickets_all"

# === LEER GOOGLE SHEET PUBLICO ===
@st.cache_data(ttl=3600)
def leer_google_sheet_publico(sheet_id, sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)

try:
    df = leer_google_sheet_publico(sheet_id, sheet_name)
    st.success(f"Datos cargados: {len(df):,} registros")
except Exception as e:
    st.error(f"Error leyendo Google Sheet: {e}")
    st.stop()

st.dataframe(df, use_container_width=True)

# === FILTRAR Y CONSULTAR BIGQUERY ===
proveedor = st.selectbox("Proveedor", sorted(df['proveedor'].dropna().unique()), index=None)
col1, col2 = st.columns(2)
fecha_inicio = col1.date_input("Inicio", value=datetime(2025,1,1))
fecha_fin = col2.date_input("Fin", value=datetime(2025,7,1))

if proveedor:
    ids = df[df['proveedor'] == proveedor]['idarticulo'].dropna().astype(int).astype(str).unique()
    if len(ids) == 0:
        st.warning("Este proveedor no tiene artículos asociados.")
        st.stop()

    id_str = ','.join(ids)

    try:
        bq_path = CREDENTIALS_PATH if not IS_CLOUD else "temp_credentials.json"
        client = bigquery.Client.from_service_account_json(bq_path)
        query = f"""
        SELECT fecha_comprobante, idarticulo, descripcion, cantidad_total,
               costo_total, precio_total, sucursal, familia, subfamilia
        FROM `{project_id}.{bigquery_table}`
        WHERE idarticulo IN ({id_str})
        AND DATE(fecha_comprobante) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        """
        df_bq = client.query(query).to_dataframe()
        st.success(f"{len(df_bq):,} registros encontrados.")
        st.dataframe(df_bq, use_container_width=True)

        # KPIs
        st.metric("Total vendido", f"${df_bq['precio_total'].sum():,.0f}")
        st.metric("Costo total", f"${df_bq['costo_total'].sum():,.0f}")
        st.metric("Artículos vendidos", f"{df_bq['cantidad_total'].sum():,.0f}")
    except Exception as e:
        st.error(f"Error en BigQuery: {e}")
