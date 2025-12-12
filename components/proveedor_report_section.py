# """
# ============================================================
# MÓDULO: Proveedor Report Section
# ============================================================
# Maneja la generación y descarga de reportes individuales
# por proveedor (con y sin filtros).

# Autor: Julio Lazarte
# Fecha: Diciembre 2024
# ============================================================
# """

#                     # nombre_archivo_cobertura = f"utilidad_stock_cobertura_{fecha_inicio_str}_{fecha_fin_str}.xlsx"


# import streamlit as st
# from utils.proveedor_exporter import generar_reporte_proveedor


# def format_millones(valor):
#     """Formatea valores grandes en millones o miles"""
#     if valor >= 1_000_000:
#         millones = valor / 1_000_000
#         return f"{millones:,.0f} mll".replace(',', 'X').replace('.', ',').replace('X', '.')
#     elif valor >= 1_000:
#         return f"{valor/1_000:,.0f} mil".replace(',', '.')
#     else:
#         return f"{valor:,.0f}"


# def show_proveedor_report_section(ranking, df_presupuesto_con_ventas, df_proveedores,
#                                   fecha_desde, fecha_hasta,
#                                   familias_seleccionadas, subfamilias_seleccionadas):
#     """
#     Renderiza la sección de reportes individuales por proveedor.
    
#     Args:
#         ranking (pd.DataFrame): Ranking de proveedores actual
#         df_presupuesto_con_ventas (pd.DataFrame): Presupuesto enriquecido con ventas
#         df_proveedores (pd.DataFrame): Catálogo de proveedores
#         fecha_desde (date): Fecha inicio del período
#         fecha_hasta (date): Fecha fin del período
#         familias_seleccionadas (list): Familias seleccionadas
#         subfamilias_seleccionadas (list): Subfamilias seleccionadas
#     """
    
#     print(f"\n{'='*80}")
#     print("📦 SECCIÓN: REPORTES INDIVIDUALES POR PROVEEDOR")
#     print(f"{'='*80}\n")
    
#     st.markdown(
#         """
#         <div style="font-size:28px; font-weight:bold; color:#1e3c72; margin-bottom:4px; text-align: center;">
#             📦 Reportes Individuales por Proveedor
#         <div style="font-size:22px; color:#555;">
#             Análisis detallado de presupuesto y ventas por proveedor
#         </div>
#         <div style="font-size:20px; color:#555;font-weight: bold; text-align: center;">
#            ⚠️ Los datos de presupuesto corresponden al análisis a 30 días
#         </div>
#         </div>
#         """,
#         unsafe_allow_html=True
#     )
    
#     # Obtener lista de proveedores con sus datos
#     proveedores_list = ranking[['Proveedor']].copy()
#     proveedores_list['id_temp'] = range(len(proveedores_list))
    
#     # Crear diccionario para el selector
#     proveedores_dict = {}
#     for idx, row in proveedores_list.iterrows():
#         nombre_prov = row['Proveedor']
#         # Obtener ID del proveedor desde df_proveedores
#         id_prov = df_proveedores[df_proveedores['proveedor'] == nombre_prov]['idproveedor'].iloc[0] if nombre_prov in df_proveedores['proveedor'].values else None
#         if id_prov:
#             proveedores_dict[nombre_prov] = int(id_prov)
    
#     col_selector, col_btns = st.columns([1, 2])
    
#     with col_selector:
#         proveedor_seleccionado = st.selectbox(
#             "🏢 Seleccionar Proveedor:",
#             options=list(proveedores_dict.keys()),
#             help="Selecciona el proveedor para generar su reporte detallado"
#         )
        
#         if proveedor_seleccionado:
#             id_proveedor = proveedores_dict[proveedor_seleccionado]
            
#             # Obtener info del proveedor del ranking
#             info_prov = ranking[ranking['Proveedor'] == proveedor_seleccionado].iloc[0]
            
#             st.markdown(f"""
#             **Información del Proveedor:**
#             - 📊 Ranking: #{info_prov['Ranking']}
#             - 💰 Venta Total: ${format_millones(info_prov['Venta Total'])}
#             - 💵 Presupuesto: ${format_millones(info_prov['Presupuesto'])}
#             - 📦 Artículos: {info_prov['Artículos']}
#             """)
    
#     with col_btns:
#         col_btn_sin_filtro, col_btn_con_filtro = st.columns(2)
        
#         # BOTÓN 1: SIN FILTROS
#         with col_btn_sin_filtro:
#             st.markdown("#### 📊 Análisis Completo")
#             st.caption("Sin filtros de familia/subfamilia")
            
#             if st.button("📥 Descargar Sin Filtros", key="btn_prov_sin_filtro", 
#                         use_container_width=True, type="secondary"):
#                 with st.spinner(f"📊 Generando reporte completo de {proveedor_seleccionado}..."):
#                     print(f"\n{'='*80}")
#                     print(f"📦 GENERANDO REPORTE SIN FILTROS: {proveedor_seleccionado}")
#                     print(f"{'='*80}")
                    
#                     # Usar el presupuesto completo (sin filtrar por familias)
#                     excel_prov, nombre_archivo_prov = generar_reporte_proveedor(
#                         df_presupuesto_con_ventas,
#                         id_proveedor,
#                         fecha_desde.strftime('%d/%m/%Y'),
#                         fecha_hasta.strftime('%d/%m/%Y'),
#                         con_filtros=False
#                     )
                    
#                     if excel_prov and nombre_archivo_prov:
#                         st.download_button(
#                             label=f"📥 {nombre_archivo_prov}",
#                             data=excel_prov,
#                             file_name=nombre_archivo_prov,
#                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                             key="download_prov_sin_filtro",
#                             use_container_width=True
#                         )
#                         st.success("✅ Reporte generado exitosamente!")
#                     else:
#                         st.error("❌ Error generando reporte")
        
#         # BOTÓN 2: CON FILTROS
#         with col_btn_con_filtro:
#             st.markdown("#### 🎯 Análisis Filtrado")
#             st.caption("Con filtros de familia/subfamilia aplicados")
            
#             if st.button("📥 Descargar Con Filtros", key="btn_prov_con_filtro", 
#                         use_container_width=True, type="primary"):
#                 with st.spinner(f"📊 Generando reporte filtrado de {proveedor_seleccionado}..."):
#                     print(f"\n{'='*80}")
#                     print(f"🎯 GENERANDO REPORTE CON FILTROS: {proveedor_seleccionado}")
#                     print(f"{'='*80}")
                    
#                     # Filtrar presupuesto por familias/subfamilias seleccionadas
#                     df_presupuesto_filtrado = df_presupuesto_con_ventas.copy()
                    
#                     # Aplicar filtros de familia y subfamilia
#                     if 'familia' in df_presupuesto_filtrado.columns:
#                         df_presupuesto_filtrado = df_presupuesto_filtrado[
#                             df_presupuesto_filtrado['familia'].isin(familias_seleccionadas)
#                         ]
                    
#                     if 'subfamilia' in df_presupuesto_filtrado.columns:
#                         df_presupuesto_filtrado = df_presupuesto_filtrado[
#                             df_presupuesto_filtrado['subfamilia'].isin(subfamilias_seleccionadas)
#                         ]
                    
#                     print(f"   📦 Artículos después de filtros: {len(df_presupuesto_filtrado):,}")
                    
#                     excel_prov, nombre_archivo_prov = generar_reporte_proveedor(
#                         df_presupuesto_filtrado,
#                         id_proveedor,
#                         fecha_desde.strftime('%d/%m/%Y'),
#                         fecha_hasta.strftime('%d/%m/%Y'),
#                         con_filtros=True,
#                         familias_activas=familias_seleccionadas,
#                         subfamilias_activas=subfamilias_seleccionadas
#                     )
                    
#                     if excel_prov and nombre_archivo_prov:
#                         st.download_button(
#                             label=f"📥 {nombre_archivo_prov}",
#                             data=excel_prov,
#                             file_name=nombre_archivo_prov,
#                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                             key="download_prov_con_filtro",
#                             use_container_width=True
#                         )
#                         st.success(f"""
#                         ✅ Reporte generado exitosamente!
                        
#                         **Filtros aplicados:**
#                         - 🏷️ {len(familias_seleccionadas)} familias
#                         - 📂 {len(subfamilias_seleccionadas)} subfamilias
#                         """)
#                     else:
#                         st.error("❌ Error generando reporte")

"""
============================================================
MÓDULO: Proveedor Report Section
============================================================
Maneja la generación, visualización y descarga de reportes 
individuales por proveedor (con y sin filtros).

Incluye análisis gráfico similar a la sección de cobertura.

Autor: Julio Lazarte
Fecha: Diciembre 2024
============================================================
"""

import streamlit as st
import plotly.graph_objects as go
from utils.proveedor_exporter import generar_reporte_proveedor, obtener_ids_originales

def format_millones(valor):
    """Formatea valores grandes en millones o miles"""
    if valor >= 1_000_000:
        millones = valor / 1_000_000
        return f"{millones:,.0f} mll".replace(',', 'X').replace('.', ',').replace('X', '.')
    elif valor >= 1_000:
        return f"{valor/1_000:,.0f} mil".replace(',', '.')
    else:
        return f"{valor:,.0f}"


def get_color_nivel_riesgo(nivel):
    """Retorna color según nivel de riesgo"""
    colores = {
        'Alto': '#FF3333',
        'Medio': '#FFCC99',
        'Bajo': '#66FF66',
        'Muy Bajo': '#33CC33',
        'Analizar stk': '#C0C0C0'
    }
    return colores.get(str(nivel), '#999999')


def get_color_cobertura(dias):
    """Retorna color según días de cobertura"""
    if dias < 15:
        return '#e74c3c'  # Rojo - Crítico
    elif dias < 30:
        return '#f39c12'  # Naranja - Bajo
    else:
        return '#27ae60'  # Verde - Óptimo

def show_proveedor_report_section(ranking, df_presupuesto_con_ventas, df_proveedores,
                                  fecha_desde, fecha_hasta,
                                  familias_disponibles, subfamilias_disponibles,
                                  familias_seleccionadas, subfamilias_seleccionadas):
    """
    Renderiza la sección de reportes individuales por proveedor.
    
    Args:
        ranking (pd.DataFrame): Ranking de proveedores actual
        df_presupuesto_con_ventas (pd.DataFrame): Presupuesto enriquecido con ventas
        df_proveedores (pd.DataFrame): Catálogo de proveedores
        fecha_desde (date): Fecha inicio del período
        fecha_hasta (date): Fecha fin del período
        familias_seleccionadas (list): Familias seleccionadas
        subfamilias_seleccionadas (list): Subfamilias seleccionadas
    """
    
    print(f"\n{'='*80}")
    print("📦 SECCIÓN: REPORTES INDIVIDUALES POR PROVEEDOR")
    print(f"{'='*80}\n")
    
    st.markdown(
        """
        <div style="font-size:28px; font-weight:bold; color:#1e3c72; margin-bottom:4px; text-align: center;">
            📦 Reportes Individuales por Proveedor
        <div style="font-size:22px; color:#555;">
            Análisis detallado de presupuesto y ventas por proveedor
        </div>
        <div style="font-size:20px; color:#555;font-weight: bold; text-align: center;">
           ⚠️ Los datos de presupuesto corresponden al análisis a 30 días
        </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Obtener lista de proveedores con sus datos
    proveedores_list = ranking[['Proveedor']].copy()
    proveedores_list['id_temp'] = range(len(proveedores_list))
    
    # Crear diccionario para el selector
    proveedores_dict = {}
    for idx, row in proveedores_list.iterrows():
        nombre_prov = row['Proveedor']
        # Obtener ID del proveedor desde df_proveedores
        id_prov = df_proveedores[df_proveedores['proveedor'] == nombre_prov]['idproveedor'].iloc[0] if nombre_prov in df_proveedores['proveedor'].values else None
        if id_prov:
            proveedores_dict[nombre_prov] = int(id_prov)
    
    col_selector, col_btns = st.columns([1, 2])
    
    with col_selector:
        proveedor_seleccionado = st.selectbox(
            "🏢 Seleccionar Proveedor:",
            options=list(proveedores_dict.keys()),
            help="Selecciona el proveedor para generar su reporte detallado"
        )
        
        if proveedor_seleccionado:
            id_proveedor = proveedores_dict[proveedor_seleccionado]
            
            # Obtener info del proveedor del ranking
            info_prov = ranking[ranking['Proveedor'] == proveedor_seleccionado].iloc[0]
            
            st.markdown(f"""
            **Información del Proveedor:**
            - 📊 Ranking: #{info_prov['Ranking']}
            - 💰 Venta Total: ${format_millones(info_prov['Venta Total'])}
            - 💵 Presupuesto: ${format_millones(info_prov['Presupuesto'])}
            - 📦 Artículos: {info_prov['Artículos']}
            """)
    
    # with col_btns:
    with col_btns:
        # Verificar si hay filtros aplicados
        filtros_aplicados = (
            len(familias_seleccionadas) < len(familias_disponibles) or 
            len(subfamilias_seleccionadas) < len(subfamilias_disponibles)
        )
        if not filtros_aplicados:
            # BOTÓN 1: GENERAR 📊 Análisis Completo
            st.markdown("""
                <div style="display: flex; align-items: center;">
                    <h4 style="margin: 0;">📊 Análisis Completo</h4>
                    <span style="color: gray; margin-left: 10px; font-size: 0.9em;">
                        Sin filtros de familia/subfamilia
                    </span>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🔄 Generar Análisis Completo", key="btn_generar_sin_filtro", 
                        use_container_width=True, type="secondary"):
                with st.spinner(f"📊 Generando análisis de {proveedor_seleccionado}..."):
                    print(f"\n{'='*80}")
                    print(f"📦 GENERANDO ANÁLISIS SIN FILTROS: {proveedor_seleccionado}")
                    print(f"{'='*80}")
                    
                    # Obtener IDs originales (maneja proveedores unificados)
                    ids_a_buscar = obtener_ids_originales(id_proveedor)

                    print(f"   🔍 IDs a buscar: {ids_a_buscar}")
                    if len(ids_a_buscar) > 1:
                        print(f"   ⚠️ Proveedor UNIFICADO - Buscando {len(ids_a_buscar)} IDs")

                    # Filtrar datos del proveedor
                    df_prov = df_presupuesto_con_ventas[
                        df_presupuesto_con_ventas['idproveedor'].isin(ids_a_buscar)
                    ].copy()

                    # Filtrar solo artículos con PRESUPUESTO > 0
                    df_prov = df_prov[df_prov['PRESUPUESTO'] > 0].copy()
                    
                    print(f"   ✅ Artículos con presupuesto > 0: {len(df_prov):,}")
                    
                    if len(df_prov) > 0:
                        # Guardar en session_state
                        st.session_state['df_prov_viz'] = df_prov
                        st.session_state['prov_con_filtros'] = False
                        st.session_state['prov_nombre'] = proveedor_seleccionado
                        st.session_state['prov_id'] = id_proveedor
                        st.success("✅ Análisis generado exitosamente!")
                    else:
                        st.warning("⚠️ No hay artículos con presupuesto > 0 para este proveedor")
        else:

# BOTÓN 1: GENERAR 📊 Análisis Completo
            st.markdown("""
                <div style="display: flex; align-items: center;">
                    <h4 style="margin: 0;">📊 Análisis Completo</h4>
                    <span style="color: gray; margin-left: 10px; font-size: 1rem;">
                        Sin filtros de familia/subfamilia
                    </span>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🔄 Generar Análisis Completo", key="btn_generar_sin_filtro", 
                        use_container_width=True, type="secondary"):
                with st.spinner(f"📊 Generando análisis de {proveedor_seleccionado}..."):
                    print(f"\n{'='*80}")
                    print(f"📦 GENERANDO ANÁLISIS SIN FILTROS: {proveedor_seleccionado}")
                    print(f"{'='*80}")
                    
                    # Obtener IDs originales (maneja proveedores unificados)
                    ids_a_buscar = obtener_ids_originales(id_proveedor)

                    print(f"   🔍 IDs a buscar: {ids_a_buscar}")
                    if len(ids_a_buscar) > 1:
                        print(f"   ⚠️ Proveedor UNIFICADO - Buscando {len(ids_a_buscar)} IDs")

                    # Filtrar datos del proveedor
                    df_prov = df_presupuesto_con_ventas[
                        df_presupuesto_con_ventas['idproveedor'].isin(ids_a_buscar)
                    ].copy()

                    # Filtrar solo artículos con PRESUPUESTO > 0
                    df_prov = df_prov[df_prov['PRESUPUESTO'] > 0].copy()
                    
                    print(f"   ✅ Artículos con presupuesto > 0: {len(df_prov):,}")
                    
                    if len(df_prov) > 0:
                        # Guardar en session_state
                        st.session_state['df_prov_viz'] = df_prov
                        st.session_state['prov_con_filtros'] = False
                        st.session_state['prov_nombre'] = proveedor_seleccionado
                        st.session_state['prov_id'] = id_proveedor
                        st.success("✅ Análisis generado exitosamente!")
                    else:
                        st.warning("⚠️ No hay artículos con presupuesto > 0 para este proveedor")            

            # BOTÓN 2: GENERAR ANÁLISIS CON FILTROS
            st.markdown("""
                <div style="display: flex; align-items: center;">
                    <h4 style="margin: 0;">🎯 Análisis Filtrado</h4>
                    <span style="color: gray; margin-left: 10px; font-size: 1rem;">
                        Con filtros de familia/subfamilia aplicados
                    </span>
                </div>
            """, unsafe_allow_html=True)

            
            if st.button("🔄 Generar Análisis Filtrado", key="btn_generar_con_filtro", 
                        use_container_width=True, type="primary"):
                with st.spinner(f"📊 Generando análisis filtrado de {proveedor_seleccionado}..."):
                    print(f"\n{'='*80}")
                    print(f"🎯 GENERANDO ANÁLISIS CON FILTROS: {proveedor_seleccionado}")
                    print(f"{'='*80}")
                    
                    # Filtrar presupuesto por familias/subfamilias seleccionadas
                    df_presupuesto_filtrado = df_presupuesto_con_ventas.copy()
                    
                    # Aplicar filtros de familia y subfamilia
                    if 'familia' in df_presupuesto_filtrado.columns:
                        df_presupuesto_filtrado = df_presupuesto_filtrado[
                            df_presupuesto_filtrado['familia'].isin(familias_seleccionadas)
                        ]
                    
                    if 'subfamilia' in df_presupuesto_filtrado.columns:
                        df_presupuesto_filtrado = df_presupuesto_filtrado[
                            df_presupuesto_filtrado['subfamilia'].isin(subfamilias_seleccionadas)
                        ]
                    
                    # Obtener IDs originales (maneja proveedores unificados)
                    ids_a_buscar = obtener_ids_originales(id_proveedor)

                    print(f"   🔍 IDs a buscar: {ids_a_buscar}")

                    # Filtrar por proveedor
                    df_prov = df_presupuesto_filtrado[
                        df_presupuesto_filtrado['idproveedor'].isin(ids_a_buscar)
                    ].copy()

                    # Filtrar solo artículos con PRESUPUESTO > 0
                    df_prov = df_prov[df_prov['PRESUPUESTO'] > 0].copy()
                    
                    print(f"   📦 Artículos después de filtros: {len(df_prov):,}")
                    
                    if len(df_prov) > 0:
                        # Guardar en session_state
                        st.session_state['df_prov_viz'] = df_prov
                        st.session_state['prov_con_filtros'] = True
                        st.session_state['prov_nombre'] = proveedor_seleccionado
                        st.session_state['prov_id'] = id_proveedor
                        st.success(f"""
                        ✅ Análisis generado exitosamente!
                        
                        **Filtros aplicados:**
                        - 🏷️ {len(familias_seleccionadas)} familias
                        - 📂 {len(subfamilias_seleccionadas)} subfamilias
                        """)
                    else:
                        st.warning("⚠️ No hay artículos con presupuesto > 0 después de aplicar filtros")

    # ═══════════════════════════════════════════════════════════════════
    # VISUALIZACIÓN DE ANÁLISIS DEL PROVEEDOR
    # ═══════════════════════════════════════════════════════════════════
    
    if 'df_prov_viz' in st.session_state and st.session_state['df_prov_viz'] is not None:
        
        st.markdown("---")
        
        # Cargar datos desde session_state
        df_viz = st.session_state['df_prov_viz'].copy()
        con_filtros = st.session_state.get('prov_con_filtros', False)
        nombre_prov = st.session_state.get('prov_nombre', 'Proveedor')
        id_prov = st.session_state.get('prov_id', 0)
        
        print(f"\n{'='*80}")
        print(f"🔍 VISUALIZANDO ANÁLISIS: {nombre_prov}")
        print(f"{'='*80}")
        print(f"   Registros: {len(df_viz):,}")
        print(f"   Con filtros: {con_filtros}")
        print(f"   Columnas: {df_viz.columns.tolist()}")
        print(f"{'='*80}\n")
        
        # === BOTÓN DE DESCARGA ===
        st.markdown(f"### 📥 Descargar Reporte Excel - {nombre_prov}")
        
        # Generar Excel
        excel_prov, nombre_archivo_prov = generar_reporte_proveedor(
            df_presupuesto_con_ventas if not con_filtros else df_presupuesto_filtrado,
            id_prov,
            fecha_desde.strftime('%d/%m/%Y'),
            fecha_hasta.strftime('%d/%m/%Y'),
            con_filtros=con_filtros,
            familias_activas=familias_seleccionadas if con_filtros else None,
            subfamilias_activas=subfamilias_seleccionadas if con_filtros else None
        )
        
        if excel_prov and nombre_archivo_prov:
            st.download_button(
                label=f"📥 Descargar Excel: {nombre_archivo_prov}",
                data=excel_prov,
                file_name=nombre_archivo_prov,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
        
        # === ANÁLISIS VISUAL ===
        st.markdown(f"### 📊 Análisis Visual - {nombre_prov}")
        
        # Crear columna con formato: "1234 - Descripción"
        df_viz['articulo_label'] = (
            df_viz['idarticulo'].astype(str) + ' - ' + 
            df_viz['descripcion'].str.slice(0, 50)
        )
        
        # Ordenar por PRESUPUESTO
        df_viz = df_viz.sort_values('PRESUPUESTO', ascending=False)
        
        # Slider para cantidad de artículos
        col_slider, col_info1, col_info2 = st.columns([3, 1, 1])
        
        with col_slider:
            top_articulos = st.slider(
                "📦 Cantidad de artículos a mostrar:",
                min_value=5,
                max_value=min(50, len(df_viz)),
                value=min(20, len(df_viz)),
                step=5,
                key='slider_articulos_proveedor'
            )
        
        with col_info1:
            st.metric(
                "Total Artículos",
                f"{len(df_viz):,}".replace(",", ".")
            )
        
        with col_info2:
            presupuesto_total = df_viz['PRESUPUESTO'].sum()
            st.metric(
                "Presupuesto Total",
                f"${presupuesto_total/1_000_000:.1f}M"
            )
        
        # Filtrar top artículos
        df_top = df_viz.head(top_articulos).copy()
        
        # === GRÁFICOS ===
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.markdown("#### 💵 Top Artículos por Presupuesto")
            
            # Preparar datos (invertir para que el mayor esté arriba)
            df_plot = df_top.iloc[::-1].copy()
            
            df_plot['Presupuesto_M'] = df_plot['PRESUPUESTO'] / 1_000_000
            df_plot['Texto'] = df_plot['PRESUPUESTO'].apply(lambda x: f"${x/1_000_000:.2f}M")
            
            # Asignar colores por nivel_riesgo
            df_plot['color_barra'] = df_plot['nivel_riesgo'].apply(get_color_nivel_riesgo)
            
            # Crear hover text
            hover_text_presupuesto = []
            for idx, row in df_plot.iterrows():
                texto = f"<b>{row['articulo_label']}</b><br>"
                texto += f"Presupuesto: ${row['PRESUPUESTO']/1_000_000:.2f}M<br>"
                texto += f"Stock Total: {int(row['STK_TOTAL']):,}<br>"
                texto += f"Nivel Riesgo: {row['nivel_riesgo']}<br>"
                texto += f"Cobertura: {row['dias_cobertura']:.0f} días"
                hover_text_presupuesto.append(texto)
            
            # Crear gráfico de presupuesto
            fig_presupuesto = go.Figure()
            
            fig_presupuesto.add_trace(go.Bar(
                y=df_plot['articulo_label'],
                x=df_plot['Presupuesto_M'],
                orientation='h',
                text=df_plot['Texto'],
                textposition='outside',
                cliponaxis=False,
                marker=dict(
                    color=df_plot['color_barra'],
                    line=dict(width=0)
                ),
                hovertemplate='%{customdata}<extra></extra>',
                customdata=hover_text_presupuesto
            ))
            
            # Calcular rango del eje X
            max_presupuesto = df_plot['Presupuesto_M'].max()
            
            fig_presupuesto.update_layout(
                height=max(400, top_articulos * 25),
                margin=dict(t=20, b=25, l=10, r=80),
                xaxis=dict(
                    visible=False,
                    range=[0, max_presupuesto * 1.2]
                ),
                yaxis=dict(
                    visible=True,
                    tickfont=dict(size=10)
                ),
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            st.plotly_chart(fig_presupuesto, use_container_width=True)
        
        with col_graf2:
            st.markdown("#### ⏱️ Días de Cobertura (Cap: 31 días)")
            
            # Preparar datos de cobertura (CAP en 31 días)
            df_plot['cobertura_visual'] = df_plot['dias_cobertura'].apply(lambda x: min(x, 31))
            df_plot['cobertura_texto'] = df_plot['dias_cobertura'].apply(
                lambda x: f"{x:.0f}d" if x <= 31 else f"31d+"
            )
            
            # Asignar colores según días de cobertura
            df_plot['color_cobertura'] = df_plot['dias_cobertura'].apply(get_color_cobertura)
            
            # Crear hover text para cobertura
            hover_text_cobertura = []
            for idx, row in df_plot.iterrows():
                texto = f"<b>{row['articulo_label']}</b><br>"
                texto += f"Cobertura: {row['dias_cobertura']:.0f} días<br>"
                texto += f"Stock Total: {int(row['STK_TOTAL']):,}<br>"
                texto += f"Nivel Riesgo: {row['nivel_riesgo']}"
                hover_text_cobertura.append(texto)
            
            # Crear gráfico de cobertura
            fig_cobertura = go.Figure()
            
            fig_cobertura.add_trace(go.Bar(
                y=df_plot['articulo_label'],
                x=df_plot['cobertura_visual'],
                orientation='h',
                text=df_plot['cobertura_texto'],
                textposition='outside',
                cliponaxis=False,
                marker=dict(
                    color=df_plot['color_cobertura'],
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
            'familia',
            'subfamilia',
            'PRESUPUESTO',
            'STK_TOTAL',
            'dias_cobertura',
            'nivel_riesgo',
            'margen_porc_all'
        ]].copy()
        
        # Renombrar columnas
        df_tabla.columns = [
            'Código',
            'Descripción',
            'Familia',
            'SubFamilia',
            'Presupuesto',
            'Stock Total',
            'Cobertura (días)',
            'Nivel Riesgo',
            'Margen %'
        ]
        
        # Formatear valores
        df_tabla['Presupuesto'] = df_tabla['Presupuesto'].apply(lambda x: f"${x:,.0f}")
        df_tabla['Stock Total'] = df_tabla['Stock Total'].apply(lambda x: f"{x:,.0f}")
        df_tabla['Cobertura (días)'] = df_tabla['Cobertura (días)'].apply(lambda x: f"{x:.0f}")
        # df_tabla['Margen %'] = df_tabla['Margen %'].apply(lambda x: f"{x:.2f}%")
        df_tabla['Margen %'] = df_tabla['Margen %'].apply(lambda x: f"{x*100:.2f}%")  # ← Multiplicar por 100

        
        # Mostrar tabla
        st.dataframe(
            df_tabla,
            use_container_width=True,
            hide_index=True,
            height=min(400, (top_articulos * 35) + 38)
        )
        
        # === MÉTRICAS RESUMEN ===
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            presupuesto_top = df_top['PRESUPUESTO'].sum()
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 12px; color: #555;">💵 Presupuesto Top</div>
                    <div style="font-size: 16px; font-weight: bold; color: #1e3c72;">
                        ${presupuesto_top/1_000_000:.2f}M
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            stock_total = df_top['STK_TOTAL'].sum()
            stock_str = f"{stock_total:,.0f}".replace(",", ".")
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 12px; color: #555;">📦 Stock Total</div>
                    <div style="font-size: 16px; font-weight: bold; color: #1e3c72;">
                        {stock_str}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            cobertura_prom = df_top['dias_cobertura'].mean()
            color_cob = '#27ae60' if 15 <= cobertura_prom <= 60 else '#e67e22'
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 12px; color: #555;">⏱️ Cobertura Prom.</div>
                    <div style="font-size: 16px; font-weight: bold; color: {color_cob};">
                        {cobertura_prom:.0f} días
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            margen_prom = df_top['margen_porc_all'].mean() * 100  # ← Multiplicar por 100
            st.markdown(f"""
            <div class="metric-box">
                <div style="text-align: center;">
                    <div style="font-size: 12px; color: #555;">📊 Margen Prom.</div>
                    <div style="font-size: 16px; font-weight: bold; color: #1e3c72;">
                        {margen_prom:.2f}%
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)        