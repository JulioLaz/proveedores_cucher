"""
Componente: Análisis Temporal
Análisis de evolución temporal de ventas, márgenes y tendencias
Autor: Julio A. Lazarte
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import io


# ============================================
# MAPEO DE DÍAS
# ============================================

DIA_MAPPING = {
    'Monday': 'Lunes',
    'Tuesday': 'Martes',
    'Wednesday': 'Miércoles',
    'Thursday': 'Jueves',
    'Friday': 'Viernes',
    'Saturday': 'Sábado',
    'Sunday': 'Domingo'
}

ORDEN_DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


# ============================================
# PROCESAMIENTO DE DATOS
# ============================================

def prepare_monthly_data(df):
    """
    Prepara datos agregados por mes
    
    Args:
        df (DataFrame): DataFrame con datos de tickets
    
    Returns:
        DataFrame: Datos mensuales agregados
    """
    mensual = df.groupby('mes_año').agg({
        'precio_total': 'sum',
        'utilidad': 'sum',
        'cantidad_total': 'sum',
        'margen_porcentual': 'mean'
    }).round(2)
    
    mensual['tickets'] = df.groupby('mes_año').size()
    mensual = mensual.reset_index()
    
    return mensual


def prepare_weekly_data(df):
    """
    Prepara datos agregados por día de la semana
    
    Args:
        df (DataFrame): DataFrame con datos de tickets
    
    Returns:
        DataFrame: Datos semanales agregados (ordenados correctamente)
    """
    # Mapear días a español
    df['dia_semana_es'] = df['dia_semana'].map(DIA_MAPPING)
    
    # Agregar por día
    semanal = df.groupby('dia_semana_es').agg({
        'precio_total': 'sum',
        'utilidad': 'sum',
        'margen_porcentual': 'mean'
    }).round(2)
    
    # Ordenar días correctamente
    semanal = semanal.reindex([dia for dia in ORDEN_DIAS if dia in semanal.index])
    semanal = semanal.reset_index()
    
    return semanal


# ============================================
# GRÁFICOS MENSUALES
# ============================================

def render_monthly_sales_chart(mensual):
    """
    Renderiza gráfico de evolución mensual de ventas
    
    Args:
        mensual (DataFrame): Datos mensuales agregados
    """
    mensual["ventas_fmt"] = mensual["precio_total"].apply(lambda x: f"{x/1e6:.1f} M")

    fig = px.line(
        mensual,
        x='mes_año',
        y='precio_total',
        text='ventas_fmt',
        title="📈 Evolución Mensual de Ventas",
        markers=True
    )

    fig.update_traces(
        line_color='#2a5298',
        line_width=2,
        marker_size=8,
        textposition="top center"
    )
    
    fig.update_layout(
        title_font=dict(size=18, color='#454448', family='Arial Black'),
        title_x=0.15,
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(t=70, b=40, l=30, r=20),
        hovermode='x unified'
    )
    
    fig.update_yaxes(showticklabels=False)
    st.plotly_chart(fig, use_container_width=True)


def render_monthly_margin_chart(mensual):
    """
    Renderiza gráfico de evolución mensual del margen
    
    Args:
        mensual (DataFrame): Datos mensuales agregados
    """
    mensual["margen_fmt"] = mensual["margen_porcentual"].map("{:.1f}%".format)

    fig = px.line(
        mensual,
        x='mes_año',
        y='margen_porcentual',
        text='margen_fmt',
        title="📊 Evolución del Margen Promedio",
        markers=True
    )

    fig.update_traces(
        line_color='#28a745',
        line_width=2,
        marker_size=8,
        textposition="top center"
    )
    
    fig.update_layout(
        title_font=dict(size=18, color='#454448', family='Arial Black'),
        title_x=0.15,
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(t=70, b=40, l=30, r=20),
        hovermode='x unified'
    )
    
    fig.update_yaxes(showticklabels=False)
    st.plotly_chart(fig, use_container_width=True)


# ============================================
# GRÁFICOS SEMANALES
# ============================================

def render_weekly_sales_chart(semanal):
    """
    Renderiza gráfico de ventas por día de la semana
    
    Args:
        semanal (DataFrame): Datos semanales agregados
    """
    semanal["ventas_fmt"] = semanal["precio_total"].apply(lambda x: f"${x/1e6:.1f}M")

    fig = px.bar(
        semanal,
        x='dia_semana_es',
        y='precio_total',
        text='ventas_fmt',
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
        coloraxis_showscale=False
    )

    fig.update_yaxes(showticklabels=False)
    st.plotly_chart(fig, use_container_width=True)


def render_weekly_margin_chart(semanal):
    """
    Renderiza gráfico de margen por día de la semana
    
    Args:
        semanal (DataFrame): Datos semanales agregados
    """
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


# ============================================
# TABLA RESUMEN
# ============================================

def inject_table_css():
    """Inyecta estilos CSS para la tabla de resumen"""
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
            font-weight: bold;
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
        tr:hover {
            background-color: #f5f5f5;
        }
    </style>
    """, unsafe_allow_html=True)


def render_monthly_summary_table(mensual):
    """
    Renderiza tabla resumen mensual con opción de descarga
    
    Args:
        mensual (DataFrame): Datos mensuales agregados
    """
    # Preparar datos para display
    mensual_display = mensual.copy()
    mensual_display.rename(columns={
        "mes_año": "Mes",
        "precio_total": "Ventas",
        "utilidad": "Utilidad",
        "cantidad_total": "Cantidad",
        "margen_porcentual": "Margen %"
    }, inplace=True)

    mensual_display = mensual_display[["Mes", "Ventas", "Utilidad", "Cantidad", "Margen %"]]

    # Formatear valores
    mensual_display["Ventas"] = mensual_display["Ventas"].apply(lambda x: f"${x:,.0f}")
    mensual_display["Utilidad"] = mensual_display["Utilidad"].apply(lambda x: f"${x:,.0f}")
    mensual_display["Cantidad"] = mensual_display["Cantidad"].apply(lambda x: f"{x:,.0f}")
    mensual_display["Margen %"] = mensual_display["Margen %"].map("{:.1f}%".format)

    # Header con botón de descarga
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown("### 📋 Resumen Mensual")
    with col2:
        # Convertir a CSV
        csv_buffer = io.StringIO()
        mensual_display.to_csv(csv_buffer, index=False)
        st.download_button(
            label="⬇️ CSV",
            data=csv_buffer.getvalue(),
            file_name="resumen_mensual.csv",
            mime="text/csv"
        )

    # Inyectar estilos CSS
    inject_table_css()

    # Mostrar tabla HTML
    html = mensual_display.to_html(index=False, escape=False)
    st.markdown(html, unsafe_allow_html=True)


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def show_temporal_analysis(df):
    """
    Muestra análisis completo de evolución temporal
    
    Args:
        df (DataFrame): DataFrame con datos de tickets
    
    Estructura:
        1. Análisis mensual (ventas y margen)
        2. Análisis por día de la semana (si disponible)
        3. Tabla resumen mensual con descarga
    """
    # Validar datos
    if df is None or df.empty:
        st.error("❌ No hay datos disponibles para el análisis temporal")
        return

    st.subheader("📅 Análisis de Evolución Temporal")
    
    # 1. Preparar datos mensuales
    mensual = prepare_monthly_data(df)
    
    # 2. Gráficos mensuales
    col1, col2 = st.columns(2)
    
    with col1:
        render_monthly_sales_chart(mensual)
    
    with col2:
        render_monthly_margin_chart(mensual)
    
    # 3. Análisis por día de la semana (si disponible)
    if 'dia_semana' in df.columns:
        st.markdown("### 📅 Análisis por Día de la Semana")
        
        semanal = prepare_weekly_data(df)
        
        col1, col2 = st.columns(2)
        
        with col1:
            render_weekly_sales_chart(semanal)
        
        with col2:
            render_weekly_margin_chart(semanal)
    
    # 4. Tabla resumen mensual
    render_monthly_summary_table(mensual)


# ============================================
# EXPORTAR FUNCIONES PÚBLICAS
# ============================================

__all__ = [
    'show_temporal_analysis',
    'prepare_monthly_data',
    'prepare_weekly_data'
]