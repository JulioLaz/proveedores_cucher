"""
Componente: Resumen Ejecutivo
Genera el dashboard de resumen ejecutivo con KPIs y gráficos principales
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime


def format_abbr(x):
    """Formatea números en formato abreviado (K, M)"""
    if x >= 1_000_000: 
        return f"${x/1_000_000:.1f}M"
    elif x >= 1_000: 
        return f"${x/1_000:.0f}K"
    else: 
        return f"${x:.0f}"


def show_executive_summary(df, proveedor, metrics):
    """
    Muestra el resumen ejecutivo del proveedor
    
    Args:
        df (DataFrame): DataFrame con los datos de tickets
        proveedor (str): Nombre del proveedor
        metrics (dict): Diccionario con métricas calculadas
    """
    
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
    </style>
    """, unsafe_allow_html=True)

    # === KPIs principales ===
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

    # === Gráficas de resumen ===
    col1, col2 = st.columns(2)

    # === Evolución Diaria de Ventas ===
    with col1:
        ventas_diarias = df.groupby('fecha')['precio_total'].sum().reset_index()
        ventas_diarias['fecha_ordinal'] = ventas_diarias['fecha'].map(pd.Timestamp.toordinal)
        coef = np.polyfit(ventas_diarias['fecha_ordinal'], ventas_diarias['precio_total'], 1)
        ventas_diarias['tendencia'] = coef[0] * ventas_diarias['fecha_ordinal'] + coef[1]
        ventas_diarias['precio'] = ventas_diarias['precio_total'].apply(format_abbr)

        fig = px.line(
            ventas_diarias,
            x='fecha',
            y='precio_total',
            custom_data=['precio'],
            title="📈 Evolución Diaria de Ventas",
            labels={'fecha': '', 'precio_total': 'Ventas'}
        )

        fig.update_traces(
            line_color='#2a5298',
            line_width=1,
            hovertemplate='<b>Fecha:</b> %{x}<br><b>Ventas:</b> %{customdata[0]}<extra></extra>'
        )

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
            custom_data=['precio'],
            title="🏆 Top 5 Productos por Ventas",
            labels={'precio_total': '', 'descripcion_corta': ''}
        )
        fig.update_yaxes(categoryorder='total ascending')

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

        st.plotly_chart(fig, use_container_width=True, key="top_productos")