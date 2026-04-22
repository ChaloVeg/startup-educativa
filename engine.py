from sqlalchemy.orm import Session
from database import TestEvaluacion, Interaccion

class MotorAdaptativo:
    """
    Motor de Inteligencia Adaptativa.
    Aislado aquí para cumplir con los principios SOLID (Open/Closed Principle).
    """
    
    UMBRAL_ECEP_BAJO = 40.0 # Puntuación por debajo de la cual se necesita apoyo extra

    def evaluar(self, db: Session, nino_id: int, nivel_actual: int, errores: int, tiempo_reaccion: float) -> dict:
        siguiente_nivel = nivel_actual
        estimulo = "visual"
        mensaje = "Ritmo estable. Manteniendo parámetros."

        # 1. Verificar si el niño tiene un test ECEP con baja puntuación
        evaluacion_ecep = db.query(TestEvaluacion).filter(
            TestEvaluacion.nino_id == nino_id,
            TestEvaluacion.tipo_test.like("%ECEP%")
        ).order_by(TestEvaluacion.fecha_evaluacion.desc()).first()

        if evaluacion_ecep and evaluacion_ecep.puntuacion < self.UMBRAL_ECEP_BAJO:
            estimulo = "visual_simplificado"
            mensaje = f"Antecedente ECEP detectado ({evaluacion_ecep.puntuacion} pts). Ajustando a estímulo simplificado por defecto."

        # Lógica heurística de adaptación
        if errores >= 3 or tiempo_reaccion > 5.0:
            siguiente_nivel = max(1, nivel_actual - 1) # No bajar de nivel 1
            estimulo = "auditivo"
            mensaje = "Frustración detectada: Dificultad reducida y cambio a apoyo auditivo."
        elif errores == 0 and tiempo_reaccion < 2.0:
            siguiente_nivel += 1
            if estimulo != "visual_simplificado":
                mensaje = "¡Rendimiento excelente! Aumentando la complejidad cognitiva."
            else:
                mensaje = "¡Rendimiento excelente! Aumentando nivel, manteniendo apoyo simplificado."

        return {
            "siguiente_nivel": siguiente_nivel,
            "recomendacion_estimulo": estimulo,
            "mensaje": mensaje
        }

class MotorInteligenciaEmocional:
    """
    Pilar 1: Emoción. Ajusta el entorno base del juego según el estado inicial.
    Intención pedagógica: Prevenir la sobrecarga sensorial si hay ansiedad, o aprovechar la energía si hay felicidad.
    """
    def procesar_checkin(self, estado: str) -> dict:
        estado = estado.lower()
        if estado == 'ansioso':
            return {"global_speed_modifier": 0.6, "color_palette": "baja_estimulacion"}
        elif estado == 'feliz':
            return {"global_speed_modifier": 1.2, "color_palette": "vibrante_ritmico"}
        
        return {"global_speed_modifier": 1.0, "color_palette": "neutra"}

class AdaptiveEngine:
    """
    Motor Central de Adaptabilidad (NeuroForge V2).
    Analiza telemetría granular (clics, latencia) para aplicar el pilar de Adaptabilidad en tiempo real.
    """
    
    def analizar_telemetria(self, db: Session, sesion_id: int) -> dict:
        # Obtener los últimos 5 eventos de la sesión (Ventana móvil)
        ultimos_eventos = db.query(Interaccion).filter(
            Interaccion.sesion_id == sesion_id
        ).order_by(Interaccion.timestamp.desc()).limit(5).all()

        # Ajustes por defecto
        ajustes = {
            "reduce_speed": False,
            "high_contrast": False,
            "audio_hint": False,
            "mensaje_sistema": "Autonomía mantenida. Parámetros óptimos."
        }

        if not ultimos_eventos:
            return ajustes

        errores = sum(1 for e in ultimos_eventos if e.es_error == 1)
        latencia_promedio = sum(e.latencia_ms for e in ultimos_eventos) / len(ultimos_eventos)

        # Evaluación Pilar 2: Ajuste por racha de errores
        ajuste_dificultad = self.ajustar_dificultad(db, sesion_id)
        ajustes["simplificar_interfaz"] = ajuste_dificultad["simplificar_interfaz"]
        if ajustes["simplificar_interfaz"]:
            ajustes["mensaje_sistema"] = ajuste_dificultad["mensaje"]
            return ajustes # Prioridad máxima: simplificar la vista si hay frustración

        # Intervención estándar basada en latencia y errores aislados
        if latencia_promedio > 5000.0:
            ajustes["reduce_speed"] = True
            ajustes["mensaje_sistema"] = "Alta carga cognitiva detectada (Latencia > 5s). Reduciendo velocidad del entorno."
        elif errores >= 3:
            ajustes["high_contrast"] = True
            ajustes["audio_hint"] = True
            ajustes["mensaje_sistema"] = "Activando alto contraste y pistas de audio."

        return ajustes

    def ajustar_dificultad(self, db: Session, sesion_id: int) -> dict:
        """
        Analiza específicamente si el niño ha cometido 3 errores consecutivos.
        Intención pedagógica: Evitar el abandono escolar o bloqueo (Learned Helplessness).
        """
        ultimos_3 = db.query(Interaccion).filter(Interaccion.sesion_id == sesion_id).order_by(Interaccion.timestamp.desc()).limit(3).all()
        errores_seguidos = sum(1 for e in ultimos_3 if e.es_error == 1)
        
        if errores_seguidos >= 3 and len(ultimos_3) == 3:
            return self.simplificar_interfaz()
        return {"simplificar_interfaz": False, "mensaje": "Dificultad óptima"}

    def simplificar_interfaz(self) -> dict:
        """Oculta elementos secundarios del juego para concentrar la atención."""
        return {"simplificar_interfaz": True, "mensaje": "Sobrecarga de frustración. Interfaz simplificada (distractores ocultos)."}

    def calcular_autonomia(self, db: Session, sesion_id: int) -> float:
        """Pilar 3: Autonomía. Se calcula al final de la sesión: (Aciertos / (Aciertos + Pistas)) * 100"""
        interacciones = db.query(Interaccion).filter(Interaccion.sesion_id == sesion_id).all()
        aciertos = sum(1 for i in interacciones if i.es_error == 0)
        # Se cuenta como "Pista/Ayuda" si hubo intervención directa o inactividad > 7s
        pistas = sum(1 for i in interacciones if i.tipo_de_ayuda_brindada is not None or i.latencia_ms > 7000.0)
        
        return round((aciertos / (aciertos + pistas)) * 100, 2) if (aciertos + pistas) > 0 else 100.0