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
import logging

warnings.filterwarnings('ignore')

# === CONFIGURACION DE LOGGING ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === CONFIGURACION DE PAGINA ===
st.set_page_config(
    page_title="📊 Analytics Dashboard Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === CSS PERSONALIZADO Y TEMAS (Modo Oscuro Profesional) ===
def apply_theme():
    if st.session_state.get('theme', 'light') == 'dark':
        st.markdown("""
        <style>
            .main-header {
                background: linear-gradient(90deg, #1A1A2E, #16213E);
                padding: 2rem;
                border-radius: 15px;
                margin-bottom: 2rem;
                text-align: center;
                color: #E0E0E0;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
            }
            .metric-container {
                background: #2E2E40;
                padding: 1.5rem;
                border-radius: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                border-left: 4px solid #0F3460;
                color: #E0E0E0;
            }
            .insight-box {
                background: #1F2C3F;
                border: 1px solid #0F3460;
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
                border-left: 4px solid #53B8BB;
                color: #E0E0E0;
            }
            .warning-box {
                background: #4D3A00;
                border: 1px solid #FFC107;
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
                border-left: 4px solid #FFC107;
                color: #FFF3CD;
            }
            .success-box {
                background: #1C4535;
                border: 1px solid #28A745;
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
                border-left: 4px solid #28A745;
                color: #D4EDDA;
            }
            .stSidebar .stSelectbox {
                background-color: #1A1A2E;
                color: #E0E0E0;
            }
            .stSidebar .stButton>button {
                background-color: #0F3460;
                color: white;
                border-radius: 5px;
            }
            .stSidebar .stButton>button:hover {
                background-color: #16213E;
                color: #E0E0E0;
                border-color: #53B8BB;
            }
            /* General text color for dark mode */
            body {
                color: #E0E0E0;
            }
            h1, h2, h3, h4, h5, h6, .stMarkdown {
                color: #E0E0E0;
            }
            /* Specific adjustments for input fields in dark mode */
            .stDateInput, .stNumberInput, .stTextInput {
                background-color: #2E2E40;
                color: #E0E0E0;
                border-color: #0F3460;
            }
            /* Adjustments for expanders in dark mode */
            .streamlit-expanderHeader {
                background-color: #16213E;
                color: #E0E0E0;
                border-radius: 8px;
                border: 1px solid #0F3460;
            }
            /* Adjust dataframe styling in dark mode */
            .stDataFrame {
                color: #E0E0E0;
                background-color: #1F2C3F;
                border: 1px solid #0F3460;
            }
            .stDataFrame th {
                background-color: #0F3460;
                color: #E0E0E0;
            }
            .stDataFrame tr:nth-child(even) {
                background-color: #2E2E40;
            }
            .stDataFrame tr:nth-child(odd) {
                background-color: #1F2C3F;
            }
        </style>
        """, unsafe_allow_html=True)
        # Apply dark theme to Plotly charts
        st.session_state['plotly_template'] = 'plotly_dark'
    else:
        st.markdown("""
        <style>
            .main-header {
                background: linear-gradient(90deg, #1e3c72, #2a5298);
                padding: 2rem;
                border-radius: 15px;
                margin-bottom: 2rem;
                text-align: center;
                color: white;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .metric-container {
                background: white;
                padding: 1.5rem;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border-left: 4px solid #2a5298;
            }
            .insight-box {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
                border-left: 4px solid #28a745;
            }
            .warning-box {
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
                border-left: 4px solid #ffc107;
            }
            .success-box {
                background: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 8px;
                padding: 1rem;
                margin: 0.5rem 0;
                border-left: 4px solid #28a745;
            }
            .sidebar .sidebar-content {
                background: #f1f3f4;
            }
        </style>
        """, unsafe_allow_html=True)
        # Apply light theme to Plotly charts
        st.session_state['plotly_template'] = 'plotly_white'

if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

apply_theme()

# === DETECTAR ENTORNO ===
IS_CLOUD = "gcp_service_account" in st.secrets if hasattr(st, 'secrets') else False

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
        try:
            if IS_CLOUD:
                self.credentials_dict = dict(st.secrets["gcp_service_account"])
                self.sheet_id = st.secrets["google_sheets"]["sheet_id"]
                self.sheet_name = st.secrets["google_sheets"]["sheet_name"]
                self.project_id = st.secrets["project_id"]
                self.bigquery_table = st.secrets["bigquery_table"]
                
                # Write credentials to a temporary file
                with open("temp_credentials.json", "w") as f:
                    json.dump(self.credentials_dict, f)
                self.credentials_path = "temp_credentials.json"
                logging.info("Credentials set up for Cloud environment.")
            else:
                load_dotenv()
                self.credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
                self.sheet_id = os.getenv("GOOGLE_SHEET_ID")
                self.sheet_name = "proveedores_all" # Assuming this is a default local sheet name
                self.project_id = "youtube-analysis-24" # Default project ID for local
                self.bigquery_table = "tickets.tickets_all" # Default table for local
                logging.info("Credentials set up for Local environment.")
            
            if not self.credentials_path or not os.path.exists(self.credentials_path):
                raise FileNotFoundError(f"Credentials file not found at {self.credentials_path}")
                
        except Exception as e:
            logging.error(f"Error setting up credentials: {e}")
            st.error(f"Error al configurar credenciales: {e}. Asegúrate de que los archivos de credenciales y las variables de entorno estén configurados correctamente.")
            st.stop() # Stop execution if credentials fail
    
    @st.cache_data(ttl=3600) # Cache for 1 hour
    def load_proveedores(_self):
        """Cargar datos de proveedores desde Google Sheet público con caching."""
        try:
            url = f"https://docs.google.com/spreadsheets/d/{_self.sheet_id}/gviz/tq?tqx=out:csv&sheet={_self.sheet_name}"
            df = pd.read_csv(url)
            df['proveedor'] = df['proveedor'].astype(str).str.strip().str.upper()
            logging.info("Proveedores data loaded successfully.")
            return df
        except Exception as e:
            logging.error(f"Error loading suppliers data: {e}")
            st.error(f"Error al cargar los datos de proveedores: {e}. Verifica el ID de la hoja de Google y el nombre de la pestaña.")
            return pd.DataFrame() # Return empty DataFrame on error
            
    @st.cache_data(ttl=600) # Cache BigQuery data for 10 minutes
    def query_bigquery_data(self, proveedor, fecha_inicio, fecha_fin):
        """Consultar datos de BigQuery con caching y manejo de errores."""
        try:
            # Obtener IDs de artículos
            # Ensure df_proveedores is loaded before trying to access it
            if self.df_proveedores is None:
                self.df_proveedores = self.load_proveedores()
                if self.df_proveedores.empty:
                    logging.warning(f"No supplier data loaded, cannot query for {proveedor}.")
                    return None
            
            ids = self.df_proveedores[
                self.df_proveedores['proveedor'] == proveedor
            ]['idarticulo'].dropna().astype(int).astype(str).unique()
            
            if len(ids) == 0:
                logging.warning(f"No article IDs found for supplier: {proveedor}")
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
            
            if df.empty:
                logging.info(f"No data found in BigQuery for supplier {proveedor} between {fecha_inicio} and {fecha_fin}.")
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
            
            logging.info(f"BigQuery data loaded and processed for supplier: {proveedor}")
            return df
            
        except Exception as e:
            logging.error(f"Error querying BigQuery for {proveedor}: {e}", exc_info=True)
            st.error(f"Error al consultar BigQuery para el proveedor '{proveedor}': {e}. Por favor, verifica la conexión y los permisos de BigQuery.")
            return None
    
    def calculate_metrics(self, df):
        """Calcular métricas principales."""
        if df.empty:
            return {
                'total_ventas': 0, 'total_costos': 0, 'total_utilidad': 0,
                'margen_promedio': 0, 'total_cantidad': 0, 'num_tickets': 0,
                'ticket_promedio': 0, 'productos_unicos': 0, 'dias_con_ventas': 0,
                'sucursales': 0, 'familias': 0
            }
        
        metrics = {
            'total_ventas': df['precio_total'].sum(),
            'total_costos': df['costo_total'].sum(),
            'total_utilidad': df['utilidad'].sum(),
            'margen_promedio': df['margen_porcentual'].mean() if not df.empty else 0,
            'total_cantidad': df['cantidad_total'].sum(),
            'num_tickets': len(df),
            'ticket_promedio': df['precio_total'].sum() / len(df) if len(df) > 0 else 0,
            'productos_unicos': df['idarticulo'].nunique(),
            'dias_con_ventas': df['fecha'].nunique(),
            'sucursales': df['sucursal'].nunique() if 'sucursal' in df.columns else 0,
            'familias': df['familia'].nunique() if 'familia' in df.columns else 0
        }
        logging.info("Metrics calculated successfully.")
        return metrics
    
    def generate_insights(self, df, metrics):
        """Generar insights automáticos."""
        insights = []
        
        if metrics['margen_promedio'] > 30:
            insights.append(("success", f"🎯 **Excelente rentabilidad**: {metrics['margen_promedio']:.1f}% de margen promedio. ¡Bien hecho!"))
        elif metrics['margen_promedio'] > 20:
            insights.append(("info", f"📈 **Buena rentabilidad**: {metrics['margen_promedio']:.1f}% de margen promedio. Mantente así."))
        else:
            insights.append(("warning", f"⚠️ **Margen bajo**: {metrics['margen_promedio']:.1f}% - Revisar estrategia de precios para mejorar la rentabilidad."))
        
        top_producto = df.groupby('descripcion')['precio_total'].sum().nlargest(1)
        if not top_producto.empty:
            producto_name = top_producto.index[0]
            producto_ventas = top_producto.iloc[0]
            participacion = (producto_ventas / metrics['total_ventas']) * 100 if metrics['total_ventas'] > 0 else 0
            insights.append(("info", f"🏆 **Producto estrella**: **{producto_name[:50]}...** (representa el {participacion:.1f}% de las ventas)."))
        
        if len(df) > 7:
            ventas_por_dia = df.groupby('fecha')['precio_total'].sum()
            tendencia_dias = min(7, len(ventas_por_dia)) # Ensure enough days for calculation
            if tendencia_dias > 0:
                ultimos_dias_avg = ventas_por_dia.tail(tendencia_dias).mean()
                primeros_dias_avg = ventas_por_dia.head(tendencia_dias).mean()
                
                if primeros_dias_avg > 0:
                    change = ((ultimos_dias_avg / primeros_dias_avg) - 1) * 100
                    if change > 10:
                        insights.append(("success", f"📈 **Tendencia positiva**: Ventas crecen un **+{change:.1f}%** en los últimos días. ¡Gran impulso!"))
                    elif change < -10:
                        insights.append(("warning", f"📉 **Tendencia bajista**: Ventas caen un **{change:.1f}%** en los últimos días. Es momento de investigar."))
                    else:
                        insights.append(("info", f"📊 **Tendencia estable**: Las ventas se mantienen consistentes en el período reciente."))
                else:
                    insights.append(("info", "📊 No hay suficientes datos de ventas recientes para determinar una tendencia clara."))
        else:
            insights.append(("info", "📊 No hay suficientes datos históricos para un análisis de tendencia significativo."))
            
        if metrics['productos_unicos'] < 5 and metrics['productos_unicos'] > 0:
            insights.append(("warning", "🎯 **Baja diversificación de productos**: Solo pocos productos únicos. Considera ampliar el catálogo."))
        elif metrics['productos_unicos'] >= 20:
            insights.append(("success", f"🌟 **Excelente diversificación**: **{metrics['productos_unicos']}** productos únicos. Esto reduce riesgos."))
        else:
            insights.append(("info", f"💡 **Diversificación adecuada**: **{metrics['productos_unicos']}** productos únicos. Hay espacio para crecer."))
        
        if metrics['ticket_promedio'] > 5000:
            insights.append(("success", f"💰 **Alto valor por transacción**: Promedio de **${metrics['ticket_promedio']:,.0f}**. ¡Excelente!"))
        elif metrics['ticket_promedio'] < 1000 and metrics['ticket_promedio'] > 0:
            insights.append(("info", "💡 **Oportunidad de cross-selling**: El ticket promedio es bajo. Promociona productos complementarios."))
        
        logging.info("Insights generated.")
        return insights
    
    def show_sidebar_filters(self):
        """Mostrar filtros en sidebar y botón de tema."""
        st.sidebar.markdown("## 🎛️ Configuración de Análisis")
        
        # Tema oscuro/claro
        if st.sidebar.button("🎨 Cambiar Tema"):
            st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'
            st.rerun()

        # Cargar proveedores
        if self.df_proveedores is None or self.df_proveedores.empty:
            with st.spinner("Cargando proveedores..."):
                self.df_proveedores = self.load_proveedores()
        
        if self.df_proveedores.empty:
            st.sidebar.error("No se pudieron cargar los datos de proveedores. Por favor, revisa la configuración.")
            return None, None, None

        st.sidebar.markdown("### 🏪 Selección de Proveedor")
        proveedores = sorted(self.df_proveedores['proveedor'].dropna().unique())
        
        proveedor = st.sidebar.selectbox(
            "Proveedor:",
            options=proveedores,
            index=None,
            placeholder="Seleccionar proveedor...",
            key="proveedor_select" # Added key for better state management
        )
        
        st.sidebar.markdown("### 📅 Período de Análisis")
        
        rango_opciones = {
            "Último mes": 30,
            "Últimos 3 meses": 90,
            "Últimos 6 meses": 180,
            "Último año": 365,
            "Personalizado": None
        }
        
        rango_seleccionado = st.sidebar.selectbox(
            "Rango de fechas:",
            options=list(rango_opciones.keys()),
            index=2, # Por defecto últimos 6 meses
            key="date_range_select"
        )
        
        fecha_fin = datetime.now().date()
        if rango_seleccionado == "Personalizado":
            col1, col2 = st.sidebar.columns(2)
            fecha_inicio = col1.date_input(
                "Desde:",
                value=datetime.now().date() - timedelta(days=180) if st.session_state.analysis_data is None else st.session_state.analysis_data['fecha'].min(),
                key="start_date_input"
            )
            fecha_fin = col2.date_input(
                "Hasta:",
                value=datetime.now().date() if st.session_state.analysis_data is None else st.session_state.analysis_data['fecha'].max(),
                key="end_date_input"
            )
            # Ensure fecha_inicio is not after fecha_fin
            if fecha_inicio > fecha_fin:
                st.sidebar.warning("La fecha de inicio no puede ser posterior a la fecha de fin.")
                fecha_inicio = fecha_fin - timedelta(days=1) # Adjust to a valid range
        else:
            dias = rango_opciones[rango_seleccionado]
            fecha_inicio = fecha_fin - timedelta(days=dias)
            st.sidebar.info(f"📅 **{rango_seleccionado}**\n\n{fecha_inicio} a {fecha_fin}")
        
        if st.sidebar.button("🔍 Realizar Análisis", type="primary", use_container_width=True):
            if not proveedor:
                st.sidebar.error("❌ Selecciona un proveedor para realizar el análisis.")
                logging.warning("Analysis button clicked without supplier selected.")
            else:
                with st.spinner("🔄 Consultando y procesando datos de BigQuery..."):
                    df_tickets = self.query_bigquery_data(proveedor, fecha_inicio, fecha_fin)
                    if df_tickets is not None:
                        st.session_state.analysis_data = df_tickets
                        st.session_state.selected_proveedor = proveedor
                        logging.info(f"Analysis data loaded for {proveedor}.")
                        st.rerun()
                    else:
                        st.sidebar.warning("⚠️ No se encontraron datos para el proveedor y período seleccionados.")
                        st.session_state.analysis_data = None # Clear previous data if no new data found
                        st.session_state.selected_proveedor = None
                        logging.info(f"No data found for {proveedor} in specified date range.")
        
        # Información del proveedor si está seleccionado
        if proveedor:
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 📊 Información del Proveedor")
            num_articulos = len(self.df_proveedores[self.df_proveedores['proveedor'] == proveedor])
            st.sidebar.metric("Artículos en catálogo", num_articulos)
            
        return proveedor, fecha_inicio, fecha_fin
    
    def show_main_dashboard(self):
        """Mostrar dashboard principal."""
        st.markdown(f"""
        <div class="main-header">
            <h1>🚀 Dashboard de Análisis de Proveedores</h1>
            <p>Sistema profesional de análisis con datos de BigQuery</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.analysis_data is None:
            st.info("👈 **Selecciona un proveedor y un rango de fechas en el panel lateral para comenzar el análisis.**")
            
            # Show general information
            st.markdown("---")
            st.markdown("### ¿Qué puedes lograr con este Dashboard?")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("""
                ### 🎯 Funcionalidades Clave
                -   Análisis completo de ventas y rentabilidad por proveedor.
                -   Métricas financieras avanzadas.
                -   Visualizaciones interactivas con **animaciones y efectos hover**.
                -   **Insights automáticos** para decisiones rápidas.
                -   Exportación de reportes a **CSV y Excel**.
                """)
            
            with col2:
                st.markdown("""
                ### 📊 Métricas Incluidas
                -   **Ventas y Utilidad Total**.
                -   **Margen de Ganancia Promedio**.
                -   Cantidad y número de transacciones.
                -   Análisis de **productos top** y su impacto.
                -   Evolución temporal y estacionalidad.
                """)
            
            with col3:
                st.markdown("""
                ### 🔍 Análisis Avanzado
                -   **Top 10** productos por métrica.
                -   Distribución por **familia y sucursal**.
                -   Análisis de **Pareto (80/20)** para identificación de productos clave.
                -   Comparativas inter-temporales.
                -   Identificación de **oportunidades y riesgos**.
                """)
            st.markdown("---")
            return
        
        df = st.session_state.analysis_data
        proveedor = st.session_state.selected_proveedor
        metrics = self.calculate_metrics(df)
        
        # Tabs principales
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Resumen Ejecutivo", 
            "🏆 Análisis de Productos", 
            "📅 Evolución Temporal",
            "🎯 Análisis Avanzado",
            "📁 Reportes"
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
            self.show_reports_section(df, proveedor, metrics)
    
    def show_executive_summary(self, df, proveedor, metrics):
        """Mostrar resumen ejecutivo."""
        st.subheader(f"📈 Resumen Ejecutivo - **{proveedor}**")
        
        st.markdown("---")
        # KPIs principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "💰 **Ventas Totales**",
                f"${metrics['total_ventas']:,.0f}",
                delta=f"{metrics['margen_promedio']:.1f}% margen" if metrics['margen_promedio'] != 0 else "0% margen"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "📈 **Utilidad Total**",
                f"${metrics['total_utilidad']:,.0f}",
                delta=f"${metrics['ticket_promedio']:,.0f} ticket prom." if metrics['ticket_promedio'] != 0 else "$0 ticket prom."
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "🧾 **Total Transacciones**",
                f"{metrics['num_tickets']:,}",
                delta=f"{metrics['dias_con_ventas']} días activos"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                "📦 **Cantidad Vendida**",
                f"{metrics['total_cantidad']:,.0f}",
                delta=f"{metrics['productos_unicos']} productos únicos"
            )
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        # Insights automáticos
        st.subheader("💡 Insights Clave")
        insights = self.generate_insights(df, metrics)
        
        for tipo, mensaje in insights:
            if tipo == "success":
                st.markdown(f'<div class="success-box">{mensaje}</div>', unsafe_allow_html=True)
            elif tipo == "warning":
                st.markdown(f'<div class="warning-box">{mensaje}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="insight-box">{mensaje}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("Visualizaciones Clave")
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribución de ventas por día
            ventas_diarias = df.groupby('fecha')['precio_total'].sum().reset_index()
            fig = px.line(
                ventas_diarias, x='fecha', y='precio_total',
                title="📈 **Evolución Diaria de Ventas**",
                labels={'precio_total': 'Ventas ($)', 'fecha': 'Fecha'},
                template=st.session_state['plotly_template']
            )
            fig.update_traces(line_color='#2a5298', line_width=3)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top 10 productos
            top_productos = df.groupby('descripcion')['precio_total'].sum().nlargest(10).sort_values(ascending=True).reset_index() # Top 10, sorted asc for horizontal bar chart
            top_productos['descripcion_corta'] = top_productos['descripcion'].str[:40] + ( '...' if top_productos['descripcion'].str.len() > 40 else '')
            
            fig = px.bar(
                top_productos, x='precio_total', y='descripcion_corta',
                orientation='h',
                title="🏆 **Top 10 Productos por Ventas**",
                labels={'precio_total': 'Ventas ($)', 'descripcion_corta': 'Producto'},
                template=st.session_state['plotly_template']
            )
            fig.update_traces(marker_color='#28a745')
            fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'}) # Ensure largest is at top
            st.plotly_chart(fig, use_container_width=True)
    
    def show_products_analysis(self, df):
        """Análisis detallado de productos."""
        st.subheader("🏆 Análisis Detallado de Productos")
        st.markdown("---")
        
        try:
            productos_stats = df.groupby(['idarticulo', 'descripcion']).agg(
                Ventas=('precio_total', 'sum'),
                Costos=('costo_total', 'sum'),
                Utilidad=('utilidad', 'sum'),
                Cantidad=('cantidad_total', 'sum'),
                Margen_Porcentual=('margen_porcentual', 'mean')
            ).round(2)
            
            productos_stats.columns = ['Ventas', 'Costos', 'Utilidad', 'Cantidad', 'Margen %']
            productos_stats['Participación %'] = (productos_stats['Ventas'] / productos_stats['Ventas'].sum() * 100).round(2)
            productos_stats['Tickets'] = df.groupby(['idarticulo', 'descripcion']).size()
            
            productos_stats = productos_stats.sort_values('Ventas', ascending=False)
            
            st.markdown("### 📊 **TOP 10 Productos Detallado**")
            
            col1, col2 = st.columns([3, 1])
            with col2:
                orden_por = st.selectbox(
                    "Ordenar tabla por:",
                    ["Ventas", "Utilidad", "Margen %", "Cantidad", "Participación %"],
                    key="product_table_sort"
                )
            
            productos_ordenados_display = productos_stats.sort_values(orden_por, ascending=False).head(10).copy()
            productos_ordenados_display.index = [f"{desc[:40]}..." if len(desc) > 40 else desc for _, desc in productos_ordenados_display.index]
            
            st.dataframe(
                productos_ordenados_display,
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
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                # Scatter plot Ventas vs Margen - TOP 10
                top_10_productos_scatter = productos_stats.head(10).reset_index()
                top_10_productos_scatter['producto_corto'] = top_10_productos_scatter['descripcion'].str[:30] + '...'
                
                fig = px.scatter(
                    top_10_productos_scatter,
                    x='Ventas', 
                    y='Margen %',
                    size='Cantidad',
                    hover_name='producto_corto',
                    hover_data={'Utilidad': ':,.0f', 'Costos': ':,.0f'},
                    title="💹 **Ventas vs Margen (Top 10 Productos)**",
                    labels={'Ventas': 'Ventas ($)', 'Margen %': 'Margen (%)'},
                    template=st.session_state['plotly_template']
                )
                fig.update_traces(marker=dict(opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Análisis de Pareto - TOP 10
                productos_pareto = productos_stats.head(10)
                participacion_acum = productos_pareto['Participación %'].cumsum()
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                fig.add_trace(
                    go.Bar(
                        x=[f"P{i+1}" for i in range(len(productos_pareto))], # Simplified labels for Pareto chart
                        y=productos_pareto['Participación %'],
                        name='Participación Individual (%)',
                        marker_color='rgba(42, 82, 152, 0.7)' if st.session_state.theme == 'dark' else 'lightblue'
                    ),
                    secondary_y=False
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=[f"P{i+1}" for i in range(len(productos_pareto))],
                        y=participacion_acum,
                        mode='lines+markers',
                        name='Participación Acumulada (%)',
                        line=dict(color='red', width=3),
                        marker=dict(size=8)
                    ),
                    secondary_y=True
                )
                
                fig.update_layout(
                    title_text="📈 **Análisis de Pareto - Concentración de Ventas (Top 10)**",
                    template=st.session_state['plotly_template']
                )
                fig.update_xaxes(title_text="Ranking de Productos")
                fig.update_yaxes(title_text="Participación Individual (%)", secondary_y=False)
                fig.update_yaxes(title_text="Participación Acumulada (%)", secondary_y=True, range=[0, 100])
                
                st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logging.error(f"Error in product analysis: {e}", exc_info=True)
            st.error(f"❌ Error al realizar el análisis de productos: {str(e)}. Asegúrate de que los datos tengan las columnas esperadas.")
            st.info("💡 Intenta con un rango de fechas diferente o verifica los datos del proveedor.")
    
    def show_temporal_analysis(self, df):
        """Análisis temporal."""
        st.subheader("📅 Análisis de Evolución Temporal")
        st.markdown("---")
        
        # Análisis mensual
        mensual = df.groupby('mes_año').agg(
            Ventas=('precio_total', 'sum'),
            Utilidad=('utilidad', 'sum'),
            Cantidad=('cantidad_total', 'sum'),
            Margen_Porcentual=('margen_porcentual', 'mean')
        ).round(2)
        
        mensual['Tickets'] = df.groupby('mes_año').size()
        mensual = mensual.reset_index()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.line(
                mensual, x='mes_año', y='Ventas',
                title="📈 **Evolución Mensual de Ventas**",
                labels={'Ventas': 'Ventas ($)', 'mes_año': 'Mes y Año'},
                markers=True,
                template=st.session_state['plotly_template']
            )
            fig.update_traces(line_color='#2a5298', line_width=4, marker_size=8)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.line(
                mensual, x='mes_año', y='Margen_Porcentual',
                title="📊 **Evolución del Margen Promedio Mensual**",
                labels={'Margen_Porcentual': 'Margen (%)', 'mes_año': 'Mes y Año'},
                markers=True,
                template=st.session_state['plotly_template']
            )
            fig.update_traces(line_color='#28a745', line_width=4, marker_size=8)
            fig.update_yaxes(tickformat='.1f', ticksuffix='%')
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        # Análisis por día de la semana
        if 'dia_semana' in df.columns and not df['dia_semana'].empty:
            st.markdown("### 📅 **Análisis por Día de la Semana**")
            
            dia_mapping = {
                'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            
            df['dia_semana_es'] = df['dia_semana'].map(dia_mapping)
            
            # Ensure correct order for days of the week
            orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            
            semanal = df.groupby('dia_semana_es').agg(
                Ventas=('precio_total', 'sum'),
                Utilidad=('utilidad', 'sum'),
                Margen_Porcentual=('margen_porcentual', 'mean')
            ).reindex(orden_dias).round(2).reset_index()
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    semanal, x='dia_semana_es', y='Ventas',
                    title="📊 **Ventas por Día de la Semana**",
                    labels={'dia_semana_es': 'Día de la Semana', 'Ventas': 'Ventas ($)'},
                    color='Ventas',
                    color_continuous_scale='Blues',
                    template=st.session_state['plotly_template']
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    semanal, x='dia_semana_es', y='Margen_Porcentual',
                    title="📈 **Margen por Día de la Semana**",
                    labels={'dia_semana_es': 'Día de la Semana', 'Margen_Porcentual': 'Margen (%)'},
                    color='Margen_Porcentual',
                    color_continuous_scale='Greens',
                    template=st.session_state['plotly_template']
                )
                fig.update_yaxes(tickformat='.1f', ticksuffix='%')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay suficientes datos para el análisis por día de la semana o la columna 'dia_semana' no está disponible.")
            
        st.markdown("---")
        # Tabla resumen mensual
        st.markdown("### 📋 **Resumen Mensual de Métricas**")
        
        mensual_display = mensual.copy()
        mensual_display.columns = ['Mes y Año', 'Ventas', 'Utilidad', 'Cantidad', 'Margen %', 'Tickets']
        
        st.dataframe(
            mensual_display,
            use_container_width=True,
            column_config={
                "Ventas": st.column_config.NumberColumn("Ventas", format="$%.0f"),
                "Utilidad": st.column_config.NumberColumn("Utilidad", format="$%.0f"),
                "Cantidad": st.column_config.NumberColumn("Cantidad", format="%.0f"),
                "Margen %": st.column_config.NumberColumn("Margen %", format="%.1f%%"),
                "Tickets": st.column_config.NumberColumn("Tickets", format="%d")
            },
            hide_index=True
        )
    
    def show_advanced_analysis(self, df, metrics):
        """Análisis avanzado."""
        st.subheader("🎯 Análisis Avanzado")
        st.markdown("---")
        
        # Análisis por familia de productos
        if 'familia' in df.columns and df['familia'].notna().any():
            st.markdown("### 🌿 **Análisis por Familia de Productos (Top 10)**")
            
            familia_stats = df.groupby('familia').agg(
                Ventas=('precio_total', 'sum'),
                Utilidad=('utilidad', 'sum'),
                Margen_Porcentual=('margen_porcentual', 'mean'),
                Cantidad=('cantidad_total', 'sum')
            ).round(2)
            
            familia_stats['Participacion %'] = (familia_stats['Ventas'] / familia_stats['Ventas'].sum() * 100).round(1)
            familia_stats = familia_stats.sort_values('Ventas', ascending=False).head(10) # Top 10 families
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(
                    values=familia_stats['Ventas'],
                    names=familia_stats.index,
                    title="🥧 **Distribución de Ventas por Familia (Top 10)**",
                    template=st.session_state['plotly_template']
                )
                fig.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05]*len(familia_stats)) # Emphasize slices
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    x=familia_stats.index,
                    y=familia_stats['Margen_Porcentual'],
                    title="📊 **Margen por Familia de Productos (Top 10)**",
                    labels={'x': 'Familia', 'Margen_Porcentual': 'Margen (%)'},
                    color='Margen_Porcentual',
                    color_continuous_scale='RdYlGn',
                    template=st.session_state['plotly_template']
                )
                fig.update_yaxes(tickformat='.1f', ticksuffix='%')
                fig.update_layout(xaxis={'categoryorder':'total descending'}) # Order bars by value
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("La columna 'familia' no está disponible o no contiene datos para el análisis.")
            
        st.markdown("---")
        # Análisis por sucursal
        if 'sucursal' in df.columns and df['sucursal'].notna().any():
            st.markdown("### 🏪 **Análisis por Sucursal (Top 10)**")
            
            sucursal_stats = df.groupby('sucursal').agg(
                Ventas=('precio_total', 'sum'),
                Utilidad=('utilidad', 'sum'),
                Margen_Porcentual=('margen_porcentual', 'mean'),
                Cantidad=('cantidad_total', 'sum')
            ).round(2)
            
            sucursal_stats['Tickets'] = df.groupby('sucursal').size()
            sucursal_stats['Participacion %'] = (sucursal_stats['Ventas'] / sucursal_stats['Ventas'].sum() * 100).round(1)
            sucursal_stats = sucursal_stats.sort_values('Ventas', ascending=False).head(10) # Top 10 branches
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                fig = px.pie(
                    values=sucursal_stats['Ventas'],
                    names=sucursal_stats.index,
                    title="🏪 **Ventas por Sucursal (Top 10)**",
                    template=st.session_state['plotly_template']
                )
                fig.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05]*len(sucursal_stats))
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    x=sucursal_stats.index,
                    y=sucursal_stats['Margen_Porcentual'],
                    title="📈 **Margen por Sucursal (Top 10)**",
                    labels={'x': 'Sucursal', 'Margen_Porcentual': 'Margen (%)'},
                    color='Margen_Porcentual',
                    color_continuous_scale='Viridis',
                    template=st.session_state['plotly_template']
                )
                fig.update_yaxes(tickformat='.1f', ticksuffix='%')
                fig.update_layout(xaxis={'categoryorder':'total descending'})
                st.plotly_chart(fig, use_container_width=True)
            
            with col3:
                # Scatter Tickets vs Ventas por Sucursal - Top 10
                sucursal_reset = sucursal_stats.reset_index()
                sucursal_reset.rename(columns={'sucursal': 'Sucursal'}, inplace=True)
                
                fig = px.scatter(
                    sucursal_reset,
                    x='Tickets',
                    y='Ventas',
                    size='Margen_Porcentual',
                    hover_name='Sucursal',
                    title="🎯 **Tickets vs Ventas por Sucursal (Top 10)**",
                    labels={'Tickets': 'Número de Tickets', 'Ventas': 'Ventas ($)'},
                    template=st.session_state['plotly_template']
                )
                fig.update_traces(marker=dict(opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("La columna 'sucursal' no está disponible o no contiene datos para el análisis.")
            
        st.markdown("---")
        # Matriz de análisis ABC
        st.markdown("### 📊 **Análisis ABC de Productos**")
        
        productos_abc = df.groupby(['idarticulo', 'descripcion']).agg(
            Ventas=('precio_total', 'sum'),
            Utilidad=('utilidad', 'sum')
        ).sort_values('Ventas', ascending=False).reset_index()
        
        productos_abc['participacion_acum'] = (productos_abc['Ventas'].cumsum() / productos_abc['Ventas'].sum() * 100)
        
        def categorizar_abc(participacion):
            if participacion <= 80:
                return 'A (Alto valor)'
            elif participacion <= 95:
                return 'B (Valor medio)'
            else:
                return 'C (Bajo valor)'
        
        productos_abc['categoria_abc'] = productos_abc['participacion_acum'].apply(categorizar_abc)
        
        abc_summary = productos_abc.groupby('categoria_abc').agg(
            Num_Productos=('idarticulo', 'count'),
            Total_Ventas=('Ventas', 'sum'),
            Participacion_Ventas=('Ventas', lambda x: (x.sum() / productos_abc['Ventas'].sum()) * 100)
        ).round(2).reset_index()

        # Define category order for plotting
        category_order = ['A (Alto valor)', 'B (Valor medio)', 'C (Bajo valor)']
        abc_summary['categoria_abc'] = pd.Categorical(abc_summary['categoria_abc'], categories=category_order, ordered=True)
        abc_summary = abc_summary.sort_values('categoria_abc')

        st.dataframe(
            abc_summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Total_Ventas": st.column_config.NumberColumn("Total Ventas", format="$%.0f"),
                "Participacion_Ventas": st.column_config.NumberColumn("Participación Ventas", format="%.1f%%")
            }
        )

        fig = px.bar(
            abc_summary,
            x='categoria_abc',
            y='Num_Productos',
            color='Participacion_Ventas',
            color_continuous_scale='Plasma',
            title="📊 **Distribución de Productos por Categoría ABC**",
            labels={'categoria_abc': 'Categoría ABC', 'Num_Productos': 'Número de Productos'},
            template=st.session_state['plotly_template']
        )
        st.plotly_chart(fig, use_container_width=True)
        
    def show_reports_section(self, df, proveedor, metrics):
        """Sección para exportación de reportes."""
        st.subheader("📁 Reportes y Exportación de Datos")
        st.markdown("---")
        
        st.write("Aquí puedes descargar los datos brutos del análisis o un resumen ejecutivo.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_export = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Exportar Datos Completos (CSV)",
                data=csv_export,
                file_name=f"reporte_completo_{proveedor}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Create a simple Excel report
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Datos Completos', index=False)
                
                # Add a summary sheet
                summary_df = pd.DataFrame([metrics]).T.rename(columns={0: 'Valor'})
                summary_df.index.name = 'Métrica'
                summary_df.loc['margen_promedio', 'Valor'] = f"{summary_df.loc['margen_promedio', 'Valor']:.1f}%"
                summary_df.loc['ticket_promedio', 'Valor'] = f"${summary_df.loc['ticket_promedio', 'Valor']:,.0f}"
                summary_df.loc['total_ventas', 'Valor'] = f"${summary_df.loc['total_ventas', 'Valor']:,.0f}"
                summary_df.loc['total_utilidad', 'Valor'] = f"${summary_df.loc['total_utilidad', 'Valor']:,.0f}"

                productos_stats = df.groupby(['idarticulo', 'descripcion']).agg(
                    Ventas=('precio_total', 'sum'),
                    Utilidad=('utilidad', 'sum'),
                    Margen_Porcentual=('margen_porcentual', 'mean')
                ).round(2).sort_values('Ventas', ascending=False)
                productos_stats.to_excel(writer, sheet_name='Productos_Resumen')

                abc_report = self.get_abc_report(df) # Helper to get ABC report
                abc_report.to_excel(writer, sheet_name='Analisis_ABC', index=False)


            processed_data = output.getvalue()
            st.download_button(
                label="📤 Exportar Reporte Detallado (Excel)",
                data=processed_data,
                file_name=f"reporte_detallado_{proveedor}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.markdown("---")
        st.info("Para análisis personalizados o consultas de datos más específicas, utiliza la sección de filtros.")

    def get_abc_report(self, df):
        """Helper function to generate ABC report for export."""
        productos_abc = df.groupby(['idarticulo', 'descripcion']).agg(
            Ventas=('precio_total', 'sum'),
            Utilidad=('utilidad', 'sum')
        ).sort_values('Ventas', ascending=False).reset_index()
        
        productos_abc['participacion_acum'] = (productos_abc['Ventas'].cumsum() / productos_abc['Ventas'].sum() * 100)
        
        def categorizar_abc(participacion):
            if participacion <= 80:
                return 'A (Alto valor)'
            elif participacion <= 95:
                return 'B (Valor medio)'
            else:
                return 'C (Bajo valor)'
        
        productos_abc['categoria_abc'] = productos_abc['participacion_acum'].apply(categorizar_abc)
        return productos_abc

# === EJECUCIÓN DEL DASHBOARD ===
if __name__ == "__main__":
    import io # Moved here as it's only needed for Excel export
    dashboard = ProveedorDashboard()
    proveedor, fecha_inicio, fecha_fin = dashboard.show_sidebar_filters()
    dashboard.show_main_dashboard()

    # Clean up temporary credentials file if it exists
    if IS_CLOUD and os.path.exists("temp_credentials.json"):
        os.remove("temp_credentials.json")
        logging.info("Temporary credentials file removed.")