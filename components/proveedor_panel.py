"""
============================================================
MÓDULO: Proveedor Panel
============================================================
Panel visual compacto para análisis de proveedor individual
con métricas por familia/subfamilia y evolución temporal.

Autor: Julio Lazarte  
Fecha: Diciembre 2024
============================================================
"""

import streamlit as st
import pandas as pd
from utils.proveedor_exporter import obtener_ids_originales, obtener_ids_originales_simple


def format_millones(valor):
    """Formatea valores grandes en millones o miles"""
    if valor >= 1_000_000:
        millones = valor / 1_000_000
        return f"{millones:,.1f} mll".replace(',', 'X').replace('.', ',').replace('X', '.')
    elif valor >= 1_000:
        return f"{valor/1_000:,.0f} mil".replace(',', '.')
    else:
        return f"{valor:,.0f}"


def mostrar_panel_proveedor(proveedor_seleccionado, id_proveedor, info_prov, 
                            df_presupuesto_con_ventas):
    """
    Muestra panel visual compacto con métricas del proveedor
    
    Args:
        proveedor_seleccionado (str): Nombre del proveedor
        id_proveedor (int): ID del proveedor
        info_prov (pd.Series): Fila del ranking con datos del proveedor
        df_presupuesto_con_ventas (pd.DataFrame): DataFrame con presupuesto y ventas
    """
    
    # Obtener todos los IDs (principal + secundarios si es unificado)
    # ids_proveedor = obtener_ids_originales(id_proveedor)
    
    # # Formatear IDs para mostrar
    # if len(ids_proveedor) > 1:
    #     ids_str = ", ".join(map(str, sorted(ids_proveedor)))
    #     ids_label = f"IDs proveedores: {ids_str}"
    # else:
    #     ids_label = f"ID proveedor: {id_proveedor}"
    
    # # ═══════════════════════════════════════════════════════════════
    # # HEADER PRINCIPAL
    # # ═══════════════════════════════════════════════════════════════
    # st.markdown(f"""
    # <div style='background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
    #             padding: 12px; 
    #             border-radius: 10px; 
    #             margin-bottom: 12px;
    #             box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
    #     <h3 style='color: white; margin: 0; text-align: center; font-size: 1.3rem;'>
    #         🏢 {proveedor_seleccionado}
    #     </h3>
    #     <p style='color: #e8f4fd; text-align: center; margin: 3px 0 0 0; font-size: 0.85rem;'>
    #         Ranking #{info_prov['Ranking']} | {ids_label}
    #     </p>
    # </div>
    # """, unsafe_allow_html=True)

# Obtener todos los IDs con nombres (formato "ID (Nombre)")
    ids_proveedor_formateados = obtener_ids_originales(id_proveedor)
    
    # Extraer solo los números para contar y validar
    ids_numericos = [int(id_str.split('(')[0].strip()) for id_str in ids_proveedor_formateados]
    
    # Formatear para mostrar
    if len(ids_numericos) > 1:
        # Ordenar por número y unir con salto de línea o coma
        ids_ordenados = sorted(ids_proveedor_formateados, key=lambda x: int(x.split('(')[0].strip()))
        ids_str = " - ".join(ids_ordenados)
        ids_label = f"IDs proveedores unificados: {ids_str}"
    else:
        ids_label = f"ID proveedor: {ids_proveedor_formateados[0]}"
    
    # ═══════════════════════════════════════════════════════════════
    # HEADER PRINCIPAL
    # ═══════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 12px; 
                border-radius: 10px; 
                margin-bottom: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <h3 style='color: white; margin: 0; text-align: center; font-size: 1.3rem;'>
            🏢 {proveedor_seleccionado}
        </h3>
        <p style='color: #e8f4fd; text-align: center; margin: 3px 0 0 0; font-size: 0.85rem;'>
            Ranking #{info_prov['Ranking']} | {ids_label}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════
    # MÉTRICAS PRINCIPALES (4 columnas)
    # ═══════════════════════════════════════════════════════════════
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Venta Total",
            f"${format_millones(info_prov['Venta Total'])}",
            delta=f"{info_prov['% Participación Ventas']:.1f}% del total"
        )
    
    with col2:
        margen = info_prov['Rentabilidad %']
        utilidad = info_prov['Utilidad']
        
        st.metric(
            "📊 Rentabilidad",
            f"{margen:.1f}%",
            delta=f"${format_millones(utilidad)} {'utilidad' if utilidad >= 0 else 'pérdida (utilidad)'}",
            delta_color="normal" if utilidad >= 0 else "inverse"
        )

    with col3:
        st.metric(
            "💵 Presupuesto",
            f"${format_millones(info_prov['Presupuesto'])}",
            delta=f"{info_prov['% Participación Presupuesto']:.1f}% del total"
        )
    
    with col4:
        st.metric(
            "📦 Artículos",
            f"{info_prov['Artículos']}",
            delta=f"{int(info_prov['Cantidad Vendida']):,} unidades".replace(",", ".")
        )
    
    # ═══════════════════════════════════════════════════════════════
    # CALCULAR DATOS DEL PROVEEDOR
    # ═══════════════════════════════════════════════════════════════
    
    # Filtrar artículos del proveedor (ids_proveedor ya calculado arriba)
    ids_proveedor = obtener_ids_originales_simple(id_proveedor)

    articulos_prov = df_presupuesto_con_ventas[
        df_presupuesto_con_ventas['idproveedor'].isin(ids_proveedor)
    ].copy()
    
    # ═══════════════════════════════════════════════════════════════
    # RECALCULAR COSTOS, UTILIDAD Y MARGEN DESDE CERO
    # ═══════════════════════════════════════════════════════════════
    
    # Limpiar costo_unit si viene como string con $
    if articulos_prov['costo_unit'].dtype == 'object':
        articulos_prov['costo_unit_clean'] = articulos_prov['costo_unit'].astype(str).str.replace('$', '').str.replace('.', '').str.replace(',', '.')
        articulos_prov['costo_unit_clean'] = pd.to_numeric(articulos_prov['costo_unit_clean'], errors='coerce').fillna(0)
    else:
        articulos_prov['costo_unit_clean'] = articulos_prov['costo_unit']
    
    # Calcular costo_total = costo_unit * cnt_ultimo_mes
    articulos_prov['costo_total_real'] = articulos_prov['costo_unit_clean'] * articulos_prov['cnt_ultimo_mes']
    
    # Calcular utilidad = venta - costo
    articulos_prov['utilidad_articulo'] = articulos_prov['venta_total_articulo'] - articulos_prov['costo_total_real']
    
    # Calcular margen % = (utilidad / venta) * 100
    articulos_prov['margen_articulo'] = (
        (articulos_prov['utilidad_articulo'] / articulos_prov['venta_total_articulo'] * 100)
        .fillna(0)
        .replace([float('inf'), -float('inf')], 0)
    )
    
    # Verificar artículos sin familia/subfamilia (para alertas)
    arts_sin_familia = articulos_prov[articulos_prov['familia'].isna() | (articulos_prov['familia'] == '')]
    arts_sin_subfamilia = articulos_prov[articulos_prov['subfamilia'].isna() | (articulos_prov['subfamilia'] == '')]
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTRICAS POR FAMILIA (TOP 3) - SOLO VENTA Y CANTIDAD
    # ═══════════════════════════════════════════════════════════════
    
    metricas_familia = articulos_prov.groupby('familia').agg({
        'venta_total_articulo': 'sum',
        'utilidad_articulo': 'sum',
        'idarticulo': 'count'
    }).reset_index()
    
    metricas_familia.columns = ['familia', 'venta', 'utilidad', 'cantidad_arts']
    metricas_familia['margen'] = (metricas_familia['utilidad'] / metricas_familia['venta'] * 100).round(1)
    metricas_familia = metricas_familia.sort_values('venta', ascending=False)
    
    if len(metricas_familia) > 0:
        st.markdown("""
        <div style='font-size: 0.9rem; font-weight: 600; color: #1e3c72; margin: 15px 0 8px 0;'>
            📊 Top Familias por Venta
        </div>
        """, unsafe_allow_html=True)
        
        top_familias = min(3, len(metricas_familia))
        cols_fam = st.columns(top_familias)
        
        for idx, (_, fam) in enumerate(metricas_familia.head(top_familias).iterrows()):
            with cols_fam[idx]:
                # Color de borde según margen
                if fam['margen'] >= 25:
                    border_color = '#27ae60'
                    margen_label = '🟢 Excelente'
                elif fam['margen'] >= 15:
                    border_color = '#f39c12'
                    margen_label = '🟠 Bueno'
                else:
                    border_color = '#e74c3c'
                    margen_label = '🔴 Bajo'
                
                # Obtener artículos de la familia
                arts_familia = articulos_prov[articulos_prov['familia'] == fam['familia']]
                
                margen_val = fam.get('margen', 0) # obtiene margen o 0 si no existe # Si es NaN, reemplazar por 0 o por texto 
                if pd.isna(margen_val): margen_str = "sin margen" 
                else: margen_str = f"{margen_val:.1f}%"

                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                            border-left: 5px solid {border_color};
                            border-radius: 8px;
                            padding: 10px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
                            margin-bottom: 8px;'>
                    <div style='font-size: 0.75rem; color: #666; font-weight: 600; margin-bottom: 4px;'>
                        🏷️ FAMILIA: {fam['familia'][:25]}{'...' if len(str(fam['familia'])) > 25 else ''}
                    </div>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <div>
                            <div style='font-size: 0.7rem; color: #888;'>Venta</div>
                            <div style='font-size: 1rem; font-weight: bold; color: #1e3c72;'>
                                ${fam['venta']/1_000_000:.1f}M
                            </div>
                        </div>
                        <div>
                            <div style='font-size: 0.7rem; color: #888;'>Margen</div>
                            <div style='font-size: 1rem; font-weight: bold; color: {border_color};'>
                                {margen_str}
                            </div>
                        </div>
                        <div>
                            <div style='font-size: 0.7rem; color: #888;'>Arts.</div>
                            <div style='font-size: 1rem; font-weight: bold; color: #555;'>
                                {int(fam['cantidad_arts'])}
                            </div>
                        </div>
                    </div>
                    <div style='margin-top: 6px; padding-top: 6px; border-top: 1px solid #eee; font-size: 0.65rem; color: #999;'>
                        {margen_label} | Utilidad: ${fam['utilidad']/1_000_000:.1f}M
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Expander con TODOS los artículos de la familia
                with st.expander(f"📋 Ver todos los artículos ({int(fam['cantidad_arts'])})", expanded=False):
                    # Obtener todos los artículos ordenados por venta
                    arts_familia_completos = arts_familia.sort_values('venta_total_articulo', ascending=False)
                    
                    # Crear DataFrame para mostrar
                    df_arts_fam = arts_familia_completos[['idarticulo', 'descripcion', 'venta_total_articulo', 'utilidad_articulo', 'margen_articulo']].copy()
                    df_arts_fam.columns = ['Código', 'Descripción', 'Venta', 'Utilidad', 'Margen %']
                    df_arts_fam['Ranking'] = range(1, len(df_arts_fam) + 1)
                    df_arts_fam = df_arts_fam[['Ranking', 'Código', 'Descripción', 'Venta', 'Utilidad', 'Margen %']]
                    
                    # Formatear valores
                    df_arts_fam['Venta'] = df_arts_fam['Venta'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                    df_arts_fam['Utilidad'] = df_arts_fam['Utilidad'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                    df_arts_fam['Margen %'] = df_arts_fam['Margen %'].apply(lambda x: f"{x:.2f}%")
                    
                    # Mostrar tabla con scroll
                    st.dataframe(
                        df_arts_fam,
                        hide_index=True,
                        height=300,
                        width='stretch'
                    )
    
    # ═══════════════════════════════════════════════════════════════
    # MÉTRICAS POR SUBFAMILIA (TOP 3)
    # ═══════════════════════════════════════════════════════════════
    
    metricas_subfamilia = articulos_prov.groupby('subfamilia').agg({
        'venta_total_articulo': 'sum',
        'utilidad_articulo': 'sum',
        'idarticulo': 'count'
    }).reset_index()
    
    metricas_subfamilia.columns = ['subfamilia', 'venta', 'utilidad', 'cantidad_arts']
    metricas_subfamilia['margen'] = (metricas_subfamilia['utilidad'] / metricas_subfamilia['venta'] * 100).round(1)
    metricas_subfamilia = metricas_subfamilia.sort_values('venta', ascending=False)
    
    if len(metricas_subfamilia) > 0:
        st.markdown("""
        <div style='font-size: 0.9rem; font-weight: 600; color: #2a5298; margin: 15px 0 8px 0;'>
            📂 Top Subfamilias por Venta
        </div>
        """, unsafe_allow_html=True)
        
        top_subfamilias = min(3, len(metricas_subfamilia))
        cols_subfam = st.columns(top_subfamilias)
        
        for idx, (_, subfam) in enumerate(metricas_subfamilia.head(top_subfamilias).iterrows()):
            with cols_subfam[idx]:
                # Colores diferentes para subfamilias (tonos azules/púrpuras)
                if subfam['margen'] >= 25:
                    border_color = '#3498db'  # Azul
                    margen_label = '🔵 Excelente'
                elif subfam['margen'] >= 15:
                    border_color = '#9b59b6'  # Púrpura
                    margen_label = '🟣 Bueno'
                else:
                    border_color = '#e67e22'  # Naranja
                    margen_label = '🟠 Bajo'
                
                # Obtener artículos de la subfamilia
                arts_subfam = articulos_prov[articulos_prov['subfamilia'] == subfam['subfamilia']]
                
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                            border-left: 5px solid {border_color};
                            border-radius: 8px;
                            padding: 10px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
                            margin-bottom: 8px;'>
                    <div style='font-size: 0.75rem; color: #666; font-weight: 600; margin-bottom: 4px;'>
                        📂 SUBFAMILIA: {subfam['subfamilia'][:25]}{'...' if len(str(subfam['subfamilia'])) > 25 else ''}
                    </div>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <div>
                            <div style='font-size: 0.7rem; color: #888;'>Venta</div>
                            <div style='font-size: 1rem; font-weight: bold; color: #2a5298;'>
                                ${subfam['venta']/1_000_000:.1f}M
                            </div>
                        </div>
                        <div>
                            <div style='font-size: 0.7rem; color: #888;'>Margen</div>
                            <div style='font-size: 1rem; font-weight: bold; color: {border_color};'>
                                {subfam['margen']:.1f}%
                            </div>
                        </div>
                        <div>
                            <div style='font-size: 0.7rem; color: #888;'>Arts.</div>
                            <div style='font-size: 1rem; font-weight: bold; color: #555;'>
                                {int(subfam['cantidad_arts'])}
                            </div>
                        </div>
                    </div>
                    <div style='margin-top: 6px; padding-top: 6px; border-top: 1px solid #ddd; font-size: 0.65rem; color: #999;'>
                        {margen_label} | Utilidad: ${subfam['utilidad']/1_000_000:.1f}M
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Expander con TODOS los artículos de la subfamilia
                with st.expander(f"📋 Ver todos los artículos ({int(subfam['cantidad_arts'])})", expanded=False):
                    # Obtener todos los artículos ordenados por venta
                    arts_subfam_completos = arts_subfam.sort_values('venta_total_articulo', ascending=False)
                    
                    # Crear DataFrame para mostrar
                    df_arts_subfam = arts_subfam_completos[['idarticulo', 'descripcion', 'venta_total_articulo', 'utilidad_articulo', 'margen_articulo']].copy()
                    df_arts_subfam.columns = ['Código', 'Descripción', 'Venta', 'Utilidad', 'Margen %']
                    df_arts_subfam['Ranking'] = range(1, len(df_arts_subfam) + 1)
                    df_arts_subfam = df_arts_subfam[['Ranking', 'Código', 'Descripción', 'Venta', 'Utilidad', 'Margen %']]
                    
                    # Formatear valores
                    df_arts_subfam['Venta'] = df_arts_subfam['Venta'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                    df_arts_subfam['Utilidad'] = df_arts_subfam['Utilidad'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                    df_arts_subfam['Margen %'] = df_arts_subfam['Margen %'].apply(lambda x: f"{x:.2f}%")
                    
                    # Mostrar tabla con scroll
                    st.dataframe(
                        df_arts_subfam,
                        hide_index=True,
                        height=300,
                        width='stretch'
                    )
    
    # ═══════════════════════════════════════════════════════════════
    # ALERTAS DE INVENTARIO
    # ═══════════════════════════════════════════════════════════════
    
    art_sin_stock = int(info_prov.get('Art. Sin Stock', 0))
    art_con_exceso = int(info_prov.get('Art. con Exceso', 0))
    costo_exceso = info_prov.get('Costo Exceso', 0)
    
    # Contar artículos con margen negativo
    art_margen_negativo = len(articulos_prov[articulos_prov['margen_articulo'] < 0])
    
    # Agregar alertas para artículos sin clasificar si existen
    alertas_activas = []
    if art_sin_stock > 0:
        alertas_activas.append('sin_stock')
    if art_con_exceso > 0:
        alertas_activas.append('con_exceso')
    if art_margen_negativo > 0:
        alertas_activas.append('margen_negativo')
    if len(arts_sin_familia) > 0:
        alertas_activas.append('sin_familia')
    if len(arts_sin_subfamilia) > 0 and len(arts_sin_subfamilia) != len(arts_sin_familia):
        alertas_activas.append('sin_subfamilia')
    
    # Determinar número de columnas según alertas activas
    num_alertas = len(alertas_activas)
    
    if num_alertas > 0:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        
        # Crear columnas dinámicamente
        cols_alertas = st.columns(min(num_alertas, 4))  # Máximo 4 columnas
        col_idx = 0

        # ALERTA 1: Sin Stock
        if 'sin_stock' in alertas_activas:
            with cols_alertas[col_idx]:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #fff5f5 0%, #ffe6e6 100%);
                            border-left: 5px solid #e74c3c;
                            border-radius: 8px;
                            padding: 12px;
                            box-shadow: 0 2px 4px rgba(231, 76, 60, 0.15);
                            cursor: pointer;'
                            title='Artículos sin stock que generaban ventas en el período'>
                    <div style='display: flex; align-items: center; gap: 10px;'>
                        <div style='font-size: 2rem;'>🚨</div>
                        <div style='flex: 1;'>
                            <div style='font-size: 0.75rem; color: #c0392b; font-weight: 600;'>
                                Sin Stock
                            </div>
                            <div style='font-size: 1.3rem; font-weight: bold; color: #e74c3c;'>
                                {art_sin_stock} artículos
                            </div>
                            <div style='font-size: 0.7rem; color: #999;'>
                                ⚠️ Requieren reposición
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Expander con TODOS los artículos sin stock
                with st.expander(f"🔍 Ver artículos sin stock ({art_sin_stock})", expanded=False):
                    # Filtrar artículos sin stock (STK_TOTAL = 0 o NaN)
                    if 'STK_TOTAL' in articulos_prov.columns:
                        arts_sin_stock = articulos_prov[
                            (articulos_prov['STK_TOTAL'].fillna(0) == 0) & 
                            (articulos_prov['venta_total_articulo'] > 0)
                        ].copy()
                        
                        if len(arts_sin_stock) > 0:
                            # Ordenar por venta descendente
                            arts_sin_stock = arts_sin_stock.sort_values('venta_total_articulo', ascending=False)
                            
                            # Crear DataFrame para mostrar
                            df_sin_stock = arts_sin_stock[['idarticulo', 'descripcion', 'familia', 'subfamilia', 'venta_total_articulo', 'utilidad_articulo', 'margen_articulo']].copy()
                            df_sin_stock.columns = ['Código', 'Descripción', 'Familia', 'Subfamilia', 'Venta', 'Utilidad', 'Margen %']
                            df_sin_stock['Ranking'] = range(1, len(df_sin_stock) + 1)
                            df_sin_stock = df_sin_stock[['Ranking', 'Código', 'Descripción', 'Familia', 'Subfamilia', 'Venta', 'Utilidad', 'Margen %']]
                            
                            # Formatear valores
                            df_sin_stock['Venta'] = df_sin_stock['Venta'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                            df_sin_stock['Utilidad'] = df_sin_stock['Utilidad'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                            df_sin_stock['Margen %'] = df_sin_stock['Margen %'].apply(lambda x: f"{x:.2f}%")
                            
                            # Mostrar tabla con scroll
                            st.dataframe(
                                df_sin_stock,
                                hide_index=True,
                                height=300,
                                width='stretch'
                            )
                            
                            # Resumen
                            venta_perdida = arts_sin_stock['venta_total_articulo'].sum()
                            st.info(f"💰 Venta total de productos sin stock: ${venta_perdida:,.0f}")
                        else:
                            st.warning("No se encontraron artículos sin stock en los datos")
                    else:
                        st.warning("No hay información de stock disponible")
            
            col_idx += 1
        
        # ALERTA 2: Con Exceso
        if 'con_exceso' in alertas_activas:
            with cols_alertas[col_idx]:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
                            border-left: 5px solid #f39c12;
                            border-radius: 8px;
                            padding: 12px;
                            box-shadow: 0 2px 4px rgba(243, 156, 18, 0.15);
                            cursor: pointer;'
                            title='Artículos con stock excesivo según velocidad de venta'>
                    <div style='display: flex; align-items: center; gap: 10px;'>
                        <div style='font-size: 2rem;'>⚠️</div>
                        <div style='flex: 1;'>
                            <div style='font-size: 0.75rem; color: #e67e22; font-weight: 600;'>
                                Con Exceso
                            </div>
                            <div style='font-size: 1.3rem; font-weight: bold; color: #f39c12;'>
                                {art_con_exceso} artículos
                            </div>
                            <div style='font-size: 0.7rem; color: #999;'>
                                💰 ${format_millones(costo_exceso)} inmovilizado
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Expander con TODOS los artículos con exceso
                with st.expander(f"🔍 Ver artículos con exceso ({art_con_exceso})", expanded=False):
                    # Filtrar artículos con exceso (exceso_STK > 0)
                    if 'exceso_STK' in articulos_prov.columns and 'costo_exceso_STK' in articulos_prov.columns:
                        arts_con_exceso = articulos_prov[
                            articulos_prov['exceso_STK'].fillna(0) > 0
                        ].copy()
                        
                        if len(arts_con_exceso) > 0:
                            # Ordenar por venta descendente (en lugar de costo de exceso)
                            arts_con_exceso = arts_con_exceso.sort_values('venta_total_articulo', ascending=False)
                            
                            # Crear DataFrame para mostrar
                            df_con_exceso = arts_con_exceso[[
                                'idarticulo', 'descripcion', 'familia', 'subfamilia', 
                                'exceso_STK', 'costo_exceso_STK', 'STK_TOTAL', 'margen_articulo'
                            ]].copy()
                            df_con_exceso.columns = ['Código', 'Descripción', 'Familia', 'Subfamilia', 'Exceso (unid.)', 'Costo Exceso', 'Stock Total', 'Margen %']
                            df_con_exceso['Ranking'] = range(1, len(df_con_exceso) + 1)
                            df_con_exceso = df_con_exceso[['Ranking', 'Código', 'Descripción', 'Familia', 'Subfamilia', 'Stock Total', 'Exceso (unid.)', 'Costo Exceso', 'Margen %']]
                            
                            # Formatear valores
                            df_con_exceso['Stock Total'] = df_con_exceso['Stock Total'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
                            df_con_exceso['Exceso (unid.)'] = df_con_exceso['Exceso (unid.)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
                            df_con_exceso['Costo Exceso'] = df_con_exceso['Costo Exceso'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "$0")
                            df_con_exceso['Margen %'] = df_con_exceso['Margen %'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")
                            
                            # Mostrar tabla con scroll
                            st.dataframe(
                                df_con_exceso,
                                hide_index=True,
                                height=300,
                                width='stretch'
                            )
                            
                            # Resumen
                            costo_total_exceso = arts_con_exceso['costo_exceso_STK'].sum()
                            exceso_total_unidades = arts_con_exceso['exceso_STK'].sum()
                            st.warning(f"⚠️ Total: {int(exceso_total_unidades):,} unidades en exceso | Costo inmovilizado: ${costo_total_exceso:,.0f}")
                        else:
                            st.info("No se encontraron artículos con exceso en los datos")
                    else:
                        st.warning("No hay información de exceso de stock disponible")
            
            col_idx += 1
        
        # ALERTA 3: Sin Familia
        if 'sin_familia' in alertas_activas:
            with cols_alertas[col_idx]:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #f0f0f0 0%, #e0e0e0 100%);
                            border-left: 5px solid #95a5a6;
                            border-radius: 8px;
                            padding: 12px;
                            box-shadow: 0 2px 4px rgba(149, 165, 166, 0.15);
                            cursor: pointer;'
                            title='Artículos sin clasificación de familia'>
                    <div style='display: flex; align-items: center; gap: 10px;'>
                        <div style='font-size: 2rem;'>❓</div>
                        <div style='flex: 1;'>
                            <div style='font-size: 0.75rem; color: #7f8c8d; font-weight: 600;'>
                                Sin Familia
                            </div>
                            <div style='font-size: 1.3rem; font-weight: bold; color: #95a5a6;'>
                                {len(arts_sin_familia)} artículos
                            </div>
                            <div style='font-size: 0.7rem; color: #999;'>
                                📋 Requieren clasificación
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Expander con artículos sin familia
                with st.expander(f"🔍 Ver artículos sin familia ({len(arts_sin_familia)})", expanded=False):
                    if len(arts_sin_familia) > 0:
                        arts_sf = arts_sin_familia.sort_values('venta_total_articulo', ascending=False)
                        
                        df_sin_familia = arts_sf[['idarticulo', 'descripcion', 'venta_total_articulo', 'utilidad_articulo', 'margen_articulo']].copy()
                        df_sin_familia.columns = ['Código', 'Descripción', 'Venta', 'Utilidad', 'Margen %']
                        df_sin_familia['Ranking'] = range(1, len(df_sin_familia) + 1)
                        df_sin_familia = df_sin_familia[['Ranking', 'Código', 'Descripción', 'Venta', 'Utilidad', 'Margen %']]
                        
                        df_sin_familia['Venta'] = df_sin_familia['Venta'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                        df_sin_familia['Utilidad'] = df_sin_familia['Utilidad'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                        df_sin_familia['Margen %'] = df_sin_familia['Margen %'].apply(lambda x: f"{x:.2f}%")
                        
                        st.dataframe(df_sin_familia, hide_index=True, height=300, width='stretch')
                        
                        venta_sin_fam = arts_sf['venta_total_articulo'].sum()
                        util_sin_fam = arts_sf['utilidad_articulo'].sum()
                        margen_sin_fam = (util_sin_fam / venta_sin_fam * 100) if venta_sin_fam > 0 else 0
                        st.warning(f"📊 Venta: ${venta_sin_fam:,.0f} | Utilidad: ${util_sin_fam:,.0f} | Margen: {margen_sin_fam:.1f}%")
            
            col_idx += 1
        
        # ALERTA 4: Sin Subfamilia (solo si es diferente de sin familia)
        if 'sin_subfamilia' in alertas_activas and col_idx < 4:
            with cols_alertas[col_idx]:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #ecf0f1 0%, #d5dbdb 100%);
                            border-left: 5px solid #bdc3c7;
                            border-radius: 8px;
                            padding: 12px;
                            box-shadow: 0 2px 4px rgba(189, 195, 199, 0.15);
                            cursor: pointer;'
                            title='Artículos sin clasificación de subfamilia'>
                    <div style='display: flex; align-items: center; gap: 10px;'>
                        <div style='font-size: 2rem;'>❔</div>
                        <div style='flex: 1;'>
                            <div style='font-size: 0.75rem; color: #95a5a6; font-weight: 600;'>
                                Sin Subfamilia
                            </div>
                            <div style='font-size: 1.3rem; font-weight: bold; color: #bdc3c7;'>
                                {len(arts_sin_subfamilia)} artículos
                            </div>
                            <div style='font-size: 0.7rem; color: #999;'>
                                📋 Clasificación incompleta
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"🔍 Ver artículos sin subfamilia ({len(arts_sin_subfamilia)})", expanded=False):
                    if len(arts_sin_subfamilia) > 0:
                        arts_ssf = arts_sin_subfamilia.sort_values('venta_total_articulo', ascending=False)
                        
                        df_sin_subfam = arts_ssf[['idarticulo', 'descripcion', 'familia', 'venta_total_articulo', 'utilidad_articulo', 'margen_articulo']].copy()
                        df_sin_subfam.columns = ['Código', 'Descripción', 'Familia', 'Venta', 'Utilidad', 'Margen %']
                        df_sin_subfam['Ranking'] = range(1, len(df_sin_subfam) + 1)
                        df_sin_subfam = df_sin_subfam[['Ranking', 'Código', 'Descripción', 'Familia', 'Venta', 'Utilidad', 'Margen %']]
                        
                        df_sin_subfam['Venta'] = df_sin_subfam['Venta'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                        df_sin_subfam['Utilidad'] = df_sin_subfam['Utilidad'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                        df_sin_subfam['Margen %'] = df_sin_subfam['Margen %'].apply(lambda x: f"{x:.2f}%")
                        
                        st.dataframe(df_sin_subfam, hide_index=True, height=300, width='stretch')
                        
                        venta_sin_subfam = arts_ssf['venta_total_articulo'].sum()
                        util_sin_subfam = arts_ssf['utilidad_articulo'].sum()
                        margen_sin_subfam = (util_sin_subfam / venta_sin_subfam * 100) if venta_sin_subfam > 0 else 0
                        st.info(f"📊 Venta: ${venta_sin_subfam:,.0f} | Utilidad: ${util_sin_subfam:,.0f} | Margen: {margen_sin_subfam:.1f}%")
                    
        # ALERTA: Artículos con Margen Negativo
        if 'margen_negativo' in alertas_activas:
            with cols_alertas[col_idx]:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #ffe6e6 0%, #ffcccc 100%);
                            border-left: 5px solid #c0392b;
                            border-radius: 8px;
                            padding: 12px;
                            box-shadow: 0 2px 4px rgba(192, 57, 43, 0.15);
                            cursor: pointer;'
                            title='Artículos con rentabilidad negativa'>
                    <div style='display: flex; align-items: center; gap: 10px;'>
                        <div style='font-size: 2rem;'>📉</div>
                        <div style='flex: 1;'>
                            <div style='font-size: 0.75rem; color: #a93226; font-weight: 600;'>
                                Margen Negativo
                            </div>
                            <div style='font-size: 1.3rem; font-weight: bold; color: #c0392b;'>
                                {art_margen_negativo} artículos
                            </div>
                            <div style='font-size: 0.7rem; color: #999;'>
                                💸 Generan pérdidas
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Expander con TODOS los artículos con margen negativo
                with st.expander(f"🔍 Ver artículos con margen negativo ({art_margen_negativo})", expanded=False):
                    # Filtrar artículos con margen < 0
                    arts_margen_neg = articulos_prov[articulos_prov['margen_articulo'] < 0].copy()
                    
                    if len(arts_margen_neg) > 0:
                        # Ordenar por venta descendente
                        arts_margen_neg = arts_margen_neg.sort_values('venta_total_articulo', ascending=False)
                        
                        # Crear DataFrame para mostrar
                        df_margen_neg = arts_margen_neg[['idarticulo', 'descripcion', 'familia', 'subfamilia', 'venta_total_articulo', 'utilidad_articulo', 'margen_articulo']].copy()
                        df_margen_neg.columns = ['Código', 'Descripción', 'Familia', 'Subfamilia', 'Venta', 'Utilidad', 'Margen %']
                        df_margen_neg['Ranking'] = range(1, len(df_margen_neg) + 1)
                        df_margen_neg = df_margen_neg[['Ranking', 'Código', 'Descripción', 'Familia', 'Subfamilia', 'Venta', 'Utilidad', 'Margen %']]
                        
                        # Formatear valores
                        df_margen_neg['Venta'] = df_margen_neg['Venta'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                        df_margen_neg['Utilidad'] = df_margen_neg['Utilidad'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
                        df_margen_neg['Margen %'] = df_margen_neg['Margen %'].apply(lambda x: f"{x:.2f}%")
                        
                        # Mostrar tabla con scroll
                        st.dataframe(
                            df_margen_neg,
                            hide_index=True,
                            height=300,
                            width='stretch'
                        )
                        
                        # Resumen
                        venta_total_neg = arts_margen_neg['venta_total_articulo'].sum()
                        perdida_total = arts_margen_neg['utilidad_articulo'].sum()
                        margen_prom = arts_margen_neg['margen_articulo'].mean()
                        st.error(f"📉 Venta total: ${venta_total_neg:,.0f} | Pérdida total: ${perdida_total:,.0f} | Margen promedio: {margen_prom:.2f}%")
                    else:
                        st.success("✅ No hay artículos con margen negativo")
            
            col_idx += 1