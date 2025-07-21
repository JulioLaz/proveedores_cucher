import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.cloud import bigquery
import warnings
import io
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suprimir advertencias
warnings.filterwarnings('ignore')

# === CONFIGURACION DE PAGINA ===
st.set_page_config(
    page_title="📊 Advanced Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://docs.streamlit.io',
        'Report a Bug': 'https://github.com/streamlit/streamlit/issues',
        'About': 'Advanced Analytics Dashboard powered by Streamlit'
    }
)

# === CSS MEJORADO ===
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72, #2a5298);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .metric-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border-left: 5px solid #2a5298;
        transition: transform 0.2s;
    }
    .metric-container:hover {
        transform: translateY(-5px);
    }
    .insight-box {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 5px solid #28a745;
        transition: all 0.3s ease;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 5px solid #ffc107;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 5px solid #28a745;
    }
    .sidebar .sidebar-content {
        background: #f8f9fa;
        border-right: 1px solid #dee2e6;
    }
    .stButton>button {
        background-color: #2a5298;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1e3c72;
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# === DETECTAR ENTORNO ===
IS_CLOUD = "gcp_service_account" in st.secrets if hasattr(st, 'secrets') else False

class ProveedorDashboard:
    def __init__(self):
        self.df_proveedores = None
        self.df_tickets = None
        self.setup_credentials()
        
        # Estado inicial
        if 'analysis_data' not in st.session_state:
            st.session_state.analysis_data = None
        if 'selected_proveedor' not in st.session_state:
            st.session_state.selected_proveedor = None
        if 'forecast_data' not in st.session_state:
            st.session_state.forecast_data = None
    
    def setup_credentials(self):
        """Configurar credenciales según el entorno"""
        try:
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
        except Exception as e:
            logger.error(f"Error al configurar credenciales: {str(e)}")
            st.error("❌ Error al configurar credenciales. Por favor verifica la configuración.")
    
    @st.cache_data(ttl=3600, show_spinner=False)
    def load_proveedores(_self):
        """Cargar datos de proveedores desde Google Sheet público"""
        try:
            url = f"https://docs.google.com/spreadsheets/d/{_self.sheet_id}/gviz/tq?tqx=out:csv&sheet={_self.sheet_name}"
            df = pd.read_csv(url)
            df['proveedor'] = df['proveedor'].astype(str).str.strip().str.upper()
            return df
        except Exception as e:
            logger.error(f"Error al cargar proveedores: {str(e)}")
            st.error("❌ Error al cargar datos de proveedores")
            return pd.DataFrame()
    
    def query_bigquery_data(self, proveedor, fecha_inicio, fecha_fin):
        """Consultar datos de BigQuery"""
        try:
            ids = self.df_proveedores[
                self.df_proveedores['proveedor'] == proveedor
            ]['idarticulo'].dropna().astype(int).astype(str).unique()
            
            if len(ids) == 0:
                return None
            
            id_str = ','.join(ids)
            
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
            
            # Procesamiento de datos
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
            df['hora'] = df['fecha_comprobante'].dt.hour
            
            return df
            
        except Exception as e:
            logger.error(f"Error consultando BigQuery: {str(e)}")
            st.error(f"❌ Error consultando datos: {str(e)}")
            return None
    
    def generate_simple_forecast(self, df):
        """Generar pronóstico simple usando media móvil"""
        try:
            ventas_diarias = df.groupby('fecha')['precio_total'].sum().reset_index()
            ventas_diarias = ventas_diarias.sort_values('fecha')
            
            if len(ventas_diarias) < 7:
                return None
            
            # Calcular media móvil de 7 días
            ventas_diarias['media_movil_7'] = ventas_diarias['precio_total'].rolling(window=7).mean()
            
            # Crear pronóstico simple para próximos 30 días
            ultimo_promedio = ventas_diarias['media_movil_7'].iloc[-1]
            
            forecast_dates = pd.date_range(
                start=ventas_diarias['fecha'].max() + timedelta(days=1),
                periods=30,
                freq='D'
            )
            
            # Agregar variabilidad basada en desviación estándar
            std_ventas = ventas_diarias['precio_total'].std()
            forecast_values = []
            
            for i in range(30):
                # Agregar algo de tendencia y estacionalidad simple
                trend_factor = 1 + (i * 0.001)  # Ligera tendencia positiva
                seasonal_factor = 1 + 0.1 * np.sin(2 * np.pi * i / 7)  # Estacionalidad semanal
                
                forecast_value = ultimo_promedio * trend_factor * seasonal_factor
                forecast_values.append(forecast_value)
            
            forecast_df = pd.DataFrame({
                'fecha': forecast_dates,
                'pronostico': forecast_values,
                'limite_superior': [v + std_ventas for v in forecast_values],
                'limite_inferior': [max(0, v - std_ventas) for v in forecast_values]
            })
            
            return forecast_df, ventas_diarias
            
        except Exception as e:
            logger.error(f"Error generando pronóstico: {str(e)}")
            return None, None
    
    def calculate_metrics(self, df):
        """Calcular métricas principales"""
        try:
            metrics = {
                'total_ventas': df['precio_total'].sum(),
                'total_costos': df['costo_total'].sum(),
                'total_utilidad': df['utilidad'].sum(),
                'margen_promedio': df['margen_porcentual'].mean(),
                'total_cantidad': df['cantidad_total'].sum(),
                'num_tickets': len(df),
                'ticket_promedio': df['precio_total'].sum() / len(df) if len(df) > 0 else 0,
                'productos_unicos': df['idarticulo'].nunique(),
                'dias_con_ventas': df['fecha'].nunique(),
                'sucursales': df['sucursal'].nunique() if 'sucursal' in df.columns else 0,
                'familias': df['familia'].nunique() if 'familia' in df.columns else 0,
                'horas_activas': df['hora'].nunique() if 'hora' in df.columns else 0
            }
            
            # Calcular métricas avanzadas
            metrics['concentracion_ventas'] = (df.groupby('idarticulo')['precio_total'].sum().nlargest(5).sum() / 
                                             metrics['total_ventas'] * 100) if metrics['total_ventas'] > 0 else 0
            
            return metrics
        except Exception as e:
            logger.error(f"Error calculando métricas: {str(e)}")
            return {}
    
    def generate_insights(self, df, metrics):
        """Generar insights automáticos"""
        insights = []
        
        try:
            # Análisis de rentabilidad
            if metrics['margen_promedio'] > 30:
                insights.append(("success", f"🎯 Excelente rentabilidad: {metrics['margen_promedio']:.1f}% de margen promedio"))
            elif metrics['margen_promedio'] > 20:
                insights.append(("info", f"📈 Buena rentabilidad: {metrics['margen_promedio']:.1f}% de margen promedio"))
            else:
                insights.append(("warning", f"⚠️ Margen bajo: {metrics['margen_promedio']:.1f}% - Revisar estrategia de precios"))
            
            # Concentración de ventas
            if metrics['concentracion_ventas'] > 70:
                insights.append(("warning", f"⚠️ Alta concentración: {metrics['concentracion_ventas']:.1f}% de ventas en top 5 productos"))
            
            # Análisis de productos
            top_producto = df.groupby('descripcion')['precio_total'].sum().nlargest(1)
            if len(top_producto) > 0:
                producto_name = top_producto.index[0]
                producto_ventas = top_producto.iloc[0]
                participacion = (producto_ventas / metrics['total_ventas']) * 100
                insights.append(("info", f"🏆 Producto estrella: {producto_name[:50]}... ({participacion:.1f}% de ventas)"))
            
            # Análisis temporal
            if len(df) > 7:
                ventas_por_dia = df.groupby('fecha')['precio_total'].sum()
                tendencia_dias = 7
                if len(ventas_por_dia) >= tendencia_dias:
                    ultimos_dias = ventas_por_dia.tail(tendencia_dias).mean()
                    primeros_dias = ventas_por_dia.head(tendencia_dias).mean()
                    if ultimos_dias > primeros_dias * 1.1:
                        insights.append(("success", f"📈 Tendencia positiva: +{((ultimos_dias/primeros_dias-1)*100):.1f}% en últimos días"))
                    elif ultimos_dias < primeros_dias * 0.9:
                        insights.append(("warning", f"📉 Tendencia bajista: {((ultimos_dias/primeros_dias-1)*100):.1f}% en últimos días"))
            
            # Análisis horario
            if 'hora' in df.columns:
                hora_pico = df.groupby('hora')['precio_total'].sum().idxmax()
                insights.append(("info", f"⏰ Hora pico de ventas: {hora_pico}:00 hrs"))
            
            return insights
        except Exception as e:
            logger.error(f"Error generando insights: {str(e)}")
            return []
    
    def generate_simple_pdf_report(self, df, proveedor, metrics):
        """Generar reporte simple sin ReportLab"""
        try:
            # Crear un reporte en texto plano
            report_text = f"""
REPORTE DE ANÁLISIS - {proveedor}
=======================================

Período: {df['fecha'].min()} a {df['fecha'].max()}
Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

RESUMEN EJECUTIVO:
- Ventas Totales: ${metrics['total_ventas']:,.2f}
- Utilidad Total: ${metrics['total_utilidad']:,.2f}
- Margen Promedio: {metrics['margen_promedio']:.1f}%
- Total Transacciones: {metrics['num_tickets']:,}
- Ticket Promedio: ${metrics['ticket_promedio']:,.2f}
- Productos Únicos: {metrics['productos_unicos']:,}
- Días con Ventas: {metrics['dias_con_ventas']:,}

TOP 10 PRODUCTOS:
"""
            
            # Agregar top productos
            top_productos = df.groupby('descripcion')['precio_total'].sum().nlargest(10)
            for i, (producto, ventas) in enumerate(top_productos.items(), 1):
                report_text += f"{i}. {producto[:50]}... - ${ventas:,.2f}\n"
            
            return report_text.encode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generando reporte: {str(e)}")
            return "Error generando reporte".encode('utf-8')
    
    def show_sidebar_filters(self):
        """Mostrar filtros en sidebar"""
        st.sidebar.markdown("## 🎛️ Panel de Control")
        
        if self.df_proveedores is None:
            with st.spinner("Cargando proveedores..."):
                self.df_proveedores = self.load_proveedores()
        
        st.sidebar.markdown("### 🏪 Selección de Proveedor")
        proveedores = sorted(self.df_proveedores['proveedor'].dropna().unique())
        
        proveedor = st.sidebar.selectbox(
            "Proveedor:",
            options=proveedores,
            index=None,
            placeholder="Seleccionar proveedor...",
            key="proveedor_select"
        )
        
        st.sidebar.markdown("### 📅 Período de Análisis")
        
        rango_opciones = {
            "Últimos 7 días": 7,
            "Último mes": 30,
            "Últimos 3 meses": 90,
            "Últimos 6 meses": 180,
            "Último año": 365,
            "Personalizado": None
        }
        
        rango_seleccionado = st.sidebar.selectbox(
            "Rango de fechas:",
            options=list(rango_opciones.keys()),
            index=3
        )
        
        if rango_seleccionado == "Personalizado":
            col1, col2 = st.sidebar.columns(2)
            fecha_inicio = col1.date_input(
                "Desde:",
                value=datetime.now().date() - timedelta(days=180),
                key="fecha_inicio"
            )
            fecha_fin = col2.date_input(
                "Hasta:",
                value=datetime.now().date(),
                key="fecha_fin"
            )
        else:
            dias = rango_opciones[rango_seleccionado]
            fecha_fin = datetime.now().date()
            fecha_inicio = fecha_fin - timedelta(days=dias)
            st.sidebar.info(f"📅 **{rango_seleccionado}**\n\n{fecha_inicio} a {fecha_fin}")
        
        # Filtros adicionales
        st.sidebar.markdown("### ⚙️ Filtros Avanzados")
        min_margen = st.sidebar.slider("Margen Mínimo (%)", 0, 100, 0)
        min_ventas = st.sidebar.number_input("Ventas Mínimas ($)", 0, 1000000, 0)
        
        if st.sidebar.button("🔍 Analizar Datos", type="primary", use_container_width=True):
            if not proveedor:
                st.sidebar.error("❌ Selecciona un proveedor")
            else:
                with st.spinner("🔄 Procesando datos..."):
                    df_tickets = self.query_bigquery_data(proveedor, fecha_inicio, fecha_fin)
                    if df_tickets is not None:
                        # Aplicar filtros
                        df_tickets = df_tickets[
                            (df_tickets['margen_porcentual'] >= min_margen) &
                            (df_tickets['precio_total'] >= min_ventas)
                        ]
                        st.session_state.analysis_data = df_tickets
                        st.session_state.selected_proveedor = proveedor
                        st.session_state.forecast_data = self.generate_simple_forecast(df_tickets) if len(df_tickets) > 0 else (None, None)
                        st.rerun()
                    else:
                        st.sidebar.error("❌ No se encontraron datos para los parámetros seleccionados")
        
        if proveedor:
            st.sidebar.markdown("### 📊 Info del Proveedor")
            num_articulos = len(self.df_proveedores[self.df_proveedores['proveedor'] == proveedor])
            st.sidebar.metric("Artículos en catálogo", num_articulos)
        
        return proveedor, fecha_inicio, fecha_fin
    
    def show_main_dashboard(self):
        """Mostrar dashboard principal"""
        st.markdown("""
        <div class="main-header">
            <h1>📊 Dashboard de Análisis Estratégico</h1>
            <p>Sistema avanzado de inteligencia de negocios con pronósticos y análisis predictivo</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.analysis_data is None:
            st.info("👈 **Selecciona un proveedor y parámetros en el panel lateral**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("""
                ### 🎯 Características Principales
                - Análisis predictivo
                - Pronósticos de ventas
                - Visualizaciones interactivas
                - Reportes exportables
                - Insights automáticos
                """)
            
            with col2:
                st.markdown("""
                ### 📊 Análisis Incluidos
                - Rendimiento financiero
                - Análisis ABC
                - Tendencias estacionales
                - Análisis por sucursal
                - Optimización de inventario
                """)
            
            with col3:
                st.markdown("""
                ### 🔍 Capacidades Avanzadas
                - Forecasting estadístico
                - Análisis horario
                - Segmentación avanzada
                - Exportación múltiple
                - Alertas personalizadas
                """)
            return
        
        df = st.session_state.analysis_data
        proveedor = st.session_state.selected_proveedor
        metrics = self.calculate_metrics(df)
        
        tabs = st.tabs([
            "📈 Resumen Ejecutivo", 
            "🏆 Productos", 
            "📅 Temporal",
            "🎯 Avanzado",
            "📁 Reportes",
            "🔮 Pronósticos"
        ])
        
        with tabs[0]:
            self.show_executive_summary(df, proveedor, metrics)
        
        with tabs[1]:
            self.show_products_analysis(df)
        
        with tabs[2]:
            self.show_temporal_analysis(df)
        
        with tabs[3]:
            self.show_advanced_analysis(df, metrics)
        
        with tabs[4]:
            self.show_reports_section(df, proveedor, metrics)
        
        with tabs[5]:
            self.show_forecast_analysis(df)
    
    def show_executive_summary(self, df, proveedor, metrics):
        """Mostrar resumen ejecutivo"""
        st.subheader(f"📈 Resumen Ejecutivo - {proveedor}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "💰 Ventas Totales",
                f"${metrics['total_ventas']:,.0f}",
                delta=f"{metrics['margen_promedio']:.1f}% margen"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "📈 Utilidad Total",
                f"${metrics['total_utilidad']:,.0f}",
                delta=f"${metrics['ticket_promedio']:,.0f} ticket prom."
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "🧾 Total Transacciones",
                f"{metrics['num_tickets']:,}",
                delta=f"{metrics['dias_con_ventas']} días activos"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "📦 Cantidad Vendida",
                f"{metrics['total_cantidad']:,.0f}",
                delta=f"{metrics['productos_unicos']} productos"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.subheader("💡 Insights Estratégicos")
        insights = self.generate_insights(df, metrics)
        
        for tipo, mensaje in insights:
            if tipo == "success":
                st.markdown(f'<div class="success-box">{mensaje}</div>', unsafe_allow_html=True)
            elif tipo == "warning":
                st.markdown(f'<div class="warning-box">{mensaje}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="insight-box">{mensaje}</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            ventas_diarias = df.groupby('fecha')['precio_total'].sum().reset_index()
            fig = px.line(
                ventas_diarias, x='fecha', y='precio_total',
                title="📈 Evolución Diaria de Ventas",
                labels={'precio_total': 'Ventas ($)', 'fecha': 'Fecha'}
            )
            fig.update_traces(line_color='#2a5298', line_width=3)
            fig.update_layout(
                height=400,
                showlegend=True,
                hovermode='x unified',
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            top_productos = df.groupby('descripcion')['precio_total'].sum().nlargest(5).reset_index()
            top_productos['descripcion_corta'] = top_productos['descripcion'].str[:30]
            
            fig = px.bar(
                top_productos, x='precio_total', y='descripcion_corta',
                orientation='h',
                title="🏆 Top 5 Productos",
                labels={'precio_total': 'Ventas ($)', 'descripcion_corta': 'Producto'}
            )
            fig.update_traces(marker_color='#28a745')
            fig.update_layout(
                height=400,
                showlegend=False,
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    def show_products_analysis(self, df):
        """Análisis detallado de productos"""
        st.subheader("🏆 Análisis de Productos")
        
        try:
            productos_stats = df.groupby(['idarticulo', 'descripcion']).agg({
                'precio_total': 'sum',
                'costo_total': 'sum',
                'utilidad': 'sum',
                'cantidad_total': 'sum',
                'margen_porcentual': 'mean'
            }).round(2)
            
            productos_stats.columns = ['Ventas', 'Costos', 'Utilidad', 'Cantidad', 'Margen %']
            productos_stats['Participación %'] = (productos_stats['Ventas'] / productos_stats['Ventas'].sum() * 100).round(2)
            productos_stats['Tickets'] = df.groupby(['idarticulo', 'descripcion']).size()
            
            col1, col2 = st.columns([3, 1])
            with col2:
                orden_por = st.selectbox(
                    "Ordenar por:",
                    ["Ventas", "Utilidad", "Margen %", "Cantidad", "Participación %"],
                    key="orden_productos"
                )
                top_n = st.slider("Mostrar top N productos:", 5, 50, 20)
            
            productos_ordenados = productos_stats.sort_values(orden_por, ascending=False).head(top_n)
            productos_display = productos_ordenados.copy()
            productos_display.index = [f"{desc[:40]}..." if len(desc) > 40 else desc for _, desc in productos_display.index]
            
            st.dataframe(
                productos_display,
                use_container_width=True,
                column_config={
                    "Ventas": st.column_config.NumberColumn("Ventas", format="$%.0f"),
                    "Costos": st.column_config.NumberColumn("Costos", format="$%.0f"),
                    "Utilidad": st.column_config.NumberColumn("Utilidad", format="$%.0f"),
                    "Cantidad": st.column_config.NumberColumn("Cantidad", format="%.0f"),
                    "Margen %": st.column_config.NumberColumn("Margen %", format="%.1f%%"),
                    "Participación %": st.column_config.NumberColumn("Participación %", format="%.1f%%"),
                    "Tickets": st.column_config.NumberColumn("Tickets", format="%d")
                }
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                top_n_df = productos_stats.head(top_n).reset_index()
                top_n_df['producto_corto'] = top_n_df['descripcion'].str[:30] + '...'
                
                fig = px.scatter(
                    top_n_df,
                    x='Ventas', 
                    y='Margen %',
                    size='Cantidad',
                    color='Utilidad',
                    hover_name='producto_corto',
                    hover_data={'Utilidad': ':,.0f'},
                    title=f"💹 Ventas vs Margen (Top {top_n})",
                    color_continuous_scale='Viridis'
                )
                fig.update_traces(marker=dict(opacity=0.7))
                fig.update_layout(template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                productos_pareto = productos_stats.head(top_n)
                participacion_acum = productos_pareto['Participación %'].cumsum()
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                fig.add_trace(
                    go.Bar(
                        x=list(range(1, len(productos_pareto) + 1)),
                        y=productos_pareto['Participación %'],
                        name='Participación Individual (%)',
                        marker_color='lightblue'
                    ),
                    secondary_y=False
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=list(range(1, len(productos_pareto) + 1)),
                        y=participacion_acum,
                        mode='lines+markers',
                        name='Participación Acumulada (%)',
                        line=dict(color='red', width=3)
                    ),
                    secondary_y=True
                )
                
                fig.update_layout(
                    title_text="📈 Análisis de Pareto",
                    xaxis_title="Ranking de Productos",
                    yaxis_title="Participación Individual (%)",
                    yaxis2_title="Participación Acumulada (%)",
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)
                
        except Exception as e:
            logger.error(f"Error en análisis de productos: {str(e)}")
            st.error(f"❌ Error en análisis de productos: {str(e)}")
    
    def show_temporal_analysis(self, df):
        """Análisis temporal"""
        st.subheader("📅 Análisis Temporal")
        
        mensual = df.groupby('mes_año').agg({
            'precio_total': 'sum',
            'utilidad': 'sum',
            'cantidad_total': 'sum',
            'margen_porcentual': 'mean'
        }).round(2)
        
        mensual['tickets'] = df.groupby('mes_año').size()
        mensual = mensual.reset_index()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(
                go.Scatter(
                    x=mensual['mes_año'],
                    y=mensual['precio_total'],
                    name='Ventas',
                    line=dict(color='#2a5298', width=4)
                ),
                secondary_y=False
            )
            
            fig.add_trace(
                go.Scatter(
                    x=mensual['mes_año'],
                    y=mensual['tickets'],
                    name='Tickets',
                    line=dict(color='#28a745', width=4, dash='dash')
                ),
                secondary_y=True
            )
            
            fig.update_layout(
                title="📈 Ventas y Tickets Mensuales",
                xaxis_title="Mes",
                yaxis_title="Ventas ($)",
                yaxis2_title="Tickets",
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.line(
                mensual, x='mes_año', y='margen_porcentual',
                title="📊 Margen Mensual",
                markers=True
            )
            fig.update_traces(line_color='#28a745', line_width=4, marker_size=8)
            fig.update_yaxes(tickformat='.1f', ticksuffix='%')
            fig.update_layout(template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)
        
        if 'dia_semana' in df.columns:
            st.markdown("### 📅 Análisis por Día de la Semana")
            
            dia_mapping = {
                'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            
            df['dia_semana_es'] = df['dia_semana'].map(dia_mapping)
            
            semanal = df.groupby('dia_semana_es').agg({
                'precio_total': 'sum',
                'utilidad': 'sum',
                'margen_porcentual': 'mean',
                'hora': 'count'
            }).round(2)
            
            orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            semanal = semanal.reindex([dia for dia in orden_dias if dia in semanal.index])
            semanal = semanal.reset_index()
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    semanal, x='dia_semana_es', y='precio_total',
                    title="📊 Ventas por Día",
                    color='precio_total',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    semanal, x='dia_semana_es', y='margen_porcentual',
                    title="📈 Margen por Día",
                    color='margen_porcentual',
                    color_continuous_scale='Greens'
                )
                fig.update_yaxes(tickformat='.1f', ticksuffix='%')
                fig.update_layout(template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
        
        # Análisis horario
        if 'hora' in df.columns:
            st.markdown("### ⏰ Análisis Horario")
            horario = df.groupby('hora').agg({
                'precio_total': 'sum',
                'margen_porcentual': 'mean'
            }).reset_index()
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(
                go.Bar(
                    x=horario['hora'],
                    y=horario['precio_total'],
                    name='Ventas',
                    marker_color='lightblue'
                ),
                secondary_y=False
            )
            
            fig.add_trace(
                go.Scatter(
                    x=horario['hora'],
                    y=horario['margen_porcentual'],
                    name='Margen',
                    line=dict(color='red', width=3)
                ),
                secondary_y=True
            )
            
            fig.update_layout(
                title="⏰ Distribución Horaria",
                xaxis_title="Hora del Día",
                yaxis_title="Ventas ($)",
                yaxis2_title="Margen (%)",
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    def show_advanced_analysis(self, df, metrics):
        """Análisis avanzado"""
        st.subheader("🎯 Análisis Estratégico")
        
        if 'familia' in df.columns and df['familia'].notna().any():
            st.markdown("### 🌿 Análisis por Familia")
            
            familia_stats = df.groupby('familia').agg({
                'precio_total': 'sum',
                'utilidad': 'sum',
                'margen_porcentual': 'mean',
                'cantidad_total': 'sum'
            }).round(2)
            
            familia_stats['participacion'] = (familia_stats['precio_total'] / familia_stats['precio_total'].sum() * 100).round(1)
            familia_stats = familia_stats.sort_values('precio_total', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(
                    values=familia_stats['precio_total'],
                    names=familia_stats.index,
                    title="🥧 Distribución por Familia"
                )
                fig.update_layout(template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    familia_stats,
                    x=familia_stats.index,
                    y='margen_porcentual',
                    title="📊 Margen por Familia",
                    color='margen_porcentual',
                    color_continuous_scale='RdYlGn'
                )
                fig.update_yaxes(tickformat='.1f', ticksuffix='%')
                fig.update_layout(template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
        
        if 'sucursal' in df.columns and df['sucursal'].notna().any():
            st.markdown("### 🏪 Análisis por Sucursal")
            
            sucursal_stats = df.groupby('sucursal').agg({
                'precio_total': 'sum',
                'utilidad': 'sum',
                'margen_porcentual': 'mean',
                'cantidad_total': 'sum'
            }).round(2)
            
            sucursal_stats['tickets'] = df.groupby('sucursal').size()
            sucursal_stats['participacion'] = (sucursal_stats['precio_total'] / sucursal_stats['precio_total'].sum() * 100).round(1)
            sucursal_stats = sucursal_stats.sort_values('precio_total', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(
                    values=sucursal_stats['precio_total'],
                    names=sucursal_stats.index,
                    title="🏪 Distribución de Ventas"
                )
                fig.update_layout(template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.scatter(
                    sucursal_stats.reset_index(),
                    x='tickets',
                    y='precio_total',
                    size='margen_porcentual',
                    color='utilidad',
                    hover_name='sucursal',
                    title="🎯 Tickets vs Ventas",
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("### 📊 Análisis ABC")
        
        productos_abc = df.groupby(['idarticulo', 'descripcion']).agg({
            'precio_total': 'sum',
            'utilidad': 'sum'
        }).sort_values('precio_total', ascending=False)
        
        productos_abc['participacion_acum'] = (productos_abc['precio_total'].cumsum() / productos_abc['precio_total'].sum() * 100)
        
        def categorizar_abc(participacion):
            if participacion <= 80:
                return 'A (Alto valor)'
            elif participacion <= 95:
                return 'B (Valor medio)'
            else:
                return 'C (Bajo valor)'
        
        productos_abc['categoria_abc'] = productos_abc['participacion_acum'].apply(categorizar_abc)
        
        abc_counts = productos_abc['categoria_abc'].value_counts()
        abc_ventas = productos_abc.groupby('categoria_abc')['precio_total'].sum()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                x=abc_counts.index,
                y=abc_counts.values,
                title="📈 Distribución ABC",
                labels={'x': 'Categoría', 'y': 'Productos'},
                color=abc_counts.values,
                color_continuous_scale='Blues'
            )
            fig.update_layout(template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.pie(
                values=abc_ventas.values,
                names=abc_ventas.index,
                title="💰 Ventas por Categoría ABC"
            )
            fig.update_layout(template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)
        
        # Recomendaciones estratégicas
        st.markdown("### 💡 Recomendaciones Estratégicas")
        
        recomendaciones = []
        
        # Análisis de productos A
        productos_a = productos_abc[productos_abc['categoria_abc'] == 'A (Alto valor)']
        if len(productos_a) > 0:
            recomendaciones.append(f"🎯 **Productos A:** {len(productos_a)} productos generan el 80% de las ventas. Priorizar su disponibilidad y promoción.")
        
        # Análisis de margen
        if metrics['margen_promedio'] < 20:
            recomendaciones.append("⚠️ **Margen bajo:** Revisar precios y costos. Considerar renegociación con proveedores.")
        
        # Análisis de diversificación
        if metrics['productos_unicos'] < 10:
            recomendaciones.append("📈 **Ampliar catálogo:** Pocos productos únicos. Considerar expandir línea de productos.")
        
        # Análisis de ticket promedio
        if metrics['ticket_promedio'] < 2000:
            recomendaciones.append("💡 **Cross-selling:** Ticket promedio bajo. Implementar estrategias de venta cruzada.")
        
        for rec in recomendaciones:
            st.markdown(f'<div class="insight-box">{rec}</div>', unsafe_allow_html=True)
    
    def show_forecast_analysis(self, df):
        """Análisis de pronósticos"""
        st.subheader("🔮 Pronósticos de Ventas")
        
        forecast_data = st.session_state.forecast_data
        
        if forecast_data[0] is None or forecast_data[1] is None:
            st.warning("⚠️ No se pudo generar el pronóstico. Verifica que haya suficientes datos (mínimo 7 días).")
            return
        
        forecast_df, ventas_históricas = forecast_data
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = go.Figure()
            
            # Datos históricos
            fig.add_trace(
                go.Scatter(
                    x=ventas_históricas['fecha'],
                    y=ventas_históricas['precio_total'],
                    name='Ventas Históricas',
                    mode='lines+markers',
                    line=dict(color='#2a5298', width=2),
                    marker=dict(size=6)
                )
            )
            
            # Media móvil histórica
            fig.add_trace(
                go.Scatter(
                    x=ventas_históricas['fecha'],
                    y=ventas_históricas['media_movil_7'],
                    name='Media Móvil 7 días',
                    line=dict(color='#28a745', width=2, dash='dash')
                )
            )
            
            # Pronóstico
            fig.add_trace(
                go.Scatter(
                    x=forecast_df['fecha'],
                    y=forecast_df['pronostico'],
                    name='Pronóstico',
                    line=dict(color='red', width=3)
                )
            )
            
            # Banda de confianza
            fig.add_trace(
                go.Scatter(
                    x=forecast_df['fecha'],
                    y=forecast_df['limite_superior'],
                    fill=None,
                    mode='lines',
                    line_color='rgba(0,0,0,0)',
                    showlegend=False
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=forecast_df['fecha'],
                    y=forecast_df['limite_inferior'],
                    fill='tonexty',
                    mode='lines',
                    line_color='rgba(0,0,0,0)',
                    name='Intervalo Confianza',
                    fillcolor='rgba(255,0,0,0.1)'
                )
            )
            
            fig.update_layout(
                title="🔮 Pronóstico de Ventas (30 días)",
                xaxis_title="Fecha",
                yaxis_title="Ventas ($)",
                template='plotly_white',
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Métricas del pronóstico
            promedio_pronostico = forecast_df['pronostico'].mean()
            total_pronosticado = forecast_df['pronostico'].sum()
            promedio_historico = ventas_históricas['precio_total'].tail(30).mean()
            
            st.markdown("### 📊 Métricas del Pronóstico")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric(
                    "Promedio Diario Proyectado",
                    f"${promedio_pronostico:,.0f}",
                    delta=f"{((promedio_pronostico/promedio_historico-1)*100):+.1f}%" if promedio_historico > 0 else None
                )
            
            with col_b:
                st.metric(
                    "Total Próximos 30 días",
                    f"${total_pronosticado:,.0f}"
                )
            
            # Distribución del pronóstico
            fig_dist = px.histogram(
                forecast_df, x='pronostico',
                title="📊 Distribución del Pronóstico",
                nbins=20
            )
            fig_dist.update_layout(template='plotly_white')
            st.plotly_chart(fig_dist, use_container_width=True)
        
        # Tabla de pronóstico
        st.markdown("### 📅 Detalle del Pronóstico")
        
        forecast_display = forecast_df.copy()
        forecast_display['fecha'] = forecast_display['fecha'].dt.strftime('%Y-%m-%d')
        forecast_display = forecast_display.round(2)
        
        st.dataframe(
            forecast_display,
            use_container_width=True,
            column_config={
                "fecha": "Fecha",
                "pronostico": st.column_config.NumberColumn("Pronóstico", format="$%.0f"),
                "limite_superior": st.column_config.NumberColumn("Límite Superior", format="$%.0f"),
                "limite_inferior": st.column_config.NumberColumn("Límite Inferior", format="$%.0f")
            },
            hide_index=True
        )
    
    def show_reports_section(self, df, proveedor, metrics):
        """Sección de reportes"""
        st.subheader("📁 Reportes y Exportaciones")
        
        resumen_data = {
            'Métrica': [
                'Proveedor',
                'Período',
                'Ventas Totales',
                'Utilidad Total',
                'Margen Promedio',
                'Total Transacciones',
                'Ticket Promedio',
                'Productos Únicos',
                'Días con Ventas',
                'Concentración Top 5'
            ],
            'Valor': [
                proveedor,
                f"{df['fecha'].min()} a {df['fecha'].max()}",
                f"${metrics['total_ventas']:,.2f}",
                f"${metrics['total_utilidad']:,.2f}",
                f"{metrics['margen_promedio']:.1f}%",
                f"{metrics['num_tickets']:,}",
                f"${metrics['ticket_promedio']:,.2f}",
                f"{metrics['productos_unicos']:,}",
                f"{metrics['dias_con_ventas']:,}",
                f"{metrics['concentracion_ventas']:.1f}%"
            ]
        }
        
        df_resumen = pd.DataFrame(resumen_data)
        st.dataframe(df_resumen, use_container_width=True, hide_index=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📊 Datos Completos (CSV)",
                data=csv_data,
                file_name=f"analisis_{proveedor.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            resumen_csv = df_resumen.to_csv(index=False)
            st.download_button(
                label="📋 Resumen (CSV)",
                data=resumen_csv,
                file_name=f"resumen_{proveedor.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col3:
            top_productos = df.groupby(['idarticulo', 'descripcion']).agg({
                'precio_total': 'sum',
                'utilidad': 'sum',
                'cantidad_total': 'sum',
                'margen_porcentual': 'mean'
            }).round(2).sort_values('precio_total', ascending=False).head(50)
            
            top_productos_csv = top_productos.to_csv()
            st.download_button(
                label="🏆 Top Productos (CSV)",
                data=top_productos_csv,
                file_name=f"top_productos_{proveedor.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col4:
            reporte_text = self.generate_simple_pdf_report(df, proveedor, metrics)
            st.download_button(
                label="📄 Reporte (TXT)",
                data=reporte_text,
                file_name=f"reporte_{proveedor.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
        
        # Generar reporte completo en JSON
        st.markdown("### 🔧 Exportación Avanzada")
        
        reporte_completo = {
            'metadata': {
                'proveedor': proveedor,
                'fecha_inicio': str(df['fecha'].min()),
                'fecha_fin': str(df['fecha'].max()),
                'generado_en': datetime.now().isoformat(),
                'total_registros': len(df)
            },
            'metricas_principales': {
                'ventas_totales': float(metrics['total_ventas']),
                'utilidad_total': float(metrics['total_utilidad']),
                'margen_promedio': float(metrics['margen_promedio']),
                'ticket_promedio': float(metrics['ticket_promedio']),
                'productos_unicos': int(metrics['productos_unicos']),
                'num_tickets': int(metrics['num_tickets']),
                'concentracion_ventas': float(metrics['concentracion_ventas'])
            },
            'insights': [insight[1] for insight in self.generate_insights(df, metrics)]
        }
        
        json_data = json.dumps(reporte_completo, indent=2, ensure_ascii=False)
        st.download_button(
            label="🗂️ Reporte Completo (JSON)",
            data=json_data,
            file_name=f"reporte_completo_{proveedor.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
        
        st.markdown("### 👁️ Vista Previa")
        st.dataframe(
            df.head(100),
            use_container_width=True,
            column_config={
                "precio_total": st.column_config.NumberColumn("Precio Total", format="$%.2f"),
                "costo_total": st.column_config.NumberColumn("Costo Total", format="$%.2f"),
                "utilidad": st.column_config.NumberColumn("Utilidad", format="$%.2f"),
                "margen_porcentual": st.column_config.NumberColumn("Margen %", format="%.1f%%"),
                "cantidad_total": st.column_config.NumberColumn("Cantidad", format="%.0f")
            }
        )
        
        if len(df) > 100:
            st.info(f"ℹ️ Mostrando las primeras 100 filas de {len(df):,} registros totales.")
    
    def run(self):
        """Ejecutar dashboard"""
        proveedor, fecha_inicio, fecha_fin = self.show_sidebar_filters()
        self.show_main_dashboard()
        
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.8em;">
            🚀 Dashboard de Análisis Estratégico | Powered by Streamlit & BigQuery
        </div>
        """, unsafe_allow_html=True)

def main():
    """Función principal"""
    try:
        dashboard = ProveedorDashboard()
        dashboard.run()
    except Exception as e:
        logger.error(f"Error en ejecución principal: {str(e)}")
        st.error("❌ Error en la ejecución del dashboard. Por favor intenta de nuevo.")

if __name__ == "__main__":
    main()