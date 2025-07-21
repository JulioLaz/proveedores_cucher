import streamlit as st
import pandas as pd

def show_executive_summary(self, df, proveedor, metrics):
    """Mostrar resumen ejecutivo"""
    st.subheader(f"📈 Resumen Ejecutivo - {proveedor}")

    # CSS para bordes finos y estilo elegante
    st.markdown("""
        <style>
        .kpi-box {
            border: 1px solid #444;
            border-radius: 10px;
            padding: 1rem;
            text-align: center;
            background-color: #0e1117;
            box-shadow: 0 2px 5px rgba(255, 255, 255, 0.05);
            transition: 0.3s ease-in-out;
        }
        .kpi-box:hover {
            border-color: #888;
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.15);
        }
        .kpi-title {
            font-size: 0.9rem;
            color: #ccc;
            margin-bottom: 0.3rem;
        }
        .kpi-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #fff;
        }
        .kpi-delta {
            font-size: 0.85rem;
            color: #aaa;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
            <div class="kpi-box">
                <div class="kpi-title">💰 Ventas Totales</div>
                <div class="kpi-value">${metrics['total_ventas']:,.0f}</div>
                <div class="kpi-delta">{metrics['margen_promedio']:.1f}% margen</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="kpi-box">
                <div class="kpi-title">📈 Utilidad Total</div>
                <div class="kpi-value">${metrics['total_utilidad']:,.0f}</div>
                <div class="kpi-delta">${metrics['ticket_promedio']:,.0f} ticket prom.</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="kpi-box">
                <div class="kpi-title">🧾 Total Transacciones</div>
                <div class="kpi-value">{metrics['num_tickets']:,}</div>
                <div class="kpi-delta">{metrics['dias_con_ventas']} días activos</div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <div class="kpi-box">
                <div class="kpi-title">📦 Cantidad Vendida</div>
                <div class="kpi-value">{metrics['total_cantidad']:,.0f}</div>
                <div class="kpi-delta">{metrics['productos_unicos']} productos únicos</div>
            </div>
        """, unsafe_allow_html=True)
