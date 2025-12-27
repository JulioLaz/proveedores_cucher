"""
Módulo: TAB1 - Análisis de Rankings de Proveedores por Ventas
Contiene visualizaciones gráficas, tabla detallada, insights y preparación de datos para cobertura
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
from google.cloud import bigquery


def format_millones(valor):
    """Formatea valores grandes en millones o miles"""
    if valor >= 1_000_000:
        millones = valor / 1_000_000
        return f"{millones:,.0f} mll".replace(',', 'X').replace('.', ',').replace('X', '.')
    elif valor >= 1_000:
        return f"{valor/1_000:,.0f} mil".replace(',', '.')
    else:
        return f"{valor:,.0f}"


def format_miles(valor: int) -> str:
    """Formatea valores con separador de miles"""
    return f"{valor:,}".replace(",", ".")


def main_tab1_ranking_ventas(
    ranking,
    df_ventas_filtrado,
    df_presupuesto_filtrado,
    df_proveedores_filtrado,
    df_prov_con_familias,
    familias_seleccionadas,
    subfamilias_seleccionadas,
    familias_disponibles,
    subfamilias_disponibles,
    fecha_desde,
    fecha_hasta,
    credentials_path,
    project_id,
    bigquery_table
):
    """
    Función principal del TAB1: Rankings de Proveedores por Ventas
    
    Muestra:
    - 3 gráficos de barras horizontales (Top Ventas, Utilidad, Presupuesto)
    - Tabla ranking detallado
    - 5 Insights en tarjetas
    - Preparación de datos para cobertura (retorna df_para_cobertura)
    """
    
    print(f"\n{'='*80}")
    print("📊 TAB1: RENDERIZANDO ANÁLISIS DE RANKINGS")
    print(f"{'='*80}")
    inicio_tab1 = time.time()
    
    # Determinar si hay filtros activos
    filtros_activos = (
        len(familias_seleccionadas) < len(familias_disponibles) or 
        len(subfamilias_seleccionadas) < len(subfamilias_disponibles)
    )
    
    # ═════════════════════════════════════════════════════════════════════════
    # SECCIÓN 1: VISUALIZACIONES GRÁFICAS (3 COLUMNAS)
    # ═════════════════════════════════════════════════════════════════════════
    
    col1, col2, col3 = st.columns(3)

    # ─────────────────────────────────────────────────────────────────────────
    # GRÁFICO 1: RANKING POR VENTA TOTAL
    # ─────────────────────────────────────────────────────────────────────────
    with col1:
        st.markdown("#### 🏆 Ranking por Venta Total")

        top_ventas_num = st.slider(
            "Cantidad de proveedores (Ventas):", 
            5, 80, 20, step=5, 
            key='slider_ventas'
        )

        top_ventas = ranking.head(top_ventas_num).copy()
        top_ventas['Venta_M'] = top_ventas['Venta Total'] / 1_000_000

        # 🎨 Escala de colores según rentabilidad
        def get_color_by_rentability(rentabilidad):
            """Verde oscuro (alta rent) → Amarillo (media) → Rojo (baja)"""
            if rentabilidad >= 15:
                return '#27ae60'  # Verde oscuro
            elif rentabilidad >= 12:
                return '#2ecc71'  # Verde medio
            elif rentabilidad >= 9:
                return '#f39c12'  # Amarillo/naranja
            elif rentabilidad >= 6:
                return '#e67e22'  # Naranja
            else:
                return '#e74c3c'  # Rojo

        top_ventas['Color'] = top_ventas['Rentabilidad %'].apply(get_color_by_rentability)
        top_ventas['Texto'] = top_ventas.apply(
            lambda row: f"${row['Venta Total']/1_000_000:.0f}M | {row['Rentabilidad %']:.1f}%", 
            axis=1
        )

        fig_ventas = go.Figure(go.Bar(
            y=top_ventas['Proveedor'][::-1],
            x=top_ventas['Venta_M'][::-1],
            orientation='h',
            text=top_ventas['Texto'][::-1],
            textposition='outside',
            cliponaxis=False,
            marker_color=top_ventas['Color'][::-1].tolist(),
            hovertemplate='<b>%{y}</b><br>' +
                        'Venta: ' + top_ventas['Venta Total'][::-1].apply(lambda x: f"${x/1_000_000:.1f}M") + '<br>' +
                        'Rentabilidad: ' + top_ventas['Rentabilidad %'][::-1].apply(lambda x: f"{x:.1f}%") + '<br>' +
                        'Participación: ' + top_ventas['% Participación Ventas'][::-1].apply(lambda x: f"{x:.1f}%") + 
                        '<extra></extra>'
        ))

        # Título interno del gráfico con indicador de filtros
        titulo_grafico = f"Top {top_ventas_num} Proveedores por Ventas"
        if filtros_activos:
            titulo_grafico += f" (Filtrado: {len(familias_seleccionadas)} familias, {len(subfamilias_seleccionadas)} subfamilias)"

        # Calcular rango del eje X para dar espacio al texto
        max_venta = top_ventas['Venta_M'].max()

        fig_ventas.update_layout(
            height=max(400, top_ventas_num * 25),
            margin=dict(t=30, b=10, l=10, r=50),
            xaxis=dict(
                visible=False,
                range=[0, max_venta * 1.30]
            ),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            title=dict(
                text=titulo_grafico,
                font=dict(size=12, color='#3498db'),
                x=0.5,
                xanchor='center'
            )
        )

        st.plotly_chart(fig_ventas, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # GRÁFICO 2: RANKING POR UTILIDAD
    # ─────────────────────────────────────────────────────────────────────────
    with col2:
        st.markdown("#### 💸 Ranking por Utilidad")

        top_util_num = st.slider(
            "Cantidad de proveedores (Utilidad):", 
            5, 80, 20, step=5, 
            key='slider_util'
        )

        ranking_util = ranking.sort_values('Utilidad', ascending=False).head(top_util_num).copy()
        ranking_util['Utilidad_M'] = ranking_util['Utilidad'] / 1_000_000
        ranking_util['Texto'] = ranking_util['Utilidad'].apply(lambda x: f"${x/1_000_000:.1f}M")

        # Color dinámico según filtros
        color_barra = '#9b59b6' if not filtros_activos else '#8e44ad'

        fig_util = go.Figure(go.Bar(
            y=ranking_util['Proveedor'][::-1],
            x=ranking_util['Utilidad_M'][::-1],
            orientation='h',
            text=ranking_util['Texto'][::-1],
            textposition='outside',
            cliponaxis=False,
            marker_color=color_barra,
            hovertemplate='<b>%{y}</b><br>Utilidad: %{text}<br>Rentabilidad: ' +
                        ranking_util['Rentabilidad %'][::-1].apply(lambda x: f"{x:.1f}%") + '<extra></extra>'
        ))

        # Título interno del gráfico con indicador de filtros
        titulo_grafico = f"Top {top_util_num} Proveedores por Utilidad"
        if filtros_activos:
            titulo_grafico += f" (Filtrado: {len(familias_seleccionadas)} familias, {len(subfamilias_seleccionadas)} subfamilias)"

        # Calcular rango del eje X para dar espacio al texto
        max_util = ranking_util['Utilidad_M'].max()

        fig_util.update_layout(
            height=max(400, top_util_num * 25),
            margin=dict(t=30, b=10, l=10, r=30),
            xaxis=dict(
                visible=False,
                range=[0, max_util * 1.15]
            ),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            title=dict(
                text=titulo_grafico,
                font=dict(size=12, color='#8e44ad'),
                x=0.5,
                xanchor='center'
            )
        )
        
        st.plotly_chart(fig_util, use_container_width=True)

    # ─────────────────────────────────────────────────────────────────────────
    # GRÁFICO 3: RANKING POR PRESUPUESTO
    # ─────────────────────────────────────────────────────────────────────────
    with col3:
        st.markdown("#### 💰 Ranking por Presupuesto")

        top_presu_num = st.slider(
            "Cantidad de proveedores (Presupuesto):", 
            5, 80, 20, step=5, 
            key='slider_presu'
        )

        ranking_presu = ranking.sort_values('Presupuesto', ascending=False).head(top_presu_num).copy()
        ranking_presu['Presupuesto_M'] = ranking_presu['Presupuesto'] / 1_000_000
        ranking_presu['Texto'] = ranking_presu['Presupuesto'].apply(lambda x: f"${x/1_000_000:.1f}M")

        # Color dinámico según filtros
        color_barra = '#e74c3c' if not filtros_activos else '#e67e22'

        fig_presu = go.Figure(go.Bar(
            y=ranking_presu['Proveedor'][::-1],
            x=ranking_presu['Presupuesto_M'][::-1],
            orientation='h',
            text=ranking_presu['Texto'][::-1],
            textposition='outside',
            cliponaxis=False,
            marker_color=color_barra,
            hovertemplate='<b>%{y}</b><br>Presupuesto: %{text}<extra></extra>'
        ))

        # Título interno del gráfico con indicador de filtros
        titulo_grafico = f"Top {top_presu_num} Proveedores por Presupuesto"
        if filtros_activos:
            titulo_grafico += f" (Filtrado: {len(familias_seleccionadas)} familias, {len(subfamilias_seleccionadas)} subfamilias)"

        # Calcular rango del eje X para dar espacio al texto
        max_presu = ranking_presu['Presupuesto_M'].max()

        fig_presu.update_layout(
            height=max(400, top_presu_num * 25),
            margin=dict(t=30, b=10, l=10, r=30),
            xaxis=dict(
                visible=False,
                range=[0, max_presu * 1.15]
            ),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            title=dict(
                text=titulo_grafico,
                font=dict(size=12, color='#e67e22'),
                x=0.5,
                xanchor='center'
            )
        )
        
        st.plotly_chart(fig_presu, use_container_width=True)

    # ═════════════════════════════════════════════════════════════════════════
    # SECCIÓN 2: TABLA RANKING DETALLADO
    # ═════════════════════════════════════════════════════════════════════════
    
    st.markdown("### 📋 Ranking Detallado de Proveedores ordenados por ranking Venta")
    
    df_display = ranking.copy()
    df_display['Venta Total'] = df_display['Venta Total'].apply(lambda x: f"${x:,.0f}")
    df_display['Costo Total'] = df_display['Costo Total'].apply(lambda x: f"${x:,.0f}")
    df_display['Utilidad'] = df_display['Utilidad'].apply(lambda x: f"${x:,.0f}")
    df_display['Presupuesto'] = df_display['Presupuesto'].apply(lambda x: f"${x:,.0f}")
    df_display['Costo Exceso'] = df_display['Costo Exceso'].apply(lambda x: f"${x:,.0f}")
    df_display['Rentabilidad %'] = df_display['Rentabilidad %'].apply(lambda x: f"{x:.2f}%")
    df_display['% Participación Presupuesto'] = df_display['% Participación Presupuesto'].apply(lambda x: f"{x:.2f}%")
    df_display['% Participación Ventas'] = df_display['% Participación Ventas'].apply(lambda x: f"{x:.2f}%")

    num_mostrar = st.slider(
        "Cantidad de proveedores a mostrar:", 
        10, len(df_display), 20, step=5, 
        key='slider_tabla'
    )
    
    st.dataframe(
        df_display.head(num_mostrar)[[
            'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total', 'Utilidad', 'Rentabilidad %',
            '% Participación Presupuesto', 'Presupuesto', 'Artículos', 'Art. con Exceso', 
            'Costo Exceso', 'Art. Sin Stock'
        ]],
        use_container_width=True,
        hide_index=True
    )
    
    # ═════════════════════════════════════════════════════════════════════════
    # SECCIÓN 3: INSIGHTS CLAVE (5 TARJETAS)
    # ═════════════════════════════════════════════════════════════════════════
    
    st.markdown("### 💡 Insights Clave de Proveedores")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        top_proveedor = ranking.iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #4caf50; font-size:13px'>
        <b style='border-bottom:1px solid gray; margin-bottom: 3px'>🏆 Proveedor Líder en Ventas</b><br>
        <b style='text-align: center'>{top_proveedor['Proveedor']}</b><br>
        💰 ${top_proveedor['Venta Total']:,.0f}<br>
        📊 {top_proveedor['% Participación Ventas']:.1f}% del total<br>
        📦 {top_proveedor['Artículos']} artículos
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        top_presupuesto = ranking.nlargest(1, 'Presupuesto').iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #4caf50; font-size:13px'>
        <b style='border-bottom:1px solid gray; margin-bottom: 3px'>💰 Mayor Presupuesto Requerido</b><br>
        <b>{top_presupuesto['Proveedor']}</b><br>
        💵 ${top_presupuesto['Presupuesto']:,.0f}<br>
        📊 {top_presupuesto['% Participación Presupuesto']:.1f}% del total<br>
        📦 {top_presupuesto['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        mas_util = ranking.nlargest(1, 'Utilidad').iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #4caf50; font-size:13px'>
        <b style='border-bottom:1px solid gray; margin-bottom: 3px'>🏆 Proveedor Líder en Utilidad</b><br>
        <b>{mas_util['Proveedor']}</b><br>
        💸 ${mas_util['Utilidad']:,.0f}<br>
        📦 {mas_util['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        peor_util = ranking.nsmallest(1, 'Utilidad').iloc[0]
        st.markdown(f"""
        <div style='background-color:#ffebee;padding:1rem;border-radius:10px;border-left:5px solid red; font-size:13px'>
        <b style='border-bottom:1px solid gray; margin-bottom: 3px'>⚠️ Proveedor con Menor Utilidad</b><br>
        <b>{peor_util['Proveedor']}</b><br>
        💸 ${peor_util['Utilidad']:,.0f}<br>
        📦 {peor_util['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
                
    with col5:
        mas_exceso = ranking.nlargest(1, 'Costo Exceso').iloc[0]
        st.markdown(f"""
        <div style='background-color:#ffebee;padding:1rem;border-radius:10px;border-left:5px solid red; font-size:13px'>
        <b style='border-bottom:1px solid gray; margin-bottom: 3px'>⚠️ Mayor Exceso de Stock</b><br>
        <b>{mas_exceso['Proveedor']}</b><br>
        💸 ${mas_exceso['Costo Exceso']:,.0f} inmovilizado<br>
        📊 {mas_exceso['Art. con Exceso']} artículos<br>
        🔄 Optimizar inventario
        </div>
        """, unsafe_allow_html=True)
    
    # ═════════════════════════════════════════════════════════════════════════
    # SECCIÓN 4: PREPARACIÓN DE DATOS PARA COBERTURA
    # ═════════════════════════════════════════════════════════════════════════
    
    print(f"\n{'='*80}")
    print("📦 PREPARANDO DATOS PARA COBERTURA DE STOCK")
    print(f"{'='*80}")

    # Agrupar ventas por artículo
    df_para_cobertura = df_ventas_filtrado.groupby('idarticulo').agg({
        'cantidad_vendida': 'sum',
        'venta_total': 'sum',
        'costo_total': 'sum'
    }).reset_index()

    # Calcular utilidad
    df_para_cobertura['utilidad_total'] = df_para_cobertura['venta_total'] - df_para_cobertura['costo_total']

    # Agregar proveedor, familia, subfamilia desde df_proveedores_filtrado
    df_para_cobertura = df_para_cobertura.merge(
        df_proveedores_filtrado[['idarticulo', 'proveedor', 'familia', 'subfamilia']],
        on='idarticulo',
        how='left'
    )

    # ═══ OBTENER DESCRIPCIÓN DESDE BIGQUERY ═══
    print(f"\n{'='*80}")
    print("🔍 OBTENIENDO DESCRIPCIONES DESDE BIGQUERY")
    print(f"{'='*80}")

    # Verificar si df_ventas_filtrado tiene descripcion
    print(f"📋 Columnas en df_ventas_filtrado: {df_ventas_filtrado.columns.tolist()}")

    if 'descripcion' in df_ventas_filtrado.columns:
        print(f"✅ Usando descripciones desde df_ventas_filtrado")
        df_desc_temp = df_ventas_filtrado[['idarticulo', 'descripcion']].drop_duplicates('idarticulo')
        df_para_cobertura = df_para_cobertura.merge(
            df_desc_temp,
            on='idarticulo',
            how='left'
        )
    else:
        print(f"⚠️ 'descripcion' NO está en df_ventas_filtrado")
        print(f"🔄 Consultando BigQuery para obtener descripciones...")
        
        try:
            inicio_desc = time.time()
            
            # Obtener lista de idarticulos únicos
            ids_para_buscar = df_para_cobertura['idarticulo'].unique().tolist()
            
            # Limitar a 10,000 IDs por consulta (límite de BigQuery)
            if len(ids_para_buscar) > 10000:
                print(f"⚠️ Hay {len(ids_para_buscar):,} artículos. Limitando a 10,000 para la consulta...")
                ids_para_buscar = ids_para_buscar[:10000]
            
            id_str = ','.join(map(str, ids_para_buscar))
            
            print(f"   • IDs a consultar: {len(ids_para_buscar):,}")
            print(f"   • Tabla: {bigquery_table}")
            
            # Conectar a BigQuery
            import os
            is_cloud = not os.path.exists(credentials_path)
            
            if is_cloud:
                print(f"   • Ambiente: Streamlit Cloud")
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_info(
                    st.secrets["gcp_service_account"]
                )
                client = bigquery.Client(credentials=credentials, project=project_id)
            else:
                print(f"   • Ambiente: Local")
                client = bigquery.Client.from_service_account_json(credentials_path, project=project_id)
            
            # Query para obtener descripciones (más reciente por artículo)
            query_desc = f"""
            SELECT idarticulo, descripcion
            FROM (
                SELECT idarticulo, descripcion,
                    ROW_NUMBER() OVER (PARTITION BY idarticulo ORDER BY fecha_comprobante DESC) as rn
                FROM `{project_id}.{bigquery_table}`
                WHERE idarticulo IN ({id_str})
                AND descripcion IS NOT NULL
                AND descripcion != ''
            )
            WHERE rn = 1
            """
            
            print(f"\n🔄 Ejecutando query...")
            df_descripciones = client.query(query_desc).to_dataframe()
            
            tiempo_desc = time.time() - inicio_desc
            
            print(f"✅ Query completada en {tiempo_desc:.2f}s")
            print(f"   • Descripciones obtenidas: {len(df_descripciones):,}")
            print(f"   • Muestra:")
            print(df_descripciones.head(5))
            
            # Merge con df_para_cobertura
            df_para_cobertura = df_para_cobertura.merge(
                df_descripciones,
                on='idarticulo',
                how='left'
            )
            
            print(f"✅ Merge completado")
            
        except Exception as e:
            print(f"\n❌ ERROR OBTENIENDO DESCRIPCIONES:")
            print(f"   Tipo de error: {type(e).__name__}")
            print(f"   Mensaje: {str(e)}")
            print(f"\n⚠️ Usando descripciones genéricas como fallback...")
            
            # Si no existe la columna descripcion, crearla genérica
            if 'descripcion' not in df_para_cobertura.columns:
                df_para_cobertura['descripcion'] = 'Artículo ' + df_para_cobertura['idarticulo'].astype(str)

    # Rellenar faltantes con genéricas
    if 'descripcion' in df_para_cobertura.columns:
        faltantes_antes = df_para_cobertura['descripcion'].isna().sum()
        if faltantes_antes > 0:
            print(f"⚠️ Rellenando {faltantes_antes:,} descripciones faltantes...")
            df_para_cobertura['descripcion'].fillna(
                'Artículo ' + df_para_cobertura['idarticulo'].astype(str),
                inplace=True
            )
    else:
        print(f"⚠️ Columna 'descripcion' no existe. Creándola...")
        df_para_cobertura['descripcion'] = 'Artículo ' + df_para_cobertura['idarticulo'].astype(str)

    # Verificar resultado final
    descripciones_genericas = df_para_cobertura['descripcion'].str.contains('Artículo', na=False).sum()
    descripciones_reales = len(df_para_cobertura) - descripciones_genericas

    print(f"\n📊 RESULTADO FINAL:")
    print(f"   • Total artículos: {len(df_para_cobertura):,}")
    print(f"   • ✅ Con descripción real: {descripciones_reales:,}")
    print(f"   • ⚠️ Con descripción genérica: {descripciones_genericas:,}")
    
    tiempo_tab1 = time.time() - inicio_tab1
    print(f"   ⏱️  Tiempo total TAB1: {tiempo_tab1:.2f}s")
    print(f"{'='*80}\n")
    
    # Retornar el DataFrame preparado para cobertura
    return df_para_cobertura