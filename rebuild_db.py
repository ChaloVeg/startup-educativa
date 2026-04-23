from database import engine, Base
# Importamos todos los modelos para que SQLAlchemy sepa qué tablas crear
from database import (
    Alumno, Curso, Medico, Profesor, Especialista, Diagnostico, 
    NecesidadEducativa, FichaAlumno, Progreso, TestEvaluacion, 
    Sesion, Interaccion, CatalogoAcciones, AccionAsignada, 
    ConfiguracionProfesor, UsuarioWeb
)

def resetear_base_de_datos():
    print("🌐 Conectando a la base de datos (PostgreSQL/Neon.tech o Local)...")
    
    print("🗑️  Eliminando todas las tablas antiguas...")
    Base.metadata.drop_all(bind=engine)
    
    print("✨ Creando las tablas con la nueva estructura...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ ¡Base de datos reconstruida exitosamente!")

if __name__ == "__main__":
    resetear_base_de_datos()