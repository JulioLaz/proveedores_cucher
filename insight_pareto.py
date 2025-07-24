def generar_insight_cantidad(counts):
    """Genera insights inteligentes sobre la distribución de cantidad de productos"""
    
    if counts.empty or counts.sum() == 0:
        return "🚫 **Sin datos disponibles:** No se encontraron productos para analizar la distribución por cantidad."
    
    total = counts.sum()
    mayor_cat = counts.idxmax()
    pct_mayor = counts.max() / total * 100
    
    # Análisis de diversificación
    num_categorias = len(counts)
    diversificacion = "alta" if num_categorias >= 5 else "media" if num_categorias >= 3 else "baja"
    
    # Análisis de concentración
    if pct_mayor >= 70:
        concentracion = "muy alta"
        riesgo = "alto"
        emoji = "🚨"
    elif pct_mayor >= 50:
        concentracion = "alta"
        riesgo = "medio-alto"
        emoji = "⚠️"
    elif pct_mayor >= 30:
        concentracion = "moderada"
        riesgo = "medio"
        emoji = "📊"
    else:
        concentracion = "baja"
        riesgo = "bajo"
        emoji = "✅"
    
    # Análisis de las otras categorías
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
    
    # Recomendaciones específicas
    if concentracion in ["muy alta", "alta"]:
        recomendacion = f"💡 **Recomendación crítica:** Diversificar el portafolio para reducir la dependencia de {mayor_cat}."
    elif concentracion == "moderada":
        recomendacion = f"💡 **Oportunidad:** {mayor_cat} tiene buen potencial. Evaluar si aumentar su participación."
    else:
        recomendacion = f"💡 **Fortaleza:** Excelente diversificación del portafolio."
    
    # Construir insight personalizado
    insight_text = f"{emoji} **Análisis de Distribución por Cantidad**\n\n"
    insight_text += f"La categoría **{mayor_cat}** {dominancia} {'a ' + segunda_cat if segunda_cat else 'el mercado'} con **{counts.max()} productos** (**{pct_mayor:.1f}%** del total).\n\n"
    
    insight_text += f"📈 **Características del portafolio:**\n"
    insight_text += f"• Diversificación: {diversificacion.capitalize()} ({num_categorias} categorías activas)\n"
    insight_text += f"• Concentración: {concentracion.capitalize()} en categoría líder\n"
    insight_text += f"• Nivel de riesgo: {riesgo.capitalize()}\n"
    
    if segunda_cat:
        insight_text += f"• Segunda categoría: {segunda_cat} con {counts[segunda_cat]} productos ({pct_segunda:.1f}%)\n"
    
    insight_text += f"\n{recomendacion}"
    
    return insight_text


def generar_insight_ventas(ventas):
    """Genera insights inteligentes sobre la distribución de ventas por categoría"""
    
    if ventas.empty or ventas.sum() == 0:
        return "🚫 **Sin datos disponibles:** No se encontraron ventas para analizar la distribución por categoría."
    
    total = ventas.sum()
    top_cat = ventas.idxmax()
    val_top = ventas.max()
    pct_top = val_top / total * 100
    val_fmt = f"${val_top:,.0f}"
    
    # Análisis de concentración de ingresos según regla 80/20
    if pct_top >= 80:
        concentracion = "extrema"
        analisis_pareto = "monopolio comercial"
        emoji = "🔴"
        urgencia = "CRÍTICO"
    elif pct_top >= 60:
        concentracion = "muy alta"
        analisis_pareto = "dominio claro (fuera del ideal 80/20)"
        emoji = "🟠"
        urgencia = "ALTO"
    elif pct_top >= 40:
        concentracion = "alta"
        analisis_pareto = "liderazgo sólido"
        emoji = "📈"
        urgencia = "MEDIO"
    elif pct_top >= 20:
        concentracion = "moderada"
        analisis_pareto = "participación equilibrada"
        emoji = "✅"
        urgencia = "BUENO"
    else:
        concentracion = "baja"
        analisis_pareto = "distribución muy fragmentada"
        emoji = "📊"
        urgencia = "MEDIO"
    
    # Análisis comparativo con otras categorías
    if len(ventas) > 1:
        segunda_cat = ventas.nlargest(2).index[1]
        val_segunda = ventas[segunda_cat]
        pct_segunda = val_segunda / total * 100
        val_segunda_fmt = f"${val_segunda:,.0f}"
        ratio_liderazgo = val_top / val_segunda
        
        if ratio_liderazgo >= 5:
            comparacion = f"supera por **{ratio_liderazgo:.1f}x** a {segunda_cat}"
        elif ratio_liderazgo >= 2:
            comparacion = f"duplica las ventas de {segunda_cat}"
        elif ratio_liderazgo >= 1.5:
            comparacion = f"supera moderadamente a {segunda_cat}"
        else:
            comparacion = f"compite estrechamente con {segunda_cat}"
        
        # Análisis de top 2 categorías
        top2_concentration = pct_top + pct_segunda
        if top2_concentration >= 80:
            duopolio = f"**Duopolio detectado:** Las top 2 categorías concentran {top2_concentration:.1f}% de las ventas."
        else:
            duopolio = f"**Distribución:** Top 2 categorías representan {top2_concentration:.1f}% del negocio."
    else:
        segunda_cat = None
        comparacion = "es la única categoría con ventas"
        duopolio = "**Monopolio total:** Una sola categoría genera todos los ingresos."
    
    # Recomendaciones estratégicas específicas
    if urgencia == "CRÍTICO":
        recomendacion = f"🚨 **ACCIÓN INMEDIATA:** Diversificar urgentemente. La dependencia del {pct_top:.1f}% en {top_cat} es un riesgo comercial extremo."
    elif urgencia == "ALTO":
        recomendacion = f"⚠️ **PRIORIDAD ALTA:** Desarrollar categorías alternativas. Reducir dependencia de {top_cat}."
    elif urgencia == "MEDIO" and concentracion == "alta":
        recomendacion = f"📈 **OPORTUNIDAD:** {top_cat} es un motor sólido. Optimizar su rentabilidad."
    elif urgencia == "BUENO":
        recomendacion = f"✅ **FORTALEZA:** Excelente equilibrio. {top_cat} lidera sin crear riesgo excesivo."
    else:
        recomendacion = f"🎯 **ESTRATEGIA:** Evaluar si consolidar liderazgo en {top_cat} o buscar mayor equilibrio."
    
    # Construir insight completo
    insight_text = f"{emoji} **Análisis de Concentración de Ventas ({urgencia})**\n\n"
    insight_text += f"**{top_cat}** domina con **{val_fmt}** (**{pct_top:.1f}%** del total) y {comparacion}.\n\n"
    
    insight_text += f"📊 **Análisis Pareto:**\n"
    insight_text += f"• Tipo de concentración: {analisis_pareto}\n"
    insight_text += f"• Nivel de riesgo: {urgencia}\n"
    insight_text += f"• {duopolio}\n"
    
    if segunda_cat:
        insight_text += f"• Segunda categoría: {segunda_cat} con {val_segunda_fmt} ({pct_segunda:.1f}%)\n"
    
    insight_text += f"\n{recomendacion}"
    
    return insight_text


def generar_insight_margen(margenes):
    """Genera insights sobre la distribución de márgenes por categoría"""
    
    if margenes.empty or margenes.sum() == 0:
        return "🚫 **Sin datos disponibles:** No se encontraron datos de margen para analizar."
    
    mejor_cat = margenes.idxmax()
    mejor_margen = margenes.max()
    margen_promedio = margenes.mean()
    
    # Análisis de rentabilidad
    if mejor_margen >= 40:
        rentabilidad = "excelente"
        emoji = "💎"
    elif mejor_margen >= 30:
        rentabilidad = "muy buena"
        emoji = "📈"
    elif mejor_margen >= 20:
        rentabilidad = "aceptable"
        emoji = "📊"
    elif mejor_margen >= 10:
        rentabilidad = "baja"
        emoji = "⚠️"
    else:
        rentabilidad = "crítica"
        emoji = "🚨"
    
    # Dispersión de márgenes
    if len(margenes) > 1:
        std_margenes = margenes.std()
        if std_margenes >= 15:
            variabilidad = "alta variabilidad entre categorías - oportunidad de optimización"
        elif std_margenes >= 8:
            variabilidad = "variabilidad moderada - gestión diferenciada recomendada"
        else:
            variabilidad = "márgenes consistentes entre categorías"
    else:
        variabilidad = "única categoría disponible"
    
    insight_text = f"{emoji} **Análisis de Rentabilidad por Categoría**\n\n"
    insight_text += f"**{mejor_cat}** lidera en rentabilidad con **{mejor_margen:.1f}%** de margen (rentabilidad {rentabilidad}).\n\n"
    insight_text += f"📈 **Características:**\n"
    insight_text += f"• Margen promedio general: {margen_promedio:.1f}%\n"
    insight_text += f"• Dispersión: {variabilidad}\n\n"
    insight_text += f"💡 **Recomendación:** {'Maximizar volumen en ' + mejor_cat if mejor_margen >= 25 else 'Revisar estrategia de precios en ' + mejor_cat}"
    
    return insight_text


def generar_insight_abc_completo(abc_counts, abc_ventas):
    """Genera un insight integral combinando cantidad y ventas del análisis ABC"""
    
    if abc_counts.empty or abc_ventas.empty:
        return "🚫 **Sin datos disponibles:** No se puede realizar análisis ABC completo."
    
    # Productos A
    productos_a = abc_counts.get('A (Alto valor)', 0)
    ventas_a = abc_ventas.get('A (Alto valor)', 0)
    pct_ventas_a = (ventas_a / abc_ventas.sum() * 100) if abc_ventas.sum() > 0 else 0
    
    # Eficiencia de productos A
    total_productos = abc_counts.sum()
    pct_productos_a = (productos_a / total_productos * 100) if total_productos > 0 else 0
    
    # Ratio de eficiencia (% ventas / % productos)
    eficiencia_ratio = (pct_ventas_a / pct_productos_a) if pct_productos_a > 0 else 0
    
    # Análisis de eficiencia
    if eficiencia_ratio >= 4:
        eficiencia = "excepcional"
        emoji = "🏆"
    elif eficiencia_ratio >= 3:
        eficiencia = "excelente"
        emoji = "💎"
    elif eficiencia_ratio >= 2:
        eficiencia = "buena"
        emoji = "📈"
    else:
        eficiencia = "mejorable"
        emoji = "⚠️"
    
    # Productos B y C
    productos_bc = abc_counts.get('B (Valor medio)', 0) + abc_counts.get('C (Bajo valor)', 0)
    ventas_bc = abc_ventas.get('B (Valor medio)', 0) + abc_ventas.get('C (Bajo valor)', 0)
    pct_ventas_bc = (ventas_bc / abc_ventas.sum() * 100) if abc_ventas.sum() > 0 else 0
    
    # Recomendaciones específicas
    if pct_productos_a <= 15 and pct_ventas_a >= 70:
        estrategia = "**Estrategia ideal:** Pocos productos de alto impacto. Maximizar disponibilidad y promoción de productos A."
    elif pct_productos_a >= 30:
        estrategia = f"**Oportunidad:** Demasiados productos A ({productos_a}). Evaluar cuáles realmente generan valor."
    elif pct_ventas_a <= 50:
        estrategia = "**Alerta:** Productos A no están generando el impacto esperado. Revisar estrategia comercial."
    else:
        estrategia = "**Equilibrio adecuado:** Los productos A están cumpliendo su función estratégica."
    
    insight_text = f"{emoji} **Análisis ABC Integral - Eficiencia {eficiencia.capitalize()}**\n\n"
    insight_text += f"**Productos Clase A:** {productos_a} productos ({pct_productos_a:.1f}%) generan **{pct_ventas_a:.1f}%** de las ventas.\n"
    insight_text += f"**Ratio de eficiencia:** {eficiencia_ratio:.1f}x (cada producto A equivale a {eficiencia_ratio:.1f} productos promedio)\n\n"
    
    insight_text += f"📊 **Distribución completa:**\n"
    insight_text += f"• Productos A: {productos_a} unidades - ${abc_ventas.get('A (Alto valor)', 0):,.0f}\n"
    insight_text += f"• Productos B+C: {productos_bc} unidades - ${ventas_bc:,.0f} ({pct_ventas_bc:.1f}%)\n\n"
    
    insight_text += f"{estrategia}\n\n"
    insight_text += f"💡 **Foco recomendado:** {'Potenciar productos A' if eficiencia_ratio >= 2.5 else 'Revisar clasificación y optimizar productos B/C'}"
    
    return insight_text