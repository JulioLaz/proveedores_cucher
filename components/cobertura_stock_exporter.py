# # ═══════════════════════════════════════════════════════════════════
# # EXPORTADOR DE COBERTURA DE STOCK
# # Genera reporte Excel con análisis de cobertura y clasificación
# # ═══════════════════════════════════════════════════════════════════
# import pandas as pd
# import numpy as np
# from google.cloud import bigquery
# from io import BytesIO
# from datetime import datetime
# import time

# class CoberturaStockExporter:
    
#     def __init__(self, credentials_path=None, project_id=None):
#         """Inicializa el exportador con configuración de BigQuery"""
        
#         # Proyecto (con default)
#         self.project_id = project_id or "youtube-analysis-24"
        
#         # Dataset y tabla
#         self.dataset_id = "stk_all_actual"
#         self.table_id = "stock_por_sucursal"
        
#         # Credenciales (con default para uso local)
#         if credentials_path:
#             self.credentials_path = credentials_path
#         else:
#             self.credentials_path = r"C:\JulioPrograma\JSON-clave-bigquery\youtube-analysis-24-432dad7a202f.json"
        
#         self.client = None

#     def conectar_bigquery(self):
#         """Conecta a BigQuery (funciona en local y en nube)"""
#         try:
#             import os
#             # Detectar si estamos en la nube (archivo no existe)
#             is_cloud = not os.path.exists(self.credentials_path)
            
#             if is_cloud:
#                 # En la nube: usar secrets de Streamlit (IGUAL que tus otras consultas)
#                 import streamlit as st
#                 from google.oauth2 import service_account
                
#                 credentials = service_account.Credentials.from_service_account_info(
#                     st.secrets["gcp_service_account"]
#                 )
#                 self.client = bigquery.Client(
#                     credentials=credentials,
#                     project=self.project_id
#                 )
#                 print(f"✅ Conectado a BigQuery (Streamlit Cloud)")
#             else:
#                 # En local: usar archivo JSON (IGUAL que tus otras consultas)
#                 self.client = bigquery.Client.from_service_account_json(
#                     self.credentials_path, 
#                     project=self.project_id
#                 )
#                 print(f"✅ Conectado a BigQuery (Local)")
            
#             return True
            
#         except Exception as e:
#             print(f"❌ Error conectando a BigQuery: {e}")
#             return False

#     def obtener_stock_bigquery(self):
#         """
#         Obtiene datos de stock desde BigQuery con TODAS las columnas necesarias
        
#         Returns:
#             DataFrame con columnas:
#             - idarticulo, idartalfa
#             - stk_corrientes, stk_express, stk_formosa, stk_hiper, stk_tirol, stk_central
#             - stk_total
#         """
#         inicio = time.time()
#         print(f"\n📥 Consultando stock desde BigQuery...")
        
#         query = f"""
#         SELECT 
#             idarticulo,
#             idartalfa,
#             stk_corrientes,
#             stk_express,
#             stk_formosa,
#             stk_hiper,
#             stk_tirol,
#             stk_central,
#             stk_total
#         FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
#         """
        
#         try:
#             df_stock = self.client.query(query).to_dataframe()
#             tiempo = time.time() - inicio
            
#             print(f"✅ Stock obtenido: {len(df_stock):,} registros en {tiempo:.2f}s")
#             print(f"   Columnas disponibles: {df_stock.columns.tolist()}")
#             print(f"   Stock total (suma): {df_stock['stk_total'].sum():,.0f} unidades")
            
#             return df_stock
            
#         except Exception as e:
#             print(f"❌ Error consultando BigQuery: {e}")
#             return None
       
#     def obtener_stock_bigquery00(self):
#       """Obtiene datos de stock desde BigQuery"""
#       inicio = time.time()
#       print(f"\n📥 Consultando stock desde BigQuery...")
      
#       query = f"""
#       SELECT 
#          idarticulo,
#          stk_total
#       FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
#       WHERE stk_total > 0
#       """
      
#       try:
#          df_stock = self.client.query(query).to_dataframe()
#          tiempo = time.time() - inicio
#          print(f"✅ Stock obtenido: {len(df_stock):,} registros en {tiempo:.2f}s")
#          return df_stock
#       except Exception as e:
#          print(f"❌ Error consultando BigQuery: {e}")
#          return None
    

# #     # En cobertura_stock_exporter.py
# #     def obtener_stock_completo_bigquery(self):
# #         """Obtiene stock CON TODAS LAS SUCURSALES desde BigQuery"""
# #         inicio = time.time()
# #         print(f"\n📥 Consultando stock completo desde BigQuery...")
        
# #         query = f"""
# #         SELECT 
# #             idarticulo,
# #             idartalfa,
# #             stk_corrientes,
# #             stk_express,
# #             stk_formosa,
# #             stk_hiper,
# #             stk_tirol,
# #             stk_central,
# #             stk_total
# #         FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
# #         """
        
# #         try:
# #             df_stock = self.client.query(query).to_dataframe()
# #             tiempo = time.time() - inicio
# #             print(f"✅ Stock obtenido: {len(df_stock):,} registros en {tiempo:.2f}s")
# #             return df_stock
# #         except Exception as e:
# #             print(f"❌ Error consultando BigQuery: {e}")
# #             return None
# # #######################################################################################
# #     def obtener_stock_bigquery(self):
# #         """Obtiene datos de stock desde BigQuery CON TODAS LAS COLUMNAS"""
# #         inicio = time.time()
# #         print(f"\n📥 Consultando stock desde BigQuery...")
        
# #         query = f"""
# #         SELECT 
# #             idarticulo,
# #             idartalfa,
# #             stk_corrientes,
# #             stk_express,
# #             stk_formosa,
# #             stk_hiper,
# #             stk_tirol,
# #             stk_central,
# #             stk_total
# #         FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
# #         """
        
# #         try:
# #             df_stock = self.client.query(query).to_dataframe()
# #             tiempo = time.time() - inicio
# #             print(f"✅ Stock obtenido: {len(df_stock):,} registros en {tiempo:.2f}s")
# #             return df_stock
# #         except Exception as e:
# #             print(f"❌ Error consultando BigQuery: {e}")
# #             return None
# # #######################################################################################

#     def calcular_cobertura(self, df_ventas, df_stock, fecha_inicio, fecha_fin, utilidad_minima=10000):
#         """
#         Calcula cobertura en días y clasifica
        
#         Args:
#             df_ventas: DataFrame con ventas y utilidad del periodo
#             df_stock: DataFrame con stock actual de BigQuery
#             fecha_inicio, fecha_fin: datetime para calcular días del periodo
#         """
#         inicio = time.time()
#         print(f"\n🔄 Calculando cobertura...")
        
#         # Calcular días del periodo
#         dias_periodo = (fecha_fin - fecha_inicio).days + 1
#         print(f"   • Periodo: {dias_periodo} días")
        
#         # Merge de ventas con stock
#         df_merged = df_ventas.merge(
#             df_stock[['idarticulo', 'stk_total']], 
#             on='idarticulo', 
#             how='left'
#         )
        
#         # Rellenar stock faltante con 0
#         df_merged['stk_total'] = df_merged['stk_total'].fillna(0)
        
#         # Calcular venta promedio diaria
#         df_merged['venta_promedio_diaria'] = df_merged['cantidad_vendida'] / dias_periodo
        
#         # Calcular cobertura en días
#         df_merged['cobertura_dias'] = np.where(
#             df_merged['venta_promedio_diaria'] > 0,
#             df_merged['stk_total'] / df_merged['venta_promedio_diaria'],
#             999  # Sin ventas = cobertura infinita
#         )
        
#         # Clasificar cobertura
#         def clasificar_cobertura(dias):
#             if dias < 15:
#                 return '🔴 Crítico'
#             elif dias < 31:
#                 return '🟡 Bajo'
#             elif dias < 61:
#                 return '🟢 Óptimo'
#             elif dias < 91:
#                 return '🟠 Alto'
#             else:
#                 return '⚫ Exceso'
        
#         df_merged['clasificacion'] = df_merged['cobertura_dias'].apply(clasificar_cobertura)
        
#         # ⭐ FILTRAR POR UTILIDAD MÍNIMA
#         print(f"   • Artículos antes de filtrar: {len(df_merged):,}")
#         df_merged = df_merged[df_merged['utilidad_total'] > utilidad_minima].copy()
#         print(f"   • Artículos después de filtrar: {len(df_merged):,}")
#         print(f"   💵 Utilidad mínima aplicada: ${utilidad_minima:,.0f}")
#         # # ⭐ FILTRAR UTILIDADES NEGATIVAS
#         # print(f"   • Artículos antes de filtrar: {len(df_merged):,}")
#         # df_merged = df_merged[df_merged['utilidad_total'] > 10000].copy()
#         # print(f"   • Artículos después de filtrar (utilidad >= 0): {len(df_merged):,}\n ⚠️ Con utilidad > $ 10K.")

#         # Ordenar por proveedor, familia, subfamilia, utilidad
#         df_merged = df_merged.sort_values(by=['proveedor', 'familia', 'subfamilia', 'utilidad_total'],
#             ascending=[True, True, True, False])

#         tiempo = time.time() - inicio
#         print(f"✅ Cobertura calculada en {tiempo:.2f}s")
        
#         return df_merged
    
#     def generar_excel(self, df, fecha_inicio, fecha_fin):
#         """
#         Genera archivo Excel con formato profesional
        
#         Args:
#             df: DataFrame con datos completos
#             fecha_inicio, fecha_fin: para nombre del archivo
#         """
#         inicio = time.time()
#         print(f"\n📊 Generando Excel profesional...")
        
#         # Seleccionar y renombrar columnas
#         columnas_finales = {
#             'idarticulo': 'Código',
#             'descripcion': 'Descripción',
#             'proveedor': 'Proveedor',
#             'familia': 'Familia',
#             'subfamilia': 'SubFamilia',
#             'utilidad_total': 'Utilidad',
#             'cantidad_vendida': 'Cant. Vendida',
#             'stk_total': 'Stock Total',
#             'venta_promedio_diaria': 'Venta Prom/Día',
#             'cobertura_dias': 'Cobertura (días)',
#             'clasificacion': 'Clasificación'
#         }
        
#         df_export = df[list(columnas_finales.keys())].copy()
#         df_export.rename(columns=columnas_finales, inplace=True)
        
#         # Crear Excel en memoria
#         output = BytesIO()
        
#         with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#             df_export.to_excel(writer, sheet_name='Cobertura Stock', index=False)
            
#             workbook = writer.book
#             worksheet = writer.sheets['Cobertura Stock']
            
#             # ═══ FORMATOS ═══
#             header_format = workbook.add_format({
#                 'bold': True,
#                 'bg_color': '#2C3E50',
#                 'font_color': 'white',
#                 'align': 'center',
#                 'valign': 'vcenter',
#                 'border': 1
#             })
            
#             # Formatos por clasificación
#             formato_critico = workbook.add_format({'bg_color': '#E74C3C', 'font_color': 'white'})
#             formato_bajo = workbook.add_format({'bg_color': '#F39C12', 'font_color': 'white'})
#             formato_optimo = workbook.add_format({'bg_color': '#27AE60', 'font_color': 'white'})
#             formato_alto = workbook.add_format({'bg_color': '#E67E22', 'font_color': 'white'})
#             formato_exceso = workbook.add_format({'bg_color': '#95A5A6', 'font_color': 'white'})
            
#             formato_numero = workbook.add_format({'num_format': '#,##0'})
#             formato_decimal = workbook.add_format({'num_format': '#,##0.00'})
#             formato_moneda = workbook.add_format({'num_format': '$#,##0.00'})
#             formato_moneda_int = workbook.add_format({'num_format': '$#,##0'})
            
#             # ═══ APLICAR FORMATOS ═══
#             # Header
#             for col_num, value in enumerate(df_export.columns.values):
#                 worksheet.write(0, col_num, value, header_format)
            
#             # Anchos de columna
#             worksheet.set_column('A:A', 12)  # Código
#             worksheet.set_column('B:B', 40)  # Descripción
#             worksheet.set_column('C:C', 25)  # Proveedor
#             worksheet.set_column('D:D', 20)  # Familia
#             worksheet.set_column('E:E', 20)  # SubFamilia
#             worksheet.set_column('F:F', 15)  # Utilidad
#             worksheet.set_column('G:G', 15)  # Cant. Vendida
#             worksheet.set_column('H:H', 15)  # Stock Total
#             worksheet.set_column('I:I', 15)  # Venta Prom/Día
#             worksheet.set_column('J:J', 18)  # Cobertura
#             worksheet.set_column('K:K', 18)  # Clasificación
            
#             # Aplicar formatos a datos
#             for row_num in range(1, len(df_export) + 1):
#                 # Números
#                 worksheet.write(row_num, 0, df_export.iloc[row_num-1]['Código'])
#                 worksheet.write(row_num, 1, df_export.iloc[row_num-1]['Descripción'])
#                 worksheet.write(row_num, 2, df_export.iloc[row_num-1]['Proveedor'])
#                 worksheet.write(row_num, 3, df_export.iloc[row_num-1]['Familia'])
#                 worksheet.write(row_num, 4, df_export.iloc[row_num-1]['SubFamilia'])
#                 worksheet.write(row_num, 5, df_export.iloc[row_num-1]['Utilidad'], formato_moneda_int)
#                 worksheet.write(row_num, 6, df_export.iloc[row_num-1]['Cant. Vendida'], formato_numero)
#                 worksheet.write(row_num, 7, df_export.iloc[row_num-1]['Stock Total'], formato_numero)
#                 worksheet.write(row_num, 8, df_export.iloc[row_num-1]['Venta Prom/Día'], formato_numero)
#                 worksheet.write(row_num, 9, df_export.iloc[row_num-1]['Cobertura (días)'], formato_numero)
                
#                 # Clasificación con color
#                 clasificacion = df_export.iloc[row_num-1]['Clasificación']
#                 if '🔴' in clasificacion:
#                     worksheet.write(row_num, 10, clasificacion, formato_critico)
#                 elif '🟡' in clasificacion:
#                     worksheet.write(row_num, 10, clasificacion, formato_bajo)
#                 elif '🟢' in clasificacion:
#                     worksheet.write(row_num, 10, clasificacion, formato_optimo)
#                 elif '🟠' in clasificacion:
#                     worksheet.write(row_num, 10, clasificacion, formato_alto)
#                 else:
#                     worksheet.write(row_num, 10, clasificacion, formato_exceso)
            
#             # Congelar primera fila
#             worksheet.freeze_panes(1, 0)
        
#         output.seek(0)
        
#         tiempo = time.time() - inicio
#         print(f"✅ Excel generado en {tiempo:.2f}s")
        
#         return output
    
#     def exportar_completo(self, df_ventas, fecha_inicio, fecha_fin, utilidad_minima=10000):
#         """
#         Función principal que ejecuta todo el proceso
        
#         Args:
#             df_ventas: DataFrame con columnas:
#                 - idarticulo
#                 - descripcion
#                 - proveedor
#                 - familia
#                 - subfamilia
#                 - utilidad_total
#                 - cantidad_vendida
#             fecha_inicio, fecha_fin: datetime
        
#         Returns:
#             BytesIO con Excel generado o None si hay error
#         """
#         inicio_total = time.time()
        
#         print("\n" + "="*70)
#         print("📦 GENERANDO REPORTE DE COBERTURA DE STOCK")
#         print("="*70)
        
#         # Conectar a BigQuery
#         if not self.conectar_bigquery():
#             return None
        
#         # Obtener stock
#         df_stock = self.obtener_stock_bigquery()
#         if df_stock is None:
#             return None
        
#         # Calcular cobertura
#         df_completo = self.calcular_cobertura(df_ventas, df_stock, fecha_inicio, fecha_fin, utilidad_minima)
        
#         # Generar Excel
#         excel_file = self.generar_excel(df_completo, fecha_inicio, fecha_fin)
        
#         tiempo_total = time.time() - inicio_total
        
#         print("\n" + "─"*70)
#         print(f"✅ REPORTE GENERADO EXITOSAMENTE")
#         print(f"   • Total artículos: {len(df_completo):,}")
#         print(f"   • Tiempo total: {tiempo_total:.2f}s")
#         print("="*70 + "\n")
        
#         return excel_file
    
#     def obtener_metricas(self, df_ventas, fecha_inicio, fecha_fin, utilidad_minima=10000):
#         """
#         Calcula métricas para la tarjeta de dashboard
        
#         Returns:
#             dict con métricas clave
#         """
#         # Obtener stock
#         if not self.conectar_bigquery():
#             return None
        
#         df_stock = self.obtener_stock_bigquery()
#         if df_stock is None:
#             return None
        
#         # Calcular cobertura
#         df_completo = self.calcular_cobertura(df_ventas, df_stock, fecha_inicio, fecha_fin, utilidad_minima)
        
#         # Calcular métricas
#         metricas = {
#             'stock_total': int(df_completo['stk_total'].sum()),
#             'cobertura_promedio': round(df_completo['cobertura_dias'].mean(), 1),
#             'articulos_sobrestock': int((df_completo['cobertura_dias'] > 60).sum()),
#             'pct_sobrestock': round((df_completo['cobertura_dias'] > 60).sum() / len(df_completo) * 100, 1),
#             'articulos_criticos': int((df_completo['cobertura_dias'] < 15).sum()),
#             'pct_critico': round((df_completo['cobertura_dias'] < 15).sum() / len(df_completo) * 100, 1)
#         }
        
#         return metricas

# # ═══════════════════════════════════════════════════════════════════
# # FUNCIONES PARA USAR EN STREAMLIT
# # ═══════════════════════════════════════════════════════════════════

# def generar_reporte_cobertura(df_ventas, fecha_inicio, fecha_fin, credentials_path=None, project_id=None, utilidad_minima=10000):
#     """
#     Función simplificada para llamar desde Streamlit
    
#     Returns:
#         tuple: (excel_file, df_completo) - Excel BytesIO y DataFrame con datos completos
#     """
#     exporter = CoberturaStockExporter(credentials_path, project_id)
    
#     # Conectar a BigQuery
#     if not exporter.conectar_bigquery():
#         return None, None
    
#     # Obtener stock
#     df_stock = exporter.obtener_stock_bigquery()
#     if df_stock is None:
#         return None, None
    
#     # Calcular cobertura (este DF tiene TODAS las columnas)
#     df_completo = exporter.calcular_cobertura(df_ventas, df_stock, fecha_inicio, fecha_fin, utilidad_minima)
    
#     # Generar Excel
#     excel_file = exporter.generar_excel(df_completo, fecha_inicio, fecha_fin)
    
#     print(f"✅ Devolviendo Excel y DataFrame con {len(df_completo):,} registros")
    
#     # Devolver AMBOS: el Excel y el DataFrame
#     return excel_file, df_completo

# def obtener_metricas_cobertura(df_ventas, fecha_inicio, fecha_fin, credentials_path=None, project_id=None):
#     """
#     Función simplificada para obtener métricas
    
#     Args:
#         df_ventas: DataFrame con datos de ventas
#         fecha_inicio, fecha_fin: datetime
#         credentials_path: Ruta al JSON (solo en local, None en nube)
#         project_id: ID del proyecto de GCP
    
#     Returns:
#         dict con métricas
#     """
#     exporter = CoberturaStockExporter(credentials_path, project_id)
#     return exporter.obtener_metricas(df_ventas, fecha_inicio, fecha_fin)

# ═══════════════════════════════════════════════════════════════════
# EXPORTADOR DE COBERTURA DE STOCK
# Genera reporte Excel con análisis de cobertura y clasificación
# ═══════════════════════════════════════════════════════════════════
import pandas as pd
import numpy as np
from google.cloud import bigquery
from io import BytesIO
from datetime import datetime
import time

class CoberturaStockExporter:
    
    def __init__(self, credentials_path=None, project_id=None):
        """Inicializa el exportador con configuración de BigQuery"""
        
        # Proyecto (con default)
        self.project_id = project_id or "youtube-analysis-24"
        
        # Dataset y tabla
        self.dataset_id = "stk_all_actual"
        self.table_id = "stock_por_sucursal"
        
        # Credenciales (con default para uso local)
        if credentials_path:
            self.credentials_path = credentials_path
        else:
            self.credentials_path = r"C:\JulioPrograma\JSON-clave-bigquery\youtube-analysis-24-432dad7a202f.json"
        
        self.client = None

    def conectar_bigquery(self):
        """Conecta a BigQuery (funciona en local y en nube)"""
        try:
            import os
            # Detectar si estamos en la nube (archivo no existe)
            is_cloud = not os.path.exists(self.credentials_path)
            
            if is_cloud:
                # En la nube: usar secrets de Streamlit (IGUAL que tus otras consultas)
                import streamlit as st
                from google.oauth2 import service_account
                
                credentials = service_account.Credentials.from_service_account_info(
                    st.secrets["gcp_service_account"]
                )
                self.client = bigquery.Client(
                    credentials=credentials,
                    project=self.project_id
                )
                print(f"✅ Conectado a BigQuery (Streamlit Cloud)")
            else:
                # En local: usar archivo JSON (IGUAL que tus otras consultas)
                self.client = bigquery.Client.from_service_account_json(
                    self.credentials_path, 
                    project=self.project_id
                )
                print(f"✅ Conectado a BigQuery (Local)")
            
            return True
            
        except Exception as e:
            print(f"❌ Error conectando a BigQuery: {e}")
            return False

    def obtener_stock_bigquery(self):
        """
        Obtiene datos de stock desde BigQuery con TODAS las columnas necesarias
        
        Returns:
            DataFrame con columnas:
            - idarticulo, idartalfa
            - stk_corrientes, stk_express, stk_formosa, stk_hiper, stk_tirol, stk_central
            - stk_total
        """
        inicio = time.time()
        print(f"\n📥 Consultando stock desde BigQuery...")
        
        query = f"""
        SELECT 
            idarticulo,
            idartalfa,
            stk_corrientes,
            stk_express,
            stk_formosa,
            stk_hiper,
            stk_tirol,
            stk_central,
            stk_total
        FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
        """
        
        try:
            df_stock = self.client.query(query).to_dataframe()
            tiempo = time.time() - inicio
            
            print(f"✅ Stock obtenido: {len(df_stock):,} registros en {tiempo:.2f}s")
            print(f"   Columnas disponibles: {df_stock.columns.tolist()}")
            print(f"   Stock total (suma): {df_stock['stk_total'].sum():,.0f} unidades")
            
            return df_stock
            
        except Exception as e:
            print(f"❌ Error consultando BigQuery: {e}")
            return None
       
    def obtener_stock_bigquery00(self):
      """Obtiene datos de stock desde BigQuery"""
      inicio = time.time()
      print(f"\n📥 Consultando stock desde BigQuery...")
      
      query = f"""
      SELECT 
         idarticulo,
         stk_total
      FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
      WHERE stk_total > 0
      """
      
      try:
         df_stock = self.client.query(query).to_dataframe()
         tiempo = time.time() - inicio
         print(f"✅ Stock obtenido: {len(df_stock):,} registros en {tiempo:.2f}s")
         return df_stock
      except Exception as e:
         print(f"❌ Error consultando BigQuery: {e}")
         return None
    

#     # En cobertura_stock_exporter.py
#     def obtener_stock_completo_bigquery(self):
#         """Obtiene stock CON TODAS LAS SUCURSALES desde BigQuery"""
#         inicio = time.time()
#         print(f"\n📥 Consultando stock completo desde BigQuery...")
        
#         query = f"""
#         SELECT 
#             idarticulo,
#             idartalfa,
#             stk_corrientes,
#             stk_express,
#             stk_formosa,
#             stk_hiper,
#             stk_tirol,
#             stk_central,
#             stk_total
#         FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
#         """
        
#         try:
#             df_stock = self.client.query(query).to_dataframe()
#             tiempo = time.time() - inicio
#             print(f"✅ Stock obtenido: {len(df_stock):,} registros en {tiempo:.2f}s")
#             return df_stock
#         except Exception as e:
#             print(f"❌ Error consultando BigQuery: {e}")
#             return None
# #######################################################################################
#     def obtener_stock_bigquery(self):
#         """Obtiene datos de stock desde BigQuery CON TODAS LAS COLUMNAS"""
#         inicio = time.time()
#         print(f"\n📥 Consultando stock desde BigQuery...")
        
#         query = f"""
#         SELECT 
#             idarticulo,
#             idartalfa,
#             stk_corrientes,
#             stk_express,
#             stk_formosa,
#             stk_hiper,
#             stk_tirol,
#             stk_central,
#             stk_total
#         FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
#         """
        
#         try:
#             df_stock = self.client.query(query).to_dataframe()
#             tiempo = time.time() - inicio
#             print(f"✅ Stock obtenido: {len(df_stock):,} registros en {tiempo:.2f}s")
#             return df_stock
#         except Exception as e:
#             print(f"❌ Error consultando BigQuery: {e}")
#             return None
# #######################################################################################

    def calcular_cobertura(self, df_ventas, df_stock, fecha_inicio, fecha_fin, utilidad_minima=10000):
        """
        Calcula cobertura en días y clasifica
        
        Args:
            df_ventas: DataFrame con ventas y utilidad del periodo
            df_stock: DataFrame con stock actual de BigQuery
            fecha_inicio, fecha_fin: datetime para calcular días del periodo
        """
        inicio = time.time()
        print(f"\n🔄 Calculando cobertura...")
        
        # Calcular días del periodo
        dias_periodo = (fecha_fin - fecha_inicio).days + 1
        print(f"   • Periodo: {dias_periodo} días")
        
        # Merge de ventas con stock
        df_merged = df_ventas.merge(
            df_stock[['idarticulo', 'stk_total']], 
            on='idarticulo', 
            how='left'
        )
        
        # Rellenar stock faltante con 0
        df_merged['stk_total'] = df_merged['stk_total'].fillna(0)
        
        # Calcular venta promedio diaria
        df_merged['venta_promedio_diaria'] = df_merged['cantidad_vendida'] / dias_periodo
        
        # Calcular cobertura en días
        df_merged['cobertura_dias'] = np.where(
            df_merged['venta_promedio_diaria'] > 0,
            df_merged['stk_total'] / df_merged['venta_promedio_diaria'],
            999  # Sin ventas = cobertura infinita
        )
        
        # Clasificar cobertura
        def clasificar_cobertura(dias):
            if dias < 15:
                return '🔴 Crítico'
            elif dias < 31:
                return '🟡 Bajo'
            elif dias < 61:
                return '🟢 Óptimo'
            elif dias < 91:
                return '🟠 Alto'
            else:
                return '⚫ Exceso'
        
        df_merged['clasificacion'] = df_merged['cobertura_dias'].apply(clasificar_cobertura)
        
        # ⭐ FILTRAR POR UTILIDAD MÍNIMA
        print(f"   • Artículos antes de filtrar: {len(df_merged):,}")
        df_merged = df_merged[df_merged['utilidad_total'] > utilidad_minima].copy()
        print(f"   • Artículos después de filtrar: {len(df_merged):,}")
        print(f"   💵 Utilidad mínima aplicada: ${utilidad_minima:,.0f}")
        # # ⭐ FILTRAR UTILIDADES NEGATIVAS
        # print(f"   • Artículos antes de filtrar: {len(df_merged):,}")
        # df_merged = df_merged[df_merged['utilidad_total'] > 10000].copy()
        # print(f"   • Artículos después de filtrar (utilidad >= 0): {len(df_merged):,}\n ⚠️ Con utilidad > $ 10K.")

        # Ordenar por proveedor, familia, subfamilia, utilidad
        df_merged = df_merged.sort_values(by=['proveedor', 'familia', 'subfamilia', 'utilidad_total'],
            ascending=[True, True, True, False])

        tiempo = time.time() - inicio
        print(f"✅ Cobertura calculada en {tiempo:.2f}s")
        
        return df_merged
    
    def generar_excel(self, df, fecha_inicio, fecha_fin):
        """
        Genera archivo Excel con formato profesional
        
        Args:
            df: DataFrame con datos completos
            fecha_inicio, fecha_fin: para nombre del archivo
        """
        inicio = time.time()
        print(f"\n📊 Generando Excel profesional...")
        
        # Seleccionar y renombrar columnas
        # Calcular margen
        df['margen'] = (df['utilidad_total'] / df['venta_total'] * 100).fillna(0)
        
        columnas_finales = {
            'idarticulo': 'Código',
            'descripcion': 'Descripción',
            'proveedor': 'Proveedor',
            'familia': 'Familia',
            'subfamilia': 'SubFamilia',
            'venta_total': 'Venta Total',
            'utilidad_total': 'Utilidad Total',
            'margen': 'Margen',
            'cantidad_vendida': 'Cant. Vendida',
            'stk_total': 'Stock Total',
            'venta_promedio_diaria': 'Venta Prom/Día',
            'cobertura_dias': 'Cobertura (días)',
            'clasificacion': 'Clasificación'
        }
        
        df_export = df[list(columnas_finales.keys())].copy()
        df_export.rename(columns=columnas_finales, inplace=True)
        
        # Crear Excel en memoria
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, sheet_name='Cobertura Stock', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Cobertura Stock']
            
            # ═══ FORMATOS ═══
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#2C3E50',
                'font_color': 'white',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            
            # Formatos por clasificación
            formato_critico = workbook.add_format({'bg_color': '#E74C3C', 'font_color': 'white'})
            formato_bajo = workbook.add_format({'bg_color': '#F39C12', 'font_color': 'white'})
            formato_optimo = workbook.add_format({'bg_color': '#27AE60', 'font_color': 'white'})
            formato_alto = workbook.add_format({'bg_color': '#E67E22', 'font_color': 'white'})
            formato_exceso = workbook.add_format({'bg_color': '#95A5A6', 'font_color': 'white'})
            
            formato_numero = workbook.add_format({'num_format': '#,##0'})
            formato_decimal = workbook.add_format({'num_format': '#,##0.00'})
            formato_moneda = workbook.add_format({'num_format': '$#,##0.00'})
            formato_moneda_int = workbook.add_format({'num_format': '$#,##0'})
            formato_porcentaje = workbook.add_format({'num_format': '0.0%'})
            
            # ═══ APLICAR FORMATOS ═══
            # Header
            for col_num, value in enumerate(df_export.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Anchos de columna
            worksheet.set_column('A:A', 12)  # Código
            worksheet.set_column('B:B', 40)  # Descripción
            worksheet.set_column('C:C', 25)  # Proveedor
            worksheet.set_column('D:D', 20)  # Familia
            worksheet.set_column('E:E', 20)  # SubFamilia
            worksheet.set_column('F:F', 15)  # Venta Total
            worksheet.set_column('G:G', 15)  # Utilidad Total
            worksheet.set_column('H:H', 12)  # Margen
            worksheet.set_column('I:I', 15)  # Cant. Vendida
            worksheet.set_column('J:J', 15)  # Stock Total
            worksheet.set_column('K:K', 15)  # Venta Prom/Día
            worksheet.set_column('L:L', 18)  # Cobertura
            worksheet.set_column('M:M', 18)  # Clasificación
            
            # Aplicar formatos a datos
            for row_num in range(1, len(df_export) + 1):
                # Columnas de texto
                worksheet.write(row_num, 0, df_export.iloc[row_num-1]['Código'])
                worksheet.write(row_num, 1, df_export.iloc[row_num-1]['Descripción'])
                worksheet.write(row_num, 2, df_export.iloc[row_num-1]['Proveedor'])
                worksheet.write(row_num, 3, df_export.iloc[row_num-1]['Familia'])
                worksheet.write(row_num, 4, df_export.iloc[row_num-1]['SubFamilia'])
                
                # Columnas con formato moneda (SIN decimales)
                worksheet.write(row_num, 5, df_export.iloc[row_num-1]['Venta Total'], formato_moneda_int)
                worksheet.write(row_num, 6, df_export.iloc[row_num-1]['Utilidad Total'], formato_moneda_int)
                
                # Margen con formato porcentaje
                worksheet.write(row_num, 7, df_export.iloc[row_num-1]['Margen'] / 100, formato_porcentaje)
                
                # Cantidades con formato número
                worksheet.write(row_num, 8, df_export.iloc[row_num-1]['Cant. Vendida'], formato_numero)
                worksheet.write(row_num, 9, df_export.iloc[row_num-1]['Stock Total'], formato_numero)
                worksheet.write(row_num, 10, df_export.iloc[row_num-1]['Venta Prom/Día'], formato_numero)
                worksheet.write(row_num, 11, df_export.iloc[row_num-1]['Cobertura (días)'], formato_numero)
                
                # Clasificación con color
                clasificacion = df_export.iloc[row_num-1]['Clasificación']
                if '🔴' in clasificacion:
                    worksheet.write(row_num, 12, clasificacion, formato_critico)
                elif '🟡' in clasificacion:
                    worksheet.write(row_num, 12, clasificacion, formato_bajo)
                elif '🟢' in clasificacion:
                    worksheet.write(row_num, 12, clasificacion, formato_optimo)
                elif '🟠' in clasificacion:
                    worksheet.write(row_num, 12, clasificacion, formato_alto)
                else:
                    worksheet.write(row_num, 12, clasificacion, formato_exceso)
            
            # Congelar primera fila
            worksheet.freeze_panes(1, 0)
        
        output.seek(0)
        
        tiempo = time.time() - inicio
        print(f"✅ Excel generado en {tiempo:.2f}s")
        
        return output
    
    def exportar_completo(self, df_ventas, fecha_inicio, fecha_fin, utilidad_minima=10000):
        """
        Función principal que ejecuta todo el proceso
        
        Args:
            df_ventas: DataFrame con columnas:
                - idarticulo
                - descripcion
                - proveedor
                - familia
                - subfamilia
                - utilidad_total
                - cantidad_vendida
            fecha_inicio, fecha_fin: datetime
        
        Returns:
            BytesIO con Excel generado o None si hay error
        """
        inicio_total = time.time()
        
        print("\n" + "="*70)
        print("📦 GENERANDO REPORTE DE COBERTURA DE STOCK")
        print("="*70)
        
        # Conectar a BigQuery
        if not self.conectar_bigquery():
            return None
        
        # Obtener stock
        df_stock = self.obtener_stock_bigquery()
        if df_stock is None:
            return None
        
        # Calcular cobertura
        df_completo = self.calcular_cobertura(df_ventas, df_stock, fecha_inicio, fecha_fin, utilidad_minima)
        
        # Generar Excel
        excel_file = self.generar_excel(df_completo, fecha_inicio, fecha_fin)
        
        tiempo_total = time.time() - inicio_total
        
        print("\n" + "─"*70)
        print(f"✅ REPORTE GENERADO EXITOSAMENTE")
        print(f"   • Total artículos: {len(df_completo):,}")
        print(f"   • Tiempo total: {tiempo_total:.2f}s")
        print("="*70 + "\n")
        
        return excel_file
    
    def obtener_metricas(self, df_ventas, fecha_inicio, fecha_fin, utilidad_minima=10000):
        """
        Calcula métricas para la tarjeta de dashboard
        
        Returns:
            dict con métricas clave
        """
        # Obtener stock
        if not self.conectar_bigquery():
            return None
        
        df_stock = self.obtener_stock_bigquery()
        if df_stock is None:
            return None
        
        # Calcular cobertura
        df_completo = self.calcular_cobertura(df_ventas, df_stock, fecha_inicio, fecha_fin, utilidad_minima)
        
        # Calcular métricas
        metricas = {
            'stock_total': int(df_completo['stk_total'].sum()),
            'cobertura_promedio': round(df_completo['cobertura_dias'].mean(), 1),
            'articulos_sobrestock': int((df_completo['cobertura_dias'] > 60).sum()),
            'pct_sobrestock': round((df_completo['cobertura_dias'] > 60).sum() / len(df_completo) * 100, 1),
            'articulos_criticos': int((df_completo['cobertura_dias'] < 15).sum()),
            'pct_critico': round((df_completo['cobertura_dias'] < 15).sum() / len(df_completo) * 100, 1)
        }
        
        return metricas

# ═══════════════════════════════════════════════════════════════════
# FUNCIONES PARA USAR EN STREAMLIT
# ═══════════════════════════════════════════════════════════════════

def generar_reporte_cobertura(df_ventas, fecha_inicio, fecha_fin, credentials_path=None, project_id=None, utilidad_minima=10000):
    """
    Función simplificada para llamar desde Streamlit
    
    Returns:
        tuple: (excel_file, df_completo) - Excel BytesIO y DataFrame con datos completos
    """
    exporter = CoberturaStockExporter(credentials_path, project_id)
    
    # Conectar a BigQuery
    if not exporter.conectar_bigquery():
        return None, None
    
    # Obtener stock
    df_stock = exporter.obtener_stock_bigquery()
    if df_stock is None:
        return None, None
    
    # Calcular cobertura (este DF tiene TODAS las columnas)
    df_completo = exporter.calcular_cobertura(df_ventas, df_stock, fecha_inicio, fecha_fin, utilidad_minima)
    
    # Generar Excel
    excel_file = exporter.generar_excel(df_completo, fecha_inicio, fecha_fin)
    
    print(f"✅ Devolviendo Excel y DataFrame con {len(df_completo):,} registros")
    
    # Devolver AMBOS: el Excel y el DataFrame
    return excel_file, df_completo

def obtener_metricas_cobertura(df_ventas, fecha_inicio, fecha_fin, credentials_path=None, project_id=None):
    """
    Función simplificada para obtener métricas
    
    Args:
        df_ventas: DataFrame con datos de ventas
        fecha_inicio, fecha_fin: datetime
        credentials_path: Ruta al JSON (solo en local, None en nube)
        project_id: ID del proyecto de GCP
    
    Returns:
        dict con métricas
    """
    exporter = CoberturaStockExporter(credentials_path, project_id)
    return exporter.obtener_metricas(df_ventas, fecha_inicio, fecha_fin)