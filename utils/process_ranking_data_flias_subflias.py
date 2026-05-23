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

 Columnas adicionales de participación (todas sobre TOTAL GENERAL):
   • % Participación Ventas               -> a nivel fila (subfamilia)
   • % Participación Ventas x Familia     -> suma por Proveedor + Familia
                                             (mismo valor en todas las filas
                                              de esa combinación)
   • % Participación Ventas x Proveedor   -> suma por Proveedor
                                             (mismo valor en todas las filas
                                              del proveedor)

 Columnas de Ranking:
   • Ranking                              -> posición del PROVEEDOR
                                             (1=mayor venta total, 2, 3...),
                                             se repite en todas las filas
                                             del mismo proveedor.
   • Ranking-proveedor-subfamilia         -> secuencial 1..N sobre el orden
                                             jerárquico (proveedor -> familia
                                             -> subfamilia, todo por venta
                                             desc).

 Orden de salida (jerárquico, todo por Venta Total desc):
   1) Proveedores ordenados por su Venta Total acumulada (desc).
   2) Dentro de cada proveedor, Familias por su Venta Total acumulada (desc).
   3) Dentro de cada familia, Subfamilias por su Venta Total (desc).
═══════════════════════════════════════════════════════════════════════════════
 VERSIONADO
───────────────────────────────────────────────────────────────────────────────
 v1.0  (2026-05-19) - Versión inicial. Replica process_ranking_data() agregando
                      el desglose por familia y subfamilia. Mismo cacheo,
                      mismos fillna, mismos prints con timing. Único agregado:
                      protección de división por cero en 'Rentabilidad %'.
 v1.1  (2026-05-19) - Orden jerárquico: el proveedor mantiene su posición por
                      Venta Total acumulada y, dentro de él, se ordena primero
                      por Familia (por venta acumulada desc) y luego por
                      Subfamilia (por venta desc).
 v1.2  (2026-05-19) - Se agregan:
                        - Columna '% Participación Ventas x Familia'.
                        - Columna '% Participación Ventas x Proveedor'.
                        - Se renombra la columna 'Ranking' anterior como
                          'Ranking-proveedor-subfamilia'.
                        - Nuevo 'Ranking' = posición del proveedor por su
                          Venta Total acumulada, repetida en todas sus filas.
═══════════════════════════════════════════════════════════════════════════════
'''

import time
import numpy as np
import pandas as pd
import streamlit as st


@st.cache_data(ttl=300, show_spinner=False)
def process_ranking_data_flias_subflias(df_proveedores, df_ventas, df_presupuesto, df_familias):
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

    ranking['% Participación Presupuesto'] = (ranking['Presupuesto'] / ranking['Presupuesto'].sum() * 100).round(3)
    ranking['% Participación Ventas'] = (ranking['Venta Total'] / ranking['Venta Total'].sum() * 100).round(3)
    ranking['% Participación Utilidad'] = (ranking['Utilidad'] / ranking['Utilidad'].sum() * 100).round(3)

    # === % PARTICIPACIÓN VENTAS x FAMILIA y x PROVEEDOR (v1.2) ===
    # Ambas sobre TOTAL GENERAL: suma del % Participación Ventas dentro del
    # grupo correspondiente, repetido en todas las filas del grupo.
    ranking['% Participación Ventas x Familia'] = (
        ranking.groupby(['Proveedor', 'Familia'])['% Participación Ventas']
        .transform('sum')
        .round(3)
    )
    ranking['% Participación Ventas x Proveedor'] = (
        ranking.groupby('Proveedor')['% Participación Ventas']
        .transform('sum')
        .round(3)
    )

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

    # === RANKINGS (v1.2) ===
    # Secuencial 1..N sobre el orden jerárquico (proveedor -> familia -> subfamilia)
    ranking['Ranking-proveedor-subfamilia'] = range(1, len(ranking) + 1)

    # Ranking del PROVEEDOR (1, 2, 3, ...) repetido en todas las filas del
    # mismo proveedor. Usamos sort=False para respetar el orden actual del df
    # (que ya está sorteado por venta total acumulada del proveedor desc).
    ranking['Ranking'] = ranking.groupby('Proveedor', sort=False).ngroup() + 1

    tiempo = time.time() - inicio
    print(f"   ✅ Ranking flias/subflias procesado: {len(ranking)} filas "
          f"({ranking['Proveedor'].nunique()} proveedores) en {tiempo:.2f}s")

    return ranking
