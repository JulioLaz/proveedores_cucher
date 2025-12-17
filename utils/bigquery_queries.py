"""
Funciones para consultas a BigQuery
"""
import streamlit as st
import pandas as pd
import numpy as np
import os
from google.cloud import bigquery
from limpiar_datos import limpiar_datos
# from time import time
import time
@st.cache_data(ttl=3600)
def query_bigquery_tickets(credentials_path, project_id, bigquery_table, 
                           ids, fecha_inicio, fecha_fin):
    """
    Consultar tickets de BigQuery para un proveedor específico
    
    Args:
        credentials_path: Ruta al archivo de credenciales
        project_id: ID del proyecto de GCP
        bigquery_table: Tabla de BigQuery
        ids: Lista de IDs de artículos
        fecha_inicio: Fecha de inicio del período
        fecha_fin: Fecha fin del período
    
    Returns:
        DataFrame con los datos de tickets o None si no hay datos
    """
    try:
        if len(ids) == 0:
            return None
        
        id_str = ','.join(ids)
        client = bigquery.Client.from_service_account_json(credentials_path)
        
        query = f"""
        SELECT fecha_comprobante, idarticulo, descripcion, cantidad_total,
               costo_total, precio_total, sucursal, familia, subfamilia
        FROM `{project_id}.{bigquery_table}`
        WHERE idarticulo IN ({id_str})
        AND DATE(fecha_comprobante) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        ORDER BY fecha_comprobante DESC
        """
        
        df = client.query(query).to_dataframe()
        
        if len(df) == 0:
            return None
        
        # Calcular métricas adicionales
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
        
        # Limpieza final
        df = limpiar_datos(df)
        return df
        
    except Exception as e:
        st.error(f"Error consultando BigQuery: {e}")
        return None

@st.cache_data(ttl=3600)
def get_tickets_para_analisis_stock(credentials_path, project_id, bigquery_table, fecha_desde, fecha_hasta):
    """
    Obtiene tickets COMPLETOS con fecha_comprobante para análisis de stock
    Solo se usa para tab4 (análisis de artículos rentables)
    
    Args:
        credentials_path: Ruta a credenciales JSON
        project_id: ID del proyecto
        bigquery_table: Nombre de la tabla
        fecha_desde: Fecha inicio (str o date)
        fecha_hasta: Fecha fin (str o date)
    
    Returns:
        DataFrame con tickets completos
    """
    import os
    
    print(f"\n{'='*80}")
    print(f"📊 CARGANDO TICKETS COMPLETOS PARA ANÁLISIS DE STOCK")
    print(f"{'='*80}")
    print(f"   • Desde: {fecha_desde}")
    print(f"   • Hasta: {fecha_hasta}")
    
    inicio = time.time()
    
    # Detectar ambiente
    is_cloud = not os.path.exists(credentials_path) if credentials_path else True
    
    if is_cloud:
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        client = bigquery.Client(credentials=credentials, project=project_id)
    else:
        client = bigquery.Client.from_service_account_json(credentials_path, project=project_id)
    
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
    FROM `{project_id}.{bigquery_table}`
    WHERE DATE(fecha_comprobante) BETWEEN '{fecha_desde}' AND '{fecha_hasta}'
    ORDER BY fecha_comprobante
    """
    
    df = client.query(query).to_dataframe()
    
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
    Consultar resultados de análisis por ID de proveedor
    
    Args:
        credentials_path: Ruta al archivo de credenciales
        project_id: ID del proyecto de GCP
        dataset: Dataset de BigQuery
        table: Tabla de BigQuery
        idproveedor: ID del proveedor (puede ser unificado)
        proveedor_unificado: Diccionario de mapeo de IDs unificados
    
    Returns:
        DataFrame con los resultados o DataFrame vacío
    """
    try:
        client = bigquery.Client.from_service_account_json(credentials_path)
        
        # Manejar IDs unificados
        if idproveedor and proveedor_unificado:
            # Verificar si es un ID unificado
            if idproveedor in [12000001, 12000002, 12000003, 12000004, 12000005]:
                # Buscar los IDs originales
                ids_originales = [k for k, v in proveedor_unificado.items() if v == idproveedor]
                id_condition = f"idproveedor IN ({','.join(map(str, ids_originales))})"
            else:
                id_condition = f"idproveedor = {idproveedor}"
            
            query = f"""
                SELECT *
                FROM `{project_id}.{dataset}.{table}`
                WHERE idarticulo IS NOT NULL
                AND {id_condition}
            """
        else:
            query = f"""
                SELECT *
                FROM `{project_id}.{dataset}.{table}`
                WHERE idarticulo IS NOT NULL
            """
        
        df = client.query(query).to_dataframe()
        
        if df.empty and idproveedor:
            st.warning(f"⚠️ No se encontraron datos para el proveedor con ID: {idproveedor}")
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error al consultar BigQuery: {e}")
        return pd.DataFrame()