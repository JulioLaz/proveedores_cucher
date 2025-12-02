import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

@st.cache_data(ttl=300, show_spinner=False)  # Cache por 5 minutos
def get_ventas_data(credentials_path, project_id, bigquery_table, fecha_desde, fecha_hasta):
    """
    Obtiene datos de ventas de BigQuery (CACHEADO)
    """
    print(f"\n🔄 EJECUTANDO QUERY DE VENTAS (sin caché)")
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
    print(f"✅ Query ventas: {len(df):,} registros en {tiempo:.2f}s")
    
    return df


@st.cache_data(ttl=300, show_spinner=False)  # Cache por 5 minutos
def get_presupuesto_data(credentials_path, project_id):
    """
    Obtiene datos de presupuesto (CACHEADO)
    """
    print(f"\n🔄 EJECUTANDO QUERY DE PRESUPUESTO (sin caché)")
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
    print(f"✅ Query presupuesto: {len(df):,} registros en {tiempo:.2f}s")
    
    return df


@st.cache_data(ttl=300, show_spinner=False)
def process_ranking_data(df_proveedores, df_ventas, df_presupuesto):
    """
    Procesa y genera el ranking (CACHEADO)
    """
    print(f"\n🔧 PROCESANDO RANKING (sin caché)")
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
    print(f"✅ Ranking procesado: {len(ranking)} proveedores en {tiempo:.2f}s")
    
    return ranking

# import streamlit as st
# import pandas as pd
# from datetime import datetime, timedelta

# @st.cache_data(ttl=300, show_spinner=False)  # Cache por 5 minutos
# def get_ventas_data(credentials_path, project_id, bigquery_table, fecha_desde, fecha_hasta):
#     """
#     Obtiene datos de ventas de BigQuery (CACHEADO)
#     """
#     print(f"\n🔄 EJECUTANDO QUERY DE VENTAS (sin caché)")
#     import time
#     from google.cloud import bigquery
    
#     inicio = time.time()
#     client = bigquery.Client.from_service_account_json(credentials_path)
    
#     query = f"""
#     SELECT 
#         idarticulo,
#         SUM(precio_total) as venta_total,
#         SUM(costo_total) as costo_total,
#         SUM(cantidad_total) as cantidad_vendida
#     FROM `{project_id}.{bigquery_table}`
#     WHERE DATE(fecha_comprobante) BETWEEN '{fecha_desde}' AND '{fecha_hasta}'
#     GROUP BY idarticulo
#     """
    
#     df = client.query(query).to_dataframe()
#     tiempo = time.time() - inicio
#     print(f"✅ Query ventas: {len(df):,} registros en {tiempo:.2f}s")
    
#     return df

# @st.cache_data(ttl=3600, show_spinner=False)  # Cache por 1 hora (cambia poco)
# def get_familias_data(credentials_path, project_id):
#     """
#     Obtiene familia y subfamilia de todos los artículos (CACHEADO)
#     Query ligera - solo trae 3 columnas
#     """
#     print(f"\n🔄 EJECUTANDO QUERY DE FAMILIAS (sin caché)")
#     import time
#     from google.cloud import bigquery
    
#     inicio = time.time()
#     client = bigquery.Client.from_service_account_json(credentials_path)
    
#     # ⚠️ AJUSTA EL NOMBRE DE TU TABLA DE ARTÍCULOS
#     query = f"""
#     SELECT DISTINCT
#         idarticulo,
#         familia,
#         subfamilia
#     FROM `{project_id}.tu_dataset.tu_tabla_de_articulos`
#     WHERE familia IS NOT NULL
#     """
    
#     df = client.query(query).to_dataframe()
#     tiempo = time.time() - inicio
#     print(f"✅ Query familias: {len(df):,} artículos en {tiempo:.2f}s")
#     print(f"   🏷️  Familias únicas: {df['familia'].nunique()}")
#     print(f"   📂 Subfamilias únicas: {df['subfamilia'].nunique()}")
    
#     return df

# @st.cache_data(ttl=300, show_spinner=False)  # Cache por 5 minutos
# def get_presupuesto_data(credentials_path, project_id):
#     """
#     Obtiene datos de presupuesto (CACHEADO)
#     """
#     print(f"\n🔄 EJECUTANDO QUERY DE PRESUPUESTO (sin caché)")
#     import time
#     from utils import query_resultados_idarticulo
    
#     inicio = time.time()
#     df = query_resultados_idarticulo(
#         credentials_path=credentials_path,
#         project_id=project_id,
#         dataset='presupuesto',
#         table='result_final_alert_all'
#     )
#     tiempo = time.time() - inicio
#     print(f"✅ Query presupuesto: {len(df):,} registros en {tiempo:.2f}s")
    
#     return df


# @st.cache_data(ttl=300, show_spinner=False)
# def process_ranking_data(df_proveedores, df_ventas, df_presupuesto, df_familias):
#     """
#     Procesa y genera el ranking (CACHEADO)
#     """
#     print(f"\n🔧 PROCESANDO RANKING (sin caché)")
#     import time
    
#     inicio = time.time()
    
#     # === AGREGAR FAMILIA Y SUBFAMILIA A df_proveedores ===
#     print(f"   🔗 Agregando familia/subfamilia a df_proveedores...")
#     df_proveedores_completo = df_proveedores.merge(
#         df_familias[['idarticulo', 'familia', 'subfamilia']],
#         on='idarticulo',
#         how='left'
#     )
    
#     print(f"   ✅ Merge completado: {len(df_proveedores_completo):,} artículos")
#     print(f"   🏷️  Familias: {df_proveedores_completo['familia'].nunique()}")
#     print(f"   📂 Subfamilias: {df_proveedores_completo['subfamilia'].nunique()}")
    
#     # === MERGE PRINCIPAL ===
#     columnas_proveedores = ['idarticulo', 'proveedor', 'idproveedor', 'familia', 'subfamilia']
    
#     df_merge = df_proveedores_completo[columnas_proveedores].merge(
#         df_ventas, on='idarticulo', how='left'
#     ).merge(
#         df_presupuesto[['idarticulo', 'PRESUPUESTO', 'exceso_STK', 'costo_exceso_STK', 'STK_TOTAL']],
#         on='idarticulo',
#         how='left'
#     )
    
#     print(f"   📊 Merge completado: {len(df_merge):,} registros")
#     if 'familia' in df_merge.columns:
#         print(f"   🏷️  Familias en merge: {df_merge['familia'].nunique()}")
#     if 'subfamilia' in df_merge.columns:
#         print(f"   📂 Subfamilias en merge: {df_merge['subfamilia'].nunique()}")
    
#     # Fillna
#     df_merge['venta_total'] = df_merge['venta_total'].fillna(0)
#     df_merge['costo_total'] = df_merge['costo_total'].fillna(0)
#     df_merge['cantidad_vendida'] = df_merge['cantidad_vendida'].fillna(0)
#     df_merge['PRESUPUESTO'] = df_merge['PRESUPUESTO'].fillna(0)
#     df_merge['exceso_STK'] = df_merge['exceso_STK'].fillna(0)
#     df_merge['costo_exceso_STK'] = df_merge['costo_exceso_STK'].fillna(0)
#     df_merge['STK_TOTAL'] = df_merge['STK_TOTAL'].fillna(0)
    
#     # === AGREGACIÓN POR PROVEEDOR (sin agrupar por familia/subfamilia) ===
#     # Solo agrupamos por proveedor para el ranking global
#     ranking = df_merge.groupby(['proveedor', 'idproveedor']).agg({
#         'venta_total': 'sum',
#         'costo_total': 'sum',
#         'cantidad_vendida': 'sum',
#         'idarticulo': 'count',
#         'PRESUPUESTO': 'sum',
#         'exceso_STK': lambda x: (x > 0).sum(),
#         'costo_exceso_STK': 'sum',
#         'STK_TOTAL': lambda x: (x == 0).sum()
#     }).reset_index()
    
#     ranking.columns = [
#         'Proveedor', 'ID', 'Venta Total', 'Costo Total', 'Cantidad Vendida', 
#         'Artículos', 'Presupuesto', 'Art. con Exceso', 
#         'Costo Exceso', 'Art. Sin Stock'
#     ]
    
#     # Cálculos
#     ranking['Utilidad'] = (ranking['Venta Total'] - ranking['Costo Total']).round(0).astype(int)
#     ranking['Rentabilidad %'] = ((ranking['Utilidad'] / ranking['Venta Total']) * 100).round(2)
#     ranking['% Participación Presupuesto'] = (ranking['Presupuesto'] / ranking['Presupuesto'].sum() * 100).round(2)
#     ranking['% Participación Ventas'] = (ranking['Venta Total'] / ranking['Venta Total'].sum() * 100).round(2)
#     ranking['% Participación Utilidad'] = (ranking['Utilidad'] / ranking['Utilidad'].sum() * 100).round(2)
#     ranking = ranking.sort_values('Venta Total', ascending=False).reset_index(drop=True)
#     ranking['Ranking'] = range(1, len(ranking) + 1)
    
#     tiempo = time.time() - inicio
#     print(f"✅ Ranking procesado: {len(ranking)} proveedores en {tiempo:.2f}s")
    
#     return ranking