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
from utils.ranking_proveedores import crear_excel_ranking, generar_nombre_archivo, generar_nombre_archivo_alimentos
from components.global_dashboard_cache import process_ranking_data, process_ranking_detallado_alimentos
from components.alimentos_analysis import show_alimentos_analysis


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
    
    col_btn1, col_btn2 = st.columns(2)
    # col_btn1, col_btn2, col_btn3 = st.columns(3)

    # ===============================================================
    # BOTÓN 1: DESCARGAR RANKING COMPLETO (SIN FILTROS)
    # ==============================================================
    with col_btn1:
        st.markdown("#### 📊 Ranking Completo")
        st.caption("Incluye TODOS los proveedores sin aplicar filtros")
        
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
        
        st.download_button(
            label=f"📥 Descargar Ranking Completo ({len(ranking_completo)} proveedores)",
            data=output_completo,
            file_name=nombre_archivo_completo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='content',
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
        
        st.download_button(
            label=f"📥 Descargar Ranking Filtrado ({len(ranking)} proveedores)",
            data=output_filtrado,
            file_name=nombre_archivo_filtrado,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='content',
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

   # ===============================================================
    # BOTÓN 3: DESCARGAR RANKING DETALLADO ALIMENTOS (POR ARTÍCULO)
    # ===============================================================
    st.markdown("---")
        # with col_btn3:
    st.markdown("#### 🥗 Ranking Detallado Alimentos")
        
        # === FILTRO ESPECÍFICO PARA ALIMENTOS ===
        # Obtener subfamilias de Alimentos disponibles
    subfamilias_alimentos = df_familias[
            df_familias['familia'].str.strip().str.lower() == 'alimentos'
        ]['subfamilia'].dropna().unique().tolist()
        
    subfamilias_alimentos_seleccionadas = st.multiselect(
            "🥗 Subfamilias de Alimentos a incluir:",
            options=['Todas'] + sorted(subfamilias_alimentos),
            default=['Todas'],
            key='subfamilias_alimentos_detalle'
        )
        
    st.caption(f"Detalle por artículo - {'Todas las subfamilias' if 'Todas' in subfamilias_alimentos_seleccionadas else f'{len(subfamilias_alimentos_seleccionadas)} subfamilias'}")
        
        # Determinar qué df usar
    if 'Todas' in subfamilias_alimentos_seleccionadas:
            df_para_alimentos = df_proveedores  # Todas las subfamilias
            filtros_aplicados = False
    else:
            # Filtrar solo las subfamilias seleccionadas
            articulos_filtrados = df_familias[
                df_familias['subfamilia'].isin(subfamilias_alimentos_seleccionadas)
            ]['idarticulo'].unique()
            
            df_para_alimentos = df_proveedores[
                df_proveedores['idarticulo'].isin(articulos_filtrados)
            ]
            filtros_aplicados = True
        
    print(f"{'='*80}")
    print("🥗 GENERANDO RANKING DETALLADO ALIMENTOS")
    if 'Todas' in subfamilias_alimentos_seleccionadas:
            print("   📊 TODAS LAS SUBFAMILIAS")
    else:
            print(f"   📊 {len(subfamilias_alimentos_seleccionadas)} SUBFAMILIAS SELECCIONADAS")
    print(f"{'='*80}")
    inicio_detallado = time.time()
        
    ranking_detallado_alimentos = process_ranking_detallado_alimentos(
            df_para_alimentos,
            df_ventas,
            df_presupuesto,
            df_familias
        )
        
    tiempo_detallado = time.time() - inicio_detallado
        
        # === VALIDAR SI HAY DATOS ===
    if ranking_detallado_alimentos.empty:
            st.warning("⚠️ No se encontraron datos de la familia 'Alimentos' en el período seleccionado.")
            print(f"   ⚠️ DataFrame vacío retornado")
            print(f"{'='*80}\n")
    else:
            print(f"   ✅ Ranking detallado generado")
            print(f"   📦 Artículos: {len(ranking_detallado_alimentos):,}")
            print(f"   👥 Proveedores: {ranking_detallado_alimentos['Proveedor'].nunique()}")
            
            # Contar subfamilias únicas
            subfamilias_count = ranking_detallado_alimentos['Subfamilia'].nunique() if 'Subfamilia' in ranking_detallado_alimentos.columns else 0
            print(f"   🥗 Subfamilias: {subfamilias_count}")
            
            print(f"   💰 Venta total: ${ranking_detallado_alimentos['Venta Artículo'].sum():,.0f}")
            print(f"   ⏱️  Tiempo: {tiempo_detallado:.2f}s")
            print(f"{'='*80}\n")
            
            # Crear Excel
            output_detallado = crear_excel_ranking(
                ranking_detallado_alimentos,
                str(fecha_desde),
                str(fecha_hasta),
                filtros_aplicados=filtros_aplicados,
                subfamilias_activas=subfamilias_alimentos_seleccionadas if filtros_aplicados else None
            )
            # periodo= f'{fecha_desde.strftime('%d%b')}_a_{fecha_hasta.strftime('%d%b%Y')}'
            periodo = f"{fecha_desde.strftime('%d%b')}_a_{fecha_hasta.strftime('%d%b%Y')}"

            nombre_archivo_detallado = generar_nombre_archivo_alimentos("ranking_detallado_alimentos", periodo)

            
            st.download_button(
                label=f"📥 Descargar Detalle Alimentos ({len(ranking_detallado_alimentos):,} artículos)",
                data=output_detallado,
                file_name=nombre_archivo_detallado,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
            
            mensaje_subfamilias = f"TODAS las subfamilias ({subfamilias_count})" if 'Todas' in subfamilias_alimentos_seleccionadas else f"{len(subfamilias_alimentos_seleccionadas)} subfamilias seleccionadas"
            
            st.success(f"""
            **Incluye:**
            - 🥗 Solo familia: **Alimentos**
            - 📂 {mensaje_subfamilias}
            - 📊 Detalle por artículo
            - 👥 {ranking_detallado_alimentos['Proveedor'].nunique()} proveedores
            - 📦 {len(ranking_detallado_alimentos):,} artículos
            - 📅 Período: {fecha_desde.strftime('%d/%m/%Y')} - {fecha_hasta.strftime('%d/%m/%Y')}
            - 💰 ${format_millones(ranking_detallado_alimentos['Venta Artículo'].sum())} en ventas
            """)   

    show_alimentos_analysis(
    df_proveedores=df_proveedores,
    df_ventas=df_ventas,
    df_presupuesto=df_presupuesto,
    df_familias=df_familias,
    fecha_desde=fecha_desde,
    fecha_hasta=fecha_hasta
)

