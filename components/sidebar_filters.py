"""
Componente de filtros y sidebar
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from babel.dates import format_date
from babel import Locale
from custom_css import custom_sidebar

locale_es = Locale.parse("es")


def show_sidebar_filters(df_proveedores, df_proveedor_ids, query_bigquery_function, 
                        query_presupuesto_function, fecha_inicio_default=30):
    """
    Mostrar filtros en el sidebar y manejar la selección
    
    Args:
        df_proveedores: DataFrame con datos de proveedores
        df_proveedor_ids: DataFrame con mapeo id-proveedor
        query_bigquery_function: Función para consultar BigQuery
        query_presupuesto_function: Función para consultar presupuesto
        fecha_inicio_default: Días por defecto para el rango de fechas
    
    Returns:
        tuple: (proveedor, fecha_inicio, fecha_fin, df_presu)
    """
    # CSS & LOGO
    st.sidebar.markdown(custom_sidebar(), unsafe_allow_html=True)
    
    ## Información usuario y logout compacto
    st.sidebar.markdown(f"""
    <div style='display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;'>
        <span style='font-size: 0.9rem; color: #555;'>👤 {st.session_state.get('name', 'Usuario')}</span>
    </div>
    """, unsafe_allow_html=True)

    # Botón logout justo debajo
    if 'authenticator' in st.session_state:
        st.session_state['authenticator'].logout(button_name='Salir', location='sidebar')

    # Lista de proveedores
    proveedores = sorted(df_proveedores['proveedor'].dropna().unique())
    proveedor_actual = st.session_state.get("selected_proveedor")
    
    # Selector de proveedor
    proveedor = st.sidebar.selectbox(
        "🔎 Elegir proveedor",
        options=proveedores,
        index=proveedores.index(proveedor_actual) if proveedor_actual in proveedores else None,
        placeholder="Seleccionar proveedor..."
    )
    
    # Rango de fechas
    rango_opciones = {
        "Últimos 30 días": 30,
        "Últimos 60 días": 60,
        "Últimos 90 días": 90,
        "Últimos 180 días": 180,
        "Últimos 356 días": 365,
        "Personalizado": None
    }
    
    if proveedor and "analysis_data" not in st.session_state:
        st.sidebar.markdown(
            '<div class="highlight-period">📅 Elige un período de análisis</div>', 
            unsafe_allow_html=True
        )
    
    rango_seleccionado = st.sidebar.selectbox(
        "📅 Período de Análisis:",
        options=list(rango_opciones.keys()),
        index=0
    )
    
    # Selección de fechas
    if rango_seleccionado == "Personalizado":
        col1, col2 = st.sidebar.columns(2)
        fecha_inicio = col1.date_input(
            "Desde:", 
            value=datetime.now().date() - timedelta(days=fecha_inicio_default)
        )
        fecha_fin = col2.date_input("Hasta:", value=datetime.now().date())
    else:
        dias = rango_opciones[rango_seleccionado]
        fecha_fin = datetime.now().date()
        fecha_inicio = fecha_fin - timedelta(days=dias)
    
    # Formateo en español
    fecha_inicio_fmt = format_date(fecha_inicio, format="d MMMM y", locale=locale_es).capitalize()
    fecha_fin_fmt = format_date(fecha_fin, format="d MMMM y", locale=locale_es).capitalize()
    
    # Mostrar resumen
    st.sidebar.info(f"📅 **{rango_seleccionado}**\n\n{fecha_inicio_fmt} / {fecha_fin_fmt}")
    
    # Inicializar variable
    df_presu = None
    
    # Obtener ID del proveedor
    filtro = df_proveedor_ids[df_proveedor_ids['proveedor'] == proveedor]
    if not filtro.empty:
        fila = int(filtro['idproveedor'].iloc[0])
    else:
        st.sidebar.error("Selecciona un proveedor y analiza.")
        return proveedor, fecha_inicio, fecha_fin, None
    
    # Botón de análisis
    if st.sidebar.button("Realizar Análisis", type="primary", width='stretch'):
        if not proveedor:
            st.sidebar.error("❌ Selecciona un proveedor")
        else:
            # Consultar tickets
            with st.spinner(f"🔄 Consultando datos de {proveedor}"):
                df_tickets = query_bigquery_function(proveedor, fecha_inicio, fecha_fin)
                if df_tickets is not None:
                    st.session_state.analysis_data = df_tickets
                    st.session_state.selected_proveedor = proveedor
                else:
                    st.sidebar.error("❌ No se encontraron datos para el período seleccionado")
            
            # Consultar presupuesto
            if fila > 0:
                with st.spinner(f"🔄 Consultando presupuesto proveedor id: {fila}"):
                    df_presu = query_presupuesto_function(fila)
                    if df_presu is not None:
                        st.session_state.resultados_data = df_presu
                    else:
                        st.sidebar.error("❌ No se encontraron datos de presupuesto")
            else:
                st.sidebar.error("❌ No se encontró el ID del proveedor")
    
    # Recuperar de session_state si existe
    if "df_presu" in st.session_state:
        df_presu = st.session_state.df_presu
    
    # Resumen del período (si hay datos cargados)
    if st.session_state.get("analysis_data") is not None:
        df_tickets = st.session_state.analysis_data
        df_tickets['fecha'] = pd.to_datetime(df_tickets['fecha'])
        
        productos_unicos = df_tickets['idarticulo'].nunique() if 'idarticulo' in df_tickets else 0
        familias = df_tickets['familia'].nunique() if 'familia' in df_tickets else 0
        subfamilias = df_tickets['subfamilia'].nunique() if 'subfamilia' in df_tickets else 0
        dia_top = df_tickets['fecha'].dt.day_name().value_counts().idxmax()
        mes_top = df_tickets['fecha'].dt.strftime('%B').value_counts().idxmax()
        
        st.sidebar.markdown(f"🛒 **Productos Únicos:** `{productos_unicos}`")
        st.sidebar.markdown(f"🧩 **Familias:** `{familias}`")
        st.sidebar.markdown(f"🧬 **Subfamilias:** `{subfamilias}`")
        st.sidebar.markdown(f"📅 **Día más ventas:** `{dia_top}`")
        st.sidebar.markdown(f"📆 **Mes más ventas:** `{mes_top}`")
    
    return proveedor, fecha_inicio, fecha_fin, df_presu