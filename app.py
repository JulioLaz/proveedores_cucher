import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import json
from babel.dates import format_date
from babel import Locale
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.cloud import bigquery
import warnings
import io
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, NamedStyle
from openpyxl.utils.dataframe import dataframe_to_rows
import time
warnings.filterwarnings('ignore')

from limpiar_datos import limpiar_datos
from insight_ABC import generar_insight_cantidad, generar_insight_ventas, generar_insight_margen, generar_insight_abc_completo, generar_insight_pareto
from generar_excel import generar_excel
from custom_css import custom_css, custom_sidebar
from analisis_quiebre import analizar_quiebre
from quiebre_streamlit_view import mostrar_analisis_quiebre_detallado
from excel_proveedor import ProveedorAnalyzerStreamlit

# 👇 NUEVA LÍNEA - Agregar al inicio después de los imports
from components.executive_summary import show_executive_summary as render_executive_summary
from components.products_analysis import show_products_analysis as render_products_analysis  # 👈 NUEVA LÍNEA
from components.temporal_analysis import show_temporal_analysis as render_temporal_analysis  # 👈 NUEVA LÍNEA
from components.advanced_analysis import show_advanced_analysis as render_advanced_analysis  # 👈 NUEVA LÍNEA
from components.global_dashboard import show_global_dashboard

locale = Locale.parse('es_AR')

def format_abbr(x):
    if x >= 1_000_000: return f"${x/1_000_000:.1f}M"
    elif x >= 1_000: return f"${x/1_000:.0f}K"
    else: return f"${x:.0f}"

# === CONFIGURACION DE PAGINA ===
st.set_page_config(page_title="Proveedores", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# === CARGAR CSS PERSONALIZADO ===
st.markdown(custom_css(), unsafe_allow_html=True)

### OCULTAR TOOLBAR COMPLETA

# st.markdown("""
#     <style>
#     div[data-testid="stToolbar"] {
#         pointer-events: none !important;
#         opacity: 0 !important;
#     }
#     </style>
# """, unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Ocultar y desactivar el botón Share */
    span[data-testid="stToolbarActionButtonLabel"] {
        display: none !important;
        pointer-events: none !important;
        visibility: hidden !important;
    }
    div[data-testid="stToolbarActionButtonIcon"] {
        display: none !important;
        pointer-events: none !important;
        visibility: hidden !important;
    }
    </style>
""", unsafe_allow_html=True)



# === DETECTAR ENTORNO ===
IS_CLOUD = "gcp_service_account" in st.secrets if hasattr(st, 'secrets') else False

from google.cloud import bigquery

def query_resultados_idarticulo(credentials_path, project_id, dataset, table):
    try:
        client = bigquery.Client.from_service_account_json(credentials_path)

        query = f"""
            SELECT idarticulo, descripcion, familia, subfamilia,
                   stk_corrientes, stk_express, stk_formosa, stk_hiper, stk_TIROL, stk_central, STK_TOTAL,PRESUPUESTO,
                   ALERTA_STK_Tirol_Central, dias_cobertura, nivel_riesgo, accion_gralporc, PRESU_accion_gral,
                   cnt_corregida, presu_10dias, presu_20dias, presu_33dias, exceso_STK, costo_exceso_STK,
                   margen_porc_all, margen_a90, margen_a30, analisis_margen, estrategia, prioridad,
                   mes_pico, mes_bajo, mes_actual, ranking_mes, meses_act_estac
            FROM `{project_id}.{dataset}.{table}`
            WHERE idarticulo IS NOT NULL
        """

        df = client.query(query).to_dataframe()
        return df

    except Exception as e:
        st.error(f"❌ Error al consultar BigQuery: {e}")
        return pd.DataFrame()

class InventoryDashboard:
    """
    Dashboard estratégico para análisis de inventario y gestión de stock
    """
    
    def __init__(self):
        pass
        
    def load_and_validate_data(self, df):
        """Carga y validación de datos con medición de tiempo"""
        start_time = time.time()
        
        st.markdown("### 🔄 Procesando Datos para Análisis Estratégico...")
        progress_bar = st.progress(0)
        
        try:
            # Validaciones básicas
            progress_bar.progress(25)
            required_cols = ['idarticulo', 'nivel_riesgo', 'prioridad', 'dias_cobertura']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.warning(f"⚠️ Algunas columnas no están disponibles: {missing_cols}")
                # Crear columnas faltantes con valores por defecto
                for col in missing_cols:
                    if col == 'nivel_riesgo':
                        df[col] = '🟡 Medio'
                    elif col == 'prioridad':
                        df[col] = 5
                    elif col == 'dias_cobertura':
                        df[col] = 30
                        
            progress_bar.progress(50)
            
            # Limpieza de datos
            df_clean = df.copy()
            
            # Convertir columnas numéricas
            numeric_cols = ['prioridad', 'dias_cobertura', 'STK_TOTAL', 'costo_unit', 
                          'total_abastecer', 'cnt_corregida', 'PRESUPUESTO']
            
            for col in numeric_cols:
                if col in df_clean.columns:
                    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
            
            progress_bar.progress(75)
            
            # Crear métricas derivadas
            df_clean = self.create_derived_metrics(df_clean)
            
            progress_bar.progress(100)
            
            load_time = time.time() - start_time
            st.success(f"✅ Datos procesados exitosamente en {load_time:.2f} segundos")
            st.info(f"📊 Dataset: {len(df_clean):,} productos | {len(df_clean.columns)} columnas")
            
            progress_bar.empty()
            return df_clean
            
        except Exception as e:
            st.error(f"❌ Error en procesamiento de datos: {e}")
            progress_bar.empty()
            return None
    
    def create_derived_metrics(self, df):
        """Crear métricas derivadas para análisis"""
        
        # Crear columnas de valor perdido y costo exceso si no existen
        if 'valor_perdido_TOTAL' not in df.columns:
            df['valor_perdido_TOTAL'] = 0
        if 'costo_exceso_STK' not in df.columns:
            df['costo_exceso_STK'] = 0
        if 'exceso_STK' not in df.columns:
            df['exceso_STK'] = 0
            
        # Impacto financiero total
        df['impacto_financiero_total'] = (
            df.get('valor_perdido_TOTAL', 0) + df.get('costo_exceso_STK', 0)
        )
        
        # Eficiencia de inventario
        df['eficiencia_inventario'] = np.where(
            df['dias_cobertura'] > 0,
            1 / (1 + df['dias_cobertura'] / 30),  # Normalizado
            0
        )
        
        # Categoría de rotación
        df['categoria_rotacion'] = pd.cut(
            df['dias_cobertura'], 
            bins=[-1, 15, 30, 60, float('inf')], 
            labels=['🔴 Crítica', '🟠 Alta', '🟡 Normal', '🟢 Lenta']
        )
        
        return df
    
    def show_main_kpis(self, df):
        """Mostrar KPIs principales"""
        st.markdown("### 📈 KPIs Principales del Inventario")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total_productos = len(df)
            st.metric("📦 Total Productos", f"{total_productos:,}")
            
        with col2:
            productos_criticos = len(df[df['nivel_riesgo'].str.contains('🔴', na=False)])
            st.metric("🚨 Productos Críticos", productos_criticos)
            
        with col3:
            valor_perdido = df.get('valor_perdido_TOTAL', pd.Series([0])).sum()
            st.metric("💸 Valor Perdido", f"${valor_perdido:,.0f}")
            
        with col4:
            stock_total = df['STK_TOTAL'].sum()
            st.metric("📊 Stock Total", f"{stock_total:,.0f}")
            
        with col5:
            productos_sin_stock = len(df[df['STK_TOTAL'] == 0])
            st.metric("❌ Sin Stock", productos_sin_stock)
    
    def tab_matriz_estrategica(self, df):
        """Matriz de priorización estratégica"""
        st.markdown("### 🎯 Matriz de Priorización Estratégica")
        
        start_time = time.time()
        
        # Crear grupos estratégicos
        def clasificar_urgencia(row):
            if '🔴' in str(row.get('nivel_riesgo', '')) and row.get('prioridad', 10) <= 3:
                return "🚨 CRÍTICO"
            elif '🟠' in str(row.get('nivel_riesgo', '')) and row.get('dias_cobertura', 100) < 20:
                return "⚠️ URGENTE"
            elif '🟡' in str(row.get('nivel_riesgo', '')) and row.get('exceso_STK', 0) > 0:
                return "👀 MONITOREO"
            else:
                return "✅ ESTABLE"
        
        df['grupo_urgencia'] = df.apply(clasificar_urgencia, axis=1)
        
        # Crear resumen por grupo
        resumen_urgencia = df.groupby('grupo_urgencia').agg({
            'idarticulo': 'count',
            'impacto_financiero_total': 'sum',
            'PRESUPUESTO': 'sum'
        }).round(0)
        
        resumen_urgencia.columns = ['Productos', 'Impacto Total $', 'Presupuesto $']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Distribución por Urgencia")
            fig = px.pie(
                values=resumen_urgencia['Productos'],
                names=resumen_urgencia.index,
                title="Productos por Nivel de Urgencia"
            )
            st.plotly_chart(fig, width="stretch")
        
        with col2:
            st.markdown("#### 💰 Resumen Financiero por Grupo")
            st.dataframe(resumen_urgencia, width="stretch")
        
        # Productos críticos
        st.markdown("#### 🚨 Productos que Requieren Atención Inmediata")
        criticos = df[df['grupo_urgencia'].isin(["🚨 CRÍTICO", "⚠️ URGENTE"])][
            ['idarticulo', 'descripcion', 'familia', 'nivel_riesgo', 'dias_cobertura', 
             'STK_TOTAL', 'prioridad']
        ].head(15)
        
        if not criticos.empty:
            st.dataframe(criticos, width="stretch")
        else:
            st.success("✅ No hay productos en estado crítico")
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_performance_sucursal(self, df):
        """Análisis de performance por sucursal"""
        st.markdown("### 🏪 Performance por Sucursal")
        
        start_time = time.time()
        
        # Definir sucursales disponibles
        sucursal_columns = [col for col in df.columns if col.startswith('stk_')]
        sucursales_data = []
        
        for col in sucursal_columns:
            sucursal_name = col.replace('stk_', '').title()
            stock_total = df[col].sum()
            productos_con_stock = len(df[df[col] > 0])
            productos_sin_stock = len(df[df[col] == 0])
            
            sucursales_data.append({
                'Sucursal': sucursal_name,
                'Stock Total': stock_total,
                'Productos con Stock': productos_con_stock,
                'Productos sin Stock': productos_sin_stock,
                'Eficiencia %': round((productos_con_stock / len(df)) * 100, 1) if len(df) > 0 else 0
            })
        
        if sucursales_data:
            df_sucursales = pd.DataFrame(sucursales_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Stock Total por Sucursal")
                fig = px.bar(
                    df_sucursales,
                    x='Sucursal',
                    y='Stock Total',
                    title="Distribución de Stock",
                    color='Stock Total'
                )
                st.plotly_chart(fig, width="stretch")
            
            with col2:
                st.markdown("#### 🎯 Eficiencia por Sucursal")
                fig = px.bar(
                    df_sucursales,
                    x='Sucursal',
                    y='Eficiencia %',
                    title="% de Productos con Stock",
                    color='Eficiencia %',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, width="stretch")
            
            st.markdown("#### 📋 Resumen Detallado")
            st.dataframe(df_sucursales, width="stretch")
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_gestion_inventario(self, df):
        """Gestión de inventario"""
        st.markdown("### 📦 Gestión Estratégica de Inventario")
        
        start_time = time.time()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📈 Distribución por Rotación")
            if 'categoria_rotacion' in df.columns:
                rotacion_counts = df['categoria_rotacion'].value_counts()
                fig = px.pie(
                    values=rotacion_counts.values,
                    names=rotacion_counts.index,
                    title="Productos por Velocidad de Rotación"
                )
                st.plotly_chart(fig, width="stretch")
        
        with col2:
            st.markdown("#### 📊 TOP 10 - Mayor Presupuesto")
            top_presupuesto = df.nlargest(10, 'PRESUPUESTO')[
                ['descripcion', 'PRESUPUESTO', 'familia', 'prioridad']
            ]
            
            if not top_presupuesto.empty:
                fig = px.bar(
                    top_presupuesto,
                    x='PRESUPUESTO',
                    y='descripcion',
                    title="Productos con Mayor Inversión Requerida",
                    orientation='h'
                )
                st.plotly_chart(fig, width="stretch")
        
        # Análisis de cobertura
        st.markdown("#### 🛡️ Análisis de Días de Cobertura")
        
        col3, col4, col5 = st.columns(3)
        
        with col3:
            cobertura_critica = len(df[df['dias_cobertura'] < 15])
            st.metric("🔴 Cobertura Crítica", f"{cobertura_critica} productos")
        
        with col4:
            cobertura_optima = len(df[(df['dias_cobertura'] >= 15) & (df['dias_cobertura'] <= 45)])
            st.metric("🟢 Cobertura Óptima", f"{cobertura_optima} productos")
        
        with col5:
            cobertura_exceso = len(df[df['dias_cobertura'] > 60])
            st.metric("🟡 Exceso Cobertura", f"{cobertura_exceso} productos")
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_analisis_familia(self, df):
        """Análisis por familia"""
        st.markdown("### 📊 Análisis por Familia de Productos")
        
        start_time = time.time()
        
        if 'familia' in df.columns:
            familia_stats = df.groupby('familia').agg({
                'idarticulo': 'count',
                'STK_TOTAL': 'sum',
                'PRESUPUESTO': 'sum',
                'impacto_financiero_total': 'sum'
            }).round(0)
            
            familia_stats.columns = ['Productos', 'Stock Total', 'Presupuesto', 'Impacto Total']
            familia_stats = familia_stats.sort_values('Presupuesto', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🏷️ TOP Familias por Presupuesto")
                top_familias = familia_stats.head(10)
                fig = px.bar(
                    x=top_familias.index,
                    y=top_familias['Presupuesto'],
                    title="Inversión Requerida por Familia"
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, width="stretch")
            
            with col2:
                st.markdown("#### 📦 Distribución de Productos")
                fig = px.pie(
                    values=familia_stats['Productos'],
                    names=familia_stats.index,
                    title="% de Productos por Familia"
                )
                st.plotly_chart(fig, width="stretch")
            
            st.markdown("#### 📋 Resumen Detallado por Familia")
            st.dataframe(familia_stats, width="stretch")
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_acciones_inmediatas(self, df):
        """Acciones inmediatas"""
        st.markdown("### ⚡ Plan de Acción Inmediata")
        
        start_time = time.time()
        
        # Crear score de prioridad
        df['score_prioridad'] = (
            (df.get('impacto_financiero_total', 0) * 0.4) +
            ((11 - df['prioridad']) * 100 * 0.3) +
            (df['PRESUPUESTO'] * 0.3)
        )
        
        # TOP 20 acciones
        top_acciones = df.nlargest(20, 'score_prioridad')[
            ['idarticulo', 'descripcion', 'familia', 'nivel_riesgo', 
             'dias_cobertura', 'STK_TOTAL', 'PRESUPUESTO', 'prioridad']
        ]
        
        # Determinar tipo de acción
        def determinar_accion(row):
            if row['STK_TOTAL'] == 0:
                return "🔄 REABASTECER URGENTE"
            elif row['dias_cobertura'] < 15:
                return "⚠️ AUMENTAR STOCK"
            elif row['PRESUPUESTO'] > 0:
                return "💰 INVERTIR"
            else:
                return "👀 MONITOREAR"
        
        top_acciones['Acción Recomendada'] = top_acciones.apply(determinar_accion, axis=1)
        
        st.markdown("#### 🎯 TOP 20 - Acciones Prioritarias")
        st.dataframe(top_acciones.drop(['score_prioridad'], axis=1, errors='ignore'), width="stretch")
        
        # Resumen de acciones
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Tipos de Acción")
            resumen_acciones = top_acciones['Acción Recomendada'].value_counts()
            fig = px.pie(
                values=resumen_acciones.values,
                names=resumen_acciones.index,
                title="Distribución de Acciones Recomendadas"
            )
            st.plotly_chart(fig, width="stretch")
        
        with col2:
            st.markdown("#### 💰 Inversión Requerida")
            inversion_total = top_acciones['PRESUPUESTO'].sum()
            productos_criticos = len(top_acciones[top_acciones['STK_TOTAL'] == 0])
            
            st.metric("💵 Inversión Total", f"${inversion_total:,.0f}")
            st.metric("🚨 Productos Sin Stock", productos_criticos)
            st.metric("📋 Acciones Totales", len(top_acciones))
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")

class ProveedorDashboard:

    # Mapeos de unificación de proveedores
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

    def __init__(self):
        self.df_proveedores = None
        self.df_tickets = None
        self.setup_credentials()
        
        if 'analysis_data' not in st.session_state:
            st.session_state.analysis_data = None
        if 'selected_proveedor' not in st.session_state:
            st.session_state.selected_proveedor = None
    
    def setup_credentials(self):
        """Configurar credenciales según el entorno"""
        if IS_CLOUD:
            self.credentials_dict = dict(st.secrets["gcp_service_account"])
            self.sheet_id = st.secrets["google_sheets"]["sheet_id"]
            self.sheet_name = st.secrets["google_sheets"]["sheet_name"]
            self.project_id = st.secrets["project_id"]
            self.bigquery_table = st.secrets["bigquery_table"]
            
            with open("temp_credentials.json", "w") as f:
                json.dump(self.credentials_dict, f)
            self.credentials_path = "temp_credentials.json"
        else:
            load_dotenv()
            self.credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
            self.sheet_id = os.getenv("GOOGLE_SHEET_ID")
            self.sheet_name = "proveedores_all"
            self.project_id = "youtube-analysis-24"
            self.bigquery_table = "tickets.tickets_all"
    
    # @st.cache_data(ttl=3600)
    # def load_proveedores(_self):
    #     """Cargar datos de proveedores desde Google Sheet público"""
    #     url = f"https://docs.google.com/spreadsheets/d/{_self.sheet_id}/gviz/tq?tqx=out:csv&sheet={_self.sheet_name}"
    #     df = pd.read_csv(url)
    #     df = df.dropna(subset=['idproveedor'])  # elimina filas sin idproveedor
    #     df['idproveedor'] = df['idproveedor'].astype(int)
    #     df['proveedor'] = df['proveedor'].astype(str).str.strip().str.upper()
    #     return df
    
    @st.cache_data(ttl=3600)
    def load_proveedores(_self):
        """Cargar datos de proveedores desde Google Sheet público"""
        url = f"https://docs.google.com/spreadsheets/d/{_self.sheet_id}/gviz/tq?tqx=out:csv&sheet={_self.sheet_name}"
        df = pd.read_csv(url)
        df = df.dropna(subset=['idproveedor'])
        df['idproveedor'] = df['idproveedor'].astype(int)
        df['proveedor'] = df['proveedor'].astype(str).str.strip().str.upper()
        
        # 🔥 UNIFICACIÓN: Cambiar ID pero MANTENER todas las filas
        df['idproveedor_original'] = df['idproveedor']  # Guardar original
        df['idproveedor'] = df['idproveedor'].map(_self.PROVEEDOR_UNIFICADO).fillna(df['idproveedor']).astype(int)
        df['proveedor'] = df['idproveedor'].map(_self.NOMBRES_UNIFICADOS).fillna(df['proveedor'])
        
        # ✅ NO eliminar duplicados aquí - mantener todos los artículos
        
        return df

    def query_bigquery_data(self, proveedor, fecha_inicio, fecha_fin):
        """Consultar datos de BigQuery"""
        # try:
        #     # Obtener IDs de artículos
        #     ids = self.df_proveedores[self.df_proveedores['proveedor'] == proveedor ]['idarticulo'].dropna().astype(int).astype(str).unique()
            
        #     if len(ids) == 0: return None

        try:
            # 🔥 Obtener todos los IDs de artículos del proveedor (incluye unificados)
            ids = self.df_proveedores[
                self.df_proveedores['proveedor'] == proveedor
            ]['idarticulo'].dropna().astype(int).astype(str).unique()
            
            if len(ids) == 0: 
                return None
            
            id_str = ','.join(ids)
            
            # Cliente BigQuery
            client = bigquery.Client.from_service_account_json(self.credentials_path)
            
            query = f"""
            SELECT fecha_comprobante, idarticulo, descripcion, cantidad_total,
                   costo_total, precio_total, sucursal, familia, subfamilia
            FROM `{self.project_id}.{self.bigquery_table}`
            WHERE idarticulo IN ({id_str})
            AND DATE(fecha_comprobante) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
            ORDER BY fecha_comprobante DESC
            """
            
            df = client.query(query).to_dataframe()
            
            if len(df) == 0:
                return None
            
            # Calcular métricas adicionales
            df['utilidad'] = df['precio_total'] - df['costo_total']
            df['margen_porcentual'] = np.where(
                df['precio_total'] > 0,
                (df['utilidad'] / df['precio_total']) * 100,
                0
            )
            df['fecha_comprobante'] = pd.to_datetime(df['fecha_comprobante'])
            df['fecha'] = df['fecha_comprobante'].dt.date
            df['mes_año'] = df['fecha_comprobante'].dt.to_period('M').astype(str)
            df['dia_semana'] = df['fecha_comprobante'].dt.day_name()
            # 🔍 Limpieza final
            df = limpiar_datos(df)
            return df
            
        except Exception as e:
            st.error(f"Error consultando BigQuery: {e}")
            return None
    
    def query_resultados_idarticulo(self, idproveedor):
        credentials_path = self.credentials_path
        project_id = self.project_id
        dataset = 'presupuesto'
        table = 'result_final_alert_all'

        try:
            # 🔥 Obtener IDs originales si es un ID unificado
            if idproveedor in self.NOMBRES_UNIFICADOS:
                # Es un ID unificado, buscar los IDs originales
                ids_originales = [k for k, v in self.PROVEEDOR_UNIFICADO.items() if v == idproveedor]
                id_condition = f"idproveedor IN ({','.join(map(str, ids_originales))})"
            else:
                # Es un ID normal
                id_condition = f"idproveedor = {idproveedor}"
            
            client = bigquery.Client.from_service_account_json(credentials_path)

            query = f"""
                SELECT *
                FROM `{project_id}.{dataset}.{table}`
                WHERE idarticulo IS NOT NULL
                AND {id_condition}
            """

            df = client.query(query).to_dataframe()

            if df.empty:
                st.warning(f"⚠️ No se encontraron datos para el proveedor con ID: {idproveedor}")
            # else:
            #     placeholder = st.empty()
            #     st.success(f"✅ Se encontraron {len(df)} registros para idproveedor {idproveedor}")
            #     time.sleep(3)   # espera 3 segundos
            #     placeholder.empty()  # borra el mensaje
            return df

        except Exception as e:
            st.error(f"❌ Error al consultar BigQuery: {e}")
            return pd.DataFrame()

   
    def calculate_metrics(self, df):
        """Calcular métricas principales"""
        
        # Sucursales únicas (si existe la columna)
        if 'sucursal' in df.columns:
            sucursales_unicas = df['sucursal'].dropna().unique()
            num_sucursales = len(sucursales_unicas)
            sucursales_str = ", ".join(sorted(s[:4].upper() for s in sucursales_unicas))
            # sucursales_str = ", ".join(sorted(map(str, sucursales_unicas)))
        else:
            num_sucursales = 0
            sucursales_str = "N/A"

        # Familias únicas (opcional)
        if 'familia' in df.columns:
            familias_unicas = df['familia'].dropna().unique()
            num_familias = len(familias_unicas)
        else:
            num_familias = 0

        return {
            'total_ventas': df['precio_total'].sum(),
            'total_costos': df['costo_total'].sum(),
            'total_utilidad': df['utilidad'].sum(),
            'margen_promedio': df['margen_porcentual'].mean(),
            'total_cantidad': df['cantidad_total'].sum(),
            'num_tickets': len(df),
            'ticket_promedio': df['precio_total'].sum() / len(df) if len(df) > 0 else 0,
            'productos_unicos': df['idarticulo'].nunique(),
            'dias_con_ventas': df['fecha'].nunique(),
            'sucursales': num_sucursales,
            'sucursales_presentes': sucursales_str,
            'familias': num_familias
        }
    
    def generate_insights(self, df, metrics):
        """Generar insights automáticos"""
        insights = []
        
        # Análisis de rentabilidad
        if metrics['margen_promedio'] > 30:
            insights.append(("success", f"🎯 Excelente rentabilidad: {metrics['margen_promedio']:.1f}% de margen promedio"))
        elif metrics['margen_promedio'] > 20:
            insights.append(("info", f"📈 Buena rentabilidad: {metrics['margen_promedio']:.1f}% de margen promedio"))
        else:
            insights.append(("warning", f"⚠️ Margen bajo: {metrics['margen_promedio']:.1f}% - Revisar estrategia de precios"))
        
        # Análisis de productos
        top_producto = df.groupby('descripcion')['precio_total'].sum().nlargest(1)
        if len(top_producto) > 0:
            producto_name = top_producto.index[0]
            producto_ventas = top_producto.iloc[0]
            participacion = (producto_ventas / metrics['total_ventas']) * 100
            insights.append(("info", f"🏆 Producto estrella: {producto_name[:50]}... ({participacion:.1f}% de ventas)"))
        
        # Análisis temporal
        if len(df) > 7:  # Suficientes días para análisis
            ventas_por_dia = df.groupby('fecha')['precio_total'].sum()
            tendencia_dias = 7
            if len(ventas_por_dia) >= tendencia_dias:
                ultimos_dias = ventas_por_dia.tail(tendencia_dias).mean()
                primeros_dias = ventas_por_dia.head(tendencia_dias).mean()
                if ultimos_dias > primeros_dias * 1.1:
                    insights.append(("success", f"📈 Tendencia positiva: +{((ultimos_dias/primeros_dias-1)*100):.1f}% en últimos días"))
                elif ultimos_dias < primeros_dias * 0.9:
                    insights.append(("warning", f"📉 Tendencia bajista: {((ultimos_dias/primeros_dias-1)*100):.1f}% en últimos días"))
        
        # Análisis de diversificación
        if metrics['productos_unicos'] < 5:
            insights.append(("warning", "🎯 Baja diversificación de productos - Considerar ampliar catálogo"))
        elif metrics['productos_unicos'] > 20:
            insights.append(("success", f"🌟 Excelente diversificación: {metrics['productos_unicos']} productos únicos"))
        
        # Análisis de ticket promedio
        if metrics['ticket_promedio'] > 5000:
            insights.append(("success", f"💰 Alto valor por transacción: ${metrics['ticket_promedio']:,.0f}"))
        elif metrics['ticket_promedio'] < 1000:
            insights.append(("info", "💡 Oportunidad de cross-selling para aumentar ticket promedio"))
        
        return insights
    
    def show_sidebar_filters(self):
        # --- CSS & LOGO ---
        st.sidebar.markdown(custom_sidebar(), unsafe_allow_html=True)

        # --- Cargar proveedores ---
        if self.df_proveedores is None:
            with st.spinner("Cargando proveedores..."):
                self.df_proveedores = self.load_proveedores()
        
        proveedores = sorted(self.df_proveedores['proveedor'].dropna().unique())
        proveedor_actual = st.session_state.get("selected_proveedor")
        df_proveedor_ids = self.df_proveedores[['idproveedor', 'proveedor']]

        proveedor = st.sidebar.selectbox(
            "🔎 Elegir proveedor",
            options=proveedores,
            index=proveedores.index(proveedor_actual) if proveedor_actual in proveedores else None,
            placeholder="Seleccionar proveedor..."
        )

        # --- Rango de fechas ---
        rango_opciones = {
            "Últimos 30 días": 30,
            "Últimos 60 días": 60,
            "Últimos 90 días": 90,
            "Últimos 180 días": 180,
            "Últimos 356 días": 365,
            "Personalizado": None
        }

        if proveedor and "analysis_data" not in st.session_state:
            st.sidebar.markdown('<div class="highlight-period">📅 Elige un período de análisis</div>', unsafe_allow_html=True)

        rango_seleccionado = st.sidebar.selectbox(
            "📅 Período de Análisis:",
            options=list(rango_opciones.keys()),
            index=0
        )

        # Crear instancia de locale español
        locale_es = Locale.parse("es")

        # Selección de fechas
        if rango_seleccionado == "Personalizado":
            col1, col2 = st.sidebar.columns(2)
            fecha_inicio = col1.date_input("Desde:", value=datetime.now().date() - timedelta(days=30))
            fecha_fin = col2.date_input("Hasta:", value=datetime.now().date())
        else:
            dias = rango_opciones[rango_seleccionado]
            fecha_fin = datetime.now().date()
            fecha_inicio = fecha_fin - timedelta(days=dias)

        # Formateo en español con Babel
        fecha_inicio_fmt = format_date(fecha_inicio, format="d MMMM y", locale=locale_es).capitalize()
        fecha_fin_fmt = format_date(fecha_fin, format="d MMMM y", locale=locale_es).capitalize()

        # Mostrar resumen en el sidebar
        st.sidebar.info(f"📅 **{rango_seleccionado}**\n\n{fecha_inicio_fmt} / {fecha_fin_fmt}")

        # --- Botón ---

        df_presu = None  # ✅ Inicializar para evitar UnboundLocalError

        filtro = df_proveedor_ids[df_proveedor_ids['proveedor'] == proveedor]
        if not filtro.empty:
            fila = int(filtro['idproveedor'].iloc[0])
        else:
            st.sidebar.error("Selecciona un proveedor y analiza.")
            return proveedor, fecha_inicio, fecha_fin, None
   
        if st.sidebar.button("Realizar Análisis", type="primary", width="stretch"):
            if not proveedor:
                st.sidebar.error("❌ Selecciona un proveedor")
            else:
                with st.spinner(f"🔄 Consultando datos de {proveedor}"):
                    df_tickets = self.query_bigquery_data(proveedor, fecha_inicio, fecha_fin)
                    if df_tickets is not None:
                        st.session_state.analysis_data = df_tickets
                        st.session_state.selected_proveedor = proveedor
                    else:
                        st.sidebar.error("❌ No se encontraron datos para el período seleccionado")
                if fila > 0:
                    with st.spinner(f"🔄 Consultando datos proveedor id: {fila}"):
                        df_presu = self.query_resultados_idarticulo(fila)
                        if df_presu is not None:
                            st.session_state.resultados_data = df_presu

                        else:
                            st.sidebar.error("❌ No se encontraron datos de presupuesto para el proveedor")
                else:
                    st.sidebar.error("❌ No se encontró el ID del proveedor seleccionado")

        # Si existe en session_state, recuperarlo
        if "df_presu" in st.session_state:
            df_presu = st.session_state.df_presu

        # --- Resumen del período ---
        if st.session_state.get("analysis_data") is not None:
            df_tickets = st.session_state.analysis_data
            df_tickets['fecha'] = pd.to_datetime(df_tickets['fecha'])

            productos_unicos = df_tickets['idarticulo'].nunique() if 'idarticulo' in df_tickets else 0
            familias = df_tickets['familia'].nunique() if 'familia' in df_tickets else 0
            subfamilias = df_tickets['subfamilia'].nunique() if 'subfamilia' in df_tickets else 0
            dia_top = df_tickets['fecha'].dt.day_name().value_counts().idxmax()
            mes_top = df_tickets['fecha'].dt.strftime('%B').value_counts().idxmax()

            # st.sidebar.markdown("### 🧾 Resumen del Período")
            st.sidebar.markdown(f"🛒 **Productos Únicos:** `{productos_unicos}`")
            st.sidebar.markdown(f"🧩 **Familias:** `{familias}`")
            st.sidebar.markdown(f"🧬 **Subfamilias:** `{subfamilias}`")
            st.sidebar.markdown(f"📅 **Día más ventas:** `{dia_top}`")
            st.sidebar.markdown(f"📆 **Mes más ventas:** `{mes_top}`")

        return proveedor, fecha_inicio, fecha_fin, df_presu
    
    def show_main_dashboard(self):
        proveedor = self.proveedor if hasattr(self, 'proveedor') else None

        if proveedor:
            st.markdown(f"""
            <div class="main-header">
                <p style='padding:5px 0px; font-size:1.5rem; font-weight:semibold;'>Proveedor: {proveedor}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="main-header">
                <p style='
                    position: absolute;
                    top: -2.5rem;
                    left: 2.5rem;
                    padding: 5px 0px;
                    font-size: 2.2rem;
                    color: #646060;
                    font-weight: 500;'>📈 Ranking de Proveedores</p>
            </div>
            """, unsafe_allow_html=True)

        if st.session_state.analysis_data is None:
            # Dashboard Global de Proveedores
            show_global_dashboard(
                df_proveedores=self.df_proveedores,
                query_function=query_resultados_idarticulo,
                credentials_path=self.credentials_path,
                project_id=self.project_id,
                bigquery_table=self.bigquery_table  # 👈 NUEVO PARÁMETRO
            )
            return# ⚠️ IMPORTANTE: Salir aquí para no mostrar el resto
        
        # === BOTÓN VOLVER ===
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← Dashboard Global", type="secondary", width="stretch"):
                st.session_state.analysis_data = None
                st.session_state.selected_proveedor = None
                st.session_state.resultados_data = None
                st.rerun()
        
        with col2:
            proveedor = st.session_state.selected_proveedor
            st.markdown(f"""
            <div class="main-header">
                <p style='padding:5px 0px; font-size:1.5rem; font-weight:semibold;'>
                    📊 Análisis Detallado: {proveedor}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # Si hay datos, mostrar análisis
        df = st.session_state.analysis_data
        try:
            df_presu = st.session_state.resultados_data
        except AttributeError:
            df_presu = None

        # df_presu = st.session_state.resultados_data
        proveedor = st.session_state.selected_proveedor
        metrics = self.calculate_metrics(df)
        
        # Tabs principales
        tab1, tab2, tab3, tab4, tab5, tab7 = st.tabs([
            "📈 Resumen Ejecutivo", 
            "🏆 Análisis de Productos", 
            "📅 Evolución Temporal",
            "🎯 Análisis Avanzado",
            "📋 Sintesis Final",
            # "📁 Articulos",
            "🧮 Presupuesto"

        ])
        
        with tab1:
            self.show_executive_summary(df, proveedor, metrics)
        
        with tab2:
            self.show_products_analysis(df)
        
        with tab3:
            self.show_temporal_analysis(df)
        
        with tab4:
            self.show_advanced_analysis(df, metrics)
        
        with tab5:
            self.show_executive_summary_best(df, proveedor, metrics)

        # with tab6:
        #     self.show_idarticulo_analysis_01(df_presu)

        with tab7:
            self.show_presupuesto_estrategico(df_presu)


    def show_executive_summary(self, df, proveedor, metrics):
        """Wrapper para el componente de resumen ejecutivo"""
        render_executive_summary(df, proveedor, metrics)
        
    def show_products_analysis(self, df):
        """
        Análisis detallado de productos
        Componente modularizado en components/products_analysis.py
        """
        # Importar la función de insights si existe
        try:
            from insight_ABC import generar_insight_pareto
            render_products_analysis(df, generar_insight_pareto)
        except ImportError:
            # Si no existe la función de insights, llamar sin ella
            render_products_analysis(df)
   
    def show_temporal_analysis(self, df):
        """
        Análisis de evolución temporal
        Componente modularizado en components/temporal_analysis.py
        """
        render_temporal_analysis(df)        
    
    def show_advanced_analysis(self, df, metrics):
        """
        Análisis avanzado
        Componente modularizado en components/advanced_analysis.py
        """
        # Importar funciones de insights si existen
        try:
            from insight_ABC import (
                generar_insight_margen,
                generar_insight_cantidad,
                generar_insight_ventas,
                generar_insight_abc_completo
            )
            render_advanced_analysis(
                df, 
                metrics,
                generar_insight_margen_func=generar_insight_margen,
                generar_insight_cantidad_func=generar_insight_cantidad,
                generar_insight_ventas_func=generar_insight_ventas,
                generar_insight_abc_completo_func=generar_insight_abc_completo
            )
        except ImportError:
            # Si no existen las funciones de insights, llamar sin ellas
            render_advanced_analysis(df, metrics)

    def show_executive_summary_best(self, df, proveedor, metrics):
        """Resumen ejecutivo completo con análisis integral"""
        df['fecha_fmt'] = df['fecha'].apply(lambda x: format_date(x, format="d MMMM y", locale=locale))
        periodo_analisado = f"{df['fecha_fmt'].min()} al {df['fecha_fmt'].max()}"

        # === Estilos CSS personalizados ===
        st.markdown("""
        <style>
            .insight-box, .success-box, .warning-box {
                border-radius: 10px;
                padding: 1rem;
                margin: 0.5rem 0;
                font-size: 0.95rem;
                border-left: 6px solid #2a5298;
            }
            .success-box {
                background-color: #e6f4ea;
                border-left-color: #28a745;
            }
            .warning-box {
                background-color: #fff3cd;
                border-left-color: #ffc107;
            }
            .insight-box {
                background-color: #d1ecf1;
                border-left-color: #17a2b8;
            }
            .executive-section {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
                border-left: 4px solid #2a5298;
            }
            .familia-item {
                background: #e9f5ff;
                padding: 0.3rem 0.8rem;
                margin: 0.2rem;
                border-radius: 15px;
                display: inline-block;
                font-size: 0.85rem;
                border: 1px solid #b3d9ff;
            }
            .mini-chart-container {
                background: white;
                border-radius: 8px;
                padding: 0.5rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
        </style>
        """, unsafe_allow_html=True)

        # === KPIs principales mejorados ===
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 1rem; color: #555;">💰 Ventas Totales</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #1e3c72;">${metrics['total_ventas']:,.0f}</div>
                </div>
                <div style="color: green; font-size: 0.8rem; margin-top: 0.2rem;">
                    ⬆️ {metrics['margen_promedio']:.1f}% margen
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 1rem; color: #555;">📈 Utilidad Total</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #1e3c72;">${metrics['total_utilidad']:,.0f}</div>
                </div>
                <div style="color: green; font-size: 0.8rem; margin-top: 0.2rem;">
                    ⬆️ ${metrics['ticket_promedio']:,.0f} ticket prom.
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 1rem; color: #555;">📦 Cantidad Vendida</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #1e3c72;">{metrics['total_cantidad']:,.0f}</div>
                </div>
                <div style="color: green; font-size: 0.8rem; margin-top: 0.2rem;">
                    ⬆️ {metrics['productos_unicos']} productos únicos
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 1rem; color: #555;">📅 Días con Ventas</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #1e3c72;">{metrics['dias_con_ventas']}</div>
                </div>
                <div style="color: #888; font-size: 0.8rem; margin-top: 0.2rem;text-align: center;">
                    {periodo_analisado}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col5:
            familias_count = df['familia'].nunique() if 'familia' in df.columns else 0
            subfamilias_count = df['subfamilia'].nunique() if 'subfamilia' in df.columns else 0
            art_count = df['idarticulo'].nunique() if 'idarticulo' in df.columns else 0
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 1.15rem; color: #555;">🌿 Familias 
                        <span style="font-size: 1.15rem; font-weight: bold; color: #1e3c72">
                        {familias_count}
                        </span>
                    </div>
                    <div style="font-size: 1.15rem; color: #555;">🌿 SubFamilias 
                        <span style="font-size: 1.15rem; font-weight: bold; color: #1e3c72">
                        {subfamilias_count}
                        </span>
                    </div>
                    <div style="font-size: 1.15rem; color: #555;">🌿 Artículos 
                        <span style="font-size: 1.15rem; font-weight: bold; color: #1e3c72">
                        {art_count}
                        </span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col6:
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 1rem; color: #555;">🏪 Sucursales</div>
                    <div style="font-size: 1rem; color: #1e3c72; padding: .4rem 0rem">{metrics['sucursales_presentes']}</div>
                </div>
                <div style="color: #888; font-size: 0.8rem; margin-top: 0.2rem;">
                    Presencia territorial
                </div>
            </div>
            """, unsafe_allow_html=True)

        # === Análisis de Familias y Subfamilias ===
        st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
        st.markdown("### 🧬 Análisis de Categorías de Productos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'familia' in df.columns and df['familia'].notna().any():
                familias_list = sorted(df['familia'].dropna().unique())
                familias_ventas = df.groupby('familia')['precio_total'].sum().sort_values(ascending=False)
                familia_principal = familias_ventas.index[0] if len(familias_ventas) > 0 else "N/A"
                
                st.markdown(f"""
                **🌿 Familias de Productos ({len(familias_list)})**
                - **Familia principal:** {familia_principal}
                - **Participación:** {(familias_ventas.iloc[0] / metrics['total_ventas'] * 100):.1f}% del total
                """)
                
                # Lista de familias en formato de chips
                familias_html = "".join([f'<span class="familia-item">{familia}</span>' for familia in familias_list[:8]])
                if len(familias_list) > 8:
                    familias_html += f'<span class="familia-item">+{len(familias_list)-8} más...</span>'
                st.markdown(familias_html, unsafe_allow_html=True)

        with col2:
            if 'subfamilia' in df.columns and df['subfamilia'].notna().any():
                subfamilias_list = sorted(df['subfamilia'].dropna().unique())
                subfamilias_ventas = df.groupby('subfamilia')['precio_total'].sum().sort_values(ascending=False)
                subfamilia_principal = subfamilias_ventas.index[0] if len(subfamilias_ventas) > 0 else "N/A"
                
                st.markdown(f"""
                **🍃 Subfamilias de Productos ({len(subfamilias_list)})**
                - **Subfamilia principal:** {subfamilia_principal}
                - **Participación:** {(subfamilias_ventas.iloc[0] / metrics['total_ventas'] * 100):.1f}% del total
                """)
                
                # Lista de subfamilias en formato de chips
                subfamilias_html = "".join([f'<span class="familia-item">{subfam}</span>' for subfam in subfamilias_list[:8]])
                if len(subfamilias_list) > 8:
                    subfamilias_html += f'<span class="familia-item">+{len(subfamilias_list)-8} más...</span>'
                st.markdown(subfamilias_html, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

        # === Síntesis de Análisis Temporal ===
        st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
        st.markdown("### 📅 Síntesis Temporal")
        
        # Análisis mensual para tendencias
        df['mes_año'] = pd.to_datetime(df['fecha']).dt.to_period('M').astype(str)
        mensual = df.groupby('mes_año')['precio_total'].sum()
        mes_top = mensual.idxmax() if len(mensual) > 0 else "N/A"
        ventas_mes_top = mensual.max() if len(mensual) > 0 else 0
        
        # Análisis por día de semana
        dia_mapping = {
            'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
            'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        
        if 'dia_semana' in df.columns:
            df['dia_semana_es'] = df['dia_semana'].map(dia_mapping)
            semanal = df.groupby('dia_semana_es')['precio_total'].sum()
            dia_top = semanal.idxmax() if len(semanal) > 0 else "N/A"
        else:
            df['dia_semana_es'] = pd.to_datetime(df['fecha']).dt.day_name().map(dia_mapping)
            semanal = df.groupby('dia_semana_es')['precio_total'].sum()
            dia_top = semanal.idxmax() if len(semanal) > 0 else "N/A"
        
        # Tendencia general
        if len(mensual) >= 3:
            valores = mensual.values
            tendencia_coef = np.polyfit(range(len(valores)), valores, 1)[0]
            tendencia_texto = "📈 Creciente" if tendencia_coef > 0 else "📉 Decreciente" if tendencia_coef < 0 else "➡️ Estable"
            tendencia_porcentaje = abs(tendencia_coef / valores.mean() * 100)
        else:
            tendencia_texto = "➡️ Período insuficiente"
            tendencia_porcentaje = 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            **📊 Mes Destacado**
            - **Período:** {mes_top}
            - **Ventas:** ${ventas_mes_top:,.0f}
            - **Participación:** {(ventas_mes_top / metrics['total_ventas'] * 100):.1f}%
            """)
        
        with col2:
            st.markdown(f"""
            **📅 Día Óptimo**
            - **Día:** {dia_top}
            - **Concentración:** {(semanal.max() / semanal.sum() * 100):.1f}%
            - **Promedio:** ${semanal.mean():,.0f}
            """)
        
        with col3:
            st.markdown(f"""
            **📈 Tendencia General**
            - **Dirección:** {tendencia_texto}
            - **Variación:** {tendencia_porcentaje:.1f}%
            - **Estabilidad:** {'Alta' if tendencia_porcentaje < 5 else 'Media' if tendencia_porcentaje < 15 else 'Baja'}
            """)
        
        st.markdown('</div>', unsafe_allow_html=True)

        # === Síntesis Análisis ABC ===
        st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
        st.markdown("### 🎯 Síntesis Análisis ABC")
        
        productos_abc = df.groupby(['idarticulo', 'descripcion']).agg({
            'precio_total': 'sum',
            'utilidad': 'sum'
        }).sort_values('precio_total', ascending=False)
        
        productos_abc['participacion_acum'] = (
            productos_abc['precio_total'].cumsum() /
            productos_abc['precio_total'].sum() * 100
        )
        
        def categorizar_abc(part):
            if part <= 80:
                return 'A'
            elif part <= 95:
                return 'B'
            else:
                return 'C'
        
        productos_abc['categoria_abc'] = productos_abc['participacion_acum'].apply(categorizar_abc)
        abc_counts = productos_abc['categoria_abc'].value_counts().sort_index()
        abc_ventas = productos_abc.groupby('categoria_abc')['precio_total'].sum().sort_index()
        
        # Diversificación
        concentracion_a = (abc_ventas.get('A', 0) / metrics['total_ventas'] * 100) if 'A' in abc_ventas else 0
        diversificacion = "Alta" if concentracion_a < 60 else "Media" if concentracion_a < 80 else "Baja"
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            productos_a = abc_counts.get('A', 0)
            st.markdown(f"""
            **🔥 Productos Clase A**
            - **Cantidad:** {productos_a} productos
            - **Concentración:** {concentracion_a:.1f}% ventas
            - **Impacto:** {'Crítico' if productos_a < 10 else 'Alto'}
            """)
        
        with col2:
            productos_b = abc_counts.get('B', 0)
            productos_c = abc_counts.get('C', 0)
            st.markdown(f"""
            **⚖️ Productos B y C**
            - **Clase B:** {productos_b} productos
            - **Clase C:** {productos_c} productos
            - **Complementarios:** {((abc_ventas.get('B', 0) + abc_ventas.get('C', 0)) / metrics['total_ventas'] * 100):.1f}%
            """)
        
        with col3:
            st.markdown(f"""
            **🎲 Diversificación**
            - **Nivel:** {diversificacion}
            - **Productos únicos:** {metrics['productos_unicos']}
            - **Riesgo:** {'Bajo' if diversificacion == 'Alta' else 'Medio' if diversificacion == 'Media' else 'Alto'}
            """)
        
        st.markdown('</div>', unsafe_allow_html=True)

        # === Análisis por Sucursal ===
        if 'sucursal' in df.columns and df['sucursal'].notna().any():
            st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
            st.markdown("### 🏪 Síntesis Geográfica")
            
            sucursal_stats = df.groupby('sucursal').agg({
                'precio_total': 'sum',
                'utilidad': 'sum',
                'margen_porcentual': 'mean'
            }).round(2)
            
            sucursal_top = sucursal_stats['precio_total'].idxmax()
            sucursal_top_ventas = sucursal_stats['precio_total'].max()
            sucursal_mejor_margen = sucursal_stats['margen_porcentual'].idxmax()
            margen_mejor = sucursal_stats['margen_porcentual'].max()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                **🏆 Sucursal Líder en Ventas**
                - **Sucursal:** {sucursal_top}
                - **Ventas:** ${sucursal_top_ventas:,.0f}
                - **Participación:** {(sucursal_top_ventas / metrics['total_ventas'] * 100):.1f}%
                """)
            
            with col2:
                st.markdown(f"""
                **💎 Sucursal Más Rentable**
                - **Sucursal:** {sucursal_mejor_margen}
                - **Margen:** {margen_mejor:.1f}%
                - **Eficiencia:** {'Excelente' if margen_mejor > 30 else 'Buena' if margen_mejor > 20 else 'Regular'}
                """)
            
            st.markdown('</div>', unsafe_allow_html=True)

        # === Insights Clave Automatizados ===
        insights = self.generate_insights(df, metrics)
        
        st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
        st.markdown("### 💡 Insights Clave del Período")
        
        # Separar insights por tipo
        insights_criticos = [insight for insight in insights if insight[0] == "warning"]
        insights_positivos = [insight for insight in insights if insight[0] == "success"]
        insights_informativos = [insight for insight in insights if insight[0] == "info"]
        
        if insights_criticos:
            st.markdown("**🚨 Puntos de Atención:**")
            for _, mensaje in insights_criticos[:2]:
                st.markdown(f'<div class="warning-box">{mensaje}</div>', unsafe_allow_html=True)
        
        if insights_positivos:
            st.markdown("**✅ Fortalezas Identificadas:**")
            for _, mensaje in insights_positivos[:2]:
                st.markdown(f'<div class="success-box">{mensaje}</div>', unsafe_allow_html=True)
        
        if insights_informativos:
            st.markdown("**📊 Información Relevante:**")
            for _, mensaje in insights_informativos[:2]:
                st.markdown(f'<div class="insight-box">{mensaje}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

        # === Recomendaciones Estratégicas Priorizadas ===
        st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
        st.markdown("### 🎯 Recomendaciones Estratégicas")
        
        recomendaciones = []
        
        # Análisis automático para recomendaciones
        if metrics['margen_promedio'] < 20:
            recomendaciones.append(("🔴 CRÍTICO", f"Optimizar márgenes: {metrics['margen_promedio']:.1f}% está por debajo del mínimo recomendado (20%)"))
        
        if concentracion_a > 80:
            recomendaciones.append(("🟠 ALTO", f"Diversificar portafolio: {concentracion_a:.1f}% de ventas concentrado en pocos productos"))
        
        if metrics['productos_unicos'] < 10:
            recomendaciones.append(("🟡 MEDIO", f"Ampliar catálogo: Solo {metrics['productos_unicos']} productos activos"))
        
        if len(recomendaciones) == 0:
            recomendaciones.append(("🟢 BUENO", "Rendimiento general satisfactorio. Mantener estrategia actual y buscar oportunidades de crecimiento"))
        
        # Agregar recomendación de producto estrella
        top_producto = df.groupby('descripcion')['precio_total'].sum().nlargest(1)
        if len(top_producto) > 0:
            producto_estrella = top_producto.index[0]
            participacion_estrella = (top_producto.iloc[0] / metrics['total_ventas']) * 100
            if participacion_estrella > 30:
                recomendaciones.append(("🟠 ALTO", f"Reducir dependencia del producto estrella ({participacion_estrella:.1f}% de ventas)"))
        
        for prioridad, mensaje in recomendaciones[:3]:
            color_class = "warning-box" if "CRÍTICO" in prioridad or "ALTO" in prioridad else "insight-box" if "MEDIO" in prioridad else "success-box"
            st.markdown(f'<div class="{color_class}"><strong>{prioridad}:</strong> {mensaje}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

        # === Tabla Resumen Ejecutivo Final ===
        st.markdown("### 📋 Tabla Resumen Ejecutivo")
        df['fecha_fmt'] = df['fecha'].apply(lambda x: format_date(x, format="d MMMM y", locale=locale))
        
        # Obtener listas completas para el resumen
        familias_completas = ", ".join(sorted(df['familia'].dropna().unique())) if 'familia' in df.columns else "N/A"
        subfamilias_completas = ", ".join(sorted(df['subfamilia'].dropna().unique())) if 'subfamilia' in df.columns else "N/A"
        
        resumen_data = {
            'Métrica': [
                'Proveedor',
                'Período de Análisis',
                'Ventas Totales',
                'Utilidad Total',
                'Margen Promedio',
                'Productos Únicos',
                'Días con Ventas',
                f'Familias ({familias_count})',
                f'Subfamilias ({df["subfamilia"].nunique() if "subfamilia" in df.columns else 0})',
                'Sucursales Activas',
                'Tendencia Período',
                'Clasificación ABC',
                'Producto estrella',
                'Recomendación Principal'
            ],
            'Valor': [
                proveedor,
                f"{df['fecha_fmt'].min()} a {df['fecha_fmt'].max()}",
                f"${metrics['total_ventas']:,.0f}",
                f"${metrics['total_utilidad']:,.0f}",
                f"{metrics['margen_promedio']:.1f}%",
                f"{metrics['productos_unicos']:,}",
                f"{metrics['dias_con_ventas']:,}",
                familias_completas[:100] + "..." if len(familias_completas) > 100 else familias_completas,
                subfamilias_completas[:100] + "..." if len(subfamilias_completas) > 100 else subfamilias_completas,
                metrics['sucursales_presentes'],
                tendencia_texto,
                f"{abc_counts.get('A', 0)}A-{abc_counts.get('B', 0)}B-{abc_counts.get('C', 0)}C",
                producto_estrella,
                recomendaciones[0][1][:80] + "..." if len(recomendaciones[0][1]) > 80 else recomendaciones[0][1]
            ]
        }
        
        df_resumen = pd.DataFrame(resumen_data)
        st.dataframe(df_resumen, width="stretch", hide_index=True)

        st.markdown("### Vista Previa de Datos")
        df['fecha_fmt'] = df['fecha'].apply(lambda x: format_date(x, format="d MMMM y", locale=locale))
        data=df[['fecha_fmt', 'idarticulo', 'descripcion', 'precio_total', 'costo_total', 'utilidad', 'margen_porcentual', 'cantidad_total']].copy()
        archivo_excel = generar_excel(data, sheet_name="ABC Clasificación")
        periodo_analisis = resumen_data['Valor'][1]

        from re import sub

        proveedor_key = sub(r'\W+', '', proveedor.lower())

        st.download_button(
            label="📥 Descargar todos los datos del proveedor (Excel)",
            data=archivo_excel,
            file_name=f"{proveedor}_{periodo_analisis}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"descarga_excel_{proveedor_key}"
)

            # Mostrar muestra de datos
        st.dataframe(
                data.head(10),
                width="stretch",
                column_config={
                    "fecha_fmt": st.column_config.DateColumn("Fecha"),
                    "precio_total": st.column_config.NumberColumn("Precio Total", format="$%.0f"),
                    "costo_total": st.column_config.NumberColumn("Costo Total", format="$%.0f"),
                    "utilidad": st.column_config.NumberColumn("Utilidad", format="$%.0f"),
                    "margen_porcentual": st.column_config.NumberColumn("Margen %", format="%.1f%%"),
                    "cantidad_total": st.column_config.NumberColumn("Cantidad", format="%.0f")
                }
            )
            
        if len(data) > 100:
                st.info(f"ℹ️ Mostrando las primeras 10 filas de {len(data):,} registros totales. Descarga el CSV completo para ver todos los datos.")
    ##   ANALISIS DETALLADO POR ARTÍCULO
    def show_idarticulo_analysis_01(self, df_presu):
        """
        Análisis estratégico mejorado de inventario por grupos
        """
        if df_presu is None or df_presu.empty:
            st.warning("⚠️ No hay datos disponibles para análisis.")
            return
        
        st.markdown("# 🎯 Análisis Estratégico de Inventario")
        st.markdown("---")
        
        # Inicializar dashboard estratégico
        dashboard = InventoryDashboard()
        
        # Procesar datos
        with st.spinner("🔄 Preparando análisis estratégico..."):
            df_processed = dashboard.load_and_validate_data(df_presu)
        
        if df_processed is not None:
            # Mostrar KPIs principales
            dashboard.show_main_kpis(df_processed)
            st.markdown("---")
            
            # Pestañas del análisis estratégico
            tabs = st.tabs([
                "🎯 Matriz Estratégica",
                "🏪 Performance Sucursales", 
                "📦 Gestión Inventario",
                "📊 Análisis por Familia",
                "⚡ Acciones Inmediatas",
                "📋 Datos Detallados"
            ])
            
            with tabs[0]:
                dashboard.tab_matriz_estrategica(df_processed)
                
            with tabs[1]:
                dashboard.tab_performance_sucursal(df_processed)
                
            with tabs[2]:
                dashboard.tab_gestion_inventario(df_processed)
                
            with tabs[3]:
                dashboard.tab_analisis_familia(df_processed)
                
            with tabs[4]:
                dashboard.tab_acciones_inmediatas(df_processed)
                
            with tabs[5]:
                # Mantener la vista de datos original como referencia
                st.markdown("### 📋 DataFrame Completo")
                st.dataframe(df_processed, width="stretch")
            
            # Botones de acción
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 Exportar Análisis", type="primary"):
                    st.success("✅ Funcionalidad de exportación lista")
            
            with col2:
                if st.button("🔄 Actualizar Datos"):
                    st.rerun()
            
            with col3:
                if st.button("📧 Generar Reporte"):
                    st.info("📋 Reporte ejecutivo generado")
    def show_idarticulo_analysis(self, df_presu):
        if df_presu is None or df_presu.empty:
            st.warning("⚠️ No hay datos disponibles para análisis por artículo.")
            return

        # === Selector de artículo ===
        opciones = df_presu[["idarticulo", "descripcion"]].drop_duplicates()
        opciones["etiqueta"] = opciones["idarticulo"].astype(str) + " - " + opciones["descripcion"]

        if opciones.empty:
            st.warning("⚠️ No hay artículos disponibles para seleccionar.")
            return

        seleccion = st.selectbox("Seleccionar artículo para análisis detallado:", opciones["etiqueta"].tolist())

        try:
            id_seleccionado = int(seleccion.split(" - ")[0])
        except (IndexError, ValueError):
            st.error("❌ Ocurrió un error al procesar la selección de artículo.")
            return

        df_item = df_presu[df_presu["idarticulo"] == id_seleccionado].copy()

        if df_item.empty:
            st.info("No se encontraron datos para el artículo seleccionado.")
            return

        # === Mostrar pestañas ===
        tabs = st.tabs(["📦 Stock y Cobertura", "📈 Demanda y Presupuesto", "💰 Rentabilidad", "📊 Estacionalidad", "📋 DataFrame"])

        with tabs[0]:
            self.tab_stock_y_cobertura(df_item)

        with tabs[1]:
            self.tab_demanda_presupuesto(df_item)

        with tabs[2]:
            self.tab_rentabilidad(df_item)

        with tabs[3]:
            self.tab_estacionalidad(df_item)

        with tabs[4]:
            self.tab_df(df_presu.head(5))            
    def show_idarticulo_analysis(self):
        if self.df_resultados is None or self.df_resultados.empty:
            st.warning("⚠️ No hay datos disponibles para análisis por artículo.")
            return

        # === Selector de artículo ===
        opciones = self.df_resultados[["idarticulo", "descripcion"]].drop_duplicates()
        opciones["etiqueta"] = opciones["idarticulo"].astype(str) + " - " + opciones["descripcion"]
        seleccion = st.selectbox("Seleccionar artículo para análisis detallado:", opciones["etiqueta"].tolist())

        # === Filtrar artículo seleccionado ===
        id_seleccionado = int(seleccion.split(" - ")[0])
        data = self.df_resultados
        df_item = self.df_resultados[self.df_resultados["idarticulo"] == id_seleccionado].copy()

        if df_item.empty:
            st.info("No se encontraron datos para el artículo seleccionado.")
            return

        # === Mostrar pestañas ===
        st.markdown("### 📋 DataFrame Detallado")
        tabs = st.tabs(["📦 Stock y Cobertura", "📈 Demanda y Presupuesto", "💰 Rentabilidad", "📊 Estacionalidad", "📋 DataFrame"])

        with tabs[0]:
            self.tab_stock_y_cobertura(df_item)

        with tabs[1]:
            self.tab_demanda_presupuesto(df_item)

        with tabs[2]:
            self.tab_rentabilidad(df_item)

        with tabs[3]:
            self.tab_estacionalidad(df_item)

        with tabs[4]:
            self.tab_df(data.head(5))
    def tab_df(self, df):
        st.markdown("### 📋 DataFrame Detallado")
        try:
            st.dataframe(df, width="stretch")
        except Exception as e:
            st.error(f"❌ Error al mostrar el DataFrame: {e}")
    def tab_stock_y_cobertura(self, df):
        st.markdown("### 🏪 Stock por Sucursal")
        cols = ['stk_corrientes', 'stk_express', 'stk_formosa', 'stk_hiper', 'stk_TIROL', 'stk_central']
        for col in cols:
            st.write(f"**{col.upper()}**: {int(df[col].iloc[0])}")
        
        st.write("**🔄 Stock Total**:", int(df["STK_TOTAL"].iloc[0]))
        st.write("**🚨 Alerta Stock**:", df["ALERTA_STK_Tirol_Central"].iloc[0])
        st.write("**📆 Días de Cobertura**:", df["dias_cobertura"].iloc[0])
        st.write("**⚠️ Nivel de Riesgo**:", df["nivel_riesgo"].iloc[0])
        st.write("**✅ Acción Recomendada**:", df["accion_gralporc"].iloc[0])
        st.write("**% PRESUPUESTO ASOCIADO**:", f"{df['PRESU_accion_gral'].iloc[0]:,.2f}")
    def tab_demanda_presupuesto(self, df):
        st.markdown("### 📈 Demanda y Presupuesto")

        st.write("**🔢 Pronóstico Final (cnt_corregida):**", int(df["cnt_corregida"].iloc[0]))
        st.write("**💰 Presupuesto ($):**", f"${df['PRESUPUESTO'].iloc[0]:,.0f}")
        st.write("**📆 Meses Activos:**", int(df["meses_act_estac"].iloc[0]))

        exceso_stk = df["exceso_STK"].iloc[0]
        costo_exceso = df["costo_exceso_STK"].iloc[0]

        if exceso_stk > 0:
            st.write("**⚠️ Exceso de Stock:**", int(exceso_stk))
            st.write("**💸 Costo del Exceso:**", f"${costo_exceso:,.0f}")
        else:
            st.success("✅ No hay exceso de stock.")
    def tab_rentabilidad(self, df):
        st.markdown("### 💰 Rentabilidad del Artículo")

        margen_all = df.get("margen_porc_all", pd.Series([None])).iloc[0]
        margen_90 = df.get("margen_a90", pd.Series([None])).iloc[0]
        margen_30 = df.get("margen_a30", pd.Series([None])).iloc[0]
        analisis = df.get("analisis_margen", pd.Series(["Sin análisis"])).iloc[0]
        estrategia = df.get("estrategia", pd.Series(["No definida"])).iloc[0]
        prioridad = df.get("prioridad", pd.Series(["N/A"])).iloc[0]

        col1, col2, col3 = st.columns(3)

        with col1:
            if margen_all is not None:
                st.metric("📊 Margen Global", f"{margen_all:.1f}%")
            if margen_90 is not None:
                st.metric("📆 Margen 90 días", f"{margen_90:.1f}%")
        
        with col2:
            if margen_30 is not None:
                st.metric("🗓️ Margen 30 días", f"{margen_30:.1f}%")
        
        with col3:
            st.markdown("#### 🧠 Análisis de Margen")
            st.markdown(f"<div style='font-size:1.1rem'>{analisis}</div>", unsafe_allow_html=True)

        st.markdown("#### 🧩 Estrategia y Prioridad")
        st.write("**🎯 Estrategia Recomendada:**", estrategia)
        st.write("**🏅 Prioridad:**", prioridad)
    def tab_estacionalidad(self, df):
        st.markdown("### 📊 Estacionalidad del Artículo")

        st.write("**📆 Mes Pico:**", df["mes_pico"].iloc[0].capitalize())
        st.write("**📉 Mes Bajo:**", df["mes_bajo"].iloc[0].capitalize())
        st.write("**📈 Contraste Relativo Mensual:**", f"{df['mes_actual'].iloc[0]:.2f}%")
        st.write("**📊 Nivel Mensual:**", df["ranking_mes"].iloc[0])
        st.write("**📅 Meses Activos Estacionalidad:**", df["meses_act_estac"].iloc[0])

        contraste = df["mes_actual"].iloc[0]
        meses_activos = df["meses_act_estac"].iloc[0]

        if contraste > 30 and meses_activos <= 4:
            interpretacion = "🌞 Alta estacionalidad: ventas concentradas en pocos meses"
        elif contraste > 20:
            interpretacion = "📈 Estacionalidad moderada"
        else:
            interpretacion = "📉 Estacionalidad baja o estable"
        st.info(f"**🔍 Interpretación:** {interpretacion}")

        ### nuevo analisis por articulo:
    def show_presupuesto_estrategico(self, df):
        if df is None or df.empty:
            st.warning("⚠️ No hay datos disponibles para el análisis de presupuesto.")
            return
        
        col1, col2 = st.columns(2)

        with col1:
            st.subheader(f"📆 Fecha del Presupuesto cargado: {df['fecha'].iloc[0]}")
        with col2:
            st.subheader(f"🛒 Cantidad de articulos presentes: {len(df)}")

        tabs = st.tabs([
            "🔄 Reposición Inmediata",
            "🏬 Presupuesto por Sucursal",
            "⚠️ Riesgo de Quiebre",
            "📦 Exceso de Stock",
            "📆 Estacionalidad",
            "📉 Oportunidad Perdida",
            "💲 Ajuste de Precios",
            "📋 DataFrame"
        ])

        with tabs[0]:
            self.analisis_reposicion(df)

        with tabs[1]:
            self.analisis_presupuesto_sucursal(df)

        with tabs[2]:
            self.analisis_riesgo_quiebre(df)

        with tabs[3]:
            self.analisis_exceso_stock(df)

        with tabs[4]:
            self.analisis_estacionalidad(df)

        with tabs[5]:
            self.analisis_oportunidad_perdida(df)

        with tabs[6]:
            self.analisis_ajuste_precios(df)

        with tabs[7]:
            st.dataframe(df)

    def analisis_reposicion(self,df):
        df_reponer = df[df['cantidad_optima'] > 0].copy()
        st.subheader("🔄 Artículos a Reponer")
        st.metric("Costo Total de Reposición", f"${df_reponer['PRESUPUESTO'].sum():,.0f}")
        columnas = ["idarticulo", "descripcion", "cantidad_optima", "PRESUPUESTO",
                    "stk_corrientes", "stk_express", "stk_formosa", "stk_hiper", "stk_TIROL", "stk_central", "STK_TOTAL",
                    "cor_abastecer", "exp_abastecer", "for_abastecer", "hip_abastecer", "total_abastecer"]
        st.dataframe(df_reponer[columnas], width="stretch")

    def analisis_presupuesto_sucursal(self, df):
        st.subheader("🏬 Presupuesto Estimado y Cobertura por Sucursal")

        df_reponer = df[df["cantidad_optima"] > 0].copy()
        sucursales = ['cor_abastecer', 'exp_abastecer', 'for_abastecer', 'hip_abastecer']

        for suc in sucursales:
            if suc in df_reponer.columns:
                df_reponer[suc] = df_reponer[suc].clip(lower=0)

        df_reponer["total_abastecer"] = df_reponer[sucursales].sum(axis=1)
        for suc in sucursales:
            df_reponer[f"{suc}_pct"] = df_reponer[suc] / df_reponer["total_abastecer"]
            df_reponer[f"{suc}_optima"] = df_reponer[f"{suc}_pct"] * df_reponer["cantidad_optima"]
            df_reponer[f"{suc}_presupuesto"] = df_reponer[f"{suc}_optima"] * df_reponer["costo_unit"]

        costos = {
            suc.replace("_abastecer", ""): df_reponer[f"{suc}_presupuesto"].sum()
            for suc in sucursales
        }

        df_costos = pd.DataFrame(costos.items(), columns=["Sucursal", "Presupuesto ($)"])
        # df_costos["Presupuesto ($)"] = df_costos["Presupuesto ($)"].astype(int)
        df_costos["Presupuesto ($)"] = (
                pd.to_numeric(df_costos["Presupuesto ($)"], errors="coerce")
                .fillna(0)
                .round(0)
                .astype(int)
            )
        df_costos["texto"] = df_costos["Presupuesto ($)"].apply(lambda x: f"${x:,.0f}")
        df_costos = df_costos.sort_values(by="Presupuesto ($)", ascending=False)

        # === Nueva gráfica: Cantidad de artículos por sucursal con distribución > 0 ===
        suc_porc = {
            "CORRIENTES": "cor_porc",
            "HIPER": "hip_porc",
            "FORMOSA": "for_porc",
            "EXPRESS": "exp_porc"
        }

        cantidad_articulos = {
            nombre: (df[df[col] > 0].shape[0]) for nombre, col in suc_porc.items()
        }

        df_cantidad = pd.DataFrame(cantidad_articulos.items(), columns=["Sucursal", "Artículos con Venta"])
        df_cantidad = df_cantidad.sort_values(by="Artículos con Venta", ascending=False)
        df_cantidad["texto"] = df_cantidad["Artículos con Venta"].apply(lambda x: f"{x:,}")

        # === Mostrar ambas gráficas en columnas ===
        col1, col2 = st.columns(2)

        with col1:
            fig1 = px.bar(
                df_costos,
                x="Sucursal",
                y="Presupuesto ($)",
                text="texto",
                title="💰 Presupuesto por Sucursal",
                color="Presupuesto ($)",
                color_continuous_scale="Reds"
            )
            fig1.update_traces(textposition="outside", hovertemplate="<b>%{x}</b><br>Presupuesto: %{text}<extra></extra>")
            fig1.update_layout(title_font=dict(size=16, color="#333"), title_x=0.08, showlegend=False, coloraxis_showscale=False, xaxis_title=None,
            yaxis_title=None, margin=dict(t=60, b=40, l=30, r=20))
            fig1.update_yaxes(showticklabels=False)
            st.plotly_chart(fig1, width="stretch")

        with col2:
            fig2 = px.bar(
                df_cantidad,
                x="Sucursal",
                y="Artículos con Venta",
                text="texto",
                title="📦 Artículos con Venta Activa",
                color="Artículos con Venta",
                color_continuous_scale="Greens"
            )
            fig2.update_traces(textposition="outside", hovertemplate="<b>%{x}</b><br>Artículos: %{text}<extra></extra>")
            fig2.update_layout(title_font=dict(size=16, color="#333"), title_x=0.08, showlegend=False,xaxis_title=None,
            yaxis_title=None, coloraxis_showscale=False, margin=dict(t=60, b=40, l=30, r=20))
            fig2.update_yaxes(showticklabels=False)
            st.plotly_chart(fig2, width="stretch")

    def analisis_riesgo_quiebre(self, df):

        col1, col2 = st.columns([2, 1])

        with col1:
            # st.subheader(" Análisis de Quiebres")
            st.markdown("#### 📈 Análisis de Pérdidas Potenciales por Quiebre")

        with col2:
            st.markdown(
                """
                <style>
                div[data-testid="stRadio"] > label {
                    justify-content: center;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            opcion_dias = st.radio(
                label="Seleccionar la cantidad de días a proyectar:",
                options=["7 días", "15 días", "30 días", "45 días"],
                index=2,
                horizontal=True
            )


        # Diccionario de equivalencias para 33 días hábiles
        dias_dict = {
            "7 días": 7,
            "15 días": 15,
            "30 días": 30,
            "45 días": 45
        }

        dias_analisis = dias_dict[opcion_dias]
        multiplicador = dias_analisis / 33

        # Validar y ajustar demanda
        if "cantidad_optima_base_33d" not in df.columns:
            df["cantidad_optima_base_33d"] = df["cantidad_optima"]

        df["cantidad_optima"] = df["cantidad_optima_base_33d"] * multiplicador

#######################################################
        df_quiebre = analizar_quiebre(df)
        mostrar_analisis_quiebre_detallado(df_quiebre)


        st.subheader("⚠️ Riesgo de Quiebre")
        if df is None or df.empty:
            st.warning("⚠️ No hay datos disponibles para el análisis de riesgo.")
            return

        # === Paso 1: Filtrar y reemplazar niveles ===
        riesgo_mapeo = {
            'Alto': '🔴 Alto',
            'Medio': '🟠 Medio',
            'Bajo': '🟡 Bajo',
            'Muy Bajo': '🟢 Muy Bajo',
            'Analizar stk': '🔍 Analizar stk'
        }

        riesgo_color = {
            '🔴 Alto': '#e74c3c',
            '🟠 Medio': '#f39c12',
            '🟡 Bajo': '#f1c40f',
            '🟢 Muy Bajo': '#2ecc71',
            '🔍 Analizar stk': '#95a5a6'
        }

        df_riesgo = df[df['nivel_riesgo'].isin(riesgo_mapeo.keys())].copy()
        df_riesgo['nivel_riesgo'] = df_riesgo['nivel_riesgo'].replace(riesgo_mapeo)

        # === Paso 2: Conteo para gráfica (orden dinámico) ===
        conteo = df_riesgo['nivel_riesgo'].value_counts().sort_values(ascending=True)
        colores = [riesgo_color[nivel] for nivel in conteo.index]

        fig = go.Figure(go.Bar(
            x=conteo.values,
            y=conteo.index,
            orientation='h',
            text=[f"{v:,}" for v in conteo.values],
            textposition='outside',
            marker_color=colores,
            hovertemplate='%{y}: %{x:,}<extra></extra>'  # Tooltips personalizados
        ))

        fig.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(visible=False),
            yaxis=dict(visible=True),
            showlegend=False
        )

        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("📊 Distribución del riesgo de quiebre")
            st.plotly_chart(fig, width="stretch")

        with col2:
            # ✅ Formatear columnas
            df_riesgo['cantidad_optima'] = df_riesgo['cantidad_optima'].astype(int).map(lambda x: f"{x:,}")
            df_riesgo['dias_cobertura'] = df_riesgo['dias_cobertura'].map(lambda x: f"{x:.1f}")

            # ✅ Ordenar por nivel de riesgo visualmente
            orden_riesgo = ['🔴 Alto', '🟠 Medio', '🟡 Bajo', '🟢 Muy Bajo', '🔍 Analizar stk']
            df_riesgo['orden'] = df_riesgo['nivel_riesgo'].apply(lambda x: orden_riesgo.index(x))
            df_riesgo = df_riesgo.sort_values(by='orden').drop(columns='orden')

            columnas = ["idarticulo", "descripcion", "dias_cobertura", "nivel_riesgo", "cantidad_optima"]
            st.caption(f"🔍 {len(df_riesgo)} artículos en riesgo de quiebre")
            st.dataframe(df_riesgo[columnas].head(300), width="stretch", hide_index=True)

        # 📥 Exportación opcional
        csv = df_riesgo[columnas].to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Riesgo de Quiebre", csv, "riesgo_quiebre.csv", "text/csv")

    def analisis_exceso_stock(self, df):
        st.subheader("📦 Exceso de Stock")

        if df is None or df.empty:
            st.warning("⚠️ No hay datos disponibles para el análisis de exceso.")
            return

        # Filtrar artículos con exceso
        df_exceso = df[(df['exceso_STK'] > 0) & (df['dias_cobertura'] > 0)].copy()

        if df_exceso.empty:
            st.info("✅ No se detectaron artículos con exceso de stock.")
            return

        # Categorizar días de cobertura en rangos
        def categorizar_dias(d):
            if d <= 30:
                return "🟢 0-30 días"
            elif d <= 60:
                return "🟡 31-60 días"
            elif d <= 90:
                return "🟠 61-90 días"
            else:
                return "🔴 90+ días"

        df_exceso["rango_cobertura"] = df_exceso["dias_cobertura"].apply(categorizar_dias)

        # Conteo por rango
        orden = ["🟡 31-60 días", "🟠 61-90 días", "🔴 90+ días"]
        colores = [ "#f1c40f", "#e67e22", "#e74c3c"]
        # orden = ["🟢 0-30 días", "🟡 31-60 días", "🟠 61-90 días", "🔴 90+ días"]
        # colores = ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"]
        conteo = df_exceso["rango_cobertura"].value_counts().reindex(orden).fillna(0).astype(int)

        # Crear gráfico
        fig = go.Figure(go.Bar(
            x=conteo.values,
            y=conteo.index,
            orientation='h',
            text=[f"{v:,}" for v in conteo.values],
            textposition='outside',
            marker_color=colores,
            hovertemplate='%{y}: %{x:,}<extra></extra>'
        ))

        fig.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(visible=False),
            yaxis=dict(visible=True),
            showlegend=False
        )

        # Dividir en columnas
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("📊 Distribución del exceso de stock por días de cobertura")
            st.plotly_chart(fig, width="stretch")

        with col2:
            # Formatear columnas
            df_exceso['exceso_STK_format'] = df_exceso['exceso_STK'].astype(int).map(lambda x: f"{x:,}")
            df_exceso['costo_exceso_STK_format'] = df_exceso['costo_exceso_STK'].map(lambda x: f"${x:,.0f}")
            df_exceso['dias_cobertura_format'] = df_exceso['dias_cobertura'].map(lambda x: f"{x:.0f}")

            # Ordenar por mayor costo
            df_exceso = df_exceso.sort_values(by='costo_exceso_STK', ascending=False)

            columnas = ["idarticulo", "descripcion", "exceso_STK_format", "costo_exceso_STK_format", "dias_cobertura_format"]
            st.markdown(f"📦 {len(df_exceso)} artículos con exceso de stock detectado")
            st.dataframe(df_exceso[columnas].head(300), width="stretch", hide_index=True)

        with st.expander("🔎 Visualizar Exceso por Impacto", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("##### 💥 Exceso de Stock: Cantidad vs Días de cobertura")
                with col2:
                    total_costo = df_exceso["costo_exceso_STK"].sum()
                    st.markdown(f"##### 💰 **Total inmovilizado en exceso:** `${total_costo:,.0f}`")

                df_top = df_exceso.sort_values("costo_exceso_STK", ascending=False).head(50).copy()

                # Validar y limpiar columnas necesarias
                for col in ["costo_exceso_STK", "exceso_STK", "dias_cobertura"]:
                    df_top[col] = pd.to_numeric(df_top[col], errors='coerce')

                df_top = df_top.dropna(subset=["costo_exceso_STK", "exceso_STK", "dias_cobertura"])

                if df_top.empty:
                    st.warning("⚠️ No hay datos válidos para graficar el impacto del exceso.")
                else:
                    df_top["producto_corto"] = df_top["descripcion"].str[:40] + "..."

                    fig = px.scatter(
                        df_top,
                        x="exceso_STK",
                        y="dias_cobertura",
                        size="costo_exceso_STK",
                        color="rango_cobertura",
                        hover_name="producto_corto",
                        hover_data={
                            "exceso_STK": ":,.0f",
                            "dias_cobertura": ":.0f",
                            "costo_exceso_STK": "$:,.0f",
                            "producto_corto": False
                        },
                        title="🧮 Exceso de Stock: Volumen vs Cobertura",
                        labels={
                            "exceso_STK": "Cantidad Excedente",
                            "dias_cobertura": "Días de Cobertura",
                            "costo_exceso_STK": "Costo Exceso ($)",
                            "rango_cobertura": "Rango de Cobertura"
                        },
                        color_discrete_sequence=["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71"],
                        size_max=70
                    )

                    fig.update_traces(marker=dict(opacity=0.9, line=dict(width=1,color="gray")))
                    fig.update_layout(
                        height=600,
                        title_font=dict(size=18, color='#454448', family='Arial Black'),
                        title_x=0.05,
                        margin=dict(t=60, b=20, l=10, r=10),
                        legend_title_text="Cobertura", xaxis_type='log'
                    )

                    st.plotly_chart(fig, width="stretch")
#################################################################
                    # === INSIGHTS AUTOMÁTICOS ===
                    st.markdown("### 📌 Insights Clave del Exceso de Stock")

                    # Producto con mayor exceso en $
                    top_exceso = df_top.loc[df_top["costo_exceso_STK"].idxmax()]
                    st.markdown(f"""
                    - 🔝 **Mayor inmovilizado:** El producto **{top_exceso['producto_corto']}** tiene el mayor exceso de stock con un valor de **${top_exceso['costo_exceso_STK']:,.0f}**, acumulando **{int(top_exceso['dias_cobertura'])} días** de cobertura y **{int(top_exceso['exceso_STK'])} unidades** excedentes.
                    """)

                    # Casos críticos por cobertura extrema
                    criticos = df_top[df_top["dias_cobertura"] > 120]
                    if not criticos.empty:
                        n_criticos = len(criticos)
                        promedio_exceso = criticos["costo_exceso_STK"].mean()
                        st.markdown(f"""
                        - ⚠️ **{n_criticos} productos tienen más de 120 días de cobertura**, lo que indica riesgo de obsolescencia. 
                        El valor promedio inmovilizado por producto en este grupo es de **${promedio_exceso:,.0f}**.
                        """)
                    else:
                        st.markdown("- ✅ **No hay productos con más de 120 días de cobertura**, lo cual es positivo para el flujo de rotación.")

                    # Productos con mucho volumen pero menor cobertura
                    volumen_alto_baja_cobertura = df_top[(df_top["exceso_STK"] > 1000) & (df_top["dias_cobertura"] < 60)]
                    if not volumen_alto_baja_cobertura.empty:
                        st.markdown(f"""
                        - 📦 **{len(volumen_alto_baja_cobertura)} productos presentan alto volumen excedente (>1.000 unidades) pero baja cobertura (<60 días)**. 
                        Podrían redistribuirse a sucursales con mayor demanda para evitar saturación local.
                        """)
                    
                    # Recomendación final
                    st.markdown("""
                    ### ✅ Recomendaciones:
                    - 🔄 Reasignar stock de productos con >90 días de cobertura hacia zonas de mayor rotación.
                    - 🧼 Revisar precios y promociones para liquidar los productos con mayor inmovilizado.
                    - 🔍 Evaluar estrategias de compra para evitar reincidencia de estos excesos.
                    """)
##########################################################################
                    # === INSIGHTS POR SEGMENTO DE COBERTURA ===
                    st.markdown("### 🔍 Análisis por Segmento de Cobertura")

                    segmentos = {
                        "🟡 31-60 días": "Moderado",
                        "🟠 61-90 días": "Alto",
                        "🔴 90+ días": "Crítico"
                    }

                    for nivel, descripcion in segmentos.items():
                        df_seg = df_top[df_top["rango_cobertura"] == nivel]

                        if not df_seg.empty:
                            total_valor = df_seg["costo_exceso_STK"].sum()
                            promedio_dias = df_seg["dias_cobertura"].mean()
                            producto_top = df_seg.loc[df_seg["costo_exceso_STK"].idxmax()]

                            # === Encabezado y lista al lado ===
                            col1, col2 = st.columns([1.5, 2])
                            with col1:
                                st.markdown(f"#### {nivel} — Exceso {descripcion}")
                            with col2:
                                with st.expander(f"🔽 Ver artículos en {nivel}", expanded=False):
                                    cols_mostrar = ["idarticulo", "descripcion", "exceso_STK", "costo_exceso_STK"]
                                    df_vista = df_seg[cols_mostrar].copy()
                                    df_vista = df_vista.rename(columns={
                                        "idarticulo": "🆔 ID Artículo",
                                        "descripcion": "📦 Producto",
                                        "exceso_STK": "📊 Exceso (Unid.)",
                                        "costo_exceso_STK": "💰 Costo Exceso"
                                    })
                                    df_vista = df_vista.sort_values("💰 Costo Exceso", ascending=False)
                                    df_vista["💰 Costo Exceso"] = df_vista["💰 Costo Exceso"].apply(lambda x: f"${x:,.0f}")
                                    st.dataframe(df_vista, width="stretch", hide_index=True)

                                    # Descargar CSV
                                    csv_data = df_seg[cols_mostrar].to_csv(index=False).encode("utf-8")
                                    st.download_button(
                                        label=f"📥 Descargar CSV de {nivel}",
                                        data=csv_data,
                                        file_name=f"exceso_segmento_{nivel.replace(' ', '_')}.csv",
                                        mime="text/csv"
                                    )

                            # === Detalles de KPIs e insights ===
                            st.markdown(f"""
                            - 🧾 **Total inmovilizado:** ${total_valor:,.0f}
                            - 📅 **Cobertura promedio:** {promedio_dias:.1f} días
                            - 🏷️ **Producto con mayor exceso:** {producto_top['producto_corto']} (${producto_top['costo_exceso_STK']:,.0f}, {int(producto_top['dias_cobertura'])} días)
                            """)

                            # Recomendación por segmento
                            if nivel == "🟡 31-60 días":
                                st.markdown("- 🟡 Recomendación: **Monitorear de cerca y planificar redistribución o promociones si no rota en las próximas semanas.**")
                            elif nivel == "🟠 61-90 días":
                                st.markdown("- 🟠 Recomendación: **Aplicar acciones correctivas ya (bonificaciones, descuentos selectivos, rotación interna).**")
                            elif nivel == "🔴 90+ días":
                                st.markdown("- 🔴 Recomendación: **Acción inmediata: evaluar liquidación, promociones agresivas o devolución a proveedor si aplica.**")

                        else:
                            st.markdown(f"- ✅ No hay productos en el rango {nivel}, lo cual indica una buena rotación en este segmento.")

#################################################################
        with st.expander("🔎 Visualizar Exceso por Impacto", expanded=True):

            # === Análisis de Pareto - Exceso de Stock ===
            pareto_exceso = df_top.sort_values("costo_exceso_STK", ascending=False).copy()
            pareto_exceso["Participación %"] = pareto_exceso["costo_exceso_STK"] / pareto_exceso["costo_exceso_STK"].sum() * 100
            pareto_exceso["ranking"] = range(1, len(pareto_exceso) + 1)
            pareto_exceso["descripcion_corta"] = pareto_exceso.apply(lambda row: f"{row['ranking']} - {row['producto_corto'][:14]}...", axis=1)
            pareto_exceso["acumulado"] = pareto_exceso['Participación %'].cumsum()
            pareto_exceso["individual_fmt"] = pareto_exceso["Participación %"].map("{:.1f}%".format)
            pareto_exceso["acumulado_fmt"] = pareto_exceso["acumulado"].map("{:.0f}%".format)

            fig = make_subplots(specs=[[{"secondary_y": True}]])

            # === Barras de participación individual ===
            fig.add_trace(
                go.Bar(
                    x=pareto_exceso["descripcion_corta"],
                    y=pareto_exceso['Participación %'],
                    name='Participación Individual (%)',
                    marker_color='lightcoral',
                    text=pareto_exceso["individual_fmt"],
                    textposition='outside',
                    hovertemplate="<b>%{customdata[0]}</b><br>Participación Individual: %{text}<extra></extra>",
                    customdata=pareto_exceso[["descripcion"]]
                ),
                secondary_y=False
            )

            # === Línea de participación acumulada ===
            fig.add_trace(
                go.Scatter(
                    x=pareto_exceso["descripcion_corta"],
                    y=pareto_exceso["acumulado"],
                    mode='lines+markers+text',
                    name='Participación Acumulada (%)',
                    line=dict(color='red', width=1),
                    text=pareto_exceso["acumulado_fmt"],
                    textposition="top center",
                    hovertemplate="<b>%{customdata[0]}</b><br>Participación Acumulada: %{y:.1f}%<extra></extra>",
                    customdata=pareto_exceso[["descripcion"]]
                ),
                secondary_y=True
            )

            fig.update_layout(
                title_text="📈 Análisis de Pareto - Concentración del Exceso de Stock",
                title_font=dict(size=18, color='#454448', family='Arial Black'),
                title_x=0.08,
                xaxis_title="Ranking de Productos",
                yaxis_title="Participación Individual (%)",
                height=600,
                margin=dict(t=70, b=50),
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=1.075,
                    xanchor="center",
                    x=0.45,
                    bgcolor='rgba(0,0,0,0)'
                )
            )

            fig.update_yaxes(title_text="Participación Individual (%)", secondary_y=False)
            fig.update_yaxes(title_text="Participación Acumulada (%)", secondary_y=True)

            st.plotly_chart(fig, width="stretch")

            # === Insight automático del Pareto ===
            top_pareto = pareto_exceso[pareto_exceso["acumulado"] <= 80]
            cant_top = len(top_pareto)
            contribucion_top = top_pareto["costo_exceso_STK"].sum()

            st.markdown(f"""
            <div style='background-color:#f8f9fa;padding:1rem;border-radius:10px;border-left:5px solid #e74c3c'>
            <b>🧠 Insight Pareto:</b><br>
            - 🔝 <b>{cant_top} productos</b> concentran el <b>80% del exceso de stock</b> (inmovilizado total: <b>${contribucion_top:,.0f}</b>).<br>
            - 🎯 Enfocar promociones, rebalanceos o acciones agresivas <b>en este grupo crítico</b> para reducir drásticamente el capital inmovilizado.
            </div>
            """, unsafe_allow_html=True)



#################################################################
        # Exportar versión sin formato
        columnas_old = ["idarticulo", "descripcion", "exceso_STK", "costo_exceso_STK", "dias_cobertura"]
        df_export = df[df['exceso_STK'] > 0][columnas_old]
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Exceso de Stock", csv, "exceso_stock.csv", "text/csv")

    def analisis_estacionalidad(self, df):
        st.subheader("📆 Estacionalidad y Demanda")

        if df is None or df.empty:
            st.warning("⚠️ No hay datos para el análisis estacional.")
            return

        # === Paso 1: Etiquetado estacional
        df_estacional = df.copy()
        df_estacional['Etiqueta Estacional'] = df_estacional['ranking_mes'].apply(
            lambda x: "📈 Mes Alto" if x >= 9 else ("📉 Mes Bajo" if x <= 4 else "Mes Intermedio")
        )

        # === Paso 2: Mapeo de meses abreviados a números
        mes_map = {
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4,
            'may': 5, 'jun': 6, 'jul': 7, 'ago': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
        }

        df_estacional["mes_pico_num"] = df_estacional["mes_pico"].map(mes_map)

        # === Paso 3: KPI - Productos en su mes pico actual
        mes_actual = datetime.now().month
        en_temporada = df_estacional[df_estacional["mes_pico_num"] == mes_actual]
        total_temporada = len(en_temporada)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("📋 Artículos con análisis estacional", f"{len(df_estacional):,}")

        with col2:
            st.metric("📌 Productos en su mes pico actual", f"{total_temporada:,}")

        # === Paso 4: Gráfico de barras por etiqueta
        conteo = df_estacional['Etiqueta Estacional'].value_counts().reindex(
            ["📈 Mes Alto", "Mes Intermedio", "📉 Mes Bajo"]
        ).fillna(0).astype(int)

        fig = px.bar(
            x=conteo.index,
            y=conteo.values,
            text=conteo.values,
            color=conteo.index,
            title="Distribución de Productos por Estacionalidad",
            color_discrete_map={
                "📈 Mes Alto": "#27ae60",
                "📉 Mes Bajo": "#c0392b",
                "Mes Intermedio": "#f1c40f"
            },
            labels={"x": "", "y": ""}
        )

        fig.update_traces(textposition='outside')
        fig.update_layout(
            showlegend=False,
            height=400,
            margin=dict(t=60, b=20, l=10, r=10),
            title_font=dict(size=14, color='#333', family='Arial Black'),
            title_x=0.1
        )

        # === Paso 5: Layout horizontal 1/3 gráfico - 2/3 tabla
        col1, col2 = st.columns([1, 2])

        with col1:
            st.plotly_chart(fig, width="stretch")

        with col2:
            df_estacional['cantidad_optima'] = df_estacional['cantidad_optima'].astype(int).map(lambda x: f"{x:,}")
            df_estacional = df_estacional.sort_values(by="ranking_mes", ascending=False)
            columnas = ["idarticulo", "descripcion", "mes_pico", "mes_bajo", "ranking_mes", "Etiqueta Estacional", "cantidad_optima"]

            # st.caption(f"📋 {len(df_estacional)} artículos con análisis estacional")
            st.dataframe(df_estacional[columnas], width="stretch", hide_index=True)

        # === Paso 6: Descargar CSV con columnas visibles
        csv = df_estacional[columnas].to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "analisis_estacionalidad.csv", "text/csv")

    def analisis_oportunidad_perdida(self,df):
        st.subheader("📉 Valor Perdido por Falta de Stock")
        df_perdido = df[df['costo_exceso_STK'] > 0].copy()
        # st.dataframe(df_perdido[["idarticulo", "descripcion", "valor_perdido_TOTAL", "unidades_perdidas_TOTAL", "cnt_reabastecer"]], width="stretch")

    def analisis_ajuste_precios(self, df=None):
        st.subheader("💲 Propuesta de Ajuste de Precios")

        if df is None:
            df = st.session_state.get("resultados_data")

        if df is None or df.empty:
            st.warning("⚠️ No hay datos disponibles para el análisis de precios.")
            return

        # === Paso 1: Reducir columnas necesarias ===
        columnas_necesarias = [
            "idarticulo", "descripcion", "precio_actual","costo_unit",
            "precio_optimo_ventas", "decision_precio", "pred_ventas_actual"
        ]

        df_reducido = df[columnas_necesarias].copy()
        df_reducido['decision_precio'] = df_reducido['decision_precio'].fillna('datos insuficientes')
        df_reducido['decision_precio'] = df_reducido['decision_precio'].replace('Modelo no confiable', 'datos insuficientes')

        # === Paso 2: Conteo para gráfica ===
        orden = ['🔻 rebaja', '🔺 alza', '✅ Mantener', 'datos insuficientes']
        conteo = df_reducido['decision_precio'].value_counts().reindex(orden).fillna(0).astype(int)

        fig = go.Figure(go.Bar(
            x=conteo.values,
            y=conteo.index,
            orientation='h',
            text=[f"{v:,}" for v in conteo.values],
            textposition='outside',
            marker_color=['#FF6B6B', '#4ECDC4', '#CFCFCF', '#B0BEC5'],
            hoverinfo='skip'
        ))

        fig.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(visible=False),
            yaxis=dict(visible=True),
            showlegend=False
        )

        col1, col2 = st.columns([1, 2])

        with col1:
            st.caption("📊 Distribución del análisis de variación de precios")
            st.plotly_chart(fig, width="stretch")

        with col2:
            df_final = df_reducido[df_reducido['decision_precio'].isin(['🔻 rebaja', '🔺 alza'])].copy()

            # ✅ Formatear columnas para mostrar
            df_final['precio_actual'] = df_final['precio_actual'].map(lambda x: f"${x:,.2f}")
            df_final['costo_unit'] = df_final['costo_unit'].map(lambda x: f"${x:,.2f}")
            df_final['precio_optimo_ventas'] = df_final['precio_optimo_ventas'].map(lambda x: f"${x:,.2f}")
            df_final.rename(columns={"pred_ventas_actual": "venta para hoy"}, inplace=True)
            df_final["venta para hoy"] = df_final["venta para hoy"].astype(int)

            st.caption(f"🎯 {len(df_final)} artículos con propuesta de cambio de precio")
            st.dataframe(df_final, width="stretch", hide_index=True)


        # Descargar versión sin formato
        df_export = df_reducido[df_reducido['decision_precio'].isin(['🔻 rebaja', '🔺 alza'])]
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "ajuste_precios.csv", "text/csv")

    def run(self):
        """Ejecutar dashboard"""
        # Filtros del sidebar → ahora devuelve también df_presu
        self.proveedor, self.fecha_inicio, self.fecha_fin, df_presu = self.show_sidebar_filters()
        
        # Mostrar análisis principal
        self.show_main_dashboard()

        # Análisis detallado por artículo
        # st.markdown("---")
        # st.markdown("## 🔍 Análisis Detallado por Artículo")
        # self.show_idarticulo_analysis_01(df_presu)

        # === Extraer datos de análisis por idarticulo ===
        self.df_resultados = query_resultados_idarticulo(
            credentials_path=self.credentials_path,
            project_id=self.project_id,
            dataset='presupuesto',
            table='result_final_alert_all'
        )

        # Análisis detallado por artículo
        # st.markdown("---")
        # st.markdown("## 🔍 Análisis Detallado por Artículo")
        # self.show_idarticulo_analysis()

        # Footer
        # st.markdown("---")
        st.markdown("""
        <hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />
        <div style="text-align: center; color: #666; font-size: 0.8em;margin-top: 20px;">
            Julio A. Lazarte    |    Científico de Datos & BI   |   Cucher Mercados
        </div>
        """, unsafe_allow_html=True)
def main():
    dashboard = ProveedorDashboard()
    dashboard.run()
if __name__ == "__main__":
    main()
