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
from utils.telegram_notifier import send_telegram_alert

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

    # ✅ AGREGAR ESTO: Limpiar infinitos y NaN
    df_prov['IEU'] = df_prov['IEU'].replace([float('inf'), -float('inf')], 0)
    df_prov['IEU'] = df_prov['IEU'].fillna(0)

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
    Mapa de Proveedores: Rentabilidad vs Participación
    """
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
        title='📊 Mapa de Proveedores: Rentabilidad vs Participación<br><sub>⚠️ Tamaño del círculo = Costo de Exceso de Stock</sub>',
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
    
    st.plotly_chart(fig, width='stretch')
    
    # EXPANDER UNIFICADO - EXPLICACIÓN COMPLETA
    with st.expander("📖 Guía Completa: Cómo interpretar el Mapa de Proveedores", expanded=False):
        st.markdown("""
        ## 🎯 ¿Qué muestra este gráfico?
        
        Este es un **mapa estratégico** que te ayuda a tomar decisiones sobre cada proveedor combinando **3 variables clave**:
        
        | Elemento | Qué representa | Cómo se ve |
        |----------|----------------|------------|
        | **Posición Horizontal (→)** | % Participación en Ventas | Más a la derecha = Vende más |
        | **Posición Vertical (↑)** | Rentabilidad % del proveedor | Más arriba = Más rentable |
        | **Tamaño del círculo (⭕)** | Costo del Exceso de Stock | Más grande = Más plata parada |
        | **Color del círculo (🎨)** | Categoría/Acción recomendada | Según análisis IEU |
        
        **Líneas grises punteadas**: Marcan el promedio de rentabilidad y participación (te ayudan a comparar cada proveedor contra el promedio de Alimentos).
        
        ---
        
        ## 🎨 PASO 1: Entender los COLORES (Categoría del Proveedor)
        
        El color te dice **qué tan urgente** es actuar sobre ese proveedor según su IEU (Índice de Eficiencia de Uso):
        
        - 🔴 **ROJO (Crítico)**: Exceso de stock > Ventas del período → **LIQUIDAR INMEDIATAMENTE**
        - 🟠 **NARANJA (Revisar)**: IEU bajo (0.8 - 1.0) → **RENEGOCIAR o REDUCIR**
        - 🟡 **AMARILLO (Promocionar)**: Buen margen pero con exceso → **LIBERAR STOCK con promoción**
        - 🟢 **VERDE (Mantener)**: Equilibrado, sin problemas → **SEGUIR IGUAL**
        - 🔵 **AZUL (Potenciar)**: IEU alto (>1.2) → **AUMENTAR EXHIBICIÓN/COMPRAR MÁS**
        
        ---
        
        ## 📍 PASO 2: Entender la POSICIÓN (Cuadrantes)
        
        El gráfico se divide en **4 cuadrantes** según rentabilidad y participación en ventas:
        
        ### 🌟 **CUADRANTE SUPERIOR DERECHO** (Alta Venta + Alta Rentabilidad)
        **→ TUS MEJORES PROVEEDORES**
        
        - ⚪ **Círculo PEQUEÑO**: ¡PERFECTO! Vende mucho, gana bien, sin exceso
          - ✅ **Acción**: Mantener, asegurar nunca romper stock, prioridad absoluta
        
        - ⚪ **Círculo GRANDE**: Excelente proveedor pero compraste de más
          - ⚠️ **Acción**: Promoción suave para normalizar exceso, NO dejar de comprar
        
        ---
        
        ### ⚡ **CUADRANTE SUPERIOR IZQUIERDO** (Baja Venta + Alta Rentabilidad)
        **→ PRODUCTOS RENTABLES PERO DE NICHO**
        
        - ⚪ **Círculo PEQUEÑO**: Producto rentable, baja rotación natural (normal)
          - ✅ **Acción**: Mantener en surtido, comprar poco y frecuente
        
        - ⚪ **Círculo GRANDE**: Producto rentable pero sobrestockeado
          - 💡 **Acción**: Promoción 2x1 o descuento para liberar capital
        
        ---
        
        ### ⚠️ **CUADRANTE INFERIOR DERECHO** (Alta Venta + Baja Rentabilidad)
        **→ GENERADORES DE TRÁFICO POCO RENTABLES**
        
        - ⚪ **Círculo PEQUEÑO**: "Gancho" de clientes, necesario pero poco rentable
          - 🔄 **Acción**: Renegociar margen o usar en folletos para atraer clientes
        
        - ⚪ **Círculo GRANDE**: Vende mucho pero no ganas Y tenés exceso
          - 🚨 **Acción**: Liquidar exceso YA, renegociar condiciones URGENTE
        
        ---
        
        ### 🔴 **CUADRANTE INFERIOR IZQUIERDO** (Baja Venta + Baja Rentabilidad)
        **→ CANDIDATOS A ELIMINAR**
        
        - ⚪ **Círculo PEQUEÑO**: Producto marginal pero sin riesgo financiero
          - 📉 **Acción**: Dejar agotar naturalmente, NO reponer
        
        - 🚨 **Círculo GRANDE**: ¡LO PEOR! No vende, no gana, capital parado
          - ❌ **Acción**: LIQUIDAR URGENTE (hasta 50% OFF), descontinuar INMEDIATO
        
        ---
        
        ## 💡 PASO 3: Combinar COLOR + POSICIÓN + TAMAÑO
        
        ### 📌 Ejemplo 1: Círculo 🔵 AZUL + Superior Derecha + GRANDE
        - **Interpretación**: Top performer (IEU alto) con exceso de stock
        - **Acción**: Hacer promoción para vender más rápido, producto excelente pero te pasaste comprando
        - **Urgencia**: MEDIA (es buen producto, solo ajustar cantidad)
        
        ### 📌 Ejemplo 2: Círculo 🔴 ROJO + Inferior Izquierda + GRANDE
        - **Interpretación**: ¡DESASTRE TOTAL! Poco margen + Poca venta + Mucho exceso
        - **Acción**: Liquidar hasta 50% OFF, descontinuar INMEDIATO, liberar capital
        - **Urgencia**: MÁXIMA (triple problema)
        
        ### 📌 Ejemplo 3: Círculo 🟢 VERDE + Superior Derecha + PEQUEÑO
        - **Interpretación**: Proveedor IDEAL (equilibrado, rentable, sin exceso)
        - **Acción**: NO cambiar nada, asegurar disponibilidad constante
        - **Urgencia**: NINGUNA (todo bien)
        
        ### 📌 Ejemplo 4: Círculo 🟡 AMARILLO + Superior Izquierda + GRANDE
        - **Interpretación**: Producto muy rentable pero con mucho exceso y poca venta
        - **Acción**: Promoción agresiva 2x1 + Mejor ubicación en góndola
        - **Urgencia**: ALTA (liberar capital parado)
        
        ---
        
        ## ⚡ REGLA DE ORO (Qué mirar PRIMERO)
        
        ### 🚨 ALERTA MÁXIMA: Círculo ROJO + GRANDE en cualquier posición
        → **ACCIÓN INMEDIATA** requerida (liquidar stock)
        
        ### 🔍 ORDEN DE REVISIÓN sugerido:
        
        1. **ROJOS GRANDES**: Liquidar urgente
        2. **NARANJAS GRANDES en cuadrante inferior izquierdo**: Descontinuar
        3. **AMARILLOS GRANDES**: Promocionar para liberar capital
        4. **AZULES en superior derecha**: Potenciar (aumentar exhibición)
        5. **VERDES**: Mantener sin cambios
        
        ---
        
        ## 📊 Resumen Visual Rápido
```
        ALTA RENTABILIDAD
              ↑
              |
        ⚡ PROMOCIONAR  |  🌟 POTENCIAR
        (Si círculo     |  (Tu mejor
         grande)        |   zona)
              |         |
        ------+-------------------→ ALTA VENTA
              |         |
        🔴 DESCONTINUAR |  ⚠️ RENEGOCIAR
        (Eliminar si    |  (Gancho de
         círculo grande)|   tráfico)
              |
        BAJA RENTABILIDAD
```
        
        ---
        
        ### 🎯 En resumen:
        - **COLOR** = Qué tan urgente actuar (según IEU)
        - **POSICIÓN** = Rentabilidad vs Volumen (dónde está parado estratégicamente)
        - **TAMAÑO** = Dinero inmovilizado (qué tan grave es el exceso)
        
        **La mejor decisión combina los 3 elementos juntos.**
        """)

def crear_scatter_portfolio_00(df_analisis):
    """
    Mapa de Proveedores: Rentabilidad vs Participación
    """
    # Explicación clara del análisis
    with st.expander("ℹ️ ¿Qué muestra este mapa y cómo interpretarlo?", expanded=False):
        st.markdown("""
        ### 📊 Mapa de Proveedores (Cuadrantes de Decisión)
        
        **¿Qué representa este gráfico?**
        - Cada **círculo** es un proveedor de Alimentos
        - **Posición horizontal (→)**: % de participación en las ventas totales
        - **Posición vertical (↑)**: Rentabilidad % del proveedor
        - **TAMAÑO del círculo**: Costo del exceso de stock
          - ⚠️ **Círculo MÁS GRANDE** = Más dinero inmovilizado en exceso
          - ✅ **Círculo MÁS PEQUEÑO** = Poco o nada de exceso
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
        
        **⚠️ CÍRCULOS MUY GRANDES = ALERTA DE CAPITAL:**
        - Indican mucho dinero parado en stock que no rota
        - Acción inmediata: Revisar por qué hay tanto exceso y liquidar
        - Ejemplo: Un círculo grande en cuadrante inferior = Doble problema (poco rentable + capital parado)
        
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
        title='📊 Mapa de Proveedores: Rentabilidad vs Participación<br><sub>⚠️ Tamaño del círculo = Costo de Exceso de Stock</sub>',  # ← AGREGADO
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
    
    st.plotly_chart(fig, width='stretch')
           
    # ← NOTA FINAL COMPLETA: CUADRANTES + TAMAÑOS + COLORES
    with st.expander("ℹ️ Cómo interpretarlo el gráfico por cuadrantes?", expanded=False):
        st.markdown("""
        ### 💡 Guía Completa de Interpretación
        #### 🎨 **COLORES (Categoría del Proveedor)**
        
        - 🔴 **Rojo (Crítico)**: Exceso mayor que ventas → Liquidar inmediatamente
        - 🟠 **Naranja (Revisar)**: IEU bajo (0.8-1.0) → Renegociar o reducir
        - 🟡 **Amarillo (Promocionar)**: Buen margen con exceso → Liberar stock
        - 🟢 **Verde (Mantener)**: Equilibrado, sin problemas → Seguir igual
        - 🔵 **Azul (Potenciar)**: IEU alto (>1.2) → Aumentar exhibición
        
        #### 📍 **POSICIÓN (Cuadrante) + TAMAÑO (Exceso de Stock)**
        
        **CUADRANTE SUPERIOR DERECHO** (Alta Venta + Alto Margen):
        - ⚪ **Círculo pequeño**: ¡Perfecto! Tu mejor proveedor sin problemas
        → Acción: Mantener, asegurar nunca romper stock
        - ⚪ **Círculo grande**: Excelente proveedor pero compraste de más
        → Acción: Promoción suave para normalizar exceso, no dejar de comprar
        
        **CUADRANTE SUPERIOR IZQUIERDO** (Baja Venta + Alto Margen):
        - ⚪ **Círculo pequeño**: Producto rentable de nicho, baja rotación natural
        → Acción: Mantener en surtido, comprar poco y frecuente
        - ⚪ **Círculo grande**: Producto rentable pero sobrestockeado
        → Acción: Promoción 2x1 o descuento para liberar capital
        
        **CUADRANTE INFERIOR DERECHO** (Alta Venta + Bajo Margen):
        - ⚪ **Círculo pequeño**: Gancho de tráfico, necesario pero poco rentable
        → Acción: Renegociar margen o usar en folletos para atraer clientes
        - ⚪ **Círculo grande**: Vende mucho pero no ganas y tenés exceso
        → Acción: Liquidar exceso YA, renegociar condiciones urgente
        
        **CUADRANTE INFERIOR IZQUIERDO** (Baja Venta + Bajo Margen):
        - ⚪ **Círculo pequeño**: Producto marginal pero sin riesgo
        → Acción: Dejar agotar naturalmente, no reponer
        - 🚨 **Círculo grande**: ¡LO PEOR! No vende, no gana, capital parado
        → Acción: LIQUIDAR URGENTE (hasta 50% OFF), descontinuar inmediato
        
        #### 📊 **CÓMO COMBINAR COLOR + POSICIÓN + TAMAÑO**
        
        **Ejemplo 1:** Círculo 🔵 azul (Potenciar) + Superior Derecha + Grande
        - Interpretación: Top performer con exceso
        - Acción: Hacer promoción para vender más rápido, no hay problema de rentabilidad
        
        **Ejemplo 2:** Círculo 🔴 rojo (Crítico) + Inferior Izquierda + Grande
        - Interpretación: ¡DESASTRE! Poco margen, poca venta, mucho exceso
        - Acción: Liquidar hasta 50% OFF, descontinuar inmediato, liberar capital
        
        **Ejemplo 3:** Círculo 🟢 verde (Mantener) + Superior Derecha + Pequeño
        - Interpretación: Proveedor ideal
        - Acción: No cambiar nada, asegurar disponibilidad
        
        ---
        
        **Resumen rápido:**
        - **Color** = Categoría de acción (qué tan urgente)
        - **Posición** = Rentabilidad vs Volumen (dónde está parado)
        - **Tamaño** = Dinero inmovilizado (qué tan grave es el exceso)
        
        ⚠️ **Regla de oro**: Círculo ROJO + GRANDE en cualquier posición = ACCIÓN INMEDIATA
        """)

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
    
    st.plotly_chart(fig, width='stretch')


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
            width='stretch',
            hide_index=True
        )

def format_millones(valor):
    """Formatea valores en millones"""
    return f"${valor/1_000_000:.1f} mll"


# def show_alimentos_analysis(df_proveedores, df_ventas, df_presupuesto, df_familias, 
#                             fecha_desde, fecha_hasta):
def show_alimentos_analysis(df_proveedores, df_ventas, df_presupuesto, df_familias,
                           fecha_desde, fecha_hasta, subfamilias_preseleccionadas=None, familia_seleccionada='Alimentos'):    
    """
    Función principal del análisis de alimentos
    """
    # Diccionario de emojis por familia
    emojis_familia = {
        'alimentos': '🥗',
        'bebidas': '🥤',
        'limpieza': '🧹',
        'perfumería': '💄',
        'bazar': '🏺',
        'textil': '👕'
    }
    emoji = emojis_familia.get(familia_seleccionada.lower(), '📦')

   #  st.markdown("---")
   #  st.markdown(f"### {emoji} Análisis Detallado por Familia: {familia_seleccionada}")
    
    # === FILTROS Y DESCARGA ===
   #  col_descarga, col_metric = st.columns([2, 1])
    
   #  with col_filtro:
        # Obtener subfamilias de Alimentos disponibles

        # subfamilias_alimentos = df_familias[
        #     df_familias['familia'].str.strip().str.lower() == 'alimentos'
        # ]['subfamilia'].dropna().unique().tolist()

    subfamilias_familia = df_familias[
            df_familias['familia'].str.strip().str.lower() == familia_seleccionada.lower()  # ← DINÁMICO!
        ]['subfamilia'].dropna().unique().tolist()

        # subfamilias_alimentos = df_familias['subfamilia'] .dropna() .unique() .tolist()

        # subfamilias_familia_seleccionadas = st.multiselect(
        #     "🥗 Subfamilias de Alimentos a incluir:",
        #     options=['Todas'] + sorted(subfamilias_alimentos),
        #     default=['Todas'],
        #     key='subfamilias_alimentos_analysis'  # ← KEY ÚNICA
        # )
    # Si ya vienen preseleccionadas, usarlas; sino, mostrar el selector
    # if subfamilias_preseleccionadas is not None:
    #     # Usar las ya seleccionadas arriba
    #     subfamilias_familia_seleccionadas = subfamilias_preseleccionadas
    #     st.info(f"📂 Usando subfamilias seleccionadas: {len(subfamilias_preseleccionadas)}")
    # else:
    #     # Mostrar selector independiente
    #     subfamilias_familia_seleccionadas = st.multiselect(
    #         "🥗 Subfamilias de Alimentos a incluir:",
    #         options=['Todas'] + sorted(subfamilias_alimentos),
    #         default=['Todas']
    #         # key='subfamilias_alimentos_analysis_secondary'
    #     )

    # Si ya vienen preseleccionadas, usarlas; sino, mostrar el selector
    if subfamilias_preseleccionadas is not None:
        # Usar las ya seleccionadas arriba
        subfamilias_familia_seleccionadas = subfamilias_preseleccionadas
      #   st.info(f"📂 Usando subfamilias seleccionadas: {len(subfamilias_preseleccionadas)}")
    else:
        
        # Mostrar selector independiente
        subfamilias_familia_seleccionadas = st.multiselect(
            f"{emoji} Subfamilias de {familia_seleccionada} a incluir:",
            options=['Todas'] + sorted(subfamilias_familia),  # ← AHORA SÍ EXISTE!
            default=['Todas']
        )

    # Determinar qué df usar
    if 'Todas' in subfamilias_familia_seleccionadas:
        # Filtrar solo por familia (todas las subfamilias de esta familia)
        articulos_familia = df_familias[
            df_familias['familia'].str.strip().str.lower() == familia_seleccionada.lower()
        ]['idarticulo'].unique()
        
        df_para_familia = df_proveedores[
            df_proveedores['idarticulo'].isin(articulos_familia)
        ]
        filtros_aplicados = False
    else:
        # Filtrar solo las subfamilias seleccionadas de esta familia
        articulos_filtrados = df_familias[
            (df_familias['familia'].str.strip().str.lower() == familia_seleccionada.lower()) &
            (df_familias['subfamilia'].isin(subfamilias_familia_seleccionadas))
        ]['idarticulo'].unique()
        
        df_para_familia = df_proveedores[
            df_proveedores['idarticulo'].isin(articulos_filtrados)
        ]
        filtros_aplicados = True
    
    print(f"{'='*80}")
    print(f"{emoji} GENERANDO RANKING DETALLADO {familia_seleccionada.upper()}")
    if 'Todas' in subfamilias_familia_seleccionadas:
        print("   📊 TODAS LAS SUBFAMILIAS")
    else:
        print(f"   📊 {len(subfamilias_familia_seleccionadas)} SUBFAMILIAS SELECCIONADAS")
    print(f"{'='*80}")
    inicio_detallado = time.time()
    
    ranking_detallado_familia = process_ranking_detallado_alimentos(
        df_para_familia,
        df_ventas,
        df_presupuesto,
        df_familias
    )
    
    tiempo_detallado = time.time() - inicio_detallado
    
    # === VALIDAR SI HAY DATOS ===
    if ranking_detallado_familia.empty:
        st.warning(f"⚠️ No se encontraron datos de la familia '{familia_seleccionada}' en el período seleccionado.")
        print(f"   ⚠️ DataFrame vacío retornado")
        print(f"{'='*80}\n")
        return
    
    print(f"   ✅ Ranking detallado generado")
    print(f"   📦 Artículos: {len(ranking_detallado_familia):,}")
    print(f"   👥 Proveedores: {ranking_detallado_familia['Proveedor'].nunique()}")
    
    subfamilias_count = ranking_detallado_familia['Subfamilia'].nunique() if 'Subfamilia' in ranking_detallado_familia.columns else 0
    print(f"   {emoji} Subfamilias: {subfamilias_count}")
    print(f"   💰 Venta total: ${ranking_detallado_familia['Venta Artículo'].sum():,.0f}")
    print(f"   ⏱️  Tiempo: {tiempo_detallado:.2f}s")
    print(f"{'='*80}\n")
    
    # === BOTÓN DE DESCARGA ===
    # === BOTÓN DE DESCARGA ===
    # === BOTÓN DE DESCARGA ===
    # === BOTÓN DE DESCARGA ===
   #  with col_descarga:
    output_detallado = crear_excel_ranking(
            ranking_detallado_familia,
            str(fecha_desde),
            str(fecha_hasta),
            filtros_aplicados=filtros_aplicados,
            subfamilias_activas=subfamilias_familia_seleccionadas if filtros_aplicados else None
        )
    nombre_archivo_detallado = generar_nombre_archivo("ranking_detallado_familia")
        
   #  descarga_xlsx_alimentos = st.download_button(
   #          label=f"📥 Descargar Excel\n({len(ranking_detallado_familia):,} artículos) - 📂 Usando subfamilias seleccionadas: {len(subfamilias_preseleccionadas)}", #f"📂 Usando subfamilias seleccionadas: {len(subfamilias_preseleccionadas)}"
   #          data=output_detallado,
   #          file_name=nombre_archivo_detallado,
   #          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
   #          width='stretch',
   #          type="secondary"
   #      )

        # Construcción del mensaje detallado
    subfamilias_count = (
            ranking_detallado_familia['Subfamilia'].nunique()
            if 'Subfamilia' in ranking_detallado_familia.columns else 0
        )

    mensaje_detalle = (
            f"📦 Artículos: {len(ranking_detallado_familia):,}\n"
            f"👥 Proveedores: {ranking_detallado_familia['Proveedor'].nunique()}\n"
            f"🥗 Subfamilias: {subfamilias_count}\n"
            f"💰 Venta total: ${ranking_detallado_familia['Venta Artículo'].sum():,.0f}"
        )

   #  if descarga_xlsx_alimentos:  # ✅ Se pulsó el botón
   #              usuario = st.session_state.get('username', 'Usuario desconocido')

   #          # Mensaje principal + detalle 
   #              mensaje = (
   #                  f"<b>👤 USUARIO:</b> {usuario}\n"
   #                  f"🥗 <b>Descarga de Ranking Alimentos</b>\n" 
   #                  f"{mensaje_detalle}"
   #                  )
   #              send_telegram_alert(mensaje, tipo="SUCCESS")

   #  # === ANÁLISIS INTERACTIVO ===
   #  st.markdown("---")
    
    # 1. CALCULAR MÉTRICAS IEU
    df_analisis = calcular_metricas_ieu(ranking_detallado_familia)
    
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
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Mapa de Proveedores",  
        "📈 IEU por Proveedor", 
        "⚠️ Alertas Críticas",
        "🎯 Análisis por Artículo"
    ])

    with tab1:
        st.info("💡 Visualiza dónde están posicionados tus proveedores según rentabilidad y volumen de ventas")
        crear_scatter_portfolio(df_analisis)

    with tab2:
        st.info("💡 Compara la eficiencia de cada proveedor: ¿Genera más ganancia que el espacio que ocupa?")
        crear_grafico_ieu(df_analisis)

    with tab3:
        st.info("💡 Proveedores que necesitan acción inmediata por bajo rendimiento o exceso crítico")
        mostrar_alertas_criticas(df_analisis)

    with tab4:
        st.info("💡 Análisis artículo por artículo: decide qué SKUs potenciar, reducir o descontinuar")
        mostrar_analisis_articulos(ranking_detallado_familia)

    # with tab1:
    #     crear_scatter_portfolio(df_analisis)
    
    # with tab2:
    #     crear_grafico_ieu(df_analisis)
    
    # with tab3:
    #     mostrar_alertas_criticas(df_analisis)

    # with tab4:
    #     mostrar_analisis_articulos(ranking_detallado_familia) 
########################################################################
# ANALISIS POR ARICULO        
########################################################################        

def calcular_metricas_ieu_articulo(df):
    """
    Calcula IEU y asigna acciones concretas POR ARTÍCULO
    """
    # Calcular totales globales
    venta_total_global = df['Venta Artículo'].sum()
    utilidad_total_global = df['Utilidad Artículo'].sum()
    
    # Calcular participaciones por artículo
    df_articulo = df.copy()
    
    df_articulo['% Participación Ventas Artículo'] = (
        df_articulo['Venta Artículo'] / venta_total_global * 100
    ).round(2)
    
    df_articulo['% Participación Utilidad Artículo'] = (
        df_articulo['Utilidad Artículo'] / utilidad_total_global * 100
    ).round(2)
    
    # Calcular IEU por artículo
    df_articulo['IEU Artículo'] = (
        df_articulo['% Participación Utilidad Artículo'] / 
        df_articulo['% Participación Ventas Artículo']
    ).round(2)
    
    # Reemplazar infinitos y NaN
    df_articulo['IEU Artículo'] = df_articulo['IEU Artículo'].replace([float('inf'), -float('inf')], 0)
    df_articulo['IEU Artículo'] = df_articulo['IEU Artículo'].fillna(0)
    
    # === ASIGNAR ACCIONES POR ARTÍCULO ===
    def asignar_accion_articulo(row):
        ieu = row['IEU Artículo']
        exceso = row['Costo Exceso Artículo']
        venta = row['Venta Artículo']
        rentabilidad = row['Rentabilidad % Artículo']
        stock = row['Stock Actual']
        tiene_exceso = row['Tiene Exceso'] == 'Sí'
        
        # 🚨 CRÍTICO: Exceso muy superior a ventas
        if exceso > venta * 2:
            return "🚨 LIQUIDAR YA: Exceso duplica ventas"
        
        if exceso > venta:
            return "🚨 LIQUIDAR: Exceso > Ventas"
        
        # 🔴 Sin stock y bajo IEU
        if stock == 0 and ieu < 0.8:
            return "🔴 NO REPONER: Bajo rendimiento"
        
        # 🔴 IEU muy bajo
        if ieu < 0.6:
            if tiene_exceso:
                return "🔴 DESCONTINUAR: Liquidar y no reponer"
            else:
                return "🔴 AGOTAR STOCK: No reponer"
        
        # ⚠️ IEU bajo
        elif ieu < 0.8:
            if tiene_exceso:
                return "⚠️ PROMOCIONAR: Liberar exceso"
            elif stock == 0:
                return "⚠️ EVALUAR: Analizar antes de reponer"
            else:
                return "⚠️ REDUCIR: Comprar menos cantidad"
        
        # ⚡ IEU medio-bajo
        elif ieu < 1.0:
            if rentabilidad < 20:
                return "⚡ RENEGOCIAR: Pedir mejor costo"
            elif tiene_exceso:
                return "⚡ PROMOCIÓN SUAVE: Normalizar stock"
            else:
                return "⚡ MANTENER: Revisar rotación"
        
        # ✅ IEU equilibrado
        elif ieu < 1.2:
            if stock == 0:
                return "✅ REPONER: Stock agotado"
            elif tiene_exceso:
                return "✅ PROMOCIÓN: Liberar exceso"
            else:
                return "✅ MANTENER: Pedido normal"
        
        # 🌟 IEU muy bueno
        elif ieu < 1.5:
            if stock == 0:
                return "🌟 REPONER URGENTE: Alta prioridad"
            elif tiene_exceso:
                return "🌟 PROMOCIONAR: Potenciar ventas"
            else:
                return "🌟 AUMENTAR: Comprar más cantidad"
        
        # 💎 IEU excelente
        else:
            if stock == 0:
                return "💎 CRÍTICO: Reponer inmediatamente"
            elif tiene_exceso:
                return "💎 POTENCIAR: Exhibición destacada"
            else:
                return "💎 AUMENTAR STOCK: Top performer"
    
    df_articulo['Acción Artículo'] = df_articulo.apply(asignar_accion_articulo, axis=1)
    
    # Categoría simplificada
    def categoria_articulo(accion):
        if '🚨' in accion or '🔴' in accion:
            return 'Crítico'
        elif '⚠️' in accion:
            return 'Revisar'
        elif '⚡' in accion:
            return 'Ajustar'
        elif '💎' in accion or '🌟' in accion:
            return 'Top Performer'
        else:
            return 'Mantener'
    
    df_articulo['Categoría Artículo'] = df_articulo['Acción Artículo'].apply(categoria_articulo)
    
    # Calcular índice de rotación
    df_articulo['Días Venta Stock'] = (
        df_articulo['Stock Actual'] / (df_articulo['Cantidad Vendida'] / 30)
    ).round(0)
    df_articulo['Días Venta Stock'] = df_articulo['Días Venta Stock'].replace([float('inf'), -float('inf')], 0)
    df_articulo['Días Venta Stock'] = df_articulo['Días Venta Stock'].fillna(0)
    
    return df_articulo


def mostrar_analisis_articulos00(df_original):
    """
    TAB 4: Análisis detallado por artículo
    """
    # Explicación
    with st.expander("ℹ️ ¿Cómo usar el análisis por artículo?", expanded=False):
        st.markdown("""
        ### 🎯 Análisis por Artículo - La Vista Más Accionable
        
        **¿Por qué es importante analizar por artículo?**
        
        Un proveedor puede tener buen IEU promedio, pero tener artículos individuales que:
        - 🚨 Tienen exceso crítico de stock
        - 💎 Son top performers que merecen más espacio
        - 🔴 No aportan valor y ocupan lugar
        
        **¿Qué muestra esta tabla?**
        
        Cada fila es un artículo individual con:
        - **IEU del artículo**: Eficiencia individual del SKU
        - **Acción específica**: Qué hacer con ESE producto puntual
        - **Días de venta en stock**: Cuántos días tardas en vender el stock actual
        - **Todas las métricas**: Ventas, costos, exceso, rentabilidad
        
        **Cómo usar los filtros:**
        
        **1. Filtro por Categoría:**
        - **Crítico** 🚨🔴: Acción inmediata (liquidar, descontinuar)
        - **Revisar** ⚠️: Decisión a corto plazo (promocionar, reducir)
        - **Top Performer** 💎🌟: Potenciar y nunca romper stock
        - **Mantener** ✅: Todo OK, seguir igual
        
        **2. Filtro por Proveedor:**
        - Ver todos los artículos de un proveedor específico
        - Útil para reuniones con comercial del proveedor
        
        **3. Filtro por Subfamilia:**
        - Analizar una categoría específica (ej: solo Arroz)
        - Comparar artículos similares
        
        **4. Buscar por descripción:**
        - Encuentra un producto específico rápidamente
        
        **Acciones específicas por artículo:**
        
        | Acción | ¿Qué significa? | Ejemplo práctico |
        |--------|-----------------|------------------|
        | 💎 **CRÍTICO: Reponer inmediatamente** | Stock 0 en tu mejor producto | Llama YA al proveedor, pide envío urgente |
        | 🌟 **REPONER URGENTE** | Stock bajo en producto rentable | Anticipar pedido, no esperar al habitual |
        | ✅ **REPONER: Stock agotado** | Stock 0 en producto normal | Incluir en próximo pedido regular |
        | 🚨 **LIQUIDAR YA** | Exceso > 2x ventas mensuales | 2x1 o 40% OFF hasta normalizar |
        | 🔴 **NO REPONER** | Stock 0 pero bajo rendimiento | Dejar que se agote, no volver a pedir |
        | ⚠️ **REDUCIR** | Comprar menos en próximo pedido | Si pedías 100 u, pedir solo 50 u |
        | 💎 **AUMENTAR STOCK** | Tu top performer merece más | Si pedías 100 u, pedir 150 u |
        
        **💡 Tips de uso:**
        
        **Para reunión con proveedor:**
        1. Filtra por el proveedor
        2. Ordena por IEU Artículo (ascendente)
        3. Los más bajos → pedir devolución o bonificación
        4. Los más altos → pedir condiciones especiales para comprar más
        
        **Para armar pedido semanal:**
        1. Filtra "Top Performer" y ordena por Stock Actual
        2. Los que tienen stock bajo o 0 → prioridad máxima
        3. Filtra "Crítico" → NO incluir en pedido
        
        **Para optimizar góndola:**
        1. Ordena por IEU Artículo (descendente)
        2. Top 10 → altura de ojos
        3. Bottom 10 → estante superior o inferior
        
        **Días Venta Stock:**
        - < 7 días = Rotación muy rápida → Aumentar stock
        - 7-30 días = Normal
        - 30-60 días = Rotación lenta → Reducir compras
        - > 60 días = Stock muerto → Liquidar
        """)
    
    # st.markdown("---")
    
    # Calcular métricas por artículo
    df_art = calcular_metricas_ieu_articulo(df_original)
    
    # === MÉTRICAS RESUMEN ===
    st.markdown("#### 📊 Resumen de Artículos")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_articulos = len(df_art)
        st.metric("Total Artículos", f"{total_articulos}")
    
    with col2:
        top_performers = len(df_art[df_art['Categoría Artículo'] == 'Top Performer'])
        st.metric("Top Performers", f"{top_performers}", 
                 delta=f"{top_performers/total_articulos*100:.0f}%")
    
    with col3:
        criticos = len(df_art[df_art['Categoría Artículo'] == 'Crítico'])
        st.metric("Artículos Críticos", f"{criticos}",
                 delta="Acción urgente" if criticos > 0 else "OK",
                 delta_color="inverse" if criticos > 0 else "normal")
    
    with col4:
        sin_stock = len(df_art[df_art['Stock Actual'] == 0])
        st.metric("Sin Stock", f"{sin_stock}")
    
    with col5:
        con_exceso = len(df_art[df_art['Tiene Exceso'] == 'Sí'])
        st.metric("Con Exceso", f"{con_exceso}")
    
    # st.markdown("---")
    
    # === FILTROS AVANZADOS ===
    st.markdown("#### 🔍 Filtros")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        categorias_disponibles = ['Todas'] + sorted(df_art['Categoría Artículo'].unique().tolist())
        categoria_filtro = st.selectbox(
            "Categoría:",
            options=categorias_disponibles,
            key='filtro_categoria_articulo'
        )
    
    with col_f2:
        proveedores_disponibles = ['Todos'] + sorted(df_art['Proveedor'].unique().tolist())
        proveedor_filtro = st.selectbox(
            "Proveedor:",
            options=proveedores_disponibles,
            key='filtro_proveedor_articulo'
        )
    
    with col_f3:
        subfamilias_disponibles = ['Todas'] + sorted(df_art['Subfamilia'].dropna().unique().tolist())
        subfamilia_filtro = st.selectbox(
            "Subfamilia:",
            options=subfamilias_disponibles,
            key='filtro_subfamilia_articulo'
        )
    
    with col_f4:
        art_descripcion = ['Todas'] + sorted(df_art['descripcion'].dropna().unique().tolist())
        subfamilia_filtro = st.selectbox(
            "Nombre art:",
            options=art_descripcion,
            key='filtro_art_descripcion'
        )
    
    # Aplicar filtros
    df_filtrado = df_art.copy()
    
    if categoria_filtro != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Categoría Artículo'] == categoria_filtro]
    
    if proveedor_filtro != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Proveedor'] == proveedor_filtro]
    
    if subfamilia_filtro != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Subfamilia'] == subfamilia_filtro]
    
    if buscar_texto:
        df_filtrado = df_filtrado[
            df_filtrado['Descripción'].str.contains(buscar_texto, case=False, na=False)
        ]
    
    st.info(f"📦 Mostrando {len(df_filtrado)} de {len(df_art)} artículos")
    
    # === TABLA INTERACTIVA ===
    st.markdown("#### 📋 Detalle por Artículo")
    
    # Preparar columnas para mostrar
    columnas_mostrar = [
        'idarticulo',
        'Descripción',
        'Subfamilia',
        'Proveedor',
        'IEU Artículo',
        'Acción Artículo',
        'Venta Artículo',
        'Utilidad Artículo',
        'Rentabilidad % Artículo',
        'Cantidad Vendida',
        'Stock Actual',
        'Días Venta Stock',
        'Tiene Exceso',
        'Costo Exceso Artículo',
        '% Participación Ventas Artículo',
        '% Participación Utilidad Artículo'
    ]
    
    df_display = df_filtrado[columnas_mostrar].copy()
    
    # Formatear para display
    df_display['Venta Artículo'] = df_display['Venta Artículo'].apply(lambda x: f"${x:,.0f}")
    df_display['Utilidad Artículo'] = df_display['Utilidad Artículo'].apply(lambda x: f"${x:,.0f}")
    df_display['Costo Exceso Artículo'] = df_display['Costo Exceso Artículo'].apply(lambda x: f"${x:,.0f}")
    df_display['Rentabilidad % Artículo'] = df_display['Rentabilidad % Artículo'].apply(lambda x: f"{x:.1f}%")
    df_display['% Participación Ventas Artículo'] = df_display['% Participación Ventas Artículo'].apply(lambda x: f"{x:.2f}%")
    df_display['% Participación Utilidad Artículo'] = df_display['% Participación Utilidad Artículo'].apply(lambda x: f"{x:.2f}%")
    df_display['Días Venta Stock'] = df_display['Días Venta Stock'].apply(lambda x: f"{int(x)} días")
    
    # Mostrar tabla
    st.dataframe(
        df_display,
        width='stretch',
        hide_index=True,
        height=600
    )
    
    # === BOTÓN DE EXPORTACIÓN ===
    st.markdown("---")
    
    col_exp1, col_exp2 = st.columns([3, 1])
    
    with col_exp1:
        st.markdown("**💾 Exportar tabla filtrada a Excel**")
        st.info(f"Se exportarán los {len(df_filtrado)} artículos actualmente filtrados")
    
    with col_exp2:
        # Preparar Excel
        from io import BytesIO
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_filtrado[columnas_mostrar].to_excel(
                writer, 
                sheet_name='Análisis Artículos',
                index=False
            )
        
        output.seek(0)
        
        st.download_button(
            label="📥 Descargar Excel",
            data=output,
            file_name=f"analisis_articulos_{categoria_filtro}_{time.strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
            type="primary"
        )
    
    # === GRÁFICO TOP/BOTTOM ===
    st.markdown("---")
    st.markdown("#### 🏆 Top 10 y Bottom 10 por IEU")
    
    col_top, col_bottom = st.columns(2)
    
    with col_top:
        st.markdown("**🌟 Top 10 Artículos (Mayor IEU)**")
        top10 = df_filtrado.nlargest(10, 'IEU Artículo')[
            ['Descripción', 'IEU Artículo', 'Venta Artículo', 'Acción Artículo']
        ].copy()
        
        # Limpiar formato para mostrar
        if len(top10) > 0:
            top10['Venta'] = df_filtrado.nlargest(10, 'IEU Artículo')['Venta Artículo'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(
                top10[['Descripción', 'IEU Artículo', 'Venta', 'Acción Artículo']],
                width='stretch',
                hide_index=True
            )
        else:
            st.info("No hay datos para mostrar")
    
    with col_bottom:
        st.markdown("**⚠️ Bottom 10 Artículos (Menor IEU)**")
        bottom10 = df_filtrado.nsmallest(10, 'IEU Artículo')[
            ['Descripción', 'IEU Artículo', 'Venta Artículo', 'Acción Artículo']
        ].copy()
        
        if len(bottom10) > 0:
            bottom10['Venta'] = df_filtrado.nsmallest(10, 'IEU Artículo')['Venta Artículo'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(
                bottom10[['Descripción', 'IEU Artículo', 'Venta', 'Acción Artículo']],
                width='stretch',
                hide_index=True
            )
        else:
            st.info("No hay datos para mostrar")

def mostrar_analisis_articulos(df_original):
    """
    TAB 4: Análisis detallado por artículo con VISUALIZACIONES
    """
    # Explicación
    with st.expander("ℹ️ ¿Cómo usar el análisis por artículo?", expanded=False):
        st.markdown("""
        ### 🎯 Análisis por Artículo - La Vista Más Accionable
        
        **¿Por qué es importante analizar por artículo?**
        
        Un proveedor puede tener buen IEU promedio, pero tener artículos individuales que:
        - 🚨 Tienen exceso crítico de stock
        - 💎 Son top performers que merecen más espacio
        - 🔴 No aportan valor y ocupan lugar
        
        **¿Qué muestra esta sección?**
        
        - **Gráficos interactivos**: Visualiza patrones y outliers rápidamente
        - **Filtros múltiples**: Enfócate en lo que necesitas analizar
        - **Tabla detallada**: Cada artículo con todas sus métricas
        - **Rankings**: Top 10 y Bottom 10 para decisiones rápidas
        
        **💡 Tip:** Usa los gráficos para detectar problemas, luego usa los filtros y tabla para el detalle.
        """)
    
    # st.markdown("---")
    
    # Calcular métricas por artículo
    df_art = calcular_metricas_ieu_articulo(df_original)
    
    # === MÉTRICAS RESUMEN ===
    st.markdown("#### 📊 Resumen de Artículos")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_articulos = len(df_art)
        st.metric("Total Artículos", f"{total_articulos}")
    
    with col2:
        top_performers = len(df_art[df_art['Categoría Artículo'] == 'Top Performer'])
        st.metric("Top Performers", f"{top_performers}", 
                 delta=f"{top_performers/total_articulos*100:.0f}%")
    
    with col3:
        criticos = len(df_art[df_art['Categoría Artículo'] == 'Crítico'])
        st.metric("Artículos Críticos", f"{criticos}",
                 delta="Acción urgente" if criticos > 0 else "OK",
                 delta_color="inverse" if criticos > 0 else "normal")
    
    with col4:
        sin_stock = len(df_art[df_art['Stock Actual'] == 0])
        st.metric("Sin Stock", f"{sin_stock}")
    
    with col5:
        con_exceso = len(df_art[df_art['Tiene Exceso'] == 'Sí'])
        st.metric("Con Exceso", f"{con_exceso}")
    
    st.markdown("---")
    
    # === FILTROS AVANZADOS ===
    st.markdown("#### 🔍 Filtros")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        categorias_disponibles = ['Todas'] + sorted(df_art['Categoría Artículo'].unique().tolist())
        categoria_filtro = st.selectbox(
            "Categoría:",
            options=categorias_disponibles,
            key='filtro_categoria_articulo'
        )
    
    with col_f2:
        proveedores_disponibles = ['Todos'] + sorted(df_art['Proveedor'].unique().tolist())
        proveedor_filtro = st.selectbox(
            "Proveedor:",
            options=proveedores_disponibles,
            key='filtro_proveedor_articulo'
        )
    
    with col_f3:
        subfamilias_disponibles = ['Todas'] + sorted(df_art['Subfamilia'].dropna().unique().tolist())
        subfamilia_filtro = st.selectbox(
            "Subfamilia:",
            options=subfamilias_disponibles,
            key='filtro_subfamilia_articulo'
        )
    
    # with col_f4:
    #     art_descripcion = ['Todas'] + sorted(df_art['descripcion'].dropna().unique().tolist())
    #     subfamilia_filtro = st.selectbox(
    #         "Nombre art:",
    #         options=art_descripcion,
    #         key='filtro_art_descripcion'
    #     )
    
    # Aplicar filtros
    df_filtrado = df_art.copy()
    
    if categoria_filtro != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Categoría Artículo'] == categoria_filtro]
    
    if proveedor_filtro != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Proveedor'] == proveedor_filtro]
    
    if subfamilia_filtro != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['Subfamilia'] == subfamilia_filtro]
    
    # if buscar_texto:
    #     df_filtrado = df_filtrado[
    #         df_filtrado['Descripción'].str.contains(buscar_texto, case=False, na=False)
    #     ]
    
    st.info(f"📦 Mostrando {len(df_filtrado)} de {len(df_art)} artículos")
    
    # ============================================================
    # 🎨 VISUALIZACIONES INTERACTIVAS
    # ============================================================
    
    st.markdown("---")
    st.markdown("#### 📈 Visualizaciones")
    
    if len(df_filtrado) == 0:
        st.warning("⚠️ No hay artículos para mostrar con los filtros actuales")
    else:
        # === GRÁFICO 1: MAPA DE ARTÍCULOS ===
        with st.expander("📊 Mapa de Artículos (Rentabilidad vs Ventas)", expanded=False):
            st.info("💡 Visualiza la posición de cada artículo según rentabilidad y participación en ventas. Tamaño = Costo de exceso.")
            
            # Limitar a top N artículos si hay muchos (para performance)
            df_grafico = df_filtrado.nlargest(100, 'Venta Artículo') if len(df_filtrado) > 100 else df_filtrado
            
            if len(df_filtrado) > 100:
                st.info(f"⚠️ Mostrando top 100 artículos por ventas (de {len(df_filtrado)} filtrados)")
            
            fig_mapa = px.scatter(
                df_grafico,
                x='% Participación Ventas Artículo',
                y='Rentabilidad % Artículo',
                size='Costo Exceso Artículo',
                color='Categoría Artículo',
                hover_data={
                    'Descripción': True,
                    'Proveedor': True,
                    'Subfamilia': True,
                    'IEU Artículo': ':.2f',
                    'Venta Artículo': ':$,.0f',
                    'Stock Actual': True,
                    'Acción Artículo': True,
                    '% Participación Ventas Artículo': ':.3f%',
                    'Rentabilidad % Artículo': ':.2f%',
                    'Costo Exceso Artículo': ':$,.0f'
                },
                color_discrete_map={
                    'Crítico': '#ff0000',
                    'Revisar': '#ff9500',
                    'Ajustar': '#ffcc00',
                    'Mantener': '#4caf50',
                    'Top Performer': '#2196f3'
                },
                title='Mapa de Artículos: Rentabilidad vs Participación en Ventas<br><sub>Tamaño = Costo de Exceso</sub>',
                labels={
                    '% Participación Ventas Artículo': '% Participación en Ventas',
                    'Rentabilidad % Artículo': 'Rentabilidad %'
                }
            )
            
            # Líneas de referencia
            if len(df_grafico) > 0:
                fig_mapa.add_hline(
                    y=df_grafico['Rentabilidad % Artículo'].mean(), 
                    line_dash="dash", 
                    line_color="gray",
                    annotation_text="Rentabilidad Promedio"
                )
                
                fig_mapa.add_vline(
                    x=df_grafico['% Participación Ventas Artículo'].mean(), 
                    line_dash="dash", 
                    line_color="gray",
                    annotation_text="Participación Promedio"
                )
            
            fig_mapa.update_layout(height=600)
            st.plotly_chart(fig_mapa, width='stretch')
            
            st.info("""
            **Cómo interpretar:**
            - **Superior Derecha** = Alta venta + Alto margen → Potenciar
            - **Superior Izquierda** = Baja venta + Alto margen → Producto nicho rentable
            - **Inferior Derecha** = Alta venta + Bajo margen → Gancho de tráfico
            - **Inferior Izquierda** = Baja venta + Bajo margen → Candidato a descontinuar
            - **Círculos grandes** = Mucho exceso de stock → Requiere acción
            """)
        
        # === GRÁFICO 2: DISTRIBUCIÓN DE ACCIONES ===
        with st.expander("🍩 Distribución de Categorías", expanded=False):
            st.info("💡 Proporción de artículos en cada categoría de acción")
            
            # Contar por categoría
            dist_categorias = df_filtrado['Categoría Artículo'].value_counts().reset_index()
            dist_categorias.columns = ['Categoría', 'Cantidad']
            
            fig_donut = px.pie(
                dist_categorias,
                values='Cantidad',
                names='Categoría',
                hole=0.4,
                color='Categoría',
                color_discrete_map={
                    'Crítico': '#ff0000',
                    'Revisar': '#ff9500',
                    'Ajustar': '#ffcc00',
                    'Mantener': '#4caf50',
                    'Top Performer': '#2196f3'
                },
                title=f'Distribución de {len(df_filtrado)} Artículos por Categoría'
            )
            
            fig_donut.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Artículos: %{value}<br>Porcentaje: %{percent}<extra></extra>'
            )
            
            fig_donut.update_layout(height=500)
            st.plotly_chart(fig_donut, width='stretch')
            
            # Mostrar tabla resumen
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("**📋 Detalle por Categoría:**")
                dist_categorias['Porcentaje'] = (dist_categorias['Cantidad'] / dist_categorias['Cantidad'].sum() * 100).round(1)
                dist_categorias['Porcentaje'] = dist_categorias['Porcentaje'].apply(lambda x: f"{x}%")
                st.dataframe(dist_categorias, width='stretch', hide_index=True)
            
            with col_b:
                st.markdown("**💡 ¿Qué significa?**")
                
                criticos_pct = (dist_categorias[dist_categorias['Categoría'] == 'Crítico']['Cantidad'].sum() / len(df_filtrado) * 100) if 'Crítico' in dist_categorias['Categoría'].values else 0
                top_pct = (dist_categorias[dist_categorias['Categoría'] == 'Top Performer']['Cantidad'].sum() / len(df_filtrado) * 100) if 'Top Performer' in dist_categorias['Categoría'].values else 0
                
                if criticos_pct > 30:
                    st.error(f"🚨 {criticos_pct:.0f}% de artículos críticos. Requiere limpieza urgente de surtido.")
                elif criticos_pct > 15:
                    st.warning(f"⚠️ {criticos_pct:.0f}% de artículos críticos. Considera optimizar el portafolio.")
                else:
                    st.success(f"✅ Solo {criticos_pct:.0f}% de artículos críticos. Portafolio saludable.")
                
                if top_pct > 20:
                    st.success(f"🌟 {top_pct:.0f}% son top performers. ¡Excelente surtido rentable!")
                elif top_pct > 10:
                    st.info(f"✅ {top_pct:.0f}% son top performers. Surtido equilibrado.")
                else:
                    st.warning(f"⚠️ Solo {top_pct:.0f}% son top performers. Busca productos más rentables.")
        
        # === GRÁFICO 3: COMPARACIÓN POR PROVEEDOR ===
        with st.expander("📊 Comparación por Proveedor", expanded=False):
            st.info("💡 Distribución de categorías de artículos por cada proveedor")
            
            # Agrupar por proveedor y categoría
            prov_cat = df_filtrado.groupby(['Proveedor', 'Categoría Artículo']).size().reset_index(name='Cantidad')
            
            # Ordenar proveedores por total de artículos
            orden_prov = df_filtrado['Proveedor'].value_counts().index.tolist()
            
            fig_barras = px.bar(
                prov_cat,
                x='Proveedor',
                y='Cantidad',
                color='Categoría Artículo',
                color_discrete_map={
                    'Crítico': '#ff0000',
                    'Revisar': '#ff9500',
                    'Ajustar': '#ffcc00',
                    'Mantener': '#4caf50',
                    'Top Performer': '#2196f3'
                },
                title='Distribución de Artículos por Proveedor y Categoría',
                labels={'Cantidad': 'Número de Artículos'},
                category_orders={'Proveedor': orden_prov}
            )
            
            fig_barras.update_layout(
                height=500,
                xaxis_tickangle=-45,
                barmode='stack',
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_barras, width='stretch')
            
            st.info("""
            **Cómo usar este gráfico:**
            - Identifica proveedores con **muchos artículos críticos** (rojo) → Reunión urgente para renegociar o reducir surtido
            - Proveedores con **muchos top performers** (azul) → Buscar más productos de ese proveedor
            - Proveedores con distribución equilibrada → Mantener relación actual
            - Si un proveedor tiene 1 top performer y 10 críticos → Mantener solo el top, descontinuar el resto
            """)
    
    st.markdown("---")
    
    # === TABLA INTERACTIVA ===
    st.markdown("#### 📋 Detalle por Artículo")
    
    # Preparar columnas para mostrar
    columnas_mostrar = [
        'idarticulo',
        'Descripción',
        'Subfamilia',
        'Proveedor',
        'IEU Artículo',
        'Acción Artículo',
        'Venta Artículo',
        'Utilidad Artículo',
        'Rentabilidad % Artículo',
        'Cantidad Vendida',
        'Stock Actual',
        'Días Venta Stock',
        'Tiene Exceso',
        'Costo Exceso Artículo',
        '% Participación Ventas Artículo',
        '% Participación Utilidad Artículo'
    ]
    
    df_display = df_filtrado[columnas_mostrar].copy()
    
    # Formatear para display
    df_display['Venta Artículo'] = df_display['Venta Artículo'].apply(lambda x: f"${x:,.0f}")
    df_display['Utilidad Artículo'] = df_display['Utilidad Artículo'].apply(lambda x: f"${x:,.0f}")
    df_display['Costo Exceso Artículo'] = df_display['Costo Exceso Artículo'].apply(lambda x: f"${x:,.0f}")
    df_display['Rentabilidad % Artículo'] = df_display['Rentabilidad % Artículo'].apply(lambda x: f"{x:.1f}%")
    df_display['% Participación Ventas Artículo'] = df_display['% Participación Ventas Artículo'].apply(lambda x: f"{x:.2f}%")
    df_display['% Participación Utilidad Artículo'] = df_display['% Participación Utilidad Artículo'].apply(lambda x: f"{x:.2f}%")
    df_display['Días Venta Stock'] = df_display['Días Venta Stock'].apply(lambda x: f"{int(x)} días")
    
    # Mostrar tabla
    st.dataframe(
        df_display,
        width='stretch',
        hide_index=True,
        height=600
    )
    
    # === BOTÓN DE EXPORTACIÓN ===
    st.markdown("---")
    
    col_exp1, col_exp2 = st.columns([3, 1])
    
    with col_exp1:
        st.markdown("**💾 Exportar tabla filtrada a Excel**")
        st.info(f"Se exportarán los {len(df_filtrado)} artículos actualmente filtrados")
    
    with col_exp2:
        # Preparar Excel
        from io import BytesIO
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_filtrado[columnas_mostrar].to_excel(
                writer, 
                sheet_name='Análisis Artículos',
                index=False
            )
        
        output.seek(0)
        
        st.download_button(
            label="📥 Descargar Excel",
            data=output,
            file_name=f"analisis_articulos_{categoria_filtro}_{time.strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch',
            type="primary"
        )
    
    # === GRÁFICO TOP/BOTTOM ===
    st.markdown("---")
    st.markdown("#### 🏆 Top 10 y Bottom 10 por IEU")
    
    col_top, col_bottom = st.columns(2)
    
    with col_top:
        st.markdown("**🌟 Top 10 Artículos (Mayor IEU)**")
        top10 = df_filtrado.nlargest(10, 'IEU Artículo')[
            ['Descripción', 'IEU Artículo', 'Venta Artículo', 'Acción Artículo']
        ].copy()
        
        # Limpiar formato para mostrar
        if len(top10) > 0:
            top10['Venta'] = df_filtrado.nlargest(10, 'IEU Artículo')['Venta Artículo'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(
                top10[['Descripción', 'IEU Artículo', 'Venta', 'Acción Artículo']],
                width='stretch',
                hide_index=True
            )
        else:
            st.info("No hay datos para mostrar")
    
    with col_bottom:
        st.markdown("**⚠️ Bottom 10 Artículos (Menor IEU)**")
        bottom10 = df_filtrado.nsmallest(10, 'IEU Artículo')[
            ['Descripción', 'IEU Artículo', 'Venta Artículo', 'Acción Artículo']
        ].copy()
        
        if len(bottom10) > 0:
            bottom10['Venta'] = df_filtrado.nsmallest(10, 'IEU Artículo')['Venta Artículo'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(
                bottom10[['Descripción', 'IEU Artículo', 'Venta', 'Acción Artículo']],
                width='stretch',
                hide_index=True
            )
        else:
            st.info("No hay datos para mostrar")