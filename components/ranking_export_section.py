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
from utils.ranking_proveedores import crear_excel_ranking, generar_nombre_archivo
from components.global_dashboard_cache import process_ranking_data


def format_millones(valor):
    """Formatea valores grandes en millones o miles"""
    if valor >= 1_000_000:
        millones = valor / 1_000_000
        return f"{millones:,.0f} mll".replace(',', 'X').replace('.', ',').replace('X', '.')
    elif valor >= 1_000:
        return f"{valor/1_000:,.0f} mil".replace(',', '.')
    else:
        return f"{valor:,.0f}"


def show_ranking_section(df_prov_con_familias, df_ventas, df_presupuesto, df_familias,
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
