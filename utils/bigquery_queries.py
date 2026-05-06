"""
Funciones para consultas a MotherDuck (antes BigQuery)
"""
import streamlit as st
import pandas as pd
import numpy as np
import time
from utils.motherduck_connection import get_connection
from limpiar_datos import limpiar_datos


@st.cache_data(ttl=3600)
def query_bigquery_tickets(credentials_path, project_id, bigquery_table,
                           ids, fecha_inicio, fecha_fin):
    """
    Consultar tickets de MotherDuck para un proveedor específico.
    Los parámetros credentials_path, project_id y bigquery_table se mantienen
    por compatibilidad con llamadores existentes pero ya no se usan.
    """
    try:
        if len(ids) == 0:
            return None

        id_str = ','.join(ids)
        con = get_connection()

        query = f"""
        SELECT fecha_comprobante, idarticulo, descripcion, cantidad_total,
               costo_total, precio_total, sucursal, familia, subfamilia
        FROM my_db.tickets_all
        WHERE idarticulo IN ({id_str})
        AND fecha_comprobante::DATE BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        ORDER BY fecha_comprobante DESC
        """

        df = con.execute(query).df()
        con.close()

        if len(df) == 0:
            return None

        df['utilidad'] = df['precio_total'] - df['costo_total']
        df['margen_porcentual'] = np.where(
            df['precio_total'] > 0,
            (df['utilidad'] / df['precio_total']) * 100,
            0
        )

        df['fecha_comprobante'] = pd.to_datetime(df['fecha_comprobante'])
        df['fecha'] = df['fecha_comprobante'].dt.date
        df['mes_año'] = df['fecha_comprobante'].dt.to_period('M').astype(str)
        df['dia_semana'] = df['fecha_comprobante'].dt.day_name()

        df = limpiar_datos(df)
        return df

    except Exception as e:
        st.error(f"Error consultando MotherDuck: {e}")
        return None


@st.cache_data(ttl=3600)
def get_tickets_para_analisis_stock(credentials_path, project_id, bigquery_table,
                                    fecha_desde, fecha_hasta):
    """
    Obtiene tickets completos para análisis de stock (tab4).
    Los parámetros de BigQuery se mantienen por compatibilidad.
    """
    print(f"\n{'='*80}")
    print(f"📊 CARGANDO TICKETS COMPLETOS PARA ANÁLISIS DE STOCK")
    print(f"{'='*80}")
    print(f"   • Desde: {fecha_desde}")
    print(f"   • Hasta: {fecha_hasta}")

    inicio = time.time()
    con = get_connection()

    query = f"""
    SELECT
        fecha_comprobante,
        idarticulo,
        idartalfa,
        descripcion,
        cantidad_total,
        precio_total,
        costo_total,
        familia,
        subfamilia
    FROM my_db.tickets_all
    WHERE fecha_comprobante::DATE BETWEEN '{fecha_desde}' AND '{fecha_hasta}'
    ORDER BY fecha_comprobante
    """

    df = con.execute(query).df()
    con.close()

    tiempo = time.time() - inicio
    print(f"   ✅ Tickets cargados: {len(df):,} registros")
    print(f"   ⏱️  Tiempo: {tiempo:.2f}s")
    print(f"{'='*80}\n")

    return df


def query_resultados_idarticulo(credentials_path, project_id,
                                dataset='presupuesto',
                                table='result_final_alert_all',
                                idproveedor=None,
                                proveedor_unificado=None):
    """
    Consultar resultados de análisis por ID de proveedor desde MotherDuck.
    Los parámetros de BigQuery se mantienen por compatibilidad.
    """
    try:
        con = get_connection()

        if idproveedor and proveedor_unificado:
            if idproveedor in [12000001, 12000002, 12000003, 12000004, 12000005]:
                ids_originales = [k for k, v in proveedor_unificado.items() if v == idproveedor]
                id_condition = f"idproveedor IN ({','.join(map(str, ids_originales))})"
            else:
                id_condition = f"idproveedor = {idproveedor}"

            query = f"""
                SELECT *
                FROM my_db.result_final_alert_all
                WHERE idarticulo IS NOT NULL
                AND {id_condition}
            """
        else:
            query = """
                SELECT *
                FROM my_db.result_final_alert_all
                WHERE idarticulo IS NOT NULL
            """

        df = con.execute(query).df()
        con.close()

        if df.empty and idproveedor:
            st.warning(f"⚠️ No se encontraron datos para el proveedor con ID: {idproveedor}")

        return df

    except Exception as e:
        st.error(f"❌ Error al consultar MotherDuck: {e}")
        return pd.DataFrame()