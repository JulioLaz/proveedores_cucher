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

    st.markdown("""
    <style>
    .rounded-box {
        background-color: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Envolver las columnas en un div con la clase
    st.markdown('<div class="rounded-box">', unsafe_allow_html=True)

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
        if periodo_seleccionado == "Personalizado" or periodo_opciones.keys() != []:
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
    st.markdown('</div>', unsafe_allow_html=True)

    # === ESTILOS CSS MEJORADOS ===
    st.markdown("""
    <style>
        .metric-box {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            padding: 0.8rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            # height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            border-left: 5px solid #2a5298;
            margin-bottom: .5rem;
                
        }
        
        .metric-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        
    </style>
    """, unsafe_allow_html=True)

    
    # === CARGA DE DATOS DE VENTAS CON FILTRO DE FECHA ===
    with st.spinner(f"🔄 Cargando ventas de los últimos {dias_periodo} días y presupuesto..."):
        # start_time = time.time()
        
        from google.cloud import bigquery
        client = bigquery.Client.from_service_account_json(credentials_path)
        
        query_ventas = f"""
        SELECT 
            idarticulo,
            SUM(precio_total) as venta_total,
            SUM(costo_total) as costo_total,
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
        
        # load_time = time.time() - start_time
    
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
    df_merge['costo_total'] = df_merge['costo_total'].fillna(0)
    df_merge['cantidad_vendida'] = df_merge['cantidad_vendida'].fillna(0)
    df_merge['PRESUPUESTO'] = df_merge['PRESUPUESTO'].fillna(0)
    df_merge['exceso_STK'] = df_merge['exceso_STK'].fillna(0)
    df_merge['costo_exceso_STK'] = df_merge['costo_exceso_STK'].fillna(0)
    df_merge['STK_TOTAL'] = df_merge['STK_TOTAL'].fillna(0)
    
    ranking = df_merge.groupby(['proveedor', 'idproveedor']).agg({
        'venta_total': 'sum',
        'costo_total': 'sum',
        'cantidad_vendida': 'sum',
        'idarticulo': 'count',
        'PRESUPUESTO': 'sum',
        'exceso_STK': lambda x: (x > 0).sum(),
        'costo_exceso_STK': 'sum',
        'STK_TOTAL': lambda x: (x == 0).sum()
    }).reset_index()
    
    ranking.columns = [
        'Proveedor', 'ID', 'Venta Total', 'Costo Total', 'Cantidad Vendida', 
        'Artículos', 'Presupuesto', 'Art. con Exceso', 
        'Costo Exceso', 'Art. Sin Stock'
    ]
    
    
    ranking['Utilidad'] = (ranking['Venta Total'] - ranking['Costo Total']).round(0).astype(int)
    ranking['Rentabilidad %'] = ((ranking['Utilidad'] / ranking['Venta Total']) * 100).round(2)
    ranking['% Participación Presupuesto'] = (ranking['Presupuesto'] / ranking['Presupuesto'].sum() * 100).round(2)
    ranking['% Participación Ventas'] = (ranking['Venta Total'] / ranking['Venta Total'].sum() * 100).round(2)
    ranking['% Participación Utilidad'] = (ranking['Utilidad'] / ranking['Utilidad'].sum() * 100).round(2)
    ranking = ranking.sort_values('Venta Total', ascending=False).reset_index(drop=True)
    ranking['Ranking'] = range(1, len(ranking) + 1)
    
    # === KPIs PRINCIPALES EN LA PARTE SUPERIOR ===    
    def format_millones(valor):
        """
        Formatea valores monetarios a millones con formato: 10.536 mll
        """
        if valor >= 1_000_000:
            millones = valor / 1_000_000
            return f"{millones:,.0f} mll".replace(',', 'X').replace('.', ',').replace('X', '.')
        elif valor >= 1_000:
            return f"{valor/1_000:,.0f} mil".replace(',', '.')
        else:
            return f"{valor:,.0f}"

    # Luego en tus KPIs:
    col1, col11, col2, col3, col4, col5 = st.columns(6)
        
    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">💰 Ventas Totales</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Venta Total'].sum())}</div>
            </div>
            <div style="color: green; font-size: 12px; margin-top: 0.2rem;">
                ⬆️ {len(ranking)} proveedores
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col11:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">💰 Utilidad Total</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Utilidad'].sum())}</div>
            </div>
            <div style="color: green; font-size: 12px; margin-top: 0.2rem;">
                ⬆️ {len(ranking)} proveedores
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">💵 Presupuesto a 30 días</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Presupuesto'].sum())}</div>
            </div>
            <div style="color: #d35400; font-size: 12px; margin-top: 0.2rem;">
                📊 Inversión requerida
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">📦 Cantidad Vendida</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">{format_millones(ranking['Cantidad Vendida'].sum())}</div>
            </div>
            <div style="color: #555; font-size: 12px; margin-top: 0.2rem;">
                🎯 {df_ventas['idarticulo'].nunique():,} art únicos
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">⚠️ Exceso de Stock</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">${format_millones(ranking['Costo Exceso'].sum())}</div>
            </div>
            <div style="color: #888; font-size: 12px; margin-top: 0.2rem;">
                📊 {ranking['Art. con Exceso'].sum():,} artículos
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-box">
            <div style="text-align: center;">
                <div style="font-size: 14px; color: #555;">❌ Sin Stock</div>
                <div style="font-size: 18px; font-weight: bold; color: #1e3c72;">{ranking['Art. Sin Stock'].sum():,}</div>
            </div>
            <div style="color: #c0392b; font-size: 12px; margin-top: 0.2rem;">
                🔴 Artículos críticos
            </div>
        </div>
        """, unsafe_allow_html=True)

    # === VISUALIZACIONES ===
    # st.markdown("---")
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
            margin=dict(t=10, b=10, l=10, r=40),
            xaxis=dict(visible=False),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig_ventas, width="stretch")
    
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
            margin=dict(t=10, b=10, l=10, r=40),
            xaxis=dict(visible=False),
            yaxis=dict(visible=True, tickfont=dict(size=10)),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig_presu, width="stretch")
    
    # === TABLA RANKING DETALLADA ===
    # st.markdown("---")
    st.markdown("### 📋 Ranking Detallado de Proveedores")
    
    # Formatear columnas para display
    df_display = ranking.copy()
    df_display['Venta Total'] = df_display['Venta Total'].apply(lambda x: f"${x:,.0f}")
    df_display['Costo Total'] = df_display['Costo Total'].apply(lambda x: f"${x:,.0f}")
    df_display['Utilidad'] = df_display['Utilidad'].apply(lambda x: f"${x:,.0f}")
    df_display['Presupuesto'] = df_display['Presupuesto'].apply(lambda x: f"${x:,.0f}")
    df_display['Costo Exceso'] = df_display['Costo Exceso'].apply(lambda x: f"${x:,.0f}")
    df_display['Rentabilidad %'] = df_display['Rentabilidad %'].apply(lambda x: f"{x:.2f}%")
    df_display['% Participación Presupuesto'] = df_display['% Participación Presupuesto'].apply(lambda x: f"{x:.2f}%")
    df_display['% Participación Ventas'] = df_display['% Participación Ventas'].apply(lambda x: f"{x:.2f}%")

    # Slider para cantidad de proveedores en tabla
    num_mostrar = st.slider("Cantidad de proveedores a mostrar:", 10, len(df_display), 20, step=5, key='slider_tabla')
    
    st.dataframe(
        df_display.head(num_mostrar)[[
            'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total', 'Utilidad', 'Rentabilidad %',
            '% Participación Presupuesto', 'Presupuesto', 'Artículos', 'Art. con Exceso', 
            'Costo Exceso', 'Art. Sin Stock'
        ]],
        width="stretch",
        hide_index=True
    )
    
    # === INSIGHTS AUTOMÁTICOS ===
    # st.markdown("---")
    st.markdown("### 💡 Insights Clave")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
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
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #ff9800'>
        <b>💰 Mayor Presupuesto Requerido</b><br>
        <b>{top_presupuesto['Proveedor']}</b><br>
        💵 ${top_presupuesto['Presupuesto']:,.0f}<br>
        📊 ${top_presupuesto['% Participación Presupuesto']:,.1f}% del total<br>
        📦 {top_presupuesto['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        mas_util = ranking.nlargest(1, 'Utilidad').iloc[0]
        st.markdown(f"""
        <div style='background-color:#e8f5e9;padding:1rem;border-radius:10px;border-left:5px solid #4caf50'>
        <b>🏆 Proveedor Líder en Utilidad</b><br>
        <b>{mas_util['Proveedor']}</b><br>
        💸 ${mas_util['Utilidad']:,.0f}<br>
        📦 {mas_util['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Menor utilidad
        peor_util = ranking.nsmallest(1, 'Utilidad').iloc[0]
        st.markdown(f"""
        <div style='background-color:#ffebee;padding:1rem;border-radius:10px;border-left:5px solid #f44336'>
            <b>⚠️ Proveedor con Menor Utilidad</b><br>
            <b>{peor_util['Proveedor']}</b><br>
            💸 ${peor_util['Utilidad']:,.0f}<br>
            📦 {peor_util['Artículos']} artículos<br>
        </div>
        """, unsafe_allow_html=True)
                
    with col5:
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
    
    # Preparar DataFrame con datos sin formato
#     df_export = ranking[[
#                     'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total', 'Utilidad', 'Rentabilidad %',
#             '% Participación Presupuesto', 'Presupuesto', 'Artículos', 'Art. con Exceso', 
#             'Costo Exceso', 'Art. Sin Stock'
#    ]].copy()
#     df_export['Venta Total'] = df_export['Venta Total'].astype(int)
#     df_export['Costo Total'] = df_export['Costo Total'].astype(int)
#     df_export['Utilidad'] = df_export['Utilidad'].astype(int)
#     df_export['Presupuesto'] = df_export['Presupuesto'].astype(int)
#     df_export['Costo Exceso'] = df_export['Costo Exceso'].astype(int)
#     # redondear en 2 decimales
#     df_export['Rentabilidad %'] = df_export['Rentabilidad %'].round(2)
#     df_export['% Participación Presupuesto'] = df_export['% Participación Presupuesto'].round(2)
#     df_export['% Participación Ventas'] = df_export['% Participación Ventas'].round(2)

#    # Crear buffer en memoria para el archivo Excel
#     output = BytesIO()
#     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#       df_export.to_excel(writer, index=False, sheet_name='Ranking')
#     output.seek(0)  # volver al inicio del buffer

#    # Botón de descarga en formato XLSX
#     st.download_button(
#       label="📥 Descargar Ranking Completo (Excel)",
#       data=output,
#       file_name=f"ranking_proveedores_{datetime.now().strftime('%Y%m%d')}.xlsx",
#       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#       width="stretch"
#    )
    # from io import BytesIO
    # import pandas as pd
    # from datetime import datetime

    # === Preparar DataFrame para exportar ===
    # df_export = ranking[[
    #     'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total',
    #     'Utilidad', 'Rentabilidad %', '% Participación Presupuesto', 'Presupuesto',
    #     'Artículos', 'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
    # ]].copy()

    # # Ajustes de tipos y redondeos
    # df_export['Venta Total'] = df_export['Venta Total'].astype(int)
    # df_export['Costo Total'] = df_export['Costo Total'].astype(int)
    # df_export['Utilidad'] = df_export['Utilidad'].astype(int)
    # df_export['Presupuesto'] = df_export['Presupuesto'].astype(int)
    # df_export['Costo Exceso'] = df_export['Costo Exceso'].astype(int)
    # df_export['Rentabilidad %'] = df_export['Rentabilidad %'].round(2)
    # df_export['% Participación Presupuesto'] = df_export['% Participación Presupuesto'].round(2)
    # df_export['% Participación Ventas'] = df_export['% Participación Ventas'].round(2)

    # # === Exportar con formato ===
    # output = BytesIO()
    # with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    #     df_export.to_excel(writer, index=False, sheet_name='Ranking')
        
    #     workbook  = writer.book
    #     worksheet = writer.sheets['Ranking']
        
    #     # Formatos
    #     formato_miles = workbook.add_format({'num_format': '#,##0'})
    #     formato_porcentaje = workbook.add_format({'num_format': '0.00%'})
    #     formato_header = workbook.add_format({
    #         'bold': True,
    #         'bg_color': '#4a90e2',   # azul agradable
    #         'font_color': 'white',
    #         'align': 'center',
    #         'valign': 'vcenter'
    #     })
        
    #     # Ajustar ancho de columnas según contenido
    #     for i, col in enumerate(df_export.columns):
    #         # calcular ancho máximo entre encabezado y datos
    #         max_len = max(
    #             df_export[col].astype(str).map(len).max(),
    #             len(col)
    #         ) + 2  # un poco de aire
    #         worksheet.set_column(i, i, max_len)
        
    #     # Aplicar formato a encabezados y altura de fila
    #     worksheet.set_row(0, 25, formato_header)
        
    #     # Inmovilizar primera fila
    #     worksheet.freeze_panes(1, 0)

    # output.seek(0)

    # # === Botón de descarga ===
    # st.download_button(
    #     label="📥 Descargar Ranking Completo (Excel)",
    #     data=output,
    #     file_name=f"ranking_proveedores_{datetime.now().strftime('%d%B%Y')}.xlsx",
    #     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    #     use_container_width=True
    # )

    from datetime import datetime
    from io import BytesIO
    import pandas as pd

    # === Preparar DataFrame para exportar ===
    df_export = ranking[[
        'Ranking', 'Proveedor', '% Participación Ventas', 'Venta Total', 'Costo Total',
        'Utilidad', 'Rentabilidad %', '% Participación Presupuesto', 'Presupuesto',
        'Artículos', 'Art. con Exceso', 'Costo Exceso', 'Art. Sin Stock'
    ]].copy()

    # === ELIMINAR COLUMNAS VACÍAS ANTES DE EXPORTAR ===
    columnas_vacias = []
    for col in df_export.columns:
        if df_export[col].isna().all() or (df_export[col] == 0).all():
            columnas_vacias.append(col)

    # Eliminar las columnas vacías
    df_export = df_export.drop(columns=columnas_vacias)

    print(f"📊 Columnas exportadas: {list(df_export.columns)}")
    print(f"🗑️ Columnas eliminadas por estar vacías: {columnas_vacias}")

    # Ajustes de tipos y redondeos
    if 'Venta Total' in df_export.columns:
        df_export['Venta Total'] = df_export['Venta Total'].astype(int)
    if 'Costo Total' in df_export.columns:
        df_export['Costo Total'] = df_export['Costo Total'].astype(int)
    if 'Utilidad' in df_export.columns:
        df_export['Utilidad'] = df_export['Utilidad'].astype(int)
    if 'Presupuesto' in df_export.columns:
        df_export['Presupuesto'] = df_export['Presupuesto'].astype(int)
    if 'Costo Exceso' in df_export.columns:
        df_export['Costo Exceso'] = df_export['Costo Exceso'].astype(int)
    if 'Rentabilidad %' in df_export.columns:
        df_export['Rentabilidad %'] = df_export['Rentabilidad %'].round(2)
    if '% Participación Presupuesto' in df_export.columns:
        df_export['% Participación Presupuesto'] = df_export['% Participación Presupuesto'].round(2)
    if '% Participación Ventas' in df_export.columns:
        df_export['% Participación Ventas'] = df_export['% Participación Ventas'].round(2)

    print("📊 Generando archivo Excel con formato profesional...")

    # === Exportar con formato ===
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Ranking')
        
        workbook = writer.book
        worksheet = writer.sheets['Ranking']
        
        # === FORMATOS ===
        formato_moneda = workbook.add_format({
            'num_format': '$#,##0',
            'align': 'right'
        })
        
        formato_entero = workbook.add_format({
            'num_format': '#,##0',
            'align': 'center'
        })
        
        formato_header = workbook.add_format({
            'bold': True,
            'bg_color': '#2E5090',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # === APLICAR FORMATO A ENCABEZADOS SOLO EN COLUMNAS CON DATOS ===
        num_columnas = len(df_export.columns)
        
        # Establecer altura de la primera fila SIN formato para toda la fila
        worksheet.set_row(0, 25)
        
        # Aplicar formato de header SOLO a las celdas con datos
        for i in range(num_columnas):
            worksheet.write(0, i, df_export.columns[i], formato_header)
        
        # === INMOVILIZAR PRIMERA FILA ===
        worksheet.freeze_panes(1, 0)
        
        # === AJUSTAR ANCHO Y APLICAR FORMATOS SOLO A COLUMNAS CON DATOS ===
        for i, col in enumerate(df_export.columns):
            # Calcular ancho necesario (mínimo el nombre de la columna)
            max_len = max(len(col), 12) + 2
            
            # Aplicar formato según el tipo de columna
            if col in ['Venta Total', 'Costo Total', 'Utilidad', 'Presupuesto', 'Costo Exceso']:
                # Formato de moneda con separador de miles
                worksheet.set_column(i, i, max(max_len, 15), formato_moneda)
                
            elif col in ['Artículos', 'Art. con Exceso', 'Art. Sin Stock', 'Ranking']:
                # Formato de número entero con separador de miles
                worksheet.set_column(i, i, max_len, formato_entero)
                
            elif col == 'Proveedor':
                # Texto sin formato especial, más ancho
                worksheet.set_column(i, i, 30)
                
            else:
                # Resto de columnas (porcentajes ya vienen formateados desde pandas)
                worksheet.set_column(i, i, max_len)

    output.seek(0)

    print(f"✅ Archivo Excel generado exitosamente con {num_columnas} columnas")

    # === Botón de descarga ===
    st.download_button(
        label="📥 Descargar Ranking Completo (Excel)",
        data=output,
        file_name=f"ranking_proveedores_{datetime.now().strftime('%d%B%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )