import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from insight_ABC import generar_insight_cantidad, generar_insight_ventas, generar_insight_margen, generar_insight_abc_completo, generar_insight_pareto


def show_products_analysis(self, df):
        """Análisis detallado de productos"""
        # st.subheader("🏆 Análisis Detallado de Productos - TOP 20")

        try:
            # === Agrupar por descripción ===
            productos_stats = df.groupby("descripcion").agg({
                "precio_total": "sum",
                "costo_total": "sum",
                "cantidad_total": "sum"
            }).reset_index()

            productos_stats["Utilidad"] = productos_stats["precio_total"] - productos_stats["costo_total"]
            productos_stats["Margen %"] = 100 * productos_stats["Utilidad"] / productos_stats["precio_total"].replace(0, pd.NA)
            productos_stats["Participación %"] = 100 * productos_stats["precio_total"] / productos_stats["precio_total"].sum()

            productos_stats.rename(columns={
                "precio_total": "Ventas",
                "costo_total": "Costos",
                "cantidad_total": "Cantidad"
            }, inplace=True)

            # === Título y selector alineados en una fila ===
            col1, col2 = st.columns([5, 1])  # Ajusta proporción según el espacio que desees
            with col1:
                st.subheader("🏆 Análisis Detallado de Productos - TOP 20")
            with col2:
                orden_por = st.selectbox(
                    "",["Ventas", "Utilidad", "Margen %", "Cantidad", "Participación %"])

            # === Obtener top ordenado ===
            productos_top = productos_stats[productos_stats[orden_por].notna()].copy()
            productos_top = productos_top.sort_values(orden_por, ascending=False).head(20).copy()
            productos_top["Producto"] = productos_top["descripcion"].apply(lambda x: x[:40] + "..." if len(x) > 40 else x)

            # === Títulos ===
            titulo_dict = {
                "Ventas": f"Top {len(productos_top)} Productos por Ventas 💰",
                "Utilidad": f"Top {len(productos_top)} Productos por Utilidad 📈",
                "Margen %": f"Top {len(productos_top)} Productos por Margen (%) 🧮",
                "Cantidad": f"Top {len(productos_top)} Productos por Cantidad Vendida 📦",
                "Participación %": f"Top {len(productos_top)} por Participación (%) del Total 🧭"
            }

            # === Gráfico principal ===
            fig = px.bar(
                productos_top,
                x="Producto",
                y=orden_por,
                text_auto='.2s' if orden_por in ["Ventas", "Utilidad"] else '.1f',
                title=titulo_dict[orden_por],
                labels={"Producto": "Producto", orden_por: orden_por}
            )

            if len(productos_top)<8:
                fig.update_layout(
                    title_font=dict(size=22, color='#454448', family='Arial Black'),
                    title_x=0.3,
                    height=400,
                    xaxis_title=None,
                    yaxis_title=None,
                    margin=dict(t=60, b=10),
                    xaxis_tickangle=0,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=12),
                    yaxis=dict(
                        showticklabels=False,  # ⛔ oculta los valores del eje x
                        showgrid=False,        # opcional: oculta líneas de grilla
                        zeroline=False         # opcional: oculta línea cero
                    ))
            else:
                fig.update_layout(
                    title_font=dict(size=22, color='#454448', family='Arial Black'),
                    title_x=0.3,
                    height=400,
                    xaxis_title=None,
                    yaxis_title=None,
                    margin=dict(t=60, b=10),
                    xaxis_tickangle=-45,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=12),
                    yaxis=dict(
                        showticklabels=False,  # ⛔ oculta los valores del eje x
                        showgrid=False,        # opcional: oculta líneas de grilla
                        zeroline=False         # opcional: oculta línea cero
                    ))

# Formato condicional para etiquetas sobre barras
            if orden_por == "Cantidad":
                fig.update_traces(
                    texttemplate='<b>%{y:,.0f}</b>',
                    textfont=dict(size=14),
                    textposition="outside"
                )
            elif orden_por in ["Ventas", "Utilidad"]:
                fig.update_traces(
                    texttemplate='<b>%{y:,.1f}</b>',
                    textfont=dict(size=14),
                    textposition="outside"
                )
            elif orden_por in ["Participación %", "Margen %"]:
                fig.update_traces(
                    texttemplate='<b>%{y:.1f}%</b>',
                    textfont=dict(size=14),
                    textposition="outside"
                )

            fig.update_traces(marker_color='#8966c6')
            st.plotly_chart(fig, use_container_width=True)

            if len(productos_top) < 5:
                st.warning(f"⚠️ Solo hay {len(productos_top)} productos disponibles con datos en '{orden_por}'.")

            ###############################################################################################################
            # === Gráfico adicional: Top 5 idarticulo por métrica y sucursal ===
            # === Gráfico adicional: Top 5 idarticulo por métrica y sucursal ===
            try:
                if "idarticulo" in df.columns and "sucursal" in df.columns:
                    
                    # Agrupar por sucursal e idarticulo
                    df_top5 = (
                        df.groupby(["sucursal", "idarticulo", "descripcion"])
                        .agg({
                            "precio_total": "sum",
                            "costo_total": "sum",
                            "cantidad_total": "sum"
                        })
                        .reset_index()
                    )

                    # Crear métricas
                    df_top5["Utilidad"] = df_top5["precio_total"] - df_top5["costo_total"]
                    df_top5["Margen %"] = 100 * df_top5["Utilidad"] / df_top5["precio_total"].replace(0, pd.NA)
                    df_top5["Participación %"] = 100 * df_top5["precio_total"] / df_top5["precio_total"].sum()

                    # Renombrar
                    df_top5.rename(columns={
                        "precio_total": "Ventas",
                        "costo_total": "Costos",
                        "cantidad_total": "Cantidad"
                    }, inplace=True)

                    # Ordenar sucursales por ventas totales
                    orden_sucursales = (
                        df.groupby("sucursal")["precio_total"].sum().sort_values(ascending=False).index.tolist()
                    )

                    # Obtener top 5 artículos por sucursal (en orden deseado)
                    df_top5 = df_top5[df_top5[orden_por].notna()]
                    df_top5 = df_top5.sort_values([ "sucursal", orden_por], ascending=[True, False])
                    df_top5 = df_top5.groupby("sucursal").head(5).copy()

                    # Convertir idarticulo a str para el eje x
                    df_top5["idarticulo"] = df_top5["idarticulo"].astype(str)

                    # Ordenar categoría compuesta para que Plotly las muestre bien agrupadas por sucursal

                    # Asegurar que idarticulo sea str
                    df_top5["idarticulo"] = df_top5["idarticulo"].astype(str)

                    # Etiqueta multilínea: ID, descripción corta y sucursal
                    # df_top5["x_label"] = df_top5.apply(
                        # lambda row: f"{row['idarticulo']}<br>{row['descripcion'][:25]}<br><b>{row['sucursal']}</b>", axis=1)
                    df_top5["x_label"] = df_top5.apply(
                        lambda row: f"<b>{row['idarticulo']}</b><br><span style='font-size:11px'>{row['descripcion'][:20]}</span><br><span style='font-size:10px; font-weight:bold'>{row['sucursal']}</span>",
                        axis=1)

                    df_top5["Etiqueta"] = df_top5["sucursal"] + " - " + df_top5["idarticulo"]
                    df_top5["Etiqueta"] = pd.Categorical(df_top5["Etiqueta"], 
                                                        categories=[
                                                            # f"{idart}" 
                                                            f"{suc} - {idart}" 
                                                            for suc in orden_sucursales
                                                            for idart in df_top5[df_top5["sucursal"] == suc]["idarticulo"].tolist()
                                                        ],
                                                        ordered=True)

                    # Título
                    titulo_top5 = f"Top {df_top5.idarticulo.nunique()} ID Artículo por {orden_por} en cada Sucursal"

                    # Gráfico
                    fig2 = px.bar(
                        df_top5,
                        x="x_label",
                        # x="Etiqueta",
                        y=orden_por,
                        color="sucursal",
                        text_auto='.2s' if orden_por in ["Ventas", "Utilidad"] else '.1f',
                        title=titulo_top5,
                        labels={"Etiqueta": "ID Artículo por Sucursal", orden_por: orden_por}
                    )

                    # Layout profesional
                    fig2.update_layout(
                        title_font=dict(size=20, color='#454448', family='Arial Black'),
                        title_x=0.3,
                        height=550,
                        xaxis_title=None,
                        yaxis_title=None,
                        margin=dict(t=60, b=10),
                        # xaxis_tickangle=-45,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=12),
                        showlegend=False,  # ❌ Oculta la leyenda
                        yaxis=dict(
                            showticklabels=False,
                            showgrid=False,
                            zeroline=False
                        ),
                        legend_title_text='Sucursal'
                    )

                    # Formato condicional para etiquetas sobre barras en gráfico por sucursal
                    if orden_por == "Cantidad":
                        fig2.update_traces(
                            texttemplate='<b>%{y:,.0f}</b>',
                            textfont=dict(size=14),
                            textposition="outside"
                        )
                    elif orden_por in ["Ventas", "Utilidad"]:
                        fig2.update_traces(
                            texttemplate='<b>$%{y:,.0f}</b>',
                            textfont=dict(size=14),
                            textposition="outside"
                        )
                    elif orden_por in ["Participación %", "Margen %"]:
                        fig2.update_traces(
                            texttemplate='<b>%{y:.1f}%</b>',
                            textfont=dict(size=14),
                            textposition="outside"
                        )


                    # Mostrar
                    st.plotly_chart(fig2, use_container_width=True)

                else:
                    st.info("⚠️ No se encontraron columnas 'idarticulo' o 'sucursal' en el DataFrame.")

            except Exception as e:
                st.error(f"❌ Error al generar la gráfica Top 5 por sucursal: {e}")

###############################################################################################################

            # === GRAFICOS ADICIONALES ===
            col1, col2 = st.columns(2)

            with col1:
                # Scatter plot Ventas vs Margen
                top_20 = productos_stats.sort_values("Ventas", ascending=False).head(20).copy()
                top_20["producto_corto"] = top_20["descripcion"].str[:30] + "..."

                fig = px.scatter(
                    top_20,
                    x="Ventas",
                    y="Margen %",
                    size="Cantidad",
                    color="Cantidad",
                    color_continuous_scale="viridis",
                    hover_name="producto_corto",
                    hover_data={"Utilidad": ":,.0f"},
                    title="💹 Ventas vs Margen (TOP 20)",
                    labels={'Ventas': 'Ventas ($)', 'Margen %': 'Margen (%)'}
                )

                fig.update_traces(marker=dict(opacity=0.8, line=dict(width=0)))
                fig.update_layout(
                    height=600,
                    title_font=dict(size=18, color='#454448', family='Arial Black'),
                    title_x=0.08,
                    # xaxis_title=None,
                # yaxis_title=None,
                    coloraxis_colorbar=dict(title='Cantidad'),
                    margin=dict(t=60, b=20, l=10, r=10)
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # === Análisis de Pareto con etiquetas y tooltips optimizados ===
                productos_pareto = productos_stats.sort_values("Ventas", ascending=False).head(20).copy()
                productos_pareto["ranking"] = range(1, len(productos_pareto) + 1)
                productos_pareto["descripcion_corta"] = productos_pareto.apply(lambda row: f"{row['ranking']} - {row['descripcion'][:14]}...", axis=1)
                productos_pareto["acumulado"] = productos_pareto['Participación %'].cumsum()
                productos_pareto["individual_fmt"] = productos_pareto["Participación %"].map("{:.1f}%".format)
                productos_pareto["acumulado_fmt"] = productos_pareto["acumulado"].map("{:.0f}%".format)

                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # === Barras ===
                fig.add_trace(
                    go.Bar(
                        x=productos_pareto["descripcion_corta"],
                        y=productos_pareto['Participación %'],
                        name='Participación Individual (%)',
                        marker_color='lightblue',
                        text=productos_pareto["individual_fmt"],
                        textposition='outside',
                        hovertemplate="<b>%{customdata[0]}</b><br>Participación Individual: %{text}<extra></extra>",
                        customdata=productos_pareto[["descripcion"]]
                    ),
                    secondary_y=False
                )

                # === Línea acumulada ===
                fig.add_trace(
                    go.Scatter(
                        x=productos_pareto["descripcion_corta"],
                        y=productos_pareto["acumulado"],
                        mode='lines+markers+text',
                        name='Participación Acumulada (%)',
                        line=dict(color='red', width=1),
                        text=productos_pareto["acumulado_fmt"],
                        textposition="top center",
                        hovertemplate="<b>%{customdata[0]}</b><br>Participación Acumulada: %{y:.1f}%<extra></extra>",
                        customdata=productos_pareto[["descripcion"]]
                    ),
                    secondary_y=True
                )

                fig.update_layout(
                    title_text="📈 Análisis de Pareto - Concentración de Ventas",
                    title_font=dict(size=18, color='#454448', family='Arial Black'),
                    title_x=0.08,
                    xaxis_title="Ranking de Productos",
                    yaxis_title="Participación Individual (%)",
                    height=600,
                    margin=dict(t=70, b=50),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=1.075,
                        xanchor="center",
                        x=0.45,
                        bgcolor='rgba(0,0,0,0)'
                    )
                )

                fig.update_yaxes(title_text="Participación Individual (%)", secondary_y=False)
                fig.update_yaxes(title_text="Participación Acumulada (%)", secondary_y=True)
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown(generar_insight_pareto(productos_pareto), unsafe_allow_html=True)

        except Exception as e:
            st.error(f"❌ Error en análisis de productos: {str(e)}")
            st.info("💡 Intenta con un rango de fechas diferente o verifica los datos del proveedor.")