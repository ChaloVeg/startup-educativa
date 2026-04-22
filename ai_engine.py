class NeuroForgeAI:
    """
    Sistema Experto Basado en Reglas Locales (Sustituye al LLM externo).
    Analiza métricas y devuelve insights predeterminados, garantizando 
    privacidad total y cero costos de API.
    """
    def __init__(self):
        # Ya no necesitamos configurar claves de API.
        pass

    def generar_insight_pedagogico(self, datos_alumno):
        historial = datos_alumno.get("historial_progreso", [])
        
        if not historial:
            return "No hay suficientes datos registrados para generar un análisis pedagógico."

        # Analizar los últimos 3 registros para ver la tendencia reciente
        ultimos_registros = historial[-3:]
        
        # Parseamos los valores (llegan como strings desde el Dashboard)
        errores_recientes = sum(int(float(r.get('errores_cometidos', 0))) for r in ultimos_registros)
        tiempo_promedio = sum(float(r.get('tiempo_reaccion', 0)) for r in ultimos_registros) / len(ultimos_registros)
        
        # --- REGLAS ESTÁTICAS DE EVALUACIÓN ---
        if errores_recientes >= 6:
            resumen = "El alumno presenta una tasa de error inusualmente alta en las últimas sesiones, indicando posible frustración o sobrecarga cognitiva."
            recomendacion = "Recomendación: Asignar 'Simplificación de Interfaz' y reducir temporalmente la velocidad del juego."
        elif tiempo_promedio >= 4.0:
            resumen = "Se observa una latencia prolongada en las respuestas, lo que sugiere fatiga o necesidad de estímulos más claros."
            recomendacion = "Recomendación: Asignar 'Aumento de Contraste' o 'Pista de Audio' para facilitar la resolución de tareas."
        elif errores_recientes <= 1 and tiempo_promedio < 2.5:
            resumen = "El alumno domina los objetivos actuales demostrando excelente precisión y tiempos de reacción muy rápidos."
            recomendacion = "Recomendación: Aumentar la complejidad de los retos para mantener el 'engagement' y evitar el aburrimiento."
        else:
            resumen = "El progreso y ritmo del alumno se mantienen estables dentro de los parámetros esperados de su curva de aprendizaje."
            recomendacion = "Recomendación: Mantener la configuración y estímulos actuales de la sesión."

        return f"**Resumen Ejecutivo:**\n{resumen}\n\n**Plan de Acción Técnico:**\n{recomendacion}"