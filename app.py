import streamlit as st
import streamlit_authenticator as stauth
import warnings
import copy
from components.proveedor_dashboard import ProveedorDashboard
from custom_css import custom_css
from utils.telegram_notifier import send_telegram_notification

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

# Guardar authenticator en session_state
st.session_state['authenticator'] = authenticator

# Widget de login
authenticator.login()

# ═══════════════════════════════════════════════════════════
# VERIFICACIÓN DE AUTENTICACIÓN
# ═══════════════════════════════════════════════════════════

if st.session_state["authentication_status"]:
    # ═══════════════════════════════════════════════════════
    # ✅ USUARIO AUTENTICADO - ENVIAR NOTIFICACIÓN TELEGRAM
    # ═══════════════════════════════════════════════════════
    
    # Enviar notificación SOLO la primera vez (evitar duplicados)
    if 'telegram_notified' not in st.session_state:
        username = st.session_state.get('username')
        name = st.session_state.get('name')
        
        # Obtener email desde secrets
        email = st.secrets['credentials']['usernames'][username]['email']
        
        # Enviar notificación a Telegram
        send_telegram_notification(
            username=username,
            name=name,
            email=email,
            success=True
        )
        
        # Marcar como notificado
        st.session_state.telegram_notified = True
        
        print(f"\n✅ [ACCESO] Usuario: {username} ({name}) - Email: {email}")
    
    # ═══════════════════════════════════════════════════════
    # DASHBOARD PRINCIPAL
    # ═══════════════════════════════════════════════════════
    
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
    # ═══════════════════════════════════════════════════════
    # ❌ AUTENTICACIÓN FALLIDA - NOTIFICAR INTENTO (OPCIONAL)
    # ═══════════════════════════════════════════════════════
    
    st.error('❌ Usuario o contraseña incorrectos')
    st.info("""
    **¿Olvidaste tu contraseña?**  
    Contacta al administrador del sistema.
    """)
    
    # OPCIONAL: Notificar intentos fallidos
    if 'failed_login_notified' not in st.session_state:
        username = st.session_state.get('username', 'desconocido')
        
        send_telegram_notification(
            username=username,
            name="Desconocido",
            email="N/A",
            success=False
        )
        
        st.session_state.failed_login_notified = True
        print(f"\n❌ [INTENTO FALLIDO] Usuario: {username}")

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
