
import pandas as pd

def analizar_quiebre(df_presupuesto):
    resultados = []

    sucursales = ['corrientes', 'hiper', 'formosa', 'express']
    porc_cols = ['cor_porc', 'hip_porc', 'for_porc', 'exp_porc']
    stock_cols = ['stk_corrientes', 'stk_hiper', 'stk_formosa', 'stk_express']

    for suc, porc_col, stk_col in zip(sucursales, porc_cols, stock_cols):
        temp = df_presupuesto.copy()
        temp['sucursal'] = suc
        temp['porc_distribucion'] = temp[porc_col].fillna(0)
        temp['cnt_suc_estimada'] = temp['cnt_optima'] * temp['porc_distribucion']
        temp['stock_actual'] = temp[stk_col].fillna(0)

        # Cálculo de unidades y valor perdido
        temp['unidades_perdidas'] = (temp['cnt_suc_estimada'] - temp['stock_actual']).clip(lower=0)
        temp['valor_perdido'] = temp['unidades_perdidas'] * temp['precio_unitario']

        # Acción recomendada
        def recomendar_accion(row):
            if row['stock_actual'] == 0 and row['cnt_suc_estimada'] > 0:
                return 'Reposición urgente'
            elif row['stock_actual'] < row['cnt_suc_estimada']:
                return 'Monitorear reposición'
            else:
                return 'Stock suficiente'

        def explicar_accion(row):
            if row['stock_actual'] == 0:
                return f"Sin stock en {row['sucursal']} y se esperan {row['cnt_suc_estimada']:.1f} unidades vendidas."
            elif row['stock_actual'] < row['cnt_suc_estimada']:
                falta = row['cnt_suc_estimada'] - row['stock_actual']
                return f"Stock insuficiente en {row['sucursal']}, faltan {falta:.1f} unidades para cubrir demanda."
            else:
                return f"Stock suficiente en {row['sucursal']}."

        temp['accion_recomendada'] = temp.apply(recomendar_accion, axis=1)
        temp['explicacion_accion'] = temp.apply(explicar_accion, axis=1)

        resultados.append(temp)

    df_resultado = pd.concat(resultados, ignore_index=True)

    resumen = df_resultado.groupby(['idarticulo', 'descripcion']).agg({
        'unidades_perdidas': 'sum',
        'valor_perdido': 'sum'
    }).reset_index().rename(columns={
        'unidades_perdidas': 'unidades_perdidas_TOTAL',
        'valor_perdido': 'valor_perdido_TOTAL'
    })

    df_final = df_resultado.merge(resumen, on=['idarticulo', 'descripcion'])

    return df_final
