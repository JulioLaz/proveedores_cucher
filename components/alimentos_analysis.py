"""
============================================================
MÓDULO: Análisis Detallado de Alimentos
============================================================
Análisis de IEU, matriz portfolio y acciones de compra/venta
para la familia Alimentos

Autor: Julio Lazarte
Fecha: Diciembre 2024
============================================================
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import time
from utils.ranking_proveedores import crear_excel_ranking, generar_nombre_archivo
from components.global_dashboard_cache import process_ranking_detallado_alimentos


def calcular_metricas_ieu(df):
    """
    Calcula IEU y asigna acciones concretas por proveedor
    """
    # Agrupar por proveedor
    df_prov = df.groupby(['Ranking', 'ID Proveedor', 'Proveedor']).agg({
        '% Participación Ventas': 'first',
        'Venta Total Proveedor': 'first',
        'Utilidad Proveedor': 'first',
        'Rentabilidad % Proveedor': 'first',
        'Costo Exceso Proveedor': 'first',
        'Artículos Proveedor': 'first'
    }).reset_index()
    
    # Calcular % Participación Utilidad
    df_prov['% Participación Utilidad'] = (
        df_prov['Utilidad Proveedor'] / df_prov['Utilidad Proveedor'].sum() * 100
    ).round(2)
    
    # Calcular IEU
    df_prov['IEU'] = (
        df_prov['% Participación Utilidad'] / df_prov['% Participación Ventas']
    ).round(2)
    
    # === ASIGNAR ACCIONES CONCRETAS ===
    def asignar_accion(row):
        ieu = row['IEU']
        exceso = row['Costo Exceso Proveedor']
        venta = row['Venta Total Proveedor']
        rentabilidad = row['Rentabilidad % Proveedor']
        
        # 🚨 CRÍTICO: Exceso > Ventas
        if exceso > venta:
            return "🚨 LIQUIDAR: Exceso crítico"
        
        # 🔴 IEU < 0.8: Muy ineficiente
        if ieu < 0.8:
            if exceso > 0:
                return "🔴 DESCONTINUAR: Bajo margen + exceso"
            else:
                return "🔴 REDUCIR: Ocupa espacio sin rendir"
        
        # ⚠️ IEU 0.8-1.0: Bajo rendimiento
        elif ieu < 1.0:
            if rentabilidad < 25:
                return "⚠️ RENEGOCIAR: Pedir mejor margen"
            else:
                return "⚠️ REVISAR: Solo da volumen"
        
        # ✅ IEU 1.0-1.2: Normal
        elif ieu < 1.2:
            if exceso > venta * 0.3:
                return "⚡ PROMOCIONAR: Liberar stock"
            else:
                return "✅ MANTENER: Surtido equilibrado"
        
        # 🌟 IEU >= 1.2: Muy eficiente
        else:
            if exceso > 0:
                return "⚡ POTENCIAR: Promoción + reposición"
            else:
                return "🌟 POTENCIAR: Aumentar exhibición"
    
    df_prov['Acción Recomendada'] = df_prov.apply(asignar_accion, axis=1)
    
    # Categoría de acción (para colorear gráficos)
    def categoria_accion(accion):
        if '🚨' in accion or '🔴' in accion:
            return 'Crítico'
        elif '⚠️' in accion:
            return 'Revisar'
        elif '⚡' in accion:
            return 'Promocionar'
        elif '🌟' in accion:
            return 'Potenciar'
        else:
            return 'Mantener'
    
    df_prov['Categoría'] = df_prov['Acción Recomendada'].apply(categoria_accion)
    
    return df_prov

def crear_scatter_portfolio(df_analisis):
    """
    Matriz Portfolio: Rentabilidad vs Participación
    """
    # Explicación clara del análisis
    with st.expander("ℹ️ ¿Qué muestra esta matriz y cómo interpretarla?", expanded=False):
        st.markdown("""
        ### 📊 Matriz Portfolio de Proveedores
        
        **¿Qué representa este gráfico?**
        - Cada **burbuja** es un proveedor de Alimentos
        - **Eje horizontal (X)**: % de participación en las ventas totales
        - **Eje vertical (Y)**: Rentabilidad % del proveedor
        - **Tamaño de la burbuja**: Costo del exceso de stock (más grande = más dinero inmovilizado)
        - **Color**: Acción recomendada según el análisis
        
        **¿Cómo lo interpreto?**
        
        **Cuadrante Superior Derecho** (🌟 POTENCIAR):
        - Alta venta + Alto margen = **Tus mejores proveedores**
        - Acción: Asegurar stock, mejor ubicación en góndola, nunca romper stock
        
        **Cuadrante Superior Izquierdo** (⚡ PROMOCIONAR):
        - Baja venta + Alto margen = **Productos rentables pero con poca rotación**
        - Acción: Si tienen exceso → promoción para liberar stock. Si no tienen exceso → revisar si el producto es conocido
        
        **Cuadrante Inferior Derecho** (⚠️ RENEGOCIAR):
        - Alta venta + Bajo margen = **Generadores de tráfico pero poco rentables**
        - Acción: Pedir mejores condiciones al proveedor, o usar como "gancho" en folletos
        
        **Cuadrante Inferior Izquierdo** (🔴 REDUCIR/DESCONTINUAR):
        - Baja venta + Bajo margen = **Candidatos a eliminar del surtido**
        - Acción: Reducir variedades o eliminar si no aportan valor estratégico
        
        **⚠️ BURBUJAS MUY GRANDES = ALERTA:**
        - Indican mucho dinero parado en stock
        - Acción inmediata: Revisar por qué hay tanto exceso y tomar medidas
        
        **Líneas grises punteadas:**
        - Marcan el promedio de rentabilidad y participación
        - Te ayudan a comparar cada proveedor con el promedio de la categoría
        """)
    
    fig = px.scatter(
        df_analisis,
        x='% Participación Ventas',
        y='Rentabilidad % Proveedor',
        size='Costo Exceso Proveedor',
        color='Categoría',
        hover_data={
            'Proveedor': True,
            'IEU': ':.2f',
            'Venta Total Proveedor': ':$,.0f',
            'Utilidad Proveedor': ':$,.0f',
            'Costo Exceso Proveedor': ':$,.0f',
            'Acción Recomendada': True,
            '% Participación Ventas': ':.2f%',
            'Rentabilidad % Proveedor': ':.2f%'
        },
        color_discrete_map={
            'Crítico': '#ff0000',
            'Revisar': '#ff9500',
            'Promocionar': '#ffcc00',
            'Mantener': '#4caf50',
            'Potenciar': '#2196f3'
        },
        title='📊 Matriz Portfolio: Rentabilidad vs Participación en Ventas',
        labels={
            '% Participación Ventas': '% Participación en Ventas',
            'Rentabilidad % Proveedor': 'Rentabilidad %'
        }
    )
    
    # Líneas de referencia
    fig.add_hline(y=df_analisis['Rentabilidad % Proveedor'].mean(), 
                  line_dash="dash", line_color="gray", 
                  annotation_text="Rentabilidad Promedio")
    
    fig.add_vline(x=df_analisis['% Participación Ventas'].mean(), 
                  line_dash="dash", line_color="gray",
                  annotation_text="Participación Promedio")
    
    fig.update_layout(height=600)
    
    st.plotly_chart(fig, use_container_width=True)


def crear_grafico_ieu(df_analisis):
    """
    Gráfico de barras: IEU por proveedor
    """
    # Explicación clara del análisis
    with st.expander("ℹ️ ¿Qué es el IEU y cómo se interpreta?", expanded=False):
        st.markdown("""
        ### 📈 Índice de Eficiencia de Utilidad (IEU)
        
        **¿Qué es el IEU?**
        
        El IEU mide si un proveedor **"merece" el espacio** que ocupa en tu negocio.
        
        **Fórmula:**
```
        IEU = % Participación en Utilidad / % Participación en Ventas
```
        
        **Ejemplo práctico:**
        - Proveedor A: Tiene el 10% de las ventas pero genera el 15% de la utilidad → IEU = 1.5 ✅
        - Proveedor B: Tiene el 10% de las ventas pero solo genera el 5% de la utilidad → IEU = 0.5 ❌
        
        **¿Cómo interpreto el IEU?**
        
        | Rango IEU | Significado | Acción |
        |-----------|-------------|--------|
        | **IEU ≥ 1.2** | 🌟 **Super eficiente** - Te da más ganancia que la venta que genera | **POTENCIAR**: Aumentar exhibición, asegurar stock, promocionar |
        | **IEU 1.0 - 1.2** | ✅ **Equilibrado** - Genera utilidad proporcional a su venta | **MANTENER**: Seguir con el surtido actual |
        | **IEU 0.8 - 1.0** | ⚠️ **Bajo rendimiento** - Da más volumen que ganancia | **REVISAR**: Renegociar margen o reducir variedades |
        | **IEU < 0.8** | 🔴 **Muy ineficiente** - Ocupa espacio sin aportar margen | **REDUCIR/DESCONTINUAR**: Evaluar salida del surtido |
        
        **¿Por qué es importante?**
        
        En retail, el espacio en góndola es **ORO**. El IEU te dice si estás usando bien ese espacio:
        - Un proveedor con IEU bajo está "desperdiciando" lugar que podría ocupar uno más rentable
        - Un proveedor con IEU alto merece más espacio porque aprovecha mejor cada cm² de góndola
        
        **💡 Tip de Comprador:**
        - Ordena tu góndola poniendo a la **altura de los ojos** los productos con IEU > 1.2
        - Los productos con IEU < 0.8 van arriba o abajo (peor visibilidad)
        
        **La línea vertical en 1.0:**
        - Marca el punto de equilibrio
        - A la derecha = eficientes, a la izquierda = ineficientes
        """)
    
    df_sorted = df_analisis.sort_values('IEU', ascending=True)
    
    fig = px.bar(
        df_sorted,
        x='IEU',
        y='Proveedor',
        color='Categoría',
        orientation='h',
        hover_data={
            'IEU': ':.2f',
            '% Participación Ventas': ':.2f%',
            '% Participación Utilidad': ':.2f%',
            'Acción Recomendada': True
        },
        color_discrete_map={
            'Crítico': '#ff0000',
            'Revisar': '#ff9500',
            'Promocionar': '#ffcc00',
            'Mantener': '#4caf50',
            'Potenciar': '#2196f3'
        },
        title='📈 Índice de Eficiencia de Utilidad (IEU) por Proveedor'
    )
    
    # Línea en IEU = 1.0
    fig.add_vline(x=1.0, line_dash="dash", line_color="gray",
                  annotation_text="IEU = 1.0 (Equilibrio)")
    
    fig.update_layout(height=max(400, len(df_sorted) * 30))
    
    st.plotly_chart(fig, use_container_width=True)


def mostrar_alertas_criticas(df_analisis):
    """
    Tabla con alertas críticas y acciones prioritarias
    """
    # Explicación clara del análisis
    with st.expander("ℹ️ ¿Qué son las alertas críticas y qué hacer con ellas?", expanded=False):
        st.markdown("""
        ### ⚠️ Alertas Críticas - Proveedores que Requieren Acción Inmediata
        
        **¿Qué muestra esta tabla?**
        
        Esta tabla filtra automáticamente los proveedores con **problemas que necesitan decisión urgente**:
        - 🚨 **Críticos**: Situaciones de riesgo financiero (exceso mayor que ventas)
        - 🔴 **Descontinuar**: Proveedores muy ineficientes (IEU < 0.8)
        - ⚠️ **Revisar**: Proveedores con bajo rendimiento (IEU 0.8-1.0)
        
        **¿Qué significan las acciones?**
        
        | Acción | ¿Qué hacer? | ¿Por qué? |
        |--------|-------------|-----------|
        | 🚨 **LIQUIDAR: Exceso crítico** | Promoción agresiva (2x1, 30% OFF) hasta normalizar stock | Tienes más dinero parado que lo que vendes en un mes |
        | 🔴 **DESCONTINUAR** | Dejar de comprar y agotar stock actual | Bajo margen + exceso = ocupa capital sin generar ganancia |
        | 🔴 **REDUCIR** | Mantener solo 1-2 variedades más vendidas | Ocupa espacio de góndola sin aportar rentabilidad |
        | ⚠️ **RENEGOCIAR** | Pedir bonificaciones o mejor margen al proveedor | El producto vende pero con poco margen |
        | ⚠️ **REVISAR** | Analizar si el cliente lo pide o puede reemplazarse | Solo aporta volumen, no ganancia |
        
        **¿Cómo priorizo las acciones?**
        
        **1. PRIMERO** - 🚨 Exceso crítico:
        - Es dinero que no está trabajando
        - Afecta tu flujo de caja
        - Puede vencerse o quedar obsoleto
        
        **2. SEGUNDO** - 🔴 IEU muy bajo con exceso:
        - Combinas dos problemas: ineficiencia + capital parado
        - Liberar este stock permite comprar productos más rentables
        
        **3. TERCERO** - 🔴 IEU muy bajo sin exceso:
        - No renovar pedidos
        - Esperar a que se agote naturalmente
        
        **4. DESPUÉS** - ⚠️ IEU bajo:
        - Renegociar en la próxima compra
        - No es urgente pero debe abordarse
        
        **💡 Tip:** 
        - Si la tabla está vacía = ¡Excelente! Todos tus proveedores están bien gestionados
        - Si tienes muchas alertas = Prioriza por "Costo Exceso" (de mayor a menor)
        
        **📞 Caso práctico:**
        
        *"Proveedor X tiene $500,000 en exceso con IEU 0.6"*
        
        Acción:
        1. Llamar al proveedor para devolver mercadería o pedir bonificación especial
        2. Si no acepta → Liquidación interna (ej: "Lleve 3, pague 2")
        3. Una vez normalizado el stock → Reducir variedades a solo las 2 más vendidas
        4. No volver a comprar hasta revisar margen con comercial
        """)
    
    # Filtrar solo críticos y revisar
    df_alertas = df_analisis[
        df_analisis['Categoría'].isin(['Crítico', 'Revisar'])
    ].sort_values('IEU')
    
    if len(df_alertas) == 0:
        st.success("✅ No hay alertas críticas. Todos los proveedores tienen buen desempeño.")
    else:
        st.warning(f"⚠️ {len(df_alertas)} proveedores requieren atención inmediata:")
        
        # Mostrar tabla
        df_display = df_alertas[[
            'Proveedor', 'IEU', '% Participación Ventas', 
            'Rentabilidad % Proveedor', 'Costo Exceso Proveedor',
            'Acción Recomendada'
        ]].copy()
        
        # Formatear
        df_display['Costo Exceso Proveedor'] = df_display['Costo Exceso Proveedor'].apply(
            lambda x: f"${x:,.0f}"
        )
        df_display['% Participación Ventas'] = df_display['% Participación Ventas'].apply(
            lambda x: f"{x:.2f}%"
        )
        df_display['Rentabilidad % Proveedor'] = df_display['Rentabilidad % Proveedor'].apply(
            lambda x: f"{x:.2f}%"
        )
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )

def format_millones(valor):
    """Formatea valores en millones"""
    return f"${valor/1_000_000:.1f} mll"


def show_alimentos_analysis(df_proveedores, df_ventas, df_presupuesto, df_familias, 
                            fecha_desde, fecha_hasta):
    """
    Función principal del análisis de alimentos
    """
    st.markdown("---")
    st.markdown("### 🥗 Análisis Detallado - Familia Alimentos")
    
    # === FILTROS Y DESCARGA ===
    col_filtro, col_descarga = st.columns([2, 1])
    
    with col_filtro:
        # Obtener subfamilias de Alimentos disponibles
        subfamilias_alimentos = df_familias[
            df_familias['familia'].str.strip().str.lower() == 'alimentos'
        ]['subfamilia'].dropna().unique().tolist()
        
        subfamilias_alimentos_seleccionadas = st.multiselect(
            "🥗 Subfamilias de Alimentos a incluir:",
            options=['Todas'] + sorted(subfamilias_alimentos),
            default=['Todas'],
            key='subfamilias_alimentos_analysis'  # ← KEY ÚNICA
        )
    
    # Determinar qué df usar
    if 'Todas' in subfamilias_alimentos_seleccionadas:
        df_para_alimentos = df_proveedores
        filtros_aplicados = False
    else:
        articulos_filtrados = df_familias[
            df_familias['subfamilia'].isin(subfamilias_alimentos_seleccionadas)
        ]['idarticulo'].unique()
        
        df_para_alimentos = df_proveedores[
            df_proveedores['idarticulo'].isin(articulos_filtrados)
        ]
        filtros_aplicados = True
    
    print(f"{'='*80}")
    print("🥗 GENERANDO RANKING DETALLADO ALIMENTOS")
    if 'Todas' in subfamilias_alimentos_seleccionadas:
        print("   📊 TODAS LAS SUBFAMILIAS")
    else:
        print(f"   📊 {len(subfamilias_alimentos_seleccionadas)} SUBFAMILIAS SELECCIONADAS")
    print(f"{'='*80}")
    inicio_detallado = time.time()
    
    ranking_detallado_alimentos = process_ranking_detallado_alimentos(
        df_para_alimentos,
        df_ventas,
        df_presupuesto,
        df_familias
    )
    
    tiempo_detallado = time.time() - inicio_detallado
    
    # === VALIDAR SI HAY DATOS ===
    if ranking_detallado_alimentos.empty:
        st.warning("⚠️ No se encontraron datos de la familia 'Alimentos' en el período seleccionado.")
        print(f"   ⚠️ DataFrame vacío retornado")
        print(f"{'='*80}\n")
        return
    
    print(f"   ✅ Ranking detallado generado")
    print(f"   📦 Artículos: {len(ranking_detallado_alimentos):,}")
    print(f"   👥 Proveedores: {ranking_detallado_alimentos['Proveedor'].nunique()}")
    
    subfamilias_count = ranking_detallado_alimentos['Subfamilia'].nunique() if 'Subfamilia' in ranking_detallado_alimentos.columns else 0
    print(f"   🥗 Subfamilias: {subfamilias_count}")
    print(f"   💰 Venta total: ${ranking_detallado_alimentos['Venta Artículo'].sum():,.0f}")
    print(f"   ⏱️  Tiempo: {tiempo_detallado:.2f}s")
    print(f"{'='*80}\n")
    
    # === BOTÓN DE DESCARGA ===
    with col_descarga:
        output_detallado = crear_excel_ranking(
            ranking_detallado_alimentos,
            str(fecha_desde),
            str(fecha_hasta),
            filtros_aplicados=filtros_aplicados,
            subfamilias_activas=subfamilias_alimentos_seleccionadas if filtros_aplicados else None
        )
        nombre_archivo_detallado = generar_nombre_archivo("ranking_detallado_alimentos")
        
        st.download_button(
            label=f"📥 Descargar Excel\n({len(ranking_detallado_alimentos):,} artículos)",
            data=output_detallado,
            file_name=nombre_archivo_detallado,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="secondary"
        )
    
    # === ANÁLISIS INTERACTIVO ===
    st.markdown("---")
    
    # 1. CALCULAR MÉTRICAS IEU
    df_analisis = calcular_metricas_ieu(ranking_detallado_alimentos)
    
    # 2. MÉTRICAS RESUMEN
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ieu_promedio = df_analisis['IEU'].mean()
        st.metric(
            "IEU Promedio",
            f"{ieu_promedio:.2f}",
            delta="Eficiente" if ieu_promedio > 1.0 else "Revisar",
            delta_color="normal" if ieu_promedio > 1.0 else "inverse"
        )
    
    with col2:
        alertas = df_analisis[df_analisis['Categoría'].isin(['Crítico', 'Revisar'])].shape[0]
        st.metric("Proveedores a Revisar", alertas)
    
    with col3:
        exceso_critico = (df_analisis['Costo Exceso Proveedor'] > df_analisis['Venta Total Proveedor']).sum()
        st.metric("Con Exceso Crítico", exceso_critico)
    
    with col4:
        eficientes = (df_analisis['IEU'] >= 1.2).sum()
        st.metric("Proveedores Eficientes", eficientes)
    
    # 3. GRÁFICOS Y TABLAS
    tab1, tab2, tab3 = st.tabs(["📊 Matriz Portfolio", "📈 IEU por Proveedor", "⚠️ Alertas Críticas"])
    
    with tab1:
        crear_scatter_portfolio(df_analisis)
    
    with tab2:
        crear_grafico_ieu(df_analisis)
    
    with tab3:
        mostrar_alertas_criticas(df_analisis)