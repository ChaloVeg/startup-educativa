import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from database import SessionLocal, UsuarioNiño, Progreso, TestEvaluacion, CatalogoAcciones, AccionAsignada, Sesion, ConfiguracionProfesor
from sqlalchemy import text
from engine import MotorInteligenciaEmocional
from ai_engine import NeuroForgeAI


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
db = SessionLocal()

try:
    # ==========================================
    # CONTROL DE ACCESO Y NAVEGACIÓN LATERAL
    # ==========================================
    st.sidebar.title("Control de Acceso")
    rol_usuario = st.sidebar.selectbox(
        "👤 Seleccione su Perfil:", 
        ["Coordinación PIE (Admin)", "Profesor(a) Especialista", "Modo Alumno (Check-In)"]
    )
    st.sidebar.divider()

    if rol_usuario == "Coordinación PIE (Admin)":
        st.sidebar.markdown("### Menú Administrativo")
        vista_seleccionada = st.sidebar.radio(
            "Navegación:", 
            ["Visión Global PIE", "Directorio y Asignaciones", "Catálogo Pedagógico", "Test y Evaluaciones", "Gestión de Accesos"]
        )

    elif rol_usuario == "Profesor(a) Especialista":
        st.sidebar.markdown("### Menú Docente")
        profesores_db = [r[0] for r in db.query(UsuarioNiño.profesor_asignado).distinct().all() if r[0]]
        if not profesores_db: 
            profesores_db = ["Sin profesores asignados"]
        
        profe_seleccionado = st.sidebar.selectbox("👩‍🏫 Seleccione su cuenta:", profesores_db)
        
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
            if submitted and nombre_nuevo:
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
            if submitted and nombre:
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
        st.title("🔐 Gestión de Accesos para Profesores")
        st.markdown("Controla qué secciones del sistema puede ver cada profesor especialista.")
        
        profesores_unicos = [r[0] for r in db.query(UsuarioNiño.profesor_asignado).distinct().all() if r[0] and r[0] != "Sin asignar"]
        
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
                        if st.button("Asignar a Próxima Sesión"):
                            nueva_asignacion = AccionAsignada(nino_id=nino_id_actual, accion_id=accion_seleccionada)
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
            asignadas = db.query(AccionAsignada).filter(AccionAsignada.nino_id.in_(alumnos_ids), AccionAsignada.estado == "Pendiente").all()
            col1, col2 = st.columns(2)
            col1.metric("Alumnos a cargo", len(alumnos_ids))
            col2.metric("Tareas Pendientes totales", len(asignadas))
            st.divider()
            if asignadas:
                for asig in asignadas:
                    nino = db.query(UsuarioNiño).filter(UsuarioNiño.id == asig.nino_id).first()
                    accion = db.query(CatalogoAcciones).filter(CatalogoAcciones.id == asig.accion_id).first()
                    c1, c2, c3 = st.columns([2, 4, 1])
                    c1.markdown(f"**👦 {nino.nombre}**\n*{nino.curso}*")
                    c2.markdown(f"**{accion.nombre_accion}**\n{accion.descripcion}")
                    if c3.button("Completar", key=f"btn_task_{asig.id}"):
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