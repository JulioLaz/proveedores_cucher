import pandas as pd

def limpiar_datos(df):
    columnas_clave = ['cantidad_total', 'precio_total', 'costo_total', 'utilidad']
    
    # Eliminar filas con NaNs en columnas clave
    df = df.dropna(subset=columnas_clave)
    
    # Convertir a numérico por seguridad
    for col in columnas_clave:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Filtrar valores negativos o 0 donde no corresponden
    df = df[(df['cantidad_total'] > 0) & (df['precio_total'] >= 0) & (df['costo_total'] >= 0)]
    
    # Limpieza de strings
    df['sucursal'] = df['sucursal'].astype(str).str.strip().str.upper()
    df['familia'] = df['familia'].astype(str).str.strip().str.upper()
    df['subfamilia'] = df['subfamilia'].astype(str).str.strip().str.upper()
    df['descripcion'] = df['descripcion'].fillna("SIN DESCRIPCIÓN")
    
    return df