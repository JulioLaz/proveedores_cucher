"""
Componentes de análisis de presupuesto
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from analisis_quiebre import analizar_quiebre
from quiebre_streamlit_view import mostrar_analisis_quiebre_detallado


def show_presupuesto_estrategico(df):
    """
    Mostrar análisis estratégico de presupuesto
    """
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
        analisis_reposicion(df)

    with tabs[1]:
        analisis_presupuesto_sucursal(df)

    with tabs[2]:
        analisis_riesgo_quiebre(df)

    with tabs[3]:
        analisis_exceso_stock(df)

    with tabs[4]:
        analisis_estacionalidad(df)

    with tabs[5]:
        analisis_oportunidad_perdida(df)

    with tabs[6]:
        analisis_ajuste_precios(df)

    with tabs[7]:
        st.dataframe(df, width='stretch')


def analisis_reposicion(df):
    """Análisis de artículos a reponer"""
    df_reponer = df[df['cantidad_optima'] > 0].copy()
    st.subheader("🔄 Artículos a Reponer")
    st.metric("Costo Total de Reposición", f"${df_reponer['PRESUPUESTO'].sum():,.0f}")
    
    columnas = [
        "idarticulo", "descripcion", "cantidad_optima", "PRESUPUESTO",
        "stk_corrientes", "stk_express", "stk_formosa", "stk_hiper", 
        "stk_TIROL", "stk_central", "STK_TOTAL",
        "cor_abastecer", "exp_abastecer", "for_abastecer", 
        "hip_abastecer", "total_abastecer"
    ]
    st.dataframe(df_reponer[columnas], width='stretch')


def analisis_presupuesto_sucursal(df):
    """Análisis de presupuesto por sucursal"""
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
    df_costos["Presupuesto ($)"] = (
        pd.to_numeric(df_costos["Presupuesto ($)"], errors="coerce")
        .fillna(0).round(0).astype(int)
    )
    df_costos["texto"] = df_costos["Presupuesto ($)"].apply(lambda x: f"${x:,.0f}")
    df_costos = df_costos.sort_values(by="Presupuesto ($)", ascending=False)

    # Cantidad de artículos por sucursal
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

    # Gráficos
    col1, col2 = st.columns(2)

    with col1:
        fig1 = px.bar(
            df_costos, x="Sucursal", y="Presupuesto ($)", text="texto",
            title="💰 Presupuesto por Sucursal",
            color="Presupuesto ($)", color_continuous_scale="Reds"
        )
        fig1.update_traces(textposition="outside")
        fig1.update_layout(
            showlegend=False, coloraxis_showscale=False,
            xaxis_title=None, yaxis_title=None,
            margin=dict(t=60, b=40, l=30, r=20)
        )
        fig1.update_yaxes(showticklabels=False)
        st.plotly_chart(fig1, width='stretch')

    with col2:
        fig2 = px.bar(
            df_cantidad, x="Sucursal", y="Artículos con Venta", text="texto",
            title="📦 Artículos con Venta Activa",
            color="Artículos con Venta", color_continuous_scale="Greens"
        )
        fig2.update_traces(textposition="outside")
        fig2.update_layout(
            showlegend=False, xaxis_title=None, yaxis_title=None,
            coloraxis_showscale=False, margin=dict(t=60, b=40, l=30, r=20)
        )
        fig2.update_yaxes(showticklabels=False)
        st.plotly_chart(fig2, width='stretch')


def analisis_riesgo_quiebre(df):
    """Análisis de riesgo de quiebre de stock"""
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### 📈 Análisis de Pérdidas Potenciales por Quiebre")

    with col2:
        st.markdown("""
            <style>
            div[data-testid="stRadio"] > label {
                justify-content: center;
            }
            </style>
        """, unsafe_allow_html=True)

        opcion_dias = st.radio(
            label="Seleccionar la cantidad de días a proyectar:",
            options=["7 días", "15 días", "30 días", "45 días"],
            index=2,
            horizontal=True
        )

    # Ajustar demanda según días seleccionados
    dias_dict = {"7 días": 7, "15 días": 15, "30 días": 30, "45 días": 45}
    dias_analisis = dias_dict[opcion_dias]
    multiplicador = dias_analisis / 33

    if "cantidad_optima_base_33d" not in df.columns:
        df["cantidad_optima_base_33d"] = df["cantidad_optima"]

    df["cantidad_optima"] = df["cantidad_optima_base_33d"] * multiplicador

    # Análisis detallado de quiebre
    df_quiebre = analizar_quiebre(df)
    mostrar_analisis_quiebre_detallado(df_quiebre)

    st.subheader("⚠️ Riesgo de Quiebre")
    
    # Mapeo de niveles de riesgo
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

    # Gráfico de distribución
    conteo = df_riesgo['nivel_riesgo'].value_counts().sort_values(ascending=True)
    colores = [riesgo_color[nivel] for nivel in conteo.index]

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

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("📊 Distribución del riesgo de quiebre")
        st.plotly_chart(fig, width='stretch')

    with col2:
        # Formatear columnas
        df_riesgo['cantidad_optima'] = df_riesgo['cantidad_optima'].astype(int).map(lambda x: f"{x:,}")
        df_riesgo['dias_cobertura'] = df_riesgo['dias_cobertura'].map(lambda x: f"{x:.1f}")

        # Ordenar por nivel de riesgo
        orden_riesgo = ['🔴 Alto', '🟠 Medio', '🟡 Bajo', '🟢 Muy Bajo', '🔍 Analizar stk']
        df_riesgo['orden'] = df_riesgo['nivel_riesgo'].apply(lambda x: orden_riesgo.index(x))
        df_riesgo = df_riesgo.sort_values(by='orden').drop(columns='orden')

        columnas = ["idarticulo", "descripcion", "dias_cobertura", "nivel_riesgo", "cantidad_optima"]
        st.info(f"🔍 {len(df_riesgo)} artículos en riesgo de quiebre")
        st.dataframe(df_riesgo[columnas].head(300), width='stretch', hide_index=True)

    # Exportación
    csv = df_riesgo[columnas].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Riesgo de Quiebre", csv, "riesgo_quiebre.csv", "text/csv")


def analisis_exceso_stock(df):
    """Análisis de exceso de stock"""
    st.subheader("📦 Exceso de Stock")

    if df is None or df.empty:
        st.warning("⚠️ No hay datos disponibles para el análisis de exceso.")
        return

    # Filtrar artículos con exceso
    df_exceso = df[(df['exceso_STK'] > 0) & (df['dias_cobertura'] > 0)].copy()

    if df_exceso.empty:
        st.info("✅ No se detectaron artículos con exceso de stock.")
        return

    # Categorizar días de cobertura
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
    colores = ["#f1c40f", "#e67e22", "#e74c3c"]
    conteo = df_exceso["rango_cobertura"].value_counts().reindex(orden).fillna(0).astype(int)

    # Gráfico
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

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("📊 Distribución del exceso de stock por días de cobertura")
        st.plotly_chart(fig, width='stretch')

    with col2:
        # Formatear columnas
        df_exceso['exceso_STK_format'] = df_exceso['exceso_STK'].astype(int).map(lambda x: f"{x:,}")
        df_exceso['costo_exceso_STK_format'] = df_exceso['costo_exceso_STK'].map(lambda x: f"${x:,.0f}")
        df_exceso['dias_cobertura_format'] = df_exceso['dias_cobertura'].map(lambda x: f"{x:.0f}")

        # Ordenar por mayor costo
        df_exceso = df_exceso.sort_values(by='costo_exceso_STK', ascending=False)

        columnas = ["idarticulo", "descripcion", "exceso_STK_format", "costo_exceso_STK_format", "dias_cobertura_format"]
        st.markdown(f"📦 {len(df_exceso)} artículos con exceso de stock detectado")
        st.dataframe(df_exceso[columnas].head(300), width='stretch', hide_index=True)

    # Análisis detallado con scatter plot
    with st.expander("🔎 Visualizar Exceso por Impacto", expanded=True):
        _mostrar_analisis_exceso_detallado(df_exceso)

    # Exportar
    columnas_export = ["idarticulo", "descripcion", "exceso_STK", "costo_exceso_STK", "dias_cobertura"]
    df_export = df[df['exceso_STK'] > 0][columnas_export]
    csv = df_export.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Exceso de Stock", csv, "exceso_stock.csv", "text/csv")


def _mostrar_analisis_exceso_detallado(df_exceso):
    """Análisis detallado del exceso de stock"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 💥 Exceso de Stock: Cantidad vs Días de cobertura")
    
    with col2:
        total_costo = df_exceso["costo_exceso_STK"].sum()
        st.markdown(f"##### 💰 **Total inmovilizado en exceso:** `${total_costo:,.0f}`")

    df_top = df_exceso.sort_values("costo_exceso_STK", ascending=False).head(50).copy()

    # Validar columnas
    for col in ["costo_exceso_STK", "exceso_STK", "dias_cobertura"]:
        df_top[col] = pd.to_numeric(df_top[col], errors='coerce')

    df_top = df_top.dropna(subset=["costo_exceso_STK", "exceso_STK", "dias_cobertura"])

    if df_top.empty:
        st.warning("⚠️ No hay datos válidos para graficar el impacto del exceso.")
        return

    df_top["producto_corto"] = df_top["descripcion"].str[:40] + "..."

    # Scatter plot
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

    fig.update_traces(marker=dict(opacity=0.9, line=dict(width=1, color="gray")))
    fig.update_layout(
        height=600,
        title_x=0.05,
        margin=dict(t=60, b=20, l=10, r=10),
        legend_title_text="Cobertura",
        xaxis_type='log'
    )

    st.plotly_chart(fig, width='stretch')

    # Insights automáticos
    _generar_insights_exceso(df_top)

    # Análisis de Pareto
    _mostrar_pareto_exceso(df_top)


def _generar_insights_exceso(df_top):
    """Generar insights del exceso de stock"""
    st.markdown("### 📌 Insights Clave del Exceso de Stock")

    # Producto con mayor exceso
    top_exceso = df_top.loc[df_top["costo_exceso_STK"].idxmax()]
    st.markdown(f"""
    - 🔝 **Mayor inmovilizado:** El producto **{top_exceso['producto_corto']}** tiene el mayor exceso de stock con un valor de **${top_exceso['costo_exceso_STK']:,.0f}**, acumulando **{int(top_exceso['dias_cobertura'])} días** de cobertura y **{int(top_exceso['exceso_STK'])} unidades** excedentes.
    """)

    # Productos críticos por cobertura
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
    volumen_alto = df_top[(df_top["exceso_STK"] > 1000) & (df_top["dias_cobertura"] < 60)]
    if not volumen_alto.empty:
        st.markdown(f"""
        - 📦 **{len(volumen_alto)} productos presentan alto volumen excedente (>1.000 unidades) pero baja cobertura (<60 días)**. 
        Podrían redistribuirse a sucursales con mayor demanda para evitar saturación local.
        """)

    # Recomendaciones
    st.markdown("""
    ### ✅ Recomendaciones:
    - 🔄 Reasignar stock de productos con >90 días de cobertura hacia zonas de mayor rotación.
    - 🧼 Revisar precios y promociones para liquidar los productos con mayor inmovilizado.
    - 🔍 Evaluar estrategias de compra para evitar reincidencia de estos excesos.
    """)


def _mostrar_pareto_exceso(df_top):
    """Análisis de Pareto del exceso de stock"""
    pareto_exceso = df_top.sort_values("costo_exceso_STK", ascending=False).copy()
    pareto_exceso["Participación %"] = pareto_exceso["costo_exceso_STK"] / pareto_exceso["costo_exceso_STK"].sum() * 100
    pareto_exceso["ranking"] = range(1, len(pareto_exceso) + 1)
    pareto_exceso["descripcion_corta"] = pareto_exceso.apply(
        lambda row: f"{row['ranking']} - {row['producto_corto'][:14]}...", 
        axis=1
    )
    pareto_exceso["acumulado"] = pareto_exceso['Participación %'].cumsum()
    pareto_exceso["individual_fmt"] = pareto_exceso["Participación %"].map("{:.1f}%".format)
    pareto_exceso["acumulado_fmt"] = pareto_exceso["acumulado"].map("{:.0f}%".format)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Barras de participación individual
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

    # Línea de participación acumulada
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

    st.plotly_chart(fig, width='stretch')

    # Insight del Pareto
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


def analisis_estacionalidad(df):
    """Análisis de estacionalidad"""
    st.subheader("📆 Estacionalidad y Demanda")

    if df is None or df.empty:
        st.warning("⚠️ No hay datos para el análisis estacional.")
        return

    df_estacional = df.copy()
    df_estacional['Etiqueta Estacional'] = df_estacional['ranking_mes'].apply(
        lambda x: "📈 Mes Alto" if x >= 9 else ("📉 Mes Bajo" if x <= 4 else "Mes Intermedio")
    )

    # Mapeo de meses
    mes_map = {
        'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4,
        'may': 5, 'jun': 6, 'jul': 7, 'ago': 8,
        'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
    }

    df_estacional["mes_pico_num"] = df_estacional["mes_pico"].map(mes_map)

    # KPIs
    mes_actual = datetime.now().month
    en_temporada = df_estacional[df_estacional["mes_pico_num"] == mes_actual]
    total_temporada = len(en_temporada)

    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("📋 Artículos con análisis estacional", f"{len(df_estacional):,}")

    with col2:
        st.metric("📌 Productos en su mes pico actual", f"{total_temporada:,}")

    # Gráfico de distribución
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
        }
    )

    fig.update_traces(textposition='outside')
    fig.update_layout(showlegend=False, height=400)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.plotly_chart(fig, width='stretch')

    with col2:
        df_estacional['cantidad_optima'] = df_estacional['cantidad_optima'].astype(int).map(lambda x: f"{x:,}")
        df_estacional = df_estacional.sort_values(by="ranking_mes", ascending=False)
        columnas = ["idarticulo", "descripcion", "mes_pico", "mes_bajo", "ranking_mes", "Etiqueta Estacional", "cantidad_optima"]
        st.dataframe(df_estacional[columnas], width='stretch', hide_index=True)

    # Descargar CSV
    csv = df_estacional[columnas].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar CSV", csv, "analisis_estacionalidad.csv", "text/csv")


def analisis_oportunidad_perdida(df):
    """Análisis de oportunidad perdida"""
    st.subheader("📉 Valor Perdido por Falta de Stock")
    df_perdido = df[df['costo_exceso_STK'] > 0].copy()
    # Placeholder para análisis futuro


def analisis_ajuste_precios(df=None):
    """Análisis y propuesta de ajuste de precios"""
    st.subheader("💲 Propuesta de Ajuste de Precios")

    if df is None:
        df = st.session_state.get("resultados_data")

    if df is None or df.empty:
        st.warning("⚠️ No hay datos disponibles para el análisis de precios.")
        return

    # Columnas necesarias
    columnas_necesarias = [
        "idarticulo", "descripcion", "precio_actual", "costo_unit",
        "precio_optimo_ventas", "decision_precio", "pred_ventas_actual"
    ]

    df_reducido = df[columnas_necesarias].copy()
    df_reducido['decision_precio'] = df_reducido['decision_precio'].fillna('datos insuficientes')
    df_reducido['decision_precio'] = df_reducido['decision_precio'].replace('Modelo no confiable', 'datos insuficientes')

    # Conteo para gráfica
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
        st.info("📊 Distribución del análisis de variación de precios")
        st.plotly_chart(fig, width='stretch')

    with col2:
        df_final = df_reducido[df_reducido['decision_precio'].isin(['🔻 rebaja', '🔺 alza'])].copy()

        # Formatear columnas
        df_final['precio_actual'] = df_final['precio_actual'].map(lambda x: f"${x:,.2f}")
        df_final['costo_unit'] = df_final['costo_unit'].map(lambda x: f"${x:,.2f}")
        df_final['precio_optimo_ventas'] = df_final['precio_optimo_ventas'].map(lambda x: f"${x:,.2f}")
        df_final.rename(columns={"pred_ventas_actual": "venta para hoy"}, inplace=True)
        df_final["venta para hoy"] = df_final["venta para hoy"].astype(int)

        st.info(f"🎯 {len(df_final)} artículos con propuesta de cambio de precio")
        st.dataframe(df_final, width='stretch', hide_index=True)

    # Descargar CSV
    df_export = df_reducido[df_reducido['decision_precio'].isin(['🔻 rebaja', '🔺 alza'])]
    csv = df_export.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar CSV", csv, "ajuste_precios.csv", "text/csv")