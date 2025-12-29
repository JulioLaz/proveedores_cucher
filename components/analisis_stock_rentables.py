"""
═══════════════════════════════════════════════════════════════════════════════
    MÓDULO: ANÁLISIS DE STOCK DE ARTÍCULOS RENTABLES
    Para integración con Streamlit - Dashboard de Proveedores
    VERSION BIGQUERY - Recibe DataFrames directamente desde BigQuery
═══════════════════════════════════════════════════════════════════════════════
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import io
from typing import Tuple, Dict, List

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

MARGEN_MIN_BUENO = 0.25
DIAS_MINIMOS_ANUAL = 270
STOCK_QUIEBRE_SEMANAL = 7
STOCK_QUIEBRE_QUINCENAL = 15

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def get_trimestre(fecha):
    """Obtiene el trimestre de una fecha"""
    mes = fecha.month
    if mes <= 3:
        return 'Q1'
    elif mes <= 6:
        return 'Q2'
    elif mes <= 9:
        return 'Q3'
    else:
        return 'Q4'

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

def get_trimestre_actual():
    """Obtiene el trimestre actual"""
    return get_trimestre(datetime.now())

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

def calcular_stk_total(row, columnas_stock):
    """Calcula stock total sumando todas las sucursales, convirtiendo -1 a 0"""
    total = 0
    for col in columnas_stock:
        valor = row[col]
        if valor == -1 or pd.isna(valor):
            continue
        else:
            total += valor
    return total

def limpiar_valores_negativos(df):
    """Convierte valores negativos de dias_cobertura y STK_TOTAL a 0"""
    if 'dias_cobertura' in df.columns:
        df.loc[df['dias_cobertura'] < 0, 'dias_cobertura'] = 0
    
    if 'STK_TOTAL' in df.columns:
        df.loc[df['STK_TOTAL'] < 0, 'STK_TOTAL'] = 0
    
    # También limpiar columnas individuales de stock
    cols_stock = [col for col in df.columns if col.startswith('stk_')]
    for col in cols_stock:
        df.loc[df[col] < 0, col] = 0
    
    return df

# ═══════════════════════════════════════════════════════════════════════════════
# PREPARACIÓN DE DATOS DESDE BIGQUERY
# ═══════════════════════════════════════════════════════════════════════════════

def preparar_datos_desde_bigquery(df_tickets: pd.DataFrame, df_presupuesto: pd.DataFrame, 
                                   df_stock: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Prepara los datos que vienen desde BigQuery
    
    Args:
        df_tickets: DataFrame de tickets desde BigQuery (tickets_all)
        df_presupuesto: DataFrame de presupuesto desde BigQuery (result_final_alert_all)
        df_stock: DataFrame de stock consolidado desde BigQuery (stock_consolidado_pivoteado)
    
    Returns:
        Tuple con (df_tickets, df_presupuesto, df_stock) preparados
    """
    # Preparar tickets
    print('############################################'*100)
    print("Preparando datos de tickets desde BigQuery...")
    print("RENTABILIDAD - TICKETS - columnas:", df_tickets.columns.tolist())

    df_tickets = df_tickets.copy()
    if 'fecha_comprobante' in df_tickets.columns:
        df_tickets['fecha_comprobante'] = pd.to_datetime(df_tickets['fecha_comprobante'])
    df_tickets['trimestre'] = df_tickets['fecha_comprobante'].apply(get_trimestre)
    df_tickets['año'] = df_tickets['fecha_comprobante'].dt.year
    
    # Preparar presupuesto (ya viene listo desde BigQuery)
    df_presupuesto = df_presupuesto.copy()
    
    # Preparar stock (ya viene pivoteado desde BigQuery)
    df_stock = df_stock.copy()
    
    return df_tickets, df_presupuesto, df_stock

def procesar_stock_consolidado(df_stock: pd.DataFrame) -> pd.DataFrame:
    """Procesa el stock consolidado calculando totales y estados"""
    
    # Identificar columnas de stock
    columnas_stock = [col for col in df_stock.columns if col.startswith('stk_')]
    
    # Calcular STK_TOTAL
    df_stock['STK_TOTAL'] = df_stock.apply(
        lambda row: calcular_stk_total(row, columnas_stock), axis=1
    )
    
    return df_stock

def calcular_ventas_anuales(df_tickets: pd.DataFrame) -> pd.DataFrame:
    """Calcula métricas de ventas anuales"""
    
    ventas_anuales = df_tickets.groupby('idarticulo').agg({
        'cantidad_total': 'sum',
        'precio_total': 'sum',
        'costo_total': 'sum',
        'descripcion': 'first',
        'familia': 'first',
        'subfamilia': 'first',
        'idartalfa': 'first',
        'fecha_comprobante': ['min', 'max', 'count']
    }).reset_index()
    
    ventas_anuales.columns = ['idarticulo', 'cantidad_total', 'precio_total', 
                              'costo_total', 'descripcion', 'familia', 'subfamilia',
                              'idartalfa', 'fecha_primera_venta', 'fecha_ultima_venta', 
                              'dias_con_ventas']
    
    ventas_anuales['margen_real'] = (
        (ventas_anuales['precio_total'] - ventas_anuales['costo_total']) / 
        ventas_anuales['precio_total']
    )
    
    ventas_anuales['dias_activo'] = (
        ventas_anuales['fecha_ultima_venta'] - ventas_anuales['fecha_primera_venta']
    ).dt.days + 1
    
    ventas_anuales['velocidad_venta_diaria'] = (
        ventas_anuales['cantidad_total'] / ventas_anuales['dias_activo']
    )
    
    # Agregar columna utilidad
    ventas_anuales['utilidad'] = ventas_anuales['precio_total'] - ventas_anuales['costo_total']
    
    return ventas_anuales

def calcular_ventas_trimestre(df_tickets: pd.DataFrame, trimestre: str, año: int) -> pd.DataFrame:
    """Calcula métricas de ventas por trimestre"""
    
    df_trim = df_tickets[
        (df_tickets['trimestre'] == trimestre) & 
        (df_tickets['año'] == año)
    ].copy()
    
    if len(df_trim) == 0:
        return pd.DataFrame()
    
    ventas_trim = df_trim.groupby('idarticulo').agg({
        'cantidad_total': 'sum',
        'precio_total': 'sum',
        'costo_total': 'sum',
        'descripcion': 'first',
        'familia': 'first',
        'subfamilia': 'first',
        'idartalfa': 'first'
    }).reset_index()
    
    ventas_trim['margen_real'] = (
        (ventas_trim['precio_total'] - ventas_trim['costo_total']) / 
        ventas_trim['precio_total']
    )
    
    # Agregar columna utilidad
    ventas_trim['utilidad'] = ventas_trim['precio_total'] - ventas_trim['costo_total']
    
    return ventas_trim

def consolidar_ventas_con_stock(df_ventas: pd.DataFrame, df_stock: pd.DataFrame, 
                                df_presupuesto: pd.DataFrame, periodo: str) -> pd.DataFrame:
    """Consolida ventas con información de stock y presupuesto"""
    
    # Preparar datos de velocidad de venta
    ventas_con_velocidad = df_ventas[['idarticulo', 'velocidad_venta_diaria']].copy() if 'velocidad_venta_diaria' in df_ventas.columns else pd.DataFrame()
    
    # Merge con stock
    columnas_stock = [col for col in df_stock.columns if col.startswith('stk_')]
    df_stock_para_merge = df_stock[['idarticulo', 'idartalfa'] + columnas_stock + ['STK_TOTAL']].copy()
    
    if len(ventas_con_velocidad) > 0:
        df_stock_con_velocidad = pd.merge(
            df_stock_para_merge,
            ventas_con_velocidad,
            on='idarticulo',
            how='left'
        )
    else:
        df_stock_con_velocidad = df_stock_para_merge.copy()
        df_stock_con_velocidad['velocidad_venta_diaria'] = 0
    
    # Calcular días de cobertura
    df_stock_con_velocidad['dias_cobertura'] = df_stock_con_velocidad.apply(
        lambda row: calcular_dias_cobertura(row['STK_TOTAL'], row.get('velocidad_venta_diaria', 0)),
        axis=1
    )
    
    # Clasificar estado de stock
    df_stock_con_velocidad['estado_stock'] = df_stock_con_velocidad.apply(
        lambda row: clasificar_estado_stock(row['dias_cobertura'], row['STK_TOTAL']),
        axis=1
    )
    
    # Agregar información de proveedor
    if 'proveedor' in df_presupuesto.columns:
        df_presupuesto_info = df_presupuesto[['idarticulo', 'proveedor']].copy()
        df_stock_con_velocidad = pd.merge(
            df_stock_con_velocidad,
            df_presupuesto_info,
            on='idarticulo',
            how='left'
        )
        df_stock_con_velocidad['proveedor'] = df_stock_con_velocidad['proveedor'].fillna('N/D')
    else:
        df_stock_con_velocidad['proveedor'] = 'N/D'
    
    # Merge con ventas
    resultado = pd.merge(
        df_ventas,
        df_stock_con_velocidad,
        on='idarticulo',
        how='left',
        suffixes=('_venta', '_actual')
    )
    
    # Filtrar artículos con problema de stock
    resultado_filtrado = resultado[
        resultado['estado_stock'].isin(['QUEBRADO', 'QUIEBRE SEMANAL', 'QUIEBRE QUINCENAL'])
    ].copy()
    
    # Limpiar valores negativos
    resultado_filtrado = limpiar_valores_negativos(resultado_filtrado)
    
    return resultado_filtrado

# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZACIONES
# ═══════════════════════════════════════════════════════════════════════════════

def crear_grafica_top_con_metrica(df: pd.DataFrame, col_ordenar: str, col_color: str, 
                                  titulo: str, top_n: int = 10) -> go.Figure:
    """
    Crea gráfica de barras TOP con colores según métrica secundaria
    
    Args:
        df: DataFrame con datos
        col_ordenar: Columna para ordenar (eje Y - valores de barras)
        col_color: Columna para colorear (rentabilidad/utilidad)
        titulo: Título de la gráfica
        top_n: Número de elementos a mostrar
    """
    
    # Ordenar y tomar top N
    df_top = df.nlargest(top_n, col_ordenar).copy()
    
    # Preparar datos
    labels = df_top['descripcion'].tolist()
    valores = df_top[col_ordenar].tolist()
    colores_vals = df_top[col_color].tolist()
    
    # Si es porcentaje (margen_real), convertir a porcentaje
    if col_color == 'margen_real':
        text_hover = [f"{v*100:.1f}%" for v in colores_vals]
    else:
        text_hover = [f"${v:,.0f}" for v in colores_vals]
    
    # Crear figura
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=labels,
        x=valores,
        orientation='h',
        marker=dict(
            color=colores_vals,
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(
                title=col_color.replace('_', ' ').title()
            )
        ),
        text=text_hover,
        textposition='inside',
        textfont=dict(color='white', size=10),
        hovertemplate='<b>%{y}</b><br>' +
                     f'{col_ordenar.replace("_", " ").title()}: %{{x:,.0f}}<br>' +
                     f'{col_color.replace("_", " ").title()}: %{{text}}<br>' +
                     '<extra></extra>'
    ))
    
    fig.update_layout(
        title=titulo,
        xaxis_title=col_ordenar.replace('_', ' ').title(),
        yaxis_title='',
        height=400,
        showlegend=False,
        hovermode='closest'
    )
    
    return fig

def crear_grafica_dias_cobertura(df: pd.DataFrame, titulo: str, top_n: int = 10, cap_dias: int = 31) -> go.Figure:
    """
    Crea gráfica de días de cobertura con cap
    
    Args:
        df: DataFrame con datos
        titulo: Título de la gráfica
        top_n: Número de elementos a mostrar
        cap_dias: Límite máximo de días a mostrar
    """
    
    # Tomar top N por utilidad
    df_top = df.nlargest(top_n, 'utilidad').copy()
    
    # Aplicar cap a días de cobertura
    df_top['dias_cobertura_cap'] = df_top['dias_cobertura'].apply(lambda x: min(x, cap_dias))
    
    # Preparar datos
    labels = df_top['descripcion'].tolist()
    dias_reales = df_top['dias_cobertura'].tolist()
    dias_cap = df_top['dias_cobertura_cap'].tolist()
    
    # Colores según estado
    colores = []
    for estado in df_top['estado_stock']:
        if estado == 'QUEBRADO':
            colores.append('#F24848')
        elif estado == 'QUIEBRE SEMANAL':
            colores.append('#F7BE89')
        elif estado == 'QUIEBRE QUINCENAL':
            colores.append('#FFFFCC')
        else:
            colores.append('#90EE90')
    
    # Crear figura
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=labels,
        x=dias_cap,
        orientation='h',
        marker=dict(color=colores),
        text=[f"{d:.0f} días" for d in dias_reales],
        textposition='inside',
        textfont=dict(color='black', size=10),
        hovertemplate='<b>%{y}</b><br>' +
                     'Días Cobertura: %{text}<br>' +
                     '<extra></extra>'
    ))
    
    # Agregar línea vertical en cap
    fig.add_vline(x=cap_dias, line_dash="dash", line_color="red", 
                  annotation_text=f"Cap: {cap_dias} días")
    
    fig.update_layout(
        title=titulo,
        xaxis_title='Días de Cobertura',
        yaxis_title='',
        height=400,
        showlegend=False,
        hovermode='closest',
        xaxis=dict(range=[0, cap_dias + 5])
    )
    
    return fig

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN A EXCEL
# ═══════════════════════════════════════════════════════════════════════════════

def preparar_dataframe_para_excel(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara el DataFrame con formato y columnas ordenadas para Excel"""
    
    df_export = df.copy()
    
    # Consolidar columnas duplicadas
    if 'idartalfa_actual' in df_export.columns and 'idartalfa_venta' in df_export.columns:
        df_export['idartalfa'] = df_export['idartalfa_actual'].fillna(df_export['idartalfa_venta'])
    elif 'idartalfa_actual' in df_export.columns:
        df_export['idartalfa'] = df_export['idartalfa_actual']
    elif 'idartalfa_venta' in df_export.columns:
        df_export['idartalfa'] = df_export['idartalfa_venta']
    
    if 'descripcion_actual' in df_export.columns and 'descripcion_venta' in df_export.columns:
        df_export['descripcion'] = df_export['descripcion_venta'].fillna(df_export['descripcion_actual'])
    elif 'descripcion_actual' in df_export.columns:
        df_export['descripcion'] = df_export['descripcion_actual']
    elif 'descripcion_venta' in df_export.columns:
        df_export['descripcion'] = df_export['descripcion_venta']
    
    if 'familia_actual' in df_export.columns and 'familia_venta' in df_export.columns:
        df_export['familia'] = df_export['familia_venta'].fillna(df_export['familia_actual'])
    elif 'familia_actual' in df_export.columns:
        df_export['familia'] = df_export['familia_actual']
    elif 'familia_venta' in df_export.columns:
        df_export['familia'] = df_export['familia_venta']
    
    if 'subfamilia_actual' in df_export.columns and 'subfamilia_venta' in df_export.columns:
        df_export['subfamilia'] = df_export['subfamilia_venta'].fillna(df_export['subfamilia_actual'])
    elif 'subfamilia_actual' in df_export.columns:
        df_export['subfamilia'] = df_export['subfamilia_actual']
    elif 'subfamilia_venta' in df_export.columns:
        df_export['subfamilia'] = df_export['subfamilia_venta']
    
    # Orden de columnas
    columnas_stock = [col for col in df_export.columns if col.startswith('stk_')]
    
    columnas_orden = [
        'idarticulo', 'idartalfa', 'proveedor', 'descripcion',
        'cantidad_total', 'precio_total', 'costo_total', 'utilidad',
        'familia', 'subfamilia'
    ]
    columnas_orden.extend(columnas_stock)
    columnas_orden.extend([
        'STK_TOTAL', 'margen_real', 'velocidad_venta_diaria',
        'dias_cobertura', 'estado_stock'
    ])
    
    # Seleccionar columnas existentes
    columnas_finales = [col for col in columnas_orden if col in df_export.columns]
    df_final = df_export[columnas_finales].copy()
    
    # Convertir tipos
    if 'idarticulo' in df_final.columns:
        df_final['idarticulo'] = df_final['idarticulo'].astype(int)
    
    if 'idartalfa' in df_final.columns:
        df_final['idartalfa'] = pd.to_numeric(df_final['idartalfa'], errors='coerce').fillna(0).astype(int)
    
    for col in ['cantidad_total', 'precio_total', 'costo_total', 'utilidad', 'dias_cobertura', 'STK_TOTAL']:
        if col in df_final.columns:
            df_final[col] = df_final[col].round(0).astype(int)
    
    if 'velocidad_venta_diaria' in df_final.columns:
        df_final['velocidad_venta_diaria'] = df_final['velocidad_venta_diaria'].round(1)
    
    # Ordenar
    sort_cols = ['proveedor', 'familia', 'subfamilia', 'margen_real']
    sort_cols = [col for col in sort_cols if col in df_final.columns]
    
    if sort_cols:
        df_final = df_final.sort_values(sort_cols, ascending=[False]*len(sort_cols))
    
    return df_final

def generar_excel_con_formato(df: pd.DataFrame, periodo: str) -> bytes:
    """Genera archivo Excel con formato condicional"""
    
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Preparar datos
        df_excel = preparar_dataframe_para_excel(df)
        df_excel.to_excel(writer, sheet_name=periodo, index=False)
        
        worksheet = writer.sheets[periodo]
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        formato_quebrado = workbook.add_format({'bg_color': '#F24848'})
        formato_quiebre_semanal = workbook.add_format({'bg_color': '#F7BE89'})
        formato_quiebre_quincenal = workbook.add_format({'bg_color': '#FFFFCC'})
        
        # Aplicar formato a encabezados
        worksheet.set_row(0, 25)
        for col_num, col_name in enumerate(df_excel.columns):
            worksheet.write(0, col_num, col_name, header_format)
            max_len = max(df_excel[col_name].astype(str).apply(len).max(), len(col_name))
            worksheet.set_column(col_num, col_num, max_len + 2)
        
        # Formato condicional por estado
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
# FUNCIÓN PRINCIPAL PARA STREAMLIT
# ═══════════════════════════════════════════════════════════════════════════════

def main_analisis_stock_rentables(df_tickets_bigquery: pd.DataFrame, 
                                   df_presupuesto_bigquery: pd.DataFrame, 
                                   df_stock_bigquery: pd.DataFrame):
    """
    Función principal para renderizar el análisis en Streamlit
    
    Args:
        df_tickets_bigquery: DataFrame de tickets desde BigQuery (tickets_all)
        df_presupuesto_bigquery: DataFrame de presupuesto desde BigQuery (result_final_alert_all)
        df_stock_bigquery: DataFrame de stock consolidado desde BigQuery (stock_consolidado_pivoteado)
    """
    
    st.header("📦 Análisis de Stock - Artículos Rentables")
    
    # Preparar datos desde BigQuery
    with st.spinner("🔄 Preparando datos desde BigQuery..."):
        try:
            df_tickets, df_presupuesto, df_stock = preparar_datos_desde_bigquery(
                df_tickets_bigquery, df_presupuesto_bigquery, df_stock_bigquery
            )
            df_stock = procesar_stock_consolidado(df_stock)
            st.success("✅ Datos preparados correctamente")
        except Exception as e:
            st.error(f"❌ Error al preparar datos: {str(e)}")
            return
    
    # Determinar trimestre actual
    fecha_max = df_tickets['fecha_comprobante'].max()
    año_actual = fecha_max.year
    trimestre_actual = get_trimestre(fecha_max)
    
    # Selector de período
    st.subheader("📅 Selección de Período")
    
    periodos = ['ANUAL', 'Q1', 'Q2', 'Q3', 'Q4']
    nombres_periodos = [get_nombre_trimestre(p) for p in periodos]
    
    # Encontrar índice del trimestre actual
    indice_default = periodos.index(trimestre_actual)
    
    periodo_seleccionado = st.selectbox(
        "Seleccione el período a analizar:",
        periodos,
        format_func=lambda x: get_nombre_trimestre(x),
        index=indice_default
    )
    
    # Procesar datos según período seleccionado
    with st.spinner(f"🔄 Procesando datos para {get_nombre_trimestre(periodo_seleccionado)}..."):
        
        if periodo_seleccionado == 'ANUAL':
            # Análisis anual
            ventas_anuales = calcular_ventas_anuales(df_tickets)
            ventas_filtradas = ventas_anuales[
                (ventas_anuales['dias_activo'] >= DIAS_MINIMOS_ANUAL) &
                (ventas_anuales['margen_real'] >= MARGEN_MIN_BUENO)
            ].copy()
            
            df_resultado = consolidar_ventas_con_stock(
                ventas_filtradas, df_stock, df_presupuesto, periodo_seleccionado
            )
        else:
            # Análisis trimestral
            ventas_trim = calcular_ventas_trimestre(df_tickets, periodo_seleccionado, año_actual)
            
            if len(ventas_trim) == 0:
                st.warning(f"⚠️ No hay datos disponibles para {get_nombre_trimestre(periodo_seleccionado)}")
                return
            
            ventas_filtradas = ventas_trim[ventas_trim['margen_real'] >= MARGEN_MIN_BUENO].copy()
            
            # Calcular velocidad de venta desde datos anuales
            ventas_anuales = calcular_ventas_anuales(df_tickets)
            ventas_filtradas = pd.merge(
                ventas_filtradas,
                ventas_anuales[['idarticulo', 'velocidad_venta_diaria']],
                on='idarticulo',
                how='left'
            )
            
            df_resultado = consolidar_ventas_con_stock(
                ventas_filtradas, df_stock, df_presupuesto, periodo_seleccionado
            )
    
    # Mostrar métricas
    if len(df_resultado) == 0:
        st.info(f"✅ No hay artículos rentables con problemas de stock en {get_nombre_trimestre(periodo_seleccionado)}")
        return
    
    st.subheader("📊 Resumen")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Artículos con Problema", f"{len(df_resultado):,}")
    
    with col2:
        quebrados = len(df_resultado[df_resultado['estado_stock'] == 'QUEBRADO'])
        st.metric("🔴 Quebrados", f"{quebrados:,}")
    
    with col3:
        quiebre_semanal = len(df_resultado[df_resultado['estado_stock'] == 'QUIEBRE SEMANAL'])
        st.metric("🟠 Quiebre Semanal", f"{quiebre_semanal:,}")
    
    with col4:
        quiebre_quincenal = len(df_resultado[df_resultado['estado_stock'] == 'QUIEBRE QUINCENAL'])
        st.metric("🟡 Quiebre Quincenal", f"{quiebre_quincenal:,}")
    
    # Métricas adicionales
    col5, col6 = st.columns(2)
    
    with col5:
        venta_perdida = df_resultado['precio_total'].sum()
        st.metric("💰 Venta Potencial Perdida", f"${venta_perdida:,.0f}")
    
    with col6:
        utilidad_perdida = df_resultado['utilidad'].sum()
        st.metric("💵 Utilidad Potencial Perdida", f"${utilidad_perdida:,.0f}")
    
    st.markdown("---")
    
    # GRUPO 1: Top por Utilidad + Días Cobertura
    st.subheader("📈 Grupo 1: Análisis por Utilidad")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = crear_grafica_top_con_metrica(
            df_resultado, 
            col_ordenar='utilidad',
            col_color='margen_real',
            titulo='🏆 Top 10 por Utilidad (color: Margen %)',
            top_n=10
        )
        st.plotly_chart(fig1, width='stretch')
    
    with col2:
        fig2 = crear_grafica_dias_cobertura(
            df_resultado,
            titulo='⏱️ Días de Cobertura (Cap: 31 días)',
            top_n=10,
            cap_dias=31
        )
        st.plotly_chart(fig2, width='stretch')
    
    st.markdown("---")
    
    # GRUPO 2: Top por Margen + Días Cobertura
    st.subheader("📈 Grupo 2: Análisis por Margen Real")
    
    col3, col4 = st.columns(2)
    
    with col3:
        fig3 = crear_grafica_top_con_metrica(
            df_resultado,
            col_ordenar='margen_real',
            col_color='utilidad',
            titulo='🏆 Top 10 por Margen % (color: Utilidad)',
            top_n=10
        )
        st.plotly_chart(fig3, width='stretch')
    
    with col4:
        # Usar los mismos top 10 por margen
        df_top_margen = df_resultado.nlargest(10, 'margen_real')
        fig4 = crear_grafica_dias_cobertura(
            df_top_margen,
            titulo='⏱️ Días de Cobertura (Cap: 31 días)',
            top_n=10,
            cap_dias=31
        )
        st.plotly_chart(fig4, width='stretch')
    
    st.markdown("---")
    
    # Tabla de datos
    st.subheader("📋 Detalle de Artículos")
    
    # Preparar DataFrame para mostrar
    df_display = preparar_dataframe_para_excel(df_resultado)
    
    # Formatear columnas para visualización
    st.dataframe(
        df_display,
        width='stretch',
        hide_index=True,
        column_config={
            "precio_total": st.column_config.NumberColumn("Precio Total", format="$%d"),
            "costo_total": st.column_config.NumberColumn("Costo Total", format="$%d"),
            "utilidad": st.column_config.NumberColumn("Utilidad", format="$%d"),
            "margen_real": st.column_config.NumberColumn("Margen %", format="%.2f%%"),
            "velocidad_venta_diaria": st.column_config.NumberColumn("Vel. Venta Diaria", format="%.1f"),
            "dias_cobertura": st.column_config.NumberColumn("Días Cobertura", format="%d"),
        }
    )
    
    # Botón de descarga
    st.subheader("💾 Descargar Reporte")
    
    nombre_archivo = f"Stock_Rentables_{periodo_seleccionado}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    
    excel_bytes = generar_excel_con_formato(df_resultado, periodo_seleccionado)
    
    st.download_button(
        label="📥 Descargar Excel",
        data=excel_bytes,
        file_name=nombre_archivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Leyenda
    st.markdown("---")
    st.info("💡 **Clasificación de alertas:**")
    st.info("🔴 **QUEBRADO**: Stock = 0 unidades")
    st.info("🟠 **QUIEBRE SEMANAL**: 1-7 días de cobertura")
    st.info("🟡 **QUIEBRE QUINCENAL**: 8-15 días de cobertura")