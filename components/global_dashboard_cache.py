import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

@st.cache_data(ttl=3600, show_spinner=True)  # ✅ Cache 1 hora, con spinner
def get_ventas_data(credentials_path, project_id, bigquery_table, fecha_desde, fecha_hasta):
    """
    Obtiene datos de ventas de BigQuery (CACHEADO)
    """
    print(f"\n{'='*80}")
    print(f"🔄 EJECUTANDO QUERY DE VENTAS")
    print(f"   └─ Período: {fecha_desde} → {fecha_hasta}")
    print(f"{'='*80}")
    
    import time
    from google.cloud import bigquery
    
    inicio = time.time()
    client = bigquery.Client.from_service_account_json(credentials_path)
    
    query = f"""
    SELECT 
        idarticulo,
        SUM(precio_total) as venta_total,
        SUM(costo_total) as costo_total,
        SUM(cantidad_total) as cantidad_vendida
    FROM `{project_id}.{bigquery_table}`
    WHERE DATE(fecha_comprobante) BETWEEN '{fecha_desde}' AND '{fecha_hasta}'
    GROUP BY idarticulo
    """
    
    df = client.query(query).to_dataframe()
    tiempo = time.time() - inicio
    
    print(f"\n✅ Query ventas ejecutada exitosamente")
    print(f"   ├─ Registros: {len(df):,}")
    print(f"   ├─ Artículos únicos: {df['idarticulo'].nunique():,}")
    print(f"   └─ Tiempo: {tiempo:.2f}s")
    
    return df


@st.cache_data(ttl=3600, show_spinner=True)  # ✅ Cache 1 hora, con spinner
def get_presupuesto_data(credentials_path, project_id):
    """
    Obtiene datos de presupuesto (CACHEADO)
    """
    print(f"\n{'='*80}")
    print(f"🔄 EJECUTANDO QUERY DE PRESUPUESTO")
    print(f"{'='*80}")
    
    import time
    from utils import query_resultados_idarticulo
    
    inicio = time.time()
    df = query_resultados_idarticulo(
        credentials_path=credentials_path,
        project_id=project_id,
        dataset='presupuesto',
        table='result_final_alert_all'
    )
    tiempo = time.time() - inicio
    
    print(f"\n✅ Query presupuesto ejecutada exitosamente")
    print(f"   ├─ Registros: {len(df):,}")
    print(f"   └─ Tiempo: {tiempo:.2f}s")
    
    return df


@st.cache_data(ttl=3600, show_spinner=False)  # ✅ Procesamiento rápido, sin spinner
def process_ranking_data(df_proveedores, df_ventas, df_presupuesto):
    """
    Procesa y genera el ranking (CACHEADO)
    """
    print(f"\n{'='*80}")
    print(f"🔧 PROCESANDO RANKING")
    print(f"{'='*80}")
    
    import time
    
    inicio = time.time()
    
    # Merge
    df_merge = df_proveedores[['idarticulo', 'proveedor', 'idproveedor']].merge(
        df_ventas, on='idarticulo', how='left'
    ).merge(
        df_presupuesto[['idarticulo', 'PRESUPUESTO', 'exceso_STK', 'costo_exceso_STK', 'STK_TOTAL']],
        on='idarticulo',
        how='left'
    )
    
    # Fillna
    df_merge['venta_total'] = df_merge['venta_total'].fillna(0)
    df_merge['costo_total'] = df_merge['costo_total'].fillna(0)
    df_merge['cantidad_vendida'] = df_merge['cantidad_vendida'].fillna(0)
    df_merge['PRESUPUESTO'] = df_merge['PRESUPUESTO'].fillna(0)
    df_merge['exceso_STK'] = df_merge['exceso_STK'].fillna(0)
    df_merge['costo_exceso_STK'] = df_merge['costo_exceso_STK'].fillna(0)
    df_merge['STK_TOTAL'] = df_merge['STK_TOTAL'].fillna(0)
    
    # Agregación
    ranking = df_merge.groupby(['proveedor', 'idproveedor']).agg({
        'venta_total': 'sum',
        'costo_total': 'sum',
        'cantidad_vendida': 'sum',
        'idarticulo': 'count',
        'PRESUPUESTO': 'sum',
        'exceso_STK': lambda x: (x > 0).sum(),
        'costo_exceso_STK': 'sum',
        'STK_TOTAL': lambda x: (x == 0).sum()
    }).reset_index()
    
    ranking.columns = [
        'Proveedor', 'ID', 'Venta Total', 'Costo Total', 'Cantidad Vendida', 
        'Artículos', 'Presupuesto', 'Art. con Exceso', 
        'Costo Exceso', 'Art. Sin Stock'
    ]
    
    # Cálculos
    ranking['Utilidad'] = (ranking['Venta Total'] - ranking['Costo Total']).round(0).astype(int)
    ranking['Rentabilidad %'] = ((ranking['Utilidad'] / ranking['Venta Total']) * 100).round(2)
    ranking['% Participación Presupuesto'] = (ranking['Presupuesto'] / ranking['Presupuesto'].sum() * 100).round(2)
    ranking['% Participación Ventas'] = (ranking['Venta Total'] / ranking['Venta Total'].sum() * 100).round(2)
    ranking['% Participación Utilidad'] = (ranking['Utilidad'] / ranking['Utilidad'].sum() * 100).round(2)
    ranking = ranking.sort_values('Venta Total', ascending=False).reset_index(drop=True)
    ranking['Ranking'] = range(1, len(ranking) + 1)
    
    tiempo = time.time() - inicio
    
    print(f"\n✅ Ranking procesado exitosamente")
    print(f"   ├─ Proveedores: {len(ranking)}")
    print(f"   ├─ Venta Total: ${ranking['Venta Total'].sum():,.0f}")
    print(f"   └─ Tiempo: {tiempo:.2f}s")
    
    return ranking