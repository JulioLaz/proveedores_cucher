import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
from io import BytesIO
import plotly.graph_objects as go
from google.cloud import bigquery  # ← AGREGAR ESTO

# Importar funciones cacheadas
from utils.ranking_proveedores import crear_excel_ranking, generar_nombre_archivo
from utils.proveedor_exporter import generar_reporte_proveedor, obtener_ids_originales

from components.cobertura_stock_exporter import generar_reporte_cobertura, obtener_metricas_cobertura  # ← CAMBIAR ESTO
from components.global_dashboard_cache import (get_ventas_data, get_presupuesto_data, get_familias_data, process_ranking_data)
from components.ranking_export_section import show_ranking_section
from components.cobertura_section import show_cobertura_section
from components.proveedor_report_section import show_proveedor_report_section
from components.cobertura_stock_exporter import CoberturaStockExporter
from components.global_dashboard_cache import get_ventas_agregadas_stock  # ← NUEVA FUNCIÓN
from components.analisis_stock_rentables_simple import main_analisis_stock_simple  

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
        col1, col2, col_fam1, col_fam2, col_fam3, col_fam4 = st.columns([1.8, 1.3, 2, 2, 1.1,0.9])

        with col1:
            periodo_opciones = {
                "Últimos 30 días": 30,
                "Últimos 60 días": 60,
                "Últimos 90 días": 90,
                # "Últimos 6 meses": 180,
                "Año 2025": ("2025-01-01", "2025-12-31"),
                "Año 2024": ("2024-01-01", "2024-12-31"),
                "Enero 2025": ("2025-01-01", "2025-01-31"),
                "Febrero 2025": ("2025-02-01", "2025-02-28"),
                "Marzo 2025": ("2025-03-01", "2025-03-31"),
                "Abril 2025": ("2025-04-01", "2025-04-30"),
                "Mayo 2025": ("2025-05-01", "2025-05-31"),
                "Junio 2025": ("2025-06-01", "2025-06-30"),
                "Julio 2025": ("2025-07-01", "2025-07-31"),
                "Agosto 2025": ("2025-08-01", "2025-08-31"),
                "Septiembre 2025": ("2025-09-01", "2025-09-30"),
                "Octubre 2025": ("2025-10-01", "2025-10-31"),
                "Noviembre 2025": ("2025-11-01", "2025-11-30"),
                "Diciembre 2025": ("2025-12-01", "2025-12-31"),
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
                            value=fecha_maxima_disponible,
                            max_value=fecha_maxima_disponible
                        )

                        if fecha_desde > fecha_hasta:
                            st.error("La fecha 'Desde' no puede ser mayor que 'Hasta'.")
                            st.stop()

                        dias_periodo = (fecha_hasta - fecha_desde).days

                    else:
                        valor_periodo = periodo_opciones[periodo_seleccionado]
                        
                        # Si es una tupla (meses completos), usar las fechas directamente
                        if isinstance(valor_periodo, tuple):
                            from datetime import datetime
                            fecha_desde = datetime.strptime(valor_periodo[0], "%Y-%m-%d").date()
                            fecha_hasta = datetime.strptime(valor_periodo[1], "%Y-%m-%d").date()
                            dias_periodo = (fecha_hasta - fecha_desde).days + 1
                        # Si es un número (días relativos), calcular desde fecha_maxima_disponible
                        else:
                            dias_periodo = valor_periodo
                            fecha_hasta = fecha_maxima_disponible
                            fecha_desde = fecha_maxima_disponible - timedelta(days=dias_periodo)

                        st.markdown(
                            f"""
                            <div style="background: linear-gradient(135deg, #ffffff 0%, #f3e3a3 100%);
                                border: 2px solid #f3c221;
                                border-radius: 10px;
                                padding: 5px;
                                box-shadow: 0 2px 4px rgba(33, 150, 243, 0.15);
                                transition: all 0.3s ease;height:150px">
                                <span style='font-weight:semi-bold;padding: 5px;font-size:.8rem'>⏳ Rango de fechas</span><br>
                                <div style='font-weight:400;padding-top: 5px;padding-left: .7rem;font-size:.8rem'>
                                    Desde: {fecha_desde.strftime('%d %b %Y')}
                                </div>
                                <div style='font-weight:400; padding-left: 1rem;font-size:.8rem'>
                                    Hasta: {fecha_hasta.strftime('%d %b %Y')}
                                </div>
                                <div style='font-weight:semi-bold;padding-top: 5px;padding-left: 5px;font-size:.8rem'> 📆 Días de actividad:</div>
                                <div style='font-weight:400;margin-left:2.8rem;font-size:.7rem'>{dias_periodo} días</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

        # === CARGAR DATOS PRIMERO (para tener df_ventas disponible) ===
        print(f"\n🔄 Cargando datos para filtros...")
        df_ventas = get_ventas_data(
            credentials_path, 
            project_id, 
            bigquery_table,
            str(fecha_desde),
            str(fecha_hasta)
        )

        print('DF_VENTAS  -- '*50)
        print('DF_VENTAS  -- '*50)
        print('DF_VENTAS:',df_ventas.columns)
        print('DF_VENTAS:',df_ventas.head())
        print('DF_VENTAS  -- '*50)
        print('DF_VENTAS  -- '*50)
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
            # <div style="text-align: center; margin-top: 0.5rem;">
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, #ffffff 0%, #f3e3a3 100%);
                                border: 2px solid #f3c221;
                                border-radius: 10px;
                                padding: 5px;
                                box-shadow: 0 2px 4px rgba(33, 150, 243, 0.15);
                                transition: all 0.3s ease;height:150px">                        
                <div style="font-size: 12px; color: #555; margin-bottom: 0.3rem;">📊 Filtros</div>
                <div style="font-size: 12px; color: #666; margin-top: 0.2rem;">
                    familias
                </div>
                <div style="font-size: 14px; font-weight: bold; color: #1e3c72;">
                    🏷️ {activas_familias}/{total_familias}
                </div>
                <div style="font-size: 12px; color: #666; margin-top: 0.2rem;">
                    subfamilias
                </div>
                <div style="font-size: 14px; font-weight: bold; color: #1e3c72; margin-top: 0.3rem;">
                    📂 {activas_subfamilias}/{total_subfamilias}
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
    col1, col2, col3 = st.columns(3)

    with col1:
        # 🎯 Título dinámico según filtros
        st.markdown("#### 🏆 Ranking por Venta Total")

        top_ventas_num = st.slider("Cantidad de proveedores (Ventas):", 5, 80, 20, step=5, key='slider_ventas')

        # ✅ ranking YA está filtrado, así que esto ya usa datos filtrados
        top_ventas = ranking.head(top_ventas_num).copy()
        top_ventas['Venta_M'] = top_ventas['Venta Total'] / 1_000_000

        # 🎨 Escala de colores según rentabilidad
        # Asumiendo que existe columna 'Rentabilidad %' en el dataframe
        import numpy as np

        def get_color_by_rentability(rentabilidad):
            """
            Verde oscuro (alta rent) → Amarillo (media) → Rojo (baja)
            """
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
            marker_color=top_ventas['Color'][::-1].tolist(),  # ← Color dinámico por rentabilidad
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
            margin=dict(t=30, b=10, l=10, r=50),  # ← Más margen derecho para el texto con rentabilidad
            xaxis=dict(
                visible=False,
                range=[0, max_venta * 1.30]  # ← 20% extra para el texto más largo
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

        st.plotly_chart(fig_ventas, width='stretch')

    with col2:
        # 🎯 Título dinámico según filtros
        st.markdown("#### 💸 Ranking por Utilidad")

        top_util_num = st.slider("Cantidad de proveedores (Utilidad):", 5, 80, 20, step=5, key='slider_util')

        # ✅ ranking YA está filtrado, usar los mismos datos filtrados que ventas
        ranking_util = ranking.sort_values('Utilidad', ascending=False).head(top_util_num).copy()
        ranking_util['Utilidad_M'] = ranking_util['Utilidad'] / 1_000_000
        ranking_util['Texto'] = ranking_util['Utilidad'].apply(lambda x: f"${x/1_000_000:.1f}M")

        # Color dinámico según filtros
        color_barra = '#9b59b6' if not filtros_activos else '#8e44ad'  # Morado normal, Morado oscuro si hay filtros

        fig_util = go.Figure(go.Bar(
            y=ranking_util['Proveedor'][::-1],
            x=ranking_util['Utilidad_M'][::-1],
            orientation='h',
            text=ranking_util['Texto'][::-1],
            textposition='outside',
            cliponaxis=False,  # ← Permite que el texto salga del área del gráfico
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
                range=[0, max_util * 1.15]  # ← 15% extra para el texto
            ),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            title=dict(
                text=titulo_grafico,
                # text=titulo_grafico if filtros_activos else None,
                font=dict(size=12, color='#8e44ad'),
                x=0.5,
                xanchor='center'
            )
        )
        st.plotly_chart(fig_util, width='stretch')

    with col3:
        # 🎯 Título dinámico según filtros
        st.markdown("#### 💰 Ranking por Presupuesto")

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
            cliponaxis=False,  # ← Permite que el texto salga del área del gráfico
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
                range=[0, max_presu * 1.15]  # ← 15% extra para el texto
            ),
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
        st.plotly_chart(fig_presu, width='stretch')

    # === TABLA RANKING ===
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

    num_mostrar = st.slider("Cantidad de proveedores a mostrar:", 10, len(df_display), 20, step=5, key='slider_tabla')
    
    st.dataframe(
        df_display.head(num_mostrar)[[
            'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total', 'Utilidad', 'Rentabilidad %',
            '% Participación Presupuesto', 'Presupuesto', 'Artículos', 'Art. con Exceso', 
            'Costo Exceso', 'Art. Sin Stock'
        ]],
        width='stretch',
        hide_index=True
    )
    
    # === INSIGHTS ===
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
       
     # Preparar DataFrame para cobertura (con datos filtrados)
    print(f"\n{'='*80}")
    print("📦 PREPARANDO DATOS PARA COBERTURA DE STOCK")
    print(f"{'='*80}")

    # Preparar DataFrame para cobertura (con datos filtrados)
    print(f"\n{'='*80}")
    print("📦 PREPARANDO DATOS PARA COBERTURA DE STOCK")
    print(f"{'='*80}")

    # Crear DataFrame con ventas + datos de proveedor/familia
    df_ventas_cobertura = df_ventas_filtrado.merge(
        df_proveedores_filtrado[['idarticulo', 'proveedor', 'familia', 'subfamilia']],
        on='idarticulo',
        how='left'
    )

    print(f"🔍 Columnas en df_ventas_cobertura: {df_ventas_cobertura.columns.tolist()}")

    # ═══ CALCULAR UTILIDAD TOTAL ═══
    if 'utilidad_total' not in df_ventas_cobertura.columns:
        if 'venta_total' in df_ventas_cobertura.columns and 'costo_total' in df_ventas_cobertura.columns:
            df_ventas_cobertura['utilidad_total'] = df_ventas_cobertura['venta_total'] - df_ventas_cobertura['costo_total']
            print(f"✅ Utilidad calculada: venta_total - costo_total")
        else:
            df_ventas_cobertura['utilidad_total'] = 0
            print(f"⚠️ No se pudo calcular utilidad, usando 0")

    # ═══ OBTENER DESCRIPCIÓN ═══
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
        how='left')

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
    print(f"{'='*80}\n")

################################################################################

    # Obtener métricas de cobertura
    with st.spinner("Calculando métricas de cobertura..."):
        # Usar el mismo filtro de utilidad si existe el session_state
        utilidad_min_metricas = st.session_state.get('utilidad_minima_cobertura', 10000)

        metricas_stock = obtener_metricas_cobertura(
            df_para_cobertura,
            fecha_desde,
            fecha_hasta,
            credentials_path,
            # project_id,
            # utilidad_min_metricas  # ← NUEVO
        )

################################################################################

    st.markdown("---")
    # st.markdown("### 📊 Análizar y descargar tablas xlsx")
    st.markdown(
        """<div style=" text-align: center; padding: 1rem; border: 1px solid gray; border-radius: 5px; background: #f0e69b; font-size: 1.8rem; font-weight: 600;">
        📊 Análizar y descargar tablas xlsx: Seleccionar reporte</div>
        """, unsafe_allow_html=True)
    st.markdown(
    """
    <style>
    /* Ajustar la distribución de los tabs */
    .stTabs [role="tablist"] {
        justify-content: space-around;
    }

    /* Estilo general de los títulos de las tabs */
    .stTabs [data-baseweb="tab"] {
        font-size: 1.5rem;
        font-weight: 600;
        color: #444;
        background-color: #f0e69b;
        border-radius: 5px;
        padding: 0.5rem 1rem;
    }

    /* Tab seleccionada */
    .stTabs [aria-selected="true"] {
        font-weight: bold;
        color: #000;
        background-color: #ffd700;
        border-bottom: 5px solid #0066cc;
    }
    </style>
    """,
    unsafe_allow_html=True)

    # ANTES de crear las tabs, inicializa el estado si no existe
    if 'active_tab_index' not in st.session_state:
        st.session_state['active_tab_index'] = 0

    tab1, tab2, tab3, tab4 = st.tabs([
      "1- 📊 Rankings de Proveedores por Ventas", 
      "2- 💰 Utilidad vs Cobertura", 
      "3- 📦 Proveedor Ventas vs Presupuesto | Cobertura",
      "4- 📊 Análisis de Stock Rentable"
   ])


    # =================================================================
    # TAB 1: RANKINGS (COMPLETO Y FILTRADO)
    # =================================================================
    with tab1:
        st.markdown(
        "<h3 style='text-align:center; color:rgb(30, 60, 114);font-weight: bold;'>📊 Rankings de Proveedores por Ventas</h3>",
        unsafe_allow_html=True)
        show_ranking_section(
            df_prov_con_familias=df_prov_con_familias,
            df_proveedores=df_proveedores,
            df_ventas=df_ventas,
            df_presupuesto=df_presupuesto,
            df_familias=df_familias,
            ranking=ranking,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            familias_disponibles=familias_disponibles,
            subfamilias_disponibles=subfamilias_disponibles,
            familias_seleccionadas=familias_seleccionadas,
            subfamilias_seleccionadas=subfamilias_seleccionadas
        )

    # =================================================================
    # TAB 2: COBERTURA DE STOCK Y UTILIDAD
    # =================================================================
    cnt_proveedores = len(ranking)
    st.session_state['cnt_proveedores_cobertura'] = cnt_proveedores
    pass

    with tab2:
        show_cobertura_section(
            df_para_cobertura=df_para_cobertura,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            credentials_path=credentials_path,
            project_id=project_id,
            familias_seleccionadas=familias_seleccionadas,
            subfamilias_seleccionadas=subfamilias_seleccionadas,
            cnt_proveedores=cnt_proveedores,
        )
        pass
    
    # =================================================================
    # TAB 3: REPORTES INDIVIDUALES POR PROVEEDOR
    # =================================================================
    with tab3:
        # ============================================
        # PREPARAR PRESUPUESTO CON VENTAS (IMPORTANTE!)
        # ============================================
        
        # DEBUG: Ver columnas de df_ventas
        print(f"\n{'='*80}")
        print("🔍 DEBUG: Preparando presupuesto con ventas")
        print(f"{'='*80}")
        print(f"Columnas df_ventas: {df_ventas.columns.tolist()}")
        print(f"Total registros: {len(df_ventas):,}")
        print(f"{'='*80}\n")
        
        # Calcular ventas por artículo desde df_ventas
        ventas_por_articulo = df_ventas.groupby('idarticulo').agg(
            venta_total_articulo=('venta_total', 'sum')
        ).reset_index()
        
        # Hacer merge de presupuesto con ventas
        df_presupuesto_con_ventas = df_presupuesto.merge(
            ventas_por_articulo, 
            on='idarticulo', 
            how='left'
        )
        df_presupuesto_con_ventas['venta_total_articulo'].fillna(0, inplace=True)
        
        print(f"   ✅ Presupuesto enriquecido con ventas: {len(df_presupuesto_con_ventas):,} artículos\n")

        # Llamar a la sección de reportes
        show_proveedor_report_section(
            ranking=ranking,
            df_presupuesto_con_ventas=df_presupuesto_con_ventas,
            df_proveedores=df_proveedores,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            familias_disponibles=familias_disponibles,          # ← AGREGAR
            subfamilias_disponibles=subfamilias_disponibles,    # ← AGREGAR
            familias_seleccionadas=familias_seleccionadas,
            subfamilias_seleccionadas=subfamilias_seleccionadas
         )
            
    with tab4:
        st.markdown(
            "<h3 style='text-align:center; color:rgb(30, 60, 114);font-weight: bold;'>📦 Artículos Rentables - Análisis de Stock</h3>",
            unsafe_allow_html=True)
        st.markdown(
            "<h4 style='text-align:center; color:#555;font-weight: bold;'>⚠️ Los filtros principales no aplican en esta sección!</h4>",
            unsafe_allow_html=True)
        

        # ═══════════════════════════════════════════════════════════════════════════
        # CARGAR DATOS (con spinner visible)
        # ═══════════════════════════════════════════════════════════════════════════
        
        with st.spinner("🔄 Cargando datos para análisis de stock... (~10 segundos)"):
            
            print(f"\n{'='*80}")
            print(f"📦 TAB4: CARGANDO DATOS PARA ANÁLISIS DE STOCK")
            print(f"{'='*80}")
            
            # Determinar año actual
            año_actual = fecha_maxima_disponible.year
            
            print(f"   • Año de análisis: {año_actual}")
            print(f"   • Tabla: {bigquery_table}")
            
            # 1. Cargar VENTAS AGREGADAS desde BigQuery (~7 segundos)
            df_ventas_agregadas = get_ventas_agregadas_stock(
                credentials_path=credentials_path,
                project_id=project_id,
                bigquery_table=bigquery_table,
                año=año_actual
            )
            
            if df_ventas_agregadas is None or len(df_ventas_agregadas) == 0:
                st.error("❌ No se pudieron cargar datos de ventas desde BigQuery")
                print(f"{'='*80}\n")
                st.stop()
            
            print(f"   ✅ Ventas agregadas: {len(df_ventas_agregadas):,} artículos")
            
            # 2. Cargar STOCK ACTUAL desde BigQuery (~2 segundos)
            exporter = CoberturaStockExporter(
                credentials_path=credentials_path,
                project_id=project_id
            )
            
            if not exporter.conectar_bigquery():
                st.error("❌ No se pudo conectar a BigQuery para cargar stock")
                print(f"{'='*80}\n")
                st.stop()
            
            df_stock = exporter.obtener_stock_bigquery()
            
            if df_stock is None or len(df_stock) == 0:
                st.error("❌ No se pudieron cargar datos de stock desde BigQuery")
                print(f"{'='*80}\n")
                st.stop()
            
            print(f"   ✅ Stock cargado: {len(df_stock):,} artículos")
            print(f"{'='*80}\n")

       # Explicación clara del análisis
        with st.expander("ℹ️ ¿Qué hace este análisis y qué contiene?", expanded=False):
            st.markdown("""
            ### 📊 **Este análisis identifica:**
            
            **🎯 Artículos rentables con análisis de inventario**
            - Analiza **todos los artículos del año o por trimestre** con sus ventas y utilidades
            - Calcula el **margen de utilidad** de cada artículo
            - Evalúa la **velocidad de venta** y **días de actividad**
            - Compara **stock actual vs velocidad de venta**
            
            ### 📈 **Filtros y criterios aplicados:**
            
            - **Margen mínimo**: Solo artículos con margen >= 25%
            - **Actividad mínima**: Artículos activos >= 270 días en el año
            - **Datos del año actual**: {año_actual}
            - **⚠️ No aplican los filtros de familia/subfamilia de la pantalla principal**
            
            ### 📋 **El análisis muestra:**
            
            1. **💰 Top artículos por utilidad** generada en el año
            2. **📦 Stock actual** de cada artículo
            3. **⏱️ Días de cobertura** según velocidad de venta
            4. **🚦 Clasificación de riesgo de quiebre:**
            - 🔴 **Crítico**: Stock agotándose en < 15 días
            - 🟠 **Bajo**: 15-30 días de cobertura
            - 🟢 **Óptimo**: 30-60 días de cobertura
            - 🔵 **Alto**: 60-90 días de cobertura
            - ⚫ **Exceso**: > 90 días de cobertura
            5. **📊 Métricas trimestrales** (Q1, Q2, Q3, Q4) de ventas
            6. **🎯 Velocidad de venta diaria** promedio
            
            ### 🎯 **Utilidad del análisis:**
            - Identificar artículos más rentables que necesitan reposición urgente
            - Priorizar compras según rentabilidad + riesgo de quiebre
            - Detectar productos rentables con exceso de stock
            - Optimizar capital enfocándose en lo que más utilidad genera
            - Análisis histórico completo del año para mejor toma de decisiones
            
            ### 📥 **Descarga disponible:**
            El reporte exportable incluye todos los artículos filtrados con:
            - Datos completos de ventas por trimestre
            - Análisis de stock y cobertura
            - Métricas de rentabilidad y velocidad de venta
            - Clasificación de riesgo y recomendaciones
            """.replace("{año_actual}", str(año_actual)))


        # ═══════════════════════════════════════════════════════════════════════════
        # ANÁLISIS Y VISUALIZACIÓN
        # ═══════════════════════════════════════════════════════════════════════════
        
        # Llamar al módulo de análisis
        main_analisis_stock_simple(
            df_ventas_agregadas=df_ventas_agregadas,
            df_stock=df_stock,
            df_presupuesto=df_presupuesto  # Ya disponible en la función
        )