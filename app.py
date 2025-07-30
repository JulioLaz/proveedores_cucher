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


locale = Locale.parse('es_AR')

def format_abbr(x):
    if x >= 1_000_000: return f"${x/1_000_000:.1f}M"
    elif x >= 1_000: return f"${x/1_000:.0f}K"
    else: return f"${x:.0f}"

# === CONFIGURACION DE PAGINA ===
st.set_page_config(page_title="Proveedores", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# === CARGAR CSS PERSONALIZADO ===
st.markdown(custom_css(), unsafe_allow_html=True)

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
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 💰 Resumen Financiero por Grupo")
            st.dataframe(resumen_urgencia, use_container_width=True)
        
        # Productos críticos
        st.markdown("#### 🚨 Productos que Requieren Atención Inmediata")
        criticos = df[df['grupo_urgencia'].isin(["🚨 CRÍTICO", "⚠️ URGENTE"])][
            ['idarticulo', 'descripcion', 'familia', 'nivel_riesgo', 'dias_cobertura', 
             'STK_TOTAL', 'prioridad']
        ].head(15)
        
        if not criticos.empty:
            st.dataframe(criticos, use_container_width=True)
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
                st.plotly_chart(fig, use_container_width=True)
            
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
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### 📋 Resumen Detallado")
            st.dataframe(df_sucursales, use_container_width=True)
        
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
                st.plotly_chart(fig, use_container_width=True)
        
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
                st.plotly_chart(fig, use_container_width=True)
        
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
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### 📦 Distribución de Productos")
                fig = px.pie(
                    values=familia_stats['Productos'],
                    names=familia_stats.index,
                    title="% de Productos por Familia"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### 📋 Resumen Detallado por Familia")
            st.dataframe(familia_stats, use_container_width=True)
        
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
        st.dataframe(top_acciones.drop(['score_prioridad'], axis=1, errors='ignore'), use_container_width=True)
        
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
            st.plotly_chart(fig, use_container_width=True)
        
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
    @st.cache_data(ttl=3600)
    def load_proveedores(_self):
        """Cargar datos de proveedores desde Google Sheet público"""
        url = f"https://docs.google.com/spreadsheets/d/{_self.sheet_id}/gviz/tq?tqx=out:csv&sheet={_self.sheet_name}"
        df = pd.read_csv(url)
        df = df.dropna(subset=['idproveedor'])  # elimina filas sin idproveedor
        df['idproveedor'] = df['idproveedor'].astype(int)
        df['proveedor'] = df['proveedor'].astype(str).str.strip().str.upper()
        return df
    def query_bigquery_data(self, proveedor, fecha_inicio, fecha_fin):
        """Consultar datos de BigQuery"""
        try:
            # Obtener IDs de artículos
            ids = self.df_proveedores[self.df_proveedores['proveedor'] == proveedor ]['idarticulo'].dropna().astype(int).astype(str).unique()
            
            if len(ids) == 0: return None
            
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
            client = bigquery.Client.from_service_account_json(credentials_path)

            query = f"""
                SELECT *
                FROM `{project_id}.{dataset}.{table}`
                WHERE idarticulo IS NOT NULL
                AND idproveedor = {idproveedor}
            """

            df = client.query(query).to_dataframe()

            if df.empty:
                st.warning(f"⚠️ No se encontraron datos para el proveedor con ID: {idproveedor}")
            # else:
                st.success(f"✅ Se encontraron {len(df)} registros para idproveedor {idproveedor}")
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
        if not proveedor_actual:
            st.sidebar.markdown('<div class="animated-title">🔎 proveedor ⬇️</div>', unsafe_allow_html=True)
        else:
            st.sidebar.markdown("#### 🏪 Selección de Proveedor")

        proveedor = st.sidebar.selectbox(
            "",
            options=proveedores,
            index=proveedores.index(proveedor_actual) if proveedor_actual in proveedores else None,
            placeholder="Seleccionar proveedor..."
        )

        # --- Rango de fechas ---
        rango_opciones = {
            "Último mes": 30,
            "Últimos 3 meses": 90,
            "Últimos 6 meses": 180,
            "Último año": 365,
            "Personalizado": None
        }

        if proveedor and "analysis_data" not in st.session_state:
            st.sidebar.markdown('<div class="highlight-period">📅 Elige un período de análisis</div>', unsafe_allow_html=True)

        rango_seleccionado = st.sidebar.selectbox(
            "📅 Período de Análisis:",
            options=list(rango_opciones.keys()),
            index=2
        )

        # Crear instancia de locale español
        locale_es = Locale.parse("es")

        # Selección de fechas
        if rango_seleccionado == "Personalizado":
            col1, col2 = st.sidebar.columns(2)
            fecha_inicio = col1.date_input("Desde:", value=datetime.now().date() - timedelta(days=180))
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
            st.sidebar.error("❌ No se encontró el ID del proveedor seleccionado.")
            return proveedor, fecha_inicio, fecha_fin, None

        if st.sidebar.button("Realizar Análisis", type="primary", use_container_width=True):
            if not proveedor:
                st.sidebar.error("❌ Selecciona un proveedor")
            else:
                with st.spinner(f"🔄 Consultando datos de {proveedor}"):
                    df_tickets = self.query_bigquery_data(proveedor, fecha_inicio, fecha_fin)
                    if df_tickets is not None:
                        st.session_state.analysis_data = df_tickets
                        st.session_state.selected_proveedor = proveedor
                        # st.rerun()
                    else:
                        st.sidebar.error("❌ No se encontraron datos para el período seleccionado")
                if fila > 0:
                    # st.write('idproveedor: ', fila)
                    with st.spinner(f"🔄 Consultando datos proveedor id: {fila}"):
                        df_presu = self.query_resultados_idarticulo(fila)
                        if df_presu is not None:
                            st.session_state.resultados_data = df_presu
                            # st.session_state.df_presu = df_presu
                            # st.rerun()
                        else:
                            st.sidebar.error("❌ No se encontraron datos de presupuesto para el proveedor")
                        # st.write(df_presu.head(5))
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
                <p style='padding:5px 0px; font-size:1.5rem; font-weight:semibold;'>📈 Dashboard de Análisis por Proveedor</p>
            </div>
            """, unsafe_allow_html=True)
        
        if st.session_state.analysis_data is None:

            # Mostrar información general
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("""
                ### 🎯 Funcionalidades
                - Análisis completo por proveedor
                - Métricas financieras avanzadas
                - Visualizaciones interactivas
                - Insights automáticos
                - Exportación de reportes
                """)
            
            with col2:
                st.markdown("""
                ### 📊 Métricas Incluidas
                - Ventas y rentabilidad
                - Análisis de productos
                - Evolución temporal
                - Distribución geográfica
                - Tendencias de mercado
                """)
            
            with col3:
                st.markdown("""
                ### 🔍 Análisis Avanzado
                - Top productos por categoría
                - Análisis de estacionalidad
                - Comparativas periodo a periodo
                - Identificación de oportunidades
                - Alertas de rendimiento
                """)
            return
        
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
            #tabs-bui171-tabpanel-1 > div > div:nth-child(1) > div.stColumn > div > div > div > label {
                display: none !important;
            }


        </style>
        """, unsafe_allow_html=True)

        # st.subheader(f"📈 Resumen Ejecutivo - {proveedor}")

        # === KPIs principales (manuales dentro de cajas HTML) ===
        col1, col2, col4, col5, col6 = st.columns(5)
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

        with col4:
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

        with col5:
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 1rem; color: #555;">📅 Días únicos con ventas</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #1e3c72;">{metrics['dias_con_ventas']}</div>
                </div>
                <div style="color: #888; font-size: 0.8rem; margin-top: 0.2rem;">
                    Período analizado
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col6:
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 1rem; color: #555;">🏪 Sucursales Presentes</div>
                    <div style="font-size: 1rem; color: #1e3c72; padding: .4rem 0rem">{metrics['sucursales_presentes']}</div>
                </div>
                <div style="color: #888; font-size: 0.8rem; margin-top: 0.2rem;">
                    Sucursales activas
                </div>
            </div>
            """, unsafe_allow_html=True)

        # === Insights automáticos ===
        insights = self.generate_insights(df, metrics)

        # Grilla 2 columnas
        cols = st.columns(2)
        for idx, (tipo, mensaje) in enumerate(insights):
            col = cols[idx % 2]
            with col:
                if tipo == "success":
                    st.markdown(f'<div class="success-box">{mensaje}</div>', unsafe_allow_html=True)
                elif tipo == "warning":
                    st.markdown(f'<div class="warning-box">{mensaje}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="insight-box">{mensaje}</div>', unsafe_allow_html=True)
            if (idx + 1) % 2 == 0 and idx + 1 < len(insights):
                cols = st.columns(2)

       # === Gráficas de resumen ===
        col1, col2 = st.columns(2)

        # === Evolución Diaria de Ventas ===
        with col1:
            ventas_diarias = df.groupby('fecha')['precio_total'].sum().reset_index()

            # Calcular línea de tendencia manual
            ventas_diarias['fecha_ordinal'] = ventas_diarias['fecha'].map(pd.Timestamp.toordinal)
            coef = np.polyfit(ventas_diarias['fecha_ordinal'], ventas_diarias['precio_total'], 1)
            ventas_diarias['tendencia'] = coef[0] * ventas_diarias['fecha_ordinal'] + coef[1]
            ventas_diarias['precio'] = ventas_diarias['precio_total'].apply(format_abbr)

            fig = px.line(
                ventas_diarias,
                x='fecha',
                y='precio_total',
                custom_data=['precio'],  # Enlazamos el valor formateado
                title="📈 Evolución Diaria de Ventas",
                labels={'fecha': '', 'precio_total': 'Ventas'}
            )

            # Estilizar la línea principal con tooltip
            fig.update_traces(
                line_color='#2a5298',
                line_width=1,
                hovertemplate='<b>Fecha:</b> %{x}<br><b>Ventas:</b> %{customdata[0]}<extra></extra>'
            )

            # Agregar línea de tendencia como línea (sin leyenda)
            fig.add_scatter(
                x=ventas_diarias['fecha'],
                y=ventas_diarias['tendencia'],
                mode='lines',
                line=dict(color='orange', width=1.5),
                showlegend=False,
                hoverinfo='skip'
            )

            fig.update_layout(
                height=300,
                margin=dict(t=60, b=20, l=10, r=10),
                title_x=0.2,
                xaxis_title=None,
                yaxis_title=None
            )

            st.plotly_chart(fig, use_container_width=True)


        # === Top 5 Productos por Ventas ===
        with col2:
            top_productos = (
                df.groupby('descripcion', as_index=False)['precio_total']
                .sum()
                .sort_values('precio_total', ascending=False)
                .head(5)
            )
            top_productos['descripcion_corta'] = top_productos['descripcion'].str[:30]
            top_productos['precio'] = top_productos['precio_total'].apply(format_abbr)

            fig = px.bar(
                top_productos,
                x='precio_total',
                y='descripcion_corta',
                orientation='h',
                text='precio',
                custom_data=['precio'],  # Enlazamos el valor formateado
                title="🏆 Top 5 Productos por Ventas",
                labels={'precio_total': '', 'descripcion_corta': ''}
            )
            fig.update_yaxes(categoryorder='total ascending')

            # Color uniforme profesional
            fig.update_traces(
                marker_color='#4682B4',
                textposition='outside',
                cliponaxis=False,
                insidetextanchor='start',
                hovertemplate='<b>Artículo:</b> %{y}<br><b>Venta:</b> %{customdata[0]}<extra></extra>'

            )

            fig.update_layout(
                height=300,
                margin=dict(t=60, b=20, l=10, r=80),
                title_x=0.2,  # Centrar título
                xaxis_title=None,
                yaxis_title=None,
                xaxis=dict(
                    showticklabels=False,  # ⛔ oculta los valores del eje x
                    showgrid=False,        # opcional: oculta líneas de grilla
                    zeroline=False         # opcional: oculta línea cero
                    )
                    )

            st.plotly_chart(fig, use_container_width=True, key="top_productos")
    def show_products_analysis(self, df):
        """Análisis detallado de productos"""
        # st.subheader("🏆 Análisis Detallado de Productos - TOP 20")

        try:
            # === Agrupar por descripción ===
            productos_stats = df.groupby("descripcion").agg({
                "precio_total": "sum",
                "costo_total": "sum",
                "cantidad_total": "sum"
            }).reset_index()

            productos_stats["Utilidad"] = productos_stats["precio_total"] - productos_stats["costo_total"]
            productos_stats["Margen %"] = 100 * productos_stats["Utilidad"] / productos_stats["precio_total"].replace(0, pd.NA)
            productos_stats["Participación %"] = 100 * productos_stats["precio_total"] / productos_stats["precio_total"].sum()

            productos_stats.rename(columns={
                "precio_total": "Ventas",
                "costo_total": "Costos",
                "cantidad_total": "Cantidad"
            }, inplace=True)

            # === Título y selector alineados en una fila ===
            col1, col2 = st.columns([5, 1])  # Ajusta proporción según el espacio que desees
            with col1:
                st.subheader("🏆 Análisis Detallado de Productos - TOP 20")
            with col2:
                orden_por = st.selectbox(
                    "",["Ventas", "Utilidad", "Margen %", "Cantidad", "Participación %"])

            # === Obtener top ordenado ===
            productos_top = productos_stats[productos_stats[orden_por].notna()].copy()
            productos_top = productos_top.sort_values(orden_por, ascending=False).head(20).copy()
            productos_top["Producto"] = productos_top["descripcion"].apply(lambda x: x[:40] + "..." if len(x) > 40 else x)

            # === Títulos ===
            titulo_dict = {
                "Ventas": "Top 20 Productos por Ventas 💰",
                "Utilidad": "Top 20 Productos por Utilidad 📈",
                "Margen %": "Top 20 Productos por Margen (%) 🧮",
                "Cantidad": "Top 20 Productos por Cantidad Vendida 📦",
                "Participación %": "Top 20 por Participación (%) del Total 🧭"
            }

            # === Gráfico principal ===
            fig = px.bar(
                productos_top,
                x="Producto",
                y=orden_por,
                text_auto='.2s' if orden_por in ["Ventas", "Utilidad"] else '.1f',
                title=titulo_dict[orden_por],
                labels={"Producto": "Producto", orden_por: orden_por}
            )
            fig.update_layout(
                title_font=dict(size=22, color='#454448', family='Arial Black'),
                title_x=0.3,
                height=400,
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(t=80, b=120),
                xaxis_tickangle=-45,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12),
                yaxis=dict(
                    showticklabels=False,  # ⛔ oculta los valores del eje x
                    showgrid=False,        # opcional: oculta líneas de grilla
                    zeroline=False         # opcional: oculta línea cero
                    
                    )
            )
            fig.update_traces(marker_color='#8966c6')
            st.plotly_chart(fig, use_container_width=True)

            if len(productos_top) < 5:
                st.warning(f"⚠️ Solo hay {len(productos_top)} productos disponibles con datos en '{orden_por}'.")

            ###############################################################################################################
            # === Gráfico adicional: Top 5 idarticulo por métrica y sucursal ===
            # === Gráfico adicional: Top 5 idarticulo por métrica y sucursal ===
            try:
                if "idarticulo" in df.columns and "sucursal" in df.columns:
                    
                    # Agrupar por sucursal e idarticulo
                    df_top5 = (
                        df.groupby(["sucursal", "idarticulo"])
                        .agg({
                            "precio_total": "sum",
                            "costo_total": "sum",
                            "cantidad_total": "sum"
                        })
                        .reset_index()
                    )

                    # Crear métricas
                    df_top5["Utilidad"] = df_top5["precio_total"] - df_top5["costo_total"]
                    df_top5["Margen %"] = 100 * df_top5["Utilidad"] / df_top5["precio_total"].replace(0, pd.NA)
                    df_top5["Participación %"] = 100 * df_top5["precio_total"] / df_top5["precio_total"].sum()

                    # Renombrar
                    df_top5.rename(columns={
                        "precio_total": "Ventas",
                        "costo_total": "Costos",
                        "cantidad_total": "Cantidad"
                    }, inplace=True)

                    # Ordenar sucursales por ventas totales
                    orden_sucursales = (
                        df.groupby("sucursal")["precio_total"].sum().sort_values(ascending=False).index.tolist()
                    )

                    # Obtener top 5 artículos por sucursal (en orden deseado)
                    df_top5 = df_top5[df_top5[orden_por].notna()]
                    df_top5 = df_top5.sort_values([ "sucursal", orden_por], ascending=[True, False])
                    df_top5 = df_top5.groupby("sucursal").head(5).copy()

                    # Convertir idarticulo a str para el eje x
                    df_top5["idarticulo"] = df_top5["idarticulo"].astype(str)

                    # Ordenar categoría compuesta para que Plotly las muestre bien agrupadas por sucursal
                    df_top5["Etiqueta"] = df_top5["sucursal"] + " - " + df_top5["idarticulo"]
                    df_top5["Etiqueta"] = pd.Categorical(df_top5["Etiqueta"], 
                                                        categories=[
                                                            f"{suc} - {idart}" 
                                                            for suc in orden_sucursales
                                                            for idart in df_top5[df_top5["sucursal"] == suc]["idarticulo"].tolist()
                                                        ],
                                                        ordered=True)

                    # Título
                    titulo_top5 = f"Top 5 ID Artículo por {orden_por} en cada Sucursal"

                    # Gráfico
                    fig2 = px.bar(
                        df_top5,
                        x="Etiqueta",
                        y=orden_por,
                        color="sucursal",
                        text_auto='.2s' if orden_por in ["Ventas", "Utilidad"] else '.1f',
                        title=titulo_top5,
                        labels={"Etiqueta": "ID Artículo por Sucursal", orden_por: orden_por}
                    )

                    # Layout profesional
                    fig2.update_layout(
                        title_font=dict(size=20, color='#454448', family='Arial Black'),
                        title_x=0.3,
                        height=500,
                        xaxis_title=None,
                        yaxis_title=None,
                        margin=dict(t=80, b=180),
                        xaxis_tickangle=-45,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=12),
                        yaxis=dict(
                            showticklabels=False,
                            showgrid=False,
                            zeroline=False
                        ),
                        legend_title_text='Sucursal'
                    )


                    # Formato condicional para etiquetas sobre barras en gráfico por sucursal
                    if orden_por == "Cantidad":
                        fig2.update_traces(
                            texttemplate='<b>%{y:,.0f}</b>',
                            textfont=dict(size=14),
                            textposition="outside"
                        )
                    elif orden_por in ["Ventas", "Utilidad"]:
                        fig2.update_traces(
                            texttemplate='<b>%{y:,.1f}</b>',
                            textfont=dict(size=14),
                            textposition="outside"
                        )
                    elif orden_por in ["Participación %", "Margen %"]:
                        fig2.update_traces(
                            texttemplate='<b>%{y:.1f}%</b>',
                            textfont=dict(size=14),
                            textposition="outside"
                        )


                    # Mostrar
                    st.plotly_chart(fig2, use_container_width=True)

                else:
                    st.info("⚠️ No se encontraron columnas 'idarticulo' o 'sucursal' en el DataFrame.")

            except Exception as e:
                st.error(f"❌ Error al generar la gráfica Top 5 por sucursal: {e}")




###############################################################################################################

            # === GRAFICOS ADICIONALES ===
            col1, col2 = st.columns(2)

            with col1:
                # Scatter plot Ventas vs Margen
                top_20 = productos_stats.sort_values("Ventas", ascending=False).head(20).copy()
                top_20["producto_corto"] = top_20["descripcion"].str[:30] + "..."

                fig = px.scatter(
                    top_20,
                    x="Ventas",
                    y="Margen %",
                    size="Cantidad",
                    color="Cantidad",
                    color_continuous_scale="viridis",
                    hover_name="producto_corto",
                    hover_data={"Utilidad": ":,.0f"},
                    title="💹 Ventas vs Margen (TOP 20)",
                    labels={'Ventas': 'Ventas ($)', 'Margen %': 'Margen (%)'}
                )

                fig.update_traces(marker=dict(opacity=0.8, line=dict(width=0)))
                fig.update_layout(
                    height=600,
                    title_font=dict(size=18, color='#454448', family='Arial Black'),
                    title_x=0.08,
                    # xaxis_title=None,
                # yaxis_title=None,
                    coloraxis_colorbar=dict(title='Cantidad'),
                    margin=dict(t=60, b=20, l=10, r=10)
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # === Análisis de Pareto con etiquetas y tooltips optimizados ===
                productos_pareto = productos_stats.sort_values("Ventas", ascending=False).head(20).copy()
                productos_pareto["ranking"] = range(1, len(productos_pareto) + 1)
                productos_pareto["descripcion_corta"] = productos_pareto.apply(lambda row: f"{row['ranking']} - {row['descripcion'][:14]}...", axis=1)
                productos_pareto["acumulado"] = productos_pareto['Participación %'].cumsum()
                productos_pareto["individual_fmt"] = productos_pareto["Participación %"].map("{:.1f}%".format)
                productos_pareto["acumulado_fmt"] = productos_pareto["acumulado"].map("{:.0f}%".format)

                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # === Barras ===
                fig.add_trace(
                    go.Bar(
                        x=productos_pareto["descripcion_corta"],
                        y=productos_pareto['Participación %'],
                        name='Participación Individual (%)',
                        marker_color='lightblue',
                        text=productos_pareto["individual_fmt"],
                        textposition='outside',
                        hovertemplate="<b>%{customdata[0]}</b><br>Participación Individual: %{text}<extra></extra>",
                        customdata=productos_pareto[["descripcion"]]
                    ),
                    secondary_y=False
                )

                # === Línea acumulada ===
                fig.add_trace(
                    go.Scatter(
                        x=productos_pareto["descripcion_corta"],
                        y=productos_pareto["acumulado"],
                        mode='lines+markers+text',
                        name='Participación Acumulada (%)',
                        line=dict(color='red', width=1),
                        text=productos_pareto["acumulado_fmt"],
                        textposition="top center",
                        hovertemplate="<b>%{customdata[0]}</b><br>Participación Acumulada: %{y:.1f}%<extra></extra>",
                        customdata=productos_pareto[["descripcion"]]
                    ),
                    secondary_y=True
                )

                fig.update_layout(
                    title_text="📈 Análisis de Pareto - Concentración de Ventas",
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
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown(generar_insight_pareto(productos_pareto), unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ Error en análisis de productos: {str(e)}")
            st.info("💡 Intenta con un rango de fechas diferente o verifica los datos del proveedor.")
    def show_temporal_analysis(self, df):
        """Análisis temporal"""
        st.subheader("📅 Análisis de Evolución Temporal")
        
        # Análisis mensual
        mensual = df.groupby('mes_año').agg({
            'precio_total': 'sum',
            'utilidad': 'sum',
            'cantidad_total': 'sum',
            'margen_porcentual': 'mean'
        }).round(2)
        
        mensual['tickets'] = df.groupby('mes_año').size()
        mensual = mensual.reset_index()
        
        # Gráficas temporales
        col1, col2 = st.columns(2)

        with col1:
            mensual["ventas_fmt"] = mensual["precio_total"].apply(lambda x: f"{x/1e6:.1f} M")

            fig = px.line(
                mensual,
                x='mes_año',
                y='precio_total',
                text='ventas_fmt',  # 👈 PASAR TEXT AQUÍ
                title="📈 Evolución Mensual de Ventas",
                markers=True
            )

            fig.update_traces(
                line_color='#2a5298',
                line_width=1,
                marker_size=5,
                textposition="top center"
            )
            fig.update_layout(
                title_font=dict(size=18, color='#454448', family='Arial Black'),
                title_x=0.15,
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(t=70, b=40, l=30, r=20),
            )
            fig.update_yaxes(showticklabels=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            mensual["margen_fmt"] = mensual["margen_porcentual"].map("{:.1f}%".format)

            fig = px.line(
                mensual,
                x='mes_año',
                y='margen_porcentual',
                text='margen_fmt',  # 👈 PASAR TEXT AQUÍ
                title="📊 Evolución del Margen Promedio",
                markers=True
            )

            fig.update_traces(
                line_color='#28a745',
                line_width=1,
                marker_size=5,
                textposition="top center"
            )
            fig.update_layout(
                title_font=dict(size=18, color='#454448', family='Arial Black'),
                title_x=0.15,
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(t=70, b=40, l=30, r=20),
            )
            fig.update_yaxes(showticklabels=False)
            st.plotly_chart(fig, use_container_width=True)
              
        # Análisis por día de la semana
        if 'dia_semana' in df.columns:
            st.markdown("### 📅 Análisis por Día de la Semana")
            
            # Mapear días en español
            dia_mapping = {
                'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            
            df['dia_semana_es'] = df['dia_semana'].map(dia_mapping)
            
            semanal = df.groupby('dia_semana_es').agg({
                'precio_total': 'sum',
                'utilidad': 'sum',
                'margen_porcentual': 'mean'
            }).round(2)
            
            # Ordenar días correctamente
            orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            semanal = semanal.reindex([dia for dia in orden_dias if dia in semanal.index])
            semanal = semanal.reset_index()
            
            col1, col2 = st.columns(2)
            with col1:
                # Formato para mostrar valores
                semanal["ventas_fmt"] = semanal["precio_total"].apply(lambda x: f"${x/1e6:.1f}M")

                fig = px.bar(
                    semanal,
                    x='dia_semana_es',
                    y='precio_total',
                    text='ventas_fmt',  # Mostrar valores arriba
                    title="📊 Ventas por Día de la Semana",
                    color='precio_total',
                    color_continuous_scale='Blues'
                )

                fig.update_traces(
                    textposition='outside',
                    hovertemplate="<b>%{x}</b><br>Ventas: %{text}<extra></extra>"
                )

                fig.update_layout(
                    title_font=dict(size=18, color='#454448', family='Arial Black'),
                    title_x=0.08,
                    xaxis_title=None,
                    yaxis_title=None,
                    margin=dict(t=70, b=40, l=30, r=20),
                    coloraxis_showscale=False  # 👈 Oculta la leyenda de color
                )

                fig.update_yaxes(showticklabels=False)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                semanal["margen_fmt"] = semanal["margen_porcentual"].map("{:.1f}%".format)

                fig = px.bar(
                    semanal,
                    x='dia_semana_es',
                    y='margen_porcentual',
                    text='margen_fmt',
                    title="📈 Margen por Día de la Semana",
                    color='margen_porcentual',
                    color_continuous_scale='Greens'
                )

                fig.update_traces(
                    textposition='outside',
                    hovertemplate="<b>%{x}</b><br>Margen: %{text}<extra></extra>"
                )

                fig.update_layout(
                    title_font=dict(size=18, color='#454448', family='Arial Black'),
                    title_x=0.08,
                    xaxis_title=None,
                    yaxis_title=None,
                    margin=dict(t=70, b=40, l=30, r=20),
                    coloraxis_showscale=False
                )

                fig.update_yaxes(
                    tickformat='.1f',
                    ticksuffix='%',
                    showticklabels=False
                )

                st.plotly_chart(fig, use_container_width=True)

        # Renombrar y formatear
        mensual_display = mensual.copy()
        mensual_display.rename(columns={
            "mes_año": "Mes",
            "precio_total": "Ventas",
            "utilidad": "Utilidad",
            "cantidad_total": "Cantidad",
            "margen_porcentual": "Margen %"
        }, inplace=True)

        mensual_display = mensual_display[["Mes", "Ventas", "Utilidad", "Cantidad", "Margen %"]]

        # Formato
        mensual_display["Ventas"] = mensual_display["Ventas"].apply(lambda x: f"${x:,.0f}")
        mensual_display["Utilidad"] = mensual_display["Utilidad"].apply(lambda x: f"${x:,.0f}")
        mensual_display["Cantidad"] = mensual_display["Cantidad"].apply(lambda x: f"{x:,.0f}")
        mensual_display["Margen %"] = mensual_display["Margen %"].map("{:.1f}%".format)

        # Convertir a HTML con estilos personalizados
        html = mensual_display.to_html(index=False, escape=False)

        # === TÍTULO Y BOTÓN EN MISMA FILA ===
        col1, col2 = st.columns([6, 1])
        with col1:
            st.markdown("### 📋 Resumen Mensual")
        with col2:
            # Convertir a CSV en memoria
            csv_buffer = io.StringIO()
            mensual_display.to_csv(csv_buffer, index=False)
            st.download_button(
                label="⬇️ Descargar CSV",
                data=csv_buffer.getvalue(),
                file_name="resumen_mensual.csv",
                mime="text/csv"
            )
        st.markdown("""
        <style>
            table {
                width: 100%;
                border-collapse: collapse;
                font-family: Arial, sans-serif;
                font-size: 15px;
            }
            th {
                text-align: center;
                background-color: #f5f5f5;
                padding: 8px;
            }
            td {
                padding: 8px;
                border-bottom: 1px solid #ddd;
            }
            td:nth-child(1) {
                text-align: center;
            }
            td:nth-child(n+2) {
                text-align: right;
            }
        </style>
        """, unsafe_allow_html=True)

        st.markdown(html, unsafe_allow_html=True)
    def show_advanced_analysis(self, df, metrics):
        """Análisis avanzado"""

        # Análisis por familia
        if 'familia' in df.columns and df['familia'].notna().any():
            # st.markdown("### 🌿 Análisis por Familia de Productos")

            familia_stats = df.groupby('familia').agg({
                'precio_total': 'sum',
                'utilidad': 'sum',
                'margen_porcentual': 'mean',
                'cantidad_total': 'sum'
            }).round(2)

            familia_stats['participacion'] = (familia_stats['precio_total'] / familia_stats['precio_total'].sum() * 100).round(1)

            metricas_opciones = {
                "Ventas": "precio_total",
                "Utilidad": "utilidad",
                "Margen %": "margen_porcentual",
                "Cantidad": "cantidad_total",
                "Participación %": "participacion"
            }

            col1, col2 = st.columns([3, 2])

            with col1:
                st.markdown("### 🌿 Análisis por Familia de Productos")

            with col2:
                metrica_seleccionada = st.selectbox(
                    "Selecciona una métrica:",
                    ["Ventas", "Utilidad", "Margen %", "Cantidad", "Participación %"],
                    index=0)

            columna = metricas_opciones[metrica_seleccionada]
            familia_stats = familia_stats.sort_values(columna, ascending=False)
            formato = "${:,.0f}" if columna in ['precio_total', 'utilidad'] else "{:,.1f}%" if 'margen' in columna or 'participa' in columna else "{:,.0f}"
            texto_etiqueta = familia_stats[columna].map(formato.format)

            col1, col2 = st.columns(2)

            with col1:
                # Crear columna con % participación para uso en etiquetas
                familia_stats['participacion'] = (familia_stats[columna] / familia_stats[columna].sum()) * 100

                # Pull dinámico: cuanto menor la participación, mayor el pull
                pulls = familia_stats['participacion'].apply(lambda x: 0.12 if x < 5 else 0.04 if x < 15 else 0.01).tolist()

                # Texto interior: % + valor abreviado
                text_mode = 'percent+label' if 'porcentual' in columna or 'participa' in columna else 'label+value'

                fig = px.pie(
                    familia_stats,
                    values=columna,
                    names=familia_stats.index,
                    title=f"🥧 Distribución de {metrica_seleccionada} por Familia",
                    hole=0.35
                )

                fig.update_traces(
                    textinfo=text_mode,
                    textposition='inside',
                    pull=pulls,
                    marker=dict(line=dict(width=0)),
                    hovertemplate="<b>%{label}</b><br>" +
                                f"{metrica_seleccionada}: " +
                                "%{value:,.0f} <br>Participación: %{percent}<extra></extra>"
                )

                fig.update_layout(
                    title_font=dict(size=18, color='#454448', family='Arial Black'),
                    title_x=0.08,
                    legend=dict(
                        bgcolor='rgba(0,0,0,0)',
                        bordercolor='rgba(0,0,0,0)',
                        font=dict(size=11)
                    ),
                    showlegend=True,
                    margin=dict(t=60, b=30, l=10, r=10)
                )

                st.plotly_chart(fig, use_container_width=True)

            with col2:
                df_bar = familia_stats.reset_index()

                fig = px.bar(
                    df_bar,
                    x='familia',
                    y=columna,
                    color=columna,
                    text=texto_etiqueta,
                    title=f"📊 {metrica_seleccionada} por Familia",
                    color_continuous_scale='Viridis'
                    )

                fig.update_traces(
                    textposition='outside',
                    hovertemplate="<b>%{x}</b><br>" + metrica_seleccionada + ": %{text}<extra></extra>"
                )
                fig.update_layout(
                    title_font=dict(size=18, color='#454448', family='Arial Black'),
                    title_x=0.08,
                    xaxis_title=None,
                    yaxis_title=None,
                    # height=370,
                    coloraxis_showscale=False,
                    margin=dict(t=70, b=40, l=30, r=20)
                )
                fig.update_yaxes(
                    showticklabels=False
                )
                st.plotly_chart(fig, use_container_width=True)

        # Análisis por subfamilia
        # === Análisis por Subfamilia ===
        if 'subfamilia' in df.columns and df['subfamilia'].notna().any():
            
            subfamilia_stats = df.groupby('subfamilia').agg({
                'precio_total': 'sum',
                'utilidad': 'sum',
                'margen_porcentual': 'mean',
                'cantidad_total': 'sum'
            }).round(2)

            subfamilia_stats['participacion'] = (subfamilia_stats['precio_total'] / subfamilia_stats['precio_total'].sum() * 100).round(1)

            metricas_opciones = {
                "Ventas": "precio_total",
                "Utilidad": "utilidad",
                "Margen %": "margen_porcentual",
                "Cantidad": "cantidad_total",
                "Participación %": "participacion"
            }

            col1, col2 = st.columns([3, 2])

            with col1:
                st.markdown("### 🍃 Análisis por Subfamilia de Productos")

            with col2:
                metrica_subfam = st.selectbox(
                    "Selecciona una métrica:",
                    list(metricas_opciones.keys()),
                    index=0,
                    key="metrica_subfamilia"
                )

            columna = metricas_opciones[metrica_subfam]
            subfamilia_stats = subfamilia_stats.sort_values(columna, ascending=False)
            formato = "${:,.0f}" if columna in ['precio_total', 'utilidad'] else "{:,.1f}%" if 'margen' in columna or 'participa' in columna else "{:,.0f}"
            texto_etiqueta = subfamilia_stats[columna].map(formato.format)

            col1, col2 = st.columns(2)

            with col1:
                subfamilia_stats['participacion'] = (subfamilia_stats[columna] / subfamilia_stats[columna].sum()) * 100
                pulls = subfamilia_stats['participacion'].apply(lambda x: 0.12 if x < 5 else 0.04 if x < 15 else 0.01).tolist()
                text_mode = 'percent+label' if 'porcentual' in columna or 'participa' in columna else 'label+value'

                fig = px.pie(
                    subfamilia_stats,
                    values=columna,
                    names=subfamilia_stats.index,
                    title=f"🥧 Distribución de {metrica_subfam} por Subfamilia",
                    hole=0.35
                )

                fig.update_traces(
                    textinfo=text_mode,
                    textposition='inside',
                    pull=pulls,
                    marker=dict(line=dict(width=0)),
                    hovertemplate="<b>%{label}</b><br>" +
                                f"{metrica_subfam}: " +
                                "%{value:,.0f} <br>Participación: %{percent}<extra></extra>"
                )

                fig.update_layout(
                    title_font=dict(size=18, color='#454448', family='Arial Black'),
                    title_x=0.08,
                    legend=dict(
                        bgcolor='rgba(0,0,0,0)',
                        bordercolor='rgba(0,0,0,0)',
                        font=dict(size=11)
                    ),
                    showlegend=True,
                    margin=dict(t=60, b=30, l=10, r=10)
                )

                st.plotly_chart(fig, use_container_width=True)

            with col2:
                df_bar = subfamilia_stats.reset_index()

                fig = px.bar(
                    df_bar,
                    x='subfamilia',
                    y=columna,
                    color=columna,
                    text=texto_etiqueta,
                    title=f"📊 {metrica_subfam} por Subfamilia",
                    color_continuous_scale='Viridis'
                )

                fig.update_traces(
                    textposition='outside',
                    hovertemplate="<b>%{x}</b><br>" + metrica_subfam + ": %{text}<extra></extra>"
                )

                fig.update_layout(
                    title_font=dict(size=18, color='#454448', family='Arial Black'),
                    title_x=0.08,
                    xaxis_title=None,
                    yaxis_title=None,
                    coloraxis_showscale=False,
                    margin=dict(t=70, b=40, l=30, r=20)
                )

                fig.update_yaxes(
                    showticklabels=False
                )

                st.plotly_chart(fig, use_container_width=True)
        
        # Análisis por sucursal
        # === Análisis por Sucursal con métrica seleccionable ===
        if 'sucursal' in df.columns and df['sucursal'].notna().any():
            col1, col2 = st.columns([3, 2])

            with col1:
                st.markdown("### 🏪 Análisis por Sucursal")

            with col2:
                metrica_seleccionada = st.selectbox(
                    "Selecciona una métrica:",
                    ["Ventas", "Utilidad", "Margen %", "Cantidad", "Participación %"],
                    index=0,
                    key="metrica_sucursal"
                )

            # === Preparación de datos ===
            sucursal_stats = df.groupby('sucursal').agg({
                'precio_total': 'sum',
                'utilidad': 'sum',
                'margen_porcentual': 'mean',
                'cantidad_total': 'sum'
            }).round(2)

            sucursal_stats['tickets'] = df.groupby('sucursal').size()
            sucursal_stats['participacion'] = (sucursal_stats['precio_total'] / sucursal_stats['precio_total'].sum()) * 100

            metricas_opciones = {
                "Ventas": "precio_total",
                "Utilidad": "utilidad",
                "Margen %": "margen_porcentual",
                "Cantidad": "cantidad_total",
                "Participación %": "participacion"
            }

            columna = metricas_opciones[metrica_seleccionada]
            sucursal_stats = sucursal_stats.sort_values(columna, ascending=False)

            formato = "${:,.0f}" if columna in ['precio_total', 'utilidad'] else "{:,.1f}%" if 'margen' in columna or 'participa' in columna else "{:,.0f}"
            texto_etiqueta = sucursal_stats[columna].map(formato.format)

            col1, col2 = st.columns(2)

            with col1:
                pulls = sucursal_stats['participacion'].apply(lambda x: 0.12 if x < 5 else 0.04 if x < 15 else 0.01).tolist()
                text_mode = 'percent+label' if 'porcentual' in columna or 'participa' in columna else 'label+value'

                fig = px.pie(
                    sucursal_stats,
                    values=columna,
                    names=sucursal_stats.index,
                    title=f"🏪 Distribución de {metrica_seleccionada} por Sucursal",
                    hole=0.35
                )
                fig.update_traces(
                    textinfo=text_mode,
                    textposition='inside',
                    pull=pulls,
                    marker=dict(line=dict(width=0)),
                    hovertemplate="<b>%{label}</b><br>" +
                                f"{metrica_seleccionada}: " +
                                "%{value:,.0f} <br>Participación: %{percent}<extra></extra>"
                )
                fig.update_layout(
                    title_font=dict(size=18, color='#454448', family='Arial Black'),
                    title_x=0.08,
                    legend=dict(
                        bgcolor='rgba(0,0,0,0)',
                        bordercolor='rgba(0,0,0,0)',
                        font=dict(size=11)
                    ),
                    showlegend=True,
                    margin=dict(t=60, b=30, l=10, r=10)
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                df_bar = sucursal_stats.reset_index()

                fig = px.bar(
                    df_bar,
                    x='sucursal',
                    y=columna,
                    color=columna,
                    text=texto_etiqueta,
                    title=f"📈 {metrica_seleccionada} por Sucursal",
                    color_continuous_scale='Viridis'
                )
                fig.update_traces(
                    textposition='outside',
                    hovertemplate="<b>%{x}</b><br>" + metrica_seleccionada + ": %{text}<extra></extra>"
                )
                fig.update_layout(
                    title_font=dict(size=18, color='#454448', family='Arial Black'),
                    title_x=0.08,
                    xaxis_title=None,
                    yaxis_title=None,
                    coloraxis_showscale=False,
                    margin=dict(t=70, b=40, l=30, r=20)
                )
                fig.update_yaxes(
                    showticklabels=False
                )
                st.plotly_chart(fig, use_container_width=True)

        col1, col2,col3 = st.columns(3)
            
        with col1:
            df_margenes_suc = df.groupby('sucursal')['margen_porcentual'].mean()
            st.markdown(generar_insight_margen(df_margenes_suc, "Sucursal"), unsafe_allow_html=True)

        with col2:
            df_margenes_flia = df.groupby('familia')['margen_porcentual'].mean()
            st.markdown(generar_insight_margen(df_margenes_flia, "Familia"), unsafe_allow_html=True)

        with col3:
            df_margenes_subflia = df.groupby('subfamilia')['margen_porcentual'].mean()
            st.markdown(generar_insight_margen(df_margenes_subflia, "Subfamilia"), unsafe_allow_html=True)

        # # Matriz de análisis ABC
        # === Análisis ABC Mejorado ===
        st.markdown("### 📊 Análisis ABC de Productos")

        productos_abc = df.groupby(['idarticulo', 'descripcion']).agg({
            'precio_total': 'sum',
            'utilidad': 'sum'
        }).sort_values('precio_total', ascending=False)

        productos_abc['participacion_acum'] = (
            productos_abc['precio_total'].cumsum() /
            productos_abc['precio_total'].sum() * 100
        )

        # Clasificación ABC
        def categorizar_abc(part):
            if part <= 80:
                return 'A (Alto valor)'
            elif part <= 95:
                return 'B (Valor medio)'
            else:
                return 'C (Bajo valor)'

        productos_abc['categoria_abc'] = productos_abc['participacion_acum'].apply(categorizar_abc)

        # Datos agregados
        abc_counts = productos_abc['categoria_abc'].value_counts().sort_index()
        abc_ventas = productos_abc.groupby('categoria_abc')['precio_total'].sum().sort_index()
        abc_ventas_fmt = abc_ventas.map("${:,.0f}".format)

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                x=abc_counts.index,
                y=abc_counts.values,
                color=abc_counts.values,
                text=abc_counts.values,
                title="📦 Cantidad de Productos por Categoría ABC",
                labels={'x': 'Categoría ABC', 'y': 'Cantidad'},
                color_continuous_scale='Blues'
            )
            fig.update_traces(
                textposition='outside',
                hovertemplate="<b>%{x}</b><br>Cantidad: %{y}<extra></extra>"
            )
            fig.update_layout(
                title_font=dict(size=18, color='#2c2c2c', family='Arial Black'),
                title_x=0.08,
                xaxis_title=None,
                yaxis_title=None,
                coloraxis_showscale=False,
                height=400,
                margin=dict(t=60, b=40, l=30, r=20)
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.pie(
                values=abc_ventas.values,
                names=abc_ventas.index,
                title="💰 Participación de Ventas por Categoría ABC",
                hole=0.35
            )
            fig.update_traces(
                textinfo='percent+label',
                textposition='inside',
                marker=dict(line=dict(width=0)),
                hovertemplate="<b>%{label}</b><br>Ventas: %{value:$,.0f}<br>Participación: %{percent}<extra></extra>"
            )
            fig.update_layout(
                title_font=dict(size=18, color='#2c2c2c', family='Arial Black'),
                title_x=0.08,
                legend=dict(
                    bgcolor='rgba(0,0,0,0)',
                    bordercolor='rgba(0,0,0,0)',
                    font=dict(size=11)
                ),
                height=400,
                margin=dict(t=60, b=30, l=10, r=10)
            )
            st.plotly_chart(fig, use_container_width=True)

        #     with col1:
        # === CSS Profesional ===
        st.markdown("""
        <style>
            .insight-box, .warning-box, .success-box {
                border-radius: 12px;
                padding: 1.2rem;
                margin: 1rem 0;
                font-size: 0.95rem;
                line-height: 1.6;
                background-color: #ffffff;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                border-left: 5px solid #2a5298;
            }

            .warning-box {
                border-left-color: #ffc107;
                background-color: #fff9e6;
            }

            .success-box {
                border-left-color: #28a745;
                background-color: #e9f7ef;
            }

            .insight-box {
                border-left-color: #17a2b8;
                background-color: #eef9fc;
            }

            .insight-titulo {
                font-size: 1.15rem;
                color: #2a2a2a;
                margin-bottom: .5rem;
            }

            .highlight {
                background-color: #ffeaa7;
                padding: 2px 6px;
                border-radius: 6px;
            }
        </style>
        """, unsafe_allow_html=True)

        with col1:
            st.markdown(generar_insight_cantidad(abc_counts), unsafe_allow_html=True)

        with col2:
            st.markdown(generar_insight_ventas(abc_ventas), unsafe_allow_html=True)

        st.markdown(generar_insight_abc_completo(abc_counts, abc_ventas), unsafe_allow_html=True)

        # === Recomendaciones Estratégicas ===
        st.markdown("### 💡 Recomendaciones Estratégicas")

        recomendaciones_criticas = []
        recomendaciones_medias = []
        recomendaciones_bajas = []

        # Productos A
        productos_a = productos_abc[productos_abc['categoria_abc'] == 'A (Alto valor)']
        if not productos_a.empty:
            ventas_a = abc_ventas.get('A (Alto valor)', 0)
            porcentaje_a = ventas_a / abc_ventas.sum() * 100
            recomendaciones_criticas.append(
                f"🔺 **Productos A:** {len(productos_a)} productos generan el {porcentaje_a:.1f}% de las ventas. Priorizá disponibilidad y promoción."
            )

        # Margen bajo
        if metrics['margen_promedio'] < 20:
            recomendaciones_criticas.append(
                f"🔴 **Margen bajo ({metrics['margen_promedio']:.1f}%):** Revisar precios y negociar con proveedores."
            )
        elif metrics['margen_promedio'] >= 30:
            recomendaciones_bajas.append(
                f"✅ **Margen saludable:** Excelente rentabilidad promedio ({metrics['margen_promedio']:.1f}%). ¡Seguir así!"
            )

        # Diversificación
        if metrics['productos_unicos'] < 10:
            recomendaciones_medias.append(
                f"📈 **Ampliar catálogo:** Solo {metrics['productos_unicos']} productos únicos. Evaluar incorporar nuevas líneas."
            )
        else:
            recomendaciones_bajas.append(
                f"🟢 **Catálogo variado:** {metrics['productos_unicos']} productos activos. Diversificación saludable."
            )


        # === Mostrar recomendaciones ordenadas ===
        if recomendaciones_criticas:
            st.markdown("#### 🔺 Alta Prioridad")
            for rec in recomendaciones_criticas:
                st.markdown(f'<div class="insight-box red">{rec}</div>', unsafe_allow_html=True)

        if recomendaciones_medias:
            st.markdown("#### ⚠️ Prioridad Media")
            for rec in recomendaciones_medias:
                st.markdown(f'<div class="insight-box">{rec}</div>', unsafe_allow_html=True)

        if recomendaciones_bajas:
            st.markdown("#### ✅ Aspectos Positivos")
            for rec in recomendaciones_bajas:
                st.markdown(f'<div class="insight-box green">{rec}</div>', unsafe_allow_html=True)

        # === Mostrar recomendaciones ordenadas ===
        # === Crear tabla ABC formateada ===
        tabla_abc = productos_abc.reset_index()[[
            'idarticulo', 'descripcion', 'precio_total', 'utilidad', 'participacion_acum', 'categoria_abc'
        ]]
        tabla_abc.columns = ['ID Artículo', 'Descripción', 'Ventas Totales', 'Utilidad', 'Participación Acum. (%)', 'Categoría ABC']

        # Redondear y aplicar formato a los valores
        tabla_abc['Ventas Totales'] = tabla_abc['Ventas Totales'].round(0).astype(int)
        tabla_abc['Utilidad'] = tabla_abc['Utilidad'].round(0).astype(int)
        tabla_abc['Participación Acum. (%)'] = tabla_abc['Participación Acum. (%)'].round(1)

        # === Función para exportar Excel con estilos ===
        def generar_excel_descarga(df):
            wb = Workbook()
            ws = wb.active
            ws.title = "Clasificación ABC"

            # Escribir los datos
            for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
                for c_idx, value in enumerate(row, 1):
                    ws.cell(row=r_idx, column=c_idx, value=value)

            # Estilos
            header_fill = PatternFill("solid", fgColor="BDD7EE")
            currency_fmt = '"$"#,##0'
            percent_fmt = '0.0"%"'
            border = Border(
                left=Side(style="thin", color="999999"),
                right=Side(style="thin", color="999999"),
                top=Side(style="thin", color="999999"),
                bottom=Side(style="thin", color="999999")
            )

            for col in ws.iter_cols(min_row=1, max_row=ws.max_row, max_col=ws.max_column):
                max_length = 0
                for cell in col:
                    cell.border = border
                    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                    if cell.row == 1:
                        cell.font = Font(bold=True)
                        cell.fill = header_fill
                    if isinstance(cell.value, (int, float)):
                        if cell.column_letter in ['C', 'D']:
                            cell.number_format = currency_fmt
                        elif cell.column_letter == 'E':
                            cell.number_format = percent_fmt
                    max_length = max(max_length, len(str(cell.value)))
                col_letter = col[0].column_letter
                ws.column_dimensions[col_letter].width = max_length + 2

            # Guardar en BytesIO
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            return output

        # === Mostrar tabla e incluir botón de descarga ===
        st.markdown("### 📋 Detalle de Clasificación ABC")
        st.dataframe(tabla_abc, use_container_width=True)

        archivo_excel = generar_excel_descarga(tabla_abc)

        st.download_button(
            label="📥 Descargar tabla ABC en Excel",
            data=archivo_excel,
            file_name="clasificacion_abc.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
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
        st.dataframe(df_resumen, use_container_width=True, hide_index=True)

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
                use_container_width=True,
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
                st.dataframe(df_processed, use_container_width=True)
            
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
            st.dataframe(df, use_container_width=True)
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
        st.dataframe(df_reponer[columnas], use_container_width=True)

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
        df_costos["Presupuesto ($)"] = df_costos["Presupuesto ($)"].astype(int)
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
            st.plotly_chart(fig1, use_container_width=True)

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
            st.plotly_chart(fig2, use_container_width=True)

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
            st.plotly_chart(fig, use_container_width=True)

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
            st.dataframe(df_riesgo[columnas].head(300), use_container_width=True, hide_index=True)

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
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Formatear columnas
            df_exceso['exceso_STK_format'] = df_exceso['exceso_STK'].astype(int).map(lambda x: f"{x:,}")
            df_exceso['costo_exceso_STK_format'] = df_exceso['costo_exceso_STK'].map(lambda x: f"${x:,.0f}")
            df_exceso['dias_cobertura_format'] = df_exceso['dias_cobertura'].map(lambda x: f"{x:.0f}")

            # Ordenar por mayor costo
            df_exceso = df_exceso.sort_values(by='costo_exceso_STK', ascending=False)

            columnas = ["idarticulo", "descripcion", "exceso_STK_format", "costo_exceso_STK_format", "dias_cobertura_format"]
            st.markdown(f"📦 {len(df_exceso)} artículos con exceso de stock detectado")
            st.dataframe(df_exceso[columnas].head(300), use_container_width=True, hide_index=True)

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

                    st.plotly_chart(fig, use_container_width=True)
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
                                    st.dataframe(df_vista, use_container_width=True, hide_index=True)

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

            st.plotly_chart(fig, use_container_width=True)

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
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            df_estacional['cantidad_optima'] = df_estacional['cantidad_optima'].astype(int).map(lambda x: f"{x:,}")
            df_estacional = df_estacional.sort_values(by="ranking_mes", ascending=False)
            columnas = ["idarticulo", "descripcion", "mes_pico", "mes_bajo", "ranking_mes", "Etiqueta Estacional", "cantidad_optima"]

            # st.caption(f"📋 {len(df_estacional)} artículos con análisis estacional")
            st.dataframe(df_estacional[columnas], use_container_width=True, hide_index=True)

        # === Paso 6: Descargar CSV con columnas visibles
        csv = df_estacional[columnas].to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "analisis_estacionalidad.csv", "text/csv")

    def analisis_oportunidad_perdida(self,df):
        st.subheader("📉 Valor Perdido por Falta de Stock")
        df_perdido = df[df['costo_exceso_STK'] > 0].copy()
        # st.dataframe(df_perdido[["idarticulo", "descripcion", "valor_perdido_TOTAL", "unidades_perdidas_TOTAL", "cnt_reabastecer"]], use_container_width=True)

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
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            df_final = df_reducido[df_reducido['decision_precio'].isin(['🔻 rebaja', '🔺 alza'])].copy()

            # ✅ Formatear columnas para mostrar
            df_final['precio_actual'] = df_final['precio_actual'].map(lambda x: f"${x:,.2f}")
            df_final['costo_unit'] = df_final['costo_unit'].map(lambda x: f"${x:,.2f}")
            df_final['precio_optimo_ventas'] = df_final['precio_optimo_ventas'].map(lambda x: f"${x:,.2f}")
            df_final.rename(columns={"pred_ventas_actual": "venta para hoy"}, inplace=True)
            df_final["venta para hoy"] = df_final["venta para hoy"].astype(int)

            st.caption(f"🎯 {len(df_final)} artículos con propuesta de cambio de precio")
            st.dataframe(df_final, use_container_width=True, hide_index=True)


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
