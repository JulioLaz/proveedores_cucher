import streamlit as st
import plotly.express as px

def mostrar_analisis_quiebre_detallado(df_quiebre):

    if df_quiebre is None or df_quiebre.empty:
        st.info("No hay pérdidas estimadas por quiebre.")
        return

    # KPIs principales

# KPIs principales
    total_perdido = df_quiebre["valor_perdido"].sum()
    total_unidades = df_quiebre["unidades_perdidas"].sum()
    total_articulos_afectados = df_quiebre[df_quiebre["unidades_perdidas"] > 0]["idarticulo"].nunique()

    col1, col2 = st.columns([1.5,1])

    with col1:

        df_filtrado = df_quiebre[df_quiebre["valor_perdido"] > 0]

        top_sucursales = (
                df_filtrado.groupby("sucursal")["valor_perdido"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
            )

        fig = px.bar(
                top_sucursales,
                x="valor_perdido",
                y="sucursal",
                orientation="h",
                text_auto=".2s",
                color_discrete_sequence=px.colors.qualitative.Safe
                # color_discrete_sequence=["#d9534f"]  # rojo profesional o cualquier otro
            )

        fig.update_layout(
                title="💰 Valor Perdido por Sucursal",
                title_x=0.15,
                height=300,
                showlegend=False,
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(l=20, r=20, t=40, b=20)

            )
        fig.update_xaxes(showticklabels=False)
        fig.update_yaxes(showticklabels=True)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(
            f"""
            <div style="background-color:transparent;border-radius:8px;padding:2px;text-align:center;border:1px solid gray; margin-bottom: 5px">
                <h5>💸 Valor de Perdida Potencial</h5>
                <p style="font-size:20px;font-weight:bold;color:#d9534f;">${total_perdido:,.0f}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            f"""
            <div style="background-color:transparent ;border-radius:8px;padding:2px;text-align:center;border:1px solid gray; margin-bottom: 5px">
                <h5>📦 Unidades Potencialmente Perdidas</h5>
                <p style="font-size:20px;font-weight:bold;color:#f0ad4e;">{total_unidades:,.0f}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="background-color:transparent ;border-radius:8px;padding:2px;text-align:center;border:1px solid gray; margin-bottom: 5px">
                <h5>🎯 Artículos Afectados</h5>
                <p style="font-size:20px;font-weight:bold;color:#5bc0de;">{total_articulos_afectados:,}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # df_filtrado = df_quiebre[df_quiebre["valor_perdido"] > 0]

    # top_sucursales = (
    #     df_filtrado.groupby("sucursal")["valor_perdido"]
    #     .sum()
    #     .sort_values(ascending=False)
    #     .reset_index()
    # )

    # fig = px.bar(
    #     top_sucursales,
    #     x="valor_perdido",
    #     y="sucursal",
    #     orientation="h",
    #     text_auto=".2s",
    #     color_discrete_sequence=px.colors.qualitative.Safe
    #     # color_discrete_sequence=["#d9534f"]  # rojo profesional o cualquier otro
    # )

    # fig.update_layout(
    #     title="💰 Valor Perdido por Sucursal",
    #     title_x=0.15,
    #     height=400,
    #     showlegend=False,
    #     xaxis_title=None,
    #     yaxis_title=None,
    #     margin=dict(l=20, r=20, t=40, b=20)

    # )
    # fig.update_xaxes(showticklabels=False)
    # fig.update_yaxes(showticklabels=True)
    # st.plotly_chart(fig, use_container_width=True)


    # Mostrar tabla de detalle por artículo y sucursal
    st.markdown("### 🧾 Detalle de Pérdidas por Artículo y Sucursal")
    columnas = [
        "idarticulo", "descripcion", "sucursal", "cnt_suc_estimada",
        "stock_actual", "unidades_perdidas", "valor_perdido",
        "accion_recomendada", "explicacion_accion"
    ]

    df_mostrar = df_quiebre[df_quiebre["unidades_perdidas"] > 0][columnas].copy()
    df_mostrar["cnt_suc_estimada"] = df_mostrar["cnt_suc_estimada"].map("{:,.1f}".format)
    df_mostrar["valor_perdido"] = df_mostrar["valor_perdido"].map("${:,.0f}".format)
    df_mostrar["unidades_perdidas"] = df_mostrar["unidades_perdidas"].astype(int)

    st.dataframe(df_mostrar.head(300), use_container_width=True, hide_index=True)

    # Opción de descarga
    csv = df_mostrar.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar Pérdidas Detalladas", csv, "perdidas_quiebre.csv", "text/csv")
