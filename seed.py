from database import SessionLocal, UsuarioNiño, Progreso, CatalogoAcciones
import random
from datetime import datetime, timedelta

def seed_data():
    """
    Script para poblar la base de datos con datos de prueba.
    Es idempotente: solo se ejecuta si la base de datos está vacía.
    """
    db = SessionLocal()
    try:
        # 1. Verificar si ya hay datos para no duplicar
        if db.query(UsuarioNiño).first():
            print("La base de datos ya contiene datos. No se agregarán nuevos.")
            return

        # 2. Crear niños de prueba
        print("Creando usuarios de prueba...")
        ninos_data = [
            UsuarioNiño(nombre="Alex García", perfil_diagnostico="TDAH", curso="3ro Básico", profesor_asignado="Profe Ana"),
            UsuarioNiño(nombre="Sofía López", perfil_diagnostico="Dislexia", curso="4to Básico", profesor_asignado="Profe Carlos"),
            UsuarioNiño(nombre="Mateo Ruiz", perfil_diagnostico="TEA", curso="2do Básico", profesor_asignado="Profe Ana")
        ]
        db.add_all(ninos_data)
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

                progreso = Progreso(nino_id=nino.id, nivel_alcanzado=nivel_actual, tiempo_reaccion=round(tiempo, 2), errores_cometidos=errores, fecha_sesion=datetime.utcnow() - timedelta(days=20-i))
                db.add(progreso)
        db.commit()
        print("¡Datos de prueba insertados correctamente!")

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
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()