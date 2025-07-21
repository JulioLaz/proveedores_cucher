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
warnings.filterwarnings('ignore')

# === CONFIGURACION DE PAGINA ===
st.set_page_config(
    page_title="📊 Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Ocultar solo el logo de Streamlit, no las pestañas */
    header .st-emotion-cache-1avcm0n { display: none !important; }

    /* Estilo para el contenedor principal (cambia padding) */
    .st-emotion-cache-16txtl3 {
        padding: 2rem 1.5rem !important;
    }

    /* Estilo profesional para el sidebar y la imagen de branding */
    .sidebar-brand-box {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
    }

    .sidebar-brand-box img {
        max-width: 100%;
        border-radius: 12px;
    }

    /* Padding general para el contenido */
    .block-container {
        width: 100% !important;
        padding: 2rem 1.5rem !important;
        min-width: auto !important;
        max-width: initial !important;
    }

</style>
""", unsafe_allow_html=True)


# st.markdown("""
# <style>
#     .main-header {
#         background: linear-gradient(90deg, #1e3c72, #2a5298);
#         border-radius: 15px;
#         margin-bottom: .5rem;
#         text-align: center;
#         color: white;
#         box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
#     }
#     .metric-container {
#         background: white;
#         padding: 1.5rem;
#         border-radius: 10px;
#         box-shadow: 0 2px 4px rgba(0,0,0,0.1);
#         border-left: 4px solid #2a5298;
#     }
#     .insight-box {
#         background: #f8f9fa;
#         border: 1px solid #e9ecef;
#         border-radius: 8px;
#         padding: 1rem;
#         margin: 0.5rem 0;
#         border-left: 4px solid #28a745;
#     }
#     .warning-box {
#         background: #fff3cd;
#         border: 1px solid #ffeaa7;
#         border-radius: 8px;
#         padding: 1rem;
#         margin: 0.5rem 0;
#         border-left: 4px solid #ffc107;
#     }
#     .success-box {
#         background: #d4edda;
#         border: 1px solid #c3e6cb;
#         border-radius: 8px;
#         padding: 1rem;
#         margin: 0.5rem 0;
#         border-left: 4px solid #28a745;
#     }
#     .sidebar .sidebar-content {
#         background: #f1f3f4;
#     }

#     /* header {
#         display: none !important;
#     } */


#     /* Quitar padding-top del contenido principal */
#     section.main > div.block-container {
#         padding-top: 0rem !important;
#     }
# </style>
# """, unsafe_allow_html=True)

    # /* 🎯 Estilo personalizado para el contenedor principal */
    # .block-container {
    #     width: 100% !important;
    #     padding: .5rem 1rem !important;
    #     min-width: auto !important;
    #     max-width: initial !important;
    # }
    # /* Estilo personalizado al contenedor específico */
    # .st-emotion-cache-16txtl3 {
    #     padding: 2rem 1rem !important;
    # }
    # /* Ocultar el header superior de Streamlit */
    # header {
    #     display: none !important
    #     }         

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
        df['proveedor'] = df['proveedor'].astype(str).str.strip().str.upper()
        return df
    
    def query_bigquery_data(self, proveedor, fecha_inicio, fecha_fin):
        """Consultar datos de BigQuery"""
        try:
            # Obtener IDs de artículos
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
            
            return df
            
        except Exception as e:
            st.error(f"Error consultando BigQuery: {e}")
            return None
    
    def calculate_metrics(self, df):
        """Calcular métricas principales"""
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
            'sucursales': df['sucursal'].nunique() if 'sucursal' in df.columns else 0,
            'familias': df['familia'].nunique() if 'familia' in df.columns else 0
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
        st.sidebar.markdown("""
            <div class="sidebar-brand-box">
                <img src="https://raw.githubusercontent.com/JulioLaz/proveedores_cucher/main/img/cucher_mercados.png" alt="Logo Cucher">
            </div>
        """, unsafe_allow_html=True)
        # st.sidebar.markdown("""
        #     <style>
        #      .sidebar-logo-box img {
        #         max-width: 100%;
        #         border-radius: 8px;
        #         margin-bottom: 0.5rem;
        #     }

        #     </style>

        #     <div class="sidebar-logo-box">
        #         <img src="https://raw.githubusercontent.com/JulioLaz/proveedores_cucher/main/img/cucher_mercados.png" alt="Cucher Mercados Logo">
        #     </div>
        # """, unsafe_allow_html=True)


        # st.sidebar.markdown("Configuración de Análisis")
        
        # Cargar proveedores
        if self.df_proveedores is None:
            with st.spinner("Cargando proveedores..."):
                self.df_proveedores = self.load_proveedores()
        
        # st.sidebar.markdown("### 🏪 Selección de Proveedor")
        proveedores = sorted(self.df_proveedores['proveedor'].dropna().unique())
        
        proveedor = st.sidebar.selectbox(
            "🏪 Selección de Proveedor:",
            options=proveedores,
            index=None,
            placeholder="Seleccionar proveedor..."
        )
        
        # st.sidebar.markdown("### 📅 Período de Análisis")
        
        # Opciones de rango predefinidas
        rango_opciones = {
            "Último mes": 30,
            "Últimos 3 meses": 90,
            "Últimos 6 meses": 180,
            "Último año": 365,
            "Personalizado": None
        }
        
        rango_seleccionado = st.sidebar.selectbox(
            "📅 Período de Análisis:",
            options=list(rango_opciones.keys()),
            index=2  # Por defecto últimos 6 meses
        )
        
        if rango_seleccionado == "Personalizado":
            col1, col2 = st.sidebar.columns(2)
            fecha_inicio = col1.date_input(
                "Desde:",
                value=datetime.now().date() - timedelta(days=180)
            )
            fecha_fin = col2.date_input(
                "Hasta:",
                value=datetime.now().date()
            )
        else:
            dias = rango_opciones[rango_seleccionado]
            fecha_fin = datetime.now().date()
            fecha_inicio = fecha_fin - timedelta(days=dias)
            st.sidebar.info(f"📅 **{rango_seleccionado}**\n\n{fecha_inicio} a {fecha_fin}")
        
        # Botón de análisis
        if st.sidebar.button("🔍 Realizar Análisis", type="primary", use_container_width=True):
            if not proveedor:
                st.sidebar.error("❌ Selecciona un proveedor")
            else:
                with st.spinner("🔄 Consultando datos..."):
                    df_tickets = self.query_bigquery_data(proveedor, fecha_inicio, fecha_fin)
                    if df_tickets is not None:
                        st.session_state.analysis_data = df_tickets
                        st.session_state.selected_proveedor = proveedor
                        st.rerun()
                    else:
                        st.sidebar.error("❌ No se encontraron datos para el período seleccionado")
        
        # Información del proveedor si está seleccionado
        if proveedor:
            st.sidebar.markdown("### 📊 Información del Proveedor")
            num_articulos = len(self.df_proveedores[self.df_proveedores['proveedor'] == proveedor])
            st.sidebar.metric("Artículos en catálogo", num_articulos)
        
        return proveedor, fecha_inicio, fecha_fin
    
    def show_main_dashboard(self):
        """Mostrar dashboard principal"""
        # Header
        st.markdown("""
        <div class="main-header">
            <h3>📈 Análisis por Proveedor</h1>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.analysis_data is None:
            st.info("👈 **Selecciona un proveedor en el panel lateral para comenzar el análisis**")
            
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
        """Mostrar resumen ejecutivo"""
        st.subheader(f"📈 Resumen Ejecutivo - {proveedor}")
        
        # KPIs principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "💰 Ventas Totales",
                f"${metrics['total_ventas']:,.0f}",
                delta=f"{metrics['margen_promedio']:.1f}% margen"
            )
        
        with col2:
            st.metric(
                "📈 Utilidad Total",
                f"${metrics['total_utilidad']:,.0f}",
                delta=f"${metrics['ticket_promedio']:,.0f} ticket prom."
            )
        
        with col3:
            st.metric(
                "🧾 Total Transacciones",
                f"{metrics['num_tickets']:,}",
                delta=f"{metrics['dias_con_ventas']} días activos"
            )
        
        with col4:
            st.metric(
                "📦 Cantidad Vendida",
                f"{metrics['total_cantidad']:,.0f}",
                delta=f"{metrics['productos_unicos']} productos únicos"
            )
        
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
        
        # Gráficas de resumen
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribución de ventas por día
            ventas_diarias = df.groupby('fecha')['precio_total'].sum().reset_index()
            fig = px.line(
                ventas_diarias, x='fecha', y='precio_total',
                title="📈 Evolución Diaria de Ventas",
                labels={'precio_total': 'Ventas ($)', 'fecha': 'Fecha'}
            )
            fig.update_traces(line_color='#2a5298', line_width=3)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top 5 productos
            top_productos = df.groupby('descripcion')['precio_total'].sum().nlargest(5).reset_index()
            top_productos['descripcion_corta'] = top_productos['descripcion'].str[:30]
            
            fig = px.bar(
                top_productos, x='precio_total', y='descripcion_corta',
                orientation='h',
                title="🏆 Top 5 Productos por Ventas",
                labels={'precio_total': 'Ventas ($)', 'descripcion_corta': 'Producto'}
            )
            fig.update_traces(marker_color='#28a745')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    def show_products_analysis(self, df):
        """Análisis detallado de productos"""
        st.subheader("🏆 Análisis Detallado de Productos")
        
        try:
            # Métricas de productos
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
            
            # Ordenar por ventas
            productos_stats = productos_stats.sort_values('Ventas', ascending=False)
            
            # Mostrar TOP productos
            st.markdown("### 📊 TOP 20 Productos")
            
            # Filtros para la tabla
            col1, col2 = st.columns([3, 1])
            with col2:
                orden_por = st.selectbox(
                    "Ordenar por:",
                    ["Ventas", "Utilidad", "Margen %", "Cantidad", "Participación %"]
                )
            
            productos_ordenados = productos_stats.sort_values(orden_por, ascending=False).head(20)
            
            # Formatear para mostrar
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

            # Gráficas de productos
            col1, col2 = st.columns(2)

            with col1:
                # Validar columnas requeridas
                required_cols = ['descripcion', 'Ventas', 'Margen %', 'Cantidad', 'Utilidad']
                missing_cols = [col for col in required_cols if col not in productos_stats.columns]
                if missing_cols:
                    st.error(f"❌ Faltan columnas para graficar: {missing_cols}")
                    st.stop()

                # Preprocesamiento seguro
                top_20 = productos_stats.head(20).copy().reset_index()
                top_20['producto_corto'] = top_20['descripcion'].astype(str).str[:30] + '...'

                # Asegurar que sean numéricos
                for col in ['Ventas', 'Margen %', 'Cantidad', 'Utilidad']:
                    top_20[col] = pd.to_numeric(top_20[col], errors='coerce')

                # Eliminar filas inválidas
                top_20.dropna(subset=['Ventas', 'Margen %', 'Cantidad'], inplace=True)

                # Evitar errores si no hay datos válidos
                if top_20.empty:
                    st.warning("⚠️ No hay datos válidos para mostrar el gráfico de productos.")
                else:
                    try:
                        fig = px.scatter(
                            top_20,
                            x='Ventas',
                            y='Margen %',
                            size='Cantidad',
                            hover_name='producto_corto',
                            hover_data={'Utilidad': ':.0f'},
                            title="💹 Ventas vs Margen (TOP 20)",
                            labels={'Ventas': 'Ventas ($)', 'Margen %': 'Margen (%)'}
                        )
                        fig.update_traces(marker=dict(opacity=0.7))
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"❌ Error al generar el gráfico: {e}")



            # # Gráficas de productos
            # col1, col2 = st.columns(2)
            
            # with col1:
            #     # Scatter plot Ventas vs Margen - CORREGIDO
            #     top_20 = productos_stats.head(20).reset_index()
            #     top_20['producto_corto'] = top_20['descripcion'].str[:30] + '...'
                
            #     fig = px.scatter(
            #         top_20,
            #         x='Ventas', 
            #         y='Margen %',
            #         size='Cantidad',
            #         hover_name='producto_corto',
            #         hover_data={'Utilidad': ':,.0f'},
            #         title="💹 Ventas vs Margen (TOP 20)",
            #         labels={'Ventas': 'Ventas ($)', 'Margen %': 'Margen (%)'}
            #     )
            #     fig.update_traces(marker=dict(opacity=0.7))
            #     st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Análisis de Pareto
                productos_pareto = productos_stats.head(20)
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
                
                fig.update_layout(title_text="📈 Análisis de Pareto - Concentración de Ventas")
                fig.update_xaxes(title_text="Ranking de Productos")
                fig.update_yaxes(title_text="Participación Individual (%)", secondary_y=False)
                fig.update_yaxes(title_text="Participación Acumulada (%)", secondary_y=True)
                
                st.plotly_chart(fig, use_container_width=True)
                
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
            fig = px.line(
                mensual, x='mes_año', y='precio_total',
                title="📈 Evolución Mensual de Ventas",
                markers=True
            )
            fig.update_traces(line_color='#2a5298', line_width=4, marker_size=8)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.line(
                mensual, x='mes_año', y='margen_porcentual',
                title="📊 Evolución del Margen Promedio",
                markers=True
            )
            fig.update_traces(line_color='#28a745', line_width=4, marker_size=8)
            fig.update_yaxes(tickformat='.1f', ticksuffix='%')
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
                fig = px.bar(
                    semanal, x='dia_semana_es', y='precio_total',
                    title="📊 Ventas por Día de la Semana",
                    color='precio_total',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    semanal, x='dia_semana_es', y='margen_porcentual',
                    title="📈 Margen por Día de la Semana",
                    color='margen_porcentual',
                    color_continuous_scale='Greens'
                )
                fig.update_yaxes(tickformat='.1f', ticksuffix='%')
                st.plotly_chart(fig, use_container_width=True)
        
        # Tabla resumen mensual
        st.markdown("### 📋 Resumen Mensual")
        
        mensual_display = mensual.copy()
        mensual_display.columns = ['Mes', 'Ventas', 'Utilidad', 'Cantidad', 'Margen %', 'Tickets']
        
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
        """Análisis avanzado"""
        st.subheader("🎯 Análisis Avanzado")
        
        # Análisis por familia de productos
        if 'familia' in df.columns and df['familia'].notna().any():
            st.markdown("### 🌿 Análisis por Familia de Productos")
            
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
                    title="🥧 Distribución de Ventas por Familia"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    x=familia_stats.index,
                    y=familia_stats['margen_porcentual'],
                    title="📊 Margen por Familia de Productos",
                    color=familia_stats['margen_porcentual'],
                    color_continuous_scale='RdYlGn'
                )
                fig.update_yaxes(tickformat='.1f', ticksuffix='%')
                st.plotly_chart(fig, use_container_width=True)
        
        # Análisis por sucursal
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
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                fig = px.pie(
                    values=sucursal_stats['precio_total'],
                    names=sucursal_stats.index,
                    title="🏪 Ventas por Sucursal"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    x=sucursal_stats.index,
                    y=sucursal_stats['margen_porcentual'],
                    title="📈 Margen por Sucursal",
                    color=sucursal_stats['margen_porcentual'],
                    color_continuous_scale='Viridis'
                )
                fig.update_yaxes(tickformat='.1f', ticksuffix='%')
                st.plotly_chart(fig, use_container_width=True)
            
            with col3:
                # Scatter Tickets vs Ventas por Sucursal - CORREGIDO
                sucursal_reset = sucursal_stats.reset_index()
                sucursal_reset.rename(columns={'sucursal': 'Sucursal'}, inplace=True)
                
                fig = px.scatter(
                    sucursal_reset,
                    x='tickets',
                    y='precio_total',
                    size='margen_porcentual',
                    hover_name='Sucursal',
                    title="🎯 Tickets vs Ventas por Sucursal",
                    labels={'tickets': 'Número de Tickets', 'precio_total': 'Ventas ($)'}
                )
                fig.update_traces(marker=dict(opacity=0.7))
                st.plotly_chart(fig, use_container_width=True)
        
        # Matriz de análisis ABC
        st.markdown("### 📊 Análisis ABC de Productos")
        
        productos_abc = df.groupby(['idarticulo', 'descripcion']).agg({
            'precio_total': 'sum',
            'utilidad': 'sum'
        }).sort_values('precio_total', ascending=False)
        
        # Calcular categorías ABC
        productos_abc['participacion_acum'] = (productos_abc['precio_total'].cumsum() / productos_abc['precio_total'].sum() * 100)
        
        def categorizar_abc(participacion):
            if participacion <= 80:
                return 'A (Alto valor)'
            elif participacion <= 95:
                return 'B (Valor medio)'
            else:
                return 'C (Bajo valor)'
        
        productos_abc['categoria_abc'] = productos_abc['participacion_acum'].apply(categorizar_abc)
        
        # Contar productos por categoría
        abc_counts = productos_abc['categoria_abc'].value_counts()
        abc_ventas = productos_abc.groupby('categoria_abc')['precio_total'].sum()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                x=abc_counts.index,
                y=abc_counts.values,
                title="📈 Distribución de Productos ABC",
                labels={'x': 'Categoría', 'y': 'Cantidad de Productos'},
                color=abc_counts.values,
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.pie(
                values=abc_ventas.values,
                names=abc_ventas.index,
                title="💰 Participación de Ventas ABC"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Recomendaciones basadas en análisis
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
    
    def show_reports_section(self, df, proveedor, metrics):
        """Sección de reportes y exportación"""
        st.subheader("📁 Generación de Reportes")
        
        # Resumen para exportación
        st.markdown("### 📊 Resumen Ejecutivo")
        
        resumen_data = {
            'Métrica': [
                'Proveedor',
                'Período de Análisis',
                'Ventas Totales',
                'Utilidad Total',
                'Margen Promedio',
                'Total Transacciones',
                'Ticket Promedio',
                'Productos Únicos',
                'Días con Ventas'
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
                f"{metrics['dias_con_ventas']:,}"
            ]
        }
        
        df_resumen = pd.DataFrame(resumen_data)
        st.dataframe(df_resumen, use_container_width=True, hide_index=True)
        
        # Botones de exportación
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Exportar datos completos
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📊 Descargar Datos Completos (CSV)",
                data=csv_data,
                file_name=f"analisis_completo_{proveedor.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Exportar resumen ejecutivo
            resumen_csv = df_resumen.to_csv(index=False)
            st.download_button(
                label="📋 Descargar Resumen (CSV)",
                data=resumen_csv,
                file_name=f"resumen_ejecutivo_{proveedor.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col3:
            # Exportar top productos
            top_productos = df.groupby(['idarticulo', 'descripcion']).agg({
                'precio_total': 'sum',
                'utilidad': 'sum',
                'cantidad_total': 'sum',
                'margen_porcentual': 'mean'
            }).round(2).sort_values('precio_total', ascending=False).head(50)
            
            top_productos_csv = top_productos.to_csv()
            st.download_button(
                label="🏆 Descargar Top Productos (CSV)",
                data=top_productos_csv,
                file_name=f"top_productos_{proveedor.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Generar reporte en JSON
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
                'num_tickets': int(metrics['num_tickets'])
            },
            'insights': [insight[1] for insight in self.generate_insights(df, metrics)]
        }
        
        json_data = json.dumps(reporte_completo, indent=2, ensure_ascii=False)
        st.download_button(
            label="🗂️ Descargar Reporte Completo (JSON)",
            data=json_data,
            file_name=f"reporte_completo_{proveedor.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
        
        # Vista previa de datos
        st.markdown("### 👁️ Vista Previa de Datos")
        
        # Mostrar muestra de datos
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
            st.info(f"ℹ️ Mostrando las primeras 100 filas de {len(df):,} registros totales. Descarga el CSV completo para ver todos los datos.")
    
    def run(self):
        """Ejecutar dashboard"""
        # Sidebar con filtros
        proveedor, fecha_inicio, fecha_fin = self.show_sidebar_filters()
        
        # Dashboard principal
        self.show_main_dashboard()
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.8em;">
            🚀 Dashboard de Análisis Empresarial | Powered by Streamlit + BigQuery
        </div>
        """, unsafe_allow_html=True)

def main():
    """Función principal"""
    dashboard = ProveedorDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()