import pytest
from unittest.mock import MagicMock
from engine import MotorAdaptativo

# --- FIXTURES Y UTILIDADES ---

@pytest.fixture
def motor():
    """Proporciona una instancia limpia del MotorAdaptativo para cada prueba."""
    return MotorAdaptativo()

def crear_db_mock(puntuacion_ecep=None):
    """
    Utilidad para simular (mockear) la sesión de SQLAlchemy.
    Evita conectarse a la BD real y permite inyectar resultados falsos
    en la consulta del test ECEP.
    """
    mock_db = MagicMock()
    
    # Simulamos la cadena: db.query(...).filter(...).order_by(...).first()
    mock_query = mock_db.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_order_by = mock_filter.order_by.return_value
    
    if puntuacion_ecep is not None:
        mock_evaluacion = MagicMock()
        mock_evaluacion.puntuacion = puntuacion_ecep
        mock_order_by.first.return_value = mock_evaluacion
    else:
        mock_order_by.first.return_value = None
        
    return mock_db

# --- PRUEBAS UNITARIAS ---

def test_rendimiento_estable_sin_antecedentes(motor):
    db_mock = crear_db_mock(puntuacion_ecep=None)
    resultado = motor.evaluar(db_mock, alumno_id=1, nivel_actual=2, errores=1, tiempo_reaccion=3.0)
    
    assert resultado["siguiente_nivel"] == 2
    assert resultado["recomendacion_estimulo"] == "visual"
    assert "Ritmo estable" in resultado["mensaje"]

def test_frustracion_por_exceso_errores(motor):
    db_mock = crear_db_mock() # Sin antecedentes por defecto
    resultado = motor.evaluar(db_mock, alumno_id=1, nivel_actual=3, errores=4, tiempo_reaccion=2.5)
    
    assert resultado["siguiente_nivel"] == 2 # Debe bajar un nivel
    assert resultado["recomendacion_estimulo"] == "auditivo" # Debe cambiar el estímulo
    assert "Frustración detectada" in resultado["mensaje"]

def test_frustracion_no_baja_del_nivel_uno(motor):
    db_mock = crear_db_mock()
    resultado = motor.evaluar(db_mock, alumno_id=1, nivel_actual=1, errores=0, tiempo_reaccion=6.0) # Tiempo excesivo
    
    assert resultado["siguiente_nivel"] == 1 # No debe ser 0 ni negativo
    assert resultado["recomendacion_estimulo"] == "auditivo"

def test_rendimiento_excelente_avanza_nivel(motor):
    db_mock = crear_db_mock()
    resultado = motor.evaluar(db_mock, alumno_id=1, nivel_actual=2, errores=0, tiempo_reaccion=1.5)
    
    assert resultado["siguiente_nivel"] == 3 # Debe subir de nivel
    assert resultado["recomendacion_estimulo"] == "visual"
    assert "Aumentando la complejidad cognitiva" in resultado["mensaje"]

def test_antecedente_ecep_bajo_ajusta_estimulo_preventivamente(motor):
    db_mock = crear_db_mock(puntuacion_ecep=35.0) # Puntuación por debajo del umbral (40)
    resultado = motor.evaluar(db_mock, alumno_id=1, nivel_actual=1, errores=1, tiempo_reaccion=3.0)
    
    assert resultado["recomendacion_estimulo"] == "visual_simplificado"
    assert "Antecedente ECEP detectado" in resultado["mensaje"]

def test_antecedente_ecep_rendimiento_excelente_mantiene_apoyo(motor):
    db_mock = crear_db_mock(puntuacion_ecep=30.0)
    resultado = motor.evaluar(db_mock, alumno_id=1, nivel_actual=2, errores=0, tiempo_reaccion=1.0)
    
    assert resultado["siguiente_nivel"] == 3 # Avanza de nivel por hacerlo excelente
    assert resultado["recomendacion_estimulo"] == "visual_simplificado" # Pero no pierde el apoyo preventivo
    assert "manteniendo apoyo simplificado" in resultado["mensaje"]