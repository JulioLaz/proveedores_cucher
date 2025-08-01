import pandas as pd
import io
import streamlit as st
from datetime import datetime
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

class ProveedorAnalyzerStreamlit:
    def __init__(self, proveedor_name, df_presu, df_tickets):
        self.proveedor_name = proveedor_name
        self.df_presu = df_presu
        self.df_tickets = df_tickets
        self.ids_proveedor = []
        self.proveedor_df = None
        self.results = {}

    def extract_provider_ids(self):
        """Extrae los IDs del proveedor desde df_presu"""
        self.ids_proveedor = self.df_presu.loc[
            self.df_presu['proveedor'].str.strip() == self.proveedor_name,
            'idarticulo'
        ].tolist()
        return len(self.ids_proveedor) > 0

    def load_and_filter_tickets(self):
      """Filtra tickets del proveedor y calcula precio_unitario si no existe."""
      cantidad_col = "cantidad_total"
      precio_total_col = "precio_total"
      precio_unit_col = "precio_unitario"

      # 1️⃣ Validar columnas esenciales
      required_cols = ["idarticulo", "fecha_comprobante", cantidad_col, precio_total_col]
      missing_cols = [c for c in required_cols if c not in self.df_tickets.columns]
      if missing_cols:
         st.error(f"❌ Faltan columnas en df_tickets: {missing_cols}")
         st.write("Columnas actuales:", self.df_tickets.columns.tolist())
         return False

      # 2️⃣ Calcular precio_unitario si no existe
      if precio_unit_col not in self.df_tickets.columns:
         self.df_tickets[precio_unit_col] = (
               self.df_tickets[precio_total_col] / self.df_tickets[cantidad_col].replace(0, pd.NA)
         )

      # 3️⃣ Asegurar mismo tipo para idarticulo
      self.df_tickets['idarticulo'] = self.df_tickets['idarticulo'].astype(str)
      self.ids_proveedor = [str(x) for x in self.ids_proveedor]

      # 4️⃣ Filtrar tickets por ids del proveedor
      self.proveedor_df = self.df_tickets[self.df_tickets['idarticulo'].isin(self.ids_proveedor)].copy()

      # 5️⃣ Si está vacío, advertir
      if self.proveedor_df.empty:
         st.warning(f"⚠️ No hay registros de tickets para {self.proveedor_name}")
         return False

      # 6️⃣ Limpiar registros nulos y cantidades cero
      self.proveedor_df = self.proveedor_df.dropna(subset=[cantidad_col, precio_unit_col])
      self.proveedor_df = self.proveedor_df[self.proveedor_df[cantidad_col] > 0]

      # 7️⃣ Convertir fechas
      self.proveedor_df["fecha_comprobante"] = pd.to_datetime(self.proveedor_df["fecha_comprobante"])

      st.write(f"✅ {len(self.proveedor_df):,} registros válidos para análisis")
      return True


    def analyze_data(self):
        """Ejemplo simplificado de análisis"""
        # Agrupación mensual
        monthly_summary = self.proveedor_df.groupby(self.proveedor_df['fecha_comprobante'].dt.to_period('M')).agg({
            'cantidad_total': 'sum',
            'precio_total': 'sum'
        }).reset_index()
        monthly_summary.rename(columns={'fecha_comprobante':'periodo'}, inplace=True)
        self.results['monthly_summary'] = monthly_summary

    def export_to_excel_bytes(self):
        """Genera Excel en memoria (BytesIO)"""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Guardar resultados principales
            for name, df in self.results.items():
                df.to_excel(writer, sheet_name=name[:31], index=False)
        output.seek(0)
        return output

    def run_analysis(self):
        """Pipeline completo para Streamlit"""
        if not self.extract_provider_ids():
            st.warning("❌ No se encontraron productos para el proveedor")
            return None
        if not self.load_and_filter_tickets():
            st.warning("❌ No se encontraron ventas para este proveedor")
            return None
        self.analyze_data()
        return self.export_to_excel_bytes()
