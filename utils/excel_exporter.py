"""
============================================================
MÓDULO: Excel Exporter
============================================================
Maneja la generación y formato de archivos Excel para
exportación de rankings y reportes.

Autor: Julio Lazarte
Fecha: 2024
============================================================
"""

import pandas as pd
from io import BytesIO
from datetime import datetime
import time


def aplicar_formato_excel(workbook):
    """
    Define formatos estándar para Excel.
    
    Returns:
        dict: Diccionario con formatos aplicables
    """
    formatos = {
        'moneda': workbook.add_format({
            'num_format': '$#,##0',
            'align': 'right',
            'border': 1
        }),
        'entero': workbook.add_format({
            'num_format': '#,##0',
            'align': 'center',
            'border': 1
        }),
        'porcentaje': workbook.add_format({
            'num_format': '0.00%',
            'align': 'center',
            'border': 1
        }),
        'header': workbook.add_format({
            'bold': True,
            'bg_color': '#2E5090',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True
        }),
        'texto': workbook.add_format({
            'align': 'left',
            'border': 1
        })
    }
    
    return formatos


def limpiar_dataframe_export(df):
    """
    Limpia el dataframe antes de exportar.
    
    Args:
        df (pd.DataFrame): DataFrame a limpiar
        
    Returns:
        pd.DataFrame: DataFrame limpio
    """
    print(f"\n{'='*60}")
    print("🧹 LIMPIANDO DATAFRAME PARA EXPORTACIÓN")
    print(f"{'='*60}")
    inicio = time.time()
    
    df_clean = df.copy()
    
    # Eliminar columnas vacías
    columnas_vacias = []
    for col in df_clean.columns:
        if df_clean[col].isna().all() or (df_clean[col] == 0).all():
            columnas_vacias.append(col)
    
    if columnas_vacias:
        print(f"   ❌ Eliminando {len(columnas_vacias)} columnas vacías:")
        for col in columnas_vacias:
            print(f"      • {col}")
        df_clean = df_clean.drop(columns=columnas_vacias)
    
    # Convertir tipos de datos
    conversiones = 0
    columnas_moneda = ['Venta Total', 'Costo Total', 'Utilidad', 'Presupuesto', 'Costo Exceso']
    columnas_entero = ['Artículos', 'Art. con Exceso', 'Art. Sin Stock', 'Ranking', 'Cantidad Vendida']
    columnas_decimal = ['Rentabilidad %', '% Participación Presupuesto', '% Participación Ventas']
    
    for col in columnas_moneda:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(float).round(0)
            conversiones += 1
    
    for col in columnas_entero:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(int)
            conversiones += 1
    
    for col in columnas_decimal:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(float).round(2)
            conversiones += 1
    
    tiempo = time.time() - inicio
    print(f"   ✅ {conversiones} columnas convertidas")
    print(f"   ⏱️  Tiempo: {tiempo:.2f}s")
    print(f"{'='*60}\n")
    
    return df_clean


def crear_excel_ranking(df, fecha_desde=None, fecha_hasta=None):
    """
    Crea archivo Excel con formato profesional para ranking de proveedores.
    
    Args:
        df (pd.DataFrame): DataFrame con datos del ranking
        fecha_desde (str, optional): Fecha inicio del período
        fecha_hasta (str, optional): Fecha fin del período
        
    Returns:
        BytesIO: Buffer con el archivo Excel generado
    """
    print(f"\n{'='*60}")
    print("📊 GENERANDO ARCHIVO EXCEL")
    print(f"{'='*60}")
    inicio = time.time()
    
    # Limpiar datos
    df_export = limpiar_dataframe_export(df)
    
    # Crear buffer
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Escribir datos
        df_export.to_excel(writer, index=False, sheet_name='Ranking')
        
        workbook = writer.book
        worksheet = writer.sheets['Ranking']
        formatos = aplicar_formato_excel(workbook)
        
        # === APLICAR FORMATO A HEADERS ===
        num_columnas = len(df_export.columns)
        worksheet.set_row(0, 30)  # Altura del header
        
        for i in range(num_columnas):
            worksheet.write(0, i, df_export.columns[i], formatos['header'])
        
        # Congelar primera fila
        worksheet.freeze_panes(1, 0)
        
        # === APLICAR FORMATO A COLUMNAS ===
        print(f"   📐 Aplicando formato a {num_columnas} columnas...")
        
        for i, col in enumerate(df_export.columns):
            max_len = max(len(str(col)), 12) + 2
            
            if col in ['Venta Total', 'Costo Total', 'Utilidad', 'Presupuesto', 'Costo Exceso']:
                worksheet.set_column(i, i, max(max_len, 15), formatos['moneda'])
                print(f"      💰 {col} → Formato moneda")
                
            elif col in ['Artículos', 'Art. con Exceso', 'Art. Sin Stock', 'Ranking', 'Cantidad Vendida']:
                worksheet.set_column(i, i, max_len, formatos['entero'])
                print(f"      🔢 {col} → Formato entero")
                
            elif col in ['Rentabilidad %', '% Participación Presupuesto', '% Participación Ventas']:
                worksheet.set_column(i, i, max_len, formatos['porcentaje'])
                print(f"      📊 {col} → Formato porcentaje")
                
            elif col == 'Proveedor':
                worksheet.set_column(i, i, 30, formatos['texto'])
                print(f"      📝 {col} → Ancho 30")
                
            else:
                worksheet.set_column(i, i, max_len, formatos['texto'])
        
        # === AGREGAR METADATA ===
        worksheet.write('A1000', f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}')
        if fecha_desde and fecha_hasta:
            worksheet.write('A1001', f'Período: {fecha_desde} - {fecha_hasta}')
    
    output.seek(0)
    
    tiempo = time.time() - inicio
    print(f"   ✅ Excel generado exitosamente")
    print(f"   📏 Filas: {len(df_export):,} | Columnas: {num_columnas}")
    print(f"   ⏱️  Tiempo: {tiempo:.2f}s")
    print(f"{'='*60}\n")
    
    return output


def generar_nombre_archivo(prefijo="ranking_proveedores", extension="xlsx"):
    """
    Genera nombre de archivo con timestamp.
    
    Args:
        prefijo (str): Prefijo del nombre
        extension (str): Extensión del archivo
        
    Returns:
        str: Nombre del archivo
    """
    fecha = datetime.now().strftime('%d%B%Y_%H%M')
    return f"{prefijo}_{fecha}.{extension}"