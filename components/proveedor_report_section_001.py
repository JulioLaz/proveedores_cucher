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
from utils.proveedor_exporter import generar_reporte_proveedor, obtener_ids_originales, obtener_ids_originales_simple
from utils.telegram_notifier import send_telegram_alert  # ← AGREGAR
from components.proveedor_panel import mostrar_panel_proveedor

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
        <div style="margin-top:10px; padding:10px; border:1px solid gray; border-radius:5px; background:#F0E69B;">
            <div style="font-size:20px; color:#555; font-weight: bold;">
                ⚠️ Los datos de presupuesto corresponden al análisis a 30 días
            </div>
            <div style='font-size:14px; color: gray'>
                Para que el análisis comparativo sea consistente, se recomienda generar reportes dentro del mismo rango de días.
            </div>
        </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Explicación clara del análisis
    with st.expander("ℹ️ ¿Qué hace este análisis y qué contiene la descarga?", expanded=False):
            st.markdown("""
            ### 📊 **Este análisis permite:**
            
            **🎯 Generar reportes individuales detallados por proveedor**
            - Selecciona un proveedor del ranking para análisis profundo
            - Compara **ventas reales vs presupuesto asignado** por artículo
            - Analiza **cobertura de stock** actual de cada producto
            - Identifica artículos con quiebre o exceso de inventario
            
            ### 📈 **Datos incluidos en el análisis:**
            
            - **Ventas por artículo**: Del período seleccionado en filtros principales
            - **Presupuesto asignado**: Proyección de compra por artículo
            - **Stock actual**: Inventario disponible en tiempo real
            - **Días de cobertura**: Stock actual / velocidad de venta
            - **Familia y subfamilia**: Clasificación de cada producto
            
            ### 📥 **El reporte Excel descargable incluye:**
            
            1. **📋 Listado completo de artículos** del proveedor seleccionado
            2. **💰 Venta real vs presupuesto** con desviaciones
            3. **📦 Stock actual y cobertura** en días por producto
            4. **🚦 Clasificación de stock:**
            - 🔴 **Sin stock**: Requiere compra urgente
            - 🟠 **Stock bajo**: Cobertura < 30 días
            - 🟢 **Stock óptimo**: Cobertura 30-60 días
            - 🟡 **Exceso moderado**: Cobertura > 60 días
            - ⚫ **Exceso crítico**: Inversión inmovilizada
            5. **📊 Análisis de rotación** por producto
            6. **💵 Costo de exceso** de inventario identificado
            
            ### 🎯 **Utilidad del reporte:**
            - **Negociación con proveedores**: Datos concretos de ventas y stock
            - **Optimización de compras**: Priorizar qué y cuánto comprar
            - **Gestión de inventario**: Detectar productos estancados
            - **Control presupuestario**: Comparar ejecutado vs proyectado
            - **Decisiones tácticas**: Foco en artículos rentables del proveedor
            
            ### ⚙️ **Filtros aplicados:**
            - ✅ Respeta los filtros de familia/subfamilia seleccionados arriba
            - ✅ Usa el período de fechas configurado
            - ✅ Incluye solo artículos del proveedor seleccionado
            """)

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
    
    container_03 = st.container(border=True)
    with container_03:

        col_selector, col_btns, col_desde_hasta = st.columns([1, 3,1])
        
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
                
                # st.markdown(f"""
                # **Información del Proveedor:**
                # - 📊 Ranking: #{info_prov['Ranking']}
                # - 💰 Venta Total: ${format_millones(info_prov['Venta Total'])}
                # - 💵 Presupuesto: ${format_millones(info_prov['Presupuesto'])}
                # - 📦 Artículos: {info_prov['Artículos']}
                # """)
        
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
                            width='stretch', type="secondary"):
                    with st.spinner(f"📊 Generando análisis de {proveedor_seleccionado}..."):
                        print(f"\n{'='*80}")
                        print(f"📦 GENERANDO ANÁLISIS SIN FILTROS: {proveedor_seleccionado}")
                        print(f"{'='*80}")
                        
                        # Obtener IDs originales (maneja proveedores unificados)
                        # ids_a_buscar = obtener_ids_originales(id_proveedor)
                        ids_a_buscar = obtener_ids_originales_simple(id_proveedor)

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
                            # ✅ NOTIFICACIÓN TELEGRAM
                            usuario = st.session_state.get('username', 'Usuario desconocido')
                            # mensaje = f"""<b>👤 USUARIO:</b> {usuario} - <b>📊 ANÁLISIS GENERADO - COMPLETO</b>
                            # 🏢 <b>Proveedor:</b> {proveedor_seleccionado} - 📦 <b>Artículos:</b> {len(df_prov):,}
                            # """
                            mensaje = (
                                f"<b>👤 USUARIO:</b> {usuario} - <b>📊 ANÁLISIS GENERADO - COMPLETO</b>\n"
                                f"🏢 <b>Proveedor:</b> {proveedor_seleccionado} - 📦 <b>Artículos:</b> {len(df_prov):,}"
                            )
                            send_telegram_alert(mensaje, tipo="SUCCESS")
                            
                            st.toast("🎉 ¡Análisis generado exitosamente!", icon="✅")
                            # st.balloons()
                            # st.success("✅ Análisis generado exitosamente!")
                        else:
                            st.warning(f"⚠️ No hay artículos con presupuesto > 0 para {proveedor_seleccionado}")
 

                # if proveedor_seleccionado:
                #     id_proveedor = proveedores_dict[proveedor_seleccionado]
                #     info_prov = ranking[ranking['Proveedor'] == proveedor_seleccionado].iloc[0]
                    
                #     # Llamar al módulo del panel
                #     mostrar_panel_proveedor(
                #         proveedor_seleccionado=proveedor_seleccionado,
                #         id_proveedor=id_proveedor,
                #         info_prov=info_prov,
                #         df_presupuesto_con_ventas=df_presupuesto_con_ventas
                #     )

###############################################################################################
################################### PANEL CON FILTROS APLICADOS ###################################
            
                # if proveedor_seleccionado:
                #     id_proveedor = proveedores_dict[proveedor_seleccionado]
                    
                #     # Obtener info del proveedor del ranking
                #     info_prov = ranking[ranking['Proveedor'] == proveedor_seleccionado].iloc[0]
                    
                #     st.markdown(f"""
                #     **Información del Proveedor:**
                #     - 📊 Ranking: #{info_prov['Ranking']}
                #     - 💰 Venta Total: ${format_millones(info_prov['Venta Total'])}
                #     - 💵 Presupuesto: ${format_millones(info_prov['Presupuesto'])}
                #     - 📦 Artículos: {info_prov['Artículos']}
                #     """)
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
                            width='stretch', type="secondary"):
                    with st.spinner(f"📊 Generando análisis de {proveedor_seleccionado}..."):
                        print(f"\n{'='*80}")
                        print(f"📦 GENERANDO ANÁLISIS SIN FILTROS: {proveedor_seleccionado}")
                        print(f"{'='*80}")
                        
                        # Obtener IDs originales (maneja proveedores unificados)
                        ids_a_buscar = obtener_ids_originales_simple(id_proveedor)
                        # ids_a_buscar = obtener_ids_originales(id_proveedor)

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
                            # ✅ NOTIFICACIÓN TELEGRAM
                            usuario = st.session_state.get('username', 'Usuario desconocido')
                            mensaje = (
                                f"<b>👤 USUARIO:</b> {usuario} - <b>📊 ANÁLISIS GENERADO - COMPLETO</b>\n"
                                f"🏢 <b>Proveedor:</b> {proveedor_seleccionado} - 📦 <b>Artículos:</b> {len(df_prov):,}"
                            )

                            send_telegram_alert(mensaje, tipo="SUCCESS")
                            
                            st.toast("🎉 ¡Análisis generado exitosamente!", icon="✅")
                            # st.success("✅ Análisis generado exitosamente!")
                        else:
                            st.warning(f"⚠️ No hay artículos con presupuesto > 0 para {proveedor_seleccionado}")            

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
                            width='stretch', type="primary"):
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
                        # ids_a_buscar = obtener_ids_originales(id_proveedor)
                        ids_a_buscar = obtener_ids_originales_simple(id_proveedor)

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

                            # ✅ NOTIFICACIÓN TELEGRAM
                            usuario = st.session_state.get('username', 'Usuario desconocido')
                            mensaje = (
                                f"<b>👤 USUARIO:</b> {usuario} - <b>🎯 ANÁLISIS GENERADO - FILTRADO</b>\n"
                                f"🏢 <b>Proveedor:</b> {proveedor_seleccionado} - 📦 <b>Artículos:</b> {len(df_prov):,}\n"
                                f"🏷️ <b>Familias:</b> {len(familias_seleccionadas)} - 📂 <b>Subfamilias:</b> {len(subfamilias_seleccionadas)}"
                            )

                            send_telegram_alert(mensaje, tipo="SUCCESS")
                            
                            st.toast("🎉 ¡Análisis filtrado generado!", icon="✅")
                            st.success(f"""
                            ✅ Análisis generado exitosamente!
                            
                            **Filtros aplicados:**
                            - 🏷️ {len(familias_seleccionadas)} familias
                            - 📂 {len(subfamilias_seleccionadas)} subfamilias
                            """)
                        else:
                            st.warning("⚠️ No hay artículos con presupuesto > 0 después de aplicar filtros")

        if proveedor_seleccionado:
                    id_proveedor = proveedores_dict[proveedor_seleccionado]
                    info_prov = ranking[ranking['Proveedor'] == proveedor_seleccionado].iloc[0]
                    
                    # Llamar al módulo del panel
                    mostrar_panel_proveedor(
                        proveedor_seleccionado=proveedor_seleccionado,
                        id_proveedor=id_proveedor,
                        info_prov=info_prov,
                        df_presupuesto_con_ventas=df_presupuesto_con_ventas
                    )
        with col_desde_hasta:
            # Calcular la cantidad de días en el período 
            dias = (fecha_hasta - fecha_desde).days
            st.markdown(
                f"""
                <div style="
                    border: 1px solid #ccc;
                    border-radius: 8px;
                    padding: 8px;
                    background-color: #f9f9f9;
                    font-size: 14px;
                    margin-bottom: 5px;
                ">
                    <b>📅 Período: {dias} días</b> 
                    <div>Desde: {fecha_desde.strftime('%d/%B/%Y')}</div>
                    <div>Hasta: {fecha_hasta.strftime('%d/%B/%Y')}</div>
                </div>
                """,
                unsafe_allow_html=True
            )        

    # ═══════════════════════════════════════════════════════════════════
    # VISUALIZACIÓN DE ANÁLISIS DEL PROVEEDOR
    # ═══════════════════════════════════════════════════════════════════
    
    if 'df_prov_viz' in st.session_state and st.session_state['df_prov_viz'] is not None:
        
        # st.markdown("---")
        
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

        try:
                    # Preparar DataFrame según si hay filtros o no
                    if con_filtros:
                        # Reconstruir df_presupuesto_filtrado aplicando los filtros
                        df_para_excel = df_presupuesto_con_ventas.copy()
                        
                        if 'familia' in df_para_excel.columns:
                            df_para_excel = df_para_excel[
                                df_para_excel['familia'].isin(familias_seleccionadas)
                            ]
                        
                        if 'subfamilia' in df_para_excel.columns:
                            df_para_excel = df_para_excel[
                                df_para_excel['subfamilia'].isin(subfamilias_seleccionadas)
                            ]
                        
                        print(f"   📊 DataFrame con filtros para Excel: {len(df_para_excel):,} artículos")
                    else:
                        df_para_excel = df_presupuesto_con_ventas
                        print(f"   📊 DataFrame sin filtros para Excel: {len(df_para_excel):,} artículos")
                    
                    # Generar Excel
                    print(f"   🔄 Generando Excel para {nombre_prov}...")
                    excel_prov, nombre_archivo_prov = generar_reporte_proveedor(
                        df_para_excel,
                        id_prov,
                        fecha_desde.strftime('%d/%m/%Y'),
                        fecha_hasta.strftime('%d/%m/%Y'),
                        con_filtros=con_filtros,
                        familias_activas=familias_seleccionadas if con_filtros else None,
                        subfamilias_activas=subfamilias_seleccionadas if con_filtros else None,
                        proveedor_name = nombre_prov
                    )
                    
                    if excel_prov and nombre_archivo_prov:
                        print(f"   ✅ Excel generado exitosamente: {nombre_archivo_prov}")
                        
                        # ✅ NOTIFICACIÓN TELEGRAM - Excel preparado para descarga
                        usuario = st.session_state.get('username', 'Usuario desconocido')
                        tipo_filtro = "CON FILTROS" if con_filtros else "SIN FILTROS"
                        mensaje = (
                            f"<b>👤 USUARIO:</b> {usuario} -\n"
                            f"<b>📥 EXCEL PREPARADO PARA DESCARGA</b>\n"
                            f"📄 <b>Archivo:</b> {nombre_archivo_prov}"
                        )

                        send_telegram_alert(mensaje, tipo="INFO")

                        st.download_button(
                            label=f"📥 Descargar Excel: {nombre_archivo_prov}",
                            data=excel_prov,
                            file_name=nombre_archivo_prov,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            type="primary"
                        )
                    else:
                        print(f"   ❌ Error: No se pudo generar el Excel")
                        st.error("❌ No se pudo generar el archivo Excel. Revisa los logs para más detalles.")
                
                except Exception as e:
                    print(f"   ❌ ERROR al generar Excel: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    st.error(f"❌ Error al generar el Excel: {str(e)}")

        # # Generar Excel
        # excel_prov, nombre_archivo_prov = generar_reporte_proveedor(
        #     df_presupuesto_con_ventas if not con_filtros else df_presupuesto_filtrado,
        #     id_prov,
        #     fecha_desde.strftime('%d/%m/%Y'),
        #     fecha_hasta.strftime('%d/%m/%Y'),
        #     con_filtros=con_filtros,
        #     familias_activas=familias_seleccionadas if con_filtros else None,
        #     subfamilias_activas=subfamilias_seleccionadas if con_filtros else None,
        #     proveedor_name = nombre_prov
        # )
        
        # if excel_prov and nombre_archivo_prov:

        # # ✅ NOTIFICACIÓN TELEGRAM - Excel preparado para descarga
        #     usuario = st.session_state.get('username', 'Usuario desconocido')
        #     tipo_filtro = "CON FILTROS" if con_filtros else "SIN FILTROS"
        #     mensaje = (
        #         f"<b>👤 USUARIO:</b> {usuario} -\n"
        #         f"<b>📥 EXCEL PREPARADO PARA DESCARGA</b>\n"
        #         f"📄 <b>Archivo:</b> {nombre_archivo_prov}"
        #     )

        #     send_telegram_alert(mensaje, tipo="INFO")

        #     st.download_button(
        #         label=f"📥 Descargar Excel: {nombre_archivo_prov}",
        #         data=excel_prov,
        #         file_name=nombre_archivo_prov,
        #         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        #         width='content',
        #         type="primary"
        #     )
        
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
            # ✅ AJUSTAR min_value DINÁMICAMENTE
            total_articulos = len(df_viz)
            min_articulos = min(5, total_articulos)  # Si hay menos de 5, usar el total
            max_articulos = min(50, total_articulos)
            valor_inicial = min(20, total_articulos)
            
            # ✅ VALIDACIÓN: Si hay muy pocos artículos, deshabilitar slider
            if total_articulos <= 5:
                st.info(f"ℹ️ Mostrando todos los {total_articulos} artículos disponibles")
                top_articulos = total_articulos
            else:
                top_articulos = st.slider(
                    "📦 Cantidad de artículos a mostrar:",
                    min_value=min_articulos,
                    max_value=max_articulos,
                    value=valor_inicial,
                    step=5,
                    key='slider_articulos_proveedor'
                )

        # # Slider para cantidad de artículos
        # col_slider, col_info1, col_info2 = st.columns([3, 1, 1])
        
        # with col_slider:
        #     top_articulos = st.slider(
        #         "📦 Cantidad de artículos a mostrar:",
        #         min_value=5,
        #         max_value=min(50, len(df_viz)),
        #         value=min(20, len(df_viz)),
        #         step=5,
        #         key='slider_articulos_proveedor'
        #     )
        
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
            # df_plot['Texto'] = df_plot['PRESUPUESTO'].apply(lambda x: f"${x:.0f}")
            df_plot['Texto'] = df_plot['PRESUPUESTO'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
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
            
            st.plotly_chart(fig_presupuesto, width='content')
        
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
            
            st.plotly_chart(fig_cobertura, width='content')
        
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
        df_tabla['Presupuesto'] = df_tabla['Presupuesto'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
        df_tabla['Stock Total'] = df_tabla['Stock Total'].apply(lambda x: f"{x:,.0f}")
        df_tabla['Cobertura (días)'] = df_tabla['Cobertura (días)'].apply(lambda x: f"{x:.0f}")
        # df_tabla['Margen %'] = df_tabla['Margen %'].apply(lambda x: f"{x:.2f}%")
        df_tabla['Margen %'] = df_tabla['Margen %'].apply(lambda x: f"{x*100:.2f}%")  # ← Multiplicar por 100

        
        # Mostrar tabla
        st.dataframe(
            df_tabla,
            # width='content',
            width='stretch',
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