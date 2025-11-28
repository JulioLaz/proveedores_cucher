"""
Configuración central de la aplicación
"""
import os
import json
import streamlit as st
from dotenv import load_dotenv

def detect_environment():
    """Detectar si estamos en cloud o local"""
    return "gcp_service_account" in st.secrets if hasattr(st, 'secrets') else False

def setup_credentials():
    """
    Configurar credenciales según el entorno
    
    Returns:
        dict: Diccionario con todas las credenciales necesarias
    """
    IS_CLOUD = detect_environment()
    
    if IS_CLOUD:
        credentials_dict = dict(st.secrets["gcp_service_account"])
        sheet_id = st.secrets["google_sheets"]["sheet_id"]
        sheet_name = st.secrets["google_sheets"]["sheet_name"]
        project_id = st.secrets["project_id"]
        bigquery_table = st.secrets["bigquery_table"]
        
        # Crear archivo temporal de credenciales
        with open("temp_credentials.json", "w") as f:
            json.dump(credentials_dict, f)
        credentials_path = "temp_credentials.json"
    else:
        load_dotenv()
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        sheet_name = "proveedores_all"
        project_id = "youtube-analysis-24"
        bigquery_table = "tickets.tickets_all"
    
    return {
        'credentials_path': credentials_path,
        'sheet_id': sheet_id,
        'sheet_name': sheet_name,
        'project_id': project_id,
        'bigquery_table': bigquery_table,
        'is_cloud': IS_CLOUD
    }

# ═══════════════════════════════════════════════════════════
# Mapeos de unificación de proveedores
# ═══════════════════════════════════════════════════════════

PROVEEDOR_UNIFICADO = {
    # YAPUR → 12000001
    1358: 12000001, 1285: 12000001, 1084: 12000001, 463: 12000001,
    1346: 12000001, 1351: 12000001, 1361: 12000001, 1366: 12000001,
    # COCA → 12000002
    1268: 12000002, 1316: 12000002, 1867: 12000002,
    # UNILEVER → 12000003
    503: 12000003, 1313: 12000003, 9: 12000003, 2466: 12000003,
    # ARCOR → 12000004
    181: 12000004, 189: 12000004, 440: 12000004, 1073: 12000004, 193: 12000004,
    # QUILMES → 12000005
    1332: 12000005, 2049: 12000005, 1702: 12000005
}

NOMBRES_UNIFICADOS = {
    12000001: 'YAPUR',
    12000002: 'COCA (Gaseosas y Cervezas)',
    12000003: 'UNILEVER',
    12000004: 'ARCOR',
    12000005: 'QUILMES'
}