"""
Funciones para procesamiento y cálculo de datos
"""
import pandas as pd
import streamlit as st


@st.cache_data(ttl=3600)
def load_proveedores_from_sheet(sheet_id, sheet_name, 
                                proveedor_unificado, nombres_unificados):
    """
    Cargar datos de proveedores desde Google Sheet público
    
    Args:
        sheet_id: ID de la Google Sheet
        sheet_name: Nombre de la hoja
        proveedor_unificado: Diccionario de mapeo de IDs
        nombres_unificados: Diccionario de nombres unificados
    
    Returns:
        DataFrame con los datos de proveedores
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url)
    df = df.dropna(subset=['idproveedor'])
    df['idproveedor'] = df['idproveedor'].astype(int)
    df['proveedor'] = df['proveedor'].astype(str).str.strip().str.upper()
    
    # 🔥 UNIFICACIÓN: Cambiar ID pero MANTENER todas las filas
    df['idproveedor_original'] = df['idproveedor']  # Guardar original
    df['idproveedor'] = df['idproveedor'].map(proveedor_unificado).fillna(df['idproveedor']).astype(int)
    df['proveedor'] = df['idproveedor'].map(nombres_unificados).fillna(df['proveedor'])
    
    return df


def calculate_metrics(df):
    """
    Calcular métricas principales de ventas
    
    Args:
        df: DataFrame con datos de tickets/ventas
    
    Returns:
        dict: Diccionario con métricas calculadas
    """
    # Sucursales únicas
    if 'sucursal' in df.columns:
        sucursales_unicas = df['sucursal'].dropna().unique()
        num_sucursales = len(sucursales_unicas)
        sucursales_str = ", ".join(sorted(s[:4].upper() for s in sucursales_unicas))
    else:
        num_sucursales = 0
        sucursales_str = "N/A"
    
    # Familias únicas
    num_familias = df['familia'].nunique() if 'familia' in df.columns else 0
    
    return {
        'total_ventas': df['precio_total'].sum(),
        'total_costos': df['costo_total'].sum(),
        'total_utilidad': df['utilidad'].sum(),
        'margen_promedio': df['margen_porcentual'].mean(),
        'total_cantidad': df['cantidad_total'].sum(),
        'num_tickets': len(df),
        'ticket_promedio': df['precio_total'].sum() / len(df) if len(df) > 0 else 0,
        'productos_unicos': df['idarticulo'].nunique(),
        'dias_con_ventas': df['fecha'].nunique(),
        'sucursales': num_sucursales,
        'sucursales_presentes': sucursales_str,
        'familias': num_familias
    }


def generate_insights(df, metrics):
    """
    Generar insights automáticos basados en datos y métricas
    
    Args:
        df: DataFrame con datos de ventas
        metrics: Diccionario con métricas calculadas
    
    Returns:
        list: Lista de tuplas (tipo, mensaje) con insights
    """
    insights = []
    
    # Análisis de rentabilidad
    if metrics['margen_promedio'] > 30:
        insights.append(("success", f"🎯 Excelente rentabilidad: {metrics['margen_promedio']:.1f}% de margen promedio"))
    elif metrics['margen_promedio'] > 20:
        insights.append(("info", f"📈 Buena rentabilidad: {metrics['margen_promedio']:.1f}% de margen promedio"))
    else:
        insights.append(("warning", f"⚠️ Margen bajo: {metrics['margen_promedio']:.1f}% - Revisar estrategia de precios"))
    
    # Análisis de productos
    top_producto = df.groupby('descripcion')['precio_total'].sum().nlargest(1)
    if len(top_producto) > 0:
        producto_name = top_producto.index[0]
        producto_ventas = top_producto.iloc[0]
        participacion = (producto_ventas / metrics['total_ventas']) * 100
        insights.append(("info", f"🏆 Producto estrella: {producto_name[:50]}... ({participacion:.1f}% de ventas)"))
    
    # Análisis temporal
    if len(df) > 7:
        ventas_por_dia = df.groupby('fecha')['precio_total'].sum()
        tendencia_dias = 7
        if len(ventas_por_dia) >= tendencia_dias:
            ultimos_dias = ventas_por_dia.tail(tendencia_dias).mean()
            primeros_dias = ventas_por_dia.head(tendencia_dias).mean()
            if ultimos_dias > primeros_dias * 1.1:
                insights.append(("success", f"📈 Tendencia positiva: +{((ultimos_dias/primeros_dias-1)*100):.1f}% en últimos días"))
            elif ultimos_dias < primeros_dias * 0.9:
                insights.append(("warning", f"📉 Tendencia bajista: {((ultimos_dias/primeros_dias-1)*100):.1f}% en últimos días"))
    
    # Análisis de diversificación
    if metrics['productos_unicos'] < 5:
        insights.append(("warning", "🎯 Baja diversificación de productos - Considerar ampliar catálogo"))
    elif metrics['productos_unicos'] > 20:
        insights.append(("success", f"🌟 Excelente diversificación: {metrics['productos_unicos']} productos únicos"))
    
    # Análisis de ticket promedio
    if metrics['ticket_promedio'] > 5000:
        insights.append(("success", f"💰 Alto valor por transacción: ${metrics['ticket_promedio']:,.0f}"))
    elif metrics['ticket_promedio'] < 1000:
        insights.append(("info", "💡 Oportunidad de cross-selling para aumentar ticket promedio"))
    
    return insights


def format_abbr(x):
    """
    Formatear números con abreviaciones (K, M)
    
    Args:
        x: Número a formatear
    
    Returns:
        str: Número formateado
    """
    if x >= 1_000_000: 
        return f"${x/1_000_000:.1f}M"
    elif x >= 1_000: 
        return f"${x/1_000:.0f}K"
    else: 
        return f"${x:.0f}"