# import streamlit as st
# import pandas as pd
# import os
# from datetime import datetime
# from dotenv import load_dotenv
# import gspread
# from google.oauth2.service_account import Credentials
# from google.cloud import bigquery

# # === CARGAR VARIABLES DE ENTORNO (.env) ===
# load_dotenv()
# CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")  # credenciales para Sheets
# GSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
# SHEET_NAME = "proveedores_all"
# BQ_CREDENTIALS_PATH = os.getenv("BIGQUERY_CREDENTIALS_PATH")  # credenciales para BigQuery

# # === CONFIGURAR PÁGINA ===
# st.set_page_config(page_title="📦 Dashboard Proveedores", layout="wide")
# st.title("📦 Dashboard de Análisis por Proveedor")

# # === CARGAR CREDENCIALES DE SHEETS ===
# SCOPES = [
#     'https://www.googleapis.com/auth/spreadsheets',
#     'https://www.googleapis.com/auth/drive.file'
# ]

# try:
#     creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
#     gc = gspread.authorize(creds)
#     st.success("✅ Credenciales cargadas correctamente.")
# except Exception as e:
#     st.error(f"❌ Error cargando credenciales: {e}")
#     st.stop()

# # === LEER GOOGLE SHEET ===
# @st.cache_data(ttl=3600)
# def leer_google_sheet(sheet_id, sheet_name):
#     spreadsheet = gc.open_by_key(sheet_id)
#     worksheet = spreadsheet.worksheet(sheet_name)
#     data = worksheet.get_all_records()
#     return pd.DataFrame(data)

# try:
#     df = leer_google_sheet(GSHEET_ID, SHEET_NAME)
#     st.success(f"✅ Datos cargados de Google Sheet ({SHEET_NAME}) con {len(df):,} registros.")
# except Exception as e:
#     st.error(f"❌ Error leyendo Google Sheet: {e}")
#     st.stop()

# # === MOSTRAR TABLA DE PROVEEDORES ===
# st.subheader("📊 Vista previa")
# st.dataframe(df, use_container_width=True)

# # === SELECCIÓN DE PROVEEDOR ===
# st.subheader("🔍 Seleccioná un proveedor")
# proveedor_seleccionado = st.selectbox("Proveedor:", sorted(df['proveedor'].dropna().unique()), index=None, placeholder="Buscar proveedor...")

# # === SELECCIÓN DE FECHAS ===
# st.subheader("📅 Seleccioná el período")
# col1, col2 = st.columns(2)
# fecha_inicio = col1.date_input("Fecha de inicio", value=datetime(2025, 1, 1))
# fecha_fin = col2.date_input("Fecha de fin", value=datetime(2025, 7, 1))

# # === FILTRAR ARTÍCULOS DEL PROVEEDOR SELECCIONADO Y CONSULTAR BIGQUERY ===
# if proveedor_seleccionado:
#     idarticulos = df[df['proveedor'] == proveedor_seleccionado]['idarticulo'].dropna().astype(str).unique().tolist()

#     if not idarticulos:
#         st.warning("⚠️ Este proveedor no tiene artículos asociados.")
#         st.stop()

#    #  idarticulo_str = ",".join([f"'{id_}'" for id_ in idarticulos])
#     idarticulo_str = ",".join(map(str, idarticulos))  # sin comillas simples


#     # === CONSULTAR BIGQUERY ===
#     client = bigquery.Client.from_service_account_json(BQ_CREDENTIALS_PATH)
#     query = f"""
#         SELECT fecha_comprobante, idarticulo, descripcion, cantidad_total,
#                costo_total, precio_total, sucursal, familia, subfamilia
#         FROM `youtube-analysis-24.tickets.tickets_all`
#         WHERE idarticulo IN ({idarticulo_str})
#         AND DATE(fecha_comprobante) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
#     """

#     try:
#         df_tickets = client.query(query).result().to_dataframe()
#         st.success(f"✅ {len(df_tickets):,} registros encontrados en tickets_all.")
#         st.dataframe(df_tickets, use_container_width=True)
#     except Exception as e:
#         st.error(f"❌ Error al consultar BigQuery: {e}")
#         st.stop()

#     # === KPIs DEL ANÁLISIS ===
#     st.subheader("📈 Indicadores del proveedor")
#     col1, col2, col3 = st.columns(3)
#     col1.metric("🛒 Total vendido", f"${df_tickets['precio_total'].sum():,.0f}")
#     col2.metric("💸 Costo total", f"${df_tickets['costo_total'].sum():,.0f}")
#     col3.metric("📦 Artículos vendidos", f"{df_tickets['cantidad_total'].sum():,.0f}")

############################################################################################################

# 📁 Estructura recomendada del proyecto:

# CUCHER_STREAMLIT/
# ├── app.py
# ├── requirements.txt
# ├── .env  ➔ solo local
# ├── .gitignore
# ├── .streamlit/
# │   ├── config.toml
# │   └── secrets.toml  ➔ solo en cloud

# # === app.py ===
import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import gspread
from google.cloud import bigquery
from google.oauth2.service_account import Credentials

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

# === CONECTAR A GOOGLE SHEETS ===
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
try:
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    gc = gspread.authorize(creds)
except Exception as e:
    st.error(f"Error al cargar credenciales de Google Sheets: {e}")
    st.stop()

try:
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    gc = gspread.authorize(creds)
    st.success("✅ Autenticación Google Sheets exitosa")
except Exception as e:
    st.error(f"❌ Error autenticando Google Sheets: {e}")
    st.stop()


@st.cache_data(ttl=3600)
def leer_google_sheet(sheet_id, sheet_name):
    spreadsheet = gc.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(sheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# def leer_google_sheet(sheet_id, sheet_name):
#     ws = gc.open_by_key(sheet_id).worksheet(sheet_name)
#     return pd.DataFrame(ws.get_all_records())
try:
    df = leer_google_sheet(sheet_id, sheet_name)
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
    ids = df[df['proveedor'] == proveedor]['idarticulo'].dropna().astype(str).unique()
    if not ids.any():
        st.warning("Este proveedor no tiene artículos asociados.")
        st.stop()

    id_str = ','.join([f"'{id_}'" for id_ in ids])

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



############################################################################################################

# """
# 🏪 SISTEMA DE ANÁLISIS POR PROVEEDOR - STREAMLIT CLOUD
# =====================================================
# Versión optimizada para deploy en Streamlit Cloud
# Conexión directa a BigQuery y Google Sheets

# Autor: Sistema de Análisis Empresarial
# Versión: 1.0 - Cloud Edition
# """

# import streamlit as st

# # IMPORTANTE: set_page_config debe ser lo PRIMERO
# st.set_page_config(
#     page_title="🏪 Análisis por Proveedor",
#     page_icon="🏪",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Ahora sí, importar el resto
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
# import numpy as np
# from datetime import datetime, timedelta
# import json
# import gspread
# from google.oauth2.service_account import Credentials
# from google.cloud import bigquery
# import io
# import warnings
# warnings.filterwarnings('ignore')

# # CSS personalizado
# st.markdown("""
# <style>
#     .main-header {
#         background: linear-gradient(90deg, #2E8B57, #32CD32);
#         padding: 2rem;
#         border-radius: 10px;
#         margin-bottom: 2rem;
#         text-align: center;
#         color: white;
#     }
#     .metric-card {
#         background: #f8f9fa;
#         padding: 1rem;
#         border-radius: 8px;
#         border-left: 4px solid #2E8B57;
#         margin: 0.5rem 0;
#     }
#     .stSelectbox > div > div {
#         background-color: #f1f3f6;
#     }
# </style>
# """, unsafe_allow_html=True)

# class ProveedorDashboard:
#     """Dashboard de análisis por proveedor"""
    
#     def __init__(self):
#         self.df_proveedores = None
#         self.df_tickets = None
#         self.client_bq = None
#         self.gc_sheets = None
        
#         # Inicializar session state
#         if 'data_loaded' not in st.session_state:
#             st.session_state.data_loaded = False
#         if 'analysis_done' not in st.session_state:
#             st.session_state.analysis_done = False
    
#     def setup_connections(self):
#         """Configurar conexiones a Google Sheets y BigQuery"""
#         try:
#             # Configurar Google Sheets
#             if st.secrets.get("google_credentials"):
#                 credentials_info = st.secrets["google_credentials"]
#                 credentials = Credentials.from_service_account_info(
#                     credentials_info,
#                     scopes=[
#                         'https://www.googleapis.com/auth/spreadsheets',
#                         'https://www.googleapis.com/auth/drive.file'
#                     ]
#                 )
#                 self.gc_sheets = gspread.authorize(credentials)
                
#                 # Configurar BigQuery
#                 bq_credentials = Credentials.from_service_account_info(
#                     credentials_info
#                 )
#                 self.client_bq = bigquery.Client(credentials=bq_credentials)
                
#                 return True
#             else:
#                 st.error("❌ No se encontraron credenciales en los secrets")
#                 return False
                
#         except Exception as e:
#             st.error(f"❌ Error configurando conexiones: {e}")
#             return False
    
#     def load_proveedores_data(self):
#         """Cargar datos de proveedores desde Google Sheets"""
#         try:
#             sheet_id = st.secrets["google_sheets"]["sheet_id"]
#             sheet_name = st.secrets["google_sheets"]["sheet_name"]
            
#             with st.spinner("📊 Cargando datos de proveedores..."):
#                 spreadsheet = self.gc_sheets.open_by_key(sheet_id)
#                 worksheet = spreadsheet.worksheet(sheet_name)
#                 data = worksheet.get_all_records()
#                 self.df_proveedores = pd.DataFrame(data)
                
#                 # Limpiar datos
#                 self.df_proveedores['proveedor'] = self.df_proveedores['proveedor'].astype(str).str.strip().str.upper()
#                 self.df_proveedores['idarticulo'] = self.df_proveedores['idarticulo'].astype(str)
                
#                 st.success(f"✅ {len(self.df_proveedores):,} registros de proveedores cargados")
#                 return True
                
#         except Exception as e:
#             st.error(f"❌ Error cargando proveedores: {e}")
#             return False
    
#     def query_tickets_data(self, proveedor, fecha_inicio, fecha_fin):
#         """Consultar datos de tickets desde BigQuery"""
#         try:
#             # Obtener artículos del proveedor
#             idarticulos = self.df_proveedores[
#                 self.df_proveedores['proveedor'] == proveedor
#             ]['idarticulo'].unique().tolist()
            
#             if not idarticulos:
#                 st.warning("⚠️ No se encontraron artículos para este proveedor")
#                 return False
            
#             # Preparar lista de IDs para la query
#             idarticulo_str = ",".join([f"'{id_}'" for id_ in idarticulos])
            
#             # Query BigQuery
#             project_id = st.secrets.get("project_id")
#             bigquery_table = st.secrets.get("bigquery_table")
            
#             query = f"""
#             SELECT 
#                 fecha_comprobante, 
#                 idarticulo, 
#                 descripcion, 
#                 cantidad_total,
#                 costo_total, 
#                 precio_total, 
#                 sucursal, 
#                 familia, 
#                 subfamilia
#             FROM `{project_id}.{bigquery_table}`
#             WHERE idarticulo IN ({idarticulo_str})
#             AND DATE(fecha_comprobante) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
#             ORDER BY fecha_comprobante DESC
#             """
            
#             with st.spinner("🔍 Consultando tickets en BigQuery..."):
#                 self.df_tickets = self.client_bq.query(query).result().to_dataframe()
                
#                 if len(self.df_tickets) == 0:
#                     st.warning("⚠️ No se encontraron tickets en el período seleccionado")
#                     return False
                
#                 # Procesar datos
#                 self.df_tickets['fecha_comprobante'] = pd.to_datetime(self.df_tickets['fecha_comprobante'])
#                 self.df_tickets['utilidad'] = self.df_tickets['precio_total'] - self.df_tickets['costo_total']
#                 self.df_tickets['margen_porcentual'] = np.where(
#                     self.df_tickets['precio_total'] > 0,
#                     (self.df_tickets['utilidad'] / self.df_tickets['precio_total']) * 100,
#                     0
#                 )
                
#                 st.success(f"✅ {len(self.df_tickets):,} tickets encontrados")
#                 return True
                
#         except Exception as e:
#             st.error(f"❌ Error consultando BigQuery: {e}")
#             return False
    
#     def show_kpis(self, proveedor):
#         """Mostrar KPIs principales"""
#         st.subheader(f"📈 Indicadores - {proveedor}")
        
#         # Calcular métricas
#         total_ventas = self.df_tickets['precio_total'].sum()
#         total_costos = self.df_tickets['costo_total'].sum()
#         total_utilidad = self.df_tickets['utilidad'].sum()
#         total_cantidad = self.df_tickets['cantidad_total'].sum()
#         num_tickets = len(self.df_tickets)
#         productos_unicos = self.df_tickets['idarticulo'].nunique()
        
#         # Mostrar métricas en columnas
#         col1, col2, col3, col4 = st.columns(4)
        
#         with col1:
#             st.metric("💰 Ventas Totales", f"${total_ventas:,.0f}")
#             st.metric("🧾 Total Tickets", f"{num_tickets:,}")
        
#         with col2:
#             st.metric("💸 Costos Totales", f"${total_costos:,.0f}")
#             st.metric("🏷️ Productos Únicos", f"{productos_unicos:,}")
        
#         with col3:
#             st.metric("📈 Utilidad Total", f"${total_utilidad:,.0f}")
#             st.metric("📦 Cantidad Vendida", f"{total_cantidad:,.0f}")
        
#         with col4:
#             margen_promedio = (total_utilidad / total_ventas * 100) if total_ventas > 0 else 0
#             ticket_promedio = total_ventas / num_tickets if num_tickets > 0 else 0
#             st.metric("🎯 Margen Promedio", f"{margen_promedio:.1f}%")
#             st.metric("💳 Ticket Promedio", f"${ticket_promedio:,.0f}")
    
#     def show_top_products(self):
#         """Mostrar top productos"""
#         st.subheader("🏆 Top 15 Productos")
        
#         # Agrupar por producto
#         productos = self.df_tickets.groupby(['idarticulo', 'descripcion']).agg({
#             'precio_total': 'sum',
#             'costo_total': 'sum',
#             'utilidad': 'sum',
#             'cantidad_total': 'sum',
#             'margen_porcentual': 'mean'
#         }).round(2)
        
#         productos.columns = ['Ventas', 'Costos', 'Utilidad', 'Cantidad', 'Margen %']
#         productos['Participación %'] = (productos['Ventas'] / productos['Ventas'].sum() * 100).round(1)
        
#         # Ordenar por ventas
#         top_productos = productos.sort_values('Ventas', ascending=False).head(15)
        
#         # Mostrar tabla
#         st.dataframe(
#             top_productos,
#             use_container_width=True,
#             column_config={
#                 "Ventas": st.column_config.NumberColumn("Ventas", format="$%.0f"),
#                 "Costos": st.column_config.NumberColumn("Costos", format="$%.0f"),
#                 "Utilidad": st.column_config.NumberColumn("Utilidad", format="$%.0f"),
#                 "Cantidad": st.column_config.NumberColumn("Cantidad", format="%.0f"),
#                 "Margen %": st.column_config.NumberColumn("Margen %", format="%.1f%%"),
#                 "Participación %": st.column_config.NumberColumn("Participación %", format="%.1f%%")
#             }
#         )
        
#         return top_productos
    
#     def show_charts(self, top_productos):
#         """Mostrar visualizaciones"""
#         st.subheader("📊 Visualizaciones")
        
#         # Tab para diferentes gráficas
#         tab1, tab2, tab3 = st.tabs(["📈 Productos", "📅 Evolución", "🎯 Análisis"])
        
#         with tab1:
#             col1, col2 = st.columns(2)
            
#             with col1:
#                 # Top 10 productos por ventas
#                 top_10 = top_productos.head(10)
#                 fig_ventas = px.bar(
#                     x=top_10['Ventas'],
#                     y=[desc[:30] + '...' if len(desc) > 30 else desc 
#                        for _, desc in top_10.index],
#                     orientation='h',
#                     title="🏆 Top 10 Productos por Ventas",
#                     labels={'x': 'Ventas ($)', 'y': 'Producto'},
#                     color=top_10['Ventas'],
#                     color_continuous_scale='Greens'
#                 )
#                 fig_ventas.update_layout(height=500, showlegend=False)
#                 st.plotly_chart(fig_ventas, use_container_width=True)
            
#             with col2:
#                 # Top 10 productos por margen
#                 top_10_margen = top_productos.nlargest(10, 'Margen %')
#                 fig_margen = px.bar(
#                     x=top_10_margen['Margen %'],
#                     y=[desc[:30] + '...' if len(desc) > 30 else desc 
#                        for _, desc in top_10_margen.index],
#                     orientation='h',
#                     title="📈 Top 10 Productos por Margen",
#                     labels={'x': 'Margen (%)', 'y': 'Producto'},
#                     color=top_10_margen['Margen %'],
#                     color_continuous_scale='Blues'
#                 )
#                 fig_margen.update_layout(height=500, showlegend=False)
#                 st.plotly_chart(fig_margen, use_container_width=True)
        
#         with tab2:
#             # Evolución temporal
#             self.df_tickets['fecha'] = self.df_tickets['fecha_comprobante'].dt.date
#             temporal = self.df_tickets.groupby('fecha').agg({
#                 'precio_total': 'sum',
#                 'utilidad': 'sum',
#                 'cantidad_total': 'sum'
#             }).reset_index()
            
#             col1, col2 = st.columns(2)
            
#             with col1:
#                 fig_ventas_tiempo = px.line(
#                     temporal, x='fecha', y='precio_total',
#                     title="📅 Evolución de Ventas Diarias",
#                     labels={'precio_total': 'Ventas ($)', 'fecha': 'Fecha'}
#                 )
#                 fig_ventas_tiempo.update_traces(line_color='#2E8B57', line_width=3)
#                 st.plotly_chart(fig_ventas_tiempo, use_container_width=True)
            
#             with col2:
#                 fig_utilidad_tiempo = px.line(
#                     temporal, x='fecha', y='utilidad',
#                     title="📈 Evolución de Utilidad Diaria", 
#                     labels={'utilidad': 'Utilidad ($)', 'fecha': 'Fecha'}
#                 )
#                 fig_utilidad_tiempo.update_traces(line_color='#32CD32', line_width=3)
#                 st.plotly_chart(fig_utilidad_tiempo, use_container_width=True)
        
#         with tab3:
#             col1, col2 = st.columns(2)
            
#             with col1:
#                 # Distribución por familia
#                 if 'familia' in self.df_tickets.columns:
#                     familia_stats = self.df_tickets.groupby('familia')['precio_total'].sum().reset_index()
#                     fig_familia = px.pie(
#                         familia_stats, values='precio_total', names='familia',
#                         title="🌿 Distribución por Familia"
#                     )
#                     st.plotly_chart(fig_familia, use_container_width=True)
            
#             with col2:
#                 # Distribución por sucursal
#                 if 'sucursal' in self.df_tickets.columns:
#                     sucursal_stats = self.df_tickets.groupby('sucursal')['precio_total'].sum().reset_index()
#                     fig_sucursal = px.pie(
#                         sucursal_stats, values='precio_total', names='sucursal',
#                         title="🏪 Distribución por Sucursal"
#                     )
#                     st.plotly_chart(fig_sucursal, use_container_width=True)
    
#     def export_data(self):
#         """Exportar datos"""
#         st.subheader("📁 Exportar Datos")
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             # Exportar CSV
#             csv_buffer = self.df_tickets.to_csv(index=False)
#             st.download_button(
#                 label="📊 Descargar CSV",
#                 data=csv_buffer,
#                 file_name=f"tickets_proveedor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
#                 mime="text/csv"
#             )
        
#         with col2:
#             # Exportar resumen
#             resumen = {
#                 'total_ventas': float(self.df_tickets['precio_total'].sum()),
#                 'total_utilidad': float(self.df_tickets['utilidad'].sum()),
#                 'num_tickets': len(self.df_tickets),
#                 'productos_unicos': int(self.df_tickets['idarticulo'].nunique())
#             }
            
#             json_buffer = json.dumps(resumen, indent=2)
#             st.download_button(
#                 label="📋 Descargar Resumen JSON",
#                 data=json_buffer,
#                 file_name=f"resumen_proveedor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
#                 mime="application/json"
#             )
    
#     def run(self):
#         """Ejecutar dashboard"""
#         # Header
#         st.markdown("""
#         <div class="main-header">
#             <h1>🏪 Dashboard de Análisis por Proveedor</h1>
#             <p>Sistema profesional de análisis empresarial con BigQuery y Google Sheets</p>
#         </div>
#         """, unsafe_allow_html=True)
        
#         # Sidebar para configuración
#         with st.sidebar:
#             st.header("⚙️ Configuración")
            
#             # Información de conexión
#             st.info("""
#             📊 **Fuentes de Datos:**
#             - Google Sheets: Proveedores
#             - BigQuery: Tickets de ventas
#             """)
            
#             # Debug info
#             if st.checkbox("🐛 Modo Debug"):
#                 st.write("**Secrets disponibles:**")
#                 available_secrets = [key for key in st.secrets.keys()]
#                 st.write(available_secrets)
        
#         # Configurar conexiones
#         if not self.setup_connections():
#             st.stop()
        
#         # Cargar datos de proveedores
#         if not self.load_proveedores_data():
#             st.stop()
        
#         # Mostrar vista previa de proveedores
#         with st.expander("📊 Vista previa de proveedores"):
#             st.dataframe(
#                 self.df_proveedores.head(10), 
#                 use_container_width=True
#             )
        
#         # Interfaz principal
#         st.subheader("🔍 Configurar Análisis")
        
#         col1, col2 = st.columns([2, 1])
        
#         with col1:
#             # Selector de proveedor
#             proveedores_unicos = sorted(self.df_proveedores['proveedor'].dropna().unique())
#             proveedor_seleccionado = st.selectbox(
#                 "🏪 Seleccionar Proveedor:",
#                 options=proveedores_unicos,
#                 index=None,
#                 placeholder="Buscar proveedor..."
#             )
        
#         with col2:
#             # Rangos de fecha
#             col_inicio, col_fin = st.columns(2)
#             with col_inicio:
#                 fecha_inicio = st.date_input(
#                     "📅 Fecha Inicio:",
#                     value=datetime.now().date() - timedelta(days=30)
#                 )
#             with col_fin:
#                 fecha_fin = st.date_input(
#                     "📅 Fecha Fin:",
#                     value=datetime.now().date()
#                 )
        
#         # Botón de análisis
#         if st.button("🔍 Realizar Análisis", type="primary", use_container_width=True):
#             if not proveedor_seleccionado:
#                 st.error("❌ Debe seleccionar un proveedor")
#             elif fecha_inicio > fecha_fin:
#                 st.error("❌ La fecha de inicio debe ser menor que la fecha de fin")
#             else:
#                 # Realizar consulta
#                 if self.query_tickets_data(proveedor_seleccionado, fecha_inicio, fecha_fin):
#                     st.session_state.analysis_done = True
#                     st.rerun()
        
#         # Mostrar resultados si hay análisis
#         if st.session_state.get('analysis_done', False) and self.df_tickets is not None:
#             # KPIs
#             self.show_kpis(proveedor_seleccionado)
            
#             # Tabs principales
#             tab1, tab2, tab3, tab4 = st.tabs([
#                 "🏆 Top Productos", "📊 Visualizaciones", 
#                 "📋 Datos Detallados", "📁 Exportar"
#             ])
            
#             with tab1:
#                 top_productos = self.show_top_products()
            
#             with tab2:
#                 if 'top_productos' in locals():
#                     self.show_charts(top_productos)
            
#             with tab3:
#                 st.subheader("📋 Datos Detallados")
#                 st.dataframe(
#                     self.df_tickets,
#                     use_container_width=True,
#                     column_config={
#                         "precio_total": st.column_config.NumberColumn("Precio Total", format="$%.2f"),
#                         "costo_total": st.column_config.NumberColumn("Costo Total", format="$%.2f"),
#                         "utilidad": st.column_config.NumberColumn("Utilidad", format="$%.2f"),
#                         "margen_porcentual": st.column_config.NumberColumn("Margen %", format="%.1f%%")
#                     }
#                 )
            
#             with tab4:
#                 self.export_data()


# def main():
#     """Función principal"""
#     dashboard = ProveedorDashboard()
#     dashboard.run()


# if __name__ == "__main__":
#     main()




# ## EJECUTAR : streamlit run proveedores_streamlit.py
