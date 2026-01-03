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

# NOMBRES_UNIFICADOS = {
#     12000001: 'YAPUR',
#     12000002: 'COCA (Gaseosas y Cervezas)',
#     12000003: 'UNILEVER',
#     12000004: 'ARCOR',
#     12000005: 'QUILMES'
# }

# Al final del archivo config.py, DESPUÉS de NOMBRES_UNIFICADOS:

# ═══════════════════════════════════════════════════════════════════════════════
# SALTA REFRESCOS - Proveedor virtual creado por agrupación de artículos
# ═══════════════════════════════════════════════════════════════════════════════

SALTA_REFRESCOS_ID = 12000006

ID_LIST_SALTA = [
    115000097, 115000006, 147000154, 147000178, 147000175, 147000174, 147000085, 147000149,
    147000096, 147000097, 147000124, 147000180, 147000179, 147000165, 147000074, 147000075,
    147000166, 147000167, 147000071, 147000072, 147000061, 147000093, 147000063, 147000120,
    147000077, 147000078, 147000157, 147000062, 147000090, 147000076, 147000079, 147000172,
    147000080, 115000095, 115000002, 115000072, 115000096, 115000011, 147000148, 147000147,
    147000117, 147000067, 147000121, 147000109, 147000114, 147000016, 147000164, 147000115,
    147000100, 147000092, 147000116, 147000087, 147000102, 147000064, 147000065, 147000005,
    147000091, 147000068, 147000118, 147000069, 147000119, 147000105, 147000104, 147000103,
    147000030, 147000122, 147000110, 147000133, 147000113, 147000101, 147000004, 147000028,
    147000059, 147000136, 147000132, 147000031, 147000126, 147000127, 147000129, 147000176,
    147000137, 147000144, 147000140, 147000141, 147000155, 147000017, 147000050, 147000052,
    147000051, 147000089, 147000094, 147000112, 147000086, 147000163, 147000106, 147000186,
    147000183, 147000070, 147000073, 147000182, 147000181, 147000177,
    190000033, 190000035, 190000044, 190000112, 190000031, 190000050, 190000079, 190000103, 
    190000057, 147000020
]

# Agregar al diccionario de nombres unificados (modificar la línea existente):
NOMBRES_UNIFICADOS = {
    12000001: 'YAPUR',
    12000002: 'COCA (Gaseosas y Cervezas)',
    12000003: 'UNILEVER',
    12000004: 'ARCOR',
    12000005: 'QUILMES',
    12000006: 'SALTA REFRESCOS'  # ← NUEVO
}