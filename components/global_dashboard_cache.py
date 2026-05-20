import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from google.cloud import bigquery
import time
import os
import numpy as np


@st.cache_data(ttl=3600, show_spinner=True)
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
        MAX(descripcion) as descripcion,
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
    print(f"   ├─ Con descripción: {df['descripcion'].notna().sum():,}")
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

@st.cache_data(ttl=3600)
def get_familias_data(credentials_path, project_id, bigquery_table):
    """
    Obtener familias y subfamilias de artículos desde la tabla de ventas.
    
    Args:
        credentials_path (str): Ruta a las credenciales de GCP
        project_id (str): ID del proyecto de BigQuery
        bigquery_table (str): Nombre completo de la tabla (proyecto.dataset.tabla)
    
    Returns:
        pd.DataFrame: DataFrame con idarticulo, familia, subfamilia
    """
    print("\n" + "="*60)
    print("📦 CARGANDO FAMILIAS Y SUBFAMILIAS")
    print("="*60)
    inicio = time.time()
    
    # ✅ USAR LA MISMA TABLA QUE LAS VENTAS
    query = f"""
    SELECT DISTINCT
        idarticulo,
        familia,
        subfamilia
    FROM `{bigquery_table}`
    WHERE idarticulo IS NOT NULL
        AND familia IS NOT NULL
    ORDER BY idarticulo
    """
    
    try:
        print(f"   📊 Tabla fuente: {bigquery_table}")
        print(f"   🔍 Query: Obteniendo familias únicas...")
        
        client = bigquery.Client.from_service_account_json(
            credentials_path,
            project=project_id
        )
        
        df = client.query(query).to_dataframe()
        
        tiempo = time.time() - inicio
        
        print(f"   ✅ {len(df):,} artículos con familia/subfamilia")
        print(f"   📁 {df['familia'].nunique()} familias únicas")
        print(f"   📂 {df['subfamilia'].nunique()} subfamilias únicas")
        print(f"   ⏱️  Tiempo: {tiempo:.2f}s")
        print("="*60 + "\n")
        
        return df
        
    except Exception as e:
        print(f"   ❌ ERROR al cargar familias: {e}")
        print("="*60 + "\n")
        return pd.DataFrame(columns=['idarticulo', 'familia', 'subfamilia'])

# ============================================================================
# CORRECCIÓN EN process_ranking_data
# ============================================================================

'''
═══════════════════════════════════════════════════════════════════════════════
 process_ranking_data_flias_subflias.py
═══════════════════════════════════════════════════════════════════════════════
 Genera el ranking de proveedores DESGLOSADO por familia y subfamilia.

 Es la versión "abierta" de process_ranking_data(): en lugar de una fila por
 proveedor, produce una fila por cada combinación
 [proveedor, idproveedor, familia, subfamilia], conservando exactamente las
 mismas métricas (Venta Total, Costo Total, Cantidad Vendida, Artículos,
 Presupuesto, Art. con Exceso, Costo Exceso, Art. Sin Stock) y los mismos
 cálculos derivados (Utilidad, Rentabilidad %, % de Participación sobre el
 total general).

 Orden de salida:
   1) Proveedores ordenados por su Venta Total acumulada (desc).
   2) Dentro de cada proveedor, filas familia/subfamilia por Venta Total (desc).

 La columna 'Ranking' es secuencial sobre ese orden jerárquico.
═══════════════════════════════════════════════════════════════════════════════
 VERSIONADO
───────────────────────────────────────────────────────────────────────────────
 v1.0  (2026-05-19) - Versión inicial. Replica process_ranking_data() agregando
                      el desglose por familia y subfamilia. Mismo cacheo,
                      mismos fillna, mismos prints con timing. Único agregado:
                      protección de división por cero en 'Rentabilidad %'
                      (necesaria porque el desglose genera filas con
                      Venta Total = 0).
═══════════════════════════════════════════════════════════════════════════════
'''
'''
═══════════════════════════════════════════════════════════════════════════════
 process_ranking_data_flias_subflias.py
═══════════════════════════════════════════════════════════════════════════════
 Genera el ranking de proveedores DESGLOSADO por familia y subfamilia.

 Es la versión "abierta" de process_ranking_data(): en lugar de una fila por
 proveedor, produce una fila por cada combinación
 [proveedor, idproveedor, familia, subfamilia], conservando exactamente las
 mismas métricas (Venta Total, Costo Total, Cantidad Vendida, Artículos,
 Presupuesto, Art. con Exceso, Costo Exceso, Art. Sin Stock) y los mismos
 cálculos derivados (Utilidad, Rentabilidad %, % de Participación sobre el
 total general).

 Orden de salida (jerárquico, todo por Venta Total desc):
   1) Proveedores ordenados por su Venta Total acumulada (desc).
   2) Dentro de cada proveedor, Familias por su Venta Total acumulada (desc).
   3) Dentro de cada familia, Subfamilias por su Venta Total (desc).

 La columna 'Ranking' es secuencial sobre ese orden jerárquico.
═══════════════════════════════════════════════════════════════════════════════
 VERSIONADO
───────────────────────────────────────────────────────────────────────────────
 v1.0  (2026-05-19) - Versión inicial. Replica process_ranking_data() agregando
                      el desglose por familia y subfamilia. Mismo cacheo,
                      mismos fillna, mismos prints con timing. Único agregado:
                      protección de división por cero en 'Rentabilidad %'
                      (necesaria porque el desglose genera filas con
                      Venta Total = 0).
 v1.1  (2026-05-19) - Orden jerárquico: el proveedor mantiene su posición por
                      Venta Total acumulada y, dentro de él, se ordena primero
                      por Familia (por venta acumulada desc) y luego por
                      Subfamilia (por venta desc).
═══════════════════════════════════════════════════════════════════════════════
'''

import time
import numpy as np
import pandas as pd
import streamlit as st

## FUERA DE USO, TOMADA DEL MODULE: 
## C:\CUCHER_STREAMLIT\CUCHER_STREAMLIT\components\process_ranking_data_flias_subflias.py
@st.cache_data(ttl=300, show_spinner=False)
def process_ranking_data_flias_subflias_00(df_proveedores, df_ventas, df_presupuesto, df_familias):
    """
    Procesa y genera el ranking de proveedores desglosado por
    familia/subfamilia (CACHEADO).
    """
    print(f"\n🔧 PROCESANDO RANKING FLIAS/SUBFLIAS (sin caché)")
    inicio = time.time()

    # === VERIFICAR QUE df_familias TENGA LAS COLUMNAS ===
    print(f"   🔍 Verificando df_familias...")
    print(f"      Columnas en df_familias: {list(df_familias.columns)}")
    print(f"      Registros en df_familias: {len(df_familias):,}")

    # === LIMPIAR COLUMNAS DUPLICADAS EN df_proveedores ===
    columnas_a_eliminar = []
    if 'familia' in df_proveedores.columns:
        columnas_a_eliminar.append('familia')
    if 'subfamilia' in df_proveedores.columns:
        columnas_a_eliminar.append('subfamilia')

    if columnas_a_eliminar:
        print(f"   🧹 Eliminando columnas duplicadas de df_proveedores: {columnas_a_eliminar}")
        df_proveedores = df_proveedores.drop(columns=columnas_a_eliminar)

    # === AGREGAR FAMILIA/SUBFAMILIA desde df_familias ===
    print(f"   🔗 Agregando familia/subfamilia...")

    columnas_merge = ['idarticulo']
    if 'familia' in df_familias.columns:
        columnas_merge.append('familia')
    if 'subfamilia' in df_familias.columns:
        columnas_merge.append('subfamilia')

    print(f"      Columnas a mergear: {columnas_merge}")

    df_proveedores_completo = df_proveedores.merge(
        df_familias[columnas_merge],
        on='idarticulo',
        how='left'
    )

    print(f"   ✅ Artículos con info: {len(df_proveedores_completo):,}")
    print(f"      Columnas después del merge: {list(df_proveedores_completo.columns)}")

    # === ASEGURAR familia/subfamilia (necesarias para el desglose) ===
    if 'familia' in df_proveedores_completo.columns:
        df_proveedores_completo['familia'] = df_proveedores_completo['familia'].fillna('SIN FAMILIA')
    else:
        df_proveedores_completo['familia'] = 'SIN FAMILIA'
        print(f"   ⚠️  Columna 'familia' no encontrada -> se asigna 'SIN FAMILIA'")

    if 'subfamilia' in df_proveedores_completo.columns:
        df_proveedores_completo['subfamilia'] = df_proveedores_completo['subfamilia'].fillna('SIN SUBFAMILIA')
    else:
        df_proveedores_completo['subfamilia'] = 'SIN SUBFAMILIA'
        print(f"   ⚠️  Columna 'subfamilia' no encontrada -> se asigna 'SIN SUBFAMILIA'")

    print(f"   🏷️  Familias: {df_proveedores_completo['familia'].nunique()}")
    print(f"   📂 Subfamilias: {df_proveedores_completo['subfamilia'].nunique()}")

    # === MERGE PRINCIPAL ===
    columnas_para_merge = ['idarticulo', 'proveedor', 'idproveedor', 'familia', 'subfamilia']

    df_merge = df_proveedores_completo[columnas_para_merge].merge(
        df_ventas,
        on='idarticulo',
        how='left'
    ).merge(
        df_presupuesto[['idarticulo', 'PRESUPUESTO', 'exceso_STK', 'costo_exceso_STK', 'STK_TOTAL']],
        on='idarticulo',
        how='left'
    )

    # === FILLNA (idéntico a process_ranking_data) ===
    df_merge['venta_total'] = df_merge['venta_total'].fillna(0)
    df_merge['costo_total'] = df_merge['costo_total'].fillna(0)
    df_merge['cantidad_vendida'] = df_merge['cantidad_vendida'].fillna(0)
    df_merge['PRESUPUESTO'] = df_merge['PRESUPUESTO'].fillna(0)
    df_merge['exceso_STK'] = df_merge['exceso_STK'].fillna(0)
    df_merge['costo_exceso_STK'] = df_merge['costo_exceso_STK'].fillna(0)
    df_merge['STK_TOTAL'] = df_merge['STK_TOTAL'].fillna(0)

    # === AGREGACIÓN POR proveedor + idproveedor + familia + subfamilia ===
    ranking = df_merge.groupby(
        ['proveedor', 'idproveedor', 'familia', 'subfamilia']
    ).agg({
        'venta_total': 'sum',
        'costo_total': 'sum',
        'cantidad_vendida': 'sum',
        'idarticulo': 'count',
        'PRESUPUESTO': 'sum',
        'exceso_STK': lambda x: (x > 0).sum(),
        'costo_exceso_STK': 'sum',
        'STK_TOTAL': lambda x: (x == 0).sum()
    }).reset_index()

    # ✅ RENOMBRAR COLUMNAS (compatible con global_dashboard.py + Familia/Subfamilia)
    ranking.columns = [
        'Proveedor', 'ID Proveedor', 'Familia', 'Subfamilia',
        'Venta Total', 'Costo Total', 'Cantidad Vendida', 'Artículos',
        'Presupuesto', 'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
    ]

    # === CÁLCULOS ADICIONALES (mismas métricas; % sobre total general) ===
    ranking['Utilidad'] = (ranking['Venta Total'] - ranking['Costo Total']).round(0).astype(int)

    # Misma fórmula que la original, con protección /0 (el desglose genera
    # filas con Venta Total = 0 que producirían inf).
    ranking['Rentabilidad %'] = (
        (ranking['Utilidad'] / ranking['Venta Total'].replace(0, np.nan)) * 100
    ).round(2).fillna(0)

    ranking['% Participación Presupuesto'] = (ranking['Presupuesto'] / ranking['Presupuesto'].sum() * 100).round(2)
    ranking['% Participación Ventas'] = (ranking['Venta Total'] / ranking['Venta Total'].sum() * 100).round(2)
    ranking['% Participación Utilidad'] = (ranking['Utilidad'] / ranking['Utilidad'].sum() * 100).round(2)

    # === ORDEN JERÁRQUICO (todo por Venta Total desc) ===
    # 1) Proveedor: por su Venta Total acumulada (desc)
    # 2) Familia: dentro del proveedor, por su Venta Total acumulada (desc)
    # 3) Subfamilia: dentro de la familia, por su Venta Total (desc)
    ranking['_venta_proveedor'] = ranking.groupby('Proveedor')['Venta Total'].transform('sum')
    ranking['_venta_familia'] = ranking.groupby(['Proveedor', 'Familia'])['Venta Total'].transform('sum')
    ranking['_venta_subfamilia'] = ranking.groupby(
        ['Proveedor', 'Familia', 'Subfamilia']
    )['Venta Total'].transform('sum')

    ranking = ranking.sort_values(
        ['_venta_proveedor', 'Proveedor',
         '_venta_familia', 'Familia',
         '_venta_subfamilia', 'Subfamilia'],
        ascending=[False, True, False, True, False, True]
    ).drop(
        columns=['_venta_proveedor', '_venta_familia', '_venta_subfamilia']
    ).reset_index(drop=True)

    # Ranking secuencial sobre el orden jerárquico
    ranking['Ranking'] = range(1, len(ranking) + 1)

    tiempo = time.time() - inicio
    print(f"   ✅ Ranking flias/subflias procesado: {len(ranking)} filas "
          f"({ranking['Proveedor'].nunique()} proveedores) en {tiempo:.2f}s")

    return ranking

@st.cache_data(ttl=300, show_spinner=False)
def process_ranking_data_flias_subflias00(df_proveedores, df_ventas, df_presupuesto, df_familias):
    """
    Procesa y genera el ranking de proveedores desglosado por
    familia/subfamilia (CACHEADO).
    """
    print(f"\n🔧 PROCESANDO RANKING FLIAS/SUBFLIAS (sin caché)")
    inicio = time.time()

    # === VERIFICAR QUE df_familias TENGA LAS COLUMNAS ===
    print(f"   🔍 Verificando df_familias...")
    print(f"      Columnas en df_familias: {list(df_familias.columns)}")
    print(f"      Registros en df_familias: {len(df_familias):,}")

    # === LIMPIAR COLUMNAS DUPLICADAS EN df_proveedores ===
    columnas_a_eliminar = []
    if 'familia' in df_proveedores.columns:
        columnas_a_eliminar.append('familia')
    if 'subfamilia' in df_proveedores.columns:
        columnas_a_eliminar.append('subfamilia')

    if columnas_a_eliminar:
        print(f"   🧹 Eliminando columnas duplicadas de df_proveedores: {columnas_a_eliminar}")
        df_proveedores = df_proveedores.drop(columns=columnas_a_eliminar)

    # === AGREGAR FAMILIA/SUBFAMILIA desde df_familias ===
    print(f"   🔗 Agregando familia/subfamilia...")

    columnas_merge = ['idarticulo']
    if 'familia' in df_familias.columns:
        columnas_merge.append('familia')
    if 'subfamilia' in df_familias.columns:
        columnas_merge.append('subfamilia')

    print(f"      Columnas a mergear: {columnas_merge}")

    df_proveedores_completo = df_proveedores.merge(
        df_familias[columnas_merge],
        on='idarticulo',
        how='left'
    )

    print(f"   ✅ Artículos con info: {len(df_proveedores_completo):,}")
    print(f"      Columnas después del merge: {list(df_proveedores_completo.columns)}")

    # === ASEGURAR familia/subfamilia (necesarias para el desglose) ===
    if 'familia' in df_proveedores_completo.columns:
        df_proveedores_completo['familia'] = df_proveedores_completo['familia'].fillna('SIN FAMILIA')
    else:
        df_proveedores_completo['familia'] = 'SIN FAMILIA'
        print(f"   ⚠️  Columna 'familia' no encontrada -> se asigna 'SIN FAMILIA'")

    if 'subfamilia' in df_proveedores_completo.columns:
        df_proveedores_completo['subfamilia'] = df_proveedores_completo['subfamilia'].fillna('SIN SUBFAMILIA')
    else:
        df_proveedores_completo['subfamilia'] = 'SIN SUBFAMILIA'
        print(f"   ⚠️  Columna 'subfamilia' no encontrada -> se asigna 'SIN SUBFAMILIA'")

    print(f"   🏷️  Familias: {df_proveedores_completo['familia'].nunique()}")
    print(f"   📂 Subfamilias: {df_proveedores_completo['subfamilia'].nunique()}")

    # === MERGE PRINCIPAL ===
    columnas_para_merge = ['idarticulo', 'proveedor', 'idproveedor', 'familia', 'subfamilia']

    df_merge = df_proveedores_completo[columnas_para_merge].merge(
        df_ventas,
        on='idarticulo',
        how='left'
    ).merge(
        df_presupuesto[['idarticulo', 'PRESUPUESTO', 'exceso_STK', 'costo_exceso_STK', 'STK_TOTAL']],
        on='idarticulo',
        how='left'
    )

    # === FILLNA (idéntico a process_ranking_data) ===
    df_merge['venta_total'] = df_merge['venta_total'].fillna(0)
    df_merge['costo_total'] = df_merge['costo_total'].fillna(0)
    df_merge['cantidad_vendida'] = df_merge['cantidad_vendida'].fillna(0)
    df_merge['PRESUPUESTO'] = df_merge['PRESUPUESTO'].fillna(0)
    df_merge['exceso_STK'] = df_merge['exceso_STK'].fillna(0)
    df_merge['costo_exceso_STK'] = df_merge['costo_exceso_STK'].fillna(0)
    df_merge['STK_TOTAL'] = df_merge['STK_TOTAL'].fillna(0)

    # === AGREGACIÓN POR proveedor + idproveedor + familia + subfamilia ===
    ranking = df_merge.groupby(
        ['proveedor', 'idproveedor', 'familia', 'subfamilia']
    ).agg({
        'venta_total': 'sum',
        'costo_total': 'sum',
        'cantidad_vendida': 'sum',
        'idarticulo': 'count',
        'PRESUPUESTO': 'sum',
        'exceso_STK': lambda x: (x > 0).sum(),
        'costo_exceso_STK': 'sum',
        'STK_TOTAL': lambda x: (x == 0).sum()
    }).reset_index()

    # ✅ RENOMBRAR COLUMNAS (compatible con global_dashboard.py + Familia/Subfamilia)
    ranking.columns = [
        'Proveedor', 'ID Proveedor', 'Familia', 'Subfamilia',
        'Venta Total', 'Costo Total', 'Cantidad Vendida', 'Artículos',
        'Presupuesto', 'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
    ]

    # === CÁLCULOS ADICIONALES (mismas métricas; % sobre total general) ===
    ranking['Utilidad'] = (ranking['Venta Total'] - ranking['Costo Total']).round(0).astype(int)

    # Misma fórmula que la original, con protección /0 (el desglose genera
    # filas con Venta Total = 0 que producirían inf).
    ranking['Rentabilidad %'] = (
        (ranking['Utilidad'] / ranking['Venta Total'].replace(0, np.nan)) * 100
    ).round(2).fillna(0)

    ranking['% Participación Presupuesto'] = (ranking['Presupuesto'] / ranking['Presupuesto'].sum() * 100).round(2)
    ranking['% Participación Ventas'] = (ranking['Venta Total'] / ranking['Venta Total'].sum() * 100).round(2)
    ranking['% Participación Utilidad'] = (ranking['Utilidad'] / ranking['Utilidad'].sum() * 100).round(2)

    # === ORDEN JERÁRQUICO ===
    # 1) Proveedores por su Venta Total acumulada (desc)
    # 2) Dentro de cada proveedor, familia/subfamilia por Venta Total (desc)
    ranking['_venta_proveedor'] = ranking.groupby('Proveedor')['Venta Total'].transform('sum')
    ranking = ranking.sort_values(
        ['_venta_proveedor', 'Proveedor', 'Venta Total'],
        ascending=[False, True, False]
    ).drop(columns='_venta_proveedor').reset_index(drop=True)

    # Ranking secuencial sobre el orden jerárquico
    ranking['Ranking'] = range(1, len(ranking) + 1)

    tiempo = time.time() - inicio
    print(f"   ✅ Ranking flias/subflias procesado: {len(ranking)} filas "
          f"({ranking['Proveedor'].nunique()} proveedores) en {tiempo:.2f}s")

    return ranking

# ============================================================================
# ============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def process_ranking_data(df_proveedores, df_ventas, df_presupuesto, df_familias):
    """
    Procesa y genera el ranking (CACHEADO)
    """
    print(f"\n🔧 PROCESANDO RANKING (sin caché)")
    import time
    inicio = time.time()

    # === VERIFICAR QUE df_familias TENGA LAS COLUMNAS ===
    print(f"   🔍 Verificando df_familias...")
    print(f"      Columnas en df_familias: {list(df_familias.columns)}")
    print(f"      Registros en df_familias: {len(df_familias):,}")

    # === LIMPIAR COLUMNAS DUPLICADAS EN df_proveedores ===
    columnas_a_eliminar = []
    if 'familia' in df_proveedores.columns:
        columnas_a_eliminar.append('familia')
    if 'subfamilia' in df_proveedores.columns:
        columnas_a_eliminar.append('subfamilia')
    
    if columnas_a_eliminar:
        print(f"   🧹 Eliminando columnas duplicadas de df_proveedores: {columnas_a_eliminar}")
        df_proveedores = df_proveedores.drop(columns=columnas_a_eliminar)

    # === AGREGAR FAMILIA/SUBFAMILIA desde df_familias ===
    print(f"   🔗 Agregando familia/subfamilia...")
    
    # Verificar qué columnas están disponibles
    columnas_merge = ['idarticulo']
    if 'familia' in df_familias.columns:
        columnas_merge.append('familia')
    if 'subfamilia' in df_familias.columns:
        columnas_merge.append('subfamilia')

    print(f"      Columnas a mergear: {columnas_merge}")

    # Hacer merge solo con las columnas que existen
    df_proveedores_completo = df_proveedores.merge(
        df_familias[columnas_merge],
        on='idarticulo',
        how='left'
    )

    print(f"   ✅ Artículos con info: {len(df_proveedores_completo):,}")
    print(f"      Columnas después del merge: {list(df_proveedores_completo.columns)}")

    # Prints condicionales
    if 'familia' in df_proveedores_completo.columns:
        print(f"   🏷️  Familias: {df_proveedores_completo['familia'].nunique()}")
    else:
        print(f"   ⚠️  Columna 'familia' no encontrada después del merge")

    if 'subfamilia' in df_proveedores_completo.columns:
        print(f"   📂 Subfamilias: {df_proveedores_completo['subfamilia'].nunique()}")
    else:
        print(f"   ⚠️  Columna 'subfamilia' no encontrada después del merge")

    # === MERGE PRINCIPAL ===
    # Preparar columnas para el merge (solo las que existen)
    columnas_para_merge = ['idarticulo', 'proveedor', 'idproveedor']
    if 'familia' in df_proveedores_completo.columns:
        columnas_para_merge.append('familia')
    if 'subfamilia' in df_proveedores_completo.columns:
        columnas_para_merge.append('subfamilia')

    df_merge = df_proveedores_completo[columnas_para_merge].merge(
        df_ventas,
        on='idarticulo',
        how='left'
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

    # ✅ RENOMBRAR COLUMNAS (necesario para global_dashboard.py)
    ranking.columns = [
        'Proveedor', 'ID Proveedor', 'Venta Total', 'Costo Total',
        'Cantidad Vendida', 'Artículos', 'Presupuesto',
        'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
    ]

    # Cálculos adicionales
    ranking['Utilidad'] = (ranking['Venta Total'] - ranking['Costo Total']).round(0).astype(int)
    ranking['Rentabilidad %'] = ((ranking['Utilidad'] / ranking['Venta Total']) * 100).round(2)
    ranking['% Participación Presupuesto'] = (ranking['Presupuesto'] / ranking['Presupuesto'].sum() * 100).round(2)
    ranking['% Participación Ventas'] = (ranking['Venta Total'] / ranking['Venta Total'].sum() * 100).round(2)
    ranking['% Participación Utilidad'] = (ranking['Utilidad'] / ranking['Utilidad'].sum() * 100).round(2)

    ranking = ranking.sort_values('Venta Total', ascending=False).reset_index(drop=True)
    ranking['Ranking'] = range(1, len(ranking) + 1)

    tiempo = time.time() - inicio
    print(f"   ✅ Ranking procesado: {len(ranking)} proveedores en {tiempo:.2f}s")

    return ranking

@st.cache_data(ttl=300, show_spinner=False)
def process_ranking_data00(df_proveedores, df_ventas, df_presupuesto, df_familias):
    """
    Procesa y genera el ranking (CACHEADO)
    """
    print(f"\n🔧 PROCESANDO RANKING (sin caché)")
    import time
    
    inicio = time.time()
    
    # === VERIFICAR QUE df_familias TENGA LAS COLUMNAS ===
    print(f"   🔍 Verificando df_familias...")
    print(f"      Columnas en df_familias: {list(df_familias.columns)}")
    print(f"      Registros en df_familias: {len(df_familias):,}")
    
    # === AGREGAR FAMILIA/SUBFAMILIA desde df_familias ===
    print(f"   🔗 Agregando familia/subfamilia...")
    
    # Verificar qué columnas están disponibles
    columnas_merge = ['idarticulo']
    if 'familia' in df_familias.columns:
        columnas_merge.append('familia')
    if 'subfamilia' in df_familias.columns:
        columnas_merge.append('subfamilia')
    
    print(f"      Columnas a mergear: {columnas_merge}")
    
    # Hacer merge solo con las columnas que existen
    df_proveedores_completo = df_proveedores.merge(
        df_familias[columnas_merge],
        on='idarticulo',
        how='left'
    )
    
    print(f"   ✅ Artículos con info: {len(df_proveedores_completo):,}")
    print(f"      Columnas después del merge: {list(df_proveedores_completo.columns)}")
    
    # Prints condicionales
    if 'familia' in df_proveedores_completo.columns:
        print(f"   🏷️  Familias: {df_proveedores_completo['familia'].nunique()}")
    else:
        print(f"   ⚠️  Columna 'familia' no encontrada después del merge")
    
    if 'subfamilia' in df_proveedores_completo.columns:
        print(f"   📂 Subfamilias: {df_proveedores_completo['subfamilia'].nunique()}")
    else:
        print(f"   ⚠️  Columna 'subfamilia' no encontrada después del merge")
    
    # === MERGE PRINCIPAL ===
    # Preparar columnas para el merge (solo las que existen)
    columnas_para_merge = ['idarticulo', 'proveedor', 'idproveedor']
    if 'familia' in df_proveedores_completo.columns:
        columnas_para_merge.append('familia')
    if 'subfamilia' in df_proveedores_completo.columns:
        columnas_para_merge.append('subfamilia')
    
    df_merge = df_proveedores_completo[columnas_para_merge].merge(
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
    
    # ✅ RENOMBRAR COLUMNAS (necesario para global_dashboard.py)
    ranking.columns = [
        'Proveedor', 'ID Proveedor', 'Venta Total', 'Costo Total', 'Cantidad Vendida', 
        'Artículos', 'Presupuesto', 'Art. con Exceso', 
        'Costo Exceso', 'Art. Sin Stock'
    ]
    
    # Cálculos adicionales
    ranking['Utilidad'] = (ranking['Venta Total'] - ranking['Costo Total']).round(0).astype(int)
    ranking['Rentabilidad %'] = ((ranking['Utilidad'] / ranking['Venta Total']) * 100).round(2)
    ranking['% Participación Presupuesto'] = (ranking['Presupuesto'] / ranking['Presupuesto'].sum() * 100).round(2)
    ranking['% Participación Ventas'] = (ranking['Venta Total'] / ranking['Venta Total'].sum() * 100).round(2)
    ranking['% Participación Utilidad'] = (ranking['Utilidad'] / ranking['Utilidad'].sum() * 100).round(2)
    ranking = ranking.sort_values('Venta Total', ascending=False).reset_index(drop=True)
    ranking['Ranking'] = range(1, len(ranking) + 1)
    
    tiempo = time.time() - inicio
    print(f"✅ Ranking procesado: {len(ranking)} proveedores en {tiempo:.2f}s")
    print("@"*200)
    print("Columnas del RANKING:", list(ranking.columns))
    print("Columnas del RANKING:", ranking.head(5))
    print("@"*200)
    return ranking

"""
═══════════════════════════════════════════════════════════════════════════════
    FUNCIÓN ANTIGUA - AHORA OBSOLETA (mantener por compatibilidad)
    Reemplazada por get_ventas_agregadas_stock() para análisis sin filtros
═══════════════════════════════════════════════════════════════════════════════
"""

@st.cache_data(ttl=3600)
def get_ventas_agregadas_filtradas(credentials_path, project_id, bigquery_table, año, margen_min=0.25, dias_min=270):
    """
    ⚠️ FUNCIÓN ANTIGUA - Reemplazada por get_ventas_agregadas_stock()
    
    Obtiene ventas agregadas CON FILTROS aplicados
    Mantener por compatibilidad con código legacy
    """
    import os
    import time
    from google.cloud import bigquery
    import streamlit as st
    
    print(f"\n{'='*80}")
    print(f"⚠️  USANDO FUNCIÓN ANTIGUA: get_ventas_agregadas_filtradas()")
    print(f"{'='*80}")
    print(f"   • Año: {año}")
    print(f"   • Margen mín: {margen_min*100:.1f}%")
    print(f"   • Días mín: {dias_min}")
    
    inicio = time.time()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONECTAR A BIGQUERY (detectar ambiente)
    # ═══════════════════════════════════════════════════════════════════════════
    
    is_cloud = not os.path.exists(credentials_path) if credentials_path else True
    
    if is_cloud:
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        client = bigquery.Client(credentials=credentials, project=project_id)
        print(f"   🌐 Ambiente: Streamlit Cloud")
    else:
        client = bigquery.Client.from_service_account_json(credentials_path, project=project_id)
        print(f"   💻 Ambiente: Local")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUERY AGREGADA (con PARSE_DATE para convertir STRING a DATE)
    # ═══════════════════════════════════════════════════════════════════════════
    
    query = f"""
    WITH ventas_agregadas AS (
      SELECT 
        idarticulo,
        idartalfa,
        MAX(descripcion) as descripcion,
        MAX(familia) as familia,
        MAX(subfamilia) as subfamilia,
        
        -- ═══ MÉTRICAS ANUALES ═══
        SUM(cantidad_total) as cantidad_total_anual,
        SUM(precio_total) as precio_total_anual,
        SUM(costo_total) as costo_total_anual,
        
        -- ═══ Q1: ENERO-MARZO ═══
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 1 THEN cantidad_total ELSE 0 END) as cantidad_q1,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 1 THEN precio_total ELSE 0 END) as venta_q1,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 1 THEN costo_total ELSE 0 END) as costo_q1,
        
        -- ═══ Q2: ABRIL-JUNIO ═══
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 2 THEN cantidad_total ELSE 0 END) as cantidad_q2,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 2 THEN precio_total ELSE 0 END) as venta_q2,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 2 THEN costo_total ELSE 0 END) as costo_q2,
        
        -- ═══ Q3: JULIO-SEPTIEMBRE ═══
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 3 THEN cantidad_total ELSE 0 END) as cantidad_q3,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 3 THEN precio_total ELSE 0 END) as venta_q3,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 3 THEN costo_total ELSE 0 END) as costo_q3,
        
        -- ═══ Q4: OCTUBRE-DICIEMBRE ═══
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 4 THEN cantidad_total ELSE 0 END) as cantidad_q4,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 4 THEN precio_total ELSE 0 END) as venta_q4,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 4 THEN costo_total ELSE 0 END) as costo_q4,
        
        -- ═══ FECHAS Y ACTIVIDAD ═══
        MIN(PARSE_DATE('%Y-%m-%d', fecha_comprobante)) as fecha_primera_venta,
        MAX(PARSE_DATE('%Y-%m-%d', fecha_comprobante)) as fecha_ultima_venta,
        COUNT(DISTINCT PARSE_DATE('%Y-%m-%d', fecha_comprobante)) as dias_con_ventas
        
      FROM `{project_id}.{bigquery_table}`
      WHERE EXTRACT(YEAR FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = {año}
      GROUP BY idarticulo, idartalfa
    ),
    
    ventas_con_metricas AS (
      SELECT 
        *,
        -- Calcular días activo
        DATE_DIFF(fecha_ultima_venta, fecha_primera_venta, DAY) + 1 as dias_activo,
        
        -- Calcular margen anual
        SAFE_DIVIDE(precio_total_anual - costo_total_anual, precio_total_anual) as margen_anual,
        
        -- Calcular utilidad anual
        precio_total_anual - costo_total_anual as utilidad_anual,
        
        -- Calcular velocidad de venta diaria
        SAFE_DIVIDE(cantidad_total_anual, 
          DATE_DIFF(fecha_ultima_venta, fecha_primera_venta, DAY) + 1
        ) as velocidad_venta_diaria
        
      FROM ventas_agregadas
    )
    
    SELECT *
    FROM ventas_con_metricas
    WHERE margen_anual >= {margen_min}
      AND dias_activo >= {dias_min}
    ORDER BY utilidad_anual DESC
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EJECUTAR QUERY
    # ═══════════════════════════════════════════════════════════════════════════
    
    try:
        df = client.query(query).to_dataframe()
        tiempo = time.time() - inicio
        
        print(f"   ✅ Datos cargados: {len(df):,} artículos")
        print(f"   ⏱️  Tiempo: {tiempo:.2f}s")
        print(f"   💰 Venta total: ${df['precio_total_anual'].sum():,.0f}")
        print(f"   💵 Utilidad total: ${df['utilidad_anual'].sum():,.0f}")
        print(f"{'='*80}\n")
        
        return df
        
    except Exception as e:
        print(f"   ❌ Error ejecutando query: {str(e)}")
        print(f"{'='*80}\n")
        return None
    
"""
═══════════════════════════════════════════════════════════════════════════════
    FUNCIÓN NUEVA - REEMPLAZA A get_ventas_agregadas_filtradas()
    Cargar ventas agregadas SIN FILTROS para permitir filtrado dinámico
    ✅ INCLUYE NORMALIZACIÓN DE FAMILIA/SUBFAMILIA
═══════════════════════════════════════════════════════════════════════════════
"""

@st.cache_data(ttl=3600)
def get_ventas_agregadas_stock(credentials_path, project_id, bigquery_table, año):
    """
    Obtiene ventas agregadas por artículo con datos por trimestre
    SIN FILTROS - Trae todos los artículos para permitir filtrado dinámico
    ✅ INCLUYE NORMALIZACIÓN: familia, subfamilia en UPPER y sin espacios
    
    Args:
        credentials_path: Ruta a credenciales JSON (None en cloud)
        project_id: ID del proyecto de GCP
        bigquery_table: Nombre de la tabla (formato: dataset.tabla)
        año: Año a analizar (ej: 2024)
    
    Returns:
        DataFrame con columnas:
        - idarticulo, idartalfa, descripcion, familia, subfamilia (NORMALIZADAS)
        - cantidad_total_anual, precio_total_anual, costo_total_anual
        - cantidad_q1, venta_q1, costo_q1 (y Q2, Q3, Q4)
        - margen_anual, utilidad_anual, velocidad_venta_diaria
        - dias_activo, fecha_primera_venta, fecha_ultima_venta
    """
    import os
    import time
    from google.cloud import bigquery
    import streamlit as st
    
    print(f"\n{'='*80}")
    print(f"📊 CARGANDO VENTAS AGREGADAS PARA ANÁLISIS DE STOCK")
    print(f"{'='*80}")
    print(f"   • Año: {año}")
    print(f"   • Sin filtros - Permite filtrado dinámico por usuario")
    print(f"   • ✅ CON NORMALIZACIÓN: familia/subfamilia UPPER + sin espacios")
    
    inicio = time.time()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONECTAR A BIGQUERY (detectar ambiente)
    # ═══════════════════════════════════════════════════════════════════════════
    
    is_cloud = not os.path.exists(credentials_path) if credentials_path else True
    
    if is_cloud:
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        client = bigquery.Client(credentials=credentials, project=project_id)
        print(f"   🌐 Ambiente: Streamlit Cloud")
    else:
        client = bigquery.Client.from_service_account_json(credentials_path, project=project_id)
        print(f"   💻 Ambiente: Local")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUERY AGREGADA CON NORMALIZACIÓN EN BIGQUERY
    # ✅ TRIM() + UPPER() aplicado directamente en la query
    # ═══════════════════════════════════════════════════════════════════════════
    
    query = f"""
    WITH ventas_agregadas AS (
      SELECT 
        idarticulo,
        idartalfa,
        MAX(descripcion) as descripcion,
        -- ✅ NORMALIZACIÓN: TRIM + UPPER
        UPPER(TRIM(MAX(familia))) as familia,
        UPPER(TRIM(MAX(subfamilia))) as subfamilia,
        
        -- ═══ MÉTRICAS ANUALES ═══
        SUM(cantidad_total) as cantidad_total_anual,
        SUM(precio_total) as precio_total_anual,
        SUM(costo_total) as costo_total_anual,
        
        -- ═══ Q1: ENERO-MARZO ═══
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 1 THEN cantidad_total ELSE 0 END) as cantidad_q1,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 1 THEN precio_total ELSE 0 END) as venta_q1,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 1 THEN costo_total ELSE 0 END) as costo_q1,
        
        -- ═══ Q2: ABRIL-JUNIO ═══
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 2 THEN cantidad_total ELSE 0 END) as cantidad_q2,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 2 THEN precio_total ELSE 0 END) as venta_q2,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 2 THEN costo_total ELSE 0 END) as costo_q2,
        
        -- ═══ Q3: JULIO-SEPTIEMBRE ═══
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 3 THEN cantidad_total ELSE 0 END) as cantidad_q3,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 3 THEN precio_total ELSE 0 END) as venta_q3,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 3 THEN costo_total ELSE 0 END) as costo_q3,
        
        -- ═══ Q4: OCTUBRE-DICIEMBRE ═══
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 4 THEN cantidad_total ELSE 0 END) as cantidad_q4,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 4 THEN precio_total ELSE 0 END) as venta_q4,
        SUM(CASE WHEN EXTRACT(QUARTER FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = 4 THEN costo_total ELSE 0 END) as costo_q4,
        
        -- ═══ FECHAS Y ACTIVIDAD ═══
        MIN(PARSE_DATE('%Y-%m-%d', fecha_comprobante)) as fecha_primera_venta,
        MAX(PARSE_DATE('%Y-%m-%d', fecha_comprobante)) as fecha_ultima_venta,
        COUNT(DISTINCT PARSE_DATE('%Y-%m-%d', fecha_comprobante)) as dias_con_ventas
        
      FROM `{project_id}.{bigquery_table}`
      WHERE EXTRACT(YEAR FROM PARSE_DATE('%Y-%m-%d', fecha_comprobante)) = {año}
      GROUP BY idarticulo, idartalfa
    ),
    
    ventas_con_metricas AS (
      SELECT 
        *,
        -- Calcular días activo
        DATE_DIFF(fecha_ultima_venta, fecha_primera_venta, DAY) + 1 as dias_activo,
        
        -- Calcular margen anual
        SAFE_DIVIDE(precio_total_anual - costo_total_anual, precio_total_anual) as margen_anual,
        
        -- Calcular utilidad anual
        precio_total_anual - costo_total_anual as utilidad_anual,
        
        -- Calcular velocidad de venta diaria
        SAFE_DIVIDE(cantidad_total_anual, 
          DATE_DIFF(fecha_ultima_venta, fecha_primera_venta, DAY) + 1
        ) as velocidad_venta_diaria
        
      FROM ventas_agregadas
    )
    
    SELECT *
    FROM ventas_con_metricas
    ORDER BY utilidad_anual DESC
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EJECUTAR QUERY
    # ═══════════════════════════════════════════════════════════════════════════
    
    try:
        df = client.query(query).to_dataframe()
        tiempo = time.time() - inicio
        
        print(f"   ✅ Datos cargados: {len(df):,} artículos")
        print(f"   ⏱️  Tiempo: {tiempo:.2f}s")
        print(f"   💰 Venta total: ${df['precio_total_anual'].sum():,.0f}")
        print(f"   💵 Utilidad total: ${df['utilidad_anual'].sum():,.0f}")
        
        # Verificar normalización
        if 'familia' in df.columns:
            print(f"   ✅ Familias normalizadas: {df['familia'].nunique()} únicas")
        if 'subfamilia' in df.columns:
            print(f"   ✅ Subfamilias normalizadas: {df['subfamilia'].nunique()} únicas")
        
        print(f"{'='*80}\n")
        
        return df
        
    except Exception as e:
        print(f"   ❌ Error ejecutando query: {str(e)}")
        print(f"{'='*80}\n")
        return None
    

# ============================================================================
# AGREGAR ESTA FUNCIÓN EN global_dashboard_cache.py
# ============================================================================

# ============================================================================
# CORRECCIÓN EN process_ranking_detallado_alimentos
# ============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def process_ranking_detallado_alimentos00(df_proveedores, df_ventas, df_presupuesto, df_familias):
    """
    Procesa y genera el ranking DETALLADO por artículo (solo familia 'Alimentos')
    """
    print(f"\n🔧 PROCESANDO RANKING DETALLADO ALIMENTOS (sin caché)")
    import time
    inicio = time.time()
    
    # === LIMPIAR COLUMNAS DUPLICADAS EN df_proveedores ===
    columnas_a_eliminar = []
    if 'familia' in df_proveedores.columns:
        columnas_a_eliminar.append('familia')
    if 'subfamilia' in df_proveedores.columns:
        columnas_a_eliminar.append('subfamilia')
    if 'descripcion' in df_proveedores.columns:
        columnas_a_eliminar.append('descripcion')
    
    if columnas_a_eliminar:
        print(f"   🧹 Eliminando columnas duplicadas de df_proveedores: {columnas_a_eliminar}")
        df_proveedores = df_proveedores.drop(columns=columnas_a_eliminar)
    
    # === VERIFICAR QUE df_familias TENGA LAS COLUMNAS ===
    print(f"   🔍 Verificando df_familias...")
    columnas_merge = ['idarticulo']
    if 'familia' in df_familias.columns:
        columnas_merge.append('familia')
    if 'subfamilia' in df_familias.columns:
        columnas_merge.append('subfamilia')
    if 'descripcion' in df_familias.columns:
        columnas_merge.append('descripcion')
    
    # === AGREGAR FAMILIA/SUBFAMILIA/DESCRIPCION ===
    df_proveedores_completo = df_proveedores.merge(
        df_familias[columnas_merge],
        on='idarticulo',
        how='left'
    )
    
    # === FILTRAR SOLO FAMILIA = 'Alimentos' ===
    if 'familia' not in df_proveedores_completo.columns:
        print(f"   ⚠️ No se encontró columna 'familia', retornando DataFrame vacío")
        return pd.DataFrame()
    
    # Mostrar familias disponibles
    print(f"   📊 Familias disponibles: {df_proveedores_completo['familia'].unique()}")
    
    # Filtro case-insensitive
    df_proveedores_completo = df_proveedores_completo[
        df_proveedores_completo['familia'].str.strip().str.lower() == 'alimentos'
    ].copy()
    
    print(f"   ✅ Artículos de Alimentos: {len(df_proveedores_completo):,}")
    
    if len(df_proveedores_completo) == 0:
        print(f"   ⚠️ NO SE ENCONTRARON ARTÍCULOS DE 'Alimentos'")
        return pd.DataFrame()
        
    # === MERGE COMPLETO (DETALLE POR ARTÍCULO) ===
    columnas_para_merge = ['idarticulo', 'proveedor', 'idproveedor', 'familia']
    if 'subfamilia' in df_proveedores_completo.columns:
        columnas_para_merge.append('subfamilia')
    if 'descripcion' in df_proveedores_completo.columns:
        columnas_para_merge.append('descripcion')
    
    df_detalle = df_proveedores_completo[columnas_para_merge].merge(
        df_ventas,
        on='idarticulo',
        how='left'
        # how='left'
    ).merge(
        df_presupuesto[['idarticulo', 'PRESUPUESTO', 'exceso_STK', 'costo_exceso_STK', 'STK_TOTAL']],
        on='idarticulo',
        how='left'
    )
    
    # Fillna
    df_detalle['venta_total'] = df_detalle['venta_total'].fillna(0)
    df_detalle['costo_total'] = df_detalle['costo_total'].fillna(0)
    df_detalle['cantidad_vendida'] = df_detalle['cantidad_vendida'].fillna(0)
    df_detalle['PRESUPUESTO'] = df_detalle['PRESUPUESTO'].fillna(0)
    df_detalle['exceso_STK'] = df_detalle['exceso_STK'].fillna(0)
    df_detalle['costo_exceso_STK'] = df_detalle['costo_exceso_STK'].fillna(0)
    df_detalle['STK_TOTAL'] = df_detalle['STK_TOTAL'].fillna(0)
    
    # === CALCULAR TOTALES POR PROVEEDOR (AGREGADOS) ===
    ranking_proveedores = df_detalle.groupby(['proveedor', 'idproveedor']).agg({
        'venta_total': 'sum',
        'costo_total': 'sum',
        'cantidad_vendida': 'sum',
        'idarticulo': 'count',
        'PRESUPUESTO': 'sum',
        'exceso_STK': lambda x: (x > 0).sum(),
        'costo_exceso_STK': 'sum',
        'STK_TOTAL': lambda x: (x == 0).sum()
    }).reset_index()
    
    ranking_proveedores.columns = [
        'Proveedor', 'ID Proveedor', 'Venta Total Proveedor', 'Costo Total Proveedor',
        'Cantidad Vendida Proveedor', 'Artículos Proveedor', 'Presupuesto Proveedor',
        'Art. con Exceso Proveedor', 'Costo Exceso Proveedor', 'Art. Sin Stock Proveedor'
    ]
    
    # Cálculos proveedor
    ranking_proveedores['Utilidad Proveedor'] = (
        ranking_proveedores['Venta Total Proveedor'] - ranking_proveedores['Costo Total Proveedor']
    ).round(0).astype(int)
    
    ranking_proveedores['Rentabilidad % Proveedor'] = (
        (ranking_proveedores['Utilidad Proveedor'] / ranking_proveedores['Venta Total Proveedor']) * 100
    ).round(2)
    
    ranking_proveedores['% Participación Ventas'] = (
        ranking_proveedores['Venta Total Proveedor'] / ranking_proveedores['Venta Total Proveedor'].sum() * 100
    ).round(2)
    
    ranking_proveedores['% Participación Presupuesto'] = (
        ranking_proveedores['Presupuesto Proveedor'] / ranking_proveedores['Presupuesto Proveedor'].sum() * 100
    ).round(2)
    
    ranking_proveedores = ranking_proveedores.sort_values('Venta Total Proveedor', ascending=False).reset_index(drop=True)
    ranking_proveedores['Ranking'] = range(1, len(ranking_proveedores) + 1)
    
    # === MERGE: DETALLE ARTÍCULOS + TOTALES PROVEEDOR ===
    df_final = df_detalle.merge(
        ranking_proveedores,
        left_on=['proveedor', 'idproveedor'],
        right_on=['Proveedor', 'ID Proveedor'],
        how='left'
    )
    
    # === CALCULAR MÉTRICAS INDIVIDUALES DEL ARTÍCULO ===
    # df_final['Utilidad Artículo'] = (df_final['venta_total'] - df_final['costo_total']).round(0).astype(int)
    # df_final['Rentabilidad % Artículo'] = (
    #     (df_final['Utilidad Artículo'] / df_final['venta_total']) * 100
    # ).round(2)
    # df_final['Tiene Exceso'] = (df_final['exceso_STK'] > 0).map({True: 'Sí', False: 'No'})
    # df_final['Sin Stock'] = (df_final['STK_TOTAL'] == 0).map({True: 'Sí', False: 'No'})
    # === CALCULAR MÉTRICAS INDIVIDUALES DEL ARTÍCULO ===
    df_final['Utilidad Artículo'] = (df_final['venta_total'] - df_final['costo_total']).round(0).astype(int)
    df_final['Rentabilidad % Artículo'] = (
        (df_final['Utilidad Artículo'] / df_final['venta_total']) * 100
    ).round(2)
    df_final['Tiene Exceso'] = (df_final['exceso_STK'] > 0).map({True: 'Sí', False: 'No'})
    df_final['Stock Actual'] = df_final['STK_TOTAL'].fillna(0).astype(int)  # ← CAMBIADO
    df_final['Sin Stock'] = (df_final['STK_TOTAL'] == 0).map({True: 'Sí', False: 'No'})

    # === RENOMBRAR COLUMNAS DE ARTÍCULO ===
    df_final = df_final.rename(columns={
        'venta_total': 'Venta Artículo',
        'costo_total': 'Costo Artículo',
        'cantidad_vendida': 'Cantidad Vendida',
        'PRESUPUESTO': 'Presupuesto Artículo',
        'costo_exceso_STK': 'Costo Exceso Artículo',
        'descripcion': 'Descripción',
        'subfamilia': 'Subfamilia'
    })
    
    # === SELECCIONAR Y ORDENAR COLUMNAS FINALES ===
    columnas_finales_renamed = [
        'Ranking', 'ID Proveedor', 'Proveedor', '% Participación Ventas',
        'Venta Total Proveedor', 'Costo Total Proveedor', 'Utilidad Proveedor',
        'Rentabilidad % Proveedor', '% Participación Presupuesto', 'Presupuesto Proveedor',
        'Artículos Proveedor', 'Art. con Exceso Proveedor', 'Costo Exceso Proveedor',
        'Art. Sin Stock Proveedor', 'idarticulo'
    ]
    
    if 'Descripción' in df_final.columns:
        columnas_finales_renamed.append('Descripción')
    if 'Subfamilia' in df_final.columns:
        columnas_finales_renamed.append('Subfamilia')
    
    columnas_finales_renamed.extend([
        'Venta Artículo', 'Costo Artículo', 'Cantidad Vendida',
        'Utilidad Artículo', 'Rentabilidad % Artículo', 'Presupuesto Artículo',
        'Tiene Exceso', 'Costo Exceso Artículo', 'Stock Actual', 'Sin Stock'
    ])
    
    df_final = df_final[columnas_finales_renamed]
    
    # Ordenar por Ranking y luego por Venta Artículo descendente
    df_final = df_final.sort_values(
        ['Ranking', 'Venta Artículo'],
        ascending=[True, False]
    ).reset_index(drop=True)
    
    tiempo = time.time() - inicio
    print(f"   ✅ Ranking detallado procesado: {len(df_final):,} artículos en {tiempo:.2f}s")
    print(f"   📊 Proveedores únicos: {df_final['Proveedor'].nunique()}")
    print(f"   💰 Venta total: ${df_final['Venta Artículo'].sum():,.0f}")
    
    return df_final

@st.cache_data(ttl=300, show_spinner=False)
def process_ranking_detallado_alimentos(df_proveedores, df_ventas, df_presupuesto, df_familias):
    """
    Procesa y genera el ranking DETALLADO por artículo (cualquier familia)
    """
    print(f"\n🔧 PROCESANDO RANKING DETALLADO (sin caché)")
    import time
    inicio = time.time()
    
    # === LIMPIAR COLUMNAS DUPLICADAS EN df_proveedores ===
    columnas_a_eliminar = []
    if 'familia' in df_proveedores.columns:
        columnas_a_eliminar.append('familia')
    if 'subfamilia' in df_proveedores.columns:
        columnas_a_eliminar.append('subfamilia')
    if 'descripcion' in df_proveedores.columns:
        columnas_a_eliminar.append('descripcion')
    
    if columnas_a_eliminar:
        print(f"   🧹 Eliminando columnas duplicadas de df_proveedores: {columnas_a_eliminar}")
        df_proveedores = df_proveedores.drop(columns=columnas_a_eliminar)
    
    # === VERIFICAR COLUMNAS EN DATAFRAMES ===
    print(f"   🔍 Verificando columnas disponibles...")
    print(f"      df_familias: {list(df_familias.columns)}")
    print(f"      df_ventas: {list(df_ventas.columns)}")
    print(f"      df_presupuesto: {list(df_presupuesto.columns)}")
    
    # === AGREGAR FAMILIA/SUBFAMILIA desde df_familias ===
    columnas_merge = ['idarticulo']
    if 'familia' in df_familias.columns:
        columnas_merge.append('familia')
    if 'subfamilia' in df_familias.columns:
        columnas_merge.append('subfamilia')
    
    df_proveedores_completo = df_proveedores.merge(
        df_familias[columnas_merge],
        on='idarticulo',
        how='left'
    )
    
    # === NOTA: EL FILTRADO POR FAMILIA YA SE HIZO ANTES ===
    # df_proveedores ya viene filtrado por la familia seleccionada
    # NO necesitamos filtrar internamente aquí
    
    print(f"   📊 Artículos a procesar: {len(df_proveedores_completo):,}")
    
    if len(df_proveedores_completo) == 0:
        print(f"   ⚠️ NO SE ENCONTRARON ARTÍCULOS")
        return pd.DataFrame()
    
    # === MERGE COMPLETO (DETALLE POR ARTÍCULO) ===
    columnas_para_merge = ['idarticulo', 'proveedor', 'idproveedor', 'familia']
    if 'subfamilia' in df_proveedores_completo.columns:
        columnas_para_merge.append('subfamilia')
    
    # MERGE CON df_ventas (incluye descripcion si está presente)
    df_detalle = df_proveedores_completo[columnas_para_merge].merge(
        df_ventas,
        on='idarticulo',
        how='inner'
    )
    
    # MERGE CON df_presupuesto (evitar duplicar descripcion si ya existe)
    columnas_presupuesto = ['idarticulo', 'PRESUPUESTO', 'exceso_STK', 'costo_exceso_STK', 'STK_TOTAL']
    
    # Si descripcion no vino de df_ventas pero está en df_presupuesto, incluirla
    # if 'descripcion' not in df_detalle.columns and 'descripcion' in df_presupuesto.columns:
    #     columnas_presupuesto.append('descripcion')
    
    df_detalle = df_detalle.merge(
        df_presupuesto[columnas_presupuesto],
        on='idarticulo',
        how='left'
    )
    
    print(f"   📋 Columnas después de merges: {list(df_detalle.columns)}")
    
    # Fillna
    df_detalle['venta_total'] = df_detalle['venta_total'].fillna(0)
    df_detalle['costo_total'] = df_detalle['costo_total'].fillna(0)
    df_detalle['cantidad_vendida'] = df_detalle['cantidad_vendida'].fillna(0)
    df_detalle['PRESUPUESTO'] = df_detalle['PRESUPUESTO'].fillna(0)
    df_detalle['exceso_STK'] = df_detalle['exceso_STK'].fillna(0)
    df_detalle['costo_exceso_STK'] = df_detalle['costo_exceso_STK'].fillna(0)
    df_detalle['STK_TOTAL'] = df_detalle['STK_TOTAL'].fillna(0)
    
    # === CALCULAR TOTALES POR PROVEEDOR (AGREGADOS) ===
    ranking_proveedores = df_detalle.groupby(['proveedor', 'idproveedor']).agg({
        'venta_total': 'sum',
        'costo_total': 'sum',
        'cantidad_vendida': 'sum',
        'idarticulo': 'count',
        'PRESUPUESTO': 'sum',
        'exceso_STK': lambda x: (x > 0).sum(),
        'costo_exceso_STK': 'sum',
        'STK_TOTAL': lambda x: (x == 0).sum()
    }).reset_index()
    
    ranking_proveedores.columns = [
        'Proveedor', 'ID Proveedor', 'Venta Total Proveedor', 'Costo Total Proveedor',
        'Cantidad Vendida Proveedor', 'Artículos Proveedor', 'Presupuesto Proveedor',
        'Art. con Exceso Proveedor', 'Costo Exceso Proveedor', 'Art. Sin Stock Proveedor'
    ]
    
    # Cálculos proveedor
    ranking_proveedores['Utilidad Proveedor'] = (
        ranking_proveedores['Venta Total Proveedor'] - ranking_proveedores['Costo Total Proveedor']
    ).round(0).astype(int)
    
    ranking_proveedores['Rentabilidad % Proveedor'] = (
        (ranking_proveedores['Utilidad Proveedor'] / ranking_proveedores['Venta Total Proveedor']) * 100
    ).round(2)
    
    ranking_proveedores['% Participación Ventas'] = (
        ranking_proveedores['Venta Total Proveedor'] / ranking_proveedores['Venta Total Proveedor'].sum() * 100
    ).round(2)
    
    ranking_proveedores['% Participación Presupuesto'] = (
        ranking_proveedores['Presupuesto Proveedor'] / ranking_proveedores['Presupuesto Proveedor'].sum() * 100
    ).round(2)
    
    ranking_proveedores = ranking_proveedores.sort_values('Venta Total Proveedor', ascending=False).reset_index(drop=True)
    ranking_proveedores['Ranking'] = range(1, len(ranking_proveedores) + 1)
    
    # === MERGE: DETALLE ARTÍCULOS + TOTALES PROVEEDOR ===
    df_final = df_detalle.merge(
        ranking_proveedores,
        left_on=['proveedor', 'idproveedor'],
        right_on=['Proveedor', 'ID Proveedor'],
        how='left'
    )
    
    # === CALCULAR MÉTRICAS INDIVIDUALES DEL ARTÍCULO ===
    df_final['Utilidad Artículo'] = (df_final['venta_total'] - df_final['costo_total']).round(0).astype(int)
    df_final['Rentabilidad % Artículo'] = (
        (df_final['Utilidad Artículo'] / df_final['venta_total']) * 100
    ).round(2)
    df_final['Tiene Exceso'] = (df_final['exceso_STK'] > 0).map({True: 'Sí', False: 'No'})
    df_final['Stock Actual'] = df_final['STK_TOTAL'].fillna(0).astype(int)
    
    # === RENOMBRAR COLUMNAS DE ARTÍCULO ===
    rename_dict = {
        'venta_total': 'Venta Artículo',
        'costo_total': 'Costo Artículo',
        'cantidad_vendida': 'Cantidad Vendida',
        'PRESUPUESTO': 'Presupuesto Artículo',
        'costo_exceso_STK': 'Costo Exceso Artículo',
        'subfamilia': 'Subfamilia'
    }
    
    # Solo renombrar descripcion si existe
    if 'descripcion' in df_final.columns:
        rename_dict['descripcion'] = 'Descripción'
    
    df_final = df_final.rename(columns=rename_dict)
    
    # === SELECCIONAR Y ORDENAR COLUMNAS FINALES ===
    columnas_finales_renamed = [
        'Ranking',
        'ID Proveedor',
        'Proveedor',
        '% Participación Ventas',
        'Venta Total Proveedor',
        'Costo Total Proveedor',
        'Utilidad Proveedor',
        'Rentabilidad % Proveedor',
        '% Participación Presupuesto',
        'Presupuesto Proveedor',
        'Artículos Proveedor',
        'Art. con Exceso Proveedor',
        'Costo Exceso Proveedor',
        'Art. Sin Stock Proveedor',
        'idarticulo',
        'Descripción',
        'Subfamilia',
        'Venta Artículo',
        'Costo Artículo',
        'Cantidad Vendida',
        'Utilidad Artículo',
        'Rentabilidad % Artículo',
        'Presupuesto Artículo',
        'Tiene Exceso',
        'Costo Exceso Artículo',
        'Stock Actual'
    ]
    
    # Filtrar solo las columnas que realmente existen
    columnas_existentes = [col for col in columnas_finales_renamed if col in df_final.columns]
    
    print(f"   📋 Columnas seleccionadas: {columnas_existentes}")
    
    df_final = df_final[columnas_existentes]
    
    # Ordenar por Ranking y luego por Venta Artículo descendente
    df_final = df_final.sort_values(
        ['Ranking', 'Venta Artículo'],
        ascending=[True, False]
    ).reset_index(drop=True)
    
    tiempo = time.time() - inicio
    print(f"   ✅ Ranking detallado procesado: {len(df_final):,} artículos en {tiempo:.2f}s")
    print(f"   📊 Proveedores únicos: {df_final['Proveedor'].nunique()}")
    print(f"   💰 Venta total: ${df_final['Venta Artículo'].sum():,.0f}")
    
    return df_final