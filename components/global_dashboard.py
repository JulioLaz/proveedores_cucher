import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import pandas as pd
from io import BytesIO
from datetime import datetime

def show_global_dashboard(df_proveedores, query_function, credentials_path, project_id, bigquery_table):
    """Dashboard Global de Proveedores - Vista inicial con ranking por ventas y presupuesto"""
    
   
    # === SELECTOR DE PERÍODO ===
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        periodo_opciones = {
            "Últimos 30 días": 30,
            "Últimos 60 días": 60,
            "Últimos 90 días": 90,
            "Últimos 6 meses": 180,
            "Último año": 365,
            "Personalizado": None
        }
        
        periodo_seleccionado = st.selectbox(
            "📅 Período de análisis de ventas:",
            options=list(periodo_opciones.keys()),
            index=0
        )
    
    with col2:
        if periodo_seleccionado == "Personalizado":
            from datetime import datetime, timedelta
            col_a, col_b = st.columns(2)
            fecha_desde = col_a.date_input("Desde:", value=datetime.now().date() - timedelta(days=30))
            fecha_hasta = col_b.date_input("Hasta:", value=datetime.now().date())
            dias_periodo = (fecha_hasta - fecha_desde).days
        else:
            dias_periodo = periodo_opciones[periodo_seleccionado]
            from datetime import datetime, timedelta
            fecha_hasta = datetime.now().date()
            fecha_desde = fecha_hasta - timedelta(days=dias_periodo)
    
    with col3:
        st.metric("📆 Días", f"{dias_periodo}")
    
    # === ESTILOS CSS MEJORADOS ===
    st.markdown("""
    <style>
        .metric-box {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        
        .metric-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        
        .metric-box-green {
            background: linear-gradient(135deg, #d4fc79 0%, #96e6a1 100%);
        }
        
        .metric-box-orange {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }
        
        .metric-box-blue {
            background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);
            color: white;
        }
        
        .metric-box-purple {
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        }
        
        .metric-box-red {
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # === CARGA DE DATOS DE VENTAS CON FILTRO DE FECHA ===
    with st.spinner(f"🔄 Cargando ventas de los últimos {dias_periodo} días y presupuesto..."):
        start_time = time.time()
        
        from google.cloud import bigquery
        client = bigquery.Client.from_service_account_json(credentials_path)
        
        query_ventas = f"""
        SELECT 
            idarticulo,
            SUM(precio_total) as venta_total,
            SUM(cantidad_total) as cantidad_vendida
        FROM `{project_id}.{bigquery_table}`
        WHERE DATE(fecha_comprobante) BETWEEN '{fecha_desde}' AND '{fecha_hasta}'
        GROUP BY idarticulo
        """
        
        df_ventas = client.query(query_ventas).to_dataframe()
        
        df_presupuesto = query_function(
            credentials_path=credentials_path,
            project_id=project_id,
            dataset='presupuesto',
            table='result_final_alert_all'
        )
        
        load_time = time.time() - start_time
    
    if df_ventas is None or df_ventas.empty or df_presupuesto is None or df_presupuesto.empty:
        st.error("❌ No se pudieron cargar los datos necesarios")
        return
    
    # st.success(f"✅ Datos cargados en {load_time:.2f}s | {len(df_ventas):,} artículos con ventas ({dias_periodo} días) | {len(df_presupuesto):,} artículos con presupuesto")
    
    # === MERGE Y AGREGACIÓN ===
    df_merge = df_proveedores[['idarticulo', 'proveedor', 'idproveedor']].merge(
        df_ventas, on='idarticulo', how='left'
    ).merge(
        df_presupuesto[['idarticulo', 'PRESUPUESTO', 'exceso_STK', 'costo_exceso_STK', 'STK_TOTAL']],
        on='idarticulo',
        how='left'
    )
    
    df_merge['venta_total'] = df_merge['venta_total'].fillna(0)
    df_merge['cantidad_vendida'] = df_merge['cantidad_vendida'].fillna(0)
    df_merge['PRESUPUESTO'] = df_merge['PRESUPUESTO'].fillna(0)
    df_merge['exceso_STK'] = df_merge['exceso_STK'].fillna(0)
    df_merge['costo_exceso_STK'] = df_merge['costo_exceso_STK'].fillna(0)
    df_merge['STK_TOTAL'] = df_merge['STK_TOTAL'].fillna(0)
    
    ranking = df_merge.groupby(['proveedor', 'idproveedor']).agg({
        'venta_total': 'sum',
        'cantidad_vendida': 'sum',
        'idarticulo': 'count',
        'PRESUPUESTO': 'sum',
        'exceso_STK': lambda x: (x > 0).sum(),
        'costo_exceso_STK': 'sum',
        'STK_TOTAL': lambda x: (x == 0).sum()
    }).reset_index()
    
    ranking.columns = [
        'Proveedor', 'ID', 'Venta Total', 'Cantidad Vendida', 
        'Artículos', 'Presupuesto', 'Art. con Exceso', 
        'Costo Exceso', 'Art. Sin Stock'
    ]
    
    ranking['% Participación Ventas'] = (ranking['Venta Total'] / ranking['Venta Total'].sum() * 100).round(2)
    ranking = ranking.sort_values('Venta Total', ascending=False).reset_index(drop=True)
    ranking['Ranking'] = range(1, len(ranking) + 1)
    
    # === KPIs PRINCIPALES CON ESTILO MEJORADO ===
    st.markdown("---")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-box metric-box-green">
            <div style="text-align: center;">
                <div style="font-size: 1rem; color: #555;">💰 Ventas Totales</div>
                <div style="font-size: 1.5rem; font-weight: bold; color: #1e3c72;">${ranking['Venta Total'].sum():,.0f}</div>
            </div>
            <div style="color: green; font-size: 0.8rem; margin-top: 0.2rem;">
                ⬆️ {len(ranking)} proveedores
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-box metric-box-orange">
            <div style="text-align: center;">
                <div style="font-size: 1rem; color: #555;">💵 Presupuesto Total</div>
                <div style="font-size: 1.5rem; font-weight: bold; color: #1e3c72;">${ranking['Presupuesto'].sum():,.0f}</div>
            </div>
            <div style="color: #d35400; font-size: 0.8rem; margin-top: 0.2rem;">
                📊 Inversión requerida
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-box metric-box-blue">
            <div style="text-align: center;">
                <div style="font-size: 1rem; color: white;">📦 Cantidad Vendida</div>
                <div style="font-size: 1.5rem; font-weight: bold; color: white;">{ranking['Cantidad Vendida'].sum():,.0f}</div>
            </div>
            <div style="color: white; font-size: 0.8rem; margin-top: 0.2rem;">
                🎯 {df_ventas['idarticulo'].nunique():,} artículos totales #            

            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-box metric-box-purple">
            <div style="text-align: center;">
                <div style="font-size: 1rem; color: #555;">⚠️ Exceso de Stock</div>
                <div style="font-size: 1.5rem; font-weight: bold; color: #1e3c72;">${ranking['Costo Exceso'].sum():,.0f}</div>
            </div>
            <div style="color: #888; font-size: 0.8rem; margin-top: 0.2rem;">
                📊 {ranking['Art. con Exceso'].sum():,} artículos
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-box metric-box-red">
            <div style="text-align: center;">
                <div style="font-size: 1rem; color: #555;">❌ Sin Stock</div>
                <div style="font-size: 1.5rem; font-weight: bold; color: #1e3c72;">{ranking['Art. Sin Stock'].sum():,}</div>
            </div>
            <div style="color: #c0392b; font-size: 0.8rem; margin-top: 0.2rem;">
                🔴 Artículos críticos
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # === VISUALIZACIONES ===
    st.markdown("---")
   #  st.markdown("### 📊 Análisis Visual de Proveedores")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # TOP VENTAS con slider
        st.markdown("#### 🏆 Ranking por Venta Total")
        top_ventas_num = st.slider("Cantidad de proveedores (Ventas):", 5, 80, 20, step=5, key='slider_ventas')
        
        top_ventas = ranking.head(top_ventas_num).copy()
        top_ventas['Venta_M'] = top_ventas['Venta Total'] / 1_000_000
        top_ventas['Texto'] = top_ventas['Venta Total'].apply(lambda x: f"${x/1_000_000:.1f}M")
        
        fig_ventas = go.Figure(go.Bar(
            y=top_ventas['Proveedor'][::-1],
            x=top_ventas['Venta_M'][::-1],
            orientation='h',
            text=top_ventas['Texto'][::-1],
            textposition='outside',
            marker_color='#2ecc71',
            hovertemplate='<b>%{y}</b><br>Venta: %{text}<br>Participación: ' + 
                          top_ventas['% Participación Ventas'][::-1].apply(lambda x: f"{x:.1f}%") + '<extra></extra>'
        ))
        
        fig_ventas.update_layout(
            height=max(400, top_ventas_num * 25),
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis=dict(visible=False),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig_ventas, use_container_width=True)
    
    with col2:
        # TOP PRESUPUESTO con slider
        st.markdown("#### 💰 Ranking por Presupuesto")
        top_presu_num = st.slider("Cantidad de proveedores (Presupuesto):", 5, 80, 20, step=5, key='slider_presu')
        
        ranking_presu = ranking.sort_values('Presupuesto', ascending=False).head(top_presu_num).copy()
        ranking_presu['Presupuesto_M'] = ranking_presu['Presupuesto'] / 1_000_000
        ranking_presu['Texto'] = ranking_presu['Presupuesto'].apply(lambda x: f"${x/1_000_000:.1f}M")
        
        fig_presu = go.Figure(go.Bar(
            y=ranking_presu['Proveedor'][::-1],
            x=ranking_presu['Presupuesto_M'][::-1],
            orientation='h',
            text=ranking_presu['Texto'][::-1],
            textposition='outside',
            marker_color='#e74c3c',
            hovertemplate='<b>%{y}</b><br>Presupuesto: %{text}<extra></extra>'
        ))
        
        fig_presu.update_layout(
            height=max(400, top_presu_num * 25),
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis=dict(visible=False),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig_presu, use_container_width=True)
    
    # === TABLA RANKING DETALLADA ===
    st.markdown("---")
    st.markdown("### 📋 Ranking Detallado de Proveedores")
    
    # Formatear columnas para display
    df_display = ranking.copy()
    df_display['Venta Total'] = df_display['Venta Total'].apply(lambda x: f"${x:,.0f}")
    df_display['Presupuesto'] = df_display['Presupuesto'].apply(lambda x: f"${x:,.0f}")
    df_display['Costo Exceso'] = df_display['Costo Exceso'].apply(lambda x: f"${x:,.0f}")
    df_display['% Participación Ventas'] = df_display['% Participación Ventas'].apply(lambda x: f"{x:.2f}%")
    
    # Slider para cantidad de proveedores en tabla
    num_mostrar = st.slider("Cantidad de proveedores a mostrar:", 10, len(df_display), 20, step=5, key='slider_tabla')
    
    st.dataframe(
        df_display.head(num_mostrar)[[
            'Ranking', 'Proveedor', 'Venta Total', '% Participación Ventas',
            'Presupuesto', 'Artículos', 'Art. con Exceso', 
            'Costo Exceso', 'Art. Sin Stock'
        ]],
        use_container_width=True,
        hide_index=True
    )
    
    # === INSIGHTS AUTOMÁTICOS ===
    st.markdown("---")
    st.markdown("### 💡 Insights Clave")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        top_proveedor = ranking.iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #4caf50'>
        <b>🏆 Proveedor Líder en Ventas</b><br>
        <b>{top_proveedor['Proveedor']}</b><br>
        💰 ${top_proveedor['Venta Total']:,.0f}<br>
        📊 {top_proveedor['% Participación Ventas']:.1f}% del total<br>
        📦 {top_proveedor['Artículos']} artículos
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        top_presupuesto = ranking.nlargest(1, 'Presupuesto').iloc[0]
        st.markdown(f"""
        <div style='background-color:#fff3e0;padding:1rem;border-radius:10px;border-left:5px solid #ff9800'>
        <b>💰 Mayor Presupuesto Requerido</b><br>
        <b>{top_presupuesto['Proveedor']}</b><br>
        💵 ${top_presupuesto['Presupuesto']:,.0f}<br>
        📦 {top_presupuesto['Artículos']} artículos<br>
        🎯 Inversión prioritaria
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        mas_exceso = ranking.nlargest(1, 'Costo Exceso').iloc[0]
        st.markdown(f"""
        <div style='background-color:#ffebee;padding:1rem;border-radius:10px;border-left:5px solid #f44336'>
        <b>⚠️ Mayor Exceso de Stock</b><br>
        <b>{mas_exceso['Proveedor']}</b><br>
        💸 ${mas_exceso['Costo Exceso']:,.0f} inmovilizado<br>
        📊 {mas_exceso['Art. con Exceso']} artículos<br>
        🔄 Optimizar inventario
        </div>
        """, unsafe_allow_html=True)
    
    # === EXPORTAR RANKING ===
    st.markdown("---")
    
   #  # Preparar CSV con datos sin formato
   #  df_export = ranking[[
   #      'Ranking', 'Proveedor', 'Venta Total', '% Participación Ventas',
   #      'Presupuesto', 'Artículos', 'Cantidad Vendida',
   #      'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
   #  ]].copy()
    
   #  csv = df_export.to_csv(index=False).encode('utf-8')
   #  st.download_button(
   #      "📥 Descargar Ranking Completo (CSV)",
   #      csv,
   #      f"ranking_proveedores_{datetime.now().strftime('%Y%m%d')}.csv",
   #      "text/csv",
   #      use_container_width=True
   #  )

   # Preparar DataFrame con datos sin formato
    df_export = ranking[[
      'Ranking', 'Proveedor', 'Venta Total', '% Participación Ventas',
      'Presupuesto', 'Artículos', 'Cantidad Vendida',
      'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
   ]].copy()

   # Crear buffer en memoria para el archivo Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
      df_export.to_excel(writer, index=False, sheet_name='Ranking')
    output.seek(0)  # volver al inicio del buffer

   # Botón de descarga en formato XLSX
    st.download_button(
      label="📥 Descargar Ranking Completo (Excel)",
      data=output,
      file_name=f"ranking_proveedores_{datetime.now().strftime('%Y%m%d')}.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      use_container_width=True
   )
