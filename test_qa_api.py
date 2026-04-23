import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app, get_db
from database import Base, Alumno, Curso

# 1. Configurar una base de datos independiente solo para pruebas (QA)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_qa.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Sobrescribir la dependencia de la BD de FastAPI para que use nuestra BD de pruebas
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# 3. Fixture de preparación (Setup & Teardown)
@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # Crea las tablas limpias antes de empezar
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Insertar un "Alumno QA" falso para poder probar los endpoints
    curso_qa = Curso(nivel="QA Testing")
    db.add(curso_qa)
    db.commit()
    db.refresh(curso_qa)
    
    alumno_qa = Alumno(rut="99999999-QA", nombres="Bot", apellidos="QA", curso_id=curso_qa.id)
    db.add(alumno_qa)
    db.commit()
    
    yield # Aquí se ejecutan todas las pruebas...
    
    # Limpiar y destruir la base de datos de prueba al terminar
    Base.metadata.drop_all(bind=engine)
    db.close()

# --- BATERÍA DE PRUEBAS QA ---

def test_qa_check_in_emocional():
    """Valida que el pilar de emoción responda correctamente a un estado de ansiedad."""
    response = client.post("/check-in/", json={"alumno_id": 1, "estado_emocional_inicio": "Ansioso"})
    assert response.status_code == 200
    data = response.json()
    assert "sesion_id" in data
    assert data["global_speed_modifier"] == 0.6  # Debe reducir la velocidad
    assert data["color_palette"] == "baja_estimulacion"

def test_qa_registrar_progreso():
    """Valida que el motor IA suba de nivel si el alumno lo hace perfecto."""
    response = client.post("/progreso/", json={"alumno_id": 1, "nivel_alcanzado": 2, "tiempo_reaccion": 1.5, "errores_cometidos": 0})
    assert response.status_code == 200
    assert response.json()["siguiente_nivel"] == 3

def test_qa_registrar_telemetria():
    """Valida la detección de sobrecarga cognitiva por alta latencia."""
    response = client.post("/telemetry/", json={"sesion_id": 1, "tipo_evento": "clic", "latencia_ms": 6000.0, "es_error": 0})
    assert response.status_code == 200
    assert response.json()["reduce_speed"] == True  # 6000ms > 5000ms, debe reducir velocidad

def test_qa_finalizar_sesion_y_analiticas():
    """Cierra la sesión de prueba y comprueba que se calculen las analíticas docentes."""
    res_end = client.post("/session-end/", json={"sesion_id": 1, "estado_emocional_final": "Tranquilo"})
    assert res_end.status_code == 200
    
    res_analytics = client.get("/teacher/analytics/1")
    assert res_analytics.status_code == 200