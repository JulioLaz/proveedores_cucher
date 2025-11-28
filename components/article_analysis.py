"""
Análisis detallado por artículo individual
"""
import streamlit as st
import pandas as pd


def show_idarticulo_analysis(df_presu):
    """
    Análisis estratégico de inventario por artículo
    """
    if df_presu is None or df_presu.empty:
        st.warning("⚠️ No hay datos disponibles para análisis por artículo.")
        return

    # Selector de artículo
    opciones = df_presu[["idarticulo", "descripcion"]].drop_duplicates()
    opciones["etiqueta"] = opciones["idarticulo"].astype(str) + " - " + opciones["descripcion"]

    if opciones.empty:
        st.warning("⚠️ No hay artículos disponibles para seleccionar.")
        return

    seleccion = st.selectbox(
        "Seleccionar artículo para análisis detallado:", 
        opciones["etiqueta"].tolist()
    )

    try:
        id_seleccionado = int(seleccion.split(" - ")[0])
    except (IndexError, ValueError):
        st.error("❌ Ocurrió un error al procesar la selección de artículo.")
        return

    df_item = df_presu[df_presu["idarticulo"] == id_seleccionado].copy()

    if df_item.empty:
        st.info("No se encontraron datos para el artículo seleccionado.")
        return

    # Mostrar pestañas
    tabs = st.tabs([
        "📦 Stock y Cobertura", 
        "📈 Demanda y Presupuesto", 
        "💰 Rentabilidad", 
        "📊 Estacionalidad"
    ])

    with tabs[0]:
        tab_stock_y_cobertura(df_item)

    with tabs[1]:
        tab_demanda_presupuesto(df_item)

    with tabs[2]:
        tab_rentabilidad(df_item)

    with tabs[3]:
        tab_estacionalidad(df_item)


def tab_stock_y_cobertura(df):
    """Análisis de stock y cobertura por artículo"""
    st.markdown("### 🏪 Stock por Sucursal")
    
    cols = ['stk_corrientes', 'stk_express', 'stk_formosa', 'stk_hiper', 'stk_TIROL', 'stk_central']
    
    # Mostrar stock por sucursal
    col1, col2, col3 = st.columns(3)
    
    for idx, col in enumerate(cols):
        if col in df.columns:
            with [col1, col2, col3][idx % 3]:
                st.metric(
                    col.replace('stk_', '').upper(), 
                    f"{int(df[col].iloc[0]):,}"
                )
    
    st.markdown("---")
    
    # Métricas principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🔄 Stock Total", f"{int(df['STK_TOTAL'].iloc[0]):,}")
    
    with col2:
        st.metric("📆 Días de Cobertura", f"{df['dias_cobertura'].iloc[0]:.1f}")
    
    with col3:
        nivel_riesgo = df["nivel_riesgo"].iloc[0]
        color = "🔴" if "Alto" in str(nivel_riesgo) else "🟠" if "Medio" in str(nivel_riesgo) else "🟢"
        st.metric("⚠️ Nivel de Riesgo", f"{color} {nivel_riesgo}")
    
    # Información adicional
    st.markdown("#### 📋 Información Adicional")
    
    if 'ALERTA_STK_Tirol_Central' in df.columns:
        st.write(f"**🚨 Alerta Stock:** {df['ALERTA_STK_Tirol_Central'].iloc[0]}")
    
    if 'accion_gralporc' in df.columns:
        st.write(f"**✅ Acción Recomendada:** {df['accion_gralporc'].iloc[0]}")
    
    if 'PRESU_accion_gral' in df.columns:
        st.write(f"**💰 Presupuesto Asociado:** ${df['PRESU_accion_gral'].iloc[0]:,.2f}")


def tab_demanda_presupuesto(df):
    """Análisis de demanda y presupuesto"""
    st.markdown("### 📈 Demanda y Presupuesto")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'cnt_corregida' in df.columns:
            st.metric("🔢 Pronóstico Final", f"{int(df['cnt_corregida'].iloc[0]):,}")
    
    with col2:
        if 'PRESUPUESTO' in df.columns:
            st.metric("💰 Presupuesto", f"${df['PRESUPUESTO'].iloc[0]:,.0f}")
    
    with col3:
        if 'meses_act_estac' in df.columns:
            st.metric("📆 Meses Activos", int(df["meses_act_estac"].iloc[0]))

    # Análisis de exceso
    if 'exceso_STK' in df.columns and 'costo_exceso_STK' in df.columns:
        exceso_stk = df["exceso_STK"].iloc[0]
        costo_exceso = df["costo_exceso_STK"].iloc[0]

        if exceso_stk > 0:
            st.markdown("---")
            st.markdown("#### ⚠️ Análisis de Exceso de Stock")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("📦 Unidades en Exceso", f"{int(exceso_stk):,}")
            
            with col2:
                st.metric("💸 Costo del Exceso", f"${costo_exceso:,.0f}")
            
            st.warning("⚠️ Se detectó exceso de stock en este artículo. Considere acciones correctivas.")
        else:
            st.success("✅ No hay exceso de stock para este artículo.")


def tab_rentabilidad(df):
    """Análisis de rentabilidad del artículo"""
    st.markdown("### 💰 Rentabilidad del Artículo")

    # Obtener datos
    margen_all = df.get("margen_porc_all", pd.Series([None])).iloc[0]
    margen_90 = df.get("margen_a90", pd.Series([None])).iloc[0]
    margen_30 = df.get("margen_a30", pd.Series([None])).iloc[0]
    analisis = df.get("analisis_margen", pd.Series(["Sin análisis"])).iloc[0]
    estrategia = df.get("estrategia", pd.Series(["No definida"])).iloc[0]
    prioridad = df.get("prioridad", pd.Series(["N/A"])).iloc[0]

    # Métricas de margen
    col1, col2, col3 = st.columns(3)

    with col1:
        if margen_all is not None:
            st.metric("📊 Margen Global", f"{margen_all:.1f}%")
    
    with col2:
        if margen_90 is not None:
            st.metric("📆 Margen 90 días", f"{margen_90:.1f}%")
    
    with col3:
        if margen_30 is not None:
            st.metric("🗓️ Margen 30 días", f"{margen_30:.1f}%")

    st.markdown("---")

    # Análisis y estrategia
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🧠 Análisis de Margen")
        st.info(analisis)
    
    with col2:
        st.markdown("#### 🎯 Estrategia y Prioridad")
        st.write(f"**Estrategia Recomendada:** {estrategia}")
        st.write(f"**Prioridad:** {prioridad}")


def tab_estacionalidad(df):
    """Análisis de estacionalidad del artículo"""
    st.markdown("### 📊 Estacionalidad del Artículo")

    # Métricas principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'mes_pico' in df.columns:
            st.metric("📆 Mes Pico", df["mes_pico"].iloc[0].capitalize())
    
    with col2:
        if 'mes_bajo' in df.columns:
            st.metric("📉 Mes Bajo", df["mes_bajo"].iloc[0].capitalize())
    
    with col3:
        if 'ranking_mes' in df.columns:
            st.metric("📊 Nivel Mensual", df["ranking_mes"].iloc[0])

    st.markdown("---")

    # Análisis detallado
    if 'mes_actual' in df.columns:
        contraste = df["mes_actual"].iloc[0]
        st.write(f"**📈 Contraste Relativo Mensual:** {contraste:.2f}%")
    
    if 'meses_act_estac' in df.columns:
        meses_activos = df["meses_act_estac"].iloc[0]
        st.write(f"**📅 Meses Activos Estacionalidad:** {meses_activos}")

        # Interpretación
        if 'mes_actual' in df.columns:
            contraste = df["mes_actual"].iloc[0]
            
            if contraste > 30 and meses_activos <= 4:
                interpretacion = "🌞 Alta estacionalidad: ventas concentradas en pocos meses"
                color = "warning"
            elif contraste > 20:
                interpretacion = "📈 Estacionalidad moderada"
                color = "info"
            else:
                interpretacion = "📉 Estacionalidad baja o estable"
                color = "success"
            
            if color == "warning":
                st.warning(f"**🔍 Interpretación:** {interpretacion}")
            elif color == "info":
                st.info(f"**🔍 Interpretación:** {interpretacion}")
            else:
                st.success(f"**🔍 Interpretación:** {interpretacion}")