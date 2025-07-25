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


def generar_insight_margen(margenes, categoria):
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
            dispersion = f"Alta variabilidad entre {categoria} - oportunidad de optimización"
        elif std >= 8:
            dispersion = "Variabilidad moderada - gestión diferenciada recomendada"
        else:
            dispersion = f"Márgenes consistentes entre {categoria}"
    else:
        dispersion = f"Única {categoria} disponible"

    html = f"""
    <div class="insight-box">
        <div class="insight-titulo">{emoji} <strong>Análisis de Rentabilidad por {categoria}</strong></div>
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

def generar_insight_pareto(productos_pareto):
    if productos_pareto.empty:
        return '<div class="warning-box">🚫 <strong>Sin datos:</strong> No se encontraron productos para análisis de Pareto.</div>'

    top1 = productos_pareto.iloc[0]
    top3_pct = productos_pareto['Participación %'].head(3).sum()
    top5_pct = productos_pareto['Participación %'].head(5).sum()
    top10_pct = productos_pareto['Participación %'].head(10).sum()

    if top1["Participación %"] >= 50:
        riesgo = "🔴 Extremadamente concentrado"
        recomendacion = f"🚨 <strong>Alerta:</strong> <strong>{top1['descripcion']}</strong> representa más del 50% de participación individual. Urge diversificar."
    elif top3_pct >= 80:
        riesgo = "🟠 Muy concentrado (Top 3 > 80%)"
        recomendacion = "⚠️ <strong>Revisión necesaria:</strong> Los 3 principales productos concentran demasiado. Analizar estrategias de diversificación."
    elif top10_pct >= 80:
        riesgo = "📊 Concentración media (Top 10 > 80%)"
        recomendacion = "📈 <strong>Oportunidad:</strong> Buena segmentación, pero todavía dependiente del top 10. Potenciar el middle tail."
    else:
        riesgo = "✅ Buena distribución"
        recomendacion = "🎯 <strong>Fortaleza:</strong> Portafolio bien distribuido. Mantener estrategia actual y explorar productos emergentes."

    html = f"""
    <div class="insight-box">
        <div class="insight-titulo">📊 <strong>Insight de Concentración de Ventas - Análisis de Pareto</strong></div>
        <p><strong>Producto líder:</strong> {top1['descripcion']} con <strong>{top1['Participación %']:.1f}%</strong> de participación individual.</p>
        <p><strong>Participación Acumulada:</strong></p>
        <ul>
            <li><strong>Top 3 productos:</strong> {top3_pct:.1f}%</li>
            <li><strong>Top 5 productos:</strong> {top5_pct:.1f}%</li>
            <li><strong>Top 10 productos:</strong> {top10_pct:.1f}%</li>
        </ul>
        <p><strong>Nivel de concentración:</strong> {riesgo}</p>
        <p>{recomendacion}</p>
    </div>
    """
    return html
