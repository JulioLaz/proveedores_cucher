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

warnings.filterwarnings('ignore')

from limpiar_datos import limpiar_datos

def format_abbr(x):
                if x >= 1_000_000:
                    return f"${x/1_000_000:.1f}M"
                elif x >= 1_000:
                    return f"${x/1_000:.0f}K"
                else:
                    return f"${x:.0f}"

# === CONFIGURACION DE PAGINA ===
st.set_page_config(
    page_title="Proveedores",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === CSS PERSONALIZADO ===
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72, #2a5298);
        border-radius: 5px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 100;
    }
    .metric-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2a5298;
    }
    .insight-box {
        background: #f8f9fa !important;
        border: 1px solid #e9ecef !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        margin: 0.6rem 0 !important;
        border-left: 5px solid #17a2b8 !important;
        font-size: 0.93rem;
        line-height: 1.4;
        box-shadow: 0 2px 3px rgba(0, 0, 0, 0.04);
        transition: background 0.2s ease;
    }

    .warning-box {
        background: #fff8e1 !important;
        border: 1px solid #ffeaa7 !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        margin: 0.6rem 0 !important;
        border-left: 5px solid #ffc107 !important;
        font-size: 0.93rem;
        line-height: 1.4;
        box-shadow: 0 2px 3px rgba(0, 0, 0, 0.04);
    }

    .success-box {
        background: #e6f4ea !important;
        border: 1px solid #c3e6cb !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        margin: 0.6rem 0 !important;
        border-left: 5px solid #28a745 !important;
        font-size: 0.93rem;
        line-height: 1.4;
        box-shadow: 0 2px 3px rgba(0, 0, 0, 0.04);
    }

    .sidebar .sidebar-content {
        background: #f1f3f4;
        background: black;
    }

    /* 🎯 Estilo personalizado para el contenedor principal */
    .block-container {
        width: 100% !important;
        padding: .5rem 1rem !important;
        min-width: auto !important;
        max-width: initial !important;
    }
            
    /* Estilo personalizado al contenedor específico */
    .st-emotion-cache-16txtl3 {
        padding: 1rem 1rem !important;
    }
            
    /* Estilo personalizado al contenedor específico */
    /* Estilo personalizado al contenedor específico */
    .st-emotion-cache-595tnf {
            height: .5rem !important;
    }

    /* Estilo personalizado btn desplieque de sidebar */
    .st-emotion-cache-595tnf.eu6y2f94 {
        padding: 0.9rem !important;
    }            

    /* Ocultar el header superior de Streamlit */
    header {
        height: 2rem !important;
        min-height: 2rem !important;
        background-color: transparent !important;
        box-shadow: none !important;
        overflow: hidden !important;
        }

    /* ✅ Asegura que el botón de sidebar esté visible */
    [data-testid="collapsedControl"] {
        display: block !important;
        position: fixed !important;
        top: 1rem;
        left: 1rem;
        z-index: 1001;
    }
            
    /* 🎨 Establece un fondo beige claro para toda la app */
    body {
        background-color: #f5f5dc !important; /* beige */
    }

    /* O si querés solo el fondo del contenedor principal */
    .appview-container {
        background-color: #f5f5dc !important;
    }            


    /* Opcional: darle margen interno y borde a todo el gráfico */
    [data-testid="stPlotlyChart"] {
        border-radius: 10px;
        border: 1px solid #ddd;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .main-svg{
        background-color: transparent !important;
            }

    .metric-box {
        background-color: #e8f7fd;
        border-radius: 12px;
        padding: .5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 5px solid #2a5298;
        margin-bottom: .5rem;
    }
            
        @keyframes bounce {
            0%, 100% {
                transform: translateX(0);
            }
            50% {
                transform: translateX(-8px);
            }
        }

        .bounce-info {
            animation: bounce 1s infinite;
            font-weight: bold;
            color: #1e3c72;
            background-color: #e9f5ff;
            border-left: 6px solid #2a5298;
            padding: .5rem;
            border-radius: 8px;
            margin-top: .5rem;
            font-size: 1rem;
        }

        .st-cw {
        padding-top: 0rem !important;
        }

        .st-an {
            padding-top: 0rem !important;
        }            

        .sidebar-box {
            background-color: #ffffff10;
            padding: 1rem;
            border-radius: 10px;
            margin-top: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .sidebar-metric-title {
            font-size: 0.85rem;
            color: #555;
            margin-bottom: 0.2rem;
        }
        .sidebar-metric-value {
            font-size: 1.4rem;
            font-weight: bold;
            color: #1e3c72;
            margin-bottom: 0.8rem;
        }

        /* Estilo marrón vintage para el sidebar */
        section[data-testid="stSidebar"] {
            background-color: #dcc594 !important;  /* Marrón vintage */
            color: white;
            padding: 0rem !important;
        }

        /* Opcional: mejorar contraste en los textos del sidebar */
        section[data-testid="stSidebar"] .css-1cpxqw2, /* texto normal */
        section[data-testid="stSidebar"] .css-10trblm, /* encabezados */
        section[data-testid="stSidebar"] .st-emotion-cache-1wmy9hl {
            color: #fff !important;
        }
        #tabs-bui42-tabpanel-0 {
            padding-top: 0 !important;
        }            

</style>
""", unsafe_allow_html=True)
    # /* O si preferís que no tenga fondo visible: */
    # [data-testid="stPlotlyChart"] {
    # }          

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
            # 🔍 Limpieza final
            df = limpiar_datos(df)
            return df
            
        except Exception as e:
            st.error(f"Error consultando BigQuery: {e}")
            return None
    
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
        """Mostrar filtros en sidebar con animaciones y lógica UX mejorada"""
        # --- CSS & LOGO ---
        st.sidebar.markdown("""
            <style>
            .sidebar-logo-box img {
                max-width: 100%;
                border-radius: 8px;
                margin-bottom: 0.5rem;
            }

            .animated-title {
                font-weight: bold;
                color: #721c24;
                padding: 0.5rem 1rem;
            color: #1e3c72;
            background-color: #e9f5ff;
            border-left: 6px solid #2a5298;                            
                animation: pulse 1.5s infinite;
                border-radius: 5px;
                margin-bottom: .5rem;
            }

            .highlight-period {
                font-weight: bold;
                color: #856404;
                background: linear-gradient(90deg, #fff3cd, #ffeeba);
                padding: 0.5rem 1rem;
                border-left: 5px solid #ffc107;
                animation: blink 1.2s infinite;
                border-radius: 5px;
                margin-bottom: .5rem;
            }

            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.04); }
                100% { transform: scale(1); }
            }

            @keyframes blink {
                0% { opacity: 1; }
                50% { opacity: 0.6; }
                100% { opacity: 1; }
            }

            .stButton > button {
                background-color: #4368d6 !important;
                color: white !important;
                font-weight: bold;
                border-radius: 8px;
                border: none;
                padding: 0.6rem 1rem;
            }

            .stButton > button:hover {
                background-color: #294ebc !important;
            }
                            
            /* Oculta el label específico apuntando al selector detallado */
            #root > div:nth-child(1) > div.withScreencast > div > div.stAppViewContainer.appview-container.st-emotion-cache-1yiq2ps.e4man110 > section > div.hideScrollbar.st-emotion-cache-jx6q2s.eu6y2f92 > div.st-emotion-cache-ja5xo9.eu6y2f91 > div > div > div:nth-child(3) > div > label {
                display: none !important;
            }

            </style>
            <div class="sidebar-logo-box">
                <img src="https://raw.githubusercontent.com/JulioLaz/proveedores_cucher/main/img/cucher_mercados.png" alt="Cucher Mercados Logo">
            </div>
        """, unsafe_allow_html=True)

        # --- Cargar proveedores ---
        if self.df_proveedores is None:
            with st.spinner("Cargando proveedores..."):
                self.df_proveedores = self.load_proveedores()

        proveedores = sorted(self.df_proveedores['proveedor'].dropna().unique())
        proveedor_actual = st.session_state.get("selected_proveedor")
        
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
        if st.sidebar.button("Realizar Análisis", type="primary", use_container_width=True):
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

        return proveedor, fecha_inicio, fecha_fin
   
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
            # Crear gráfico de línea de ventas
            # Crear gráfico de línea de ventas con tooltip personalizado
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
            
            # with col1:
            #     fig = px.bar(
            #         semanal, x='dia_semana_es', y='precio_total',
            #         title="📊 Ventas por Día de la Semana",
            #         color='precio_total',
            #         color_continuous_scale='Blues'
            #     )
            #     st.plotly_chart(fig, use_container_width=True)
            
            # with col2:
            #     fig = px.bar(
            #         semanal, x='dia_semana_es', y='margen_porcentual',
            #         title="📈 Margen por Día de la Semana",
            #         color='margen_porcentual',
            #         color_continuous_scale='Greens'
            #     )
            #     fig.update_yaxes(tickformat='.1f', ticksuffix='%')
            #     st.plotly_chart(fig, use_container_width=True)
        
        # Tabla resumen mensual
        st.markdown("### 📋 Resumen Mensual")
        
        mensual_display = mensual.copy()
        # mensual_display.columns = ['Mes', 'Ventas', 'Utilidad', 'Cantidad', 'Margen %', 'Tickets']
        mensual_display.rename(columns={
            "mes_año": "Mes",
            "precio_total": "Ventas",
            "utilidad": "Utilidad",
            "cantidad_total": "Cantidad",
            "margen_porcentual": "Margen %",
            "tickets": "Tickets"
        }, inplace=True)

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
            
         
#########################################################################

            with col3:
                # Scatter Tickets vs Ventas por Sucursal - CORREGIDO
                sucursal_reset = sucursal_stats.reset_index()
                sucursal_reset.rename(columns={'sucursal': 'Sucursal'}, inplace=True)

                # Validación defensiva
                cols = ['tickets', 'precio_total', 'margen_porcentual']
                sucursal_reset = sucursal_reset.dropna(subset=cols)

                for col in cols:
                    sucursal_reset[col] = pd.to_numeric(sucursal_reset[col], errors='coerce')

                # Eliminar valores negativos o no válidos
                sucursal_reset = sucursal_reset[
                    (sucursal_reset['tickets'] > 0) &
                    (sucursal_reset['precio_total'] > 0) &
                    (sucursal_reset['margen_porcentual'] > 0)
                ]

                # Aplicar winsorización para `size`
                if not sucursal_reset.empty:
                    mediana = sucursal_reset['margen_porcentual'].median()
                    percentil_95 = sucursal_reset['margen_porcentual'].quantile(0.95)
                    umbral_max = min(percentil_95, mediana * 2)
                    sucursal_reset['margen_plot'] = sucursal_reset['margen_porcentual'].clip(upper=umbral_max)

                    try:
                        fig = px.scatter(
                            sucursal_reset,
                            x='tickets',
                            y='precio_total',
                            size='margen_plot',
                            hover_name='Sucursal',
                            title="🎯 Tickets vs Ventas por Sucursal",
                            labels={'tickets': 'Número de Tickets', 'precio_total': 'Ventas ($)'}
                        )
                        fig.update_traces(marker=dict(opacity=0.7))

                        # 🚀 CORRECCIÓN CLAVE: evitar error de elementos duplicados
                        st.plotly_chart(fig, use_container_width=True, key="scatter_sucursal")
                    except Exception as e:
                        st.warning(f"⚠️ No se pudo generar el gráfico de dispersión: {e}")
                        st.dataframe(sucursal_reset)
                else:
                    st.info("⚠️ No hay datos válidos para el gráfico de sucursales.")

#########################################################################

                # sucursal_reset = sucursal_stats.reset_index()
                # sucursal_reset.rename(columns={'sucursal': 'Sucursal'}, inplace=True)
                
                # fig = px.scatter(
                #     sucursal_reset,
                #     x='tickets',
                #     y='precio_total',
                #     size='margen_porcentual',
                #     hover_name='Sucursal',
                #     title="🎯 Tickets vs Ventas por Sucursal",
                #     labels={'tickets': 'Número de Tickets', 'precio_total': 'Ventas ($)'}
                # )

#########################################################################


                # fig.update_traces(marker=dict(opacity=0.7))
                # st.plotly_chart(fig, use_container_width=True)
        
        
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
        # Sidebar con filtros (guardar en atributos de instancia)
        self.proveedor, self.fecha_inicio, self.fecha_fin = self.show_sidebar_filters()
        
        # Dashboard principal
        self.show_main_dashboard()
        
        # Footer
        # st.markdown("---")
        st.markdown("""
        <hr style="margin: 0; border: none; border-top: 1px solid #ccc;" />
        <div style="text-align: center; color: #666; font-size: 0.8em;margin-top: 20px;">
            Julio A. Lazarte    |    Científico de Datos & BI   |   Cucher Mercados
        </div>
        """, unsafe_allow_html=True)

def main():
    """Función principal"""
    dashboard = ProveedorDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()