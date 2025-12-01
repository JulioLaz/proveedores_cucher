"""
Dashboard de Análisis de Proveedores
Versión Modularizada - Cucher Mercados
Sistema de autenticación integrado
"""
import streamlit as st
import streamlit_authenticator as stauth
import warnings
import copy
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
# SISTEMA DE AUTENTICACIÓN
# ═══════════════════════════════════════════════════════════

# Crear copia profunda completamente independiente de secrets
credentials = copy.deepcopy({
    'usernames': {
        username: dict(user_data)
        for username, user_data in st.secrets['credentials']['usernames'].items()
    }
})

# Crear autenticador
authenticator = stauth.Authenticate(
    credentials,
    st.secrets['cookie']['name'],
    st.secrets['cookie']['key'],
    st.secrets['cookie']['expiry_days']
)

# AGREGAR ESTA LÍNEA:
st.session_state['authenticator'] = authenticator

# Widget de login
authenticator.login()

# ═══════════════════════════════════════════════════════════
# VERIFICACIÓN DE AUTENTICACIÓN
# ═══════════════════════════════════════════════════════════

if st.session_state["authentication_status"]:
    # ═══════════════════════════════════════════════════════
    # USUARIO AUTENTICADO - DASHBOARD PRINCIPAL
    # ═══════════════════════════════════════════════════════
    
    # Sidebar con información de usuario
    with st.sidebar:
      #   st.markdown("---")
        st.markdown(f"### ✨ {st.session_state['name']}")
        authenticator.logout(location='sidebar')
      #   st.markdown("---")
    
    # Función principal de la aplicación
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
    
    # Ejecutar dashboard
    main()

elif st.session_state["authentication_status"] is False:
    st.error('❌ Usuario o contraseña incorrectos')
    st.info("""
    **¿Olvidaste tu contraseña?**  
    Contacta al administrador del sistema.
    """)
    
   
elif st.session_state["authentication_status"] is None:
    st.warning('👋 Por favor ingrese sus credenciales para acceder')
    
    # Instrucciones de acceso
    with st.expander("ℹ️ Información de acceso"):
        st.markdown("""
        **Usuario:** La parte de tu email antes del @  
        Ejemplo: `cucher_mercados` para cucher_mercados@gmail.com
        
        **Contraseña temporal:** Primeras 3 letras de tu nombre + 2025  
        Ejemplo: `cucher2025` para Cucher Mercados
        
        **⚠️ Nota:** En tu primer acceso, contacta al administrador para cambiar tu contraseña si tienes dudas.
        **⚠️ Nota:** Guarda los datos en google.
                    
        """)