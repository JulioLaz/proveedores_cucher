import streamlit as st
import pandas as pd
import plotly.express as px


class ExecutiveSummary:
    def show_executive_summary(self, df, proveedor, metrics):
        """Mostrar resumen ejecutivo"""
        st.subheader(f"📈 Resumen Ejecutivo - {proveedor}")
        
        # === KPIs principales en 2 filas y 2 columnas ===
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "💰 Ventas Totales",
                f"${metrics['total_ventas']:,.0f}",
                delta=f"{metrics['margen_promedio']:.1f}% margen"
            )
        with col2:
            st.metric(
                "📈 Utilidad Total",
                f"${metrics['total_utilidad']:,.0f}",
                delta=f"${metrics['ticket_promedio']:,.0f} ticket prom."
            )
        
        col3, col4 = st.columns(2)
        with col3:
            st.metric(
                "🧾 Total Transacciones",
                f"{metrics['num_tickets']:,}",
                delta=f"{metrics['dias_con_ventas']} días activos"
            )
        with col4:
            st.metric(
                "📦 Cantidad Vendida",
                f"{metrics['total_cantidad']:,.0f}",
                delta=f"{metrics['productos_unicos']} productos únicos"
            )
        
        # === Insights automáticos ===
        st.subheader("💡 Insights Clave")
        insights = self.generate_insights(df, metrics)
        for tipo, mensaje in insights:
            if tipo == "success":
                st.markdown(f'<div class="success-box">{mensaje}</div>', unsafe_allow_html=True)
            elif tipo == "warning":
                st.markdown(f'<div class="warning-box">{mensaje}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="insight-box">{mensaje}</div>', unsafe_allow_html=True)

        # === Gráficas de resumen ===
        col1, col2 = st.columns(2)

        with col1:
            ventas_diarias = df.groupby('fecha')['precio_total'].sum().reset_index()
            fig = px.line(
                ventas_diarias, x='fecha', y='precio_total',
                title="📈 Evolución Diaria de Ventas",
                labels={'precio_total': 'Ventas ($)', 'fecha': 'Fecha'}
            )
            fig.update_traces(line_color='#2a5298', line_width=2)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            top_productos = (
                df.groupby('descripcion', as_index=False)['precio_total']
                .sum()
                .sort_values('precio_total', ascending=False)
                .head(5)
            )
            top_productos['descripcion_corta'] = top_productos['descripcion'].str[:30]
            viridis = px.colors.sequential.Viridis[:5]

            fig = px.bar(
                top_productos,
                x='precio_total',
                y='descripcion_corta',
                orientation='h',
                text='precio_total',
                title="🏆 Top 5 Productos por Ventas",
            )
            fig.update_yaxes(categoryorder='total ascending')
            for i, bar in enumerate(fig.data):
                bar.marker.color = viridis[i]
            fig.update_traces(
                texttemplate='%{text:,.0f}',
                textposition='outside',
                cliponaxis=False
            )
            fig.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True, key="top_productos")
        pass
