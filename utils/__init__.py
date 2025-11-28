"""
Módulo de utilidades para la aplicación
"""
from .config import setup_credentials, PROVEEDOR_UNIFICADO, NOMBRES_UNIFICADOS
from .bigquery_queries import query_bigquery_tickets, query_resultados_idarticulo
from .data_processing import (
    load_proveedores_from_sheet, 
    calculate_metrics, 
    generate_insights,
    format_abbr
)

__all__ = [
    'setup_credentials',
    'PROVEEDOR_UNIFICADO',
    'NOMBRES_UNIFICADOS',
    'query_bigquery_tickets',
    'query_resultados_idarticulo',
    'load_proveedores_from_sheet',
    'calculate_metrics',
    'generate_insights',
    'format_abbr'
]