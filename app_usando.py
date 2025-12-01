"""
Dashboard de Análisis de Proveedores
Versión Modularizada - Cucher Mercados
"""
import streamlit as st
import warnings
from components.proveedor_dashboard import ProveedorDashboard
from custom_css import custom_css

# Suprimir warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Proveedores", 
    page_icon="📊", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════
# CSS PERSONALIZADO
# ═══════════════════════════════════════════════════════════

st.markdown(custom_css(), unsafe_allow_html=True)

# Ocultar botón Share
st.markdown("""
    <style>
    span[data-testid="stToolbarActionButtonLabel"],
    div[data-testid="stToolbarActionButtonIcon"] {
        display: none !important;
        pointer-events: none !important;
        visibility: hidden !important;
    }
    </style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════

def main():
    """Función principal de la aplicación"""
    dashboard = ProveedorDashboard()
    dashboard.run()
    
    # Footer
    st.markdown("""
    <hr style="margin: 0; border: none; border-top: 2px solid #ccc;" />
    <div style="text-align: center; color: #666; font-size: 0.8em; margin-top: 20px;">
        Julio A. Lazarte | Científico de Datos & BI | Cucher Mercados
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()