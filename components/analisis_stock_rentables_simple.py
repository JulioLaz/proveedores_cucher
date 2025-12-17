"""
═══════════════════════════════════════════════════════════════════════════════
    MÓDULO SIMPLIFICADO: ANÁLISIS DE STOCK DE ARTÍCULOS RENTABLES
    Versión optimizada para recibir datos PRE-AGREGADOS desde BigQuery
    Con selectores dinámicos y gráficas mejoradas
═══════════════════════════════════════════════════════════════════════════════
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import io

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

STOCK_QUIEBRE_SEMANAL = 7
STOCK_QUIEBRE_QUINCENAL = 15

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def get_nombre_trimestre(trimestre):
    """Mapea código de trimestre a nombre legible"""
    nombres = {
        'Q1': 'Q1: Enero - Marzo',
        'Q2': 'Q2: Abril - Junio',
        'Q3': 'Q3: Julio - Septiembre',
        'Q4': 'Q4: Octubre - Diciembre',
        'ANUAL': 'ANUAL: Año Completo'
    }
    return nombres.get(trimestre, trimestre)

def calcular_dias_cobertura(stock_total, velocidad_venta_diaria):
    """Calcula días de cobertura de stock"""
    if velocidad_venta_diaria == 0 or pd.isna(velocidad_venta_diaria):
        return 999
    return stock_total / velocidad_venta_diaria

def clasificar_estado_stock(dias_cobertura, stock_total):
    """Clasifica el estado de stock según días de cobertura"""
    if stock_total == 0:
        return 'QUEBRADO'
    elif dias_cobertura <= STOCK_QUIEBRE_SEMANAL:
        return 'QUIEBRE SEMANAL'
    elif dias_cobertura <= STOCK_QUIEBRE_QUINCENAL:
        return 'QUIEBRE QUINCENAL'
    else:
        return 'OK'

def limpiar_valores_negativos(df):
    """Convierte valores negativos de dias_cobertura y STK_TOTAL a 0"""
    if 'dias_cobertura' in df.columns:
        df.loc[df['dias_cobertura'] < 0, 'dias_cobertura'] = 0
    
    if 'STK_TOTAL' in df.columns:
        df.loc[df['STK_TOTAL'] < 0, 'STK_TOTAL'] = 0
    
    return df

# ═══════════════════════════════════════════════════════════════════════════════
# PROCESAMIENTO DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════

def filtrar_por_periodo(df_ventas_agregadas, periodo, tipo_margen, margen_min):
    """
    Filtra y prepara datos según el período seleccionado
    
    Args:
        df_ventas_agregadas: DataFrame con datos agregados por trimestre
        periodo: 'ANUAL', 'Q1', 'Q2', 'Q3', 'Q4'
        tipo_margen: 'Margen Anual' o 'Margen del Período'
        margen_min: Margen mínimo (0.0 a 1.0)
    
    Returns:
        DataFrame con columnas necesarias para análisis
    """
    
    df_periodo = df_ventas_agregadas.copy()
    
    print(f"\n   📊 Procesando período: {periodo}")
    print(f"   📈 Tipo de margen: {tipo_margen}")
    print(f"   💰 Margen mínimo: {margen_min*100:.1f}%")
    
    # ═══ SELECCIONAR DATOS DEL PERÍODO ═══
    if periodo == 'ANUAL':
        df_periodo['cantidad_total'] = df_periodo['cantidad_total_anual']
        df_periodo['precio_total'] = df_periodo['precio_total_anual']
        df_periodo['costo_total'] = df_periodo['costo_total_anual']
        df_periodo['utilidad'] = df_periodo['utilidad_anual']
        
        # Filtrar por días activos SOLO para ANUAL
        articulos_antes = len(df_periodo)
        df_periodo = df_periodo[df_periodo['dias_activo'] >= 270].copy()
        articulos_despues = len(df_periodo)
        print(f"   🔍 Filtro días activos >= 270: {articulos_antes:,} → {articulos_despues:,} (-{articulos_antes - articulos_despues:,})")
    else:
        # Usar datos del trimestre específico
        q_num = periodo[1]  # 'Q1' → '1'
        df_periodo['cantidad_total'] = df_periodo[f'cantidad_q{q_num}']
        df_periodo['precio_total'] = df_periodo[f'venta_q{q_num}']
        df_periodo['costo_total'] = df_periodo[f'costo_q{q_num}']
        df_periodo['utilidad'] = df_periodo['precio_total'] - df_periodo['costo_total']
    
    # ═══ CALCULAR MARGEN DEL PERÍODO ═══
    df_periodo['margen_real'] = np.where(
        df_periodo['precio_total'] > 0,
        (df_periodo['precio_total'] - df_periodo['costo_total']) / df_periodo['precio_total'],
        0
    )
    
    # ═══ APLICAR FILTRO DE MARGEN SEGÚN TIPO ═══
    articulos_antes_margen = len(df_periodo)
    
    if tipo_margen == 'Margen Anual':
        df_periodo = df_periodo[df_periodo['margen_anual'] >= margen_min].copy()
        print(f"   🔍 Filtro margen anual >= {margen_min*100:.1f}%: {articulos_antes_margen:,} → {len(df_periodo):,} (-{articulos_antes_margen - len(df_periodo):,})")
    else:
        df_periodo = df_periodo[df_periodo['margen_real'] >= margen_min].copy()
        print(f"   🔍 Filtro margen período >= {margen_min*100:.1f}%: {articulos_antes_margen:,} → {len(df_periodo):,} (-{articulos_antes_margen - len(df_periodo):,})")
    
    return df_periodo

def consolidar_con_stock(df_periodo, df_stock, df_presupuesto):
    """
    Cruza datos de ventas con stock actual
    """
    
    # Merge con stock
    df_resultado = df_periodo.merge(
        df_stock,
        on='idarticulo',
        how='left',
        suffixes=('_venta', '_actual')
    )
    
    # DEBUG: Ver qué columnas tenemos después del merge
    print(f"\n🔍 DEBUG: Columnas después de merge con stock:")
    print(f"   {df_resultado.columns.tolist()}")
    
    # ═══ CALCULAR STK_TOTAL ═══
    if 'stk_total' in df_resultado.columns:
        print(f"   ✅ Encontrada columna 'stk_total'")
        df_resultado['STK_TOTAL'] = df_resultado['stk_total'].fillna(0)
    elif 'STK_TOTAL' in df_resultado.columns:
        print(f"   ✅ Encontrada columna 'STK_TOTAL'")
        df_resultado['STK_TOTAL'] = df_resultado['STK_TOTAL'].fillna(0)
    else:
        cols_stock = [col for col in df_resultado.columns if col.startswith('stk_') and col != 'stk_total']
        if cols_stock:
            print(f"   ✅ Calculando STK_TOTAL desde: {cols_stock}")
            df_resultado['STK_TOTAL'] = df_resultado[cols_stock].fillna(0).sum(axis=1)
        else:
            print(f"   ⚠️  No se encontraron columnas de stock, usando STK_TOTAL = 0")
            df_resultado['STK_TOTAL'] = 0
    
    df_resultado['STK_TOTAL'] = df_resultado['STK_TOTAL'].astype(int)
    print(f"   📊 Estadísticas STK_TOTAL: min={df_resultado['STK_TOTAL'].min()}, max={df_resultado['STK_TOTAL'].max()}, promedio={df_resultado['STK_TOTAL'].mean():.2f}\n")
    
    # Calcular días de cobertura
    df_resultado['dias_cobertura'] = df_resultado.apply(
        lambda row: calcular_dias_cobertura(
            row.get('STK_TOTAL', 0), 
            row.get('velocidad_venta_diaria', 0)
        ),
        axis=1
    )
    
    print(f"🔍 DEBUG: Días de cobertura calculados")
    print(f"   min={df_resultado['dias_cobertura'].min():.2f}, max={df_resultado['dias_cobertura'].max():.2f}")
    print(f"   Artículos con cobertura > 0: {(df_resultado['dias_cobertura'] > 0).sum()}")
    print(f"   Artículos con stock = 0: {(df_resultado['STK_TOTAL'] == 0).sum()}\n")
    
    # Clasificar estado de stock
    df_resultado['estado_stock'] = df_resultado.apply(
        lambda row: clasificar_estado_stock(
            row.get('dias_cobertura', 0), 
            row.get('STK_TOTAL', 0)
        ),
        axis=1
    )
    
    # Agregar información de proveedor
    if 'proveedor' in df_presupuesto.columns:
        df_presupuesto_info = df_presupuesto[['idarticulo', 'proveedor']].copy()
        df_resultado = df_resultado.merge(
            df_presupuesto_info,
            on='idarticulo',
            how='left'
        )
        df_resultado['proveedor'] = df_resultado['proveedor'].fillna('N/D')
    else:
        df_resultado['proveedor'] = 'N/D'
    
    # Filtrar solo artículos con problemas de stock
    df_resultado = df_resultado[
        df_resultado['estado_stock'].isin(['QUEBRADO', 'QUIEBRE SEMANAL', 'QUIEBRE QUINCENAL'])
    ].copy()
    
    # Limpiar valores negativos
    df_resultado = limpiar_valores_negativos(df_resultado)
    
    return df_resultado

# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZACIONES MEJORADAS
# ═══════════════════════════════════════════════════════════════════════════════

def crear_grafica_utilidad_mejorada(df, top_n=20):
    """
    Gráfica de barras de utilidad con margen en la misma barra
    Formato: $392.66M | 88.0%
    """
    
    df_top = df.nlargest(top_n, 'utilidad').iloc[::-1].copy()
    
    if len(df_top) == 0:
        return None
    
    labels = df_top['descripcion'].tolist()
    utilidades = df_top['utilidad'].tolist()
    margenes = df_top['margen_real'].tolist()
    
    # Formatear utilidad en millones
    utilidades_m = [u / 1_000_000 for u in utilidades]
    
    # Texto combinado: Utilidad | Margen
    texto_barras = [f"${u/1_000_000:.2f}M | {m*100:.1f}%" 
                    for u, m in zip(utilidades, margenes)]
    
    # Crear hover text personalizado
    hover_texts = []
    for i in range(len(df_top)):
        texto = f"<b>{labels[i]}</b><br>"
        texto += f"Utilidad: ${utilidades[i]/1_000_000:.2f}M<br>"
        texto += f"Margen: {margenes[i]*100:.1f}%"
        hover_texts.append(texto)
    
    fig = go.Figure(go.Bar(
        y=labels,
        x=utilidades_m,
        orientation='h',
        text=texto_barras,
        textposition='outside',
        cliponaxis=False,
        marker_color='#3498db',
        hovertemplate='%{customdata}<extra></extra>',
        customdata=hover_texts
    ))
    
    max_val = max(utilidades_m)
    
    fig.update_layout(
        height=max(400, top_n * 25),
        margin=dict(t=20, b=25, l=10, r=120),  # Más margen para texto combinado
        xaxis=dict(
            visible=False,
            range=[0, max_val * 1.35]  # Más espacio para texto
        ),
        yaxis=dict(
            visible=True,
            tickfont=dict(size=10)
        ),
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig

def crear_grafica_margen_mejorada(df, top_n=20):
    """
    Gráfica de barras de margen con utilidad en la misma barra
    Formato: 88.0% | $392.66M
    """
    
    df_top = df.nlargest(top_n, 'margen_real').iloc[::-1].copy()
    
    if len(df_top) == 0:
        return None
    
    labels = df_top['descripcion'].tolist()
    margenes = df_top['margen_real'].tolist()
    utilidades = df_top['utilidad'].tolist()
    
    # Formatear valores
    margenes_pct = [m * 100 for m in margenes]
    
    # Texto combinado: Margen | Utilidad
    texto_barras = [f"{m*100:.1f}% | ${u/1_000_000:.2f}M" 
                    for m, u in zip(margenes, utilidades)]
    
    # Crear hover text personalizado
    hover_texts = []
    for i in range(len(df_top)):
        texto = f"<b>{labels[i]}</b><br>"
        texto += f"Margen: {margenes[i]*100:.1f}%<br>"
        texto += f"Utilidad: ${utilidades[i]/1_000_000:.2f}M"
        hover_texts.append(texto)
    
    fig = go.Figure(go.Bar(
        y=labels,
        x=margenes_pct,
        orientation='h',
        text=texto_barras,
        textposition='outside',
        cliponaxis=False,
        marker_color='#27ae60',
        hovertemplate='%{customdata}<extra></extra>',
        customdata=hover_texts
    ))
    
    max_val = max(margenes_pct)
    
    fig.update_layout(
        height=max(400, top_n * 25),
        margin=dict(t=20, b=25, l=10, r=120),  # Más margen para texto combinado
        xaxis=dict(
            visible=False,
            range=[0, max_val * 1.30]  # Más espacio para texto
        ),
        yaxis=dict(
            visible=True,
            tickfont=dict(size=10)
        ),
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig

def crear_grafica_cobertura_mejorada(df, top_n=20, cap_dias=31):
    """
    Gráfica de días de cobertura con colores según clasificación
    Incluye líneas verticales de referencia
    """
    
    df_top = df.nlargest(top_n, 'utilidad').iloc[::-1].copy()
    
    if len(df_top) == 0:
        return None
    
    labels = df_top['descripcion'].tolist()
    dias_reales = df_top['dias_cobertura'].tolist()
    dias_visual = [min(d, cap_dias) for d in dias_reales]
    estados = df_top['estado_stock'].tolist()
    stocks = df_top['STK_TOTAL'].tolist()
    
    texto_barras = [f"{d:.0f}d" if d <= cap_dias else f"{cap_dias}d+" for d in dias_reales]
    
    # Asignar colores según estado
    def get_color_estado(estado):
        if estado == 'QUEBRADO':
            return '#e74c3c'
        elif estado == 'QUIEBRE SEMANAL':
            return '#f39c12'
        elif estado == 'QUIEBRE QUINCENAL':
            return '#f1c40f'
        else:
            return '#27ae60'
    
    colores = [get_color_estado(e) for e in estados]
    
    # Crear hover text personalizado
    hover_texts = []
    for i in range(len(df_top)):
        texto = f"<b>{labels[i]}</b><br>"
        texto += f"Cobertura: {dias_reales[i]:.0f} días<br>"
        texto += f"Stock: {int(stocks[i]):,}<br>"
        texto += f"Estado: {estados[i]}"
        hover_texts.append(texto)
    
    fig = go.Figure()
    
    # Agregar barras
    fig.add_trace(go.Bar(
        y=labels,
        x=dias_visual,
        orientation='h',
        text=texto_barras,
        textposition='outside',
        cliponaxis=False,
        marker=dict(
            color=colores,
            line=dict(width=0)
        ),
        hovertemplate='%{customdata}<extra></extra>',
        customdata=hover_texts
    ))
    
    # Agregar líneas verticales de referencia
    lineas_config = [
        (7, '#e74c3c', '7d'),
        (14, '#e67e22', '14d'),
        (21, '#f39c12', '21d'),
        (28, '#3498db', '28d')
    ]
    
    for dia, color, etiqueta in lineas_config:
        fig.add_vline(
            x=dia,
            line_dash="dash",
            line_color=color,
            line_width=1.5,
            opacity=0.6,
            annotation_text=etiqueta,
            annotation_position="top",
            annotation_font_size=9,
            annotation_font_color=color
        )
    
    fig.update_layout(
        height=max(400, top_n * 25),
        margin=dict(t=20, b=5, l=30, r=80),
        xaxis=dict(
            visible=True,
            range=[0, cap_dias + 2],
            tickmode='array',
            tickvals=[0, 7, 14, 21, 28, cap_dias],
            ticktext=['0', '7', '14', '21', '28', f'{cap_dias}+'],
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
    
    return fig

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN A EXCEL
# ═══════════════════════════════════════════════════════════════════════════════

def generar_excel_con_formato(df, periodo):
    """Genera archivo Excel con formato condicional"""
    
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        cols_export = [
            'idarticulo', 'descripcion', 'proveedor', 'familia', 'subfamilia',
            'cantidad_total', 'precio_total', 'costo_total', 'utilidad',
            'margen_real', 'STK_TOTAL', 'velocidad_venta_diaria',
            'dias_cobertura', 'estado_stock'
        ]
        
        cols_disponibles = [col for col in cols_export if col in df.columns]
        df_excel = df[cols_disponibles].copy()
        
        for col in ['cantidad_total', 'precio_total', 'costo_total', 'utilidad', 'dias_cobertura', 'STK_TOTAL']:
            if col in df_excel.columns:
                df_excel[col] = df_excel[col].round(0).astype(int)
        
        if 'velocidad_venta_diaria' in df_excel.columns:
            df_excel['velocidad_venta_diaria'] = df_excel['velocidad_venta_diaria'].round(1)
        
        df_excel.to_excel(writer, sheet_name=periodo, index=False)
        worksheet = writer.sheets[periodo]
        
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#4472C4', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 1
        })
        
        formato_quebrado = workbook.add_format({'bg_color': '#F24848'})
        formato_quiebre_semanal = workbook.add_format({'bg_color': '#F7BE89'})
        formato_quiebre_quincenal = workbook.add_format({'bg_color': '#FFFFCC'})
        
        worksheet.set_row(0, 25)
        for col_num, col_name in enumerate(df_excel.columns):
            worksheet.write(0, col_num, col_name, header_format)
            max_len = max(df_excel[col_name].astype(str).apply(len).max(), len(col_name))
            worksheet.set_column(col_num, col_num, max_len + 2)
        
        if 'estado_stock' in df_excel.columns:
            estado_col = df_excel.columns.get_loc('estado_stock')
            
            for row_num, row_data in enumerate(df_excel.itertuples(index=False), start=1):
                estado = row_data[estado_col]
                
                if estado == 'QUEBRADO':
                    formato = formato_quebrado
                elif estado == 'QUIEBRE SEMANAL':
                    formato = formato_quiebre_semanal
                elif estado == 'QUIEBRE QUINCENAL':
                    formato = formato_quiebre_quincenal
                else:
                    continue
                
                for col_num in range(len(df_excel.columns)):
                    valor = row_data[col_num]
                    worksheet.write(row_num, col_num, valor, formato)
        
        worksheet.freeze_panes(1, 0)
    
    output.seek(0)
    return output.getvalue()

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main_analisis_stock_simple(df_ventas_agregadas, df_stock, df_presupuesto):
    """
    Función principal para renderizar el análisis en Streamlit
    """
    
    # st.header("📦 Análisis de Stock - Artículos Rentables")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SELECTORES DE CONFIGURACIÓN
    # ═══════════════════════════════════════════════════════════════════════════
    container = st.container(border=True)

    with container:

        st.subheader("⚙️ Configuración de Análisis")
        
        # FILA 1: Período, Tipo Margen, Margen Mínimo
        col1, col2, col3 = st.columns([2, 1.5, 1])
        
        with col1:
            mes_actual = datetime.now().month
            if mes_actual <= 3:
                trimestre_default = 'Q1'
            elif mes_actual <= 6:
                trimestre_default = 'Q2'
            elif mes_actual <= 9:
                trimestre_default = 'Q3'
            else:
                trimestre_default = 'Q4'
            
            periodos = ['ANUAL', 'Q1', 'Q2', 'Q3', 'Q4']
            indice_default = periodos.index(trimestre_default)
            
            periodo_seleccionado = st.selectbox(
                "📅 Período a analizar:",
                periodos,
                format_func=lambda x: get_nombre_trimestre(x),
                index=indice_default
            )
        
        with col2:
            tipo_margen = st.radio(
                "📊 Base de cálculo de margen:",
                ["Margen Anual", "Margen del Período"],
                help="**Margen Anual**: Artículos rentables todo el año\n**Margen del Período**: Artículos rentables en el trimestre seleccionado"
            )
        
        with col3:
            margen_min = st.number_input(
                "💰 Margen mínimo (%):",
                min_value=10.0,
                max_value=50.0,
                value=25.0,
                step=5.0,
                help="Porcentaje mínimo de margen para considerar rentable"
            )
        
        # FILA 2: Filtros de Proveedor, Familia, Subfamilia con botones de control
        
        # Procesar datos preliminares para obtener opciones de filtros
        with st.spinner("🔄 Cargando opciones de filtros..."):
            df_temp = filtrar_por_periodo(
                df_ventas_agregadas, 
                periodo_seleccionado,
                tipo_margen,
                margen_min / 100
            )
            
            df_temp_stock = consolidar_con_stock(df_temp, df_stock, df_presupuesto)
        
        # Obtener listas únicas
        proveedores_disponibles = sorted(df_temp_stock['proveedor'].unique().tolist())
        familias_disponibles = sorted(df_temp_stock['familia'].unique().tolist()) if 'familia' in df_temp_stock.columns else []
        subfamilias_disponibles = sorted(df_temp_stock['subfamilia'].unique().tolist()) if 'subfamilia' in df_temp_stock.columns else []
        
        # Inicializar session_state si no existe
        if 'proveedores_selected' not in st.session_state:
            st.session_state.proveedores_selected = proveedores_disponibles
        if 'familias_selected' not in st.session_state:
            st.session_state.familias_selected = familias_disponibles
        if 'subfamilias_selected' not in st.session_state:
            st.session_state.subfamilias_selected = subfamilias_disponibles
        
        # Crear columnas para filtros
        col4, col5, col6 = st.columns(3)
        
        # FILTRO PROVEEDORES
        with col4:
 
            proveedores_seleccionados = st.multiselect(
                "Seleccione proveedores:",
                options=proveedores_disponibles,
                default=st.session_state.proveedores_selected,
                key='multiselect_prov',
                label_visibility='collapsed'
            )
            st.session_state.proveedores_selected = proveedores_seleccionados
        
        # FILTRO FAMILIAS
        with col5:

            familias_seleccionadas = st.multiselect(
                "Seleccione familias:",
                options=familias_disponibles,
                default=st.session_state.familias_selected,
                key='multiselect_fam',
                label_visibility='collapsed'
            )
            st.session_state.familias_selected = familias_seleccionadas
        
        # FILTRO SUBFAMILIAS
        with col6:
            
            subfamilias_seleccionadas = st.multiselect(
                "Seleccione subfamilias:",
                options=subfamilias_disponibles,
                default=st.session_state.subfamilias_selected,
                key='multiselect_sub',
                label_visibility='collapsed'
            )
            st.session_state.subfamilias_selected = subfamilias_seleccionadas
    
    # st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROCESAR DATOS CON FILTROS
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Usar datos ya filtrados preliminarmente
    df_resultado = df_temp_stock.copy()
    
    # Aplicar filtros adicionales (solo si hay selecciones)
    if proveedores_seleccionados:  # Si lista NO está vacía
        df_resultado = df_resultado[df_resultado['proveedor'].isin(proveedores_seleccionados)]
        print(f"   🔍 Filtro proveedores: {len(proveedores_seleccionados)} seleccionados → {len(df_resultado):,} artículos")
    else:
        print(f"   ⚠️  Sin proveedores seleccionados → 0 artículos")
        df_resultado = df_resultado[df_resultado['proveedor'].isin([])]  # Ninguno
    
    if familias_seleccionadas:  # Si lista NO está vacía
        df_resultado = df_resultado[df_resultado['familia'].isin(familias_seleccionadas)]
        print(f"   🔍 Filtro familias: {len(familias_seleccionadas)} seleccionadas → {len(df_resultado):,} artículos")
    else:
        print(f"   ⚠️  Sin familias seleccionadas → 0 artículos")
        df_resultado = df_resultado[df_resultado['familia'].isin([])]  # Ninguno
    
    if subfamilias_seleccionadas:  # Si lista NO está vacía
        df_resultado = df_resultado[df_resultado['subfamilia'].isin(subfamilias_seleccionadas)]
        print(f"   🔍 Filtro subfamilias: {len(subfamilias_seleccionadas)} seleccionadas → {len(df_resultado):,} artículos")
    else:
        print(f"   ⚠️  Sin subfamilias seleccionadas → 0 artículos")
        df_resultado = df_resultado[df_resultado['subfamilia'].isin([])]  # Ninguno
    
    print(f"   ✅ Total artículos después de filtros: {len(df_resultado):,}\n")
    
    if len(df_resultado) == 0:
        st.info(f"✅ No hay artículos rentables con problemas de stock en {get_nombre_trimestre(periodo_seleccionado)}")
        return
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTRICAS RESUMEN
    # ═══════════════════════════════════════════════════════════════════════════

    container = st.container(border=True)

    with container:
        st.subheader("📊 Resumen")
        
        # FILA 1: Contadores de artículos
        col1, col2, col3, col4, col_margen = st.columns(5)

        with col1:
            st.metric(
                "Artículos con Problema", 
                f"{len(df_resultado):,}",
                help="Total de artículos rentables con stock insuficiente"
            )
        
        with col2:
            quebrados = len(df_resultado[df_resultado['estado_stock'] == 'QUEBRADO'])
            st.metric(
                "🔴 Quebrados", 
                f"{quebrados:,}",
                help="Artículos sin stock disponible (0 unidades)"
            )
        
        with col3:
            quiebre_semanal = len(df_resultado[df_resultado['estado_stock'] == 'QUIEBRE SEMANAL'])
            st.metric(
                "🟠 Quiebre Semanal", 
                f"{quiebre_semanal:,}",
                help="Artículos con cobertura de 1-7 días"
            )
        
        with col4:
            quiebre_quincenal = len(df_resultado[df_resultado['estado_stock'] == 'QUIEBRE QUINCENAL'])
            st.metric(
                "🟡 Quiebre Quincenal", 
                f"{quiebre_quincenal:,}",
                help="Artículos con cobertura de 8-15 días"
            )
        
        with col_margen:
            st.metric(
                "📈 Margen mínimo", 
                f"{margen_min:.1f}%",
                help="Margen mín promedio de los artículos considerados en el análisis"
            )

        st.markdown("---")
        
        # FILA 2: Estimación de pérdidas
        col_selector, col_spacer, col5, col6 = st.columns([1.5, 0.5, 2, 2])
        
        with col_selector:
            dias_estimacion = st.select_slider(
                "⏱️ Horizonte de estimación:",
                options=[7, 14, 21, 30],
                value=14,
                format_func=lambda x: f"{x} días",
                help="Período para calcular pérdida potencial basado en velocidad de venta histórica"
            )
        
        # Calcular métricas diarias
        df_resultado['precio_unitario'] = df_resultado['precio_total'] / df_resultado['cantidad_total']
        df_resultado['venta_diaria_$'] = df_resultado['velocidad_venta_diaria'] * df_resultado['precio_unitario']
        df_resultado['utilidad_diaria_$'] = df_resultado['venta_diaria_$'] * df_resultado['margen_real']

        # Estimar pérdida
        venta_perdida = (df_resultado['venta_diaria_$'] * dias_estimacion).sum()
        utilidad_perdida = (df_resultado['utilidad_diaria_$'] * dias_estimacion).sum()
        
        # Calcular pérdida diaria promedio para el delta
        venta_diaria_total = df_resultado['venta_diaria_$'].sum()
        utilidad_diaria_total = df_resultado['utilidad_diaria_$'].sum()

        with col5:
            st.metric(
                f"💰 Venta Perdida ({dias_estimacion} días)", 
                f"${venta_perdida:,.0f}",
                delta=f"${venta_diaria_total:,.0f}/día",
                delta_color="off",
                help=f"Estimación de venta no realizada en {dias_estimacion} días si no se repone stock. Calculado como: Velocidad de venta diaria × Precio unitario × {dias_estimacion} días."
            )
        
        with col6:
            st.metric(
                f"💵 Utilidad Perdida ({dias_estimacion} días)", 
                f"${utilidad_perdida:,.0f}",
                delta=f"${utilidad_diaria_total:,.0f}/día",
                delta_color="off",
                help=f"Estimación de ganancia no obtenida en {dias_estimacion} días si no se repone stock. Calculado como: Venta diaria estimada × Margen real × {dias_estimacion} días."
            )
    
#     container = st.container(border=True)

#     with container:

#         st.subheader("📊 Resumen")
        
#         col1, col2, col3, col4 = st.columns(4)

#         with col1:
#             st.metric("Artículos con Problema", f"{len(df_resultado):,}")
        
#         with col2:
#             quebrados = len(df_resultado[df_resultado['estado_stock'] == 'QUEBRADO'])
#             st.metric("🔴 Quebrados", f"{quebrados:,}")
        
#         with col3:
#             quiebre_semanal = len(df_resultado[df_resultado['estado_stock'] == 'QUIEBRE SEMANAL'])
#             st.metric("🟠 Quiebre Semanal", f"{quiebre_semanal:,}")
        
#         with col4:
#             quiebre_quincenal = len(df_resultado[df_resultado['estado_stock'] == 'QUIEBRE QUINCENAL'])
#             st.metric("🟡 Quiebre Quincenal", f"{quiebre_quincenal:,}")
        
#         col_selector, col5, col6 = st.columns([1,2,2])
        
#         with col_selector:
#             dias_estimacion = st.select_slider(
#                 "Estimación de pérdida:",
#                 options=[7, 14, 21, 30],
#                 value=14,
#                 format_func=lambda x: f"{x} días")        # Calcular métricas diarias
            
#             df_resultado['precio_unitario'] = df_resultado['precio_total'] / df_resultado['cantidad_total']
#             df_resultado['venta_diaria_$'] = df_resultado['velocidad_venta_diaria'] * df_resultado['precio_unitario']
#             df_resultado['utilidad_diaria_$'] = df_resultado['venta_diaria_$'] * df_resultado['margen_real']

#             # Estimar pérdida (14 días por default)
#             venta_perdida = (df_resultado['venta_diaria_$'] * dias_estimacion).sum()
#             utilidad_perdida = (df_resultado['utilidad_diaria_$'] * dias_estimacion).sum()

#         with col5:
#             # venta_perdida = df_resultado['precio_total'].sum()
#             st.metric(f"💰 Venta Potencial Perdida en {dias_estimacion} días por falta de stock", f"${venta_perdida:,.0f}",
#             help="Suma de ventas del período de artículos rentables con problemas de stock (quebrados, quiebre semanal/quincenal)"
# )
        
#         with col6:
#             # utilidad_perdida = df_resultado['utilidad'].sum()
#             st.metric(f"💵 Utilidad Potencial Perdida en {dias_estimacion} días por falta de stock", f"${utilidad_perdida:,.0f}",
#             help="Suma de utilidades del período de artículos rentables con problemas de stock (quebrados, quiebre semanal/quincenal)")
    
    # st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GRÁFICAS - ANÁLISIS POR UTILIDAD
    # ═══════════════════════════════════════════════════════════════════════════
    
    st.subheader("📈 Análisis por Utilidad")
    
    # Slider para Top Utilidad
    top_utilidad = st.slider(
        "Cantidad de artículos (Utilidad):", 
        min_value=5, 
        max_value=80, 
        value=20, 
        step=5, 
        key='slider_utilidad'
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"#### 💰 Top {top_utilidad} Artículos por Utilidad")
        fig1 = crear_grafica_utilidad_mejorada(df_resultado, top_n=top_utilidad)
        if fig1:
            st.plotly_chart(fig1, width='content')
    
    with col2:
        st.markdown("#### ⏱️ Días de Cobertura (Cap: 31 días)")
        fig2 = crear_grafica_cobertura_mejorada(df_resultado, top_n=top_utilidad, cap_dias=31)
        if fig2:
            st.plotly_chart(fig2, width='content')
    
    st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GRÁFICAS - ANÁLISIS POR MARGEN
    # ═══════════════════════════════════════════════════════════════════════════
    
    st.subheader("📈 Análisis por Margen Real")
    
    # Slider para Top Margen
    top_margen = st.slider(
        "Cantidad de artículos (Margen):", 
        min_value=5, 
        max_value=80, 
        value=20, 
        step=5, 
        key='slider_margen'
    )
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown(f"#### 💹 Top {top_margen} Artículos por Margen %")
        fig3 = crear_grafica_margen_mejorada(df_resultado, top_n=top_margen)
        if fig3:
            st.plotly_chart(fig3, width='content')
    
    with col4:
        st.markdown("#### ⏱️ Días de Cobertura (Top Margen)")
        df_top_margen = df_resultado.nlargest(top_margen, 'margen_real')
        fig4 = crear_grafica_cobertura_mejorada(df_top_margen, top_n=top_margen, cap_dias=31)
        if fig4:
            st.plotly_chart(fig4, width='content')
    
    st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TABLA Y DESCARGA
    # ═══════════════════════════════════════════════════════════════════════════
    
    st.subheader("📋 Detalle de Artículos")
    
    st.dataframe(
        df_resultado[[
            'idarticulo', 'descripcion', 'proveedor', 'familia', 'subfamilia',
            'cantidad_total', 'precio_total', 'costo_total', 'utilidad',
            'margen_real', 'STK_TOTAL', 'dias_cobertura', 'estado_stock'
        ]],
        hide_index=True,
        column_config={
            "precio_total": st.column_config.NumberColumn("Precio Total", format="$%d"),
            "costo_total": st.column_config.NumberColumn("Costo Total", format="$%d"),
            "utilidad": st.column_config.NumberColumn("Utilidad", format="$%d"),
            "margen_real": st.column_config.NumberColumn("Margen %", format="%.2f%%"),
            "dias_cobertura": st.column_config.NumberColumn("Días Cobertura", format="%d"),
        }
    )
    
    st.subheader("💾 Descargar Reporte")
    
    nombre_archivo = f"Stock_Rentables_{periodo_seleccionado}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    
    excel_bytes = generar_excel_con_formato(df_resultado, periodo_seleccionado)
    
    st.download_button(
        label="📥 Descargar Excel",
        data=excel_bytes,
        file_name=nombre_archivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.markdown("---")
    st.caption("💡 **Clasificación de alertas:**")
    st.caption("🔴 **QUEBRADO**: Stock = 0 unidades")
    st.caption("🟠 **QUIEBRE SEMANAL**: 1-7 días de cobertura")
    st.caption("🟡 **QUIEBRE QUINCENAL**: 8-15 días de cobertura")