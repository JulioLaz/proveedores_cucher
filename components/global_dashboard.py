import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
from io import BytesIO
import plotly.graph_objects as go

# Importar funciones cacheadas
from utils.excel_exporter import crear_excel_ranking, generar_nombre_archivo

from components.global_dashboard_cache import (
    get_ventas_data,
    get_presupuesto_data,
    get_familias_data,    # ← AGREGAR
    process_ranking_data
)

def format_millones(valor):
        if valor >= 1_000_000:
            millones = valor / 1_000_000
            return f"{millones:,.0f} mll".replace(',', 'X').replace('.', ',').replace('X', '.')
        elif valor >= 1_000:
            return f"{valor/1_000:,.0f} mil".replace(',', '.')
        else:
            return f"{valor:,.0f}"
        
def format_miles(valor: int) -> str:
        return f"{valor:,}".replace(",", ".")

def show_global_dashboard(df_proveedores, query_function, credentials_path, project_id, bigquery_table):
    """Dashboard Global de Proveedores"""
    
    print("\n" + "="*80)
    print("🚀 DASHBOARD GLOBAL DE PROVEEDORES")
    print("="*80)
    inicio_total = time.time()

    df_presupuesto = get_presupuesto_data(credentials_path, project_id)
    
    if 'ultima_fecha' in df_presupuesto.columns:
        fecha_maxima_disponible = pd.to_datetime(df_presupuesto['ultima_fecha']).iloc[0].date()
    else:
        # Fallback: usar fecha actual menos 1 día
        fecha_maxima_disponible = datetime.now().date() - timedelta(days=1)
    
    print(f"   ✅ Última fecha con datos: {fecha_maxima_disponible.strftime('%d/%m/%Y')}")


    container = st.container(border=True)

    with container:
        # === SELECTOR DE PERÍODO ===
        col1, col2, col_fam1, col_fam2, col_fam3, col_fam4 = st.columns([2, 1.4, 2.1, 2.1, 1.1,0.8])
        # col1, col2, col3, col_fam1, col_fam2, col_fam3, col_fam4 = st.columns([2, 1, 1, 2, 2, 1,1])

        with col1:
            periodo_opciones = {
                "Últimos 30 días": 30,
                "Últimos 60 días": 60,
                "Últimos 90 días": 90,
                "Últimos 6 meses": 180,
                "Último año": 365,
                "Personalizado": None,
            }

            periodo_seleccionado = st.selectbox(
                "📅 Período de análisis de ventas:",
                options=list(periodo_opciones.keys()),
                index=0,
            )

            st.markdown(
                    f"""
                    <div>
                        <span style='font-weight:semi-bold;padding: 5px;font-size:1rem'>🆙 Actualizado al:</span><br>
                        <div style='font-weight:300;padding-top: 5px;padding-left: 1.5rem;font-size:1rem'>
                            {fecha_maxima_disponible.strftime('%d %B %Y')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


        with col2:
            if periodo_seleccionado == "Personalizado":
                col_a, col_b = st.columns(2)
                fecha_desde = col_a.date_input(
                    "Desde:",
                    value= fecha_maxima_disponible - timedelta(days=30),
                )
                fecha_hasta = col_b.date_input(
                    "Hasta:",
                    value=fecha_maxima_disponible,  # ← CAMBIADO
                    max_value=fecha_maxima_disponible
                )

                if fecha_desde > fecha_hasta:
                    st.error("La fecha 'Desde' no puede ser mayor que 'Hasta'.")
                    st.stop()

                dias_periodo = (fecha_hasta - fecha_desde).days

            else:
                dias_periodo = periodo_opciones[periodo_seleccionado]
                fecha_hasta = fecha_maxima_disponible
                fecha_desde = fecha_maxima_disponible - timedelta(days=dias_periodo)

                st.markdown(
                    f"""
                    <div>
                        <span style='font-weight:semi-bold;padding: 5px;font-size:1rem'>⏳ Rango de fechas</span><br>
                        <div style='font-weight:300;padding-top: 5px;padding-left: 1rem;font-size:1rem'>
                            Desde: {fecha_desde.strftime('%d %b %Y')}
                        </div>
                        <div style='font-weight:300; padding-left: 1rem;font-size:1rem'>
                            Hasta: {fecha_hasta.strftime('%d %b %Y')}
                        </div>
                        <div style='font-weight:semi-bold;padding-top: 5px;padding-left: 5px;font-size:1rem'> 📆 Días de actividad:</div>
                        <div style='font-weight:400;margin-left:2.8rem;font-size:1.4rem'>{dias_periodo} días</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # with col3:
        #     st.metric("📆 Días", f"{dias_periodo}")

        # === CARGAR DATOS PRIMERO (para tener df_ventas disponible) ===
        print(f"\n🔄 Cargando datos para filtros...")
        df_ventas = get_ventas_data(
            credentials_path, 
            project_id, 
            bigquery_table,
            str(fecha_desde),
            str(fecha_hasta)
        )

        df_presupuesto = get_presupuesto_data(credentials_path, project_id)
        # print(f"   ✅ df_presupuesto: ", df_presupuesto.columns.tolist())
        df_familias = get_familias_data(credentials_path, project_id, bigquery_table)

        # Agregar familia/subfamilia a df_proveedores
        df_prov_con_familias = df_proveedores.merge(
            df_familias[['idarticulo', 'familia', 'subfamilia']],
            on='idarticulo',
            how='left'
        )

        # ⭐ FILTRAR SOLO ARTÍCULOS CON VENTAS EN EL PERÍODO
        articulos_con_ventas = df_ventas['idarticulo'].unique()
        df_prov_con_familias = df_prov_con_familias[
            df_prov_con_familias['idarticulo'].isin(articulos_con_ventas)
        ]

        print(f"   ✅ Artículos con ventas en período: {len(df_prov_con_familias):,}")

        # === FILTROS DE FAMILIA Y SUBFAMILIA ===

        with col_fam1:
            familias_disponibles = sorted(df_prov_con_familias['familia'].dropna().unique().tolist())
            
            familias_seleccionadas = st.multiselect(
                "🏷️ Filtrar por Familia:",
                options=familias_disponibles,
                default=familias_disponibles,
                placeholder="Deselecciona las familias que NO quieres ver"
            )
            
            if not familias_seleccionadas:
                familias_seleccionadas = familias_disponibles
                st.warning("⚠️ Debes mantener al menos una familia seleccionada")

        with col_fam2:
            df_familias_filtradas = df_prov_con_familias[
                df_prov_con_familias['familia'].isin(familias_seleccionadas)
            ]
            
            subfamilias_disponibles = sorted(df_familias_filtradas['subfamilia'].dropna().unique().tolist())
            
            subfamilias_seleccionadas = st.multiselect(
                "📂 Filtrar por Subfamilia:",
                options=subfamilias_disponibles,
                default=subfamilias_disponibles,
                placeholder="Deselecciona las subfamilias que NO quieres ver"
            )
            
            if not subfamilias_seleccionadas:
                subfamilias_seleccionadas = subfamilias_disponibles
                st.warning("⚠️ Debes mantener al menos una subfamilia seleccionada")

        with col_fam3:
            df_temp = df_prov_con_familias[
                df_prov_con_familias['familia'].isin(familias_seleccionadas)
            ]
            
            if subfamilias_seleccionadas:
                df_temp = df_temp[
                    df_temp['subfamilia'].isin(subfamilias_seleccionadas)
                ]
                                  
            # Calcular artículos totales vs filtrados
            articulos_totales = df_prov_con_familias['idarticulo'].nunique()
            articulos_filtrados = df_temp['idarticulo'].nunique()
            
            st.metric(
                "🎯 Artículos", 
                f"{format_miles(articulos_filtrados)}",
                delta=f"{format_miles(articulos_totales)} totales"
            )

        with col_fam4:
            # Calcular totales
            total_familias = len(familias_disponibles)
            activas_familias = len(familias_seleccionadas)
            total_subfamilias = len(subfamilias_disponibles)
            activas_subfamilias = len(subfamilias_seleccionadas)
            
            # Mostrar métricas de filtros
            st.markdown(f"""
            <div style="text-align: center; margin-top: 0.5rem;">
                <div style="font-size: 12px; color: #555; margin-bottom: 0.3rem;">📊 Filtros</div>
                <div style="font-size: 14px; font-weight: bold; color: #1e3c72;">
                    🏷️ {activas_familias}/{total_familias}
                </div>
                <div style="font-size: 11px; color: #666; margin-top: 0.2rem;">
                    familias
                </div>
                <div style="font-size: 14px; font-weight: bold; color: #1e3c72; margin-top: 0.3rem;">
                    📂 {activas_subfamilias}/{total_subfamilias}
                </div>
                <div style="font-size: 11px; color: #666; margin-top: 0.2rem;">
                    subfamilias
                </div>
            </div>
            """, unsafe_allow_html=True)



        # === APLICAR FILTROS AL DATAFRAME PRINCIPAL ===
        df_proveedores_filtrado = df_prov_con_familias[
            df_prov_con_familias['familia'].isin(familias_seleccionadas)
        ].copy()

        if subfamilias_seleccionadas:
            df_proveedores_filtrado = df_proveedores_filtrado[
                df_proveedores_filtrado['subfamilia'].isin(subfamilias_seleccionadas)
            ]

        # Logs de filtros aplicados
        excluidas_familias = set(familias_disponibles) - set(familias_seleccionadas)
        excluidas_subfamilias = set(subfamilias_disponibles) - set(subfamilias_seleccionadas)

        print(f"\n{'='*80}")
        print(f"🎯 FILTROS APLICADOS")
        print(f"{'='*80}")
        print(f"   ✅ Familias activas: {len(familias_seleccionadas)}/{len(familias_disponibles)}")
        if excluidas_familias:
            print(f"   ❌ Familias excluidas: {', '.join(sorted(excluidas_familias))}")
        print(f"   ✅ Subfamilias activas: {len(subfamilias_seleccionadas)}/{len(subfamilias_disponibles)}")
        if excluidas_subfamilias:
            print(f"   ❌ Subfamilias excluidas: {len(excluidas_subfamilias)} items")
        print(f"   📦 Artículos filtrados: {df_proveedores_filtrado['idarticulo'].nunique():,}")
        print(f"{'='*80}")

        # === 🔥 FILTRAR VENTAS Y PRESUPUESTO POR ARTÍCULOS SELECCIONADOS ===
        print(f"\n{'='*80}")
        print(f"🎯 APLICANDO FILTROS A VENTAS Y PRESUPUESTO")
        print(f"{'='*80}")
        
        articulos_filtrados = df_proveedores_filtrado['idarticulo'].unique()
        print(f"   📦 Artículos únicos en filtro: {len(articulos_filtrados):,}")
        
        # Filtrar VENTAS
        df_ventas_filtrado = df_ventas[
            df_ventas['idarticulo'].isin(articulos_filtrados)
        ].copy()
        
        venta_filtrada = df_ventas_filtrado['venta_total'].sum()  # ← CORREGIDO
        print(f"   💰 Ventas filtradas: ${venta_filtrada:,.0f}")
        print(f"   📊 Artículos con ventas: {df_ventas_filtrado['idarticulo'].nunique():,}")
        
        # Filtrar PRESUPUESTO
        df_presupuesto_filtrado = df_presupuesto[
            df_presupuesto['idarticulo'].isin(articulos_filtrados)
        ].copy()
        
        presupuesto_filtrado = df_presupuesto_filtrado['PRESUPUESTO'].sum()
        print(f"   💵 Presupuesto filtrado: ${presupuesto_filtrado:,.0f}")
        print(f"   📦 Artículos en presupuesto: {df_presupuesto_filtrado['idarticulo'].nunique():,}")
        print(f"{'='*80}\n")

    # === ADVERTENCIA VISUAL SI HAY FILTROS ACTIVOS ===
    filtros_activos = (
        len(familias_seleccionadas) < len(familias_disponibles) or 
        len(subfamilias_seleccionadas) < len(subfamilias_disponibles)
    )
    
    if filtros_activos:
        st.info(f"""
        🎯 **FILTROS ACTIVOS**: Los valores de ventas, presupuesto y todas las métricas están calculados 
        **solo para las {len(familias_seleccionadas)} familias y {len(subfamilias_seleccionadas)} subfamilias seleccionadas**.
        Para ver el ranking completo sin filtros, selecciona todas las familias y subfamilias.
        """)

    # 📊 DEBUG: Mostrar período seleccionado en consola
    print(f"{'='*80}")
    print(f"📅 PERÍODO SELECCIONADO")
    print(f"{'='*80}")
    print(f"   ├─ Opción: {periodo_seleccionado}")
    print(f"   ├─ Desde: {fecha_desde}")
    print(f"   ├─ Hasta: {fecha_hasta}")
    print(f"   └─ Días: {dias_periodo}")
    print(f"{'='*80}\n")
    
    # === ESTILOS ===
    st.markdown("""
    <style>
        .metric-box {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            padding: 0.8rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            justify-content: center;
            border-left: 5px solid #2a5298;
            margin-bottom: .5rem;
        }
        .metric-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        .stSlider > div > div > label {
            margin-bottom: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    # ✅ CALCULAR RANKING CON DATOS FILTRADOS
    print(f"{'='*80}")
    print(f"📊 PROCESANDO RANKING CON DATOS FILTRADOS")
    print(f"{'='*80}")
    inicio_ranking = time.time()
    
    ranking = process_ranking_data(
        df_proveedores_filtrado, 
        df_ventas_filtrado,       # ← FILTRADO
        df_presupuesto_filtrado,  # ← FILTRADO
        df_familias
    )
    
    tiempo_ranking = time.time() - inicio_ranking
    
    if ranking is None or ranking.empty:
        st.error("❌ No se pudieron cargar los datos")
        return
    
    print(f"   ✅ Ranking procesado exitosamente")
    print(f"   📊 Proveedores en ranking: {len(ranking):,}")
    print(f"   ⏱️  Tiempo: {tiempo_ranking:.2f}s")
    print(f"{'='*80}\n")
    
    # === KPIs ===
    col1, col11, col2, col3, col4, col5 = st.columns(6)
        
    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">💰 Ventas Totales</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Venta Total'].sum())}</div>
            </div>
            <div style="color: green; font-size: 12px; margin-top: 0.2rem;">
                ⬆️ {len(ranking)} proveedores
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col11:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">💰 Utilidad Total</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Utilidad'].sum())}</div>
            </div>
            <div style="color: green; font-size: 12px; margin-top: 0.2rem;">
                ⬆️ {len(ranking)} proveedores
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">💵 Presupuesto a 30 días</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Presupuesto'].sum())}</div>
            </div>
            <div style="color: #d35400; font-size: 12px; margin-top: 0.2rem;">
                📊 Inversión requerida
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">📦 Cantidad Vendida</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">{format_miles(int(ranking['Cantidad Vendida'].sum()))}</div>
            </div>
            <div style="color: #555; font-size: 12px; margin-top: 0.2rem;">
                🎯 {df_ventas_filtrado['idarticulo'].nunique():,} art únicos
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">⚠️ Exceso de Stock</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Costo Exceso'].sum())}</div>
            </div>
            <div style="color: #888; font-size: 12px; margin-top: 0.2rem;">
                📊 {ranking['Art. con Exceso'].sum():,} artículos
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">❌ Sin Stock</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">{format_miles(int(ranking['Art. Sin Stock'].sum()))}</div>
            </div>
            <div style="color: #c0392b; font-size: 12px; margin-top: 0.2rem;">
                🔴 Artículos críticos
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

    # === VISUALIZACIONES ===
    col1, col2 = st.columns(2)

    with col1:
        # 🎯 Título dinámico según filtros
        st.markdown("#### 🏆 Ranking por Venta Total")
        # if filtros_activos:
        #     st.markdown(f"""
        #     #### 🏆 Ranking por Venta Total 🎯
        #     #### 🏆 Ranking por Venta Total 🎯
        #     <small style='color: #666; font-weight: bold'>Filtrado: {len(familias_seleccionadas)} familias, {len(subfamilias_seleccionadas)} subfamilias</small>
        #     """, unsafe_allow_html=True)
        # else:
        #     st.markdown("#### 🏆 Ranking por Venta Total")
        
        top_ventas_num = st.slider("Cantidad de proveedores (Ventas):", 5, 80, 20, step=5, key='slider_ventas')
        
        # ✅ ranking YA está filtrado, así que esto ya usa datos filtrados
        top_ventas = ranking.head(top_ventas_num).copy()
        top_ventas['Venta_M'] = top_ventas['Venta Total'] / 1_000_000
        top_ventas['Texto'] = top_ventas['Venta Total'].apply(lambda x: f"${x/1_000_000:.1f}M")
        
        # Color dinámico según filtros
        color_barra = '#2ecc71' if not filtros_activos else '#3498db'  # Verde normal, Azul si hay filtros
        
        fig_ventas = go.Figure(go.Bar(
            y=top_ventas['Proveedor'][::-1],
            x=top_ventas['Venta_M'][::-1],
            orientation='h',
            text=top_ventas['Texto'][::-1],
            textposition='outside',
            marker_color=color_barra,
            hovertemplate='<b>%{y}</b><br>Venta: %{text}<br>Participación: ' + 
                        top_ventas['% Participación Ventas'][::-1].apply(lambda x: f"{x:.1f}%") + '<extra></extra>'
        ))
        
        # Título interno del gráfico con indicador de filtros
        titulo_grafico = f"Top {top_ventas_num} Proveedores por Ventas"
        if filtros_activos:
            titulo_grafico += f" (Filtrado: {len(familias_seleccionadas)} familias, {len(subfamilias_seleccionadas)} subfamilias)"
        
        fig_ventas.update_layout(
            height=max(400, top_ventas_num * 25),
            margin=dict(t=30, b=10, l=10, r=10),
            xaxis=dict(visible=False),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            title=dict(
                text=titulo_grafico,
                # text=titulo_grafico if filtros_activos else None,
                font=dict(size=12, color='#3498db'),
                x=0.5,
                xanchor='center'
            )
        )
        
        st.plotly_chart(fig_ventas, use_container_width=True)

    with col2:
        # 🎯 Título dinámico según filtros
        st.markdown("#### 🏆 Ranking por Venta Total")
        # if filtros_activos:
        #     st.markdown(f"""
        #     #### 💰 Ranking por Presupuesto 🎯
        #     <small style='color: #666;font-weight: bold'>Filtrado: {len(familias_seleccionadas)} familias, {len(subfamilias_seleccionadas)} subfamilias</small>
        #     """, unsafe_allow_html=True)
        # else:
        #     st.markdown("#### 💰 Ranking por Presupuesto")
        
        top_presu_num = st.slider("Cantidad de proveedores (Presupuesto):", 5, 80, 20, step=5, key='slider_presu')
        
        # ✅ ranking YA está filtrado, así que esto ya usa datos filtrados
        ranking_presu = ranking.sort_values('Presupuesto', ascending=False).head(top_presu_num).copy()
        ranking_presu['Presupuesto_M'] = ranking_presu['Presupuesto'] / 1_000_000
        ranking_presu['Texto'] = ranking_presu['Presupuesto'].apply(lambda x: f"${x/1_000_000:.1f}M")
        
        # Color dinámico según filtros
        color_barra = '#e74c3c' if not filtros_activos else '#e67e22'  # Rojo normal, Naranja si hay filtros
        
        fig_presu = go.Figure(go.Bar(
            y=ranking_presu['Proveedor'][::-1],
            x=ranking_presu['Presupuesto_M'][::-1],
            orientation='h',
            text=ranking_presu['Texto'][::-1],
            textposition='outside',
            marker_color=color_barra,
            hovertemplate='<b>%{y}</b><br>Presupuesto: %{text}<extra></extra>'
        ))
        
        # Título interno del gráfico con indicador de filtros
        titulo_grafico = f"Top {top_presu_num} Proveedores por Presupuesto"
        if filtros_activos:
            titulo_grafico += f" (Filtrado: {len(familias_seleccionadas)} familias, {len(subfamilias_seleccionadas)} subfamilias)"
        
        fig_presu.update_layout(
            height=max(400, top_presu_num * 25),
            margin=dict(t=30, b=10, l=10, r=10),
            xaxis=dict(visible=False),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            title=dict(
                text=titulo_grafico,
                # text=titulo_grafico if filtros_activos else None,
                font=dict(size=12, color='#e67e22'),
                x=0.5,
                xanchor='center'
            )
        )
        
        st.plotly_chart(fig_presu, use_container_width=True)



    # === TABLA RANKING ===
    st.markdown("### 📋 Ranking Detallado de Proveedores")
    
    df_display = ranking.copy()
    df_display['Venta Total'] = df_display['Venta Total'].apply(lambda x: f"${x:,.0f}")
    df_display['Costo Total'] = df_display['Costo Total'].apply(lambda x: f"${x:,.0f}")
    df_display['Utilidad'] = df_display['Utilidad'].apply(lambda x: f"${x:,.0f}")
    df_display['Presupuesto'] = df_display['Presupuesto'].apply(lambda x: f"${x:,.0f}")
    df_display['Costo Exceso'] = df_display['Costo Exceso'].apply(lambda x: f"${x:,.0f}")
    df_display['Rentabilidad %'] = df_display['Rentabilidad %'].apply(lambda x: f"{x:.2f}%")
    df_display['% Participación Presupuesto'] = df_display['% Participación Presupuesto'].apply(lambda x: f"{x:.2f}%")
    df_display['% Participación Ventas'] = df_display['% Participación Ventas'].apply(lambda x: f"{x:.2f}%")

    num_mostrar = st.slider("Cantidad de proveedores a mostrar:", 10, len(df_display), 20, step=5, key='slider_tabla')
    
    st.dataframe(
        df_display.head(num_mostrar)[[
            'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total', 'Utilidad', 'Rentabilidad %',
            '% Participación Presupuesto', 'Presupuesto', 'Artículos', 'Art. con Exceso', 
            'Costo Exceso', 'Art. Sin Stock'
        ]],
        use_container_width=True,
        hide_index=True
    )
    
    # === INSIGHTS ===
    st.markdown("### 💡 Insights Clave")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        top_proveedor = ranking.iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #4caf50'>
        <b>🏆 Proveedor Líder en Ventas</b><br>
        <b>{top_proveedor['Proveedor']}</b><br>
        💰 ${top_proveedor['Venta Total']:,.0f}<br>
        📊 {top_proveedor['% Participación Ventas']:.1f}% del total<br>
        📦 {top_proveedor['Artículos']} artículos
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        top_presupuesto = ranking.nlargest(1, 'Presupuesto').iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #ff9800'>
        <b>💰 Mayor Presupuesto Requerido</b><br>
        <b>{top_presupuesto['Proveedor']}</b><br>
        💵 ${top_presupuesto['Presupuesto']:,.0f}<br>
        📊 {top_presupuesto['% Participación Presupuesto']:.1f}% del total<br>
        📦 {top_presupuesto['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        mas_util = ranking.nlargest(1, 'Utilidad').iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #4caf50'>
        <b>🏆 Proveedor Líder en Utilidad</b><br>
        <b>{mas_util['Proveedor']}</b><br>
        💸 ${mas_util['Utilidad']:,.0f}<br>
        📦 {mas_util['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        peor_util = ranking.nsmallest(1, 'Utilidad').iloc[0]
        st.markdown(f"""
        <div style='background-color:#ffebee;padding:1rem;border-radius:10px;border-left:5px solid #f44336'>
        <b>⚠️ Proveedor con Menor Utilidad</b><br>
        <b>{peor_util['Proveedor']}</b><br>
        💸 ${peor_util['Utilidad']:,.0f}<br>
        📦 {peor_util['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
                
    with col5:
        mas_exceso = ranking.nlargest(1, 'Costo Exceso').iloc[0]
        st.markdown(f"""
        <div style='background-color:#ffebee;padding:1rem;border-radius:10px;border-left:5px solid #f44336'>
        <b>⚠️ Mayor Exceso de Stock</b><br>
        <b>{mas_exceso['Proveedor']}</b><br>
        💸 ${mas_exceso['Costo Exceso']:,.0f} inmovilizado<br>
        📊 {mas_exceso['Art. con Exceso']} artículos<br>
        🔄 Optimizar inventario
        </div>
        """, unsafe_allow_html=True)
       
    # === EXPORTAR RANKING ===
    st.markdown("---")
    st.markdown("### 📥 Exportar Datos")

    col_btn1, col_btn2 = st.columns(2)

    # ============================================
    # BOTÓN 1: DESCARGAR RANKING COMPLETO (SIN FILTROS)
    # ============================================
    with col_btn1:
        st.markdown("#### 📊 Ranking Completo")
        st.caption("Incluye TODOS los proveedores sin aplicar filtros de familia/subfamilia")
        
        print(f"\n{'='*80}")
        print("📊 GENERANDO RANKING COMPLETO (SIN FILTROS)")
        print(f"{'='*80}")
        inicio_completo = time.time()
        
        ranking_completo = process_ranking_data(
            df_prov_con_familias,  # ← SIN filtrar por familia/subfamilia
            df_ventas,             # Ventas del período seleccionado (todas las familias)
            df_presupuesto,        # Presupuesto completo (todas las familias)
            df_familias
        )
        
        tiempo_completo = time.time() - inicio_completo
        print(f"   ✅ Ranking completo generado")
        print(f"   📦 Proveedores: {len(ranking_completo):,}")
        print(f"   💰 Venta total: ${ranking_completo['Venta Total'].sum():,.0f}")
        print(f"   💵 Presupuesto total: ${ranking_completo['Presupuesto'].sum():,.0f}")
        print(f"   ⏱️  Tiempo: {tiempo_completo:.2f}s")
        print(f"{'='*80}\n")
        
        df_export_completo = ranking_completo[[
            'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total',
            'Utilidad', 'Rentabilidad %', '% Participación Presupuesto', 'Presupuesto',
            'Artículos', 'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
        ]].copy()
        
        output_completo = crear_excel_ranking(
            df_export_completo, 
            str(fecha_desde), 
            str(fecha_hasta),
            filtros_aplicados=False
        )
        nombre_archivo_completo = generar_nombre_archivo("ranking_completo")
        
        st.download_button(
            label=f"📥 Descargar Ranking Completo ({len(ranking_completo)} proveedores)",
            data=output_completo,
            file_name=nombre_archivo_completo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="secondary"
        )
        
        st.info(f"""
        **Incluye:**
        - ✅ Todas las familias ({len(familias_disponibles)})
        - ✅ Todas las subfamilias ({len(subfamilias_disponibles)})
        - 📅 Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}
        - 📊 {len(ranking_completo):,} proveedores
        - 💰 ${format_millones(ranking_completo['Venta Total'].sum())} en ventas
        - 💵 ${format_millones(ranking_completo['Presupuesto'].sum())} en presupuesto
        """)

    # ============================================
    # BOTÓN 2: DESCARGAR RANKING FILTRADO
    # ============================================
    with col_btn2:
        st.markdown("#### 🎯 Ranking Filtrado")
        st.caption("Solo incluye los filtros actualmente seleccionados")
        
        print(f"\n{'='*80}")
        print("🎯 PREPARANDO RANKING FILTRADO PARA DESCARGA")
        print(f"{'='*80}")
        print(f"   📦 Proveedores filtrados: {len(ranking):,}")
        print(f"   💰 Venta filtrada: ${ranking['Venta Total'].sum():,.0f}")
        print(f"   💵 Presupuesto filtrado: ${ranking['Presupuesto'].sum():,.0f}")
        print(f"{'='*80}\n")
        
        df_export_filtrado = ranking[[
            'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total',
            'Utilidad', 'Rentabilidad %', '% Participación Presupuesto', 'Presupuesto',
            'Artículos', 'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
        ]].copy()
        
        output_filtrado = crear_excel_ranking(
            df_export_filtrado, 
            str(fecha_desde), 
            str(fecha_hasta),
            filtros_aplicados=True,
            familias_activas=familias_seleccionadas,
            subfamilias_activas=subfamilias_seleccionadas
        )
        nombre_archivo_filtrado = generar_nombre_archivo("ranking_filtrado")
        
        st.download_button(
            label=f"📥 Descargar Ranking Filtrado ({len(ranking)} proveedores)",
            data=output_filtrado,
            file_name=nombre_archivo_filtrado,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
        
        st.success(f"""
        **Filtros aplicados:**
        - 🏷️ {len(familias_seleccionadas)}/{len(familias_disponibles)} familias
        - 📂 {len(subfamilias_seleccionadas)}/{len(subfamilias_disponibles)} subfamilias
        - 📅 Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}
        - 📊 {len(ranking):,} proveedores
        - 💰 ${format_millones(ranking['Venta Total'].sum())} en ventas
        - 💵 ${format_millones(ranking['Presupuesto'].sum())} en presupuesto
        """)
    
    # === TIEMPO TOTAL DE EJECUCIÓN ===
    tiempo_total = time.time() - inicio_total
    print(f"\n{'='*80}")
    print(f"✅ DASHBOARD COMPLETADO")
    print(f"{'='*80}")
    print(f"   ⏱️  Tiempo total de ejecución: {tiempo_total:.2f}s")
    print(f"{'='*80}\n")

def show_global_dashboard_00(df_proveedores, query_function, credentials_path, project_id, bigquery_table):
    """Dashboard Global de Proveedores"""
    
    print("\n" + "="*80)
    print("🚀 DASHBOARD GLOBAL DE PROVEEDORES")
    print("="*80)
    inicio_total = time.time()

    container = st.container(border=True)

    with container:
        # === SELECTOR DE PERÍODO ===
        col1, col2, col3,col_fam1, col_fam2, col_fam3 = st.columns([2, 2, 1,2, 2, 1])

        with col1:
            periodo_opciones = {
                "Últimos 30 días": 30,
                "Últimos 60 días": 60,
                "Últimos 90 días": 90,
                "Últimos 6 meses": 180,
                "Último año": 365,
                "Personalizado": None,
            }

            periodo_seleccionado = st.selectbox(
                "📅 Período de análisis de ventas:",
                options=list(periodo_opciones.keys()),
                index=0,
            )

        with col2:
            if periodo_seleccionado == "Personalizado":
                col_a, col_b = st.columns(2)
                fecha_desde = col_a.date_input(
                    "Desde:",
                    value=datetime.now().date() - timedelta(days=30),
                )
                fecha_hasta = col_b.date_input(
                    "Hasta:",
                    value=datetime.now().date(),
                )

                if fecha_desde > fecha_hasta:
                    st.error("La fecha 'Desde' no puede ser mayor que 'Hasta'.")
                    st.stop()

                dias_periodo = (fecha_hasta - fecha_desde).days

            else:
                dias_periodo = periodo_opciones[periodo_seleccionado]
                fecha_hasta = datetime.now().date()
                fecha_desde = fecha_hasta - timedelta(days=dias_periodo)

                # 👇 Mostrar el rango calculado también cuando NO es personalizado
                # st.info(
                #     f"📅 Rango:\n"
                #     f"**Desde: {fecha_desde.strftime('%d/%m/%Y')}   -   hasta:{fecha_hasta.strftime('%d/%m/%Y')}**"
                # )
                st.markdown(
                            f"""
                            <div style:"text-align: center;">
                                📅 <span style:"text-align: center;">Rango</span><br>
                                <span class="label">Desde:</span>
                                <span class="date">{fecha_desde.strftime('%d/%m/%Y')}</span><br>
                                <span class="label">Hasta:</span>
                                <span class="date">{fecha_hasta.strftime('%d/%m/%Y')}</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

        with col3:
            st.metric("📆 Días", f"{dias_periodo}")

        # === CARGAR DATOS PRIMERO (para tener df_ventas disponible) ===
        print(f"\n🔄 Cargando datos para filtros...")
        df_ventas = get_ventas_data(
            credentials_path, 
            project_id, 
            bigquery_table,
            str(fecha_desde),
            str(fecha_hasta)
        )

        df_presupuesto = get_presupuesto_data(credentials_path, project_id)
        # df_familias = get_familias_data(credentials_path, project_id)
        df_familias = get_familias_data(credentials_path, project_id, bigquery_table)

        # Agregar familia/subfamilia a df_proveedores
        df_prov_con_familias = df_proveedores.merge(
            df_familias[['idarticulo', 'familia', 'subfamilia']],
            on='idarticulo',
            how='left'
        )

        # ⭐ FILTRAR SOLO ARTÍCULOS CON VENTAS EN EL PERÍODO
        articulos_con_ventas = df_ventas['idarticulo'].unique()
        df_prov_con_familias = df_prov_con_familias[
            df_prov_con_familias['idarticulo'].isin(articulos_con_ventas)
        ]

        print(f"   ✅ Artículos con ventas en período: {len(df_prov_con_familias):,}")

        # === FILTROS DE FAMILIA Y SUBFAMILIA ===

        with col_fam1:
            familias_disponibles = sorted(df_prov_con_familias['familia'].dropna().unique().tolist())
            
            familias_seleccionadas = st.multiselect(
                "🏷️ Filtrar por Familia:",
                options=familias_disponibles,
                default=familias_disponibles,  # ← TODAS SELECCIONADAS POR DEFECTO
                placeholder="Deselecciona las familias que NO quieres ver"
            )
            
            # Si se deseleccionan todas, mantener todas (evitar vacío)
            if not familias_seleccionadas:
                familias_seleccionadas = familias_disponibles
                st.warning("⚠️ Debes mantener al menos una familia seleccionada")

        with col_fam2:
            # Filtrar subfamilias según familias seleccionadas
            df_familias_filtradas = df_prov_con_familias[
                df_prov_con_familias['familia'].isin(familias_seleccionadas)
            ]
            
            subfamilias_disponibles = sorted(df_familias_filtradas['subfamilia'].dropna().unique().tolist())
            
            subfamilias_seleccionadas = st.multiselect(
                "📂 Filtrar por Subfamilia:",
                options=subfamilias_disponibles,
                default=subfamilias_disponibles,  # ← TODAS SELECCIONADAS POR DEFECTO
                placeholder="Deselecciona las subfamilias que NO quieres ver"
            )
            
            # Si se deseleccionan todas, mantener todas
            if not subfamilias_seleccionadas:
                subfamilias_seleccionadas = subfamilias_disponibles
                st.warning("⚠️ Debes mantener al menos una subfamilia seleccionada")

        with col_fam3:
            # Aplicar filtros para contar
            df_temp = df_prov_con_familias[
                df_prov_con_familias['familia'].isin(familias_seleccionadas)
            ]
            
            if subfamilias_seleccionadas:
                df_temp = df_temp[
                    df_temp['subfamilia'].isin(subfamilias_seleccionadas)
                ]
            
            # Mostrar cuántas están activas/totales
            total_familias = len(familias_disponibles)
            activas_familias = len(familias_seleccionadas)
            
            st.metric(
                "🎯 Artículos", 
                f"{format_miles(int(df_temp['idarticulo'].nunique()))}",
                delta=f"{activas_familias}/{total_familias} familias"
            )

        # === APLICAR FILTROS AL DATAFRAME PRINCIPAL ===
        df_proveedores_filtrado = df_prov_con_familias[
            df_prov_con_familias['familia'].isin(familias_seleccionadas)
        ].copy()

        if subfamilias_seleccionadas:
            df_proveedores_filtrado = df_proveedores_filtrado[
                df_proveedores_filtrado['subfamilia'].isin(subfamilias_seleccionadas)
            ]

        # Logs mejorados
        articulos_filtrados = df_temp['idarticulo'].unique()
        df_ventas_filtrado = df_ventas[df_ventas['idarticulo'].isin(articulos_filtrados)].copy()

        excluidas_familias = set(familias_disponibles) - set(familias_seleccionadas)
        excluidas_subfamilias = set(subfamilias_disponibles) - set(subfamilias_seleccionadas)

        print(f"\n🎯 FILTROS APLICADOS:")
        print(f"   ✅ Familias activas: {len(familias_seleccionadas)}/{len(familias_disponibles)}")
        if excluidas_familias:
            print(f"   ❌ Familias excluidas: {', '.join(excluidas_familias)}")
        print(f"   ✅ Subfamilias activas: {len(subfamilias_seleccionadas)}/{len(subfamilias_disponibles)}")
        if excluidas_subfamilias:
            print(f"   ❌ Subfamilias excluidas: {len(excluidas_subfamilias)} items")
        print(f"   📦 Artículos filtrados: {df_proveedores_filtrado['idarticulo'].nunique():,}")
    
        print(f"\n🎯 ARTÍCULOS DESPUÉS DE FILTROS:")
        print(f"   📦 En proveedores: {df_temp['idarticulo'].nunique():,}")
        print(f"   📊 Con ventas: {df_ventas_filtrado['idarticulo'].nunique():,}")
        # print(f"   💰 Venta filtrada: ${df_ventas_filtrado['importeConImpuestos'].sum():,.0f}")

        # === APLICAR FILTROS AL DATAFRAME PRINCIPAL ===
        df_proveedores_filtrado = df_prov_con_familias[
            df_prov_con_familias['familia'].isin(familias_seleccionadas)
        ].copy()

        if subfamilias_seleccionadas:
            df_proveedores_filtrado = df_proveedores_filtrado[
                df_proveedores_filtrado['subfamilia'].isin(subfamilias_seleccionadas)
            ]

        # Logs mejorados
        excluidas_familias = set(familias_disponibles) - set(familias_seleccionadas)
        excluidas_subfamilias = set(subfamilias_disponibles) - set(subfamilias_seleccionadas)

        print(f"\n🎯 FILTROS APLICADOS:")
        print(f"   ✅ Familias activas: {len(familias_seleccionadas)}/{len(familias_disponibles)}")
        if excluidas_familias:
            print(f"   ❌ Familias excluidas: {', '.join(excluidas_familias)}")
        print(f"   ✅ Subfamilias activas: {len(subfamilias_seleccionadas)}/{len(subfamilias_disponibles)}")
        if excluidas_subfamilias:
            print(f"   ❌ Subfamilias excluidas: {len(excluidas_subfamilias)} items")
        print(f"   📦 Artículos filtrados: {df_proveedores_filtrado['idarticulo'].nunique():,}")




    # 📊 DEBUG: Mostrar período seleccionado en consola
    print(f"\n{'='*80}")
    print(f"📅 PERÍODO SELECCIONADO")
    print(f"{'='*80}")
    print(f"   ├─ Opción: {periodo_seleccionado}")
    print(f"   ├─ Desde: {fecha_desde}")
    print(f"   ├─ Hasta: {fecha_hasta}")
    print(f"   └─ Días: {dias_periodo}")
    
    # === ESTILOS ===
    st.markdown("""
    <style>
        .metric-box {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            padding: 0.8rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            justify-content: center;
            border-left: 5px solid #2a5298;
            margin-bottom: .5rem;
        }
        .metric-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        .stSlider > div > div > label {
            margin-bottom: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    # ✅ CARGAR DATOS (con spinner visible)
    df_ventas = get_ventas_data(
        credentials_path, 
        project_id, 
        bigquery_table,
        str(fecha_desde),
        str(fecha_hasta)
    )
    
    df_presupuesto = get_presupuesto_data(credentials_path, project_id)
    
    # ranking = process_ranking_data(df_proveedores, df_ventas, df_presupuesto)
    ranking = process_ranking_data(df_proveedores_filtrado, df_ventas, df_presupuesto, df_familias)
    if ranking is None or ranking.empty:
        st.error("❌ No se pudieron cargar los datos")
        return
    
    # === KPIs ===
    col1, col11, col2, col3, col4, col5 = st.columns(6)
        
    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">💰 Ventas Totales</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Venta Total'].sum())}</div>
            </div>
            <div style="color: green; font-size: 12px; margin-top: 0.2rem;">
                ⬆️ {len(ranking)} proveedores
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col11:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">💰 Utilidad Total</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Utilidad'].sum())}</div>
            </div>
            <div style="color: green; font-size: 12px; margin-top: 0.2rem;">
                ⬆️ {len(ranking)} proveedores
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">💵 Presupuesto a 30 días</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Presupuesto'].sum())}</div>
            </div>
            <div style="color: #d35400; font-size: 12px; margin-top: 0.2rem;">
                📊 Inversión requerida
            </div>
        </div>
        """, unsafe_allow_html=True)

                # <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">{format_millones(ranking['Cantidad Vendida'].sum())}</div>
    with col3:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">📦 Cantidad Vendida</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">{format_miles(int(ranking['Cantidad Vendida'].sum()))}</div>
            </div>
            <div style="color: #555; font-size: 12px; margin-top: 0.2rem;">
                🎯 {df_ventas_filtrado['idarticulo'].nunique():,} art únicos
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">⚠️ Exceso de Stock</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Costo Exceso'].sum())}</div>
            </div>
            <div style="color: #888; font-size: 12px; margin-top: 0.2rem;">
                📊 {ranking['Art. con Exceso'].sum():,} artículos
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">❌ Sin Stock</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">{format_miles(int(ranking['Art. Sin Stock'].sum()))}</div>
            </div>
            <div style="color: #c0392b; font-size: 12px; margin-top: 0.2rem;">
                🔴 Artículos críticos
            </div>
        </div>
        """, unsafe_allow_html=True)

    # === VISUALIZACIONES ===
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🏆 Ranking por Venta Total")
        top_ventas_num = st.slider("Cantidad de proveedores (Ventas):", 5, 80, 20, step=5, key='slider_ventas')
        
        top_ventas = ranking.head(top_ventas_num).copy()
        top_ventas['Venta_M'] = top_ventas['Venta Total'] / 1_000_000
        top_ventas['Texto'] = top_ventas['Venta Total'].apply(lambda x: f"${x/1_000_000:.1f}M")
        
        fig_ventas = go.Figure(go.Bar(
            y=top_ventas['Proveedor'][::-1],
            x=top_ventas['Venta_M'][::-1],
            orientation='h',
            text=top_ventas['Texto'][::-1],
            textposition='outside',
            marker_color='#2ecc71',
            hovertemplate='<b>%{y}</b><br>Venta: %{text}<br>Participación: ' + 
                          top_ventas['% Participación Ventas'][::-1].apply(lambda x: f"{x:.1f}%") + '<extra></extra>'
        ))
        
        fig_ventas.update_layout(
            height=max(400, top_ventas_num * 25),
            margin=dict(t=10, b=10, l=10, r=40),
            xaxis=dict(visible=False),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig_ventas, width="stretch")
    
    with col2:
        st.markdown("#### 💰 Ranking por Presupuesto")
        top_presu_num = st.slider("Cantidad de proveedores (Presupuesto):", 5, 80, 20, step=5, key='slider_presu')
        
        ranking_presu = ranking.sort_values('Presupuesto', ascending=False).head(top_presu_num).copy()
        ranking_presu['Presupuesto_M'] = ranking_presu['Presupuesto'] / 1_000_000
        ranking_presu['Texto'] = ranking_presu['Presupuesto'].apply(lambda x: f"${x/1_000_000:.1f}M")
        
        fig_presu = go.Figure(go.Bar(
            y=ranking_presu['Proveedor'][::-1],
            x=ranking_presu['Presupuesto_M'][::-1],
            orientation='h',
            text=ranking_presu['Texto'][::-1],
            textposition='outside',
            marker_color='#e74c3c',
            hovertemplate='<b>%{y}</b><br>Presupuesto: %{text}<extra></extra>'
        ))
        
        fig_presu.update_layout(
            height=max(400, top_presu_num * 25),
            margin=dict(t=10, b=10, l=10, r=40),
            xaxis=dict(visible=False),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig_presu, width="stretch")
    
    # === TABLA RANKING ===
    st.markdown("### 📋 Ranking Detallado de Proveedores")
    
    df_display = ranking.copy()
    df_display['Venta Total'] = df_display['Venta Total'].apply(lambda x: f"${x:,.0f}")
    df_display['Costo Total'] = df_display['Costo Total'].apply(lambda x: f"${x:,.0f}")
    df_display['Utilidad'] = df_display['Utilidad'].apply(lambda x: f"${x:,.0f}")
    df_display['Presupuesto'] = df_display['Presupuesto'].apply(lambda x: f"${x:,.0f}")
    df_display['Costo Exceso'] = df_display['Costo Exceso'].apply(lambda x: f"${x:,.0f}")
    df_display['Rentabilidad %'] = df_display['Rentabilidad %'].apply(lambda x: f"{x:.2f}%")
    df_display['% Participación Presupuesto'] = df_display['% Participación Presupuesto'].apply(lambda x: f"{x:.2f}%")
    df_display['% Participación Ventas'] = df_display['% Participación Ventas'].apply(lambda x: f"{x:.2f}%")

    num_mostrar = st.slider("Cantidad de proveedores a mostrar:", 10, len(df_display), 20, step=5, key='slider_tabla')
    
    st.dataframe(
        df_display.head(num_mostrar)[[
            'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total', 'Utilidad', 'Rentabilidad %',
            '% Participación Presupuesto', 'Presupuesto', 'Artículos', 'Art. con Exceso', 
            'Costo Exceso', 'Art. Sin Stock'
        ]],
        width="stretch",
        hide_index=True
    )
    
    # === INSIGHTS ===
    st.markdown("### 💡 Insights Clave")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        top_proveedor = ranking.iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #4caf50'>
        <b>🏆 Proveedor Líder en Ventas</b><br>
        <b>{top_proveedor['Proveedor']}</b><br>
        💰 ${top_proveedor['Venta Total']:,.0f}<br>
        📊 {top_proveedor['% Participación Ventas']:.1f}% del total<br>
        📦 {top_proveedor['Artículos']} artículos
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        top_presupuesto = ranking.nlargest(1, 'Presupuesto').iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #ff9800'>
        <b>💰 Mayor Presupuesto Requerido</b><br>
        <b>{top_presupuesto['Proveedor']}</b><br>
        💵 ${top_presupuesto['Presupuesto']:,.0f}<br>
        📊 {top_presupuesto['% Participación Presupuesto']:.1f}% del total<br>
        📦 {top_presupuesto['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        mas_util = ranking.nlargest(1, 'Utilidad').iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #4caf50'>
        <b>🏆 Proveedor Líder en Utilidad</b><br>
        <b>{mas_util['Proveedor']}</b><br>
        💸 ${mas_util['Utilidad']:,.0f}<br>
        📦 {mas_util['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        peor_util = ranking.nsmallest(1, 'Utilidad').iloc[0]
        st.markdown(f"""
        <div style='background-color:#ffebee;padding:1rem;border-radius:10px;border-left:5px solid #f44336'>
        <b>⚠️ Proveedor con Menor Utilidad</b><br>
        <b>{peor_util['Proveedor']}</b><br>
        💸 ${peor_util['Utilidad']:,.0f}<br>
        📦 {peor_util['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
                
    with col5:
        mas_exceso = ranking.nlargest(1, 'Costo Exceso').iloc[0]
        st.markdown(f"""
        <div style='background-color:#ffebee;padding:1rem;border-radius:10px;border-left:5px solid #f44336'>
        <b>⚠️ Mayor Exceso de Stock</b><br>
        <b>{mas_exceso['Proveedor']}</b><br>
        💸 ${mas_exceso['Costo Exceso']:,.0f} inmovilizado<br>
        📊 {mas_exceso['Art. con Exceso']} artículos<br>
        🔄 Optimizar inventario
        </div>
        """, unsafe_allow_html=True)
       
    # === EXPORTAR RANKING ===
    # st.markdown("---")

    # # Preparar dataframe para exportación
    # df_export = ranking[[
    #     'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total',
    #     'Utilidad', 'Rentabilidad %', '% Participación Presupuesto', 'Presupuesto',
    #     'Artículos', 'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
    # ]].copy()

    # # Generar Excel
    # output = crear_excel_ranking(df_export, str(fecha_desde), str(fecha_hasta))
    # nombre_archivo = generar_nombre_archivo("ranking_proveedores")

    # st.download_button(
    #     label="📥 Descargar Ranking Completo (Excel)",
    #     data=output,
    #     file_name=nombre_archivo,
    #     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    #     use_container_width=True
    # )

    # === EXPORTAR RANKING ===
    st.markdown("---")
    st.markdown("### 📥 Exportar Datos")

    col_btn1, col_btn2 = st.columns(2)

    # ============================================
    # BOTÓN 1: DESCARGAR RANKING COMPLETO (SIN FILTROS)
    # ============================================
    with col_btn1:
        st.markdown("#### 📊 Ranking Completo")
        st.caption("Incluye TODOS los proveedores sin aplicar filtros de familia/subfamilia")
        
        # Calcular ranking SIN filtros de familia/subfamilia
        print(f"\n{'='*60}")
        print("📊 GENERANDO RANKING COMPLETO (SIN FILTROS)")
        print(f"{'='*60}")
        inicio_completo = time.time()
        
        ranking_completo = process_ranking_data(
            df_prov_con_familias,  # ← SIN filtrar
            df_ventas,             # Ventas del período seleccionado
            df_presupuesto,
            df_familias
        )
        
        tiempo_completo = time.time() - inicio_completo
        print(f"   ✅ Ranking completo generado")
        print(f"   📦 Proveedores: {len(ranking_completo):,}")
        print(f"   ⏱️  Tiempo: {tiempo_completo:.2f}s")
        print(f"{'='*60}\n")
        
        # Preparar dataframe completo
        df_export_completo = ranking_completo[[
            'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total',
            'Utilidad', 'Rentabilidad %', '% Participación Presupuesto', 'Presupuesto',
            'Artículos', 'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
        ]].copy()
        
        # Generar Excel completo
        output_completo = crear_excel_ranking(
            df_export_completo, 
            str(fecha_desde), 
            str(fecha_hasta),
            filtros_aplicados=False  # ← Nuevo parámetro
        )
        nombre_archivo_completo = generar_nombre_archivo("ranking_completo")
        
        st.download_button(
            label=f"📥 Descargar Ranking Completo ({len(ranking_completo)} proveedores)",
            data=output_completo,
            file_name=nombre_archivo_completo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="secondary"
        )
        
        # Mostrar resumen
        st.info(f"""
        **Incluye:**
        - ✅ Todas las familias
        - ✅ Todas las subfamilias
        - 📅 Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}
        - 📊 {len(ranking_completo):,} proveedores
        - 💰 ${format_millones(ranking_completo['Venta Total'].sum())} en ventas
        """)

    # ============================================
    # BOTÓN 2: DESCARGAR RANKING FILTRADO
    # ============================================
    with col_btn2:
        st.markdown("#### 🎯 Ranking Filtrado")
        st.caption("Solo incluye los filtros actualmente seleccionados")
        
        # ranking ya está calculado con filtros arriba
        print(f"\n{'='*60}")
        print("🎯 GENERANDO RANKING FILTRADO")
        print(f"{'='*60}")
        print(f"   📦 Proveedores filtrados: {len(ranking):,}")
        print(f"   💰 Venta filtrada: ${ranking['Venta Total'].sum():,.0f}")
        print(f"{'='*60}\n")
        
        # Preparar dataframe filtrado
        df_export_filtrado = ranking[[
            'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total',
            'Utilidad', 'Rentabilidad %', '% Participación Presupuesto', 'Presupuesto',
            'Artículos', 'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
        ]].copy()
        
        # Generar Excel filtrado
        output_filtrado = crear_excel_ranking(
            df_export_filtrado, 
            str(fecha_desde), 
            str(fecha_hasta),
            filtros_aplicados=True,  # ← Nuevo parámetro
            familias_activas=familias_seleccionadas,
            subfamilias_activas=subfamilias_seleccionadas
        )
        nombre_archivo_filtrado = generar_nombre_archivo("ranking_filtrado")
        
        st.download_button(
            label=f"📥 Descargar Ranking Filtrado ({len(ranking)} proveedores)",
            data=output_filtrado,
            file_name=nombre_archivo_filtrado,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
        
        # Mostrar resumen con filtros aplicados
        st.success(f"""
        **Filtros aplicados:**
        - 🏷️ {len(familias_seleccionadas)}/{len(familias_disponibles)} familias
        - 📂 {len(subfamilias_seleccionadas)}/{len(subfamilias_disponibles)} subfamilias
        - 📅 Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}
        - 📊 {len(ranking):,} proveedores
        - 💰 ${format_millones(ranking['Venta Total'].sum())} en ventas
        """)