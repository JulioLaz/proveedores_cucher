"""
Componente: Análisis de Productos
Análisis detallado de productos con múltiples visualizaciones y métricas
Autor: Julio A. Lazarte
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ============================================
# PROCESAMIENTO DE DATOS
# ============================================

def prepare_products_data(df):
    """
    Procesa y agrega datos por producto
    
    Args:
        df (DataFrame): DataFrame con datos de tickets
    
    Returns:
        DataFrame: Datos agregados por producto con métricas calculadas
    """
    productos_stats = df.groupby("descripcion").agg({
        "precio_total": "sum",
        "costo_total": "sum",
        "cantidad_total": "sum"
    }).reset_index()

    # Calcular métricas
    productos_stats["Utilidad"] = productos_stats["precio_total"] - productos_stats["costo_total"]
    productos_stats["Margen %"] = 100 * productos_stats["Utilidad"] / productos_stats["precio_total"].replace(0, pd.NA)
    productos_stats["Participación %"] = 100 * productos_stats["precio_total"] / productos_stats["precio_total"].sum()

    # Renombrar columnas
    productos_stats.rename(columns={
        "precio_total": "Ventas",
        "costo_total": "Costos",
        "cantidad_total": "Cantidad"
    }, inplace=True)

    return productos_stats


def get_top_products(productos_stats, orden_por, top_n=20):
    """
    Obtiene el top N de productos según métrica seleccionada
    
    Args:
        productos_stats (DataFrame): Datos de productos procesados
        orden_por (str): Métrica para ordenar
        top_n (int): Número de productos a retornar
    
    Returns:
        DataFrame: Top N productos ordenados
    """
    productos_top = productos_stats[productos_stats[orden_por].notna()].copy()
    productos_top = productos_top.sort_values(orden_por, ascending=False).head(top_n).copy()
    productos_top["Producto"] = productos_top["descripcion"].apply(
        lambda x: x[:40] + "..." if len(x) > 40 else x
    )
    return productos_top


# ============================================
# GRÁFICO PRINCIPAL - TOP PRODUCTOS
# ============================================

def render_top_products_chart(productos_top, orden_por):
    """
    Renderiza gráfico de barras con top productos
    
    Args:
        productos_top (DataFrame): Top productos a graficar
        orden_por (str): Métrica seleccionada
    """
    # Títulos según métrica
    titulo_dict = {
        "Ventas": f"Top {len(productos_top)} Productos por Ventas 💰",
        "Utilidad": f"Top {len(productos_top)} Productos por Utilidad 📈",
        "Margen %": f"Top {len(productos_top)} Productos por Margen (%) 🧮",
        "Cantidad": f"Top {len(productos_top)} Productos por Cantidad Vendida 📦",
        "Participación %": f"Top {len(productos_top)} por Participación (%) del Total 🧭"
    }

    # Crear gráfico
    fig = px.bar(
        productos_top,
        x="Producto",
        y=orden_por,
        text_auto='.2s' if orden_por in ["Ventas", "Utilidad"] else '.1f',
        title=titulo_dict[orden_por],
        labels={"Producto": "Producto", orden_por: orden_por}
    )

    # Configuración de layout según cantidad de productos
    angle = 0 if len(productos_top) < 8 else -45
    
    fig.update_layout(
        title_font=dict(size=22, color='#454448', family='Arial Black'),
        title_x=0.3,
        height=400,
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(t=60, b=10),
        xaxis_tickangle=angle,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False
        )
    )

    # Formato condicional para etiquetas
    if orden_por == "Cantidad":
        fig.update_traces(
            texttemplate='<b>%{y:,.0f}</b>',
            textfont=dict(size=14),
            textposition="outside"
        )
    elif orden_por in ["Ventas", "Utilidad"]:
        fig.update_traces(
            texttemplate='<b>$%{y:,.0f}</b>',
            textfont=dict(size=14),
            textposition="outside"
        )
    elif orden_por in ["Participación %", "Margen %"]:
        fig.update_traces(
            texttemplate='<b>%{y:.1f}%</b>',
            textfont=dict(size=14),
            textposition="outside"
        )

    fig.update_traces(marker_color='#8966c6')
   
   # Configurar hovertemplate según el caso
    if orden_por == "Cantidad":
      fig.update_traces(
         hovertemplate="<b>%{x}</b><br>Cantidad: %{y:,}<br>Ventas: $%{customdata[0]:,}<br>Utilidad: $%{customdata[1]:,}<extra></extra>"
      )
    elif orden_por in ["Ventas", "Utilidad"]:
      fig.update_traces(
         hovertemplate="<b>%{x}</b><br>$ %{y:,}<br>Cantidad: %{customdata[0]:,}<extra></extra>"
      )
    elif orden_por in ["Participación %", "Margen %"]:
      fig.update_traces(
         hovertemplate="<b>%{x}</b><br>%{y:.1f}%<br>Cantidad: %{customdata[0]:,}<extra></extra>"
      )

   # Mostrar gráfico en Streamlit
    st.plotly_chart(fig, use_container_width=True)

    # Advertencia si hay pocos productos
    if len(productos_top) < 5:
        st.warning(f"⚠️ Solo hay {len(productos_top)} productos disponibles con datos en '{orden_por}'.")


# ============================================
# GRÁFICO TOP 5 POR SUCURSAL
# ============================================

def render_top_products_by_branch(df, orden_por):
    """
    Renderiza gráfico de top 5 productos por sucursal
    
    Args:
        df (DataFrame): DataFrame original con datos
        orden_por (str): Métrica seleccionada
    """
    try:
        if "idarticulo" not in df.columns or "sucursal" not in df.columns:
            st.info("⚠️ No se encontraron columnas 'idarticulo' o 'sucursal' en el DataFrame.")
            return

        # Agrupar por sucursal e idarticulo
        df_top5 = (
            df.groupby(["sucursal", "idarticulo", "descripcion"])
            .agg({
                "precio_total": "sum",
                "costo_total": "sum",
                "cantidad_total": "sum"
            })
            .reset_index()
        )

        # Calcular métricas
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
            df.groupby("sucursal")["precio_total"]
            .sum()
            .sort_values(ascending=False)
            .index.tolist()
        )

        # Obtener top 5 artículos por sucursal
        df_top5 = df_top5[df_top5[orden_por].notna()]
        df_top5 = df_top5.sort_values(["sucursal", orden_por], ascending=[True, False])
        df_top5 = df_top5.groupby("sucursal").head(5).copy()

        # Preparar etiquetas
        df_top5["idarticulo"] = df_top5["idarticulo"].astype(str)
        df_top5["x_label"] = df_top5.apply(
            lambda row: f"<b>{row['idarticulo']}</b><br>"
                       f"<span style='font-size:11px'>{row['descripcion'][:20]}</span><br>"
                       f"<span style='font-size:10px; font-weight:bold'>{row['sucursal']}</span>",
            axis=1
        )

        # Crear gráfico
        titulo_top5 = f"Top {df_top5['idarticulo'].nunique()} ID Artículo por {orden_por} en cada Sucursal"

        fig = px.bar(
            df_top5,
            x="x_label",
            y=orden_por,
            color="sucursal",
            text_auto='.2s' if orden_por in ["Ventas", "Utilidad"] else '.1f',
            title=titulo_top5,
            labels={"x_label": "ID Artículo por Sucursal", orden_por: orden_por}
        )

        # Layout
        fig.update_layout(
            title_font=dict(size=20, color='#454448', family='Arial Black'),
            title_x=0.3,
            height=550,
            xaxis_title=None,
            yaxis_title=None,
            margin=dict(t=60, b=10),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            showlegend=False,
            yaxis=dict(
                showticklabels=False,
                showgrid=False,
                zeroline=False
            )
        )

        # Formato condicional
        if orden_por == "Cantidad":
            fig.update_traces(
                texttemplate='<b>%{y:,.0f}</b>',
                textfont=dict(size=14),
                textposition="outside"
            )
        elif orden_por in ["Ventas", "Utilidad"]:
            fig.update_traces(
                texttemplate='<b>$%{y:,.0f}</b>',
                textfont=dict(size=14),
                textposition="outside"
            )
        elif orden_por in ["Participación %", "Margen %"]:
            fig.update_traces(
                texttemplate='<b>%{y:.1f}%</b>',
                textfont=dict(size=14),
                textposition="outside"
            )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Error al generar la gráfica Top 5 por sucursal: {e}")


# ============================================
# SCATTER PLOT - VENTAS VS MARGEN
# ============================================

def render_sales_margin_scatter(productos_stats):
    """
    Renderiza gráfico de dispersión Ventas vs Margen
    
    Args:
        productos_stats (DataFrame): Datos de productos procesados
    """
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
        coloraxis_colorbar=dict(title='Cantidad'),
        margin=dict(t=60, b=20, l=10, r=10)
    )
    
    st.plotly_chart(fig, use_container_width=True)


# ============================================
# ANÁLISIS DE PARETO
# ============================================

def render_pareto_analysis(productos_stats):
    """
    Renderiza análisis de Pareto con concentración de ventas
    
    Args:
        productos_stats (DataFrame): Datos de productos procesados
    """
    productos_pareto = productos_stats.sort_values("Ventas", ascending=False).head(20).copy()
    productos_pareto["ranking"] = range(1, len(productos_pareto) + 1)
    productos_pareto["descripcion_corta"] = productos_pareto.apply(
        lambda row: f"{row['ranking']} - {row['descripcion'][:14]}...", 
        axis=1
    )
    productos_pareto["acumulado"] = productos_pareto['Participación %'].cumsum()
    productos_pareto["individual_fmt"] = productos_pareto["Participación %"].map("{:.1f}%".format)
    productos_pareto["acumulado_fmt"] = productos_pareto["acumulado"].map("{:.0f}%".format)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Barras
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

    # Línea acumulada
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
    
    return productos_pareto


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def show_products_analysis(df, generate_insight_pareto_func=None):
    """
    Muestra análisis completo de productos
    
    Args:
        df (DataFrame): DataFrame con datos de tickets
        generate_insight_pareto_func (callable): Función para generar insights de Pareto
    
    Estructura:
        1. Procesamiento de datos
        2. Selector de métrica y gráfico TOP 20
        3. Gráfico TOP 5 por sucursal
        4. Scatter plot Ventas vs Margen
        5. Análisis de Pareto
        6. Insights automáticos
    """
    try:
        # Validar datos
        if df is None or df.empty:
            st.error("❌ No hay datos disponibles para el análisis de productos")
            return

        # 1. Preparar datos
        productos_stats = prepare_products_data(df)

        # 2. Header con selector de métrica
        col1, col2 = st.columns([5, 1])
        with col1:
            st.subheader("🏆 Análisis Detallado de Productos - TOP 20")
        with col2:
            orden_por = st.selectbox(
                "",
                ["Ventas", "Utilidad", "Margen %", "Cantidad", "Participación %"]
            )

        # 3. Obtener top productos y graficar
        productos_top = get_top_products(productos_stats, orden_por, top_n=20)
        render_top_products_chart(productos_top, orden_por)

        # 4. Gráfico por sucursal
        render_top_products_by_branch(df, orden_por)

        # 5. Gráficos adicionales
        col1, col2 = st.columns(2)

        with col1:
            render_sales_margin_scatter(productos_stats)

        with col2:
            productos_pareto = render_pareto_analysis(productos_stats)

        # 6. Insights de Pareto (si se proporciona la función)
        if generate_insight_pareto_func and productos_pareto is not None:
            st.markdown(
                generate_insight_pareto_func(productos_pareto), 
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"❌ Error en análisis de productos: {str(e)}")
        st.info("💡 Intenta con un rango de fechas diferente o verifica los datos del proveedor.")


# ============================================
# EXPORTAR FUNCIONES PÚBLICAS
# ============================================

__all__ = [
    'show_products_analysis',
    'prepare_products_data',
    'get_top_products'
]