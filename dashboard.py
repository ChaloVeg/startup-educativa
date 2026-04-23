import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
from database import SessionLocal, Alumno, Curso, Diagnostico, NecesidadEducativa, CategoriaDiagnostico, Progreso, TestEvaluacion, CatalogoAcciones, AccionAsignada, Sesion, ConfiguracionProfesor, UsuarioWeb, Medico, EspecialidadMedico, Especialista, TipoEspecialista, Profesor, FichaAlumno, Base, engine
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from engine import MotorInteligenciaEmocional
from ai_engine import NeuroForgeAI
import random
from datetime import datetime, timedelta, timezone
import re
import base64
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

Base.metadata.create_all(bind=engine)

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
                            if db_user.must_change_password and db_user.account_expires_at and datetime.now(timezone.utc).replace(tzinfo=None) > db_user.account_expires_at:
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
                    new_email = st.text_input("Ingresa tu Correo Electrónico (Opcional)")
                    reg_btn = st.form_submit_button("Crear Cuenta")
                    
                    if reg_btn:
                        if not new_rut:
                            st.error("Por favor, ingresa tu RUT.")
                        elif not validar_rut(new_rut):
                            st.error("RUT inválido. Usa el formato 12345678-9 (sin puntos y con guion).")
                        elif new_email and not validar_correo(new_email):
                            st.error("El formato del correo electrónico es inválido.")
                        else:
                            existe_rut = db.query(UsuarioWeb).filter(UsuarioWeb.username == new_rut).first()
                            existe_correo = db.query(UsuarioWeb).filter(UsuarioWeb.email == new_email).first() if new_email else None
                            
                            if existe_rut:
                                st.error("Ya existe una cuenta con este RUT.")
                            elif existe_correo:
                                st.error("Este correo electrónico ya está registrado en otra cuenta. Por favor, usa otro o recupera tu contraseña.")
                            else:
                                try:
                                    temp_pwd = str(random.randint(10000, 99999))
                                    nuevo_profe = UsuarioWeb(
                                        username=new_rut, 
                                        email=new_email if new_email else None,
                                        password=temp_pwd, 
                                        rol="Profesor",
                                        must_change_password=True,
                                        account_expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)
                                    )
                                    db.add(nuevo_profe)
                                    db.commit()
                                    st.success("¡Cuenta creada exitosamente!")
                                    
                                    if new_email:
                                        asunto = "Bienvenido a NeuroForge - Tu Clave Temporal"
                                        cuerpo = f"Hola,\n\nTu cuenta ha sido creada exitosamente.\nTu usuario/RUT es: {new_rut}\nTu clave temporal de acceso es: {temp_pwd}\n\nPor seguridad, esta clave caducará en 24 horas y el sistema te pedirá cambiarla apenas inicies sesión.\n\nSaludos,\nEquipo NeuroForge"
                                        if enviar_correo_real(new_email, asunto, cuerpo):
                                            st.info(f"📧 Correo enviado exitosamente a {new_email}.")
                                        else:
                                            st.warning(f"⚠️ La cuenta se creó, pero falta configurar el servidor de correos. La clave temporal es: {temp_pwd}")
                                    else:
                                        st.warning(f"⚠️ Cuenta creada sin correo. Anota tu clave temporal ahora: {temp_pwd}")
                                except Exception as e:
                                    db.rollback()
                                    st.error("Ocurrió un error en la base de datos al crear la cuenta. Por favor, intenta nuevamente.")

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
                                user_rec.account_expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)
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
        opciones_admin = ["Visión Global PIE", "Analítica Avanzada y Reportes", "Cronograma de Tareas (Gantt)", "Directorio y Asignaciones", "Catálogo Pedagógico", "Test y Evaluaciones", "Gestión de Usuarios y Accesos"]
        
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

        try:
            # Verificación de integridad del esquema en la nube
            total_alumnos = db.query(Alumno).count()
            total_tareas = db.query(AccionAsignada).filter(AccionAsignada.estado == "Pendiente").count()
            _ = db.query(FichaAlumno).first() # Fuerza la validación de nuevas columnas (Alergias)
        except SQLAlchemyError:
            db.rollback() # Limpia la transacción fallida
            st.error("⚠️ Desfase Estructural Detectado en Neon.tech")
            st.warning("El código en la nube está actualizado al 100%, pero tu base de datos en Neon aún conserva las tablas antiguas. Para que el sistema funcione, debemos sincronizarlas.")
            st.divider()
            if st.button("🛠️ Limpiar y Reconstruir Base de Datos en la Nube", type="primary", use_container_width=True):
                Base.metadata.drop_all(bind=engine)
                Base.metadata.create_all(bind=engine)
                st.success("✅ Base de datos sincronizada con éxito. Por favor recarga la página web (Presiona F5).")
            st.stop() # Detiene la ejecución para no mostrar el resto de gráficas rotas

        if total_alumnos == 0:
            from seed import seed_data
            with st.spinner("Inicializando métricas y cargando 10 expedientes de prueba. Por favor espera un segundo..."):
                seed_data()
            st.rerun()

        c1, c2, c3 = st.columns(3)
        c1.metric("Estudiantes en PIE", total_alumnos)
        c2.metric("Tareas Docentes Pendientes", total_tareas)
        c3.metric("Evaluaciones Registradas", db.query(TestEvaluacion).count())
        st.divider()

        st.subheader("📊 Resumen Ejecutivo de Gestión y Avances")
        tab_tareas, tab_avance, tab_eval = st.tabs(["📋 Estado de Tareas", "📈 Progreso Estudiantil", "📝 Últimas Evaluaciones"])
        
        with tab_tareas:
            query_tareas = text("SELECT n.nombres || ' ' || n.apellidos as Alumno, c.nombre_accion as 'Intervención Pedagógica', a.estado as Estado, a.fecha_vencimiento as Vencimiento FROM acciones_asignadas a JOIN alumnos n ON a.alumno_id = n.id JOIN catalogo_acciones c ON a.accion_id = c.id ORDER BY a.fecha_vencimiento ASC")
            df_tareas = pd.read_sql_query(query_tareas, db.bind)
            if not df_tareas.empty:
                df_tareas['Vencimiento'] = pd.to_datetime(df_tareas['Vencimiento']).dt.strftime('%Y-%m-%d')
                st.dataframe(df_tareas, use_container_width=True, hide_index=True)
            else:
                st.info("No hay tareas asignadas actualmente.")
                
        with tab_avance:
            query_prog = text("SELECT n.nombres || ' ' || n.apellidos as Alumno, ROUND(AVG(p.nivel_alcanzado), 1) as 'Nivel Promedio', COUNT(p.id) as 'Sesiones Jugadas', ROUND(AVG(p.errores_cometidos), 1) as 'Errores Promedio' FROM progreso p JOIN alumnos n ON p.alumno_id = n.id GROUP BY n.id")
            df_prog = pd.read_sql_query(query_prog, db.bind)
            if not df_prog.empty:
                st.dataframe(df_prog, use_container_width=True, hide_index=True)
            else:
                st.info("No hay registros de progreso todavía.")
                
        with tab_eval:
            query_evals = text("SELECT n.nombres || ' ' || n.apellidos as Alumno, e.tipo_test as 'Test Realizado', e.puntuacion as 'Puntuación', e.fecha_evaluacion as Fecha FROM evaluaciones e JOIN alumnos n ON e.alumno_id = n.id ORDER BY e.fecha_evaluacion DESC LIMIT 10")
            df_evals = pd.read_sql_query(query_evals, db.bind)
            if not df_evals.empty:
                df_evals['Fecha'] = pd.to_datetime(df_evals['Fecha']).dt.strftime('%Y-%m-%d')
                st.dataframe(df_evals, use_container_width=True, hide_index=True)
            else:
                st.info("No hay evaluaciones registradas en el sistema todavía.")
                
    elif vista_seleccionada == "Analítica Avanzada y Reportes":
        st.title("📈 Analítica Avanzada y Reportes PIE")
        st.markdown("Panel ejecutivo con visualización integral del estado del programa, distribución poblacional y rendimiento global.")
        st.divider()

        # --- 1. KPIs EJECUTIVOS ---
        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        tot_alumnos = db.query(Alumno).count()
        tot_evals = db.query(TestEvaluacion).count()
        tot_tareas = db.query(AccionAsignada).count()
        tot_sesiones = db.query(Progreso).count()
        
        col_kpi1.metric("Estudiantes Activos", tot_alumnos)
        col_kpi2.metric("Evaluaciones Realizadas", tot_evals)
        col_kpi3.metric("Intervenciones Históricas", tot_tareas)
        col_kpi4.metric("Sesiones de Juego", tot_sesiones)
        st.divider()

        # --- 2. GRÁFICOS AVANZADOS EN PESTAÑAS ---
        tab_dist, tab_operaciones = st.tabs(["🧩 Distribución Poblacional", "⚙️ Operaciones y Carga Docente"])

        with tab_dist:
            st.subheader("Demografía y Categorización Diagnóstica")
            c_dist1, c_dist2 = st.columns(2)
            
            # Gráfico de Barras: Alumnos por Curso
            query_cursos = text("SELECT c.nivel as Curso, count(a.id) as Cantidad FROM alumnos a JOIN cursos c ON a.curso_id = c.id GROUP BY c.nivel")
            df_cursos = pd.read_sql_query(query_cursos, db.bind)
            if not df_cursos.empty:
                fig_cursos = px.bar(df_cursos, x="Curso", y="Cantidad", title="Distribución de Alumnos por Curso", color="Curso", color_discrete_sequence=px.colors.qualitative.Set3)
                fig_cursos.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E0E0'))
                c_dist1.plotly_chart(fig_cursos, use_container_width=True)
            else:
                c_dist1.info("No hay datos suficientes de cursos.")

            # Gráfico Donut: Diagnósticos Permanentes vs Transitorios
            query_diag = text("SELECT d.categoria as Categoria, count(ne.id) as Cantidad FROM necesidades_educativas ne JOIN diagnosticos d ON ne.diagnostico_id = d.id GROUP BY d.categoria")
            df_diag = pd.read_sql_query(query_diag, db.bind)
            if not df_diag.empty:
                fig_diag = px.pie(df_diag, values="Cantidad", names="Categoria", hole=0.5, title="Proporción Diagnóstica (NEE)", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_diag.update_traces(textposition='inside', textinfo='percent+label')
                fig_diag.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E0E0'))
                c_dist2.plotly_chart(fig_diag, use_container_width=True)
            else:
                c_dist2.info("No hay datos de categorización diagnóstica.")

        with tab_operaciones:
            st.subheader("Estado de Intervenciones y Casos por Profesional")
            c_op1, c_op2 = st.columns(2)
            
            # Gráfico Donut: Estado de Tareas
            query_tareas_est = text("SELECT estado as Estado, count(id) as Cantidad FROM acciones_asignadas GROUP BY estado")
            df_tareas_est = pd.read_sql_query(query_tareas_est, db.bind)
            if not df_tareas_est.empty:
                color_map = {'Pendiente': '#FFC107', 'En Proceso': '#00BFFF', 'Completada': '#00FF00'}
                fig_est = px.pie(df_tareas_est, values="Cantidad", names="Estado", hole=0.4, title="Estado de Intervenciones Asignadas", color="Estado", color_discrete_map=color_map)
                fig_est.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E0E0'))
                c_op1.plotly_chart(fig_est, use_container_width=True)
            else:
                c_op1.info("No hay tareas asignadas para evaluar su estado.")

            # Gráfico de Barras: Carga por Profesor
            query_carga = text("SELECT p.nombres || ' ' || p.apellidos as Profesional, count(f.id) as Casos FROM profesores p JOIN fichas_alumnos f ON p.id = f.profesor_id GROUP BY p.id")
            df_carga = pd.read_sql_query(query_carga, db.bind)
            if not df_carga.empty:
                fig_carga = px.bar(df_carga, x="Profesional", y="Casos", title="Casos Asignados por Docente PIE", color="Profesional", color_discrete_sequence=px.colors.qualitative.Vivid)
                fig_carga.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E0E0'), showlegend=False)
                c_op2.plotly_chart(fig_carga, use_container_width=True)
            else:
                c_op2.info("No hay docentes con casos asignados actualmente.")

    elif vista_seleccionada == "Cronograma de Tareas (Gantt)":
        st.title("🗓️ Cronograma de Intervenciones (Carta Gantt)")
        st.markdown("Visualiza de forma interactiva el estado, tiempos y responsables de todas las tareas pedagógicas asignadas.")
        st.divider()
        
        query_gantt = text("""
                SELECT n.nombres || ' ' || n.apellidos as Alumno, 
                       c.nombre_accion as Tarea, 
                       a.estado as Estado, 
                       a.fecha_asignacion as Inicio, 
                       a.fecha_vencimiento as Fin,
                       cu.nivel as Curso,
                       p.nombres || ' ' || p.apellidos as Profesor
                FROM acciones_asignadas a 
                JOIN alumnos n ON a.alumno_id = n.id 
                JOIN catalogo_acciones c ON a.accion_id = c.id
                LEFT JOIN cursos cu ON n.curso_id = cu.id
                LEFT JOIN fichas_alumnos f ON n.id = f.alumno_id
                LEFT JOIN profesores p ON f.profesor_id = p.id
                WHERE a.fecha_vencimiento IS NOT NULL
            """)
        df_gantt = pd.read_sql_query(query_gantt, db.bind)
        if not df_gantt.empty:
            # Convertir a formato fecha para poder comparar y graficar
            df_gantt['Inicio'] = pd.to_datetime(df_gantt['Inicio'])
            df_gantt['Fin'] = pd.to_datetime(df_gantt['Fin'])
            ahora = pd.Timestamp(datetime.now(timezone.utc).replace(tzinfo=None))
            
            # Llenar nulos por si algún alumno no tiene profesor o curso asignado
            df_gantt['Curso'] = df_gantt['Curso'].fillna('Sin Curso')
            df_gantt['Profesor'] = df_gantt['Profesor'].fillna('Sin Asignar')

            st.markdown("**🔍 Filtros del Cronograma:**")
            col_f1, col_f2 = st.columns(2)
            cursos_disp = ["Todos"] + sorted(df_gantt["Curso"].unique().tolist())
            profes_disp = ["Todos"] + sorted(df_gantt["Profesor"].unique().tolist())

            filtro_curso_g = col_f1.selectbox("Filtrar por Curso", cursos_disp, key="gantt_curso")
            filtro_profe_g = col_f2.selectbox("Filtrar por Profesor(a)", profes_disp, key="gantt_profe")

            if filtro_curso_g != "Todos":
                df_gantt = df_gantt[df_gantt["Curso"] == filtro_curso_g]
            if filtro_profe_g != "Todos":
                df_gantt = df_gantt[df_gantt["Profesor"] == filtro_profe_g]

            if not df_gantt.empty:
                # Lógica para detectar si una tarea está atrasada
                df_gantt['Estado Actual'] = df_gantt.apply(lambda row: 'Atrasada' if row['Fin'] < ahora and row['Estado'] != 'Completada' else row['Estado'], axis=1)
                df_gantt['Etiqueta'] = df_gantt['Alumno'] + " - " + df_gantt['Tarea']
                
                # Mapeo estricto de colores
                color_map = {'Pendiente': '#FFC107', 'En Proceso': '#00BFFF', 'Completada': '#00FF00', 'Atrasada': '#FF0000'}
                fig_gantt = px.timeline(df_gantt, x_start="Inicio", x_end="Fin", y="Etiqueta", color="Estado Actual", color_discrete_map=color_map)
                fig_gantt.update_yaxes(autorange="reversed") # Invierte el eje Y para ver la primera tarea arriba
                fig_gantt.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E0E0'), height=600)
                st.plotly_chart(fig_gantt, use_container_width=True)
            else:
                st.info("No hay tareas que coincidan con los filtros seleccionados.")
        else:
            st.info("No hay tareas asignadas con fecha de vencimiento para generar el cronograma.")

    elif vista_seleccionada == "Directorio y Asignaciones":
        st.title("📝 Directorio PIE y Asignación de Casos")
        
        profesores_db = db.query(Profesor).all()
        medicos_db = db.query(Medico).all()
        especialistas_db = db.query(Especialista).all()
        diagnosticos_db = db.query(Diagnostico).all()

        opciones_prof = {p.id: f"{p.nombres} {p.apellidos}" for p in profesores_db}
        opciones_med = {m.id: f"{m.nombre} ({m.especialidad.value})" for m in medicos_db}
        opciones_esp = {e.id: f"{e.nombres} {e.apellidos}" for e in especialistas_db}
        opciones_diag = {d.id: f"{d.tipo.upper()} ({d.categoria.value})" for d in diagnosticos_db}

        st.subheader("Directorio y Métricas de Alumnos")
        alumnos_registrados = db.query(Alumno).all()
        if alumnos_registrados:
            # 1. Pre-procesar los datos en una lista
            datos_dir = []
            for a in alumnos_registrados:
                curso = db.query(Curso).filter(Curso.id == a.curso_id).first()
                ne = db.query(NecesidadEducativa).filter(NecesidadEducativa.alumno_id == a.id).first()
                diag = db.query(Diagnostico).filter(Diagnostico.id == ne.diagnostico_id).first() if ne else None
                ficha = db.query(FichaAlumno).filter(FichaAlumno.alumno_id == a.id).first()
                profe = db.query(Profesor).filter(Profesor.id == ficha.profesor_id).first() if ficha and ficha.profesor_id else None
                med = db.query(Medico).filter(Medico.id == ficha.medico_id).first() if ficha and ficha.medico_id else None
                
                profe_str = f"{profe.nombres} {profe.apellidos}" if profe else "Sin Asignar"
                med_str = med.nombre if med else "Sin Asignar"
                datos_dir.append({"RUT": a.rut, "Nombre": f"{a.nombres} {a.apellidos}", "Curso": curso.nivel if curso else "N/A", "Perfil": diag.tipo.upper() if diag else "Sin especificar", "Profesor": profe_str, "Médico": med_str})
            
            df_directorio = pd.DataFrame(datos_dir)
            
            # 2. Agregar UI de Filtros de Búsqueda
            st.markdown("**🔍 Filtros de Búsqueda:**")
            f_col1, f_col2, f_col3 = st.columns(3)
            cursos_disp = ["Todos"] + sorted(df_directorio["Curso"].unique().tolist())
            diag_disp = ["Todos"] + sorted(df_directorio["Perfil"].unique().tolist())
            
            filtro_nombre = f_col1.text_input("Buscar por Nombre o RUT", "")
            filtro_curso = f_col2.selectbox("Filtrar por Curso", cursos_disp)
            filtro_diag = f_col3.selectbox("Filtrar por Diagnóstico", diag_disp)
            
            # Aplicar filtros si el usuario selecciona algo distinto a "Todos"
            if filtro_nombre.strip():
                df_directorio = df_directorio[df_directorio["Nombre"].str.contains(filtro_nombre, case=False, na=False) | df_directorio["RUT"].str.contains(filtro_nombre, case=False, na=False)]
            if filtro_curso != "Todos":
                df_directorio = df_directorio[df_directorio["Curso"] == filtro_curso]
            if filtro_diag != "Todos":
                df_directorio = df_directorio[df_directorio["Perfil"] == filtro_diag]
                
            # 3. Mostrar Resultados Dinámicos
            if not df_directorio.empty:
                tab_lista, tab_grafica = st.tabs(["📋 Lista Detallada", "📊 Gráfica de Distribución"])
                
                with tab_lista:
                    st.markdown(f"**Alumnos encontrados: {len(df_directorio)}**")
                    st.dataframe(df_directorio, hide_index=True, use_container_width=True)
                    
                with tab_grafica:
                    df_perfiles = df_directorio[['Perfil']].copy()
                    df_conteo = df_perfiles.value_counts().reset_index()
                    df_conteo.columns = ['Perfil', 'Cantidad']
                    fig_perfiles = px.pie(df_conteo, values='Cantidad', names='Perfil', hole=0.4, title="Distribución Diagnóstica", color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_perfiles.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E0E0'))
                    st.plotly_chart(fig_perfiles, use_container_width=True)
            else:
                st.info("Ningún alumno coincide con los filtros seleccionados.")
                
        st.divider()
        st.subheader("🗂️ Fichas Individuales PIE (Vista y Exportación)")
        # Usamos el dataframe ya filtrado para el selector de edición
        if not df_directorio.empty:
            # Creamos un diccionario a partir del dataframe filtrado para el selectbox
            alumnos_filtrados = db.query(Alumno).filter(Alumno.rut.in_(df_directorio['RUT'].tolist())).all()
            
            opciones_fichas = {a.id: f"{a.nombres} {a.apellidos} ({a.rut})" for a in alumnos_filtrados}
            ficha_sel_id = st.selectbox("Seleccione un alumno para visualizar su ficha clínica y pedagógica:", options=list(opciones_fichas.keys()), format_func=lambda x: opciones_fichas[x])
            
            if ficha_sel_id:
                alumno_ficha = db.query(Alumno).filter(Alumno.id == ficha_sel_id).first()
                ficha_data = db.query(FichaAlumno).filter(FichaAlumno.alumno_id == ficha_sel_id).first()
                curso_data = db.query(Curso).filter(Curso.id == alumno_ficha.curso_id).first()
                ne_data = db.query(NecesidadEducativa).filter(NecesidadEducativa.alumno_id == ficha_sel_id).first()
                diag_data = db.query(Diagnostico).filter(Diagnostico.id == ne_data.diagnostico_id).first() if ne_data else None
                
                profe_data = db.query(Profesor).filter(Profesor.id == ficha_data.profesor_id).first() if ficha_data and ficha_data.profesor_id else None
                med_data = db.query(Medico).filter(Medico.id == ficha_data.medico_id).first() if ficha_data and ficha_data.medico_id else None
                esp_data = db.query(Especialista).filter(Especialista.id == ficha_data.especialista_id).first() if ficha_data and ficha_data.especialista_id else None
                
                hist_evals = db.query(TestEvaluacion).filter(TestEvaluacion.alumno_id == ficha_sel_id).order_by(TestEvaluacion.fecha_evaluacion.desc()).all()
                
                profe_str = f"{profe_data.nombres} {profe_data.apellidos}" if profe_data else 'Sin asignar'
                med_str = f"{med_data.nombre} ({med_data.especialidad.value})" if med_data else 'Sin asignar'
                esp_str = f"{esp_data.nombres} {esp_data.apellidos} ({esp_data.tipo.value})" if esp_data else 'Sin asignar'

                with st.container():
                    c_info1, c_info2 = st.columns(2)
                    c_info1.markdown(f"**RUT:** {alumno_ficha.rut}\n\n**Nombre Social:** {ficha_data.nombre_social if ficha_data and ficha_data.nombre_social else 'N/A'}\n\n**Curso:** {curso_data.nivel if curso_data else 'N/A'}\n\n**Alergias / Condiciones:** {ficha_data.alergias_condiciones if ficha_data and ficha_data.alergias_condiciones else 'Ninguna registrada'}")
                    c_info2.markdown(f"**Diagnóstico Principal:** {diag_data.tipo.upper() if diag_data else 'No registrado'} ({diag_data.categoria.value if diag_data else ''})\n\n**Fecha Última Evaluación:** {ficha_data.fecha_evaluaciones.strftime('%Y-%m-%d') if ficha_data and ficha_data.fecha_evaluaciones else 'N/A'}")
                    
                    st.markdown("#### Equipo Profesional a Cargo")
                    c_eq1, c_eq2, c_eq3 = st.columns(3)
                    c_eq1.info(f"**Profesor(a) PIE:**\n\n{profe_str}")
                    c_eq2.warning(f"**Médico Tratante:**\n\n{med_str}")
                    c_eq3.success(f"**Especialista Asignado:**\n\n{esp_str}")
                
                    html_print = f"""
                    <html>
                    <head>
                        <title>Ficha PIE - {alumno_ficha.nombres} {alumno_ficha.apellidos}</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; padding: 20px; color: #333; background-color: #fff; }}
                            .no-print {{ text-align: center; margin-bottom: 20px; }}
                            .btn-print {{ background-color: #FF00FF; color: white; padding: 12px 24px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                            .btn-print:hover {{ background-color: #d900d9; }}
                            .header {{ text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; }}
                            .section {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background: #f9f9f9; }}
                            h2, h3 {{ color: #2c3e50; margin-top: 0; }}
                            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                            th, td {{ border: 1px solid #aaa; padding: 8px; text-align: left; }}
                            th {{ background-color: #eee; }}
                            @media print {{
                                .no-print {{ display: none; }}
                                body {{ padding: 0; }}
                                .section {{ page-break-inside: avoid; background: #fff; border: 1px solid #000; }}
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="no-print">
                            <button class="btn-print" onclick="window.print()">🖨️ Imprimir / Guardar en PDF</button>
                        </div>
                        <div class="header">
                            <h1>Programa de Integración Escolar (PIE)</h1>
                            <h2>Ficha Clínica y Pedagógica</h2>
                        </div>
                        <div class="section">
                            <h3>Datos del Alumno</h3>
                            <p><strong>Nombre Oficial:</strong> {alumno_ficha.nombres} {alumno_ficha.apellidos} &nbsp; | &nbsp; <strong>RUT:</strong> {alumno_ficha.rut}</p>
                            <p><strong>Nombre Social:</strong> {ficha_data.nombre_social if ficha_data and ficha_data.nombre_social else 'N/A'} &nbsp; | &nbsp; <strong>Curso:</strong> {curso_data.nivel if curso_data else 'N/A'}</p>
                            <p><strong>Alergias o Condiciones Médicas:</strong> {ficha_data.alergias_condiciones if ficha_data and ficha_data.alergias_condiciones else 'Ninguna registrada'}</p>
                        </div>
                        <div class="section">
                            <h3>Diagnóstico y Equipo a Cargo</h3>
                            <p><strong>Diagnóstico PIE:</strong> {diag_data.tipo.upper() if diag_data else 'No registrado'} ({diag_data.categoria.value if diag_data else ''})</p>
                            <p><strong>Profesor(a) a Cargo:</strong> {profe_str}</p>
                            <p><strong>Médico Tratante:</strong> {med_str}</p>
                            <p><strong>Especialista de Apoyo:</strong> {esp_str}</p>
                        </div>
                        <div class="section">
                            <h3>Historial de Evaluaciones Estandarizadas</h3>
                            <table>
                                <tr><th>Fecha</th><th>Test Realizado</th><th>Puntuación</th><th>Observaciones</th></tr>
                                {''.join([f"<tr><td>{e.fecha_evaluacion.strftime('%Y-%m-%d')}</td><td>{e.tipo_test}</td><td>{e.puntuacion}</td><td>{e.observaciones}</td></tr>" for e in hist_evals]) if hist_evals else "<tr><td colspan='4'>No hay evaluaciones registradas.</td></tr>"}
                            </table>
                        </div>
                    </body>
                    </html>
                    """
                    st.divider()
                    if st.button("👁️ Visualizar Ficha", type="primary"):
                        st.markdown("### 📄 Previsualización de la Ficha")
                        components.html(html_print, height=600, scrolling=True)
                        
            st.divider()
            with st.expander("✏️ Editar Datos del Alumno y Asignaciones"):
                st.markdown("### Selecciona el alumno que deseas modificar")
                edit_sel_id = st.selectbox("🔎 Buscar alumno por Nombre o RUT:", options=list(opciones_fichas.keys()), format_func=lambda x: opciones_fichas[x], key="edit_selectbox")
                
                if edit_sel_id:
                    alumno_edit = db.query(Alumno).filter(Alumno.id == edit_sel_id).first()
                    ficha_edit = db.query(FichaAlumno).filter(FichaAlumno.alumno_id == edit_sel_id).first()
                    curso_edit = db.query(Curso).filter(Curso.id == alumno_edit.curso_id).first()
                    ne_edit = db.query(NecesidadEducativa).filter(NecesidadEducativa.alumno_id == edit_sel_id).first()
                    diag_edit = db.query(Diagnostico).filter(Diagnostico.id == ne_edit.diagnostico_id).first() if ne_edit else None
                    
                    profe_edit = db.query(Profesor).filter(Profesor.id == ficha_edit.profesor_id).first() if ficha_edit and ficha_edit.profesor_id else None
                    med_edit = db.query(Medico).filter(Medico.id == ficha_edit.medico_id).first() if ficha_edit and ficha_edit.medico_id else None
                    esp_edit = db.query(Especialista).filter(Especialista.id == ficha_edit.especialista_id).first() if ficha_edit and ficha_edit.especialista_id else None

                    with st.form(key=f"edit_form_{edit_sel_id}"):
                        col_e1, col_e2 = st.columns(2)
                        edit_rut = col_e1.text_input("RUT", value=alumno_edit.rut)
                        edit_nombres = col_e1.text_input("Nombres", value=alumno_edit.nombres)
                        edit_apellidos = col_e2.text_input("Apellidos", value=alumno_edit.apellidos)
                        edit_nombre_social = col_e2.text_input("Nombre Social", value=ficha_edit.nombre_social if ficha_edit and ficha_edit.nombre_social else "")
                        edit_curso = col_e1.text_input("Curso", value=curso_edit.nivel if curso_edit else "")
                        edit_alergias = st.text_area("Alergias o Condiciones Médicas", value=ficha_edit.alergias_condiciones if ficha_edit and ficha_edit.alergias_condiciones else "")
                        
                        st.markdown("**Actualizar Equipo Asignado**")
                        c_e1, c_e2, c_e3, c_e4 = st.columns(4)
                        
                        prof_keys = list(opciones_prof.keys())
                        idx_prof = prof_keys.index(profe_edit.id) if (profe_edit and profe_edit.id in prof_keys) else 0
                        med_keys = list(opciones_med.keys())
                        idx_med = med_keys.index(med_edit.id) if (med_edit and med_edit.id in med_keys) else 0
                        esp_keys = list(opciones_esp.keys())
                        idx_esp = esp_keys.index(esp_edit.id) if (esp_edit and esp_edit.id in esp_keys) else 0
                        diag_keys = list(opciones_diag.keys())
                        idx_diag = diag_keys.index(diag_edit.id) if (diag_edit and diag_edit.id in diag_keys) else 0
                        
                        edit_profe_id = c_e1.selectbox("Profesor(a)", options=prof_keys, format_func=lambda x: opciones_prof[x], index=idx_prof) if prof_keys else None
                        edit_med_id = c_e2.selectbox("Médico", options=med_keys, format_func=lambda x: opciones_med[x], index=idx_med) if med_keys else None
                        edit_esp_id = c_e3.selectbox("Especialista", options=esp_keys, format_func=lambda x: opciones_esp[x], index=idx_esp) if esp_keys else None
                        edit_diag_id = c_e4.selectbox("Diagnóstico", options=diag_keys, format_func=lambda x: opciones_diag[x], index=idx_diag) if diag_keys else None
                        
                        if st.form_submit_button("💾 Guardar Cambios"):
                            alumno_edit.rut = edit_rut
                            alumno_edit.nombres = edit_nombres
                            alumno_edit.apellidos = edit_apellidos
                            
                            curso_obj = db.query(Curso).filter(Curso.nivel == edit_curso).first()
                            if not curso_obj:
                                curso_obj = Curso(nivel=edit_curso)
                                db.add(curso_obj)
                                db.commit()
                                db.refresh(curso_obj)
                            alumno_edit.curso_id = curso_obj.id
                            
                            if ficha_edit:
                                ficha_edit.rut = edit_rut
                                ficha_edit.nombre_social = edit_nombre_social
                                ficha_edit.profesor_id = edit_profe_id
                                ficha_edit.medico_id = edit_med_id
                                ficha_edit.especialista_id = edit_esp_id
                                ficha_edit.alergias_condiciones = edit_alergias
                                
                            if ne_edit:
                                ne_edit.diagnostico_id = edit_diag_id
                            elif edit_diag_id:
                                db.add(NecesidadEducativa(alumno_id=alumno_edit.id, diagnostico_id=edit_diag_id))
                                
                            db.commit()
                            st.success("¡Datos actualizados correctamente!")
                            st.rerun()
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
            st.dataframe(df_acciones, use_container_width=True, hide_index=True)
        else:
            st.info("No hay acciones registradas en el catálogo.")
            if st.button("📚 Cargar Estrategias Predeterminadas"):
                from seed import seed_data
                with st.spinner("Cargando el catálogo base..."):
                    seed_data()
                st.rerun()

    elif vista_seleccionada == "Test y Evaluaciones":
        st.title("📋 Evaluaciones Psicométricas y Cognitivas")
        st.markdown("Registra y consulta los resultados de tests estandarizados de los alumnos.")
        tab1, tab2 = st.tabs(["✏️ Registrar Nuevo Test", "📊 Historial de Evaluaciones"])
        with tab1:
            st.subheader("Registrar Resultado de Evaluación")
            alumnos_registrados = db.query(Alumno).all()
            if alumnos_registrados:
                with st.form("nuevo_test_form", clear_on_submit=True):
                    opciones_alumnos = {a.id: f"{a.nombres} {a.apellidos}" for a in alumnos_registrados}
                    nino_id_seleccionado = st.selectbox("Seleccione un Alumno", options=list(opciones_alumnos.keys()), format_func=lambda x: opciones_alumnos[x])
                    tipo_test = st.selectbox("Tipo de Test", ["ECEP (Escala de Comportamiento Preescolar)", "Test de Atención de Conners", "WISC-V (Inteligencia)", "PROLEC-R (Lectura)", "Otro"])
                    puntuacion = st.number_input("Puntuación Total / Percentil", min_value=0.0, step=0.5)
                    observaciones = st.text_area("Observaciones Clínicas / Notas del Docente")
                    submitted = st.form_submit_button("Guardar Evaluación")
                    if submitted:
                        if not observaciones:
                            st.error("Por favor, ingresa las observaciones o notas de la evaluación.")
                        else:
                            nueva_evaluacion = TestEvaluacion(alumno_id=nino_id_seleccionado, tipo_test=tipo_test, puntuacion=puntuacion, observaciones=observaciones)
                            db.add(nueva_evaluacion)
                            db.commit()
                            st.success(f"¡Evaluación '{tipo_test}' guardada exitosamente para {opciones_alumnos[nino_id_seleccionado]}!")
            else:
                st.warning("Debe registrar al menos un alumno en 'Directorio' antes de guardar evaluaciones.")
        with tab2:
            st.subheader("Registro Histórico")
            evaluaciones = db.query(TestEvaluacion).all()
            if evaluaciones:
                query = text("SELECT n.nombres || ' ' || n.apellidos as Alumno, e.tipo_test as 'Test Realizado', e.puntuacion as Puntuación, e.observaciones as Observaciones, e.fecha_evaluacion as Fecha FROM evaluaciones e JOIN alumnos n ON e.alumno_id = n.id ORDER BY e.fecha_evaluacion DESC")
                df_evals = pd.read_sql_query(query, db.bind)
                st.dataframe(df_evals, use_container_width=True, hide_index=True)
            else:
                st.info("No hay evaluaciones registradas en el sistema todavía.")

    elif vista_seleccionada == "Gestión de Usuarios y Accesos":
        st.title("🔐 Gestión de Usuarios y Accesos")
        st.markdown("Administra cuentas de acceso, da de alta a nuevos alumnos PIE y gestiona al equipo de Profesionales.")
        
        tab_crear, tab_alumno, tab_prof, tab_med, tab_esp, tab_lista = st.tabs(["🔑 Cuentas Web", "👦 Alumnos PIE", "📚 Profesores", "🩺 Médicos", "🧩 Especialistas", "📋 Analítica y Permisos"])
        
        with tab_crear:
            with st.form("new_user_form_admin", clear_on_submit=True):
                st.subheader("Crear Cuenta de Usuario")
                st.caption("Se generará una clave inicial automática que expirará en 24 horas.")
                new_rol = st.selectbox("Tipo de Cuenta", ["Profesor", "Admin"])
                new_rut = st.text_input("RUT / Usuario")
                new_email = st.text_input("Correo Electrónico (Opcional)")
                submit_user = st.form_submit_button("Crear y Enviar Accesos")
                
                if submit_user:
                    if not new_rut:
                        st.error("Por favor, ingresa el RUT / Usuario.")
                    elif new_rol == "Profesor" and not validar_rut(new_rut):
                        st.error("RUT inválido. Para profesores usa el formato 12345678-9.")
                    elif new_email and not validar_correo(new_email):
                        st.error("El formato del correo electrónico es inválido.")
                    else:
                        existe_rut = db.query(UsuarioWeb).filter(UsuarioWeb.username == new_rut).first()
                        existe_correo = db.query(UsuarioWeb).filter(UsuarioWeb.email == new_email).first() if new_email else None
                        
                        if existe_rut:
                            st.error("Ya existe una cuenta con este nombre de usuario o RUT.")
                        elif existe_correo:
                            st.error("Este correo electrónico ya está registrado en otra cuenta.")
                        else:
                            try:
                                temp_pwd = str(random.randint(10000, 99999))
                                nuevo_usuario = UsuarioWeb(
                                    username=new_rut, 
                                    email=new_email if new_email else None,
                                    password=temp_pwd, 
                                    rol=new_rol,
                                    must_change_password=True,
                                    account_expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)
                                )
                                db.add(nuevo_usuario)
                                db.commit()
                                st.success(f"Cuenta de {new_rol} para '{new_rut}' creada exitosamente.")
                                
                                asunto = "Acceso Creado - NeuroForge"
                                cuerpo = f"Hola,\n\nEl Administrador ha creado tu cuenta de {new_rol}.\nUsuario: {new_rut}\nClave temporal: {temp_pwd}\n\nIngresa al portal para cambiar tu clave.\n\nSaludos."
                                if enviar_correo_real(new_email, asunto, cuerpo):
                                    st.info(f"📧 Correo con clave inicial enviado a {new_email}")
                                if new_email:
                                    asunto = "Acceso Creado - NeuroForge"
                                    cuerpo = f"Hola,\n\nEl Administrador ha creado tu cuenta de {new_rol}.\nUsuario: {new_rut}\nClave temporal: {temp_pwd}\n\nIngresa al portal para cambiar tu clave.\n\nSaludos."
                                    if enviar_correo_real(new_email, asunto, cuerpo):
                                        st.info(f"📧 Correo con clave inicial enviado a {new_email}")
                                    else:
                                        st.warning(f"⚠️ Cuenta creada, pero falta configurar el servidor SMTP. Entrégale esta clave al usuario: {temp_pwd}")
                                else:
                                    st.warning(f"⚠️ Cuenta creada, pero falta configurar el servidor SMTP. Entrégale esta clave al usuario: {temp_pwd}")
                                    st.warning(f"⚠️ Cuenta creada sin correo. Entrégale esta clave temporal al usuario: {temp_pwd}")
                            except Exception as e:
                                db.rollback()
                                st.error("Ocurrió un error en la base de datos al crear la cuenta. Por favor, intenta nuevamente.")
        
        with tab_alumno:
            st.subheader("Añadir Nuevo Alumno")
            profesores_db_g = db.query(Profesor).all()
            medicos_db_g = db.query(Medico).all()
            especialistas_db_g = db.query(Especialista).all()
            diagnosticos_db_g = db.query(Diagnostico).all()

            with st.form("nuevo_alumno_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                rut_nuevo = col1.text_input("RUT del Alumno (Ej: 12345678-9)")
                nombre_nuevo = col2.text_input("Nombre completo (Nombres y Apellidos)")
                nombre_social = col1.text_input("Nombre Social")
                curso_nuevo = col2.text_input("Curso (Ej: 3ro Básico)")
                alergias_nuevo = st.text_area("Alergias o Condiciones Médicas (Opcional)")
                
                st.markdown("**Equipo Asignado y Diagnóstico**")
                c1, c2, c3, c4 = st.columns(4)
                
                opciones_prof_g = {p.id: f"{p.nombres} {p.apellidos}" for p in profesores_db_g}
                opciones_med_g = {m.id: f"{m.nombre} ({m.especialidad.value})" for m in medicos_db_g}
                opciones_esp_g = {e.id: f"{e.nombres} {e.apellidos}" for e in especialistas_db_g}
                opciones_diag_g = {d.id: f"{d.tipo.upper()} ({d.categoria.value})" for d in diagnosticos_db_g}

                profe_id = c1.selectbox("Profesor(a)", options=list(opciones_prof_g.keys()), format_func=lambda x: opciones_prof_g[x]) if opciones_prof_g else None
                med_id = c2.selectbox("Médico", options=list(opciones_med_g.keys()), format_func=lambda x: opciones_med_g[x]) if opciones_med_g else None
                esp_id = c3.selectbox("Especialista", options=list(opciones_esp_g.keys()), format_func=lambda x: opciones_esp_g[x]) if opciones_esp_g else None
                diag_id = c4.selectbox("Diagnóstico", options=list(opciones_diag_g.keys()), format_func=lambda x: opciones_diag_g[x]) if opciones_diag_g else None
                
                submitted = st.form_submit_button("Añadir Alumno")
                if submitted:
                    if not rut_nuevo or not nombre_nuevo or not curso_nuevo:
                        st.error("Por favor, completa todos los campos obligatorios del alumno.")
                    elif not validar_rut(rut_nuevo):
                        st.error("El RUT del alumno es inválido (formato: 12345678-9).")
                    else:
                        existe_alumno = db.query(Alumno).filter(Alumno.rut == rut_nuevo).first()
                        if existe_alumno:
                            st.error("Ya existe un alumno registrado con este RUT.")
                        else:
                            curso_obj = db.query(Curso).filter(Curso.nivel == curso_nuevo).first()
                            if not curso_obj:
                                curso_obj = Curso(nivel=curso_nuevo)
                                db.add(curso_obj)
                                db.commit()
                                db.refresh(curso_obj)
                            nombres_split = nombre_nuevo.split(" ", 1)
                            nombres = nombres_split[0]
                            apellidos = nombres_split[1] if len(nombres_split) > 1 else ""
                            nuevo_nino = Alumno(rut=rut_nuevo, nombres=nombres, apellidos=apellidos, curso_id=curso_obj.id)
                            db.add(nuevo_nino)
                            db.commit()
                            db.refresh(nuevo_nino)
                            
                            nueva_ficha = FichaAlumno(alumno_id=nuevo_nino.id, rut=rut_nuevo, nombre_social=nombre_social, fecha_evaluaciones=datetime.now(timezone.utc), profesor_id=profe_id, medico_id=med_id, especialista_id=esp_id, alergias_condiciones=alergias_nuevo)
                            db.add(nueva_ficha)
                            
                            if diag_id:
                                db.add(NecesidadEducativa(alumno_id=nuevo_nino.id, diagnostico_id=diag_id))
                            db.commit()
                            st.success(f"¡Alumno '{nombre_nuevo}' añadido y ficha PIE creada correctamente!")

        with tab_prof:
            with st.form("form_profesor", clear_on_submit=True):
                st.subheader("Registrar Profesor(a)")
                col1, col2 = st.columns(2)
                rut_prof = col1.text_input("RUT (Ej: 12345678-9)")
                reg_prof = col2.text_input("Registro MINEDUC")
                nom_prof = col1.text_input("Nombres")
                ape_prof = col2.text_input("Apellidos")
                if st.form_submit_button("Guardar Profesor"):
                    if not rut_prof or not nom_prof or not ape_prof:
                        st.error("RUT, Nombres y Apellidos son obligatorios.")
                    else:
                        if db.query(Profesor).filter(Profesor.rut == rut_prof).first():
                            st.error("Ya existe un Profesor registrado con este RUT.")
                        else:
                            db.add(Profesor(rut=rut_prof, nombres=nom_prof, apellidos=ape_prof, registro=reg_prof))
                            db.commit()
                            st.success("¡Profesor registrado exitosamente!")
            st.divider()
            st.subheader("Directorio Docente")
            profesores = db.query(Profesor).all()
            if profesores:
                st.dataframe(pd.DataFrame([{"RUT": p.rut, "Nombres": p.nombres, "Apellidos": p.apellidos, "Registro": p.registro} for p in profesores]), hide_index=True, use_container_width=True)
            else:
                st.info("No hay profesores registrados.")

        with tab_med:
            with st.form("form_medico", clear_on_submit=True):
                st.subheader("Registrar Médico Evaluador")
                col1, col2 = st.columns(2)
                rut_med = col1.text_input("RUT Médico")
                nom_med = col2.text_input("Nombre Completo (Ej: Dr. Juan Pérez)")
                esp_med = st.selectbox("Especialidad", [e.value for e in EspecialidadMedico])
                if st.form_submit_button("Guardar Médico"):
                    if not rut_med or not nom_med:
                        st.error("Todos los campos son obligatorios.")
                    else:
                        if db.query(Medico).filter(Medico.rut == rut_med).first():
                            st.error("Ya existe un Médico con este RUT.")
                        else:
                            db.add(Medico(rut=rut_med, nombre=nom_med, especialidad=EspecialidadMedico(esp_med)))
                            db.commit()
                            st.success("¡Médico registrado exitosamente!")
            st.divider()
            st.subheader("Directorio Médico")
            medicos = db.query(Medico).all()
            if medicos:
                st.dataframe(pd.DataFrame([{"RUT": m.rut, "Nombre": m.nombre, "Especialidad": m.especialidad.value} for m in medicos]), hide_index=True, use_container_width=True)
            else:
                st.info("No hay médicos registrados.")

        with tab_esp:
            with st.form("form_especialista", clear_on_submit=True):
                st.subheader("Registrar Especialista PIE")
                col1, col2 = st.columns(2)
                rut_esp = col1.text_input("RUT Especialista")
                reg_esp = col2.text_input("Registro Profesional")
                nom_esp = col1.text_input("Nombres")
                ape_esp = col2.text_input("Apellidos")
                tipo_esp = st.selectbox("Tipo de Especialista", [e.value for e in TipoEspecialista])
                if st.form_submit_button("Guardar Especialista"):
                    if not rut_esp or not nom_esp or not ape_esp:
                        st.error("RUT, Nombres y Apellidos son obligatorios.")
                    else:
                        if db.query(Especialista).filter(Especialista.rut == rut_esp).first():
                            st.error("Ya existe un Especialista con este RUT.")
                        else:
                            db.add(Especialista(rut=rut_esp, nombres=nom_esp, apellidos=ape_esp, registro=reg_esp, tipo=TipoEspecialista(tipo_esp)))
                            db.commit()
                            st.success("¡Especialista registrado exitosamente!")
            st.divider()
            st.subheader("Directorio de Especialistas")
            especialistas = db.query(Especialista).all()
            if especialistas:
                st.dataframe(pd.DataFrame([{"RUT": e.rut, "Nombres": e.nombres, "Apellidos": e.apellidos, "Registro": e.registro, "Tipo": e.tipo.value} for e in especialistas]), hide_index=True, use_container_width=True)
            else:
                st.info("No hay especialistas registrados.")

        with tab_lista:
            st.subheader("Analítica y Control de Usuarios")
            usuarios_unicos = db.query(UsuarioWeb).filter(UsuarioWeb.username != "admin").all()
        
            if usuarios_unicos:
                for usuario in usuarios_unicos:
                    if not usuario.created_at:
                        usuario.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    dias_creacion = (datetime.now(timezone.utc).replace(tzinfo=None) - usuario.created_at).days
                    
                    with st.expander(f"👤 {usuario.username} | Rol: {usuario.rol} | ⏳ Días en sistema: {dias_creacion}"):
                        st.write(f"**Correo:** {usuario.email}")
                        estado_cuenta = "Caducada" if usuario.must_change_password and usuario.account_expires_at and datetime.utcnow() > usuario.account_expires_at else "Pendiente de Cambio" if usuario.must_change_password else "Activa"
                        st.write(f"**Estado:** {estado_cuenta}")
                        
                        if usuario.rol == "Profesor":
                            alumnos_ids = [n.id for n in db.query(Alumno).all()]
                            pendientes = db.query(AccionAsignada).filter(AccionAsignada.alumno_id.in_(alumnos_ids), AccionAsignada.estado == "Pendiente").count() if alumnos_ids else 0
                            en_proceso = db.query(AccionAsignada).filter(AccionAsignada.alumno_id.in_(alumnos_ids), AccionAsignada.estado == "En Proceso").count() if alumnos_ids else 0
                            asignadas_total = db.query(AccionAsignada).filter(AccionAsignada.alumno_id.in_(alumnos_ids)).count() if alumnos_ids else 0
                            
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
                            
                        if col_btn2.button("🔄 Resetear Clave", key=f"reset_{usuario.id}"):
                            temp_pwd = str(random.randint(10000, 99999))
                            usuario.password = temp_pwd
                            usuario.must_change_password = True
                            usuario.account_expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)
                            db.commit()
                            st.success(f"Clave temporal generada exitosamente para {usuario.username}: **{temp_pwd}**")
                            if usuario.email:
                                asunto = "NeuroForge - Clave Reseteada por Administrador"
                                cuerpo = f"Hola,\n\nEl administrador ha reseteado tu acceso.\nTu nueva clave temporal es: {temp_pwd}\n\nRecuerda cambiarla al iniciar sesión.\n\nSaludos."
                                enviar_correo_real(usuario.email, asunto, cuerpo)
                        
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
            query_ninos = db.query(Alumno)
            df_ninos = pd.read_sql(query_ninos.statement, db.bind)
            if not df_ninos.empty:
                df_ninos["nombre"] = df_ninos["nombres"] + " " + df_ninos["apellidos"]
            df_progreso = pd.read_sql(db.query(Progreso).statement, db.bind)
            if not df_progreso.empty and not df_ninos.empty:
                df_full = pd.merge(df_progreso, df_ninos, left_on="alumno_id", right_on="id")
                st.sidebar.header("Filtros del Dashboard")
                nino_seleccionado = st.sidebar.selectbox("Seleccione un Alumno", df_ninos["nombre"].tolist())
                datos_alumno = df_full[df_full["nombre"] == nino_seleccionado].copy()
                if not datos_alumno.empty:
                    datos_alumno['fecha_sesion'] = pd.to_datetime(datos_alumno['fecha_sesion'])
                    datos_alumno = datos_alumno.sort_values('fecha_sesion')
                    nino_id_actual = int(datos_alumno.iloc[0]['alumno_id'])
                    
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
                            fecha_venc = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=dias_duracion)
                            nueva_asignacion = AccionAsignada(alumno_id=nino_id_actual, accion_id=accion_seleccionada, fecha_vencimiento=fecha_venc)
                            db.add(nueva_asignacion)
                            db.commit()
                            st.success("Acción asignada exitosamente para la próxima sesión.")
                    else:
                        st.info("El catálogo está vacío. Ve al 'Catálogo Pedagógico' para agregar acciones.")
                    
                    asignadas = db.query(AccionAsignada).filter(AccionAsignada.alumno_id == nino_id_actual, AccionAsignada.estado == "Pendiente").all()
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
                                    
                    completadas = db.query(AccionAsignada).filter(AccionAsignada.alumno_id == nino_id_actual, AccionAsignada.estado == "Completada").order_by(AccionAsignada.fecha_asignacion.desc()).all()
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
        alumnos_ids = [n.id for n in db.query(Alumno).all()]
        if alumnos_ids:
            asignadas = db.query(AccionAsignada).filter(AccionAsignada.alumno_id.in_(alumnos_ids), AccionAsignada.estado.in_(["Pendiente", "En Proceso"])).all()
            col1, col2 = st.columns(2)
            col1.metric("Alumnos a cargo", len(alumnos_ids))
            col2.metric("Tareas Pendientes totales", len(asignadas))
            st.divider()
            if asignadas:
                for asig in asignadas:
                    nino = db.query(Alumno).filter(Alumno.id == asig.alumno_id).first()
                    curso_obj = db.query(Curso).filter(Curso.id == nino.curso_id).first()
                    curso_nivel = curso_obj.nivel if curso_obj else "Sin curso"
                    accion = db.query(CatalogoAcciones).filter(CatalogoAcciones.id == asig.accion_id).first()
                    
                    # Cálculo de caducidad y alertas
                    dias_restantes = (asig.fecha_vencimiento - datetime.now(timezone.utc).replace(tzinfo=None)).days if asig.fecha_vencimiento else 99
                    alerta_msg = ""
                    if 0 <= dias_restantes <= 2:
                        alerta_msg = f"\n⚠️ **¡Alerta!** Vence en {dias_restantes} días. *(Correo enviado al profesor)*"
                    
                    estado_color = "🔴" if asig.estado == "Pendiente" else "🟡"
                    c1, c2, c3 = st.columns([2, 4, 1])
                    c1.markdown(f"**👦 {nino.nombres} {nino.apellidos}**\n*{curso_nivel}*\n{estado_color} {asig.estado}")
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
        alumnos = db.query(Alumno).all()
        if alumnos:
            opciones_alumnos = {a.id: f"{a.nombres} {a.apellidos}" for a in alumnos}
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
            nueva_sesion = Sesion(alumno_id=nino_id_checkin, estado_emocional_inicio=emocion_seleccionada)
            db.add(nueva_sesion)
            db.commit()
            st.success(f"¡Gracias por contarnos! Has seleccionado: **{emocion_seleccionada}**")
            st.info(f"**Parámetros enviados al juego:**\n- Velocidad del Motor: `{ajustes['global_speed_modifier']}x`\n- Paleta de Colores: `{ajustes['color_palette'].replace('_', ' ').title()}`")
            if emocion_seleccionada == "Ansioso":
                st.warning("🧠 **Acción Pedagógica:** El motor detectó ansiedad. La velocidad del juego ha disminuido un 40% y se aplicarán colores pastel/suaves.")

finally:
    # El bloque try/finally asegura que la conexión siempre se cierre al terminar el script
    db.close()