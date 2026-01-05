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
from components.tab1_ranking_ventas import main_tab1_ranking_ventas  # ← NUEVO MÓDULO TAB1  
# Busca la sección de imports de components y agrega:
from components.tab_prediccion_presupuesto import render_tab_prediccion_presupuesto

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
        # AQUÍ, ANTES DE LAS TABS, AGREGA:

    st.markdown("""
            <style>
            .stMultiSelect {
                background: linear-gradient(135deg, #ffffff 0%, #d1e8ff 100%);
                border: 2px solid #1e90ff;
                border-radius: 10px;
                padding: 2px;
                box-shadow: 0 2px 6px rgba(30, 144, 255, 0.25);
                transition: all 0.3s ease;
            }
            </style>
            """, unsafe_allow_html=True)    
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

    container_filters = st.container(border=True)

    with container_filters:
        st.markdown("#### ⚙️ Ajustar filtros generales: Período - Familia - Subfamilia ")

        # === SELECTOR DE PERÍODO ===
        col1, col2, col3, col4, col5 = st.columns([1.8, 2, 2, 1.4, 1.2])

        with col1:

            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, #ffffff 0%, #f3e3a3 100%);
                    border: 2px solid #f3c221;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(33, 150, 243, 0.15);
                    transition: all 0.3s ease;
                    min-height:auto;
                    display:flex;
                    flex-direction:column;
                    justify-content:center;
                    overflow:hidden;">
                    <span style="font-weight:600;padding-top: 5px;font-size:1rem; text-align:center;">
                        🆙 Actualizado al:
                    </span>
                    <div style="font-weight:400;font-size:.9rem; text-align:center;">
                        {fecha_maxima_disponible.strftime('%d %B %Y')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

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

            st.markdown("""
            <style>
            .stSelectbox {
                background: linear-gradient(135deg, #ffffff 0%, #d1e8ff 100%);
                border: 2px solid #1e90ff;
                border-radius: 10px;
                padding: 4px;
                box-shadow: 0 2px 6px rgba(30, 144, 255, 0.25);
                transition: all 0.3s ease;
            }
            </style>
            """, unsafe_allow_html=True)

            periodo_seleccionado = st.selectbox(
                "📅 Período de análisis de ventas:",
                options=list(periodo_opciones.keys()),
                index=0,
            )
    # with col2:
        if periodo_seleccionado == "Personalizado":
            col_a, col_b = st.columns(2)
            fecha_desde = col_a.date_input(
                "Desde:",
                value=fecha_maxima_disponible - timedelta(days=30),
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

            if isinstance(valor_periodo, tuple):
                from datetime import datetime
                fecha_desde = datetime.strptime(valor_periodo[0], "%Y-%m-%d").date()
                fecha_hasta = datetime.strptime(valor_periodo[1], "%Y-%m-%d").date()
                dias_periodo = (fecha_hasta - fecha_desde).days + 1
            else:
                dias_periodo = valor_periodo
                fecha_hasta = fecha_maxima_disponible
                fecha_desde = fecha_maxima_disponible - timedelta(days=dias_periodo)

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

        # with col_fam1:
        with col2:
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

        with col3:
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

        with col4:
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, #ffffff 0%, #f3e3a3 100%);
                    border: 2px solid #f3c221;
                    border-radius: 10px;
                    padding: 5px;
                    box-shadow: 0 2px 4px rgba(33, 150, 243, 0.15);
                    transition: all 0.3s ease;
                    min-height:154px;
                    display:flex;
                    flex-direction:column;
                    justify-content:space-between;
                    overflow:hidden;">
                    <span style='font-weight:600;padding: 5px;font-size:.9rem; text-align: center;'>⏳ Rango de fechas</span>
                    <div style='font-weight:400;font-size:.9rem; text-align: center;'>
                        Desde: {fecha_desde.strftime('%d %b %Y')}
                    </div>
                    <div style='font-weight:400;font-size:.9rem; text-align: center;'>
                        Hasta: {fecha_hasta.strftime('%d %b %Y')}
                    </div>
                    <div style='font-weight:600;padding-left:5px;font-size:.9rem; text-align: center;'>📆 Días de actividad:</div>
                    <div style='font-weight:400;font-size:.9rem; text-align: center;'>
                        {dias_periodo} días
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col5:
            # Filtrar dataframe según familias y subfamilias seleccionadas
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
            
            # Calcular totales de familias y subfamilias
            total_familias = len(familias_disponibles)
            activas_familias = len(familias_seleccionadas)
            total_subfamilias = len(subfamilias_disponibles)
            activas_subfamilias = len(subfamilias_seleccionadas)
            
            # Mostrar métricas en un solo bloque HTML estilizado
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #ffffff 0%, #f3e3a3 100%);
                border: 2px solid #f3c221;
                border-radius: 10px;
                padding: 3px;
                box-shadow: 0 2px 4px rgba(33, 150, 243, 0.15);
                transition: all 0.3s ease;
                min-height:154px;
                display:flex;
                flex-direction:column;
                justify-content:space-between;
                overflow:hidden;">
                <div style="font-size: 15px; color: #666; text-align:center;">
                    🎯 artículos
                </div>
                <div style="font-size: 14px; font-weight: bold; color: #1e3c72; text-align:center;">
                    {format_miles(articulos_filtrados)} / {format_miles(articulos_totales)}
                </div>
                <div style="font-size: 15px; color: #666; text-align:center;">
                    🏷️ familias
                </div>
                <div style="font-size: 14px; font-weight: bold; color: #1e3c72; text-align:center;">
                    {activas_familias}/{total_familias}
                </div>
                <div style="font-size: 15px; color: #666; text-align:center;">
                    📂 subfamilias
                </div>
                <div style="font-size: 14px; font-weight: bold; color: #1e3c72; text-align:center;">
                    {activas_subfamilias}/{total_subfamilias}
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
    

    container_kpis = st.container(border=True)

    with container_kpis:

        st.markdown("### 💹 Indicadores generales")

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
    
    # st.markdown("---")
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
         font-size: 1rem;          /* tamaño de fuente */
         font-weight: 800;         /* negrita */
         height: 50px;             /* altura mayor */
         line-height: 50px;        /* centra el texto verticalmente */
         padding-top: 5px;         /* opcional: más espacio arriba */
         padding-bottom: 5px;      /* opcional: más espacio abajo */
         transition: all 0.2s ease-in-out;        
    }
    </style>
    """,
    unsafe_allow_html=True)

    # ANTES de crear las tabs, inicializa el estado si no existe
    if 'active_tab_index' not in st.session_state:
        st.session_state['active_tab_index'] = 0

#####################################################################################
#### tooltips para tabs
#####################################################################################
    # st.markdown(
    # """
    # <style>
    # /* Ajustar la distribución de los tabs */
    # .stTabs [role="tablist"] {
    #     justify-content: space-around;
    #     overflow: visible !important;
    # }

    # /* Estilo general de los títulos de las tabs */
    # .stTabs [data-baseweb="tab"] {
    #     font-size: 1.5rem;
    #     font-weight: 600;
    #     color: #444;
    #     background-color: #f0e69b;
    #     border-radius: 5px;
    #     padding: 0.5rem 1rem;
    #     position: relative;
    #     overflow: visible !important;
    # }

    # /* Tab seleccionada */
    # .stTabs [aria-selected="true"] {
    #     font-weight: bold;
    #     color: #000;
    #     background-color: #ffd700;
    #     border-bottom: 5px solid #0066cc;
    #     font-size: 1rem;
    #     font-weight: 800;
    #     height: 50px;
    #     line-height: 50px;
    #     padding-top: 5px;
    #     padding-bottom: 5px;
    #     transition: all 0.2s ease-in-out;        
    # }

    # /* TOOLTIPS - Posición absoluta, 1rem arriba, fondo transparente */
    # .stTabs [data-baseweb="tab"]:nth-child(1):hover::after {
    #     content: "Rankings de proveedores, análisis de desempeño y reportes detallados";
    #     position: absolute;
    #     top: -.8rem;
    #     left: 50%;
    #     transform: translateX(-50%) translateY(-100%);
    #     background: rgba(45, 55, 72, 0.8);  /* Fondo semi-transparente */
    #     color: white;
    #     padding: 12px 18px;
    #     border-radius: 8px;
    #     font-size: 0.85rem;
    #     font-weight: 500;
    #     max-width: 280px;
    #     white-space: normal;
    #     text-align: center;
    #     z-index: 99999;
    #     box-shadow: 0 8px 16px rgba(0,0,0,0.4);
    #     line-height: 1.5;
    #     pointer-events: none;
    #     backdrop-filter: blur(4px);  /* Efecto de desenfoque */
    # }

    # .stTabs [data-baseweb="tab"]:nth-child(2):hover::after {
    #     content: "Análisis de utilidad vs cobertura de stock por proveedor";
    #     position: absolute;
    #     top: -.8rem;
    #     left: 50%;
    #     transform: translateX(-50%) translateY(-100%);
    #     background: rgba(45, 55, 72, 0.8);
    #     color: white;
    #     padding: 12px 18px;
    #     border-radius: 8px;
    #     font-size: 0.85rem;
    #     font-weight: 500;
    #     max-width: 280px;
    #     white-space: normal;
    #     text-align: center;
    #     z-index: 99999;
    #     box-shadow: 0 8px 16px rgba(0,0,0,0.4);
    #     line-height: 1.5;
    #     pointer-events: none;
    #     backdrop-filter: blur(4px);
    # }

    # .stTabs [data-baseweb="tab"]:nth-child(3):hover::after {
    #     content: "Comparación de ventas vs presupuesto y análisis de cobertura";
    #     position: absolute;
    #     top: -.8rem;
    #     left: 50%;
    #     transform: translateX(-50%) translateY(-100%);
    #     background: rgba(45, 55, 72, 0.8);
    #     color: white;
    #     padding: 12px 18px;
    #     border-radius: 8px;
    #     font-size: 0.85rem;
    #     font-weight: 500;
    #     max-width: 280px;
    #     white-space: normal;
    #     text-align: center;
    #     z-index: 99999;
    #     box-shadow: 0 8px 16px rgba(0,0,0,0.4);
    #     line-height: 1.5;
    #     pointer-events: none;
    #     backdrop-filter: blur(4px);
    # }

    # .stTabs [data-baseweb="tab"]:nth-child(4):hover::after {
    #     content: "Identificar artículos rentables con análisis de rotación y utilidad";
    #     position: absolute;
    #     top: -.8rem;
    #     left: 50%;
    #     transform: translateX(-50%) translateY(-100%);
    #     background: rgba(45, 55, 72, 0.8);
    #     color: white;
    #     padding: 12px 18px;
    #     border-radius: 8px;
    #     font-size: 0.85rem;
    #     font-weight: 500;
    #     max-width: 280px;
    #     white-space: normal;
    #     text-align: center;
    #     z-index: 99999;
    #     box-shadow: 0 8px 16px rgba(0,0,0,0.4);
    #     line-height: 1.5;
    #     pointer-events: none;
    #     backdrop-filter: blur(4px);
    # }

    # .stTabs [data-baseweb="tab"]:nth-child(5):hover::after {
    #     content: "Sistema de predicción y cálculo de presupuesto de reabastecimiento";
    #     position: absolute;
    #     top: -.8rem;
    #     left: 50%;
    #     transform: translateX(-50%) translateY(-100%);
    #     background: rgba(45, 55, 72, 0.8);
    #     color: white;
    #     padding: 12px 18px;
    #     border-radius: 8px;
    #     font-size: 0.85rem;
    #     font-weight: 500;
    #     max-width: 280px;
    #     white-space: normal;
    #     text-align: center;
    #     z-index: 99999;
    #     box-shadow: 0 8px 16px rgba(0,0,0,0.4);
    #     line-height: 1.5;
    #     pointer-events: none;
    #     backdrop-filter: blur(4px);
    # }
    # </style>
    # """,
    # unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "1- 📊 Proveedores: Rankings, Insights y Reportes", 
        "2- 💰 Utilidad vs Cobertura", 
        "3- 📦 Proveedor Ventas vs Presupuesto | Cobertura",
        "4- 📊 Análisis de Stock Rentable",
        "5- 🎯 Predicción y Presupuesto Proveedor"  # ← NUEVA
    ])

    # =================================================================
    # TAB 1: RANKINGS (COMPLETO Y FILTRADO)
    # =================================================================
    with tab1:
        st.markdown(
        "<h3 style='text-align:center; color:rgb(30, 60, 114);font-weight: bold;'>📊 Rankings de Proveedores</h3>",
        unsafe_allow_html=True)

        with st.expander("ℹ️ ¿Qué hace este análisis y qué contiene la descarga?", expanded=False):
            st.markdown(f"""
            ### 📊 **Este análisis muestra:**
            
            **🎯 Visualizaciones gráficas interactivas:**
            - **Top Proveedores por Ventas** con colores según rentabilidad (verde=alta, rojo=baja)
            - **Top Proveedores por Utilidad** ordenados por ganancia generada
            - **Top Proveedores por Presupuesto** requerido a 30 días
            - Control de cantidad de proveedores a visualizar (5 a 80)
            
            **📋 Tabla detallada de rankings:**
            - Ranking completo de todos los proveedores
            - Métricas: Ventas, Costos, Utilidad, Rentabilidad %, Presupuesto
            - Participación porcentual en ventas y presupuesto total
            - Artículos totales, con exceso de stock y sin stock
            - Costo de exceso de inventario inmovilizado
            
            **💡 Insights clave automáticos:**
            - 🏆 Proveedor líder en ventas
            - 💰 Mayor presupuesto requerido
            - 🏆 Proveedor líder en utilidad
            - ⚠️ Proveedor con menor utilidad
            - ⚠️ Mayor exceso de stock inmovilizado
            
            ### 📥 **Descarga de reportes Excel incluye:**
            
            **📊 Hoja 1 - Ranking Completo (sin filtros):**
            - Todos los proveedores con todas las familias/subfamilias
            - Ranking ordenado por ventas totales
            - Todas las métricas y columnas detalladas
            - Formato profesional con colores y bordes
            
            **🎯 Hoja 2 - Ranking Filtrado:**
            - Solo proveedores de las familias/subfamilias seleccionadas
            - Recalcula rankings y participaciones según filtros activos
            - Permite análisis segmentado por categorías específicas
            
            ### 🔍 **Filtros aplicados:**
            - **Período**: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')} ({dias_periodo} días)
            - **Familias activas**: {len(familias_seleccionadas)}/{len(familias_disponibles)}
            - **Subfamilias activas**: {len(subfamilias_seleccionadas)}/{len(subfamilias_disponibles)}
            
            **⚠️ Importante:**
            - Todos los valores se calculan solo con los filtros activos
            - Para ver el ranking completo, seleccionar todas las familias y subfamilias
            - Los porcentajes de participación se recalculan según los datos filtrados
            
            ### 🎯 **Utilidad del análisis:**
            - Identificar proveedores estratégicos por volumen de ventas
            - Evaluar rentabilidad por proveedor
            - Detectar problemas de stock (excesos y faltantes)
            - Planificar presupuesto de compras mensual
            - Tomar decisiones basadas en participación real de cada proveedor
            - Comparar performance entre períodos y categorías
            """.replace("{fecha_desde.strftime('%d/%m/%Y')}", fecha_desde.strftime('%d/%m/%Y'))
               .replace("{fecha_hasta.strftime('%d/%m/%Y')}", fecha_hasta.strftime('%d/%m/%Y'))
               .replace("{dias_periodo}", str(dias_periodo))
               .replace("{len(familias_seleccionadas)}", str(len(familias_seleccionadas)))
               .replace("{len(familias_disponibles)}", str(len(familias_disponibles)))
               .replace("{len(subfamilias_seleccionadas)}", str(len(subfamilias_seleccionadas)))
               .replace("{len(subfamilias_disponibles)}", str(len(subfamilias_disponibles))))


        # ⭐ ANÁLISIS GRÁFICO DE RANKINGS (Gráficos, Tabla, Insights, Preparación Cobertura)
        df_para_cobertura = main_tab1_ranking_ventas(
            ranking=ranking,
            df_ventas_filtrado=df_ventas_filtrado,
            df_presupuesto_filtrado=df_presupuesto_filtrado,
            df_proveedores_filtrado=df_proveedores_filtrado,
            df_prov_con_familias=df_prov_con_familias,
            familias_seleccionadas=familias_seleccionadas,
            subfamilias_seleccionadas=subfamilias_seleccionadas,
            familias_disponibles=familias_disponibles,
            subfamilias_disponibles=subfamilias_disponibles,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            credentials_path=credentials_path,
            project_id=project_id,
            bigquery_table=bigquery_table
        )
        
        # ✅ EXPORTACIÓN DE REPORTES EXCEL
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
        # ═══════════════════════════════════════════════════════════════════
        # SELECTOR DE AÑO PARA ANÁLISIS
        # ═══════════════════════════════════════════════════════════════════
        
        # Determinar años disponibles (desde 2020 hasta año actual)
        # import datetime
        from datetime import datetime
        año_actual_sistema = datetime.now().year
        años_disponibles = list(range(2024, año_actual_sistema + 1))
        
        # Selector de año
        col_año, col_info = st.columns([1, 3])
        
        with col_año:
            año_seleccionado = st.selectbox(
                "📅 Año a analizar:",
                options=años_disponibles,
                index=len(años_disponibles) - 2,  # Por defecto: año más reciente
                key='selector_año_stock'
            )
        
        with col_info:
            st.info(f"""
            💡 **Año seleccionado: {año_seleccionado}**
            - Q1: Enero - Marzo | Q2: Abril - Junio | Q3: Julio - Septiembre | Q4: Octubre - Diciembre
            """)
        
        # ═══════════════════════════════════════════════════════════════════
        # CARGAR DATOS
        # ═══════════════════════════════════════════════════════════════════
        
        with st.spinner(f"🔄 Cargando datos del año {año_seleccionado}... (~10 segundos)"):
            
            print(f"\n{'='*80}")
            print(f"📦 TAB4: CARGANDO DATOS PARA ANÁLISIS DE STOCK")
            print(f"{'='*80}")
            print(f"   • Año seleccionado: {año_seleccionado}")
            print(f"   • Tabla: {bigquery_table}")


# #######################################################################################3
        # with st.spinner("🔄 Cargando datos para análisis de stock... (~10 segundos)"):
            
        #     print(f"\n{'='*80}")
        #     print(f"📦 TAB4: CARGANDO DATOS PARA ANÁLISIS DE STOCK")
        #     print(f"{'='*80}")
            
        #     # Determinar año actual
        #     año_actual = fecha_maxima_disponible.year
            
        #     print(f"   • Año de análisis: {año_actual}")
        #     print(f"   • Tabla: {bigquery_table}")
            
            # 1. Cargar VENTAS AGREGADAS desde BigQuery (~7 segundos)
            df_ventas_agregadas = get_ventas_agregadas_stock(
                credentials_path=credentials_path,
                project_id=project_id,
                bigquery_table=bigquery_table,
                año=año_seleccionado  
                # año=año_actual
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
            """.replace("{año_actual}", str(año_seleccionado)))


        # ═══════════════════════════════════════════════════════════════════════════
        # ANÁLISIS Y VISUALIZACIÓN
        # ═══════════════════════════════════════════════════════════════════════════
        
        # Llamar al módulo de análisis
        main_analisis_stock_simple(
            df_ventas_agregadas=df_ventas_agregadas,
            df_stock=df_stock,
            df_presupuesto=df_presupuesto,
            año_analisis=año_seleccionado  # ✅ PASAR AÑO SELECCIONADO
        )

    with tab5:
        from utils.config import setup_credentials
        
        config = setup_credentials()
        render_tab_prediccion_presupuesto(df_proveedores, config)