'''
═══════════════════════════════════════════════════════════════════════════════
 process_resumen_proveedor_familia.py
═══════════════════════════════════════════════════════════════════════════════
 Genera una tabla RESUMEN con 1 fila por combinación [Proveedor + Familia],
 a partir del ranking detallado de process_ranking_data_flias_subflias().

 Vista pensada para decisión de COMPRA: muestra, dentro de cada proveedor,
 cómo se reparte la torta entre sus familias y qué subfamilias de cada
 familia concentran las ventas.

 Columnas de salida:
   • Ranking                       -> ranking del PROVEEDOR (1=mayor venta).
   • Proveedor, Familia
   • % Part. Ventas                -> venta de la familia / TOTAL GENERAL.
   • % Part. Ventas x Proveedor    -> peso del proveedor en el total general.
   • Venta Total, Utilidad         -> sumas de la familia.
   • Rentabilidad %                -> Utilidad / Venta Total × 100.
   • Subfamilias                   -> TEXTO con el Top 5 de subfamilias de
                                       esa familia, en formato
                                       "Nombre tru…: 45.0%, ..." donde el %
                                       es SOBRE LA FAMILIA (no sobre total
                                       general) y los nombres están
                                       truncados a 18 chars con '…'. Si
                                       hay más de 5 subfamilias, agrega al
                                       final "…+N más (X.X%)".
   • Presupuesto
   • % Cumplimiento Presup.        -> Venta Total / Presupuesto × 100.

 Orden de salida:
   1) Ranking del proveedor (asc) -> respeta el orden ya sorteado.
   2) Dentro del proveedor, familia por Venta Total (desc).
═══════════════════════════════════════════════════════════════════════════════
 VERSIONADO
───────────────────────────────────────────────────────────────────────────────
 v1.0  (2026-05-19) - Versión inicial. Agregación por Proveedor + Familia
                      con columna 'Subfamilias' en formato texto Top 5,
                      % sobre familia, nombres truncados a 18 chars con '…'.
═══════════════════════════════════════════════════════════════════════════════
'''

import time
import numpy as np
import pandas as pd
import streamlit as st


# ─── Configuración del resumen de subfamilias ────────────────────────────────
TOP_N_SUBFAMILIAS = 5
MAX_CHARS_SUBFAMILIA = 18


def _truncar(nombre, n=MAX_CHARS_SUBFAMILIA):
    """Trunca un nombre a n caracteres agregando '…' si hace falta."""
    s = str(nombre)
    if len(s) <= n:
        return s
    return s[:n].rstrip() + '…'


def _resumen_subfamilias(grupo):
    """
    Para un sub-df de [Proveedor + Familia], devuelve un string del tipo:
        'Aditivos para lav…: 47.0%, Jabón en polvo: 33.0%, ..., …+3 más (2.1%)'
    con porcentajes SOBRE LA FAMILIA.
    """
    total_familia = grupo['Venta Total'].sum()
    if total_familia <= 0:
        return ""

    sub = (
        grupo[['Subfamilia', 'Venta Total']]
        .sort_values('Venta Total', ascending=False)
        .copy()
    )
    sub['_pct'] = (sub['Venta Total'] / total_familia * 100).round(1)

    top = sub.head(TOP_N_SUBFAMILIAS)
    resto = sub.iloc[TOP_N_SUBFAMILIAS:]

    items = [
        f"{_truncar(row['Subfamilia'])}: {row['_pct']:.1f}%"
        for _, row in top.iterrows()
    ]

    if len(resto) > 0:
        pct_resto = resto['_pct'].sum()
        items.append(f"…+{len(resto)} más ({pct_resto:.1f}%)")

    return ", ".join(items)


@st.cache_data(ttl=300, show_spinner=False)
def process_resumen_proveedor_familia(ranking_detalle):
    """
    Construye el resumen [Proveedor + Familia] a partir del ranking detallado
    (salida de process_ranking_data_flias_subflias).
    """
    print(f"\n🔧 PROCESANDO RESUMEN PROVEEDOR x FAMILIA (sin caché)")
    inicio = time.time()

    if ranking_detalle is None or len(ranking_detalle) == 0:
        print(f"   ⚠️  Ranking vacío. No se genera resumen.")
        return pd.DataFrame()

    df = ranking_detalle.copy()

    # === AGREGACIÓN POR PROVEEDOR + FAMILIA ===
    resumen = df.groupby(
        ['Proveedor', 'ID Proveedor', 'Familia'], sort=False
    ).agg({
        'Venta Total': 'sum',
        'Costo Total': 'sum',
        'Utilidad': 'sum',
        'Presupuesto': 'sum',
        # Estas se repiten dentro del grupo -> first basta
        'Ranking': 'first',
        '% Participación Ventas x Proveedor': 'first',
    }).reset_index()

    print(f"   📊 Combinaciones Proveedor+Familia: {len(resumen):,}")

    # === % PART. VENTAS (sobre TOTAL GENERAL) ===
    venta_total_general = df['Venta Total'].sum()
    if venta_total_general > 0:
        resumen['% Part. Ventas'] = (
            resumen['Venta Total'] / venta_total_general * 100
        ).round(2)
    else:
        resumen['% Part. Ventas'] = 0.0

    # === RENTABILIDAD % (con protección /0) ===
    resumen['Rentabilidad %'] = (
        resumen['Utilidad'] / resumen['Venta Total'].replace(0, np.nan) * 100
    ).round(2).fillna(0)

    # === % CUMPLIMIENTO PRESUPUESTO ===
    resumen['% Cumplimiento Presup.'] = (
        resumen['Venta Total'] / resumen['Presupuesto'].replace(0, np.nan) * 100
    ).round(2).fillna(0)

    # === COLUMNA 'Subfamilias' (texto Top 5, % sobre familia) ===
    print(f"   🧩 Generando texto Top {TOP_N_SUBFAMILIAS} de subfamilias por grupo...")
    subfamilias_txt = (
        df.groupby(['Proveedor', 'Familia'], sort=False)
        .apply(_resumen_subfamilias, include_groups=False)
        .reset_index(name='Subfamilias')
    )
    resumen = resumen.merge(subfamilias_txt, on=['Proveedor', 'Familia'], how='left')

    # === RENOMBRAR % Part. Ventas x Proveedor a versión corta para tabla ===
    resumen = resumen.rename(columns={
        '% Participación Ventas x Proveedor': '% Part. Ventas x Proveedor'
    })

    # === ORDEN FINAL DE COLUMNAS ===
    columnas_finales = [
        'Ranking', 'Proveedor', 'Familia',
        '% Part. Ventas', '% Part. Ventas x Proveedor',
        'Venta Total', 'Utilidad', 'Rentabilidad %',
        'Subfamilias',
        'Presupuesto', '% Cumplimiento Presup.',
    ]
    # defensivo por si alguna no existe
    columnas_finales = [c for c in columnas_finales if c in resumen.columns]
    resumen = resumen[columnas_finales]

    # === ORDEN DE FILAS: Ranking proveedor (asc) -> Venta familia (desc) ===
    resumen = resumen.sort_values(
        ['Ranking', 'Venta Total'],
        ascending=[True, False]
    ).reset_index(drop=True)

    tiempo = time.time() - inicio
    print(f"   ✅ Resumen procesado: {len(resumen):,} filas "
          f"({resumen['Proveedor'].nunique()} proveedores) en {tiempo:.2f}s")

    return resumen


# ═══════════════════════════════════════════════════════════════════════════════
#  USO EN STREAMLIT
# ═══════════════════════════════════════════════════════════════════════════════
#  Ubicar este bloque ANTES del ranking detallado actual.
#
#  from utils.process_resumen_proveedor_familia import process_resumen_proveedor_familia
#
#  resumen_pf = process_resumen_proveedor_familia(ranking_flia_subflia)
#
#  with st.expander("📊 Resumen Proveedor × Familia — ¿En qué concentrar las compras?",
#                   expanded=True):
#      st.caption(
#          "Una fila por combinación Proveedor + Familia. La columna "
#          "**Subfamilias** muestra el Top 5 de subfamilias dentro de cada "
#          "familia (con % sobre la familia, no sobre el total general)."
#      )
#
#      config_resumen = {
#          'Ranking':                     st.column_config.NumberColumn('Rk.', format='%d', width='small'),
#          'Proveedor':                   st.column_config.TextColumn('Proveedor', width='medium'),
#          'Familia':                     st.column_config.TextColumn('Familia',   width='medium'),
#          '% Part. Ventas':              st.column_config.NumberColumn('% Part. Ventas',       format='%.2f%%'),
#          '% Part. Ventas x Proveedor':  st.column_config.NumberColumn('% Part. Ventas x Prov', format='%.2f%%'),
#          'Venta Total':                 st.column_config.NumberColumn('Venta Total',  format='dollar'),
#          'Utilidad':                    st.column_config.NumberColumn('Utilidad',     format='dollar'),
#          'Rentabilidad %':              st.column_config.NumberColumn('Rentabilidad %', format='%.2f%%'),
#          'Subfamilias':                 st.column_config.TextColumn(
#                                             'Subfamilias (Top 5, % s/ familia)',
#                                             width='large',
#                                             help='Top 5 subfamilias de la familia, ordenadas por venta. % sobre la familia.'
#                                         ),
#          'Presupuesto':                 st.column_config.NumberColumn('Presupuesto', format='dollar'),
#          '% Cumplimiento Presup.':      st.column_config.NumberColumn('% Cumpl. Presup.', format='%.2f%%'),
#      }
#
#      st.dataframe(
#          resumen_pf,
#          width='stretch',
#          hide_index=True,
#          column_config=config_resumen
#      )
# ═══════════════════════════════════════════════════════════════════════════════
