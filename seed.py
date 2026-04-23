from database import (
    SessionLocal, Alumno, Curso, Progreso, CatalogoAcciones, UsuarioWeb,
    Medico, Profesor, Especialista, Diagnostico, NecesidadEducativa, FichaAlumno,
    CategoriaDiagnostico, EspecialidadMedico, TipoEspecialista,
    TestEvaluacion, AccionAsignada
)
import random
from datetime import datetime, timedelta, timezone

def seed_data():
    """
    Script para poblar la base de datos con datos de prueba.
    Es idempotente: solo se ejecuta si la base de datos está vacía.
    """
    db = SessionLocal()
    try:
        # 1. Crear usuarios de sistema si no existen
        if not db.query(UsuarioWeb).filter(UsuarioWeb.username == "admin").first():
            print("Creando usuario MasterAdmin...")
            admin_user = UsuarioWeb(username="admin", password="123", rol="MasterAdmin", email="admin@neuroforge.cl")
            db.add(admin_user)

        profe_ana_rut = "11111111-K"
        profe_carlos_rut = "22222222-K"
        if not db.query(UsuarioWeb).filter(UsuarioWeb.username == profe_ana_rut).first():
            print("Creando usuario de prueba para Profe Ana...")
            profe_ana = UsuarioWeb(username=profe_ana_rut, email="ana@neuroforge.cl", password="123", rol="Profesor")
            db.add(profe_ana)
        
        if not db.query(UsuarioWeb).filter(UsuarioWeb.username == profe_carlos_rut).first():
            print("Creando usuario de prueba para Profe Carlos...")
            profe_carlos = UsuarioWeb(username=profe_carlos_rut, email="carlos@neuroforge.cl", password="123", rol="Profesor")
            db.add(profe_carlos)
        db.commit()

        # --- NUEVOS ACTORES DEL SISTEMA PIE ---
        print("Creando registro de Profesores...")
        if not db.query(Profesor).first():
            db.add_all([
                Profesor(rut=profe_ana_rut, nombres="Ana", apellidos="Gómez", registro="12345-MINEDUC"),
                Profesor(rut=profe_carlos_rut, nombres="Carlos", apellidos="Soto", registro="67890-MINEDUC")
            ])
            db.commit()

        print("Creando registro de Médicos...")
        if not db.query(Medico).first():
            db.add_all([
                Medico(rut="88888888-8", nombre="Dr. Roberto Neira", especialidad=EspecialidadMedico.NEUROLOGO),
                Medico(rut="99999999-9", nombre="Dra. Camila Torres", especialidad=EspecialidadMedico.PSIQUIATRA)
            ])
            db.commit()

        print("Creando registro de Especialistas...")
        if not db.query(Especialista).first():
            db.add_all([
                Especialista(rut="10101010-1", nombres="Felipe", apellidos="Paredes", registro="REG-PSI-01", tipo=TipoEspecialista.PSICOLOGO),
                Especialista(rut="12121212-2", nombres="Marta", apellidos="Lagos", registro="REG-FON-02", tipo=TipoEspecialista.FONOAUDIOLOGO)
            ])
            db.commit()

        print("Creando catálogo de Diagnósticos base...")
        if not db.query(Diagnostico).first():
            db.add_all([
                Diagnostico(categoria=CategoriaDiagnostico.PERMANENTE, tipo="tea"),
                Diagnostico(categoria=CategoriaDiagnostico.TRANSITORIO, tipo="tdah"),
                Diagnostico(categoria=CategoriaDiagnostico.TRANSITORIO, tipo="tel expresivo")
            ])
            db.commit()

        # 2. Verificar si ya hay alumnos para no duplicar
        if not db.query(Alumno).first():
            print("Creando cursos base...")
            curso_2 = Curso(nivel="2do Básico")
            curso_3 = Curso(nivel="3ro Básico")
            curso_4 = Curso(nivel="4to Básico")
            db.add_all([curso_2, curso_3, curso_4])
            db.commit()
            # Crear niños de prueba
            print("Creando usuarios de prueba (10 expedientes)...")
            nombres = ["Alex", "Sofía", "Mateo", "Valentina", "Lucas", "Martina", "Diego", "Camila", "Joaquín", "Valeria"]
            apellidos = ["García", "López", "Ruiz", "Soto", "Pérez", "Gómez", "Silva", "Díaz", "Rojas", "Torres"]
            
            ninos_data = []
            for i in range(10):
                ninos_data.append(Alumno(rut=f"{10000000+i}-{i%9}", nombres=nombres[i], apellidos=apellidos[i], curso_id=random.choice([curso_2.id, curso_3.id, curso_4.id])))
            
            db.add_all(ninos_data)
            db.commit()

            # Asignar Fichas y Necesidades Educativas
            print("Creando Fichas de Alumnos y Asignando Diagnósticos...")
            diagnosticos_list = db.query(Diagnostico).all()
            
            profesores = db.query(Profesor).all()
            medicos = db.query(Medico).all()
            especialistas = db.query(Especialista).all()
            
            for i, nino in enumerate(ninos_data):
                ficha = FichaAlumno(
                    alumno_id=nino.id, 
                    rut=nino.rut, 
                    nombre_social=nombres[i][:4], 
                    fecha_evaluaciones=datetime.now(timezone.utc) - timedelta(days=random.randint(10, 90)), 
                    profesor_id=random.choice(profesores).id, 
                    medico_id=random.choice(medicos).id, 
                    especialista_id=random.choice(especialistas).id
                )
                ne = NecesidadEducativa(
                    alumno_id=nino.id, 
                    diagnostico_id=random.choice(diagnosticos_list).id
                )
                db.add(ficha)
                db.add(ne)
            db.commit()

            # 3. Generar datos de progreso para cada niño
            print("Generando datos de progreso simulado...")
            for nino in ninos_data:
                db.refresh(nino) # Obtener el ID asignado
                nivel_actual = random.randint(1, 3)
                for i in range(20): # 20 sesiones de progreso por niño
                    errores = random.randint(0, 4)
                    tiempo = random.uniform(1.8, 5.5)
                    
                    # Simular progresión simple
                    if errores < 2 and tiempo < 3.0: nivel_actual += 1
                    elif errores > 2: nivel_actual = max(1, nivel_actual - 1)

                    progreso = Progreso(alumno_id=nino.id, nivel_alcanzado=nivel_actual, tiempo_reaccion=round(tiempo, 2), errores_cometidos=errores, fecha_sesion=datetime.now(timezone.utc) - timedelta(days=20-i))
                    db.add(progreso)
            db.commit()
            print("¡Datos de prueba insertados correctamente!")
        else:
            print("La base de datos ya contiene alumnos. Omitiendo...")

        # 4. Generar catálogo de acciones predeterminadas
        print("Verificando Catálogo de Acciones...")
        if not db.query(CatalogoAcciones).first():
            print("Creando acciones pedagógicas predeterminadas...")
            acciones_default = [
                CatalogoAcciones(nombre_accion="Simplificación de Interfaz", descripcion="Oculta elementos distractores del fondo.", categoria="Adaptabilidad", es_personalizada=False),
                CatalogoAcciones(nombre_accion="Aumento de Contraste", descripcion="Aumenta el contraste de los elementos clave.", categoria="Adaptabilidad", es_personalizada=False),
                CatalogoAcciones(nombre_accion="Pista de Audio", descripcion="Habilita instrucciones por voz.", categoria="Autonomía", es_personalizada=False),
                CatalogoAcciones(nombre_accion="Reducción de Velocidad", descripcion="Disminuye la velocidad global del juego un 40%.", categoria="Emoción", es_personalizada=False),
                CatalogoAcciones(nombre_accion="Paleta de Baja Estimulación", descripcion="Usa colores pastel para reducir ansiedad.", categoria="Emoción", es_personalizada=False)
            ]
            db.add_all(acciones_default)
            db.commit()
            print("¡Catálogo de acciones creado!")
            
        # 5. Generar Evaluaciones y Tareas Pendientes
        print("Generando Evaluaciones y Tareas de prueba...")
        alumnos_db = db.query(Alumno).all()
        acciones_db = db.query(CatalogoAcciones).all()
        
        if alumnos_db and acciones_db:
            if not db.query(TestEvaluacion).first():
                tipos_test = ["WISC-V (Inteligencia)", "Test de Atención de Conners", "ECEP (Comportamiento)", "PROLEC-R (Lectura)"]
                for nino in alumnos_db:
                    # 1 a 2 evaluaciones aleatorias por cada alumno
                    for _ in range(random.randint(1, 2)):
                        db.add(TestEvaluacion(
                            alumno_id=nino.id, 
                            tipo_test=random.choice(tipos_test), 
                            puntuacion=round(random.uniform(35.0, 115.0), 1), 
                            observaciones="Evaluación periódica de seguimiento PIE."
                        ))
            
            if not db.query(AccionAsignada).first():
                estados = ["Pendiente", "En Proceso", "Completada"]
                for nino in alumnos_db:
                    # 2 a 3 tareas asignadas por alumno
                    for _ in range(random.randint(2, 3)):
                        db.add(AccionAsignada(
                            alumno_id=nino.id, 
                            accion_id=random.choice(acciones_db).id, 
                            estado=random.choice(estados), 
                            fecha_vencimiento=datetime.now(timezone.utc) + timedelta(days=random.randint(-5, 15))
                        ))
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()