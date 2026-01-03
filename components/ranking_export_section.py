"""
============================================================
MÓDULO: Ranking Export Section
============================================================
Maneja la visualización y exportación de rankings de 
proveedores (completo y filtrado).

Autor: Julio Lazarte
Fecha: Diciembre 2024
============================================================
"""

import streamlit as st
import time
import pandas as pd
from utils.ranking_proveedores import crear_excel_ranking, generar_nombre_archivo, generar_nombre_archivo_alimentos
from components.global_dashboard_cache import process_ranking_data, process_ranking_detallado_alimentos
from components.alimentos_analysis import show_alimentos_analysis
from utils.telegram_notifier import send_telegram_alert

def format_millones(valor):
    """Formatea valores grandes en millones o miles"""
    if valor >= 1_000_000:
        millones = valor / 1_000_000
        return f"{millones:,.0f} mll".replace(',', 'X').replace('.', ',').replace('X', '.')
    elif valor >= 1_000:
        return f"{valor/1_000:,.0f} mil".replace(',', '.')
    else:
        return f"{valor:,.0f}"

def show_ranking_section(df_prov_con_familias, df_proveedores, df_ventas, df_presupuesto, df_familias,
                         ranking, fecha_desde, fecha_hasta, 
                         familias_disponibles, subfamilias_disponibles,
                         familias_seleccionadas, subfamilias_seleccionadas):

    """
    Renderiza la sección de exportación de rankings.
    
    Args:
        df_prov_con_familias (pd.DataFrame): Proveedores con familias
        df_ventas (pd.DataFrame): Datos de ventas
        df_presupuesto (pd.DataFrame): Datos de presupuesto
        df_familias (pd.DataFrame): Catálogo de familias
        ranking (pd.DataFrame): Ranking filtrado actual
        fecha_desde (date): Fecha inicio del período
        fecha_hasta (date): Fecha fin del período
        familias_disponibles (list): Lista de todas las familias
        subfamilias_disponibles (list): Lista de todas las subfamilias
        familias_seleccionadas (list): Familias actualmente seleccionadas
        subfamilias_seleccionadas (list): Subfamilias actualmente seleccionadas
    """
    
    print(f"\n{'='*80}")
    print("📊 SECCIÓN: EXPORTACIÓN DE RANKINGS")
    print(f"{'='*80}\n")
    
    container_descarga = st.container(border=True)

    with container_descarga:
        col_btn1, col_btn2 = st.columns(2)
        # ===============================================================
        # BOTÓN 1: DESCARGAR RANKING COMPLETO (SIN FILTROS)
        # ==============================================================
        with col_btn1:
            st.markdown("#### 📊 Ranking Completo")
            st.info("Incluye TODOS los proveedores sin aplicar filtros")
            
            print(f"{'='*80}")
            print("📊 GENERANDO RANKING COMPLETO (SIN FILTROS)")
            print(f"{'='*80}")
            inicio_completo = time.time()
            
            ranking_completo = process_ranking_data(
                df_prov_con_familias,  # SIN filtrar por familia/subfamilia
                df_ventas,             # Ventas del período seleccionado
                df_presupuesto,        # Presupuesto completo
                df_familias
            )
            
            tiempo_completo = time.time() - inicio_completo
            print(f"{'='*80}\n")
            print('&'*150)
            print(f"   ✅ Ranking completo generado")
            print(f"   📦 Proveedores: {len(ranking_completo):,}")
            print(f"   💰 Venta total: ${ranking_completo['Venta Total'].sum():,.0f}")
            print(f"   💵 Presupuesto total: ${ranking_completo['Presupuesto'].sum():,.0f}")
            print(f"   ⏱️  Tiempo: {tiempo_completo:.2f}s")
            print('columnas: ',ranking_completo.columns)
            print('columnas: ',ranking_completo.head())
            print(f"{'='*80}\n")
            print('&'*150)
            
            df_export_completo = ranking_completo[[
                'Ranking', 'ID Proveedor', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total',
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
            
            btn_completo  = st.download_button(
                label=f"📥 Descargar Ranking Completo ({len(ranking_completo)} proveedores)",
                data=output_completo,
                file_name=nombre_archivo_completo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='content',
                type="secondary"
            )

            if btn_completo: # ✅ Se pulsó el botón 
                usuario = st.session_state.get('username', 'Usuario desconocido')
                mensaje = (
                    f"<b>👤 USUARIO:</b> {usuario}\n"
                    f"📊 <b>Ranking Completo generado</b>\n"
                    f"📦 Proveedores: {len(ranking_completo):,}\n"
                    f"💰 Venta total: ${ranking_completo['Venta Total'].sum():,.0f}\n"
                    f"💵 Presupuesto total: ${ranking_completo['Presupuesto'].sum():,.0f}\n"
                    f"📅 Perídod: desde: {fecha_desde} - hasta: {fecha_hasta}"
                )
                send_telegram_alert(mensaje, tipo="SUCCESS")

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
            st.info("Solo incluye los filtros actualmente seleccionados")
            
            print(f"{'='*80}")
            print("🎯 PREPARANDO RANKING FILTRADO PARA DESCARGA")
            print(f"{'='*80}")
            print(f"   📦 Proveedores filtrados: {len(ranking):,}")
            print(f"   💰 Venta filtrada: ${ranking['Venta Total'].sum():,.0f}")
            print(f"   💵 Presupuesto filtrado: ${ranking['Presupuesto'].sum():,.0f}")
            print(f"{'='*80}\n")
            
            df_export_filtrado = ranking[[
                'Ranking', 'ID Proveedor', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total',
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

            btn_filtrado = st.download_button(
                label=f"📥 Descargar Ranking Filtrado ({len(ranking)} proveedores)",
                data=output_filtrado,
                file_name=nombre_archivo_filtrado,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

            if btn_filtrado:  # ✅ Se pulsó el botón
                usuario = st.session_state.get('username', 'Usuario desconocido')

                mensaje = (
                    f"<b>👤 USUARIO:</b> {usuario}\n"
                    f"🎯 <b>Ranking Filtrado generado</b>\n"
                    f"📦 Proveedores: {len(ranking):,}\n"
                    f"💰 Venta filtrada: ${ranking['Venta Total'].sum():,.0f}\n"
                    f"💵 Presupuesto filtrado: ${ranking['Presupuesto'].sum():,.0f}\n"
                    f"📅 Período: desde {fecha_desde} - hasta {fecha_hasta}"
                )

                send_telegram_alert(mensaje, tipo="SUCCESS")

            st.success(f"""
            **Filtros aplicados:**
            - 🏷️ {len(familias_seleccionadas)}/{len(familias_disponibles)} familias
            - 📂 {len(subfamilias_seleccionadas)}/{len(subfamilias_disponibles)} subfamilias
            - 📅 Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}
            - 📊 {len(ranking):,} proveedores
            - 💰 ${format_millones(ranking['Venta Total'].sum())} en ventas
            - 💵 ${format_millones(ranking['Presupuesto'].sum())} en presupuesto
            """)

    # ═══════════════════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 3: RANKING DETALLADO POR FAMILIA (CON SELECTBOX)
    # ═══════════════════════════════════════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════════════════════
    
    st.markdown(
        """<div style=" text-align: center; padding: 1rem; border: 1px solid gray; border-radius: 5px; background: #f0e69b; font-size: 1.8rem; font-weight: 600;margin-bottom:1rem">
        📊 Ranking Detallado por Familia</div>
        """, unsafe_allow_html=True)
    
    # ═══ PASO 1: SELECTOR DE FAMILIA (ÚNICA) ═══
    # st.markdown("#### 🏷️ Paso 1: Seleccionar Familia  -  📂 Paso 2: Seleccionar Subfamilias")
    st.markdown(
        """<div style=" text-align: center; font-size: 1.2rem; font-weight: 500;margin-bottom:10px">
        🏷️ Paso 1: Seleccionar Familia  -  📂 Paso 2: Seleccionar Subfamilias</div>
        """, unsafe_allow_html=True)    
    # Obtener todas las familias disponibles
    familias_lista = sorted(df_familias['familia'].dropna().str.strip().unique().tolist())
    
    # Determinar el índice de "Alimentos" como default
    try:
        alimentos_idx = next(
            i for i, fam in enumerate(familias_lista) 
            if fam.lower() == 'alimentos'
        )
    except StopIteration:
        alimentos_idx = 0  # Si no existe Alimentos, usar primera familia
    
    col_fam,col2, col_sub,col4 = st.columns(4)
    
    with col_fam:
        familia_seleccionada = st.selectbox(
            "Seleccionar familia:",
            options=familias_lista,
            index=alimentos_idx,
            key='familia_detalle_selector',
            help="Selecciona una familia para analizar en detalle"
        )
    
    # with col_info:
        # Contar artículos y proveedores de esta familia
        df_temp_fam = df_prov_con_familias[
            df_prov_con_familias['familia'].str.strip().str.lower() == familia_seleccionada.lower()
        ]
        cant_articulos = df_temp_fam['idarticulo'].nunique()
        cant_proveedores = df_temp_fam['proveedor'].nunique()

    with col2:        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                    padding: .4rem; border-radius: 8px; border-left: 4px solid #2196f3;min-height:80px'>
            <span style='font-size: 1rem; color: #555;'>🏷️ Familia: </span>
            <span style='font-size: 1.1rem; font-weight: bold; color: #1976d2;'>{familia_seleccionada}</span>
            <div style='font-size: 0.85rem; color: #666; margin-top: 0.3rem;'>
                📦 {cant_articulos:,} artículos | 🏢 {cant_proveedores} proveedores
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ═══ PASO 2: MULTISELECT DE SUBFAMILIAS (DINÁMICO) ═══
    
    # Obtener subfamilias de la familia seleccionada
    subfamilias_disponibles_familia = df_familias[
        df_familias['familia'].str.strip().str.lower() == familia_seleccionada.lower()
    ]['subfamilia'].dropna().unique().tolist()
    
    if not subfamilias_disponibles_familia:
        st.warning(f"⚠️ No se encontraron subfamilias para '{familia_seleccionada}'")
        subfamilias_familia_seleccionadas = []
    else:
        # col_sub, col_count = st.columns([3, 2])
        
        with col_sub:
            # st.markdown("#### 📂 Paso 2: Seleccionar Subfamilias")
            subfamilias_familia_seleccionadas = st.multiselect(
                f"Subfamilias de {familia_seleccionada}:",
                options=['Todas'] + sorted(subfamilias_disponibles_familia),
                default=['Todas'],
                key=f'subfamilias_{familia_seleccionada.lower().replace(" ", "_")}_detalle',
                help=f"Selecciona 'Todas' o subfamilias específicas"
            )
        
        # with col_count:
            # Determinar subfamilias a usar
            if 'Todas' in subfamilias_familia_seleccionadas:
                subfamilias_a_usar = subfamilias_disponibles_familia
                texto_filtro = f"✅ Todas ({len(subfamilias_disponibles_familia)})"
                filtros_aplicados_familia = False
            else:
                subfamilias_a_usar = subfamilias_familia_seleccionadas
                texto_filtro = f"🎯 {len(subfamilias_a_usar)} de {len(subfamilias_disponibles_familia)}"
                filtros_aplicados_familia = True

        with col4:            
            st.markdown(f"""
            <div style='background: #e8f5e9; padding: 0.8rem; border-radius: 8px; 
                        border-left: 4px solid #4caf50; margin-top: 0rem;;min-height:80px'>
                <div style='font-size: 0.85rem; color: #555;'>📂 Subfamilias activas:</div>
                <div style='font-size: 1.1rem; font-weight: bold; color: #2e7d32;'>{texto_filtro}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # ═══ PASO 3: GENERAR RANKING DETALLADO ═══
        # st.markdown("---")
        st.markdown("<br>", unsafe_allow_html=True)

        # st.info(f"Detalle por artículo - {texto_filtro}")
        
        # Filtrar artículos por familia y subfamilias
        articulos_filtrados = df_familias[
            (df_familias['familia'].str.strip().str.lower() == familia_seleccionada.lower()) &
            (df_familias['subfamilia'].isin(subfamilias_a_usar))
        ]['idarticulo'].unique()
        
        df_para_familia = df_proveedores[
            df_proveedores['idarticulo'].isin(articulos_filtrados)
        ]
        
        print(f"{'='*80}")
        print(f"📊 GENERANDO RANKING DETALLADO - {familia_seleccionada.upper()}")
        print(f"   📊 Subfamilias: {texto_filtro}")
        print(f"{'='*80}")
        inicio_detallado = time.time()
        
        ranking_detallado_familia = process_ranking_detallado_alimentos(
            df_para_familia,
            df_ventas,
            df_presupuesto,
            df_familias
        )

        ##### mostrar proveedores unicos de ranking_detallado_familia  #####
        import math

        def mostrar_proveedores_en_columnas(df, columna="Proveedor", familia="(familia)", n_cols=4, font_size=12):
            """
            Muestra proveedores únicos en columnas con su ranking y ventas totales formateadas.
            
            Args:
                df: DataFrame con columnas 'Ranking', 'Proveedor' y 'Venta Total Proveedor'
                columna: Nombre de la columna del proveedor (por defecto "Proveedor")
                familia: Nombre de la familia para el título
                n_cols: Número de columnas a mostrar
                font_size: Tamaño de fuente
            """
            # Función para formatear valores a millones
            def formatear_millones(valor):
                if pd.isna(valor) or valor == 0:
                    return "$0,00 M"
                millones = valor / 1_000_000
                return f"${millones:,.2f} M".replace(",", ".")
            
            # Obtener proveedores únicos con su ranking y ventas (sin duplicados)
            proveedores_unicos = df[[columna, 'Ranking', 'Venta Total Proveedor']].drop_duplicates(subset=[columna])
            
            # Crear lista de tuplas (ranking, proveedor, ventas)
            proveedores_data = [
                (row['Ranking'], row[columna], formatear_millones(row['Venta Total Proveedor']))
                for _, row in proveedores_unicos.iterrows()
            ]
            
            n = len(proveedores_data)
            chunk_size = math.ceil(n / n_cols)

            # Expander con título dinámico
            with st.expander(f"🛠️ VER: {n} Proveedores únicos de {familia.upper()}: Ranking - Proveedor - Venta (📅 Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')})", expanded=False):
                cols = st.columns(n_cols)
                for i, col in enumerate(cols):
                    start = i * chunk_size
                    end = start + chunk_size
                    subset = proveedores_data[start:end]
                    with col:
                        texto = "".join([
                            f'<div><span style="font-weight:bold">{ranking}.</span> {proveedor} - <span style="color:red">{ventas}</span></div>'
                            for ranking, proveedor, ventas in subset
                        ])
                        st.markdown(
                            f"<div style='font-size:{font_size}px; line-height:1.2;'>{texto}</div>",
                            unsafe_allow_html=True
                        )

        # Llamada (reemplazar la anterior)
        mostrar_proveedores_en_columnas(ranking_detallado_familia, columna="Proveedor", familia="Alimentos", n_cols=5)

        # def mostrar_proveedores_en_columnas(df, columna="Proveedor", familia="(familia)", n_cols=4, font_size=12):
        #     proveedores = df[columna].unique().tolist()
        #     n = len(proveedores)
        #     chunk_size = math.ceil(n / n_cols)

        #     # Expander con título dinámico
        #     with st.expander(f"🛠️ VER: {n} Proveedores únicos de {familia.upper()}", expanded=False):
        #         cols = st.columns(n_cols)
        #         for i, col in enumerate(cols):
        #             start = i * chunk_size
        #             end = start + chunk_size
        #             subset = proveedores[start:end]
        #             with col:
        #                 texto = "".join([f"<div>• {p}</div>" for p in subset])
        #                 st.markdown(
        #                     f"<div style='font-size:{font_size}px; line-height:1.2;'>{texto}</div>",
        #                     unsafe_allow_html=True
        #                 )

        # mostrar_proveedores_en_columnas(ranking_detallado_familia, columna="Proveedor", n_cols=6)

        # st.markdown(f"<br>", unsafe_allow_html=True)
        tiempo_detallado = time.time() - inicio_detallado
        
        print("@"*100)
        print("@"*100)
        print('ranking_detallado_familia: ', ranking_detallado_familia.columns)
        print("@"*100)
        print("@"*100)

        # === VALIDAR SI HAY DATOS ===
        if ranking_detallado_familia.empty:
            st.warning(f"⚠️ No se encontraron datos de la familia '{familia_seleccionada}' en el período seleccionado.")
            print(f"   ⚠️ DataFrame vacío retornado")
            print(f"{'='*80}\n")
        else:
            print(f"   ✅ Ranking detallado generado")
            print(f"   📦 Artículos: {len(ranking_detallado_familia):,}")
            print(f"   👥 Proveedores: {ranking_detallado_familia['Proveedor'].nunique()}")
            
            # Contar subfamilias únicas
            subfamilias_count = ranking_detallado_familia['Subfamilia'].nunique() if 'Subfamilia' in ranking_detallado_familia.columns else 0
            print(f"   📂 Subfamilias: {subfamilias_count}")
            
            print(f"   💰 Venta total: ${ranking_detallado_familia['Venta Artículo'].sum():,.0f}")
            print(f"   ⏱️  Tiempo: {tiempo_detallado:.2f}s")
            print(f"{'='*80}\n")
            
            # Crear Excel
            output_detallado = crear_excel_ranking(
                ranking_detallado_familia,
                str(fecha_desde),
                str(fecha_hasta),
                filtros_aplicados=filtros_aplicados_familia,
                subfamilias_activas=subfamilias_familia_seleccionadas if filtros_aplicados_familia else None
            )
            
            periodo = f"{fecha_desde.strftime('%d%b')}_a_{fecha_hasta.strftime('%d%b%Y')}"
            nombre_archivo_detallado = generar_nombre_archivo_alimentos(
                f"ranking_detallado_{familia_seleccionada.lower().replace(' ', '_')}", 
                periodo
            )
            
            # Determinar emoji según familia
            emoji_familia = {
                'alimentos': '🥗',
                'bebidas': '🥤',
                'limpieza': '🧹',
                'perfumería': '💄',
                'bazar': '🏺',
                'textil': '👕'
            }.get(familia_seleccionada.lower(), '📦')
            
            mensaje_subfamilias = f"TODAS las subfamilias ({subfamilias_count})" if 'Todas' in subfamilias_familia_seleccionadas else f"{len(subfamilias_familia_seleccionadas)} subfamilias seleccionadas"
            
            btn_ranking_familia = st.download_button(
                label=f"📥 Descargar detalle Familia: {familia_seleccionada.upper()} con {len(ranking_detallado_familia):,} artículos  - 📂 Usando: {mensaje_subfamilias} - Proveedores: {ranking_detallado_familia.Proveedor.nunique()}",
                data=output_detallado,
                file_name=nombre_archivo_detallado,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch',
                type="primary"
            )
            
            # Mensaje de éxito
            mensaje_success = f"""
            **Incluye:**
            - {emoji_familia} Solo familia: **{familia_seleccionada}**
            - 📂 {mensaje_subfamilias}
            - 📊 Detalle por artículo
            - 👥 {ranking_detallado_familia['Proveedor'].nunique()} proveedores
            - 📦 {len(ranking_detallado_familia):,} artículos
            - 📅 Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}
            - 💰 ${format_millones(ranking_detallado_familia['Venta Artículo'].sum())} en ventas
            """

            # Crear layout en dos columnas con proporción 1:3
            col1, col2 = st.columns([1, 3])

            with col1:
                st.success(mensaje_success)

            with col2:
                # Definir formatos para cada tipo de columna
                formato_porcentaje = lambda x: f"{x:.2f}%"
                formato_moneda = lambda x: f"${x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                formato_numero = lambda x: f"{x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
                # Aplicar formatos a todas las columnas correspondientes
                st.dataframe(
                    ranking_detallado_familia.style.format({
                        # Porcentajes con 2 decimales
                        "% Participación Ventas": formato_porcentaje,
                        "Rentabilidad % Proveedor": formato_porcentaje,
                        "% Participación Presupuesto": formato_porcentaje,
                        "Rentabilidad % Artículo": formato_porcentaje,
                        
                        # Monedas sin decimales
                        "Venta Total Proveedor": formato_moneda,
                        "Costo Total Proveedor": formato_moneda,
                        "Utilidad Proveedor": formato_moneda,
                        "Presupuesto Proveedor": formato_moneda,
                        "Costo Exceso Proveedor": formato_moneda,
                        "Venta Artículo": formato_moneda,
                        "Costo Artículo": formato_moneda,
                        "Utilidad Artículo": formato_moneda,
                        "Presupuesto Artículo": formato_moneda,
                        "Costo Exceso Artículo": formato_moneda,
                        
                        # Números enteros
                        "Cantidad Vendida": formato_numero,
                        "Stock Actual": formato_numero,
                    }),
                    width='stretch',
                    height=244
                )
            # with col2:
            #     # st.markdown("### 📊 Tabla detallada")
            #     st.dataframe(
            #         ranking_detallado_familia.style.format({
            #             "Venta Artículo": lambda x: f"${x:,.0f}".replace(",", ".").replace(".", ",")
            #         }),
            #         width='stretch',
            #         height=244
            #     )
            
            if btn_ranking_familia:  # ✅ Se pulsó el botón
                usuario = st.session_state.get('username', 'Usuario desconocido')
                
                mensaje = (
                    f"<b>👤 USUARIO:</b> {usuario}\n"
                    f"{emoji_familia} <b>Descarga de Ranking {familia_seleccionada}</b>\n\n" 
                    f"{mensaje_success}"
                )
                
                send_telegram_alert(mensaje, tipo="SUCCESS")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANÁLISIS ESPECÍFICO DE ALIMENTOS (Si la familia es Alimentos)
    # ═══════════════════════════════════════════════════════════════════════════

    # Mostrar análisis detallado para CUALQUIER familia
    show_alimentos_analysis(
        df_proveedores=df_proveedores,
        df_ventas=df_ventas,
        df_presupuesto=df_presupuesto,
        df_familias=df_familias,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        subfamilias_preseleccionadas=subfamilias_a_usar,
        familia_seleccionada=familia_seleccionada
    )