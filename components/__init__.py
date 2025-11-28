"""
Componentes modulares para el dashboard de proveedores
"""

# Componentes principales
from .proveedor_dashboard import ProveedorDashboard
from .inventory_dashboard import InventoryDashboard

# Componentes de análisis
from .sidebar_filters import show_sidebar_filters
from .budget_analysis import show_presupuesto_estrategico
from .article_analysis import show_idarticulo_analysis
from .executive_summary_detailed import show_executive_summary_best

# Componentes existentes
from .executive_summary import show_executive_summary
from .products_analysis import show_products_analysis
from .temporal_analysis import show_temporal_analysis
from .advanced_analysis import show_advanced_analysis
from .global_dashboard import show_global_dashboard

__all__ = [
    'ProveedorDashboard',
    'InventoryDashboard',
    'show_sidebar_filters',
    'show_presupuesto_estrategico',
    'show_idarticulo_analysis',
    'show_executive_summary_best',
    'show_executive_summary',
    'show_products_analysis',
    'show_temporal_analysis',
    'show_advanced_analysis',
    'show_global_dashboard'
]