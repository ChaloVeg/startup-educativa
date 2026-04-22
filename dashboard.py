import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from database import SessionLocal, UsuarioNiño, Progreso, TestEvaluacion, CatalogoAcciones, AccionAsignada, Sesion, ConfiguracionProfesor, UsuarioWeb, Base, engine
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from engine import MotorInteligenciaEmocional
from ai_engine import NeuroForgeAI
import random
from datetime import datetime, timedelta
import re
import smtplib
import ssl
from email.message import EmailMessage
import os

def validar_rut(rut):
    """Valida formato de RUT chileno simple: 12345678-9 (sin puntos, con guion)"""
    return re.match(r'^\d{7,8}-[0-9Kk]$', str(rut)) is not None

def validar_correo(correo):
    """Valida formato de correo electrónico estándar"""
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', str(correo)) is not None

def enviar_correo_real(destinatario, asunto, mensaje_texto):
    """Envía un correo electrónico usando un servidor SMTP (ej. Gmail)."""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 465))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    if not smtp_user or not smtp_password:
        return False # No hay credenciales configuradas

    msg = EmailMessage()
    msg.set_content(mensaje_texto)
    msg['Subject'] = asunto
    msg['From'] = smtp_user
    msg['To'] = destinatario

    try:
        if smtp_port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error SMTP: {e}")
        return False

# Configuración de la interfaz
st.set_page_config(page_title="NeuroForge: Coordinación PIE", layout="wide")

# Ocultar el menú predeterminado de Streamlit
ocultar_menu_estilo = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
"""
st.markdown(ocultar_menu_estilo, unsafe_allow_html=True)

# Iniciar conexión segura con la BD

@st.cache_resource
def inicializar_base_datos():
    """Verifica y repara la base de datos UNA SOLA VEZ al iniciar la app para evitar latencia."""
    Base.metadata.create_all(bind=engine)
    db_temp = SessionLocal()
    try:
        try:
            db_temp.query(UsuarioWeb).first()
        except SQLAlchemyError:
            db_temp.rollback()
            UsuarioWeb.__table__.drop(engine, checkfirst=True)
            UsuarioWeb.__table__.create(engine)
            
        try:
            db_temp.query(AccionAsignada).first()
        except SQLAlchemyError:
            db_temp.rollback()
            AccionAsignada.__table__.drop(engine, checkfirst=True)
            AccionAsignada.__table__.create(engine)
            
        try:
            db_temp.query(ConfiguracionProfesor).first()
        except SQLAlchemyError:
            db_temp.rollback()
            ConfiguracionProfesor.__table__.drop(engine, checkfirst=True)
            ConfiguracionProfesor.__table__.create(engine)
    finally:
        db_temp.close()

inicializar_base_datos()

db = SessionLocal()

try:
    # --- SISTEMA DE LOGIN ---
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.rol = None
        st.session_state.username = None
    if "require_pwd_change" not in st.session_state:
        st.session_state.require_pwd_change = False
        st.session_state.temp_user_id = None

    if st.session_state.require_pwd_change:
        st.title("⚠️ Cambio de Contraseña Obligatorio")
        st.warning("Tu cuenta tiene una contraseña temporal. Debes cambiarla ahora para mantenerla activa.")
        with st.form("change_pwd_form"):
            new_pwd = st.text_input("Nueva Contraseña", type="password")
            new_pwd2 = st.text_input("Confirmar Contraseña", type="password")
            if st.form_submit_button("Actualizar y Entrar"):
                if new_pwd == new_pwd2 and len(new_pwd) >= 4:
                    user_to_update = db.query(UsuarioWeb).filter(UsuarioWeb.id == st.session_state.temp_user_id).first()
                    user_to_update.password = new_pwd
                    user_to_update.must_change_password = False
                    user_to_update.account_expires_at = None
                    db.commit()
                    st.session_state.require_pwd_change = False
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Las contraseñas no coinciden o son muy cortas (mín. 4 caracteres).")
        st.stop()

    elif not st.session_state.logged_in:
        st.title("🔐 Acceso a NeuroForge")
        st.markdown("Por favor, ingresa tus credenciales para continuar.")
        
        # Crear usuario admin por defecto si no existe en la BD
        admin_exists = db.query(UsuarioWeb).filter(UsuarioWeb.username == "admin").first()
        if not admin_exists:
            default_admin = UsuarioWeb(username="admin", password="123", rol="MasterAdmin")
            db.add(default_admin)
            db.commit()
        elif admin_exists.rol == "Admin":
            admin_exists.rol = "MasterAdmin"
            db.commit()

        col1, col2 = st.columns([1, 2])
        with col1:
            tab_login, tab_registro, tab_recuperar = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse", "🆘 Recuperar Contraseña"])
            
            with tab_login:
                with st.form("login_form"):
                    user_input = st.text_input("Usuario")
                    pwd_input = st.text_input("Contraseña", type="password")
                    submit_btn = st.form_submit_button("Ingresar")

                    if submit_btn:
                        db_user = db.query(UsuarioWeb).filter(UsuarioWeb.username == user_input, UsuarioWeb.password == pwd_input).first()
                        if db_user:
                            if db_user.must_change_password and db_user.account_expires_at and datetime.utcnow() > db_user.account_expires_at:
                                st.error("Tu cuenta ha caducado por no cambiar la contraseña a tiempo. Contacta al administrador.")
                            elif db_user.must_change_password:
                                st.session_state.require_pwd_change = True
                                st.session_state.temp_user_id = db_user.id
                                st.session_state.rol = db_user.rol
                                st.session_state.username = db_user.username
                                st.rerun()
                            else:
                                st.session_state.logged_in = True
                                st.session_state.rol = db_user.rol
                                st.session_state.username = db_user.username
                                st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos.")

            with tab_registro:
                with st.form("register_form"):
                    st.markdown("Registro exclusivo para Profesores")
                    new_rut = st.text_input("Ingresa tu RUT (Será tu usuario)")
                    new_email = st.text_input("Ingresa tu Correo Electrónico")
                    reg_btn = st.form_submit_button("Crear Cuenta")
                    
                    if reg_btn:
                        if not new_rut or not new_email:
                            st.error("Por favor, completa todos los campos.")
                        elif not validar_rut(new_rut):
                            st.error("RUT inválido. Usa el formato 12345678-9 (sin puntos y con guion).")
                        elif not validar_correo(new_email):
                            st.error("El formato del correo electrónico es inválido.")
                        else:
                            existe = db.query(UsuarioWeb).filter(UsuarioWeb.username == new_rut).first()
                            if existe:
                                st.error("Ya existe una cuenta con este RUT.")
                            else:
                                temp_pwd = str(random.randint(10000, 99999))
                                nuevo_profe = UsuarioWeb(
                                    username=new_rut, 
                                    email=new_email,
                                    password=temp_pwd, 
                                    rol="Profesor",
                                    must_change_password=True,
                                    account_expires_at=datetime.utcnow() + timedelta(hours=24)
                                )
                                db.add(nuevo_profe)
                                db.commit()
                                st.success("¡Cuenta creada exitosamente!")
                                
                                asunto = "Bienvenido a NeuroForge - Tu Clave Temporal"
                                cuerpo = f"Hola,\n\nTu cuenta ha sido creada exitosamente.\nTu usuario/RUT es: {new_rut}\nTu clave temporal de acceso es: {temp_pwd}\n\nPor seguridad, esta clave caducará en 24 horas y el sistema te pedirá cambiarla apenas inicies sesión.\n\nSaludos,\nEquipo NeuroForge"
                                if enviar_correo_real(new_email, asunto, cuerpo):
                                    st.info(f"📧 Correo enviado exitosamente a {new_email}.")
                                else:
                                    st.warning(f"⚠️ La cuenta se creó, pero falta configurar el servidor de correos (SMTP Secrets). La clave temporal es: {temp_pwd}")

            with tab_recuperar:
                with st.form("recover_form"):
                    rec_rut = st.text_input("Ingresa tu RUT")
                    rec_email = st.text_input("Ingresa tu Correo")
                    reg_btn = st.form_submit_button("Recuperar Contraseña")
                    
                    if reg_btn:
                        if not rec_rut or not rec_email:
                            st.error("Por favor, completa todos los campos.")
                        elif not validar_rut(rec_rut):
                            st.error("RUT inválido. Usa el formato 12345678-9.")
                        elif not validar_correo(rec_email):
                            st.error("El formato del correo electrónico es inválido.")
                        else:
                            user_rec = db.query(UsuarioWeb).filter(UsuarioWeb.username == rec_rut, UsuarioWeb.email == rec_email).first()
                            if user_rec:
                                temp_pwd = str(random.randint(10000, 99999))
                                user_rec.password = temp_pwd
                                user_rec.must_change_password = True
                                user_rec.account_expires_at = datetime.utcnow() + timedelta(hours=24)
                                db.commit()
                                st.success("Petición procesada.")
                                
                                asunto = "NeuroForge - Recuperación de Contraseña"
                                cuerpo = f"Hola,\n\nHas solicitado recuperar tu acceso.\nTu nueva clave temporal es: {temp_pwd}\n\nRecuerda cambiarla al iniciar sesión.\n\nSaludos."
                                if enviar_correo_real(rec_email, asunto, cuerpo):
                                    st.info(f"📧 Hemos enviado las instrucciones a {rec_email}")
                                else:
                                    st.warning(f"⚠️ Falta configurar servidor de correos (SMTP). Tu clave temporal es: {temp_pwd}")
                            else:
                                st.error("RUT o correo no encontrados.")

            st.divider()
            if st.button("👦 Entrar como Alumno (Check-In)", use_container_width=True):
                st.session_state.logged_in = True
                st.session_state.rol = "Alumno"
                st.session_state.username = "Alumno"
                st.rerun()
        st.stop()

    # ==========================================
    # CONTROL DE ACCESO Y NAVEGACIÓN LATERAL
    # ==========================================
    st.sidebar.title("NeuroForge")
    st.sidebar.markdown(f"👤 **Usuario:** {st.session_state.username}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.rol = None
        st.session_state.username = None
        st.rerun()
    st.sidebar.divider()

    rol_usuario = st.session_state.rol

    if rol_usuario in ["MasterAdmin", "Admin"]:
        st.sidebar.markdown("### Menú Administrativo")
        opciones_admin = ["Visión Global PIE", "Directorio y Asignaciones", "Catálogo Pedagógico", "Test y Evaluaciones"]
        if rol_usuario == "MasterAdmin":
            opciones_admin.append("Gestión de Usuarios y Accesos")
            
        vista_seleccionada = st.sidebar.radio("Navegación:", opciones_admin)

    elif rol_usuario == "Profesor":
        st.sidebar.markdown("### Menú Docente")
        # El profesor ya no puede elegir quién es, el sistema asume su identidad de login
        profe_seleccionado = st.session_state.username
        
        config_profe = db.query(ConfiguracionProfesor).filter(ConfiguracionProfesor.nombre_profesor == profe_seleccionado).first()
        opciones_docente = []
        if not config_profe or config_profe.ver_alumnos:
            opciones_docente.append("Mis Alumnos y Avances")
        if not config_profe or config_profe.ver_tareas:
            opciones_docente.append("Mi Panel de Tareas")
            
        if opciones_docente:
            vista_seleccionada = st.sidebar.radio("Navegación:", opciones_docente)
        else:
            st.sidebar.warning("No tienes vistas habilitadas por el Administrador.")
            vista_seleccionada = "Acceso Restringido"

    else:
        vista_seleccionada = "Check-In"

    # ==========================================
    # VISTAS: COORDINACIÓN PIE (ADMIN)
    # ==========================================
    if vista_seleccionada == "Visión Global PIE":
        st.title("⚡ Centro de Comando: Mando Ejecutivo")
        st.markdown("### Visión Departamental: PIE")
        
        st.markdown("""
            <style>
            div[data-testid="stMetricValue"] { color: #00FFCC; text-shadow: 0px 0px 10px rgba(0,255,204,0.6); }
            h1, h2, h3 { color: #E0E0E0; }
            hr { border-color: #FF00FF; box-shadow: 0px 0px 5px #FF00FF; }
            </style>
        """, unsafe_allow_html=True)
        st.divider()

        total_alumnos = db.query(UsuarioNiño).count()
        total_tareas = db.query(AccionAsignada).filter(AccionAsignada.estado == "Pendiente").count()
        
        if total_alumnos == 0:
            st.info("👋 ¡Bienvenido a tu nueva base de datos en la nube! Actualmente está vacía.")
            if st.button("🚀 Cargar Datos de Prueba Automáticos"):
                from seed import seed_data
                with st.spinner("Sembrando la base de datos con alumnos y catálogo..."):
                    seed_data()
                st.rerun()
            st.markdown("*O si lo prefieres, ve a **Directorio y Asignaciones** en el menú izquierdo para crear tu primer alumno manualmente.*")
            st.divider()

        c1, c2, c3 = st.columns(3)
        c1.metric("Estudiantes en PIE", total_alumnos)
        c2.metric("Tareas Docentes Pendientes", total_tareas)
        c3.metric("Evaluaciones Registradas", db.query(TestEvaluacion).count())
        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔥 Mapa de Calor de Autonomía")
            dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
            tareas = ['Lectura', 'Matemáticas', 'Lógica', 'Motricidad']
            z_data = np.random.uniform(0.3, 1.0, size=(len(tareas), len(dias)))
            fig_heat = px.imshow(z_data, labels=dict(x="Día", y="Área", color="Autonomía"), x=dias, y=tareas, color_continuous_scale='Inferno')
            fig_heat.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E0E0'))
            st.plotly_chart(fig_heat, use_container_width=True)
            
        with col2:
            st.subheader("🧠 Curva de Carga Cognitiva")
            sesiones_idx = list(range(1, 21))
            latencia_trend = np.convolve(np.random.normal(3000, 500, 20), np.ones(3)/3, mode='same')
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=sesiones_idx, y=latencia_trend, mode='lines+markers', name='Latencia (ms)', line=dict(color='#FF00FF', width=3, shape='spline')))
            fig_line.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E0E0'),
                xaxis=dict(showgrid=True, gridcolor='#333333', title='Minuto de Sesión'),
                yaxis=dict(showgrid=True, gridcolor='#333333', title='Milisegundos')
            )
            st.plotly_chart(fig_line, use_container_width=True)

    elif vista_seleccionada == "Directorio y Asignaciones":
        st.title("📝 Directorio PIE y Asignación de Casos")
        with st.form("nuevo_alumno_form", clear_on_submit=True):
            st.subheader("Añadir Nuevo Alumno")
            nombre_nuevo = st.text_input("Nombre completo del alumno")
            perfil_nuevo = st.selectbox("Perfil Diagnóstico", ["TDAH", "Dislexia", "TEA", "Sin especificar"])
            curso_nuevo = st.text_input("Curso (Ej: 3ro Básico)")
            profe_nuevo = st.text_input("Profesor(a) Asignado(a) (Ej: Profe Ana)")
            submitted = st.form_submit_button("Añadir Alumno")
            if submitted:
                if not nombre_nuevo or not curso_nuevo or not profe_nuevo:
                    st.error("Por favor, completa todos los campos obligatorios del alumno.")
                elif not validar_rut(profe_nuevo):
                    st.error("El RUT del profesor asignado es inválido (formato: 12345678-9).")
                else:
                    nuevo_nino = UsuarioNiño(nombre=nombre_nuevo, perfil_diagnostico=perfil_nuevo, curso=curso_nuevo, profesor_asignado=profe_nuevo)
                    db.add(nuevo_nino)
                    db.commit()
                    st.success(f"¡Alumno '{nombre_nuevo}' añadido correctamente y asignado a {profe_nuevo}!")

        st.divider()
        st.subheader("Directorio y Métricas de Alumnos")
        alumnos_registrados = db.query(UsuarioNiño).all()
        if alumnos_registrados:
            col_lista, col_grafica = st.columns(2)
            with col_lista:
                st.markdown("**Lista Detallada:**")
                df_directorio = pd.DataFrame([{"ID": a.id, "Nombre": a.nombre, "Curso": a.curso, "Perfil": a.perfil_diagnostico, "Profesor": a.profesor_asignado} for a in alumnos_registrados])
                st.dataframe(df_directorio, hide_index=True)
            with col_grafica:
                df_perfiles = pd.DataFrame([a.perfil_diagnostico for a in alumnos_registrados], columns=['Perfil'])
                df_conteo = df_perfiles.value_counts().reset_index()
                df_conteo.columns = ['Perfil', 'Cantidad']
                fig_perfiles = px.pie(df_conteo, values='Cantidad', names='Perfil', hole=0.4, title="Distribución Diagnóstica", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_perfiles.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E0E0'))
                st.plotly_chart(fig_perfiles, use_container_width=True)
        else:
            st.info("Aún no hay alumnos registrados en el sistema.")

    elif vista_seleccionada == "Catálogo Pedagógico":
        st.title("🧠 Catálogo de Acciones Pedagógicas")
        st.markdown("Gestiona el catálogo oficial de estrategias e intervenciones de NeuroForge.")
        with st.form("nueva_accion_form", clear_on_submit=True):
            st.subheader("Registrar Nueva Estrategia Pedagógica")
            nombre = st.text_input("Nombre de la Acción")
            descripcion = st.text_area("Descripción Pedagógica")
            categoria = st.selectbox("Pilar / Categoría", ["Emoción", "Adaptabilidad", "Autonomía"])
            submitted = st.form_submit_button("Guardar en Catálogo")
            if submitted:
                if not nombre or not descripcion:
                    st.error("Por favor, completa el nombre y la descripción de la acción.")
                else:
                    existe = db.query(CatalogoAcciones).filter(CatalogoAcciones.nombre_accion.ilike(nombre)).first()
                    if existe:
                        st.error(f"La acción '{nombre}' ya existe en el catálogo. Intenta con otro nombre.")
                    else:
                        nueva_accion = CatalogoAcciones(nombre_accion=nombre, descripcion=descripcion, categoria=categoria, es_personalizada=True)
                        db.add(nueva_accion)
                        db.commit()
                        st.success(f"Acción '{nombre}' registrada exitosamente.")
        st.divider()
        st.subheader("Catálogo Oficial de Estrategias")
        acciones = db.query(CatalogoAcciones).all()
        if acciones:
            df_acciones = pd.DataFrame([{"ID": a.id, "Nombre": a.nombre_accion, "Categoría": a.categoria, "Descripción": a.descripcion, "Personalizada": "Sí" if a.es_personalizada else "Por defecto"} for a in acciones])
            st.dataframe(df_acciones, use_container_width=True)
        else:
            st.info("No hay acciones registradas. Ejecuta `seed.py` para cargar las predeterminadas.")

    elif vista_seleccionada == "Test y Evaluaciones":
        st.title("📋 Evaluaciones Psicométricas y Cognitivas")
        st.markdown("Registra y consulta los resultados de tests estandarizados de los alumnos.")
        tab1, tab2 = st.tabs(["✏️ Registrar Nuevo Test", "📊 Historial de Evaluaciones"])
        with tab1:
            st.subheader("Registrar Resultado de Evaluación")
            alumnos_registrados = db.query(UsuarioNiño).all()
            if alumnos_registrados:
                with st.form("nuevo_test_form", clear_on_submit=True):
                    opciones_alumnos = {a.id: a.nombre for a in alumnos_registrados}
                    nino_id_seleccionado = st.selectbox("Seleccione un Alumno", options=list(opciones_alumnos.keys()), format_func=lambda x: opciones_alumnos[x])
                    tipo_test = st.selectbox("Tipo de Test", ["ECEP (Escala de Comportamiento Preescolar)", "Test de Atención de Conners", "WISC-V (Inteligencia)", "PROLEC-R (Lectura)", "Otro"])
                    puntuacion = st.number_input("Puntuación Total / Percentil", min_value=0.0, step=0.5)
                    observaciones = st.text_area("Observaciones Clínicas / Notas del Docente")
                    submitted = st.form_submit_button("Guardar Evaluación")
                    if submitted:
                        if not observaciones:
                            st.error("Por favor, ingresa las observaciones o notas de la evaluación.")
                        else:
                            nueva_evaluacion = TestEvaluacion(nino_id=nino_id_seleccionado, tipo_test=tipo_test, puntuacion=puntuacion, observaciones=observaciones)
                            db.add(nueva_evaluacion)
                            db.commit()
                            st.success(f"¡Evaluación '{tipo_test}' guardada exitosamente para {opciones_alumnos[nino_id_seleccionado]}!")
            else:
                st.warning("Debe registrar al menos un alumno en 'Directorio' antes de guardar evaluaciones.")
        with tab2:
            st.subheader("Registro Histórico")
            evaluaciones = db.query(TestEvaluacion).all()
            if evaluaciones:
                query = text("SELECT n.nombre as Alumno, e.tipo_test as 'Test Realizado', e.puntuacion as Puntuación, e.observaciones as Observaciones, e.fecha_evaluacion as Fecha FROM evaluaciones e JOIN ninos n ON e.nino_id = n.id ORDER BY e.fecha_evaluacion DESC")
                df_evals = pd.read_sql_query(query, db.bind)
                st.dataframe(df_evals, use_container_width=True)
            else:
                st.info("No hay evaluaciones registradas en el sistema todavía.")

    elif vista_seleccionada == "Gestión de Accesos":
        st.title("🔐 Gestión de Accesos y Credenciales")
        st.markdown("Crea cuentas de acceso para los profesores y controla qué secciones pueden ver.")
        
        with st.form("new_user_form", clear_on_submit=True):
            st.subheader("Crear Cuenta de Profesor")
            st.caption("El nombre de usuario debe coincidir exactamente con el 'Profesor Asignado' en el Directorio (Ej: Profe Ana).")
            new_user = st.text_input("Nombre de Usuario")
            new_pwd = st.text_input("Contraseña", type="password")
            submit_user = st.form_submit_button("Crear Cuenta")
            
            if submit_user and new_user and new_pwd:
                existe = db.query(UsuarioWeb).filter(UsuarioWeb.username == new_user).first()
                if existe:
                    st.error("Ya existe una cuenta con ese nombre de usuario.")
                else:
                    db.add(UsuarioWeb(username=new_user, password=new_pwd, rol="Profesor"))
                    db.commit()
                    st.success(f"Cuenta para '{new_user}' creada exitosamente.")
                    
        st.divider()
        st.subheader("Permisos de Vistas por Profesor")
        
        profesores_unicos = [r[0] for r in db.query(UsuarioWeb.username).filter(UsuarioWeb.rol == "Profesor").all()]
        
        if profesores_unicos:
            for profe in profesores_unicos:
                config = db.query(ConfiguracionProfesor).filter(ConfiguracionProfesor.nombre_profesor == profe).first()
                if not config:
                    config = ConfiguracionProfesor(nombre_profesor=profe)
                    db.add(config)
                    db.commit()
                    db.refresh(config)
                
                with st.expander(f"⚙️ Configurar permisos para: {profe}"):
                    ver_alum = st.checkbox("Ver 'Mis Alumnos y Avances'", value=config.ver_alumnos, key=f"alum_{profe}")
                    ver_tar = st.checkbox("Ver 'Mi Panel de Tareas'", value=config.ver_tareas, key=f"tar_{profe}")
                    if st.button("Guardar Cambios", key=f"btn_{profe}"):
                        config.ver_alumnos = ver_alum
                        config.ver_tareas = ver_tar
                        db.commit()
                        st.success(f"Permisos actualizados para {profe}.")
        else:
            st.info("Aún no hay profesores registrados en el sistema.")

    elif vista_seleccionada == "Gestión de Usuarios y Accesos":
        st.title("🔐 Gestión de Usuarios y Accesos")
        st.markdown("Administra cuentas, visualiza la actividad del profesorado y controla sus permisos.")
        
        tab_crear, tab_lista = st.tabs(["➕ Dar de Alta Usuario", "📋 Directorio de Usuarios y Analítica"])
        
        with tab_crear:
            with st.form("new_user_form_admin", clear_on_submit=True):
                st.subheader("Crear Cuenta de Usuario")
                st.caption("Se generará una clave inicial automática que expirará en 24 horas.")
                new_rol = st.selectbox("Tipo de Cuenta", ["Profesor", "Admin"])
                new_rut = st.text_input("RUT / Usuario")
                new_email = st.text_input("Correo Electrónico")
                submit_user = st.form_submit_button("Crear y Enviar Accesos")
                
                if submit_user:
                    if not new_rut or not new_email:
                        st.error("Por favor, completa todos los campos.")
                    elif new_rol == "Profesor" and not validar_rut(new_rut):
                        st.error("RUT inválido. Para profesores usa el formato 12345678-9.")
                    elif not validar_correo(new_email):
                        st.error("El formato del correo electrónico es inválido.")
                    else:
                        existe = db.query(UsuarioWeb).filter(UsuarioWeb.username == new_rut).first()
                        if existe:
                            st.error("Ya existe una cuenta con este nombre de usuario o RUT.")
                        else:
                            temp_pwd = str(random.randint(10000, 99999))
                            nuevo_usuario = UsuarioWeb(
                                username=new_rut, 
                                email=new_email,
                                password=temp_pwd, 
                                rol=new_rol,
                                must_change_password=True,
                                account_expires_at=datetime.utcnow() + timedelta(hours=24)
                            )
                            db.add(nuevo_usuario)
                            db.commit()
                            st.success(f"Cuenta de {new_rol} para '{new_rut}' creada exitosamente.")
                            
                            asunto = "Acceso Creado - NeuroForge"
                            cuerpo = f"Hola,\n\nEl Administrador ha creado tu cuenta de {new_rol}.\nUsuario: {new_rut}\nClave temporal: {temp_pwd}\n\nIngresa al portal para cambiar tu clave.\n\nSaludos."
                            if enviar_correo_real(new_email, asunto, cuerpo):
                                st.info(f"📧 Correo con clave inicial enviado a {new_email}")
                            else:
                                st.warning(f"⚠️ Cuenta creada, pero falta configurar el servidor SMTP. Entrégale esta clave al usuario: {temp_pwd}")
        
        with tab_lista:
            st.subheader("Analítica y Control de Usuarios")
            usuarios_unicos = db.query(UsuarioWeb).filter(UsuarioWeb.username != "admin").all()
        
            if usuarios_unicos:
                for usuario in usuarios_unicos:
                    if not usuario.created_at:
                        usuario.created_at = datetime.utcnow()
                    dias_creacion = (datetime.utcnow() - usuario.created_at).days
                    
                    with st.expander(f"👤 {usuario.username} | Rol: {usuario.rol} | ⏳ Días en sistema: {dias_creacion}"):
                        st.write(f"**Correo:** {usuario.email}")
                        estado_cuenta = "Caducada" if usuario.must_change_password and usuario.account_expires_at and datetime.utcnow() > usuario.account_expires_at else "Pendiente de Cambio" if usuario.must_change_password else "Activa"
                        st.write(f"**Estado:** {estado_cuenta}")
                        
                        if usuario.rol == "Profesor":
                            alumnos_ids = [n.id for n in db.query(UsuarioNiño).filter(UsuarioNiño.profesor_asignado == usuario.username).all()]
                            pendientes = db.query(AccionAsignada).filter(AccionAsignada.nino_id.in_(alumnos_ids), AccionAsignada.estado == "Pendiente").count() if alumnos_ids else 0
                            en_proceso = db.query(AccionAsignada).filter(AccionAsignada.nino_id.in_(alumnos_ids), AccionAsignada.estado == "En Proceso").count() if alumnos_ids else 0
                            asignadas_total = db.query(AccionAsignada).filter(AccionAsignada.nino_id.in_(alumnos_ids)).count() if alumnos_ids else 0
                            
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Tareas Totales", asignadas_total)
                            c2.metric("En Proceso", en_proceso)
                            c3.metric("Pendientes", pendientes)
                            
                            config = db.query(ConfiguracionProfesor).filter(ConfiguracionProfesor.nombre_profesor == usuario.username).first()
                            if not config:
                                config = ConfiguracionProfesor(nombre_profesor=usuario.username)
                                db.add(config)
                                db.commit()
                                db.refresh(config)
                        
                        col_btn1, col_btn2 = st.columns(2)
                        if col_btn1.button("🗑️ Eliminar Usuario", key=f"del_{usuario.id}"):
                            db.delete(usuario)
                            db.commit()
                            st.rerun()
                        
                        if usuario.rol == "Profesor":
                            st.write("---")
                            st.write("**Permisos de Vistas**")
                            ver_alum = st.checkbox("Ver 'Mis Alumnos y Avances'", value=config.ver_alumnos, key=f"alum_{usuario.id}")
                            ver_tar = st.checkbox("Ver 'Mi Panel de Tareas'", value=config.ver_tareas, key=f"tar_{usuario.id}")
                            if st.button("Actualizar Permisos", key=f"btn_perm_{usuario.id}"):
                                config.ver_alumnos = ver_alum
                                config.ver_tareas = ver_tar
                                db.commit()
                                st.success("Permisos actualizados.")
            else:
                st.info("Aún no hay otros usuarios registrados en el sistema.")

    # ==========================================
    # VISTAS: PROFESOR(A) ESPECIALISTA
    # ==========================================
    elif vista_seleccionada == "Mis Alumnos y Avances":
        st.title(f"📚 Panel de Control: {profe_seleccionado}")
        st.markdown("### Monitoreo de Progreso y Acciones Pedagógicas")
        try:
            query_ninos = db.query(UsuarioNiño).filter(UsuarioNiño.profesor_asignado == profe_seleccionado)
            df_ninos = pd.read_sql(query_ninos.statement, db.bind)
            df_progreso = pd.read_sql(db.query(Progreso).statement, db.bind)
            if not df_progreso.empty and not df_ninos.empty:
                df_full = pd.merge(df_progreso, df_ninos, left_on="nino_id", right_on="id")
                st.sidebar.header("Filtros del Dashboard")
                nino_seleccionado = st.sidebar.selectbox("Seleccione un Alumno", df_ninos["nombre"].tolist())
                datos_alumno = df_full[df_full["nombre"] == nino_seleccionado].copy()
                if not datos_alumno.empty:
                    datos_alumno['fecha_sesion'] = pd.to_datetime(datos_alumno['fecha_sesion'])
                    datos_alumno = datos_alumno.sort_values('fecha_sesion')
                    nino_id_actual = int(datos_alumno.iloc[0]['nino_id'])
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Nivel Promedio", f"{datos_alumno['nivel_alcanzado'].mean():.1f}")
                    col2.metric("Errores Totales", int(datos_alumno["errores_cometidos"].sum()))
                    col3.metric("T. Reacción Medio (s)", f"{datos_alumno['tiempo_reaccion'].mean():.2f}")
                    
                    st.subheader(f"📈 Curva de Aprendizaje de {nino_seleccionado}")
                    st.line_chart(datos_alumno.set_index('fecha_sesion')[["nivel_alcanzado", "errores_cometidos"]])
                    
                    st.divider()
                    st.subheader("🤖 Copiloto de IA Pedagógica")
                    if st.button(f"✨ Generar Plan de Acción para {nino_seleccionado}"):
                        with st.spinner("El Sistema Experto está analizando la telemetría. Por favor espera..."):
                            try:
                                motor_ia_gen = NeuroForgeAI()
                                datos_para_ia = {"historial_progreso": datos_alumno.astype(str).to_dict(orient='records')}
                                plan_accion = motor_ia_gen.generar_insight_pedagogico(datos_para_ia)
                                st.success("¡Análisis pedagógico completado!")
                                st.info(plan_accion)
                            except Exception as error_analisis:
                                st.error(f"⚙️ Error al procesar las métricas: {error_analisis}")
                    
                    st.divider()
                    st.subheader("🎯 Asignar Ajuste Pedagógico")
                    catalogo = db.query(CatalogoAcciones).all()
                    if catalogo:
                        opciones_acciones = {a.id: f"[{a.categoria}] {a.nombre_accion}" for a in catalogo}
                        accion_seleccionada = st.selectbox("Seleccione Acción", options=list(opciones_acciones.keys()), format_func=lambda x: opciones_acciones[x])
                        dias_duracion = st.number_input("Días de duración esperados", min_value=1, value=7)
                        
                        if st.button("Asignar a Próxima Sesión"):
                            fecha_venc = datetime.utcnow() + timedelta(days=dias_duracion)
                            nueva_asignacion = AccionAsignada(nino_id=nino_id_actual, accion_id=accion_seleccionada, fecha_vencimiento=fecha_venc)
                            db.add(nueva_asignacion)
                            db.commit()
                            st.success("Acción asignada exitosamente para la próxima sesión.")
                    else:
                        st.info("El catálogo está vacío. Ve al 'Catálogo Pedagógico' para agregar acciones.")
                    
                    asignadas = db.query(AccionAsignada).filter(AccionAsignada.nino_id == nino_id_actual, AccionAsignada.estado == "Pendiente").all()
                    if asignadas:
                        st.markdown("**Acciones Pendientes:**")
                        for asig in asignadas:
                            accion = db.query(CatalogoAcciones).filter(CatalogoAcciones.id == asig.accion_id).first()
                            col_t, col_b = st.columns([4, 1])
                            with col_t:
                                st.caption(f"- {accion.nombre_accion} ({accion.categoria})")
                            with col_b:
                                if st.button("✅ Completar", key=f"comp_{asig.id}"):
                                    asig.estado = "Completada"
                                    db.commit()
                                    st.rerun()
                                    
                    completadas = db.query(AccionAsignada).filter(AccionAsignada.nino_id == nino_id_actual, AccionAsignada.estado == "Completada").order_by(AccionAsignada.fecha_asignacion.desc()).all()
                    if completadas:
                        with st.expander("📚 Ver Historial de Intervenciones Completadas"):
                            for comp in completadas:
                                accion_comp = db.query(CatalogoAcciones).filter(CatalogoAcciones.id == comp.accion_id).first()
                                if accion_comp:
                                    fecha_str = comp.fecha_asignacion.strftime("%Y-%m-%d")
                                    st.markdown(f"- ✅ **{accion_comp.nombre_accion}** ({accion_comp.categoria}) - *{fecha_str}*")
                else:
                    st.warning(f"No hay datos de progreso registrados para {nino_seleccionado} todavía.")
            else:
                st.info("No hay registros. Ejecuta `seed.py` o registra progreso.")
        except Exception as e:
            st.error(f"Error al cargar datos: {e}")

    elif vista_seleccionada == "Mi Panel de Tareas":
        st.title(f"✅ Tareas Pendientes: {profe_seleccionado}")
        st.markdown("Gestiona las intervenciones pedagógicas programadas para tus alumnos.")
        alumnos_ids = [n.id for n in db.query(UsuarioNiño).filter(UsuarioNiño.profesor_asignado == profe_seleccionado).all()]
        if alumnos_ids:
            asignadas = db.query(AccionAsignada).filter(AccionAsignada.nino_id.in_(alumnos_ids), AccionAsignada.estado.in_(["Pendiente", "En Proceso"])).all()
            col1, col2 = st.columns(2)
            col1.metric("Alumnos a cargo", len(alumnos_ids))
            col2.metric("Tareas Pendientes totales", len(asignadas))
            st.divider()
            if asignadas:
                for asig in asignadas:
                    nino = db.query(UsuarioNiño).filter(UsuarioNiño.id == asig.nino_id).first()
                    accion = db.query(CatalogoAcciones).filter(CatalogoAcciones.id == asig.accion_id).first()
                    
                    # Cálculo de caducidad y alertas
                    dias_restantes = (asig.fecha_vencimiento - datetime.utcnow()).days if asig.fecha_vencimiento else 99
                    alerta_msg = ""
                    if 0 <= dias_restantes <= 2:
                        alerta_msg = f"\n⚠️ **¡Alerta!** Vence en {dias_restantes} días. *(Correo enviado al profesor)*"
                    
                    estado_color = "🔴" if asig.estado == "Pendiente" else "🟡"
                    c1, c2, c3 = st.columns([2, 4, 1])
                    c1.markdown(f"**👦 {nino.nombre}**\n*{nino.curso}*\n{estado_color} {asig.estado}")
                    c2.markdown(f"**{accion.nombre_accion}**\n{accion.descripcion}{alerta_msg}")
                    with c3:
                        if asig.estado == "Pendiente" and st.button("Iniciar", key=f"prog_{asig.id}"):
                            asig.estado = "En Proceso"
                            db.commit()
                            st.rerun()
                        if st.button("Completar", key=f"comp_{asig.id}"):
                            asig.estado = "Completada"
                            db.commit()
                            st.rerun()
                    st.write("---")
            else:
                st.success("¡Excelente! No tienes acciones pedagógicas pendientes para tus alumnos.")
        else:
            st.info("No tienes alumnos asignados actualmente.")

    elif vista_seleccionada == "Acceso Restringido":
        st.title("🚫 Acceso Restringido")
        st.warning("El administrador ha desactivado temporalmente todas tus vistas. Por favor, comunícate con Coordinación PIE.")

    # ==========================================
    # VISTAS: MODO ALUMNO
    # ==========================================
    elif vista_seleccionada == "Check-In":
        st.title("🌟 ¡Hola! ¿Cómo te sientes hoy?")
        st.markdown("### Selecciona el icono que mejor represente tu emoción:")
        st.divider()
        alumnos = db.query(UsuarioNiño).all()
        if alumnos:
            opciones_alumnos = {a.id: a.nombre for a in alumnos}
            nino_id_checkin = st.selectbox("¿Quién eres?", options=list(opciones_alumnos.keys()), format_func=lambda x: opciones_alumnos[x])
        else:
            st.warning("No hay alumnos registrados. Pide a tu profesor que te registre primero.")
            nino_id_checkin = None

        motor_emo = MotorInteligenciaEmocional()
        st.markdown("""
            <style>
            div.stButton > button { 
                height: 200px !important; 
                border-radius: 20px !important;
                border: 2px solid #333 !important;
                transition: all 0.3s ease-in-out !important;
            }
            div.stButton > button p {
                font-size: 120px !important;
                line-height: 1.2 !important;
            }
            div.stButton > button:hover {
                transform: scale(1.05) !important;
                border: 3px solid #00FFCC !important;
                box-shadow: 0px 0px 25px rgba(0, 255, 204, 0.6) !important;
                background-color: rgba(0, 255, 204, 0.1) !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        emocion_seleccionada = None
        with c1:
            if st.button("😃", use_container_width=True): emocion_seleccionada = "Feliz"
        with c2:
            if st.button("😐", use_container_width=True): emocion_seleccionada = "Neutro"
        with c3:
            if st.button("😰", use_container_width=True): emocion_seleccionada = "Ansioso"
            
        if emocion_seleccionada and nino_id_checkin:
            ajustes = motor_emo.procesar_checkin(emocion_seleccionada)
            nueva_sesion = Sesion(nino_id=nino_id_checkin, estado_emocional_inicio=emocion_seleccionada)
            db.add(nueva_sesion)
            db.commit()
            st.success(f"¡Gracias por contarnos! Has seleccionado: **{emocion_seleccionada}**")
            st.info(f"**Parámetros enviados al juego:**\n- Velocidad del Motor: `{ajustes['global_speed_modifier']}x`\n- Paleta de Colores: `{ajustes['color_palette'].replace('_', ' ').title()}`")
            if emocion_seleccionada == "Ansioso":
                st.warning("🧠 **Acción Pedagógica:** El motor detectó ansiedad. La velocidad del juego ha disminuido un 40% y se aplicarán colores pastel/suaves.")

finally:
    # El bloque try/finally asegura que la conexión siempre se cierre al terminar el script
    db.close()