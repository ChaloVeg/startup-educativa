from pydantic import BaseModel
from typing import Optional

# Esquemas base para validar las peticiones que entran y salen de la API

class ProgresoBase(BaseModel):
    nivel_alcanzado: int
    tiempo_reaccion: float
    errores_cometidos: int

class ProgresoCreate(ProgresoBase):
    alumno_id: int

class AdaptacionResponse(BaseModel):
    """Contrato de respuesta del Motor Adaptativo"""
    siguiente_nivel: int
    recomendacion_estimulo: str
    mensaje: str

class CheckInCreate(BaseModel):
    alumno_id: int
    estado_emocional_inicio: str

class CheckInResponse(BaseModel):
    sesion_id: int
    mensaje: str
    global_speed_modifier: float
    color_palette: str

class SessionEndCreate(BaseModel):
    sesion_id: int
    estado_emocional_final: str

class TelemetryCreate(BaseModel):
    sesion_id: int
    tipo_evento: str
    latencia_ms: float
    es_error: int
    tipo_de_ayuda_brindada: Optional[str] = None

class AdaptiveAdjustments(BaseModel):
    """Configuración que se retorna en tiempo real a la interfaz educativa"""
    reduce_speed: bool
    high_contrast: bool
    audio_hint: bool
    simplificar_interfaz: bool # Pilar 2: Reduce distractores
    mensaje_sistema: str