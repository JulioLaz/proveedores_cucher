import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class InventoryDashboard:
    """
    Dashboard estratégico para análisis de inventario y gestión de stock
    """
    
    def __init__(self):
        self.setup_page_config()
        
    def setup_page_config(self):
        """Configuración inicial de la página"""
        st.set_page_config(
            page_title="📊 Dashboard Estratégico de Inventario",
            page_icon="📦",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
    def load_and_validate_data(self, df):
        """Carga y validación de datos con medición de tiempo"""
        start_time = time.time()
        
        st.markdown("### 🔄 Cargando y Validando Datos...")
        progress_bar = st.progress(0)
        
        try:
            # Validaciones básicas
            progress_bar.progress(25)
            required_cols = ['idarticulo', 'nivel_riesgo', 'prioridad', 'dias_cobertura']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Columnas faltantes: {missing_cols}")
                return None
                
            progress_bar.progress(50)
            
            # Limpieza de datos
            df_clean = df.copy()
            
            # Convertir columnas numéricas
            numeric_cols = ['prioridad', 'dias_cobertura', 'STK_TOTAL', 'costo_unit', 
                          'valor_perdido_TOTAL', 'costo_exceso_STK', 'total_abastecer']
            
            for col in numeric_cols:
                if col in df_clean.columns:
                    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
            
            progress_bar.progress(75)
            
            # Crear métricas derivadas
            df_clean = self.create_derived_metrics(df_clean)
            
            progress_bar.progress(100)
            
            load_time = time.time() - start_time
            st.success(f"✅ Datos cargados exitosamente en {load_time:.2f} segundos")
            st.info(f"📊 Dataset: {len(df_clean):,} productos | {len(df_clean.columns)} columnas")
            
            progress_bar.empty()
            return df_clean
            
        except Exception as e:
            st.error(f"❌ Error en carga de datos: {e}")
            progress_bar.empty()
            return None
    
    def create_derived_metrics(self, df):
        """Crear métricas derivadas para análisis"""
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
    
    def show_strategic_dashboard(self, df):
        """Dashboard principal estratégico"""
        if df is None or df.empty:
            st.warning("⚠️ No hay datos disponibles para análisis.")
            return
            
        st.markdown("# 📊 Dashboard Estratégico de Inventario")
        st.markdown("---")
        
        # Métricas principales
        self.show_main_kpis(df)
        
        # Pestañas principales
        tabs = st.tabs([
            "🎯 Matriz Estratégica",
            "💰 Oportunidades Financieras", 
            "🏪 Performance por Sucursal",
            "📦 Gestión de Inventario",
            "📊 Análisis por Familia",
            "⚡ Acciones Inmediatas"
        ])
        
        with tabs[0]:
            self.tab_matriz_estrategica(df)
            
        with tabs[1]:
            self.tab_oportunidades_financieras(df)
            
        with tabs[2]:
            self.tab_performance_sucursal(df)
            
        with tabs[3]:
            self.tab_gestion_inventario(df)
            
        with tabs[4]:
            self.tab_analisis_familia(df)
            
        with tabs[5]:
            self.tab_acciones_inmediatas(df)
    
    def show_main_kpis(self, df):
        """Mostrar KPIs principales"""
        st.markdown("### 📈 KPIs Principales")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total_productos = len(df)
            st.metric("📦 Total Productos", f"{total_productos:,}")
            
        with col2:
            productos_criticos = len(df[df['nivel_riesgo'].str.contains('🔴', na=False)])
            st.metric("🚨 Productos Críticos", productos_criticos)
            
        with col3:
            valor_perdido = df['valor_perdido_TOTAL'].sum()
            st.metric("💸 Valor Perdido Total", f"${valor_perdido:,.0f}")
            
        with col4:
            costo_exceso = df['costo_exceso_STK'].sum()
            st.metric("📊 Costo Exceso Stock", f"${costo_exceso:,.0f}")
            
        with col5:
            productos_sin_stock = len(df[df['STK_TOTAL'] == 0])
            st.metric("❌ Sin Stock", productos_sin_stock)
    
    def tab_matriz_estrategica(self, df):
        """Matriz de priorización estratégica"""
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
        
        # Clasificar impacto financiero
        df['impacto_categoria'] = pd.cut(
            df['impacto_financiero_total'],
            bins=3,
            labels=['💚 Bajo', '🟡 Medio', '🔴 Alto']
        )
        
        # Crear matriz
        matriz = df.groupby(['grupo_urgencia', 'impacto_categoria']).agg({
            'idarticulo': 'count',
            'valor_perdido_TOTAL': 'sum',
            'costo_exceso_STK': 'sum',
            'impacto_financiero_total': 'sum'
        }).round(0)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Matriz de Productos por Categoría")
            if not matriz.empty:
                fig = px.imshow(
                    matriz['idarticulo'].unstack(fill_value=0),
                    text_auto=True,
                    aspect="auto",
                    color_continuous_scale="Reds",
                    title="Cantidad de Productos por Urgencia vs Impacto"
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 💰 Resumen por Grupo de Urgencia")
            resumen_urgencia = df.groupby('grupo_urgencia').agg({
                'idarticulo': 'count',
                'impacto_financiero_total': 'sum',
                'valor_perdido_TOTAL': 'sum'
            }).round(0)
            
            resumen_urgencia.columns = ['Productos', 'Impacto Total $', 'Valor Perdido $']
            st.dataframe(resumen_urgencia, use_container_width=True)
        
        # Tabla detallada de productos críticos
        st.markdown("#### 🚨 Productos Críticos - Acción Inmediata")
        criticos = df[df['grupo_urgencia'] == "🚨 CRÍTICO"][
            ['idarticulo', 'descripcion', 'nivel_riesgo', 'dias_cobertura', 
             'valor_perdido_TOTAL', 'prioridad', 'familia']
        ].head(10)
        
        if not criticos.empty:
            st.dataframe(criticos, use_container_width=True)
        else:
            st.success("✅ No hay productos en estado crítico")
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_oportunidades_financieras(self, df):
        """Análisis de oportunidades financieras"""
        st.markdown("### 💰 Oportunidades de Mejora Financiera")
        
        start_time = time.time()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💸 TOP 10 - Mayor Valor Perdido")
            top_perdido = df.nlargest(10, 'valor_perdido_TOTAL')[
                ['descripcion', 'valor_perdido_TOTAL', 'nivel_riesgo', 'familia']
            ]
            
            if not top_perdido.empty:
                fig = px.bar(
                    top_perdido, 
                    x='valor_perdido_TOTAL', 
                    y='descripcion',
                    color='nivel_riesgo',
                    title="Productos con Mayor Valor Perdido",
                    orientation='h'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 📊 TOP 10 - Mayor Costo de Exceso")
            top_exceso = df.nlargest(10, 'costo_exceso_STK')[
                ['descripcion', 'costo_exceso_STK', 'exceso_STK', 'familia']
            ]
            
            if not top_exceso.empty:
                fig = px.bar(
                    top_exceso, 
                    x='costo_exceso_STK', 
                    y='descripcion',
                    title="Productos con Mayor Costo de Exceso",
                    orientation='h',
                    color_discrete_sequence=['#ff6b6b']
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        # Análisis de oportunidades de pricing
        if 'precio_actual' in df.columns and 'precio_optimo_ventas' in df.columns:
            st.markdown("#### 🎯 Oportunidades de Optimización de Precios")
            
            df['diferencia_precio_pct'] = np.where(
                df['precio_actual'] > 0,
                ((df['precio_optimo_ventas'] - df['precio_actual']) / df['precio_actual']) * 100,
                0
            )
            
            oportunidades_precio = df[
                (abs(df['diferencia_precio_pct']) > 5) & 
                (df.get('nivel_confianza', 0) > 0.7)
            ].nlargest(15, 'diferencia_precio_pct')[
                ['descripcion', 'precio_actual', 'precio_optimo_ventas', 
                 'diferencia_precio_pct', 'nivel_confianza']
            ]
            
            if not oportunidades_precio.empty:
                st.dataframe(oportunidades_precio, use_container_width=True)
            else:
                st.info("ℹ️ No se encontraron oportunidades significativas de pricing")
        
        # Resumen financiero
        st.markdown("#### 💼 Resumen de Impacto Financiero")
        
        col3, col4, col5 = st.columns(3)
        
        with col3:
            total_oportunidad = df['valor_perdido_TOTAL'].sum() + df['costo_exceso_STK'].sum()
            st.metric("🎯 Oportunidad Total", f"${total_oportunidad:,.0f}")
        
        with col4:
            productos_oportunidad = len(df[df['impacto_financiero_total'] > 0])
            st.metric("📈 Productos con Oportunidad", productos_oportunidad)
        
        with col5:
            promedio_impacto = df['impacto_financiero_total'].mean()
            st.metric("📊 Impacto Promedio", f"${promedio_impacto:,.0f}")
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_performance_sucursal(self, df):
        """Análisis de performance por sucursal"""
        st.markdown("### 🏪 Performance por Sucursal")
        
        start_time = time.time()
        
        # Definir sucursales
        sucursales = ['corrientes', 'express', 'formosa', 'hiper']
        
        # Crear métricas por sucursal
        sucursal_data = []
        
        for suc in sucursales:
            stock_col = f'stk_{suc}'
            cnt_col = f'{suc[:3]}_cnt_day'
            abastecer_col = f'{suc[:3]}_abastecer'
            
            if stock_col in df.columns:
                stock_total = df[stock_col].sum()
                productos_con_stock = len(df[df[stock_col] > 0])
                productos_sin_stock = len(df[df[stock_col] == 0])
                
                if cnt_col in df.columns:
                    ventas_dia = df[cnt_col].sum()
                else:
                    ventas_dia = 0
                    
                if abastecer_col in df.columns:
                    necesidad_reposicion = df[abastecer_col].sum()
                else:
                    necesidad_reposicion = 0
                
                sucursal_data.append({
                    'Sucursal': suc.title(),
                    'Stock Total': stock_total,
                    'Productos con Stock': productos_con_stock,
                    'Productos sin Stock': productos_sin_stock,
                    'Ventas Último Día': ventas_dia,
                    'Necesidad Reposición': necesidad_reposicion,
                    'Eficiencia Stock %': round((productos_con_stock / len(df)) * 100, 1) if len(df) > 0 else 0
                })
        
        if sucursal_data:
            df_sucursales = pd.DataFrame(sucursal_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Comparativa de Stock por Sucursal")
                fig = px.bar(
                    df_sucursales,
                    x='Sucursal',
                    y=['Productos con Stock', 'Productos sin Stock'],
                    title="Distribución de Stock por Sucursal"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### 🔄 Necesidades de Reposición")
                fig = px.bar(
                    df_sucursales,
                    x='Sucursal',
                    y='Necesidad Reposición',
                    title="Unidades a Reabastecer por Sucursal",
                    color='Necesidad Reposición',
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### 📋 Resumen Detallado por Sucursal")
            st.dataframe(df_sucursales, use_container_width=True)
            
            # Análisis de eficiencia
            st.markdown("#### 🎯 Ranking de Eficiencia")
            df_ranking = df_sucursales.sort_values('Eficiencia Stock %', ascending=False)
            
            for i, row in df_ranking.iterrows():
                eficiencia = row['Eficiencia Stock %']
                if eficiencia >= 80:
                    emoji = "🟢"
                elif eficiencia >= 60:
                    emoji = "🟡"
                else:
                    emoji = "🔴"
                
                st.write(f"{emoji} **{row['Sucursal']}**: {eficiencia}% de productos con stock")
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_gestion_inventario(self, df):
        """Gestión de inventario - excesos vs faltantes"""
        st.markdown("### 📦 Gestión de Inventario")
        
        start_time = time.time()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📈 Productos por Categoría de Rotación")
            rotacion_counts = df['categoria_rotacion'].value_counts()
            
            fig = px.pie(
                values=rotacion_counts.values,
                names=rotacion_counts.index,
                title="Distribución por Velocidad de Rotación"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### ⚖️ Balance Inventario")
            
            productos_exceso = len(df[df['exceso_STK'] > 0])
            productos_faltante = len(df[df['valor_perdido_TOTAL'] > 0])
            productos_optimo = len(df) - productos_exceso - productos_faltante
            
            balance_data = pd.DataFrame({
                'Estado': ['🔴 Con Exceso', '🟡 Con Faltante', '🟢 Óptimo'],
                'Cantidad': [productos_exceso, productos_faltante, productos_optimo]
            })
            
            fig = px.bar(
                balance_data,
                x='Estado',
                y='Cantidad',
                title="Balance General del Inventario",
                color='Estado'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Análisis detallado de excesos
        st.markdown("#### 📊 Análisis de Excesos de Stock")
        
        productos_exceso_df = df[df['exceso_STK'] > 0].nlargest(10, 'costo_exceso_STK')[
            ['descripcion', 'exceso_STK', 'costo_exceso_STK', 'familia', 'dias_cobertura']
        ]
        
        if not productos_exceso_df.empty:
            st.dataframe(productos_exceso_df, use_container_width=True)
            
            # Resumen de excesos
            col3, col4, col5 = st.columns(3)
            
            with col3:
                total_exceso_unidades = df['exceso_STK'].sum()
                st.metric("📦 Total Unidades Exceso", f"{total_exceso_unidades:,.0f}")
            
            with col4:
                total_costo_exceso = df['costo_exceso_STK'].sum()
                st.metric("💰 Costo Total Exceso", f"${total_costo_exceso:,.0f}")
            
            with col5:
                promedio_dias_exceso = df[df['exceso_STK'] > 0]['dias_cobertura'].mean()
                st.metric("📅 Días Cobertura Promedio", f"{promedio_dias_exceso:.0f}")
        else:
            st.success("✅ No hay productos con exceso de stock significativo")
        
        # Productos sin stock
        st.markdown("#### ❌ Productos Sin Stock")
        sin_stock = df[df['STK_TOTAL'] == 0][
            ['descripcion', 'valor_perdido_TOTAL', 'familia', 'nivel_riesgo']
        ].head(10)
        
        if not sin_stock.empty:
            st.dataframe(sin_stock, use_container_width=True)
        else:
            st.success("✅ Todos los productos tienen stock disponible")
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_analisis_familia(self, df):
        """Análisis por familia y proveedor"""
        st.markdown("### 📊 Análisis por Familia y Proveedor")
        
        start_time = time.time()
        
        # Análisis por familia
        if 'familia' in df.columns:
            st.markdown("#### 🏷️ Performance por Familia")
            
            familia_stats = df.groupby('familia').agg({
                'idarticulo': 'count',
                'valor_perdido_TOTAL': 'sum',
                'costo_exceso_STK': 'sum',
                'STK_TOTAL': 'sum',
                'impacto_financiero_total': 'sum'
            }).round(0)
            
            familia_stats.columns = ['Productos', 'Valor Perdido', 'Costo Exceso', 
                                   'Stock Total', 'Impacto Total']
            familia_stats = familia_stats.sort_values('Impacto Total', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # TOP familias por impacto
                top_familias = familia_stats.head(10)
                fig = px.bar(
                    x=top_familias.index,
                    y=top_familias['Impacto Total'],
                    title="TOP 10 Familias por Impacto Financiero"
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Distribución de productos por familia
                fig = px.pie(
                    values=familia_stats['Productos'],
                    names=familia_stats.index,
                    title="Distribución de Productos por Familia"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(familia_stats, use_container_width=True)
        
        # Análisis por proveedor
        if 'proveedor' in df.columns:
            st.markdown("#### 🏢 Performance por Proveedor")
            
            proveedor_stats = df.groupby('proveedor').agg({
                'idarticulo': 'count',
                'valor_perdido_TOTAL': 'sum',
                'costo_exceso_STK': 'sum',
                'impacto_financiero_total': 'sum'
            }).round(0)
            
            proveedor_stats.columns = ['Productos', 'Valor Perdido', 'Costo Exceso', 'Impacto Total']
            proveedor_stats = proveedor_stats.sort_values('Impacto Total', ascending=False).head(15)
            
            if not proveedor_stats.empty:
                fig = px.bar(
                    x=proveedor_stats.index,
                    y=proveedor_stats['Impacto Total'],
                    title="TOP 15 Proveedores por Impacto Financiero"
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(proveedor_stats, use_container_width=True)
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")
    
    def tab_acciones_inmediatas(self, df):
        """TOP acciones inmediatas"""
        st.markdown("### ⚡ Acciones Inmediatas Recomendadas")
        
        start_time = time.time()
        
        # TOP 20 productos que requieren acción inmediata
        st.markdown("#### 🚨 TOP 20 - Acción Inmediata Requerida")
        
        # Crear score de prioridad
        df['score_prioridad'] = (
            (df['valor_perdido_TOTAL'] * 0.4) +
            (df['costo_exceso_STK'] * 0.3) +
            ((11 - df['prioridad']) * 100 * 0.2) +  # Invertir prioridad
            (df['total_abastecer'] * df['costo_unit'] * 0.1)
        )
        
        top_acciones = df.nlargest(20, 'score_prioridad')[
            ['idarticulo', 'descripcion', 'familia', 'nivel_riesgo', 
             'dias_cobertura', 'valor_perdido_TOTAL', 'costo_exceso_STK',
             'total_abastecer', 'prioridad', 'score_prioridad']
        ]
        
        # Asignar tipo de acción
        def determinar_accion(row):
            if row['valor_perdido_TOTAL'] > 0:
                return "🔄 REABASTECER"
            elif row['costo_exceso_STK'] > 0:
                return "📉 REDUCIR STOCK"
            elif row['total_abastecer'] > 0:
                return "🔄 REPONER"
            else:
                return "👀 MONITOREAR"
        
        top_acciones['Acción Recomendada'] = top_acciones.apply(determinar_accion, axis=1)
        
        # Mostrar con formato condicional
        st.dataframe(
            top_acciones.drop(['score_prioridad'], axis=1),
            use_container_width=True
        )
        
        # Resumen de acciones
        st.markdown("#### 📋 Resumen de Acciones por Tipo")
        
        resumen_acciones = top_acciones['Acción Recomendada'].value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(
                values=resumen_acciones.values,
                names=resumen_acciones.index,
                title="Distribución de Tipos de Acción"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 💰 Impacto Financiero de Acciones")
            
            impacto_reabastecer = top_acciones[
                top_acciones['Acción Recomendada'] == "🔄 REABASTECER"
            ]['valor_perdido_TOTAL'].sum()
            
            impacto_reducir = top_acciones[
                top_acciones['Acción Recomendada'] == "📉 REDUCIR STOCK"
            ]['costo_exceso_STK'].sum()
            
            st.metric("💸 Pérdidas por Reabastecimiento", f"${impacto_reabastecer:,.0f}")
            st.metric("📊 Ahorro por Reducción", f"${impacto_reducir:,.0f}")
            st.metric("🎯 Oportunidad Total", f"${impacto_reabastecer + impacto_reducir:,.0f}")
        
        # Plan de acción detallado
        st.markdown("#### 📝 Plan de Acción Detallado")
        
        plan_reabastecimiento = top_acciones[
            top_acciones['Acción Recomendada'].str.contains('REABASTECER|REPONER')
        ][['descripcion', 'total_abastecer', 'valor_perdido_TOTAL', 'familia']].head(10)
        
        if not plan_reabastecimiento.empty:
            st.markdown("**🔄 Productos para Reabastecer:**")
            st.dataframe(plan_reabastecimiento, use_container_width=True)
        
        plan_reduccion = top_acciones[
            top_acciones['Acción Recomendada'] == "📉 REDUCIR STOCK"
        ][['descripcion', 'costo_exceso_STK', 'dias_cobertura', 'familia']].head(10)
        
        if not plan_reduccion.empty:
            st.markdown("**📉 Productos para Reducir Stock:**")
            st.dataframe(plan_reduccion, use_container_width=True)
        
        exec_time = time.time() - start_time
        st.info(f"⏱️ Análisis completado en {exec_time:.2f} segundos")

# ====================================================================================
# FUNCIÓN PRINCIPAL PARA INTEGRAR EN TU CLASE EXISTENTE
# ====================================================================================

def show_strategic_analysis(self, df_presu):
    """
    Función principal para mostrar el análisis estratégico
    Integra en tu clase existente reemplazando show_idarticulo_analysis_01
    """
    if df_presu is None or df_presu.empty:
        st.warning("⚠️ No hay datos disponibles para análisis estratégico.")
        return
    
    st.markdown("# 🎯 Análisis Estratégico de Inventario")
    st.markdown("---")
    
    # Inicializar dashboard
    dashboard = InventoryDashboard()
    
    # Procesar datos
    with st.spinner("🔄 Procesando datos..."):
        df_processed = dashboard.load_and_validate_data(df_presu)
    
    if df_processed is not None:
        # Mostrar dashboard completo
        dashboard.show_strategic_dashboard(df_processed)
        
        # Botón para exportar resultados
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Exportar Dashboard", type="primary"):
                st.success("✅ Funcionalidad de exportación lista para implementar")
        
        with col2:
            if st.button("🔄 Actualizar Análisis"):
                st.rerun()
        
        with col3:
            if st.button("📧 Generar Reporte"):
                st.info("📋 Reporte ejecutivo generado (funcionalidad por implementar)")

# ====================================================================================
# FUNCIONES AUXILIARES PARA ANÁLISIS ESPECÍFICOS
# ====================================================================================

def analyze_stock_efficiency(df):
    """Análisis específico de eficiencia de stock"""
    start_time = time.time()
    
    # Calcular métricas de eficiencia
    efficiency_metrics = {}
    
    # Rotación promedio
    avg_coverage = df['dias_cobertura'].mean()
    efficiency_metrics['cobertura_promedio'] = avg_coverage
    
    # Productos en rango óptimo (15-45 días)
    optimal_range = df[
        (df['dias_cobertura'] >= 15) & 
        (df['dias_cobertura'] <= 45)
    ]
    efficiency_metrics['productos_optimos'] = len(optimal_range)
    efficiency_metrics['pct_optimos'] = (len(optimal_range) / len(df)) * 100
    
    # Productos críticos
    critical_products = df[df['dias_cobertura'] < 15]
    efficiency_metrics['productos_criticos'] = len(critical_products)
    efficiency_metrics['pct_criticos'] = (len(critical_products) / len(df)) * 100
    
    # Productos con exceso
    excess_products = df[df['dias_cobertura'] > 60]
    efficiency_metrics['productos_exceso'] = len(excess_products)
    efficiency_metrics['pct_exceso'] = (len(excess_products) / len(df)) * 100
    
    exec_time = time.time() - start_time
    efficiency_metrics['tiempo_calculo'] = exec_time
    
    return efficiency_metrics

def generate_executive_summary(df):
    """Generar resumen ejecutivo"""
    summary = {
        'total_productos': len(df),
        'valor_perdido_total': df['valor_perdido_TOTAL'].sum(),
        'costo_exceso_total': df['costo_exceso_STK'].sum(),
        'productos_criticos': len(df[df['nivel_riesgo'].str.contains('🔴', na=False)]),
        'productos_sin_stock': len(df[df['STK_TOTAL'] == 0]),
        'oportunidad_total': df['valor_perdido_TOTAL'].sum() + df['costo_exceso_STK'].sum(),
        'productos_accion_inmediata': len(df[
            (df['valor_perdido_TOTAL'] > 0) | 
            (df['costo_exceso_STK'] > 0) |
            (df['prioridad'] <= 3)
        ])
    }
    
    return summary

def create_priority_matrix(df):
    """Crear matriz de priorización avanzada"""
    # Normalizar métricas para crear score
    df_matrix = df.copy()
    
    # Normalizar valor perdido (0-100)
    if df_matrix['valor_perdido_TOTAL'].max() > 0:
        df_matrix['score_perdido'] = (
            df_matrix['valor_perdido_TOTAL'] / df_matrix['valor_perdido_TOTAL'].max()
        ) * 100
    else:
        df_matrix['score_perdido'] = 0
    
    # Normalizar costo exceso (0-100)
    if df_matrix['costo_exceso_STK'].max() > 0:
        df_matrix['score_exceso'] = (
            df_matrix['costo_exceso_STK'] / df_matrix['costo_exceso_STK'].max()
        ) * 100
    else:
        df_matrix['score_exceso'] = 0
    
    # Score de urgencia (invertir prioridad)
    df_matrix['score_urgencia'] = (11 - df_matrix['prioridad']) * 10
    
    # Score total combinado
    df_matrix['score_total'] = (
        df_matrix['score_perdido'] * 0.4 +
        df_matrix['score_exceso'] * 0.3 +
        df_matrix['score_urgencia'] * 0.3
    )
    
    # Clasificar en cuadrantes
    urgencia_threshold = df_matrix['score_urgencia'].quantile(0.7)
    impacto_threshold = df_matrix['score_perdido'].quantile(0.7)
    
    def clasificar_cuadrante(row):
        if row['score_urgencia'] >= urgencia_threshold and row['score_perdido'] >= impacto_threshold:
            return "🚨 Crítico"
        elif row['score_urgencia'] >= urgencia_threshold:
            return "⚠️ Urgente"
        elif row['score_perdido'] >= impacto_threshold:
            return "💰 Alto Impacto"
        else:
            return "📊 Rutinario"
    
    df_matrix['cuadrante'] = df_matrix.apply(clasificar_cuadrante, axis=1)
    
    return df_matrix

# ====================================================================================
# MÉTRICAS AVANZADAS Y ANÁLISIS PREDICTIVO
# ====================================================================================

def calculate_inventory_health_score(df):
    """Calcular score de salud del inventario (0-100)"""
    
    # Componentes del score
    scores = {}
    
    # 1. Cobertura adecuada (30% del score)
    optimal_coverage = len(df[(df['dias_cobertura'] >= 15) & (df['dias_cobertura'] <= 45)])
    scores['cobertura'] = (optimal_coverage / len(df)) * 30
    
    # 2. Sin quiebres críticos (25% del score)
    no_critical = len(df[~df['nivel_riesgo'].str.contains('🔴', na=False)])
    scores['sin_criticos'] = (no_critical / len(df)) * 25
    
    # 3. Control de excesos (20% del score)
    no_excess = len(df[df['exceso_STK'] == 0])
    scores['sin_excesos'] = (no_excess / len(df)) * 20
    
    # 4. Eficiencia financiera (15% del score)
    low_impact = len(df[df['impacto_financiero_total'] <= df['impacto_financiero_total'].quantile(0.5)])
    scores['eficiencia'] = (low_impact / len(df)) * 15
    
    # 5. Disponibilidad (10% del score)
    with_stock = len(df[df['STK_TOTAL'] > 0])
    scores['disponibilidad'] = (with_stock / len(df)) * 10
    
    total_score = sum(scores.values())
    
    return {
        'score_total': round(total_score, 1),
        'componentes': scores,
        'clasificacion': get_health_classification(total_score)
    }

def get_health_classification(score):
    """Clasificar salud del inventario"""
    if score >= 85:
        return "🟢 Excelente"
    elif score >= 70:
        return "🟡 Bueno"
    elif score >= 55:
        return "🟠 Regular"
    else:
        return "🔴 Crítico"

# ====================================================================================
# EJEMPLO DE USO E INTEGRACIÓN
# ====================================================================================

"""
INSTRUCCIONES DE INTEGRACIÓN:

1. Reemplaza tu función show_idarticulo_analysis_01 con show_strategic_analysis

2. En tu clase principal, agrega este método:

def show_strategic_inventory_analysis(self, df_presu):
    show_strategic_analysis(self, df_presu)

3. Para usar métricas específicas:

# Calcular eficiencia
efficiency = analyze_stock_efficiency(df_presu)
st.write(f"Eficiencia general: {efficiency['pct_optimos']:.1f}%")

# Generar resumen ejecutivo
summary = generate_executive_summary(df_presu)
st.metric("Oportunidad Total", f"${summary['oportunidad_total']:,.0f}")

# Calcular salud del inventario
health = calculate_inventory_health_score(df_presu)
st.metric("Salud del Inventario", f"{health['score_total']}% {health['clasificacion']}")

4. Tiempo de ejecución estimado:
   - Dataset de 1,000 productos: ~3-5 segundos
   - Dataset de 10,000 productos: ~15-25 segundos
   - Todas las visualizaciones incluyen medición de tiempo

5. Características implementadas:
   ✅ Medición de tiempo en todas las operaciones
   ✅ Progress bars para carga de datos
   ✅ Outputs visuales profesionales con emojis
   ✅ Análisis por grupos estratégicos
   ✅ Múltiples niveles de análisis (KPIs, detalles, acciones)
   ✅ Integración completa con Streamlit
   ✅ Manejo de errores y validaciones
"""