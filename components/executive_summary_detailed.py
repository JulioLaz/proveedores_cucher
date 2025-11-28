"""
Resumen ejecutivo completo con análisis integral
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from babel.dates import format_date
from babel import Locale
from generar_excel import generar_excel
from re import sub

locale = Locale.parse('es_AR')


def show_executive_summary_best(df, proveedor, metrics):
    """Resumen ejecutivo completo con análisis integral"""
    
    # Formatear fechas
    df['fecha_fmt'] = df['fecha'].apply(lambda x: format_date(x, format="d MMMM y", locale=locale))
    periodo_analisado = f"{df['fecha_fmt'].min()} al {df['fecha_fmt'].max()}"

    # Estilos CSS personalizados
    _inject_custom_css()

    # KPIs principales mejorados
    _show_main_kpis(df, metrics, periodo_analisado)

    # Análisis de Familias y Subfamilias
    st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
    _show_family_analysis(df, metrics)

    # Síntesis de Análisis Temporal
    st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
    _show_temporal_synthesis(df, metrics)

    # Síntesis Análisis ABC
    st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
    _show_abc_synthesis(df, metrics)

    # Análisis por Sucursal
    if 'sucursal' in df.columns and df['sucursal'].notna().any():
        st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
        _show_geographical_synthesis(df, metrics)

    # Insights Clave Automatizados
    st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
    _show_key_insights(df, metrics)

    # Recomendaciones Estratégicas
    st.markdown("""<hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />""", unsafe_allow_html=True)
    _show_strategic_recommendations(df, metrics)

    # Tabla Resumen Ejecutivo Final
    st.markdown("### 📋 Tabla Resumen Ejecutivo")
    _show_executive_table(df, proveedor, metrics, periodo_analisado)

    # Vista Previa de Datos y Descarga
    _show_data_preview(df, proveedor, periodo_analisado)


def _inject_custom_css():
    """Inyectar CSS personalizado"""
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
        .familia-item {
            background: #e9f5ff;
            padding: 0.3rem 0.8rem;
            margin: 0.2rem;
            border-radius: 15px;
            display: inline-block;
            font-size: 0.85rem;
            border: 1px solid #b3d9ff;
        }
    </style>
    """, unsafe_allow_html=True)


def _show_main_kpis(df, metrics, periodo_analisado):
    """Mostrar KPIs principales mejorados"""
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
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

    with col3:
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

    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 1rem; color: #555;">📅 Días con Ventas</div>
                <div style="font-size: 1.5rem; font-weight: bold; color: #1e3c72;">{metrics['dias_con_ventas']}</div>
            </div>
            <div style="color: #888; font-size: 0.8rem; margin-top: 0.2rem;text-align: center;">
                {periodo_analisado}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        familias_count = df['familia'].nunique() if 'familia' in df.columns else 0
        subfamilias_count = df['subfamilia'].nunique() if 'subfamilia' in df.columns else 0
        art_count = df['idarticulo'].nunique() if 'idarticulo' in df.columns else 0
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 1.15rem; color: #555;">🌿 Familias 
                    <span style="font-size: 1.15rem; font-weight: bold; color: #1e3c72">
                    {familias_count}
                    </span>
                </div>
                <div style="font-size: 1.15rem; color: #555;">🌿 SubFamilias 
                    <span style="font-size: 1.15rem; font-weight: bold; color: #1e3c72">
                    {subfamilias_count}
                    </span>
                </div>
                <div style="font-size: 1.15rem; color: #555;">🌿 Artículos 
                    <span style="font-size: 1.15rem; font-weight: bold; color: #1e3c72">
                    {art_count}
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 1rem; color: #555;">🏪 Sucursales</div>
                <div style="font-size: 1rem; color: #1e3c72; padding: .4rem 0rem">{metrics['sucursales_presentes']}</div>
            </div>
            <div style="color: #888; font-size: 0.8rem; margin-top: 0.2rem;">
                Presencia territorial
            </div>
        </div>
        """, unsafe_allow_html=True)


def _show_family_analysis(df, metrics):
    """Análisis de Familias y Subfamilias"""
    st.markdown("### 🧬 Análisis de Categorías de Productos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'familia' in df.columns and df['familia'].notna().any():
            familias_list = sorted(df['familia'].dropna().unique())
            familias_ventas = df.groupby('familia')['precio_total'].sum().sort_values(ascending=False)
            familia_principal = familias_ventas.index[0] if len(familias_ventas) > 0 else "N/A"
            
            st.markdown(f"""
            **🌿 Familias de Productos ({len(familias_list)})**
            - **Familia principal:** {familia_principal}
            - **Participación:** {(familias_ventas.iloc[0] / metrics['total_ventas'] * 100):.1f}% del total
            """)
            
            # Lista de familias
            familias_html = "".join([f'<span class="familia-item">{familia}</span>' for familia in familias_list[:8]])
            if len(familias_list) > 8:
                familias_html += f'<span class="familia-item">+{len(familias_list)-8} más...</span>'
            st.markdown(familias_html, unsafe_allow_html=True)

    with col2:
        if 'subfamilia' in df.columns and df['subfamilia'].notna().any():
            subfamilias_list = sorted(df['subfamilia'].dropna().unique())
            subfamilias_ventas = df.groupby('subfamilia')['precio_total'].sum().sort_values(ascending=False)
            subfamilia_principal = subfamilias_ventas.index[0] if len(subfamilias_ventas) > 0 else "N/A"
            
            st.markdown(f"""
            **🍃 Subfamilias de Productos ({len(subfamilias_list)})**
            - **Subfamilia principal:** {subfamilia_principal}
            - **Participación:** {(subfamilias_ventas.iloc[0] / metrics['total_ventas'] * 100):.1f}% del total
            """)
            
            # Lista de subfamilias
            subfamilias_html = "".join([f'<span class="familia-item">{subfam}</span>' for subfam in subfamilias_list[:8]])
            if len(subfamilias_list) > 8:
                subfamilias_html += f'<span class="familia-item">+{len(subfamilias_list)-8} más...</span>'
            st.markdown(subfamilias_html, unsafe_allow_html=True)


def _show_temporal_synthesis(df, metrics):
    """Síntesis de Análisis Temporal"""
    st.markdown("### 📅 Síntesis Temporal")
    
    # Análisis mensual
    df['mes_año'] = pd.to_datetime(df['fecha']).dt.to_period('M').astype(str)
    mensual = df.groupby('mes_año')['precio_total'].sum()
    mes_top = mensual.idxmax() if len(mensual) > 0 else "N/A"
    ventas_mes_top = mensual.max() if len(mensual) > 0 else 0
    
    # Análisis por día de semana
    dia_mapping = {
        'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
        'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    
    if 'dia_semana' in df.columns:
        df['dia_semana_es'] = df['dia_semana'].map(dia_mapping)
    else:
        df['dia_semana_es'] = pd.to_datetime(df['fecha']).dt.day_name().map(dia_mapping)
    
    semanal = df.groupby('dia_semana_es')['precio_total'].sum()
    dia_top = semanal.idxmax() if len(semanal) > 0 else "N/A"
    
    # Tendencia general
    if len(mensual) >= 3:
        valores = mensual.values
        tendencia_coef = np.polyfit(range(len(valores)), valores, 1)[0]
        tendencia_texto = "📈 Creciente" if tendencia_coef > 0 else "📉 Decreciente" if tendencia_coef < 0 else "➡️ Estable"
        tendencia_porcentaje = abs(tendencia_coef / valores.mean() * 100)
    else:
        tendencia_texto = "➡️ Período insuficiente"
        tendencia_porcentaje = 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        **📊 Mes Destacado**
        - **Período:** {mes_top}
        - **Ventas:** ${ventas_mes_top:,.0f}
        - **Participación:** {(ventas_mes_top / metrics['total_ventas'] * 100):.1f}%
        """)
    
    with col2:
        st.markdown(f"""
        **📅 Día Óptimo**
        - **Día:** {dia_top}
        - **Concentración:** {(semanal.max() / semanal.sum() * 100):.1f}%
        - **Promedio:** ${semanal.mean():,.0f}
        """)
    
    with col3:
        st.markdown(f"""
        **📈 Tendencia General**
        - **Dirección:** {tendencia_texto}
        - **Variación:** {tendencia_porcentaje:.1f}%
        - **Estabilidad:** {'Alta' if tendencia_porcentaje < 5 else 'Media' if tendencia_porcentaje < 15 else 'Baja'}
        """)


def _show_abc_synthesis(df, metrics):
    """Síntesis Análisis ABC"""
    st.markdown("### 🎯 Síntesis Análisis ABC")
    
    productos_abc = df.groupby(['idarticulo', 'descripcion']).agg({
        'precio_total': 'sum',
        'utilidad': 'sum'
    }).sort_values('precio_total', ascending=False)
    
    productos_abc['participacion_acum'] = (
        productos_abc['precio_total'].cumsum() /
        productos_abc['precio_total'].sum() * 100
    )
    
    def categorizar_abc(part):
        if part <= 80:
            return 'A'
        elif part <= 95:
            return 'B'
        else:
            return 'C'
    
    productos_abc['categoria_abc'] = productos_abc['participacion_acum'].apply(categorizar_abc)
    abc_counts = productos_abc['categoria_abc'].value_counts().sort_index()
    abc_ventas = productos_abc.groupby('categoria_abc')['precio_total'].sum().sort_index()
    
    # Diversificación
    concentracion_a = (abc_ventas.get('A', 0) / metrics['total_ventas'] * 100) if 'A' in abc_ventas else 0
    diversificacion = "Alta" if concentracion_a < 60 else "Media" if concentracion_a < 80 else "Baja"
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        productos_a = abc_counts.get('A', 0)
        st.markdown(f"""
        **🔥 Productos Clase A**
        - **Cantidad:** {productos_a} productos
        - **Concentración:** {concentracion_a:.1f}% ventas
        - **Impacto:** {'Crítico' if productos_a < 10 else 'Alto'}
        """)
    
    with col2:
        productos_b = abc_counts.get('B', 0)
        productos_c = abc_counts.get('C', 0)
        st.markdown(f"""
        **⚖️ Productos B y C**
        - **Clase B:** {productos_b} productos
        - **Clase C:** {productos_c} productos
        - **Complementarios:** {((abc_ventas.get('B', 0) + abc_ventas.get('C', 0)) / metrics['total_ventas'] * 100):.1f}%
        """)
    
    with col3:
        st.markdown(f"""
        **🎲 Diversificación**
        - **Nivel:** {diversificacion}
        - **Productos únicos:** {metrics['productos_unicos']}
        - **Riesgo:** {'Bajo' if diversificacion == 'Alta' else 'Medio' if diversificacion == 'Media' else 'Alto'}
        """)


def _show_geographical_synthesis(df, metrics):
    """Análisis por Sucursal"""
    st.markdown("### 🏪 Síntesis Geográfica")
    
    sucursal_stats = df.groupby('sucursal').agg({
        'precio_total': 'sum',
        'utilidad': 'sum',
        'margen_porcentual': 'mean'
    }).round(2)
    
    sucursal_top = sucursal_stats['precio_total'].idxmax()
    sucursal_top_ventas = sucursal_stats['precio_total'].max()
    sucursal_mejor_margen = sucursal_stats['margen_porcentual'].idxmax()
    margen_mejor = sucursal_stats['margen_porcentual'].max()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        **🏆 Sucursal Líder en Ventas**
        - **Sucursal:** {sucursal_top}
        - **Ventas:** ${sucursal_top_ventas:,.0f}
        - **Participación:** {(sucursal_top_ventas / metrics['total_ventas'] * 100):.1f}%
        """)
    
    with col2:
        st.markdown(f"""
        **💎 Sucursal Más Rentable**
        - **Sucursal:** {sucursal_mejor_margen}
        - **Margen:** {margen_mejor:.1f}%
        - **Eficiencia:** {'Excelente' if margen_mejor > 30 else 'Buena' if margen_mejor > 20 else 'Regular'}
        """)


def _show_key_insights(df, metrics):
    """Insights Clave Automatizados"""
    from utils import generate_insights
    
    insights = generate_insights(df, metrics)
    
    st.markdown("### 💡 Insights Clave del Período")
    
    # Separar insights por tipo
    insights_criticos = [insight for insight in insights if insight[0] == "warning"]
    insights_positivos = [insight for insight in insights if insight[0] == "success"]
    insights_informativos = [insight for insight in insights if insight[0] == "info"]
    
    if insights_criticos:
        st.markdown("**🚨 Puntos de Atención:**")
        for _, mensaje in insights_criticos[:2]:
            st.markdown(f'<div class="warning-box">{mensaje}</div>', unsafe_allow_html=True)
    
    if insights_positivos:
        st.markdown("**✅ Fortalezas Identificadas:**")
        for _, mensaje in insights_positivos[:2]:
            st.markdown(f'<div class="success-box">{mensaje}</div>', unsafe_allow_html=True)
    
    if insights_informativos:
        st.markdown("**📊 Información Relevante:**")
        for _, mensaje in insights_informativos[:2]:
            st.markdown(f'<div class="insight-box">{mensaje}</div>', unsafe_allow_html=True)


def _show_strategic_recommendations(df, metrics):
    """Recomendaciones Estratégicas Priorizadas"""
    st.markdown("### 🎯 Recomendaciones Estratégicas")
    
    recomendaciones = []
    
    # Análisis automático
    if metrics['margen_promedio'] < 20:
        recomendaciones.append(("🔴 CRÍTICO", f"Optimizar márgenes: {metrics['margen_promedio']:.1f}% está por debajo del mínimo recomendado (20%)"))
    
    # Concentración
    productos_abc = df.groupby(['idarticulo', 'descripcion']).agg({'precio_total': 'sum'}).sort_values('precio_total', ascending=False)
    productos_abc['participacion_acum'] = (productos_abc['precio_total'].cumsum() / productos_abc['precio_total'].sum() * 100)
    productos_abc['categoria_abc'] = productos_abc['participacion_acum'].apply(lambda x: 'A' if x <= 80 else 'B' if x <= 95 else 'C')
    abc_ventas = productos_abc.groupby('categoria_abc')['precio_total'].sum()
    concentracion_a = (abc_ventas.get('A', 0) / metrics['total_ventas'] * 100) if 'A' in abc_ventas else 0
    
    if concentracion_a > 80:
        recomendaciones.append(("🟠 ALTO", f"Diversificar portafolio: {concentracion_a:.1f}% de ventas concentrado en pocos productos"))
    
    if metrics['productos_unicos'] < 10:
        recomendaciones.append(("🟡 MEDIO", f"Ampliar catálogo: Solo {metrics['productos_unicos']} productos activos"))
    
    if len(recomendaciones) == 0:
        recomendaciones.append(("🟢 BUENO", "Rendimiento general satisfactorio. Mantener estrategia actual"))
    
    # Producto estrella
    top_producto = df.groupby('descripcion')['precio_total'].sum().nlargest(1)
    if len(top_producto) > 0:
        producto_estrella = top_producto.index[0]
        participacion_estrella = (top_producto.iloc[0] / metrics['total_ventas']) * 100
        if participacion_estrella > 30:
            recomendaciones.append(("🟠 ALTO", f"Reducir dependencia del producto estrella ({participacion_estrella:.1f}% de ventas)"))
    
    for prioridad, mensaje in recomendaciones[:3]:
        color_class = "warning-box" if "CRÍTICO" in prioridad or "ALTO" in prioridad else "insight-box" if "MEDIO" in prioridad else "success-box"
        st.markdown(f'<div class="{color_class}"><strong>{prioridad}:</strong> {mensaje}</div>', unsafe_allow_html=True)


def _show_executive_table(df, proveedor, metrics, periodo_analisado):
    """Tabla Resumen Ejecutivo Final"""
    familias_completas = ", ".join(sorted(df['familia'].dropna().unique())) if 'familia' in df.columns else "N/A"
    subfamilias_completas = ", ".join(sorted(df['subfamilia'].dropna().unique())) if 'subfamilia' in df.columns else "N/A"
    
    # Calcular ABC
    productos_abc = df.groupby(['idarticulo', 'descripcion']).agg({'precio_total': 'sum'}).sort_values('precio_total', ascending=False)
    productos_abc['participacion_acum'] = (productos_abc['precio_total'].cumsum() / productos_abc['precio_total'].sum() * 100)
    productos_abc['categoria_abc'] = productos_abc['participacion_acum'].apply(lambda x: 'A' if x <= 80 else 'B' if x <= 95 else 'C')
    abc_counts = productos_abc['categoria_abc'].value_counts().sort_index()
    
    # Producto estrella
    top_producto = df.groupby('descripcion')['precio_total'].sum().nlargest(1)
    producto_estrella = top_producto.index[0] if len(top_producto) > 0 else "N/A"
    
    # Tendencia
    df['mes_año'] = pd.to_datetime(df['fecha']).dt.to_period('M').astype(str)
    mensual = df.groupby('mes_año')['precio_total'].sum()
    if len(mensual) >= 3:
        valores = mensual.values
        tendencia_coef = np.polyfit(range(len(valores)), valores, 1)[0]
        tendencia_texto = "📈 Creciente" if tendencia_coef > 0 else "📉 Decreciente"
    else:
        tendencia_texto = "➡️ Período insuficiente"
    
    resumen_data = {
        'Métrica': [
            'Proveedor',
            'Período de Análisis',
            'Ventas Totales',
            'Utilidad Total',
            'Margen Promedio',
            'Productos Únicos',
            'Días con Ventas',
            'Familias',
            'Subfamilias',
            'Sucursales Activas',
            'Tendencia Período',
            'Clasificación ABC',
            'Producto estrella'
        ],
        'Valor': [
            proveedor,
            periodo_analisado,
            f"${metrics['total_ventas']:,.0f}",
            f"${metrics['total_utilidad']:,.0f}",
            f"{metrics['margen_promedio']:.1f}%",
            f"{metrics['productos_unicos']:,}",
            f"{metrics['dias_con_ventas']:,}",
            familias_completas[:100] + "..." if len(familias_completas) > 100 else familias_completas,
            subfamilias_completas[:100] + "..." if len(subfamilias_completas) > 100 else subfamilias_completas,
            metrics['sucursales_presentes'],
            tendencia_texto,
            f"{abc_counts.get('A', 0)}A-{abc_counts.get('B', 0)}B-{abc_counts.get('C', 0)}C",
            producto_estrella
        ]
    }
    
    df_resumen = pd.DataFrame(resumen_data)
    st.dataframe(df_resumen, use_container_width=True, hide_index=True)


def _show_data_preview(df, proveedor, periodo_analisado):
    """Vista Previa de Datos y Descarga"""
    st.markdown("### Vista Previa de Datos")
    
    data = df[[
        'fecha_fmt', 'idarticulo', 'descripcion', 
        'precio_total', 'costo_total', 'utilidad', 
        'margen_porcentual', 'cantidad_total'
    ]].copy()
    
    # Generar Excel
    archivo_excel = generar_excel(data, sheet_name="Datos Proveedor")
    proveedor_key = sub(r'\W+', '', proveedor.lower())
    
    st.download_button(
        label="📥 Descargar todos los datos del proveedor (Excel)",
        data=archivo_excel,
        file_name=f"{proveedor}_{periodo_analisado}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"descarga_excel_{proveedor_key}"
    )
    
    # Mostrar muestra
    st.dataframe(
        data.head(10),
        use_container_width=True,
        column_config={
            "fecha_fmt": st.column_config.TextColumn("Fecha"),
            "precio_total": st.column_config.NumberColumn("Precio Total", format="$%.0f"),
            "costo_total": st.column_config.NumberColumn("Costo Total", format="$%.0f"),
            "utilidad": st.column_config.NumberColumn("Utilidad", format="$%.0f"),
            "margen_porcentual": st.column_config.NumberColumn("Margen %", format="%.1f%%"),
            "cantidad_total": st.column_config.NumberColumn("Cantidad", format="%.0f")
        }
    )
    
    if len(data) > 10:
        st.info(f"ℹ️ Mostrando las primeras 10 filas de {len(data):,} registros totales.")