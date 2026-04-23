import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float, Boolean, Enum
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timezone
import enum

# Leemos la URL desde la nube. Si no existe (como en tu PC), usa SQLite local por defecto.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./neuroforge.db")

# Configuramos el motor de base de datos dependiendo de si es SQLite o PostgreSQL
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Corrección para compatibilidad de URLs de PostgreSQL modernas
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Para la nube (Neon.tech), agregamos pre_ping para evitar caídas por inactividad
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, pool_recycle=300)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- NUEVOS MODELOS DOMINIO PIE ---

class CategoriaDiagnostico(enum.Enum):
    PERMANENTE = "Permanente"
    TRANSITORIO = "Transitorio"

class EspecialidadMedico(enum.Enum):
    FAMILIA = "Medico Familia"
    NEUROLOGO = "Neurologo"
    PSIQUIATRA = "Psiquiatra"

class TipoEspecialista(enum.Enum):
    PSICOLOGO = "Psicólogo(a)"
    FONOAUDIOLOGO = "Fonoaudiólogo(a)"
    TERAPEUTA_OCUPACIONAL = "Terapeuta ocupacional"

class Curso(Base):
    __tablename__ = "cursos"
    id = Column(Integer, primary_key=True, index=True)
    nivel = Column(String, index=True)

class Alumno(Base):
    __tablename__ = "alumnos"
    id = Column(Integer, primary_key=True, index=True)
    rut = Column(String, unique=True, index=True)
    nombres = Column(String)
    apellidos = Column(String)
    curso_id = Column(Integer, ForeignKey("cursos.id"))
    # NOTA: profesor_asignado podría seguir existiendo si se vincula la entidad Profesor, 
    # pero bajo el nuevo modelo dependerá de la Ficha o asignaciones.

class FichaAlumno(Base):
    __tablename__ = "fichas_alumnos"
    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"), unique=True)
    rut = Column(String)
    nombre_social = Column(String)
    fecha_evaluaciones = Column(DateTime)
    profesor_id = Column(Integer, ForeignKey("profesores.id"), nullable=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=True)
    especialista_id = Column(Integer, ForeignKey("especialistas.id"), nullable=True)
    alergias_condiciones = Column(String, nullable=True)

class Medico(Base):
    __tablename__ = "medicos"
    id = Column(Integer, primary_key=True, index=True)
    rut = Column(String, unique=True, index=True)
    nombre = Column(String)
    especialidad = Column(Enum(EspecialidadMedico))

class Profesor(Base):
    __tablename__ = "profesores"
    id = Column(Integer, primary_key=True, index=True)
    rut = Column(String, unique=True, index=True)
    nombres = Column(String)
    apellidos = Column(String)
    registro = Column(String)

class Especialista(Base):
    __tablename__ = "especialistas"
    id = Column(Integer, primary_key=True, index=True)
    rut = Column(String, unique=True, index=True)
    nombres = Column(String)
    apellidos = Column(String)
    registro = Column(String)
    tipo = Column(Enum(TipoEspecialista))

class Diagnostico(Base):
    __tablename__ = "diagnosticos"
    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(Enum(CategoriaDiagnostico))
    tipo = Column(String) # Ej: "tea", "tdah", etc.

class NecesidadEducativa(Base):
    __tablename__ = "necesidades_educativas"
    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"))
    diagnostico_id = Column(Integer, ForeignKey("diagnosticos.id"))

# --- ACTUALIZACIÓN DE MODELOS EXISTENTES ---

class Progreso(Base):
    __tablename__ = "progreso"
    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"))
    nivel_alcanzado = Column(Integer)
    tiempo_reaccion = Column(Float) # Segundos que tardó en responder
    errores_cometidos = Column(Integer)
    fecha_sesion = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class TestEvaluacion(Base):
    __tablename__ = "evaluaciones"
    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"))
    tipo_test = Column(String) # ej. ECEP, Conners, WISC, etc.
    puntuacion = Column(Float)
    observaciones = Column(String)
    fecha_evaluacion = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class Sesion(Base):
    __tablename__ = "sesiones"
    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"))
    estado_emocional_inicio = Column(String) # Ej: Feliz, Ansioso, Cansado
    estado_emocional_final = Column(String, nullable=True) # Pilar 1: Cierre emocional
    nivel_frustracion_detectado = Column(Float, default=0.0)
    indice_autonomia = Column(Float, default=1.0)
    fecha_inicio = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class Interaccion(Base):
    __tablename__ = "interacciones"
    id = Column(Integer, primary_key=True, index=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    tipo_evento = Column(String) # "clic", "arrastre"
    latencia_ms = Column(Float)
    es_error = Column(Integer, default=0) # 1 si fue error, 0 si acierto
    tipo_de_ayuda_brindada = Column(String, nullable=True)

class CatalogoAcciones(Base):
    __tablename__ = "catalogo_acciones"
    id = Column(Integer, primary_key=True, index=True)
    nombre_accion = Column(String, unique=True, index=True)
    descripcion = Column(String)
    categoria = Column(String) # Emoción, Adaptabilidad o Autonomía
    es_personalizada = Column(Boolean, default=False)

class AccionAsignada(Base):
    __tablename__ = "acciones_asignadas"
    id = Column(Integer, primary_key=True, index=True)
    alumno_id = Column(Integer, ForeignKey("alumnos.id"))
    accion_id = Column(Integer, ForeignKey("catalogo_acciones.id"))
    fecha_asignacion = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    fecha_vencimiento = Column(DateTime, nullable=True) # Para alertas de vencimiento
    estado = Column(String, default="Pendiente")

class ConfiguracionProfesor(Base):
    __tablename__ = "configuracion_profesores"
    id = Column(Integer, primary_key=True, index=True)
    nombre_profesor = Column(String, unique=True, index=True)
    ver_alumnos = Column(Boolean, default=True) # Por defecto, pueden ver sus alumnos
    ver_tareas = Column(Boolean, default=True)  # Por defecto, pueden ver sus tareas

class UsuarioWeb(Base):
    __tablename__ = "usuarios_web"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, nullable=True)
    password = Column(String)
    rol = Column(String) # "Admin" o "Profesor"
    must_change_password = Column(Boolean, default=False)
    account_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

# NOTA: No ejecutamos Base.metadata.create_all() aquí.
# Se ejecutará de forma segura directamente desde dashboard.py para evitar ImportErrors.