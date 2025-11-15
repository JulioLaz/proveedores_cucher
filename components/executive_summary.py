"""
Componente: Resumen Ejecutivo
Genera el dashboard de resumen ejecutivo con KPIs, insights y gráficos principales
Autor: Julio A. Lazarte
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px


# ============================================
# UTILIDADES
# ============================================

def format_abbr(x):
    """Formatea números en formato abreviado (K, M)"""
    if x >= 1_000_000: 
        return f"${x/1_000_000:.1f}M"
    elif x >= 1_000: 
        return f"${x/1_000:.0f}K"
    else: 
        return f"${x:.0f}"


def inject_custom_css():
    """Inyecta estilos CSS personalizados para el resumen ejecutivo"""
    st.markdown("""
    <style>
        /* Estilos para cajas de insights */
        .insight-box, .success-box, .warning-box {
            border-radius: 10px;
            padding: 1rem;
            margin: 0.5rem 0;
            font-size: 0.95rem;
            border-left: 6px solid #2a5298;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        
        .insight-box:hover, .success-box:hover, .warning-box:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
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
        
        /* Ocultar label específico de tabs */
        #tabs-bui171-tabpanel-1 > div > div:nth-child(1) > div.stColumn > div > div > div > label {
            display: none !important;
        }
        
        /* Estilos para métricas */
        .metric-box {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        
        .metric-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
    </style>
    """, unsafe_allow_html=True)


# ============================================
# GENERACIÓN DE INSIGHTS
# ============================================

def generate_insights(df, metrics):
    """
    Genera insights automáticos basados en los datos
    
    Args:
        df (DataFrame): DataFrame con los datos de tickets
        metrics (dict): Diccionario con métricas calculadas
    
    Returns:
        list: Lista de tuplas (tipo, mensaje) con los insights
    """
    insights = []
    
    # 1. Análisis de rentabilidad
    if metrics['margen_promedio'] > 30:
        insights.append((
            "success", 
            f"🎯 Excelente rentabilidad: {metrics['margen_promedio']:.1f}% de margen promedio"
        ))
    elif metrics['margen_promedio'] > 20:
        insights.append((
            "info", 
            f"📈 Buena rentabilidad: {metrics['margen_promedio']:.1f}% de margen promedio"
        ))
    else:
        insights.append((
            "warning", 
            f"⚠️ Margen bajo: {metrics['margen_promedio']:.1f}% - Revisar estrategia de precios"
        ))
    
    # 2. Análisis de productos
    top_producto = df.groupby('descripcion')['precio_total'].sum().nlargest(1)
    if len(top_producto) > 0:
        producto_name = top_producto.index[0]
        producto_ventas = top_producto.iloc[0]
        participacion = (producto_ventas / metrics['total_ventas']) * 100
        insights.append((
            "info", 
            f"🏆 Producto estrella: {producto_name[:50]}... ({participacion:.1f}% de ventas)"
        ))
    
    # 3. Análisis temporal
    if len(df) > 7:  # Suficientes días para análisis
        ventas_por_dia = df.groupby('fecha')['precio_total'].sum()
        tendencia_dias = 7
        if len(ventas_por_dia) >= tendencia_dias:
            ultimos_dias = ventas_por_dia.tail(tendencia_dias).mean()
            primeros_dias = ventas_por_dia.head(tendencia_dias).mean()
            if ultimos_dias > primeros_dias * 1.1:
                insights.append((
                    "success", 
                    f"📈 Tendencia positiva: +{((ultimos_dias/primeros_dias-1)*100):.1f}% en últimos días"
                ))
            elif ultimos_dias < primeros_dias * 0.9:
                insights.append((
                    "warning", 
                    f"📉 Tendencia bajista: {((ultimos_dias/primeros_dias-1)*100):.1f}% en últimos días"
                ))
    
    # 4. Análisis de diversificación
    if metrics['productos_unicos'] < 5:
        insights.append((
            "warning", 
            "🎯 Baja diversificación de productos - Considerar ampliar catálogo"
        ))
    elif metrics['productos_unicos'] > 20:
        insights.append((
            "success", 
            f"🌟 Excelente diversificación: {metrics['productos_unicos']} productos únicos"
        ))
    
    # 5. Análisis de ticket promedio
    if metrics['ticket_promedio'] > 5000:
        insights.append((
            "success", 
            f"💰 Alto valor por transacción: ${metrics['ticket_promedio']:,.0f}"
        ))
    elif metrics['ticket_promedio'] < 1000:
        insights.append((
            "info", 
            "💡 Oportunidad de cross-selling para aumentar ticket promedio"
        ))
    
    # 6. Análisis de cobertura de sucursales
    if metrics['sucursales'] >= 4:
        insights.append((
            "success", 
            f"🏪 Excelente cobertura: Presente en {metrics['sucursales']} sucursales"
        ))
    elif metrics['sucursales'] <= 2:
        insights.append((
            "info", 
            f"🔍 Oportunidad de expansión: Solo {metrics['sucursales']} sucursales activas"
        ))
    
    return insights


# ============================================
# COMPONENTES DE KPIs
# ============================================

def render_kpi_card(icon, label, value, subtitle, color="green"):
    """
    Renderiza una tarjeta KPI individual
    
    Args:
        icon (str): Emoji del icono
        label (str): Etiqueta del KPI
        value (str): Valor formateado
        subtitle (str): Subtítulo o métrica secundaria
        color (str): Color del subtítulo
    """
    st.markdown(f"""
    <div class="metric-box">
        <div style="text-align: center;">
            <div style="font-size: 1rem; color: #555;">{icon} {label}</div>
            <div style="font-size: 1rem; font-weight: bold; color: #1e3c72;">{value}</div>
        </div>
        <div style="color: {color}; font-size: 0.8rem; margin-top: 0.2rem;">
            {subtitle}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_main_kpis(metrics):
    """
    Renderiza los KPIs principales en tarjetas
    
    Args:
        metrics (dict): Diccionario con métricas calculadas
    """
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        render_kpi_card(
            icon="💰",
            label="Ventas Totales",
            value=f"${metrics['total_ventas']:,.0f}",
            subtitle=f"⬆️ {metrics['margen_promedio']:.1f}% margen"
        )
    
    with col2:
        render_kpi_card(
            icon="📈",
            label="Utilidad Total",
            value=f"${metrics['total_utilidad']:,.0f}",
            subtitle=f"⬆️ ${metrics['ticket_promedio']:,.0f} ticket prom."
        )
    
    with col3:
        render_kpi_card(
            icon="📦",
            label="Cantidad Vendida",
            value=f"{metrics['total_cantidad']:,.0f}",
            subtitle=f"⬆️ {metrics['productos_unicos']} productos únicos"
        )
    
    with col4:
        render_kpi_card(
            icon="📅",
            label="Días con Ventas",
            value=f"{metrics['dias_con_ventas']}",
            subtitle="Período analizado",
            color="#888"
        )
    
    with col5:
        render_kpi_card(
            icon="🏪",
            label="Sucursales",
            value=metrics['sucursales_presentes'],
            subtitle="Presencia territorial",
            color="#888"
        )


# ============================================
# COMPONENTES DE INSIGHTS
# ============================================

def render_insights_grid(insights):
    """
    Renderiza los insights en una grilla de 2 columnas
    
    Args:
        insights (list): Lista de tuplas (tipo, mensaje)
    """
    if not insights:
        st.info("📊 No hay insights disponibles para este período")
        return
    
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
        
        # Crear nueva fila de columnas cada 2 insights
        if (idx + 1) % 2 == 0 and idx + 1 < len(insights):
            cols = st.columns(2)


# ============================================
# COMPONENTES DE GRÁFICOS
# ============================================

def render_sales_evolution_chart(df):
    """
    Renderiza el gráfico de evolución diaria de ventas con línea de tendencia
    
    Args:
        df (DataFrame): DataFrame con los datos de tickets
    """
    ventas_diarias = df.groupby('fecha')['precio_total'].sum().reset_index()
    
    # Calcular línea de tendencia
    ventas_diarias['fecha_ordinal'] = ventas_diarias['fecha'].map(pd.Timestamp.toordinal)
    coef = np.polyfit(ventas_diarias['fecha_ordinal'], ventas_diarias['precio_total'], 1)
    ventas_diarias['tendencia'] = coef[0] * ventas_diarias['fecha_ordinal'] + coef[1]
    ventas_diarias['precio'] = ventas_diarias['precio_total'].apply(format_abbr)
    
    # Crear gráfico
    fig = px.line(
        ventas_diarias,
        x='fecha',
        y='precio_total',
        custom_data=['precio'],
        title="📈 Evolución Diaria de Ventas",
        labels={'fecha': '', 'precio_total': 'Ventas'}
    )
    
    # Estilizar línea principal
    fig.update_traces(
        line_color='#2a5298',
        line_width=2,
        hovertemplate='<b>Fecha:</b> %{x}<br><b>Ventas:</b> %{customdata[0]}<extra></extra>'
    )
    
    # Agregar línea de tendencia
    fig.add_scatter(
        x=ventas_diarias['fecha'],
        y=ventas_diarias['tendencia'],
        mode='lines',
        line=dict(color='orange', width=1.5, dash='dash'),
        showlegend=False,
        hoverinfo='skip',
        name='Tendencia'
    )
    
    fig.update_layout(
        height=300,
        margin=dict(t=60, b=20, l=10, r=10),
        title_x=0.2,
        xaxis_title=None,
        yaxis_title=None,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_top_products_chart(df):
    """
    Renderiza el gráfico de top 5 productos por ventas
    
    Args:
        df (DataFrame): DataFrame con los datos de tickets
    """
    top_productos = (
        df.groupby('descripcion', as_index=False)['precio_total']
        .sum()
        .sort_values('precio_total', ascending=False)
        .head(5)
    )
    
    if top_productos.empty:
        st.warning("⚠️ No hay datos de productos disponibles")
        return
    
    top_productos['descripcion_corta'] = top_productos['descripcion'].str[:30]
    top_productos['precio'] = top_productos['precio_total'].apply(format_abbr)
    
    fig = px.bar(
        top_productos,
        x='precio_total',
        y='descripcion_corta',
        orientation='h',
        text='precio',
        custom_data=['precio'],
        title="🏆 Top 5 Productos por Ventas",
        labels={'precio_total': '', 'descripcion_corta': ''}
    )
    
    fig.update_yaxes(categoryorder='total ascending')
    
    # Estilizar barras
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
        title_x=0.2,
        xaxis_title=None,
        yaxis_title=None,
        xaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False
        )
    )
    
    st.plotly_chart(fig, use_container_width=True, key="top_productos_executive")


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def show_executive_summary(df, proveedor, metrics):
    """
    Muestra el resumen ejecutivo completo del proveedor
    
    Args:
        df (DataFrame): DataFrame con los datos de tickets
        proveedor (str): Nombre del proveedor
        metrics (dict): Diccionario con métricas calculadas
    
    Estructura del resumen:
        1. Estilos CSS personalizados
        2. KPIs principales (5 tarjetas)
        3. Insights automáticos (grilla 2 columnas)
        4. Gráficos de resumen (evolución + top productos)
    """
    
    # Validación de datos
    if df is None or df.empty:
        st.error("❌ No hay datos disponibles para mostrar el resumen ejecutivo")
        return
    
    if not metrics:
        st.error("❌ No se proporcionaron métricas para el resumen ejecutivo")
        return
    
    # 1. Inyectar estilos CSS
    inject_custom_css()
    
    # 2. Renderizar KPIs principales
    render_main_kpis(metrics)
    
    # 3. Generar y mostrar insights
    st.markdown("### 💡 Insights Clave")
    insights = generate_insights(df, metrics)
    render_insights_grid(insights)
    
    # 4. Mostrar gráficos de resumen
    st.markdown("### 📊 Visualizaciones Principales")
    col1, col2 = st.columns(2)
    
    with col1:
        render_sales_evolution_chart(df)
    
    with col2:
        render_top_products_chart(df)


# ============================================
# EXPORTAR FUNCIONES PÚBLICAS
# ============================================

__all__ = [
    'show_executive_summary',
    'generate_insights',
    'format_abbr'
]