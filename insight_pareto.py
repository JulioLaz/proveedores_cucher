from babel.numbers import format_currency

# ====== TEXTO AUTOMÁTICO PARA INSIGHT POR CATEGORÍA ======
def generar_insight_cantidad(counts):
    total = counts.sum()
    mayor_cat = counts.idxmax()
    pct_mayor = counts.max() / total * 100

    texto = f"""
    🧠 **Insight:**
    La categoría **{mayor_cat}** concentra la mayor cantidad de productos, con un total de **{counts.max()} artículos**, lo que representa aproximadamente **{pct_mayor:.1f}%** del total.
    Esto sugiere que una gran parte del surtido se encuentra en esta categoría, lo cual puede implicar una amplia variedad de productos con menor impacto individual.
    """
    return texto

def generar_insight_ventas(ventas):
    total = ventas.sum()
    top_cat = ventas.idxmax()
    val_top = ventas.max()
    pct_top = val_top / total * 100
   #  val_fmt = format_currency(val_top, '$', locale='es_AR', format='#,##0')
    val_fmt = val_top

    texto = f"""
    🧠 **Insight:**
    En términos de ventas, la categoría **{top_cat}** domina con un total de **{val_fmt}**, representando el **{pct_top:.1f}%** del total.
    Esta categoría es estratégica para los ingresos y debe ser priorizada en promociones, disponibilidad y análisis de margen.
    """
    return texto
