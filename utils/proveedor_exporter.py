"""
============================================================
MÓDULO: Proveedor Exporter
============================================================
Genera reportes Excel individuales por proveedor con formato
profesional y métricas detalladas.

Autor: Julio Lazarte
Fecha: Diciembre 2024
============================================================
"""

import pandas as pd
from io import BytesIO
from datetime import datetime
import time


# 🔧 AGREGAR AQUÍ - Diccionario de unificación de proveedores
PROVEEDOR_UNIFICADO = {
    # YAPUR → 12000001
    1358: 12000001, 1285: 12000001, 1084: 12000001, 463: 12000001,
    1346: 12000001, 1351: 12000001, 1361: 12000001, 1366: 12000001,
    # COCA → 12000002
    1268: 12000002, 1316: 12000002, 1867: 12000002,
    # UNILEVER → 12000003
    503: 12000003, 1313: 12000003, 9: 12000003, 2466: 12000003,
    # ARCOR → 12000004
    181: 12000004, 189: 12000004, 440: 12000004, 1073: 12000004, 193: 12000004,
    # QUILMES → 12000005
    1332: 12000005, 2049: 12000005, 1702: 12000005
}

# 📋 Diccionario con nombres de proveedores
NOMBRES_PROVEEDORES = {
    503: "UNILEVER DE ARG. - REF",
    440: "BAGLEY ARGENTINA S.A.",
    2466: "UNILEVER BPC",
    189: "ARCOR S.A.I.C.",
    9: "UNILEVER de Argentina S.A. HC",
    1316: "SALTA REFRESCOS S.A. (CTES)",
    1268: "Cia. Industrial Cervecera S.A.",
    1332: "CLARG S.A.",
    1285: "YAPUR",
    463: "J.J.YAPUR-CAR",
    1313: "MOLINOS TRES ARROYOS",
    181: "FRUTOS DE CUYO S.A.",
    1073: "LA CAMPAGNOLA S.A.",
    2049: "Cerveceria y Malteria Quilmes",
    1358: "JOSÉ JUAN YAPUR S.A.",
    1867: "Salta Refrescos (Chaco)",
    193: "DULCIORA S.A.",
    1702: "Alfa Nea S.A"
}

def obtener_ids_originales(id_proveedor):
    """
    Obtiene los IDs originales de un proveedor unificado con sus nombres.
    Si no es unificado, retorna solo el ID original con su nombre.
    
    Args:
        id_proveedor (int): ID del proveedor (puede ser unificado o no)
        
    Returns:
        list[str]: Lista de strings formato "ID (Nombre)" o "ID (proveedor)"
    """
    # IDs unificados (12000001 - 12000005)
    ids_unificados = [12000001, 12000002, 12000003, 12000004, 12000005]
    
    if id_proveedor in ids_unificados:
        # Es un ID unificado, obtener todos los IDs originales
        ids_originales = [k for k, v in PROVEEDOR_UNIFICADO.items() if v == id_proveedor]
    else:
        # No es unificado, retornar el mismo ID
        ids_originales = [id_proveedor]
    
    # Formatear con nombres
    resultado = []
    for id_orig in ids_originales:
        nombre = NOMBRES_PROVEEDORES.get(id_orig, "proveedor")
        resultado.append(f"{id_orig} ({nombre})")
    
    return resultado
# 🔧 AGREGAR AQUÍ - Diccionario de unificación de proveedores
# PROVEEDOR_UNIFICADO = {
#     # YAPUR → 12000001
#     1358: 12000001, 1285: 12000001, 1084: 12000001, 463: 12000001,
#     1346: 12000001, 1351: 12000001, 1361: 12000001, 1366: 12000001,
#     # COCA → 12000002
#     1268: 12000002, 1316: 12000002, 1867: 12000002,
#     # UNILEVER → 12000003
#     503: 12000003, 1313: 12000003, 9: 12000003, 2466: 12000003,
#     # ARCOR → 12000004
#     181: 12000004, 189: 12000004, 440: 12000004, 1073: 12000004, 193: 12000004,
#     # QUILMES → 12000005
#     1332: 12000005, 2049: 12000005, 1702: 12000005
# }

def obtener_ids_originales_simple(id_proveedor):
    """
    Obtiene los IDs originales de un proveedor unificado.
    Si no es unificado, retorna solo el ID original.
    
    Args:
        id_proveedor (int): ID del proveedor (puede ser unificado o no)
        
    Returns:
        list: Lista de IDs originales
    """
    # IDs unificados (12000001 - 12000005)
    ids_unificados = [12000001, 12000002, 12000003, 12000004, 12000005]
    
    if id_proveedor in ids_unificados:
        # Es un ID unificado, obtener todos los IDs originales
        ids_originales = [k for k, v in PROVEEDOR_UNIFICADO.items() if v == id_proveedor]
        return ids_originales
    else:
        # No es unificado, retornar el mismo ID
        return [id_proveedor]

def aplicar_formatos_proveedor(workbook):
    """
    Define formatos específicos para reportes de proveedores.
    
    Args:
        workbook: Objeto workbook de xlsxwriter
        
    Returns:
        dict: Diccionario con todos los formatos necesarios
    """
    formatos = {
        # Headers por categoría
        'header_default': workbook.add_format({
            'bold': True, 'bg_color': '#4472C4', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        }),
        'header_presupuesto': workbook.add_format({
            'bold': True, 'bg_color': '#FF9999', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        }),
        'header_stocks': workbook.add_format({
            'bold': True, 'bg_color': '#FFD699', 'font_color': 'black',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        }),
        'header_promedios': workbook.add_format({
            'bold': True, 'bg_color': '#A5D6A7', 'font_color': 'black',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        }),
        'header_cobertura': workbook.add_format({
            'bold': True, 'bg_color': '#81D4FA', 'font_color': 'black',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        }),
        'header_margenes': workbook.add_format({
            'bold': True, 'bg_color': '#CCCCCC', 'font_color': 'black',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        }),
        
        # Formatos de datos
        'moneda': workbook.add_format({'num_format': '$#,##0', 'border': 1}),
        'porcentaje': workbook.add_format({'num_format': '0.00"%"', 'border': 1}),
        'numero': workbook.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center'}),
        'texto': workbook.add_format({'border': 1, 'align': 'left'}),
        'presupuesto_data': workbook.add_format({
            'num_format': '$#,##0', 'border': 1, 'bg_color': '#FFCCCC'
        }),
        
        # Formatos condicionales para nivel_riesgo
        'riesgo_alto': workbook.add_format({
            'bg_color': '#FF3333', 'font_color': 'white', 'border': 1
        }),
        'riesgo_medio': workbook.add_format({
            'bg_color': '#FFCC99', 'border': 1
        }),
        'riesgo_bajo': workbook.add_format({
            'bg_color': '#66FF66', 'border': 1
        }),
        'riesgo_muy_bajo': workbook.add_format({
            'bg_color': '#33CC33', 'border': 1
        }),
        'riesgo_analizar': workbook.add_format({
            'bg_color': '#C0C0C0', 'font_color': 'white', 'border': 1
        })
    }
    
    return formatos


def get_header_format(col_name, formatos):
    """
    Retorna el formato de header apropiado según el nombre de la columna.
    
    Args:
        col_name (str): Nombre de la columna
        formatos (dict): Diccionario de formatos
        
    Returns:
        Format: Formato de xlsxwriter para el header
    """
    if col_name == 'PRESUPUESTO':
        return formatos['header_presupuesto']
    elif col_name in ['stk_corrientes', 'stk_express', 'stk_formosa', 'stk_hiper', 
                      'stk_TIROL', 'stk_central', 'STK_TOTAL', 'cnt_reabastecer']:
        return formatos['header_stocks']
    elif col_name in ['prom_gral', 'prom_3m', 'cnt_ultimos_7d', 'cnt_ultimos_14d', 'cnt_ultimo_mes']:
        return formatos['header_promedios']
    elif col_name in ['cnt_corregida', 'cantidad_optima', 'dias_cobertura', 'dias_cobertura_7d', 
                      'dias_cobertura_14d', 'dias_cobertura_30d']:
        return formatos['header_cobertura']
    elif col_name in ['margen_porc_all', 'margen_a90', 'margen_a30', 'margen_a14', 'margen_a7']:
        return formatos['header_margenes']
    else:
        return formatos['header_default']


def configurar_anchos_columnas(worksheet):
    """
    Configura los anchos de columna según el contenido.
    
    Args:
        worksheet: Objeto worksheet de xlsxwriter
    """
    worksheet.set_column('A:A', 12)   # idproveedor
    worksheet.set_column('B:B', 35)   # proveedor
    worksheet.set_column('C:D', 12)   # idarticulo, idarticuloalfa
    worksheet.set_column('E:F', 15)   # familia, subfamilia
    worksheet.set_column('G:G', 45)   # descripcion
    worksheet.set_column('H:H', 7)    # uxb
    worksheet.set_column('I:I', 12)   # costo_unit
    worksheet.set_column('J:P', 14)   # stocks
    worksheet.set_column('Q:Q', 15)   # cnt_reabastecer
    worksheet.set_column('R:V', 15)   # promedios y conteos
    worksheet.set_column('W:AA', 15)  # márgenes
    worksheet.set_column('AB:AD', 16) # cnt_corregida, cantidad_optima, PRESUPUESTO
    worksheet.set_column('AE:AE', 17) # meses_activos
    worksheet.set_column('AF:AI', 18) # dias_cobertura
    worksheet.set_column('AJ:AL', 15) # mes_pico, mes_bajo
    worksheet.set_column('AM:AM', 18) # nivel_riesgo
    worksheet.set_column('AN:AN', 20) # venta_total_articulo


def escribir_fila_datos(worksheet, row_num, row_data, formatos):
    """
    Escribe una fila de datos con formato apropiado.
    
    Args:
        worksheet: Objeto worksheet de xlsxwriter
        row_num (int): Número de fila
        row_data (Series): Datos de la fila
        formatos (dict): Diccionario de formatos
    """
    # Columnas básicas
    worksheet.write(row_num, 0, row_data['idproveedor'], formatos['numero'])
    worksheet.write(row_num, 1, row_data['proveedor'], formatos['texto'])
    worksheet.write(row_num, 2, row_data['idarticulo'], formatos['numero'])
    worksheet.write(row_num, 3, row_data['idarticuloalfa'], formatos['texto'])
    worksheet.write(row_num, 4, row_data['familia'], formatos['texto'])
    worksheet.write(row_num, 5, row_data['subfamilia'], formatos['texto'])
    worksheet.write(row_num, 6, row_data['descripcion'], formatos['texto'])
    worksheet.write(row_num, 7, row_data['uxb'], formatos['numero'])
    worksheet.write(row_num, 8, row_data['costo_unit'], formatos['moneda'])
    
    # Stocks (columnas 9-15)
    for col in range(9, 16):
        worksheet.write(row_num, col, row_data.iloc[col], formatos['numero'])
    
    # cnt_reabastecer
    worksheet.write(row_num, 16, row_data['cnt_reabastecer'], formatos['numero'])
    
    # Promedios
    worksheet.write(row_num, 17, row_data['prom_gral'], formatos['numero'])
    worksheet.write(row_num, 18, row_data['prom_3m'], formatos['numero'])
    
    # Conteos (19-21)
    for col in range(19, 22):
        worksheet.write(row_num, col, row_data.iloc[col], formatos['numero'])
    
    # Márgenes (22-26)
    # Márgenes (22-26) - Multiplicar por 100 porque están en decimal
    for col in range(22, 27):
      valor_decimal = row_data.iloc[col]
      valor_porcentaje = valor_decimal * 100 if valor_decimal is not None else 0
      worksheet.write(row_num, col, valor_porcentaje, formatos['porcentaje'])
   #  for col in range(22, 27):
      #   worksheet.write(row_num, col, row_data.iloc[col], formatos['porcentaje'])
    
    # cnt_corregida, cantidad_optima
    worksheet.write(row_num, 27, row_data['cnt_corregida'], formatos['numero'])
    worksheet.write(row_num, 28, row_data['cantidad_optima'], formatos['numero'])
    
    # PRESUPUESTO con fondo de color
    worksheet.write(row_num, 29, row_data['PRESUPUESTO'], formatos['presupuesto_data'])
    
    # meses_activos
    worksheet.write(row_num, 30, row_data['meses_activos'], formatos['texto'])
    
    # dias_cobertura (31-34)
    for col in range(31, 35):
        worksheet.write(row_num, col, row_data.iloc[col], formatos['numero'])
    
    # mes_pico, mes_bajo
    worksheet.write(row_num, 35, row_data['mes_pico'], formatos['texto'])
    worksheet.write(row_num, 36, row_data['mes_bajo'], formatos['texto'])
    
    # nivel_riesgo con formato condicional
    nivel = str(row_data['nivel_riesgo'])
    if nivel == 'Alto':
        worksheet.write(row_num, 37, nivel, formatos['riesgo_alto'])
    elif nivel == 'Medio':
        worksheet.write(row_num, 37, nivel, formatos['riesgo_medio'])
    elif nivel == 'Bajo':
        worksheet.write(row_num, 37, nivel, formatos['riesgo_bajo'])
    elif nivel == 'Muy Bajo':
        worksheet.write(row_num, 37, nivel, formatos['riesgo_muy_bajo'])
    elif nivel == 'Analizar stk':
        worksheet.write(row_num, 37, nivel, formatos['riesgo_analizar'])
    else:
        worksheet.write(row_num, 37, nivel, formatos['texto'])
    
    # venta_total_articulo
    worksheet.write(row_num, 38, row_data['venta_total_articulo'], formatos['moneda'])


def crear_excel_proveedor(df_proveedor, nombre_proveedor, fecha_inicio, fecha_fin, 
                          con_filtros=False, familias_activas=None, subfamilias_activas=None):
    """
    Genera archivo Excel con reporte detallado de un proveedor específico.
    
    Args:
        df_proveedor (pd.DataFrame): DataFrame con datos del proveedor
        nombre_proveedor (str): Nombre del proveedor
        fecha_inicio (str): Fecha inicio del período (formato: dd/mm/yyyy)
        fecha_fin (str): Fecha fin del período (formato: dd/mm/yyyy)
        con_filtros (bool): Si se aplicaron filtros de familia/subfamilia
        familias_activas (list): Lista de familias incluidas (opcional)
        subfamilias_activas (list): Lista de subfamilias incluidas (opcional)
        
    Returns:
        tuple: (BytesIO con Excel, nombre del archivo)
    """
    print(f"\n{'='*80}")
    print(f"📊 GENERANDO REPORTE EXCEL - PROVEEDOR: {nombre_proveedor}")
    print(f"{'='*80}")
    inicio_total = time.time()
    
    # Información del reporte
    tipo_analisis = "CON_FILTROS" if con_filtros else "SIN_FILTROS"
    
    print(f"   📅 Período: {fecha_inicio} - {fecha_fin}")
    print(f"   🎯 Tipo: {tipo_analisis}")
    print(f"   📦 Artículos: {len(df_proveedor):,}")
    
    if con_filtros:
        if familias_activas:
            print(f"   🏷️  Familias activas: {len(familias_activas)}")
        if subfamilias_activas:
            print(f"   📂 Subfamilias activas: {len(subfamilias_activas)}")
    
    print(f"{'='*80}\n")
    
    # Generar nombre de archivo
    fecha_ini_fmt = datetime.strptime(fecha_inicio, '%d/%m/%Y').strftime('%d%b%Y')
    fecha_fin_fmt = datetime.strptime(fecha_fin, '%d/%m/%Y').strftime('%d%b%Y')
   #  nombre_limpio = nombre_proveedor.replace(' ', '_').replace('/', '_').replace('\\', '_')
    import re
    nombre_limpio = re.sub(r"[ /\\]+", "_", nombre_proveedor)
    nombre_archivo = f"{nombre_limpio}{tipo_analisis}_{fecha_ini_fmt}_a_{fecha_fin_fmt}.xlsx"
    
    print(f"   📁 Nombre archivo: {nombre_archivo}")
    print(f"   {'─'*76}\n")
    
    # Crear buffer
    output = BytesIO()
    
    print(f"   🔧 Creando estructura Excel...")
    t1 = time.time()

    # Definir columnas exactas a exportar
    COLUMNAS_REPORTE = [
        'idproveedor', 'proveedor', 'idarticulo', 'idarticuloalfa', 'familia', 'subfamilia', 
        'descripcion', 'uxb', 'costo_unit', 'stk_corrientes', 'stk_express', 'stk_formosa', 
        'stk_hiper', 'stk_TIROL', 'stk_central', 'STK_TOTAL', 'cnt_reabastecer', 'prom_gral', 
        'prom_3m', 'cnt_ultimos_7d', 'cnt_ultimos_14d', 'cnt_ultimo_mes', 'margen_porc_all', 
        'margen_a90', 'margen_a30', 'margen_a14', 'margen_a7', 'cnt_corregida', 
        'cantidad_optima', 'PRESUPUESTO', 'meses_activos', 'dias_cobertura', 
        'dias_cobertura_7d', 'dias_cobertura_14d', 'dias_cobertura_30d', 'mes_pico', 
        'mes_bajo', 'nivel_riesgo', 'venta_total_articulo'
    ]
    
    # Filtrar solo las columnas que existen en el DataFrame
    columnas_disponibles = [col for col in COLUMNAS_REPORTE if col in df_proveedor.columns]
    df_proveedor = df_proveedor[columnas_disponibles].copy()
    
    print(f"   📊 Columnas en reporte: {len(columnas_disponibles)}")

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Escribir datos
        df_proveedor.to_excel(writer, sheet_name='Presupuesto', index=False)
        worksheet = writer.sheets['Presupuesto']
        
        # Obtener formatos
        formatos = aplicar_formatos_proveedor(workbook)
        
        print(f"   ✅ Estructura creada: {time.time() - t1:.2f}s")
        print(f"\n   🎨 Aplicando formatos...")
        t2 = time.time()
        
        # Configurar altura de headers
        worksheet.set_row(0, 30)
        
        # Aplicar formato a headers
        for col_num, col_name in enumerate(df_proveedor.columns.values):
            formato = get_header_format(col_name, formatos)
            worksheet.write(0, col_num, col_name, formato)
        
        # Configurar anchos de columna
        configurar_anchos_columnas(worksheet)
        
        print(f"   ✅ Headers formateados: {time.time() - t2:.2f}s")
        print(f"\n   📝 Escribiendo datos...")
        t3 = time.time()
        
        # Escribir datos con formato
        for row_num in range(1, len(df_proveedor) + 1):
            row_data = df_proveedor.iloc[row_num - 1]
            escribir_fila_datos(worksheet, row_num, row_data, formatos)
        
        print(f"   ✅ Datos escritos: {time.time() - t3:.2f}s")
        print(f"\n   🔒 Congelando panel...")
        
        # Congelar primera fila
        worksheet.freeze_panes(1, 0)
        
        # Agregar metadata al final
        print(f"   📋 Agregando metadata...")
        fila_metadata = len(df_proveedor) + 5
        
        worksheet.write(f'A{fila_metadata}', '═══════════════════════════════════════')
        fila_metadata += 1
        worksheet.write(f'A{fila_metadata}', f'📊 REPORTE GENERADO: {datetime.now().strftime("%d/%m/%Y %H:%M")}')
        fila_metadata += 1
        worksheet.write(f'A{fila_metadata}', f'📅 Período analizado: {fecha_inicio} - {fecha_fin}')
        fila_metadata += 1
        worksheet.write(f'A{fila_metadata}', f'🏢 Proveedor: {nombre_proveedor}')
        fila_metadata += 1
        worksheet.write(f'A{fila_metadata}', f'📦 Total artículos: {len(df_proveedor):,}')
        fila_metadata += 1
        
        # Información de filtros
        if con_filtros:
            worksheet.write(f'A{fila_metadata}', '🎯 ANÁLISIS CON FILTROS APLICADOS')
            fila_metadata += 1
            
            if familias_activas:
                worksheet.write(f'A{fila_metadata}', f'  • Familias: {len(familias_activas)} activas')
                fila_metadata += 1
            
            if subfamilias_activas:
                worksheet.write(f'A{fila_metadata}', f'  • Subfamilias: {len(subfamilias_activas)} activas')
                fila_metadata += 1
        else:
            worksheet.write(f'A{fila_metadata}', '📊 ANÁLISIS COMPLETO (SIN FILTROS)')
            fila_metadata += 1
            worksheet.write(f'A{fila_metadata}', '  • Incluye todas las familias y subfamilias')
        
        # Totales
        fila_metadata += 1
        worksheet.write(f'A{fila_metadata}', '═══════════════════════════════════════')
        fila_metadata += 1
        
        venta_total = df_proveedor['venta_total_articulo'].sum()
        presupuesto_total = df_proveedor['PRESUPUESTO'].sum()
        
        worksheet.write(f'A{fila_metadata}', f'💰 Venta Total: ${venta_total:,.0f}')
        fila_metadata += 1
        worksheet.write(f'A{fila_metadata}', f'💵 Presupuesto Total: ${presupuesto_total:,.0f}')
    
    output.seek(0)
    
    tiempo_total = time.time() - inicio_total
    
    # Resumen en terminal
    print(f"\n   {'─'*76}")
    print(f"   ✅ EXCEL GENERADO EXITOSAMENTE")
    print(f"   {'─'*76}")
    print(f"   📏 Artículos exportados: {len(df_proveedor):,}")
    print(f"   📊 Columnas: {len(df_proveedor.columns)}")
    print(f"   💰 Venta total: ${venta_total:,.0f}")
    print(f"   💵 Presupuesto total: ${presupuesto_total:,.0f}")
    print(f"   📁 Nombre archivo: {nombre_archivo}")
    print(f"   ⏱️  Tiempo total: {tiempo_total:.2f}s")
    print(f"   {'─'*76}")
    print(f"{'='*80}\n")
    
    return output, nombre_archivo


def generar_reporte_proveedor(df_presupuesto, id_proveedor, fecha_inicio, fecha_fin,
                              con_filtros=False, familias_activas=None, subfamilias_activas=None, proveedor_name=None):
    """
    Función principal para generar reporte de un proveedor específico.
    
    Args:
        df_presupuesto (pd.DataFrame): DataFrame completo con presupuesto
        id_proveedor (int): ID del proveedor a reportar
        fecha_inicio (str): Fecha inicio del período (formato: dd/mm/yyyy)
        fecha_fin (str): Fecha fin del período (formato: dd/mm/yyyy)
        con_filtros (bool): Si se aplicaron filtros
        familias_activas (list): Lista de familias incluidas
        subfamilias_activas (list): Lista de subfamilias incluidas
        
    Returns:
        tuple: (BytesIO con Excel, nombre del archivo)
    """
    print(f"\n{'='*80}")
    print(f"🎯 INICIANDO GENERACIÓN DE REPORTE PROVEEDOR")
    print(f"{'='*80}")
    print(f"   🔍 Filtrando datos para proveedor ID: {id_proveedor}")
    
    # Filtrar datos del proveedor
   #  df_prov = df_presupuesto[df_presupuesto['idproveedor'] == id_proveedor].copy()

   # Obtener IDs originales (si es unificado, obtiene todos los IDs)
    ids_a_buscar = obtener_ids_originales(id_proveedor)
      
    print(f"   🔍 IDs a buscar: {ids_a_buscar}")
    if len(ids_a_buscar) > 1:
      print(f"   ⚠️ Proveedor UNIFICADO detectado - Buscando {len(ids_a_buscar)} proveedores originales")

   # Filtrar datos del proveedor (uno o múltiples IDs)
    df_prov = df_presupuesto[df_presupuesto['idproveedor'].isin(ids_a_buscar)].copy()


    if len(df_prov) == 0:
        print(f"   ❌ ERROR: No se encontraron datos para el proveedor ID {id_proveedor}")
        return None, None
    
    nombre_proveedor = df_prov['proveedor'].iloc[0]
    print(f"   ✅ Proveedor encontrado: {nombre_proveedor}")
    print(f"   📦 Artículos encontrados: {len(df_prov):,}")
    
    # Ordenar por venta_total_articulo descendente
    df_prov = df_prov.sort_values('venta_total_articulo', ascending=False).reset_index(drop=True)
    
    # Generar Excel
    return crear_excel_proveedor(
        df_prov, 
        # nombre_proveedor,
        proveedor_name,
        fecha_inicio, 
        fecha_fin,
        con_filtros,
        familias_activas,
        subfamilias_activas
    )