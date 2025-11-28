"""
Dashboard de Análisis de Inventario
Módulo completo para gestión estratégica de stock
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time


class InventoryDashboard:
    """
    Dashboard estratégico para análisis de inventario y gestión de stock
    """
    
    def __init__(self):
        """Inicializar dashboard"""
        pass
    
    def load_and_validate_data(self, df):
        """
        Carga y validación de datos con medición de tiempo
        
        Args:
            df: DataFrame con datos de inventario
        
        Returns:
            DataFrame procesado y validado
        """
        start_time = time.time()
        
        st.markdown("### 🔄 Procesando Datos para Análisis Estratégico...")
        progress_bar = st.progress(0)
        
        try:
            # Validaciones básicas
            progress_bar.progress(25)
            required_cols = ['idarticulo', 'nivel_riesgo', 'prioridad', 'dias_cobertura']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.warning(f"⚠️ Algunas columnas no están disponibles: {missing_cols}")
                # Crear columnas faltantes con valores por defecto
                for col in missing_cols:
                    if col == 'nivel_riesgo':
                        df[col] = '🟡 Medio'
                    elif col == 'prioridad':
                        df[col] = 5
                    elif col == 'dias_cobertura':
                        df[col] = 30
            
            progress_bar.progress(50)
            
            # Limpieza de datos
            df_clean = df.copy()
            
            # Convertir columnas numéricas
            numeric_cols = ['prioridad', 'dias_cobertura', 'STK_TOTAL', 'costo_unit', 
                          'total_abastecer', 'cnt_corregida', 'PRESUPUESTO']
            
            for col in numeric_cols:
                if col in df_clean.columns:
                    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
            
            progress_bar.progress(75)
            
            # Crear métricas derivadas
            df_clean = self.create_derived_metrics(df_clean)
            
            progress_bar.progress(100)
            
            load_time = time.time() - start_time
            st.success(f"✅ Datos procesados exitosamente en {load_time:.2f} segundos")
            st.info(f"📊 Dataset: {len(df_clean):,} productos | {len(df_clean.columns)} columnas")
            
            progress_bar.empty()
            return df_clean
            
        except Exception as e:
            st.error(f"❌ Error en procesamiento de datos: {e}")
            progress_bar.empty()
            return None
    
    def create_derived_metrics(self, df):
        """
        Crear métricas derivadas para análisis
        
        Args:
            df: DataFrame con datos base
        
        Returns:
            DataFrame con métricas adicionales
        """
        # Crear columnas de valor perdido y costo exceso si no existen
        if 'valor_perdido_TOTAL' not in df.columns:
            df['valor_perdido_TOTAL'] = 0
        if 'costo_exceso_STK' not in df.columns:
            df['costo_exceso_STK'] = 0
        if 'exceso_STK' not in df.columns:
            df['exceso_STK'] = 0
        
        # Impacto financiero total
        df['impacto_financiero_total'] = (
            df.get('valor_perdido_TOTAL', 0) + df.get('costo_exceso_STK', 0)
        )
        
        # Eficiencia de inventario
        df['eficiencia_inventario'] = np.where(
            df['dias_cobertura'] > 0,
            1 / (1 + df['dias_cobertura'] / 30),  # Normalizado
            0
        )
        
        # Categoría de rotación
        df['categoria_rotacion'] = pd.cut(
            df['dias_cobertura'], 
            bins=[-1, 15, 30, 60, float('inf')], 
            labels=['🔴 Crítica', '🟠 Alta', '🟡 Normal', '🟢 Lenta']
        )
        
        return df
    
    def show_main_kpis(self, df):
        """
        Mostrar KPIs principales del inventario
        
        Args:
            df: DataFrame con datos procesados
        """
        st.markdown("### 📈 KPIs Principales del Inventario")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total_productos = len(df)
            st.metric("📦 Total Productos", f"{total_productos:,}")
        
        with col2:
            productos_criticos = len(df[df['nivel_riesgo'].str.contains('🔴', na=False)])
            st.metric("🚨 Productos Críticos", productos_criticos)
        
        with col3:
            valor_perdido = df.get('valor_perdido_TOTAL', pd.Series([0])).sum()
            st.metric("💸 Valor Perdido", f"${valor_perdido:,.0f}")
        
        with col4:
            stock_total = df['STK_TOTAL'].sum()
            st.metric("📊 Stock Total", f"{stock_total:,.0f}")
        
        with col5:
            productos_sin_stock = len(df[df['STK_TOTAL'] == 0])
            st.metric("❌ Sin Stock", productos_sin_stock)
    
    def tab_matriz_estrategica(self, df):
        """
        Matriz de priorización estratégica
        
        Args:
            df: DataFrame con datos procesados
        """
        st.markdown("### 🎯 Matriz de Priorización Estratégica")
        
        start_time = time.time()
        
        # Crear grupos estratégicos
        def clasificar_urgencia(row):
            if '🔴' in str(row.get('nivel_riesgo', '')) and row.get('prioridad', 10) <= 3:
                return "🚨 CRÍTICO"
            elif '🟠' in str(row.get('nivel_riesgo', '')) and row.get('dias_cobertura', 100) < 20:
                return "⚠️ URGENTE"
            elif '🟡' in str(row.get('nivel_riesgo', '')) and row.get('exceso_STK', 0) > 0:
                return "👀 MONITOREO"
            else:
                return "✅ ESTABLE"
        
        df['grupo_urgencia'] = df.apply(clasificar_urgencia, axis=1)
        
        # Crear resumen por grupo
        resumen_urgencia = df.groupby('grupo_urgencia').agg({
            'idarticulo': 'count',
            'impacto_financiero_total': 'sum',
            'PRESUPUESTO': 'sum'
        }).round(0)
        
        resumen_urgencia.columns = ['Productos', 'Impacto Total $', 'Presupuesto $']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Distribución por Urgencia")
            fig = px.pie(
                values=resumen_urgencia['Productos'],
                names=resumen_urgencia.index,
                title="Productos por Nivel de Urgencia"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 💰 Resumen Financiero por Grupo")
            st.dataframe(resumen_urgencia, use_container_width=True)
        
        # Productos críticos
        st.markdown("#### 🚨 Productos que Requieren Atención Inmediata")
        criticos = df[df['grupo_urgencia'].isin(["🚨 CRÍTICO", "⚠️ URGENTE"])][
            ['idarticulo', 'descripcion', 'familia', 'nivel_riesgo', 'dias_cobertura', 
             'STK_TOTAL', 'prioridad']
        ].head(15)
        
        if not criticos.empty:
            st.dataframe(criticos, use_container_width=True)
        else:
            st.success("✅ No hay productos en estado crítico")
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_performance_sucursal(self, df):
        """
        Análisis de performance por sucursal
        
        Args:
            df: DataFrame con datos procesados
        """
        st.markdown("### 🏪 Performance por Sucursal")
        
        start_time = time.time()
        
        # Definir sucursales disponibles
        sucursal_columns = [col for col in df.columns if col.startswith('stk_')]
        sucursales_data = []
        
        for col in sucursal_columns:
            sucursal_name = col.replace('stk_', '').title()
            stock_total = df[col].sum()
            productos_con_stock = len(df[df[col] > 0])
            productos_sin_stock = len(df[df[col] == 0])
            
            sucursales_data.append({
                'Sucursal': sucursal_name,
                'Stock Total': stock_total,
                'Productos con Stock': productos_con_stock,
                'Productos sin Stock': productos_sin_stock,
                'Eficiencia %': round((productos_con_stock / len(df)) * 100, 1) if len(df) > 0 else 0
            })
        
        if sucursales_data:
            df_sucursales = pd.DataFrame(sucursales_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Stock Total por Sucursal")
                fig = px.bar(
                    df_sucursales,
                    x='Sucursal',
                    y='Stock Total',
                    title="Distribución de Stock",
                    color='Stock Total'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### 🎯 Eficiencia por Sucursal")
                fig = px.bar(
                    df_sucursales,
                    x='Sucursal',
                    y='Eficiencia %',
                    title="% de Productos con Stock",
                    color='Eficiencia %',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### 📋 Resumen Detallado")
            st.dataframe(df_sucursales, use_container_width=True)
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_gestion_inventario(self, df):
        """
        Gestión estratégica de inventario
        
        Args:
            df: DataFrame con datos procesados
        """
        st.markdown("### 📦 Gestión Estratégica de Inventario")
        
        start_time = time.time()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📈 Distribución por Rotación")
            if 'categoria_rotacion' in df.columns:
                rotacion_counts = df['categoria_rotacion'].value_counts()
                fig = px.pie(
                    values=rotacion_counts.values,
                    names=rotacion_counts.index,
                    title="Productos por Velocidad de Rotación"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 📊 TOP 10 - Mayor Presupuesto")
            top_presupuesto = df.nlargest(10, 'PRESUPUESTO')[
                ['descripcion', 'PRESUPUESTO', 'familia', 'prioridad']
            ]
            
            if not top_presupuesto.empty:
                fig = px.bar(
                    top_presupuesto,
                    x='PRESUPUESTO',
                    y='descripcion',
                    title="Productos con Mayor Inversión Requerida",
                    orientation='h'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Análisis de cobertura
        st.markdown("#### 🛡️ Análisis de Días de Cobertura")
        
        col3, col4, col5 = st.columns(3)
        
        with col3:
            cobertura_critica = len(df[df['dias_cobertura'] < 15])
            st.metric("🔴 Cobertura Crítica", f"{cobertura_critica} productos")
        
        with col4:
            cobertura_optima = len(df[(df['dias_cobertura'] >= 15) & (df['dias_cobertura'] <= 45)])
            st.metric("🟢 Cobertura Óptima", f"{cobertura_optima} productos")
        
        with col5:
            cobertura_exceso = len(df[df['dias_cobertura'] > 60])
            st.metric("🟡 Exceso Cobertura", f"{cobertura_exceso} productos")
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_analisis_familia(self, df):
        """
        Análisis por familia de productos
        
        Args:
            df: DataFrame con datos procesados
        """
        st.markdown("### 📊 Análisis por Familia de Productos")
        
        start_time = time.time()
        
        if 'familia' in df.columns:
            familia_stats = df.groupby('familia').agg({
                'idarticulo': 'count',
                'STK_TOTAL': 'sum',
                'PRESUPUESTO': 'sum',
                'impacto_financiero_total': 'sum'
            }).round(0)
            
            familia_stats.columns = ['Productos', 'Stock Total', 'Presupuesto', 'Impacto Total']
            familia_stats = familia_stats.sort_values('Presupuesto', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🏷️ TOP Familias por Presupuesto")
                top_familias = familia_stats.head(10)
                fig = px.bar(
                    x=top_familias.index,
                    y=top_familias['Presupuesto'],
                    title="Inversión Requerida por Familia"
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### 📦 Distribución de Productos")
                fig = px.pie(
                    values=familia_stats['Productos'],
                    names=familia_stats.index,
                    title="% de Productos por Familia"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### 📋 Resumen Detallado por Familia")
            st.dataframe(familia_stats, use_container_width=True)
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_acciones_inmediatas(self, df):
        """
        Plan de acción inmediata
        
        Args:
            df: DataFrame con datos procesados
        """
        st.markdown("### ⚡ Plan de Acción Inmediata")
        
        start_time = time.time()
        
        # Crear score de prioridad
        df['score_prioridad'] = (
            (df.get('impacto_financiero_total', 0) * 0.4) +
            ((11 - df['prioridad']) * 100 * 0.3) +
            (df['PRESUPUESTO'] * 0.3)
        )
        
        # TOP 20 acciones
        top_acciones = df.nlargest(20, 'score_prioridad')[
            ['idarticulo', 'descripcion', 'familia', 'nivel_riesgo', 
             'dias_cobertura', 'STK_TOTAL', 'PRESUPUESTO', 'prioridad']
        ]
        
        # Determinar tipo de acción
        def determinar_accion(row):
            if row['STK_TOTAL'] == 0:
                return "🔄 REABASTECER URGENTE"
            elif row['dias_cobertura'] < 15:
                return "⚠️ AUMENTAR STOCK"
            elif row['PRESUPUESTO'] > 0:
                return "💰 INVERTIR"
            else:
                return "👀 MONITOREAR"
        
        top_acciones['Acción Recomendada'] = top_acciones.apply(determinar_accion, axis=1)
        
        st.markdown("#### 🎯 TOP 20 - Acciones Prioritarias")
        st.dataframe(top_acciones.drop(['score_prioridad'], axis=1, errors='ignore'), use_container_width=True)
        
        # Resumen de acciones
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Tipos de Acción")
            resumen_acciones = top_acciones['Acción Recomendada'].value_counts()
            fig = px.pie(
                values=resumen_acciones.values,
                names=resumen_acciones.index,
                title="Distribución de Acciones Recomendadas"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 💰 Inversión Requerida")
            inversion_total = top_acciones['PRESUPUESTO'].sum()
            productos_criticos = len(top_acciones[top_acciones['STK_TOTAL'] == 0])
            
            st.metric("💵 Inversión Total", f"${inversion_total:,.0f}")
            st.metric("🚨 Productos Sin Stock", productos_criticos)
            st.metric("📋 Acciones Totales", len(top_acciones))
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")