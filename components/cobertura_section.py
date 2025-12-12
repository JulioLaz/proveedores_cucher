"""
============================================================
MÓDULO: Cobertura Section
============================================================
Maneja la visualización y exportación del análisis de
cobertura de stock vs utilidad.

Autor: Julio Lazarte
Fecha: Diciembre 2024
============================================================
"""

import streamlit as st
import time
import plotly.graph_objects as go
from components.cobertura_stock_exporter import generar_reporte_cobertura


def show_cobertura_section(df_para_cobertura, fecha_desde, fecha_hasta,
                           credentials_path, project_id,
                           familias_seleccionadas, subfamilias_seleccionadas, cnt_proveedores):
    """
    Renderiza la sección de análisis de cobertura vs utilidad.
    
    Args:
        df_para_cobertura (pd.DataFrame): Datos preparados para análisis de cobertura
        fecha_desde (date): Fecha inicio del período
        fecha_hasta (date): Fecha fin del período
        credentials_path (str): Ruta a credenciales de GCP
        project_id (str): ID del proyecto de BigQuery
        familias_seleccionadas (list): Familias seleccionadas
        subfamilias_seleccionadas (list): Subfamilias seleccionadas
    """
    
    print(f"\n{'='*80}")
    print("💰 SECCIÓN: ANÁLISIS DE COBERTURA VS UTILIDAD")
    print(f"{'='*80}\n")
    
    st.markdown(
        """
        <div style="font-size:28px; font-weight:bold; color:#1e3c72; margin-bottom:4px; text-align: center;">
            💰 Utilidad vs Stock
        <div style="font-size:22px; color:#555;">
            Análisis detallado de inventario vs utilidad
        </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_btn_UTILIDAD, col_btn_REPORTE = st.columns([1, 3])

    with col_btn_UTILIDAD:
        # Selector de utilidad mínima
        utilidad_minima = st.number_input(
            "💵 Utilidad mínima a considerar ($):",
            min_value=0,
            max_value=10_000_000,
            value=10_000,
            step=50_000,
            format="%d",
            help=f"Solo se incluirán artículos con utilidad superior a este monto. "
                f"Ref: $10.000",
            key='utilidad_minima_cobertura'
        )

    with col_btn_REPORTE:
        if st.button("🔄 Generar Análisis y Reporte para descarga: Top Artículos x Utilidad vs días de cobertura", 
                     use_container_width=True, type="primary"):
            with st.spinner("📊 Generando reporte..."):
                print(f"\n{'='*80}")
                print("📦 GENERANDO REPORTE DE COBERTURA")
                print(f"{'='*80}")
                inicio_cobertura = time.time()

                # Generar reporte (devuelve Excel Y DataFrame)
                excel_cobertura, df_cobertura_completo = generar_reporte_cobertura(
                    df_para_cobertura,
                    fecha_desde,
                    fecha_hasta,
                    credentials_path,
                    project_id,
                    utilidad_minima
                )

                tiempo_cobertura = time.time() - inicio_cobertura
                print(f"   ⏱️  Tiempo generación: {tiempo_cobertura:.2f}s")
                print(f"{'='*80}\n")

                if excel_cobertura and df_cobertura_completo is not None:
                    # Guardar en session_state para visualización
                    st.session_state['df_cobertura_viz'] = df_cobertura_completo
                    st.session_state['excel_generado'] = True

                    fecha_inicio_str = fecha_desde.strftime('%d%b%Y')
                    fecha_fin_str = fecha_hasta.strftime('%d%b%Y')
                    nombre_archivo_cobertura = f"utilidad_stock_cobertura_{fecha_inicio_str}_{fecha_fin_str}.xlsx"

                    st.download_button(
                        label="📥 Descargar Análisis de Cobertura",
                        data=excel_cobertura,
                        file_name=nombre_archivo_cobertura,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.error("❌ Error generando reporte de cobertura")

    if 'df_cobertura_viz' not in st.session_state or st.session_state['df_cobertura_viz'] is None:
        # Crear un contenedor con estilo similar a st.info
        with st.container():
            st.markdown("""
                <div style="
                    background-color: #e8f4fd;
                    padding: 5px 15px;
                    border-radius: 8px;
                    border-left: 5px solid #1f77b4;
                    margin-bottom: 10px;
                ">
                <strong>Incluye:</strong>
                </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                st.info(f"""
                        - 📦 Stock actual por artículo
                        - 📊 Cobertura en días
                        - 🎯 Clasificación (Crítico/Bajo/Óptimo/Alto/Exceso)
                        - 💰 Análisis de utilidad vs inventario""")                

            with col2:
                st.info(f"""
                        - 🚚 {cnt_proveedores} proveedores analizados
                        - 💵 Utilidad mínima: ${utilidad_minima:,.0f}                    
                        - 📅 Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}
                        - 🏷️ Filtros: {len(familias_seleccionadas)} familias, {len(subfamilias_seleccionadas)} subfamilias
                        """)

    # ═══════════════════════════════════════════════════════════════════
    # VISUALIZACIÓN DE TOP ARTÍCULOS POR COBERTURA
    # ═══════════════════════════════════════════════════════════════════

    # Verificar si hay datos de cobertura para visualizar
    if 'df_cobertura_viz' in st.session_state and st.session_state['df_cobertura_viz'] is not None:
        
        # Cargar datos desde session_state
        df_viz = st.session_state['df_cobertura_viz'].copy()
        
        print(f"\n{'='*80}")
        print(f"🔍 DEBUG: CARGANDO DATOS DE SESSION_STATE")
        print(f"{'='*80}")
        print(f"   Tipo: {type(df_viz)}")
        print(f"   Registros: {len(df_viz):,}")
        print(f"   Columnas ({len(df_viz.columns)}): {df_viz.columns.tolist()}")
        print(f"   Memoria: {df_viz.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        print(f"{'='*80}\n")
        
        # === VISUALIZACIÓN DE TOP ARTÍCULOS POR UTILIDAD ===
        st.markdown("### 📊 Análisis Detallado por Artículo")
        
        # Crear columna con formato: "1234 - Descripción"
        df_viz['articulo_label'] = (
            df_viz['idarticulo'].astype(str) + ' - ' + 
            df_viz['descripcion'].str.slice(0, 50)
        )
        
        # Ordenar por utilidad
        df_viz = df_viz.sort_values('utilidad_total', ascending=False)
        
        # Slider para cantidad de artículos
        col_slider, col_info, col_info_01 = st.columns([3, 1, 1])
        
        with col_slider:
            top_articulos = st.slider(
                "📦 Cantidad de artículos a mostrar:",
                min_value=5,
                max_value=min(100, len(df_viz)),
                value=min(20, len(df_viz)),
                step=5,
                key='slider_articulos_cobertura'
            )
        
        with col_info:
            st.metric(
                "Total Artículos",
                f"{len(df_viz):,}".replace(",", "."),
                delta=f"{df_viz.proveedor.nunique()} proveedores"
            )
        
        with col_info_01:
            utilidad_minima = st.session_state.get('utilidad_minima_cobertura', 10000)
            st.metric(
                "Sólo Utilidad Mayor a:",
                f"${utilidad_minima:,.0f}".replace(",", "."))
        
        # Filtrar top artículos
        df_top = df_viz.head(top_articulos).copy()
        
        print(f"\n🔍 DEBUG - Columnas en df_top: {df_top.columns.tolist()}")
        print(f"   ¿Tiene stk_total?: {'stk_total' in df_top.columns}")
        
        # === GRÁFICOS ===
        col_graf1, col_graf2 = st.columns(2)
                
        with col_graf1:
            st.markdown("#### 💰 Top Artículos por Utilidad")
            
            # Preparar datos para el gráfico (invertir para que el mayor esté arriba)
            df_plot = df_top.iloc[::-1].copy()
            
            df_plot['Utilidad_M'] = df_plot['utilidad_total'] / 1_000_000
            df_plot['Texto'] = df_plot['utilidad_total'].apply(lambda x: f"${x/1_000_000:.2f}M")
            
            # Crear hover text
            hover_text_utilidad = []
            for idx, row in df_plot.iterrows():
                texto = f"<b>{row['articulo_label']}</b><br>"
                texto += f"Utilidad: ${row['utilidad_total']/1_000_000:.2f}M<br>"
                texto += f"Stock: {int(row['stk_total']):,}<br>"
                texto += f"Cobertura: {row['cobertura_dias']:.0f} días"
                hover_text_utilidad.append(texto)
            
            # Crear gráfico de utilidad
            fig_utilidad = go.Figure(go.Bar(
                y=df_plot['articulo_label'],
                x=df_plot['Utilidad_M'],
                orientation='h',
                text=df_plot['Texto'],
                textposition='outside',
                cliponaxis=False,
                marker_color='#3498db',
                hovertemplate='%{customdata}<extra></extra>',
                customdata=hover_text_utilidad
            ))
            
            # Calcular rango del eje X
            max_utilidad = df_plot['Utilidad_M'].max()
            
            fig_utilidad.update_layout(
                height=max(400, top_articulos * 25),
                margin=dict(t=20, b=25, l=10, r=20),
                xaxis=dict(
                    visible=False,
                    range=[0, max_utilidad * 1.2]
                ),
                yaxis=dict(
                    visible=True,
                    tickfont=dict(size=10)
                ),
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            st.plotly_chart(fig_utilidad, use_container_width=True)

        with col_graf2:
            st.markdown("#### ⏱️ Días de Cobertura (Cap: 31 días)")
            
            # Preparar datos de cobertura (CAP en 31 días)
            df_plot['cobertura_visual'] = df_plot['cobertura_dias'].apply(lambda x: min(x, 31))
            df_plot['cobertura_texto'] = df_plot['cobertura_dias'].apply(
                lambda x: f"{x:.0f}d" if x <= 31 else f"31d+"
            )
            
            # Asignar colores según clasificación
            def get_color_cobertura(dias):
                if dias < 15:
                    return '#e74c3c'  # Rojo - Crítico
                elif dias < 30:
                    return '#f39c12'  # Naranja - Bajo
                else:
                    return '#27ae60'  # Verde - Óptimo
            
            df_plot['color_barra'] = df_plot['cobertura_dias'].apply(get_color_cobertura)
            
            # Crear hover text para cobertura
            hover_text_cobertura = []
            for idx, row in df_plot.iterrows():
                texto = f"<b>{row['articulo_label']}</b><br>"
                texto += f"Cobertura: {row['cobertura_dias']:.0f} días<br>"
                texto += f"Stock: {int(row['stk_total']):,}<br>"
                texto += f"Clasificación: {row['clasificacion']}"
                hover_text_cobertura.append(texto)
            
            # Crear gráfico de cobertura
            fig_cobertura = go.Figure()
            
            # Agregar barras
            fig_cobertura.add_trace(go.Bar(
                y=df_plot['articulo_label'],
                x=df_plot['cobertura_visual'],
                orientation='h',
                text=df_plot['cobertura_texto'],
                textposition='outside',
                cliponaxis=False,
                marker=dict(
                    color=df_plot['color_barra'],
                    line=dict(width=0)
                ),
                hovertemplate='%{customdata}<extra></extra>',
                customdata=hover_text_cobertura
            ))
            
            # Agregar líneas verticales de referencia
            lineas_dias = [7, 14, 21, 28]
            colores_lineas = ['#e74c3c', '#e67e22', '#f39c12', '#3498db']
            
            for dia, color in zip(lineas_dias, colores_lineas):
                fig_cobertura.add_vline(
                    x=dia,
                    line_dash="dash",
                    line_color=color,
                    line_width=1.5,
                    opacity=0.6,
                    annotation_text=f"{dia}d",
                    annotation_position="top",
                    annotation_font_size=9,
                    annotation_font_color=color
                )
            
            fig_cobertura.update_layout(
                height=max(400, top_articulos * 25),
                margin=dict(t=20, b=5, l=30, r=20),
                xaxis=dict(
                    visible=True,
                    range=[0, 33],
                    tickmode='array',
                    tickvals=[0, 7, 14, 21, 28, 31],
                    ticktext=['0', '7', '14', '21', '28', '31+'],
                    tickfont=dict(size=9)
                ),
                yaxis=dict(
                    visible=True,
                    tickfont=dict(size=10)
                ),
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            st.plotly_chart(fig_cobertura, use_container_width=True)
        
        # === TABLA DETALLADA ===
        st.markdown("#### 📋 Tabla Detallada")
        
        # Preparar DataFrame para mostrar
        df_tabla = df_top[[
            'idarticulo',
            'descripcion',
            'proveedor',
            'familia',
            'subfamilia',
            'utilidad_total',
            'cantidad_vendida',
            'stk_total',
            'cobertura_dias',
            'clasificacion'
        ]].copy()
        
        # Renombrar columnas
        df_tabla.columns = [
            'Código',
            'Descripción',
            'Proveedor',
            'Familia',
            'SubFamilia',
            'Utilidad',
            'Cant. Vendida',
            'Stock',
            'Cobertura (días)',
            'Clasificación'
        ]
        
        # Formatear valores
        df_tabla['Utilidad'] = df_tabla['Utilidad'].apply(lambda x: f"${x:,.0f}")
        df_tabla['Cant. Vendida'] = df_tabla['Cant. Vendida'].apply(lambda x: f"{x:,.0f}")
        df_tabla['Stock'] = df_tabla['Stock'].apply(lambda x: f"{x:,.0f}")
        df_tabla['Cobertura (días)'] = df_tabla['Cobertura (días)'].apply(lambda x: f"{x:.0f}")
        
        # Mostrar tabla con estilo
        st.dataframe(
            df_tabla,
            use_container_width=True,
            hide_index=True,
            height=min(400, (top_articulos * 35) + 38)
        )
        
        # === RESUMEN ESTADÍSTICO ===
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            utilidad_total_top = df_top['utilidad_total'].sum()
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 12px; color: #555;">💰 Utilidad Total</div>
                    <div style="font-size: 16px; font-weight: bold; color: #1e3c72;">
                        ${utilidad_total_top/1_000_000:.2f}M
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            stock_total_top = df_top['stk_total'].sum()
            stock_total_top_str = f"{stock_total_top:,.0f}".replace(",", ".")
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 12px; color: #555;">📦 Stock Total</div>
                    <div style="font-size: 16px; font-weight: bold; color: #1e3c72;">
                        {stock_total_top_str}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            cobertura_prom_top = df_top['cobertura_dias'].mean()
            color_cobertura = '#27ae60' if 15 <= cobertura_prom_top <= 60 else '#e67e22'
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 12px; color: #555;">⏱️ Cobertura Prom.</div>
                    <div style="font-size: 16px; font-weight: bold; color: {color_cobertura};">
                        {cobertura_prom_top:.0f} días
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            cant_vendida_top = df_top['cantidad_vendida'].sum()
            cant_vendida_top_str = f"{cant_vendida_top:,.0f}".replace(",", ".")
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 12px; color: #555;">🛒 Cant. Vendida</div>
                    <div style="font-size: 16px; font-weight: bold; color: #1e3c72;">
                        {cant_vendida_top_str}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
