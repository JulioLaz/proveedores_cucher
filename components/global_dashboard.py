import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

def show_global_dashboard(df_proveedores, query_function, credentials_path, project_id):
    """
    Dashboard Global de Proveedores - Vista inicial antes de seleccionar proveedor
    
    Args:
        df_proveedores: DataFrame con relación proveedor-articulo
        query_function: Función para consultar BigQuery (query_resultados_idarticulo)
        credentials_path: Ruta credenciales GCP
        project_id: ID proyecto BigQuery
    """
    
    st.markdown("""
    <div class="main-header">
        <p style='padding:5px 0px; font-size:1.8rem; font-weight:bold;'>
            🏆 Dashboard Ejecutivo - Ranking de Proveedores
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # === CARGA DE DATOS ===
    with st.spinner("🔄 Cargando datos globales de presupuesto..."):
        start_time = time.time()
        
        # Consultar TODOS los artículos con presupuesto
        df_presupuesto = query_function(
            credentials_path=credentials_path,
            project_id=project_id,
            dataset='presupuesto',
            table='result_final_alert_all'
        )
        
        load_time = time.time() - start_time
    
    if df_presupuesto is None or df_presupuesto.empty:
        st.error("❌ No se pudieron cargar los datos de presupuesto")
        return
    
    st.success(f"✅ Datos cargados en {load_time:.2f}s | {len(df_presupuesto):,} artículos procesados")
    
    # === MERGE PROVEEDORES ===
    df_merge = df_presupuesto.merge(
        df_proveedores[['idarticulo', 'proveedor', 'idproveedor']],
        on='idarticulo',
        how='inner'
    )
    
    # === AGREGACIÓN POR PROVEEDOR ===
    ranking = df_merge.groupby(['proveedor', 'idproveedor']).agg({
        'idarticulo': 'count',
        'PRESUPUESTO': 'sum',
        'nivel_riesgo': lambda x: (x.str.contains('🔴', na=False)).sum(),
        'dias_cobertura': 'mean',
        'exceso_STK': lambda x: (x > 0).sum(),
        'costo_exceso_STK': 'sum',
        'STK_TOTAL': lambda x: (x == 0).sum()
    }).reset_index()
    
    ranking.columns = [
        'Proveedor', 'ID', 'Artículos', 'Presupuesto', 
        'Alertas Críticas', 'Días Cobertura Prom', 
        'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
    ]
    
    ranking = ranking.sort_values('Presupuesto', ascending=False).reset_index(drop=True)
    ranking['Ranking'] = range(1, len(ranking) + 1)
    
    # === KPIs GLOBALES ===
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "💰 Presupuesto Total",
            f"${ranking['Presupuesto'].sum():,.0f}",
            delta=f"{len(ranking)} proveedores"
        )
    
    with col2:
        st.metric(
            "📦 Total Artículos",
            f"{ranking['Artículos'].sum():,}",
            delta=f"{df_merge['idarticulo'].nunique():,} únicos"
        )
    
    with col3:
        st.metric(
            "🚨 Alertas Críticas",
            f"{ranking['Alertas Críticas'].sum():,}",
            delta="Nivel 🔴 Alto"
        )
    
    with col4:
        st.metric(
            "⚠️ Exceso de Stock",
            f"${ranking['Costo Exceso'].sum():,.0f}",
            delta=f"{ranking['Art. con Exceso'].sum():,} artículos"
        )
    
    with col5:
        st.metric(
            "❌ Sin Stock",
            f"{ranking['Art. Sin Stock'].sum():,}",
            delta="Artículos"
        )
    
    # === VISUALIZACIONES ===
    st.markdown("---")
    st.markdown("### 📊 Análisis Visual de Proveedores")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # TREEMAP INTERACTIVO
        top_treemap = ranking.head(20).copy()
        top_treemap['Texto'] = top_treemap.apply(
            lambda x: f"{x['Proveedor']}<br>${x['Presupuesto']:,.0f}<br>{x['Artículos']} arts.", 
            axis=1
        )
        
        fig_tree = px.treemap(
            top_treemap,
            path=['Proveedor'],
            values='Presupuesto',
            color='Alertas Críticas',
            color_continuous_scale='Reds',
            title='🗺️ Mapa de Presupuesto por Proveedor (TOP 20)',
            hover_data={
                'Presupuesto': ':$,.0f',
                'Artículos': ':,',
                'Alertas Críticas': ':,'
            }
        )
        
        fig_tree.update_traces(
            textposition="middle center",
            textfont_size=11,
            marker=dict(line=dict(width=2, color='white'))
        )
        
        fig_tree.update_layout(
            height=500,
            margin=dict(t=50, b=10, l=10, r=10),
            title_font=dict(size=16, color='#333', family='Arial Black'),
            title_x=0.05
        )
        
        st.plotly_chart(fig_tree, use_container_width=True)
    
    with col2:
        # TOP 10 BARRAS
        top10 = ranking.head(10).copy()
        top10['Presupuesto_M'] = top10['Presupuesto'] / 1_000_000
        top10['Texto'] = top10['Presupuesto'].apply(lambda x: f"${x/1_000_000:.1f}M")
        
        fig_bar = go.Figure(go.Bar(
            y=top10['Proveedor'][::-1],
            x=top10['Presupuesto_M'][::-1],
            orientation='h',
            text=top10['Texto'][::-1],
            textposition='outside',
            marker_color='#e74c3c',
            hovertemplate='<b>%{y}</b><br>Presupuesto: %{text}<extra></extra>'
        ))
        
        fig_bar.update_layout(
            title='🏆 TOP 10 Proveedores',
            title_font=dict(size=16, color='#333', family='Arial Black'),
            title_x=0.1,
            height=500,
            margin=dict(t=50, b=10, l=10, r=10),
            xaxis=dict(visible=False),
            yaxis=dict(visible=True),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # === TABLA RANKING DETALLADA ===
    st.markdown("---")
    st.markdown("### 📋 Ranking Detallado de Proveedores")
    
    # Formatear columnas para display
    df_display = ranking.copy()
    df_display['Presupuesto'] = df_display['Presupuesto'].apply(lambda x: f"${x:,.0f}")
    df_display['Días Cobertura Prom'] = df_display['Días Cobertura Prom'].apply(lambda x: f"{x:.1f}")
    df_display['Costo Exceso'] = df_display['Costo Exceso'].apply(lambda x: f"${x:,.0f}")
    
    # Mostrar top 20 por defecto, con opción de ver más
    num_mostrar = st.slider("Cantidad de proveedores a mostrar:", 10, len(df_display), 20, step=5)
    
    st.dataframe(
        df_display.head(num_mostrar)[[
            'Ranking', 'Proveedor', 'Presupuesto', 'Artículos',
            'Alertas Críticas', 'Días Cobertura Prom', 
            'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
        ]],
        use_container_width=True,
        hide_index=True
    )
    
    # === SELECTOR RÁPIDO DE PROVEEDOR ===
    st.markdown("---")
    st.markdown("### 🔍 Análisis Rápido de Proveedor")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        proveedor_seleccionado = st.selectbox(
            "Selecciona un proveedor para análisis detallado:",
            options=ranking['Proveedor'].tolist(),
            index=0,
            key='quick_select_proveedor'
        )
    
    with col2:
        if st.button("🚀 Analizar Proveedor", type="primary", use_container_width=True):
            # Guardar en session_state para que el sidebar lo detecte
            st.session_state.selected_proveedor = proveedor_seleccionado
            st.info(f"✅ Selecciona **{proveedor_seleccionado}** en el sidebar y presiona 'Realizar Análisis'")
    
    # === INSIGHTS AUTOMÁTICOS ===
    st.markdown("---")
    st.markdown("### 💡 Insights Clave")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        top_proveedor = ranking.iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #4caf50'>
        <b>🏆 Proveedor Líder</b><br>
        <b>{top_proveedor['Proveedor']}</b><br>
        💰 ${top_proveedor['Presupuesto']:,.0f}<br>
        📦 {top_proveedor['Artículos']} artículos<br>
        📊 {(top_proveedor['Presupuesto'] / ranking['Presupuesto'].sum() * 100):.1f}% del presupuesto total
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        mas_alertas = ranking.nlargest(1, 'Alertas Críticas').iloc[0]
        st.markdown(f"""
        <div style='background-color:#ffebee;padding:1rem;border-radius:10px;border-left:5px solid #f44336'>
        <b>🚨 Mayor Riesgo</b><br>
        <b>{mas_alertas['Proveedor']}</b><br>
        ⚠️ {mas_alertas['Alertas Críticas']} alertas críticas<br>
        ❌ {mas_alertas['Art. Sin Stock']} artículos sin stock<br>
        🎯 Requiere atención inmediata
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        mas_exceso = ranking.nlargest(1, 'Costo Exceso').iloc[0]
        st.markdown(f"""
        <div style='background-color:#fff3e0;padding:1rem;border-radius:10px;border-left:5px solid #ff9800'>
        <b>📦 Mayor Exceso</b><br>
        <b>{mas_exceso['Proveedor']}</b><br>
        💸 ${mas_exceso['Costo Exceso']:,.0f} inmovilizado<br>
        📊 {mas_exceso['Art. con Exceso']} artículos con exceso<br>
        🔄 Optimizar inventario
        </div>
        """, unsafe_allow_html=True)
    
    # === EXPORTAR RANKING ===
    st.markdown("---")
    csv = ranking.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Descargar Ranking Completo (CSV)",
        csv,
        f"ranking_proveedores_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv",
        use_container_width=True
    )