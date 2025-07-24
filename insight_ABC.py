def generar_insight_cantidad(counts):
    """Genera insights inteligentes sobre la distribución de cantidad de productos"""

    if counts.empty or counts.sum() == 0:
        return '<div class="warning-box">🚫 <strong>Sin datos disponibles:</strong> No se encontraron productos para analizar la distribución por cantidad.</div>'

    total = counts.sum()
    mayor_cat = counts.idxmax()
    pct_mayor = counts.max() / total * 100

    # Análisis de diversificación
    num_categorias = len(counts)
    diversificacion = "Alta" if num_categorias >= 5 else "Media" if num_categorias >= 3 else "Baja"

    # Análisis de concentración
    if pct_mayor >= 70:
        concentracion = "Muy alta"
        riesgo = "Alto"
        emoji = "🚨"
    elif pct_mayor >= 50:
        concentracion = "Alta"
        riesgo = "Medio-Alto"
        emoji = "⚠️"
    elif pct_mayor >= 30:
        concentracion = "Moderada"
        riesgo = "Medio"
        emoji = "📊"
    else:
        concentracion = "Baja"
        riesgo = "Bajo"
        emoji = "✅"

    if len(counts) > 1:
        segunda_cat = counts.nlargest(2).index[1]
        pct_segunda = counts[segunda_cat] / total * 100
        diferencia = pct_mayor - pct_segunda
        if diferencia >= 40:
            dominancia = "domina ampliamente"
        elif diferencia >= 20:
            dominancia = "lidera claramente"
        elif diferencia >= 10:
            dominancia = "supera moderadamente"
        else:
            dominancia = "compite estrechamente con"
    else:
        segunda_cat = None
        dominancia = "es la única categoría"

    if concentracion in ["Muy alta", "Alta"]:
        recomendacion = f"<strong>Recomendación crítica:</strong> Diversificar el portafolio para reducir la dependencia de <strong>{mayor_cat}</strong>."
    elif concentracion == "Moderada":
        recomendacion = f"<strong>Oportunidad:</strong> <strong>{mayor_cat}</strong> tiene buen potencial. Evaluar si aumentar su participación."
    else:
        recomendacion = f"<strong>Fortaleza:</strong> Excelente diversificación del portafolio."

    insight_html = f"""
    <div class="insight-box">
        <div class="insight-titulo">{emoji} <strong>Análisis de Distribución por Cantidad:</strong></div>
        <p>La categoría <strong>{mayor_cat}</strong> {dominancia} {"a " + segunda_cat if segunda_cat else "el mercado"} con <strong>{counts.max()} productos</strong> (<strong>{pct_mayor:.1f}%</strong> del total).</p>
        <p><strong>📈 Características del portafolio:</strong></p>
        <ul>
            <li><strong>Diversificación:</strong> {diversificacion} ({num_categorias} categorías activas)</li>
            <li><strong>Concentración:</strong> {concentracion} en categoría líder</li>
            <li><strong>Nivel de riesgo:</strong> {riesgo}</li>
    """

    if segunda_cat:
        insight_html += f'<li><strong>Segunda categoría:</strong> {segunda_cat} con {counts[segunda_cat]} productos ({pct_segunda:.1f}%)</li>'

    insight_html += f"""
        </ul>
        <p>💡 {recomendacion}</p>
    </div>
    """
    return insight_html

# def generar_insight_ventas(ventas):
#     """Genera insights inteligentes sobre la distribución de ventas por categoría"""
    
#     if ventas.empty or ventas.sum() == 0:
#         return "🚫 **Sin datos disponibles:** No se encontraron ventas para analizar la distribución por categoría."
    
#     total = ventas.sum()
#     top_cat = ventas.idxmax()
#     val_top = ventas.max()
#     pct_top = val_top / total * 100
#     val_fmt = f"${val_top:,.0f}"
    
#     # Análisis de concentración de ingresos según regla 80/20
#     if pct_top >= 80:
#         concentracion = "extrema"
#         analisis_pareto = "monopolio comercial"
#         emoji = "🔴"
#         urgencia = "CRÍTICO"
#     elif pct_top >= 60:
#         concentracion = "muy alta"
#         analisis_pareto = "dominio claro (fuera del ideal 80/20)"
#         emoji = "🟠"
#         urgencia = "ALTO"
#     elif pct_top >= 40:
#         concentracion = "alta"
#         analisis_pareto = "liderazgo sólido"
#         emoji = "📈"
#         urgencia = "MEDIO"
#     elif pct_top >= 20:
#         concentracion = "moderada"
#         analisis_pareto = "participación equilibrada"
#         emoji = "✅"
#         urgencia = "BUENO"
#     else:
#         concentracion = "baja"
#         analisis_pareto = "distribución muy fragmentada"
#         emoji = "📊"
#         urgencia = "MEDIO"
    
#     # Análisis comparativo con otras categorías
#     if len(ventas) > 1:
#         segunda_cat = ventas.nlargest(2).index[1]
#         val_segunda = ventas[segunda_cat]
#         pct_segunda = val_segunda / total * 100
#         val_segunda_fmt = f"${val_segunda:,.0f}"
#         ratio_liderazgo = val_top / val_segunda
        
#         if ratio_liderazgo >= 5:
#             comparacion = f"supera por **{ratio_liderazgo:.1f}x** a {segunda_cat}"
#         elif ratio_liderazgo >= 2:
#             comparacion = f"duplica las ventas de {segunda_cat}"
#         elif ratio_liderazgo >= 1.5:
#             comparacion = f"supera moderadamente a {segunda_cat}"
#         else:
#             comparacion = f"compite estrechamente con {segunda_cat}"
        
#         # Análisis de top 2 categorías
#         top2_concentration = pct_top + pct_segunda
#         if top2_concentration >= 80:
#             duopolio = f"**Duopolio detectado:** Las top 2 categorías concentran {top2_concentration:.1f}% de las ventas."
#         else:
#             duopolio = f"**Distribución:** Top 2 categorías representan {top2_concentration:.1f}% del negocio."
#     else:
#         segunda_cat = None
#         comparacion = "es la única categoría con ventas"
#         duopolio = "**Monopolio total:** Una sola categoría genera todos los ingresos."
    
#     # Recomendaciones estratégicas específicas
#     if urgencia == "CRÍTICO":
#         recomendacion = f"🚨 **ACCIÓN INMEDIATA:** Diversificar urgentemente. La dependencia del {pct_top:.1f}% en {top_cat} es un riesgo comercial extremo."
#     elif urgencia == "ALTO":
#         recomendacion = f"⚠️ **PRIORIDAD ALTA:** Desarrollar categorías alternativas. Reducir dependencia de {top_cat}."
#     elif urgencia == "MEDIO" and concentracion == "alta":
#         recomendacion = f"📈 **OPORTUNIDAD:** {top_cat} es un motor sólido. Optimizar su rentabilidad."
#     elif urgencia == "BUENO":
#         recomendacion = f"✅ **FORTALEZA:** Excelente equilibrio. {top_cat} lidera sin crear riesgo excesivo."
#     else:
#         recomendacion = f"🎯 **ESTRATEGIA:** Evaluar si consolidar liderazgo en {top_cat} o buscar mayor equilibrio."
    
#     # Construir insight completo
#     insight_text = f"{emoji} **Análisis de Concentración de Ventas ({urgencia})**\n\n"
#     insight_text += f"**{top_cat}** domina con **{val_fmt}** (**{pct_top:.1f}%** del total) y {comparacion}.\n\n"
    
#     insight_text += f"📊 **Análisis Pareto:**\n"
#     insight_text += f"• Tipo de concentración: {analisis_pareto}\n"
#     insight_text += f"• Nivel de riesgo: {urgencia}\n"
#     insight_text += f"• {duopolio}\n"
    
#     if segunda_cat:
#         insight_text += f"• Segunda categoría: {segunda_cat} con {val_segunda_fmt} ({pct_segunda:.1f}%)\n"
    
#     insight_text += f"\n{recomendacion}"
    
#     return f'<div class="insight-box">{insight_text}</div>'


# def generar_insight_margen(margenes):
#     """Genera insights sobre la distribución de márgenes por categoría"""
    
#     if margenes.empty or margenes.sum() == 0:
#         return "🚫 **Sin datos disponibles:** No se encontraron datos de margen para analizar."
    
#     mejor_cat = margenes.idxmax()
#     mejor_margen = margenes.max()
#     margen_promedio = margenes.mean()
    
#     # Análisis de rentabilidad
#     if mejor_margen >= 40:
#         rentabilidad = "excelente"
#         emoji = "💎"
#     elif mejor_margen >= 30:
#         rentabilidad = "muy buena"
#         emoji = "📈"
#     elif mejor_margen >= 20:
#         rentabilidad = "aceptable"
#         emoji = "📊"
#     elif mejor_margen >= 10:
#         rentabilidad = "baja"
#         emoji = "⚠️"
#     else:
#         rentabilidad = "crítica"
#         emoji = "🚨"
    
#     # Dispersión de márgenes
#     if len(margenes) > 1:
#         std_margenes = margenes.std()
#         if std_margenes >= 15:
#             variabilidad = "alta variabilidad entre categorías - oportunidad de optimización"
#         elif std_margenes >= 8:
#             variabilidad = "variabilidad moderada - gestión diferenciada recomendada"
#         else:
#             variabilidad = "márgenes consistentes entre categorías"
#     else:
#         variabilidad = "única categoría disponible"
    
#     insight_text = f"{emoji} **Análisis de Rentabilidad por Categoría**\n\n"
#     insight_text += f"**{mejor_cat}** lidera en rentabilidad con **{mejor_margen:.1f}%** de margen (rentabilidad {rentabilidad}).\n\n"
#     insight_text += f"📈 **Características:**\n"
#     insight_text += f"• Margen promedio general: {margen_promedio:.1f}%\n"
#     insight_text += f"• Dispersión: {variabilidad}\n\n"
#     insight_text += f"💡 **Recomendación:** {'Maximizar volumen en ' + mejor_cat if mejor_margen >= 25 else 'Revisar estrategia de precios en ' + mejor_cat}"
    
#     return f'<div class="warning-box">{insight_text}</div>'


# def generar_insight_abc_completo(abc_counts, abc_ventas):
#     """Genera un insight integral combinando cantidad y ventas del análisis ABC"""
    
#     if abc_counts.empty or abc_ventas.empty:
#         return "🚫 **Sin datos disponibles:** No se puede realizar análisis ABC completo."
    
#     # Productos A
#     productos_a = abc_counts.get('A (Alto valor)', 0)
#     ventas_a = abc_ventas.get('A (Alto valor)', 0)
#     pct_ventas_a = (ventas_a / abc_ventas.sum() * 100) if abc_ventas.sum() > 0 else 0
    
#     # Eficiencia de productos A
#     total_productos = abc_counts.sum()
#     pct_productos_a = (productos_a / total_productos * 100) if total_productos > 0 else 0
    
#     # Ratio de eficiencia (% ventas / % productos)
#     eficiencia_ratio = (pct_ventas_a / pct_productos_a) if pct_productos_a > 0 else 0
    
#     # Análisis de eficiencia
#     if eficiencia_ratio >= 4:
#         eficiencia = "excepcional"
#         emoji = "🏆"
#     elif eficiencia_ratio >= 3:
#         eficiencia = "excelente"
#         emoji = "💎"
#     elif eficiencia_ratio >= 2:
#         eficiencia = "buena"
#         emoji = "📈"
#     else:
#         eficiencia = "mejorable"
#         emoji = "⚠️"
    
#     # Productos B y C
#     productos_bc = abc_counts.get('B (Valor medio)', 0) + abc_counts.get('C (Bajo valor)', 0)
#     ventas_bc = abc_ventas.get('B (Valor medio)', 0) + abc_ventas.get('C (Bajo valor)', 0)
#     pct_ventas_bc = (ventas_bc / abc_ventas.sum() * 100) if abc_ventas.sum() > 0 else 0
    
#     # Recomendaciones específicas
#     if pct_productos_a <= 15 and pct_ventas_a >= 70:
#         estrategia = "**Estrategia ideal:** Pocos productos de alto impacto. Maximizar disponibilidad y promoción de productos A."
#     elif pct_productos_a >= 30:
#         estrategia = f"**Oportunidad:** Demasiados productos A ({productos_a}). Evaluar cuáles realmente generan valor."
#     elif pct_ventas_a <= 50:
#         estrategia = "**Alerta:** Productos A no están generando el impacto esperado. Revisar estrategia comercial."
#     else:
#         estrategia = "**Equilibrio adecuado:** Los productos A están cumpliendo su función estratégica."
    
#     insight_text = f"{emoji} **Análisis ABC Integral - Eficiencia {eficiencia.capitalize()}**\n\n"
#     insight_text += f"**Productos Clase A:** {productos_a} productos ({pct_productos_a:.1f}%) generan **{pct_ventas_a:.1f}%** de las ventas.\n"
#     insight_text += f"**Ratio de eficiencia:** {eficiencia_ratio:.1f}x (cada producto A equivale a {eficiencia_ratio:.1f} productos promedio)\n\n"
    
#     insight_text += f"📊 **Distribución completa:**\n"
#     insight_text += f"• Productos A: {productos_a} unidades - ${abc_ventas.get('A (Alto valor)', 0):,.0f}\n"
#     insight_text += f"• Productos B+C: {productos_bc} unidades - ${ventas_bc:,.0f} ({pct_ventas_bc:.1f}%)\n\n"
    
#     insight_text += f"{estrategia}\n\n"
#     insight_text += f"💡 **Foco recomendado:** {'Potenciar productos A' if eficiencia_ratio >= 2.5 else 'Revisar clasificación y optimizar productos B/C'}"

#     return f'<div class="success-box">{insight_text}</div>'

def generar_insight_ventas(ventas):
    if ventas.empty or ventas.sum() == 0:
        return '<div class="warning-box">🚫 <strong>Sin datos disponibles:</strong> No se encontraron ventas para analizar la distribución por categoría.</div>'

    total = ventas.sum()
    top_cat = ventas.idxmax()
    val_top = ventas.max()
    pct_top = val_top / total * 100
    val_fmt = f"${val_top:,.0f}"

    # Nivel de concentración
    if pct_top >= 80:
        concentracion = "Extrema"
        pareto = "Monopolio comercial"
        emoji = "🔴"
        urgencia = "CRÍTICO"
    elif pct_top >= 60:
        concentracion = "Muy alta"
        pareto = "Dominio claro (fuera del ideal 80/20)"
        emoji = "🟠"
        urgencia = "ALTO"
    elif pct_top >= 40:
        concentracion = "Alta"
        pareto = "Liderazgo sólido"
        emoji = "📈"
        urgencia = "MEDIO"
    elif pct_top >= 20:
        concentracion = "Moderada"
        pareto = "Participación equilibrada"
        emoji = "✅"
        urgencia = "BUENO"
    else:
        concentracion = "Baja"
        pareto = "Distribución muy fragmentada"
        emoji = "📊"
        urgencia = "MEDIO"

    # Segunda categoría
    if len(ventas) > 1:
        segunda_cat = ventas.nlargest(2).index[1]
        val_seg = ventas[segunda_cat]
        pct_seg = val_seg / total * 100
        val_seg_fmt = f"${val_seg:,.0f}"
        ratio = val_top / val_seg

        if ratio >= 5:
            comparacion = f"supera por <strong>{ratio:.1f}x</strong> a {segunda_cat}"
        elif ratio >= 2:
            comparacion = f"duplica las ventas de {segunda_cat}"
        elif ratio >= 1.5:
            comparacion = f"supera moderadamente a {segunda_cat}"
        else:
            comparacion = f"compite estrechamente con {segunda_cat}"

        top2_pct = pct_top + pct_seg
        duopolio = f"<strong>Duopolio detectado:</strong> Las top 2 categorías concentran {top2_pct:.1f}% de las ventas." if top2_pct >= 80 else f"<strong>Distribución:</strong> Top 2 categorías representan {top2_pct:.1f}% del negocio."
    else:
        segunda_cat = None
        comparacion = "es la única categoría con ventas"
        duopolio = "<strong>Monopolio total:</strong> Una sola categoría genera todos los ingresos."

    # Recomendación
    if urgencia == "CRÍTICO":
        recomendacion = f"🚨 <strong>ACCIÓN INMEDIATA:</strong> Diversificar urgentemente. La dependencia del {pct_top:.1f}% en <strong>{top_cat}</strong> es un riesgo comercial extremo."
    elif urgencia == "ALTO":
        recomendacion = f"⚠️ <strong>PRIORIDAD ALTA:</strong> Desarrollar categorías alternativas. Reducir dependencia de <strong>{top_cat}</strong>."
    elif urgencia == "MEDIO" and concentracion == "Alta":
        recomendacion = f"📈 <strong>OPORTUNIDAD:</strong> <strong>{top_cat}</strong> es un motor sólido. Optimizar su rentabilidad."
    elif urgencia == "BUENO":
        recomendacion = f"✅ <strong>FORTALEZA:</strong> Excelente equilibrio. <strong>{top_cat}</strong> lidera sin crear riesgo excesivo."
    else:
        recomendacion = f"🎯 <strong>ESTRATEGIA:</strong> Evaluar si consolidar liderazgo en <strong>{top_cat}</strong> o buscar mayor equilibrio."

    # HTML final
    html = f"""
    <div class="warning-box">
        <div class="insight-titulo">{emoji} <strong>Análisis de Concentración de Ventas ({urgencia})</strong></div>
        <p><strong>{top_cat}</strong> domina con <strong>{val_fmt}</strong> (<strong>{pct_top:.1f}%</strong> del total) y {comparacion}.</p>
        <p><strong>📊 Análisis Pareto:</strong></p>
        <ul>
            <li><strong>Tipo de concentración:</strong> {pareto}</li>
            <li><strong>Nivel de riesgo:</strong> {urgencia}</li>
            <li>{duopolio}</li>
    """
    if segunda_cat:
        html += f'<li><strong>Segunda categoría:</strong> {segunda_cat} con {val_seg_fmt} ({pct_seg:.1f}%)</li>'
    html += f"""
        </ul>
        <p>{recomendacion}</p>
    </div>
    """
    return html


def generar_insight_margen(margenes):
    if margenes.empty or margenes.sum() == 0:
        return '<div class="warning-box">🚫 <strong>Sin datos disponibles:</strong> No se encontraron datos de margen para analizar.</div>'

    mejor_cat = margenes.idxmax()
    mejor_margen = margenes.max()
    margen_promedio = margenes.mean()

    if mejor_margen >= 40:
        rentabilidad = "Excelente"
        emoji = "💎"
    elif mejor_margen >= 30:
        rentabilidad = "Muy buena"
        emoji = "📈"
    elif mejor_margen >= 20:
        rentabilidad = "Aceptable"
        emoji = "📊"
    elif mejor_margen >= 10:
        rentabilidad = "Baja"
        emoji = "⚠️"
    else:
        rentabilidad = "Crítica"
        emoji = "🚨"

    if len(margenes) > 1:
        std = margenes.std()
        if std >= 15:
            dispersion = "Alta variabilidad entre categorías - oportunidad de optimización"
        elif std >= 8:
            dispersion = "Variabilidad moderada - gestión diferenciada recomendada"
        else:
            dispersion = "Márgenes consistentes entre categorías"
    else:
        dispersion = "Única categoría disponible"

    html = f"""
    <div class="insight-box">
        <div class="insight-titulo">{emoji} <strong>Análisis de Rentabilidad por Categoría</strong></div>
        <p><strong>{mejor_cat}</strong> lidera en rentabilidad con <strong>{mejor_margen:.1f}%</strong> de margen (<em>{rentabilidad}</em>).</p>
        <p><strong>📈 Características:</strong></p>
        <ul>
            <li><strong>Margen promedio general:</strong> {margen_promedio:.1f}%</li>
            <li><strong>Dispersión:</strong> {dispersion}</li>
        </ul>
        <p>💡 <strong>Recomendación:</strong> {"Maximizar volumen en " + mejor_cat if mejor_margen >= 25 else "Revisar estrategia de precios en " + mejor_cat}</p>
    </div>
    """
    return html


def generar_insight_abc_completo(abc_counts, abc_ventas):
    if abc_counts.empty or abc_ventas.empty:
        return '<div class="warning-box">🚫 <strong>Sin datos disponibles:</strong> No se puede realizar análisis ABC completo.</div>'

    a = abc_counts.get('A (Alto valor)', 0)
    ventas_a = abc_ventas.get('A (Alto valor)', 0)
    total_productos = abc_counts.sum()
    total_ventas = abc_ventas.sum()

    pct_a = (a / total_productos) * 100 if total_productos > 0 else 0
    pct_ventas_a = (ventas_a / total_ventas) * 100 if total_ventas > 0 else 0
    eficiencia = (pct_ventas_a / pct_a) if pct_a > 0 else 0

    if eficiencia >= 4:
        nivel = "Excepcional"
        emoji = "🏆"
    elif eficiencia >= 3:
        nivel = "Excelente"
        emoji = "💎"
    elif eficiencia >= 2:
        nivel = "Buena"
        emoji = "📈"
    else:
        nivel = "Mejorable"
        emoji = "⚠️"

    # Productos B y C
    b = abc_counts.get('B (Valor medio)', 0)
    c = abc_counts.get('C (Bajo valor)', 0)
    ventas_bc = abc_ventas.get('B (Valor medio)', 0) + abc_ventas.get('C (Bajo valor)', 0)
    productos_bc = b + c
    pct_ventas_bc = (ventas_bc / total_ventas) * 100 if total_ventas > 0 else 0

    if pct_a <= 15 and pct_ventas_a >= 70:
        estrategia = "<strong>Estrategia ideal:</strong> Pocos productos de alto impacto. Potenciar productos A."
    elif pct_a >= 30:
        estrategia = f"<strong>Oportunidad:</strong> Demasiados productos A ({a}). Evaluar cuáles realmente generan valor."
    elif pct_ventas_a <= 50:
        estrategia = "<strong>Alerta:</strong> Productos A no están generando el impacto esperado. Revisar estrategia comercial."
    else:
        estrategia = "<strong>Equilibrio adecuado:</strong> Los productos A cumplen su función estratégica."

    html = f"""
    <div class="success-box">
        <div class="insight-titulo">{emoji} <strong>Análisis ABC Integral - Eficiencia {nivel}</strong></div>
        <p><strong>Productos A:</strong> {a} productos ({pct_a:.1f}%) generan <strong>{pct_ventas_a:.1f}%</strong> de las ventas.</p>
        <p><strong>Ratio de eficiencia:</strong> {eficiencia:.1f}x (cada producto A equivale a {eficiencia:.1f} productos promedio)</p>
        <p><strong>📊 Distribución completa:</strong></p>
        <ul>
            <li><strong>Productos A:</strong> {a} unidades – ${ventas_a:,.0f}</li>
            <li><strong>Productos B+C:</strong> {productos_bc} unidades – ${ventas_bc:,.0f} ({pct_ventas_bc:.1f}%)</li>
        </ul>
        <p>{estrategia}</p>
        <p>💡 <strong>Foco recomendado:</strong> {"Potenciar productos A" if eficiencia >= 2.5 else "Optimizar productos B/C y revisar clasificación"}</p>
    </div>
    """
    return html
