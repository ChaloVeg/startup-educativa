from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, UsuarioNiño, Progreso, Sesion, Interaccion
import schemas
from engine import MotorAdaptativo, AdaptiveEngine, MotorInteligenciaEmocional

app = FastAPI(title="NeuroForge API", version="1.0")
motor_ia = MotorAdaptativo()
adaptive_engine = AdaptiveEngine()
motor_emocional = MotorInteligenciaEmocional()

# Dependencia para la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/progreso/", response_model=schemas.AdaptacionResponse)
def registrar_progreso(progreso: schemas.ProgresoCreate, db: Session = Depends(get_db)):
    """
    Endpoint principal que registra telemetría y devuelve la adaptación inmediata.
    """
    # 1. Guardar telemetría
    db_progreso = Progreso(
        nino_id=progreso.nino_id,
        nivel_alcanzado=progreso.nivel_alcanzado,
        tiempo_reaccion=progreso.tiempo_reaccion,
        errores_cometidos=progreso.errores_cometidos
    )
    db.add(db_progreso)
    db.commit()

    # 2. Consultar al Motor Adaptativo
    evaluacion = motor_ia.evaluar(
        db=db,
        nino_id=progreso.nino_id,
        nivel_actual=progreso.nivel_alcanzado,
        errores=progreso.errores_cometidos,
        tiempo_reaccion=progreso.tiempo_reaccion
    )
    return evaluacion

@app.post("/check-in/", response_model=schemas.CheckInResponse)
def check_in_emocional(data: schemas.CheckInCreate, db: Session = Depends(get_db)):
    """Pilar de Emoción: Registra el estado inicial del niño antes de la sesión."""
    try:
        nueva_sesion = Sesion(
            nino_id=data.nino_id,
            estado_emocional_inicio=data.estado_emocional_inicio
        )
        db.add(nueva_sesion)
        db.commit()
        db.refresh(nueva_sesion)
        
        # Computar ajustes iniciales según la emoción
        ajustes = motor_emocional.procesar_checkin(data.estado_emocional_inicio)
        
        return {
            "sesion_id": nueva_sesion.id, 
            "mensaje": "Check-in emocional registrado.",
            **ajustes
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en el registro: {str(e)}")

@app.post("/telemetry/", response_model=schemas.AdaptiveAdjustments)
def registrar_interaccion(telemetria: schemas.TelemetryCreate, db: Session = Depends(get_db)):
    """Pilar de Adaptabilidad: Recibe cada acción del juego y retorna ajustes en JSON."""
    try:
        # 1. Guardar el evento granular
        nueva_interaccion = Interaccion(
            sesion_id=telemetria.sesion_id,
            tipo_evento=telemetria.tipo_evento,
            latencia_ms=telemetria.latencia_ms,
            es_error=telemetria.es_error,
            tipo_de_ayuda_brindada=telemetria.tipo_de_ayuda_brindada
        )
        db.add(nueva_interaccion)
        db.commit()

        # 2. Consultar al Motor de Adaptabilidad (Ventana de 5 eventos)
        ajustes = adaptive_engine.analizar_telemetria(db, telemetria.sesion_id)
        return ajustes
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Fallo en el motor adaptativo: {str(e)}")

@app.post("/session-end/")
def finalizar_sesion(data: schemas.SessionEndCreate, db: Session = Depends(get_db)):
    """Cierra la sesión y calcula el Índice de Autonomía final."""
    sesion = db.query(Sesion).filter(Sesion.id == data.sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")
        
    try:
        sesion.estado_emocional_final = data.estado_emocional_final
        # Calcular y guardar el Índice de Autonomía (Pilar 3)
        sesion.indice_autonomia = adaptive_engine.calcular_autonomia(db, sesion.id)
        
        db.commit()
        return {"mensaje": "Sesión finalizada", "indice_autonomia_logrado": sesion.indice_autonomia}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error cerrando la sesión: {str(e)}")

@app.get("/teacher/analytics/{nino_id}")
def obtener_analiticas_profesor(nino_id: int, db: Session = Depends(get_db)):
    """Pilar de Autonomía: Devuelve un resumen gerencial comparando avance actual vs histórico."""
    try:
        sesiones = db.query(Sesion).filter(Sesion.nino_id == nino_id).all()
        if not sesiones:
            raise HTTPException(status_code=404, detail="No hay datos de sesiones para este alumno.")
        
        # Simulación de agregación profunda de Autonomía
        autonomia_historica = sum(s.indice_autonomia for s in sesiones) / len(sesiones)
        
        return {
            "nino_id": nino_id,
            "total_sesiones": len(sesiones),
            "indice_autonomia_historico": round(autonomia_historica, 2),
            "estado_emocional_frecuente": sesiones[-1].estado_emocional_inicio if sesiones else "N/A",
            "tendencia_carga_cognitiva": "Estable" # Reemplazable por cálculos algorítmicos complejos
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar analíticas: {str(e)}")