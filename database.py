import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# Leemos la URL desde la nube. Si no existe (como en tu PC), usa SQLite local por defecto.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./neuroforge.db")

# Configuramos el motor de base de datos dependiendo de si es SQLite o PostgreSQL
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Corrección para compatibilidad de URLs de PostgreSQL modernas
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # PostgreSQL no necesita el parámetro "check_same_thread"
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UsuarioNiño(Base):
    __tablename__ = "ninos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    perfil_diagnostico = Column(String) # TEA, TDAH, etc.
    curso = Column(String, default="No asignado")
    profesor_asignado = Column(String, default="Sin asignar")

class Progreso(Base):
    __tablename__ = "progreso"
    id = Column(Integer, primary_key=True, index=True)
    nino_id = Column(Integer, ForeignKey("ninos.id"))
    nivel_alcanzado = Column(Integer)
    tiempo_reaccion = Column(Float) # Segundos que tardó en responder
    errores_cometidos = Column(Integer)
    fecha_sesion = Column(DateTime, default=datetime.datetime.utcnow)

class TestEvaluacion(Base):
    __tablename__ = "evaluaciones"
    id = Column(Integer, primary_key=True, index=True)
    nino_id = Column(Integer, ForeignKey("ninos.id"))
    tipo_test = Column(String) # ej. ECEP, Conners, WISC, etc.
    puntuacion = Column(Float)
    observaciones = Column(String)
    fecha_evaluacion = Column(DateTime, default=datetime.datetime.utcnow)

class Sesion(Base):
    __tablename__ = "sesiones"
    id = Column(Integer, primary_key=True, index=True)
    nino_id = Column(Integer, ForeignKey("ninos.id"))
    estado_emocional_inicio = Column(String) # Ej: Feliz, Ansioso, Cansado
    estado_emocional_final = Column(String, nullable=True) # Pilar 1: Cierre emocional
    nivel_frustracion_detectado = Column(Float, default=0.0)
    indice_autonomia = Column(Float, default=1.0)
    fecha_inicio = Column(DateTime, default=datetime.datetime.utcnow)

class Interaccion(Base):
    __tablename__ = "interacciones"
    id = Column(Integer, primary_key=True, index=True)
    sesion_id = Column(Integer, ForeignKey("sesiones.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
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
    nino_id = Column(Integer, ForeignKey("ninos.id"))
    accion_id = Column(Integer, ForeignKey("catalogo_acciones.id"))
    fecha_asignacion = Column(DateTime, default=datetime.datetime.utcnow)
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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Crear las tablas
Base.metadata.create_all(bind=engine)