"""
Dashboard principal de proveedores - Versión modularizada
"""
import streamlit as st
import pandas as pd
from babel.dates import format_date
from babel import Locale

# Imports de utilidades
from utils import (
    setup_credentials,
    PROVEEDOR_UNIFICADO,
    NOMBRES_UNIFICADOS,
    query_bigquery_tickets,
    query_resultados_idarticulo,
    load_proveedores_from_sheet,
    calculate_metrics,
    generate_insights
)

# Agregar estos imports al inicio del archivo
# Imports de componentes
from components.sidebar_filters import show_sidebar_filters
from components.executive_summary import show_executive_summary as render_executive_summary
from components.products_analysis import show_products_analysis as render_products_analysis
from components.temporal_analysis import show_temporal_analysis as render_temporal_analysis
from components.advanced_analysis import show_advanced_analysis as render_advanced_analysis
from components.global_dashboard import show_global_dashboard
from components.article_analysis import show_idarticulo_analysis
from components.executive_summary_detailed import show_executive_summary_best
from components.budget_analysis import show_presupuesto_estrategico

# Imports de funciones auxiliares
from generar_excel import generar_excel
from custom_css import custom_css

locale = Locale.parse('es_AR')


class ProveedorDashboard:
    """
    Dashboard principal para análisis de proveedores
    Versión simplificada y modularizada
    """
    
    def __init__(self):
        """Inicializar dashboard"""
        self.df_proveedores = None
        self.df_tickets = None
        self.config = setup_credentials()
        
        # Inicializar session state
        if 'analysis_data' not in st.session_state:
            st.session_state.analysis_data = None
        if 'selected_proveedor' not in st.session_state:
            st.session_state.selected_proveedor = None
    
    def load_proveedores(self):
        """Cargar datos de proveedores"""
        if self.df_proveedores is None:
            with st.spinner("Cargando proveedores..."):
                self.df_proveedores = load_proveedores_from_sheet(
                    self.config['sheet_id'],
                    self.config['sheet_name'],
                    PROVEEDOR_UNIFICADO,
                    NOMBRES_UNIFICADOS
                )
    
    def query_bigquery_data(self, proveedor, fecha_inicio, fecha_fin):
        """Consultar datos de BigQuery para un proveedor"""
        # Obtener IDs de artículos del proveedor
        ids = self.df_proveedores[
            self.df_proveedores['proveedor'] == proveedor
        ]['idarticulo'].dropna().astype(int).astype(str).unique()
        
        return query_bigquery_tickets(
            self.config['credentials_path'],
            self.config['project_id'],
            self.config['bigquery_table'],
            ids,
            fecha_inicio,
            fecha_fin
        )
    
    def query_presupuesto(self, idproveedor):
        """Consultar datos de presupuesto"""
        return query_resultados_idarticulo(
            self.config['credentials_path'],
            self.config['project_id'],
            idproveedor=idproveedor,
            proveedor_unificado=PROVEEDOR_UNIFICADO
        )
    
    def show_sidebar_filters(self):
        """Wrapper para mostrar filtros del sidebar"""
        self.load_proveedores()
        
        df_proveedor_ids = self.df_proveedores[['idproveedor', 'proveedor']]
        
        return show_sidebar_filters(
            self.df_proveedores,
            df_proveedor_ids,
            self.query_bigquery_data,
            self.query_presupuesto
        )
    
    def show_main_dashboard(self):
        """Mostrar dashboard principal"""
        proveedor = self.proveedor if hasattr(self, 'proveedor') else None
        
        # Header
        if proveedor:
            st.markdown(f"""
            <div class="main-header">
                <p style='padding:5px 0px; font-size:1.5rem; font-weight:semibold;'>
                    Proveedor: {proveedor}
                </p>
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
        
        # Si no hay datos, mostrar dashboard global
        if st.session_state.analysis_data is None:
            show_global_dashboard(
                df_proveedores=self.df_proveedores,
                query_function=query_resultados_idarticulo,
                credentials_path=self.config['credentials_path'],
                project_id=self.config['project_id'],
                bigquery_table=self.config['bigquery_table']
            )
            return
        
        # Botón volver
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← Dashboard Global", type="secondary", use_container_width=True):
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
        
        # Datos y métricas
        df = st.session_state.analysis_data
        df_presu = st.session_state.get('resultados_data')
        proveedor = st.session_state.selected_proveedor
        metrics = calculate_metrics(df)
        
        # Tabs principales
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📈 Resumen Ejecutivo",
            "🏆 Análisis de Productos",
            "📅 Evolución Temporal",
            "🎯 Análisis Avanzado",
            "📋 Síntesis Final",
            "🧮 Presupuesto"
        ])
        
        with tab1:
            render_executive_summary(df, proveedor, metrics)
        
        with tab2:
            try:
                from insight_ABC import generar_insight_pareto
                render_products_analysis(df, generar_insight_pareto)
            except ImportError:
                render_products_analysis(df)
        
        with tab3:
            render_temporal_analysis(df)
        
        with tab4:
            try:
                from insight_ABC import (
                    generar_insight_margen,
                    generar_insight_cantidad,
                    generar_insight_ventas,
                    generar_insight_abc_completo
                )
                render_advanced_analysis(
                    df, metrics,
                    generar_insight_margen_func=generar_insight_margen,
                    generar_insight_cantidad_func=generar_insight_cantidad,
                    generar_insight_ventas_func=generar_insight_ventas,
                    generar_insight_abc_completo_func=generar_insight_abc_completo
                )
            except ImportError:
                render_advanced_analysis(df, metrics)
        
        with tab5:
            self.show_executive_summary_best(df, proveedor, metrics)
        
        with tab6:
            if df_presu is not None:
               show_presupuesto_estrategico(df_presu)
            else:
                st.info("📊 No hay datos de presupuesto disponibles")
    
    def show_executive_summary_best(self, df, proveedor, metrics):
        """Síntesis ejecutiva completa"""
        # Importar el componente de síntesis si existe
        # Por ahora, mostrar mensaje simple
        st.info("🚧 Componente de síntesis en desarrollo")
        
        # Preview de datos
        st.markdown("### Vista Previa de Datos")
        df['fecha_fmt'] = df['fecha'].apply(
            lambda x: format_date(x, format="d MMMM y", locale=locale)
        )
        
        data = df[[
            'fecha_fmt', 'idarticulo', 'descripcion', 
            'precio_total', 'costo_total', 'utilidad', 
            'margen_porcentual', 'cantidad_total'
        ]].copy()
        
        st.dataframe(data.head(10), use_container_width=True)
    
    def run(self):
        """Ejecutar dashboard"""
        # Mostrar filtros y obtener selección
        self.proveedor, self.fecha_inicio, self.fecha_fin, df_presu = self.show_sidebar_filters()
        
        # Mostrar dashboard principal
        self.show_main_dashboard()