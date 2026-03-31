import streamlit as st
import pandas as pd
from datetime import datetime, date
import database as db
import pdf_extractor as pex
import xml_processor as xp
import tax_calculator as tc
import report_generator as rg
import traceback
import plotly.express as px
import io
from st_aggrid import AgGrid, GridOptionsBuilder

# Configuración de página
st.set_page_config(page_title="Sistema Contable de Despacho", page_icon="📈", layout="wide")

# Inicializar Base de Datos
db.init_db()

# Importar módulos de Fase 4 y 5 (DIOT, Conciliación, Portal y IA)
import diot_generator as diot
import bank_reconciliation as br
import polizas_generator as contpaqi
import ai_assistant as ai
import backend_tools as bt
from PIL import Image

import os

# --- Configuración Visual y CSS ---
config = db.obtener_configuracion()
if not config:
    config = {'logo': None, 'c1': '#000000', 'c2': '#FFCC00', 'c3': '#CC0000'}

# Inyectar CSS
st.markdown(f"""
<style>
    /* Colores Personalizados */
    :root {{
        --color-primario: {config['c1']};
        --color-secundario: {config['c2']};
        --color-terciario: {config['c3']};
    }}
    
    .stButton>button {{
        background-color: var(--color-secundario);
        color: var(--color-primario);
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }}
    
    .stButton>button:hover {{
        background-color: var(--color-primario);
        color: white;
        border-color: var(--color-primario);
    }}
    
    .stAlert {{
        border-left: 5px solid var(--color-secundario);
    }}
    
    /* Headers de sidebar */
    [data-testid="stSidebarNav"]::before {{
        content: "Mi Despacho App";
        margin-left: 20px;
        margin-top: 20px;
        font-size: 30px;
        position: relative;
        top: 20px;
        font-weight: bold;
        color: var(--color-primario);
    }}
</style>
""", unsafe_allow_html=True)

# Asegurar que el directorio de archivos existe
ARCHIVOS_DIR = "archivos_clientes"
os.makedirs(ARCHIVOS_DIR, exist_ok=True)

# Gestión de Sesiones para Portal de Clientes y Equipo
if "logged_in_client" not in st.session_state:
    st.session_state.logged_in_client = None

if "logged_in_staff" not in st.session_state:
    st.session_state.logged_in_staff = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Lógica de Autenticación de Equipo (Staff) y Clientes ---
if not st.session_state.logged_in_staff and not st.session_state.logged_in_client:
    st.title("🔐 Acceso al Sistema Contable")
    tab1, tab2 = st.tabs(["Acceso Despacho (Staff)", "Acceso Clientes"])
    
    with tab1:
        st.subheader("Login de Equipo")
        staff_user = st.text_input("Usuario")
        staff_pass = st.text_input("Contraseña", type="password", key="staff_pass")
        if st.button("Ingresar (Staff)"):
            staff_data = db.verificar_login_equipo(staff_user, staff_pass)
            if staff_data:
                st.session_state.logged_in_staff = {
                    'id': staff_data[0], 
                    'nombre': staff_data[1], 
                    'rol': staff_data[2], 
                    'permisos': staff_data[3]
                }
                st.success(f"Bienvenido {staff_data[1]} ({staff_data[2]})")
                st.rerun()
            else:
                st.error("Credenciales de staff incorrectas.")
                
    with tab2:
        st.subheader("Portal del Cliente")
        rfc_login = st.text_input("RFC", key="login_rfc")
        pass_login = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Ingresar (Cliente)"):
            cliente_data = db.verificar_login_cliente(rfc_login, pass_login)
            if cliente_data:
                st.session_state.logged_in_client = {'id': cliente_data[0], 'nombre': cliente_data[1], 'rfc': rfc_login.upper()}
                st.success(f"Bienvenido {cliente_data[1]}")
                st.rerun()
            else:
                st.error("RFC o contraseña incorrectos.")
    st.stop() # Detener ejecución si no hay nadie logueado


# Menú lateral dinámico según quién está logueado
if config and config.get('logo') and os.path.exists(config['logo']):
    st.sidebar.image(config['logo'], use_container_width=True)

st.sidebar.title("Navegación")

if st.session_state.logged_in_client:
    st.sidebar.success(f"Logueado como Cliente: {st.session_state.logged_in_client['nombre']}")
    opciones = ["Mi Portal (Cliente)", "🤖 Asistente Fiscal AI"]
    if st.sidebar.button("Cerrar Sesión"):
         st.session_state.logged_in_client = None
         st.rerun()
elif st.session_state.logged_in_staff:
    staff = st.session_state.logged_in_staff
    st.sidebar.success(f"Logueado como: {staff['nombre']} ({staff['rol']})")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logged_in_staff = None
        st.rerun()
        
    # Usar permisos extraídos de la BD en JSON
    permisos = staff.get('permisos', [])
    
    # Todos los módulos posibles
    todos_modulos = [
        "Mi Despacho (Finanzas)",
        "Gestión de Equipo (Admin)",
        "Configuración de Marca",
        "Dashboard",
        "Agenda y Citas",
        "Facturación (CFDI)",
        "Tablero Kanban (Staff)",
        "Envío de Líneas de Captura",
        "Personas Físicas", 
        "Personas Morales", 
        "Cálculo de Impuestos y XML",
        "Conciliación Bancaria y DIOT",
        "Descarga Masiva SAT (Simulador)",
        "Exportación a CONTPAQi",
        "Calendario General",
        "Expediente de Cliente",
        "Control de Honorarios",
        "Notificaciones a Clientes",
        "🤖 Asistente Fiscal AI"
    ]
    
    # Filtrar solo los que están en los permisos
    opciones = [m for m in todos_modulos if m in permisos]
    
    # Para evitar romper si los permisos fallan (fallback de seguridad)
    if not opciones:
        opciones = ["Dashboard", "Personas Físicas"]

else:
    opciones = []

seleccion = st.sidebar.radio("Ir a:", opciones)

# ---------- Funciones Auxiliares para el Semáforo ----------
def calcular_semaforo(df):
    """Calcula los días restantes y asigna un color al semáforo."""
    if df.empty:
        return df
        
    hoy = date.today()
    df['dias_restantes'] = (df['fecha_limite'] - hoy).dt.days
    
    def asignar_color(row):
        if row['estado'] == 'Completada':
            return '✅ Completada'
        elif row['dias_restantes'] < 0:
            return '🔴 Vencida'
        elif row['dias_restantes'] == 0:
            return '🔴 Vence Hoy'
        elif row['dias_restantes'] <= 3:
            return f'🟠 En {row["dias_restantes"]} días'
        else:
            return f'🟢 En {row["dias_restantes"]} días'
            
    df['semaforo'] = df.apply(asignar_color, axis=1)
    cols = ['id', 'Cliente', 'semaforo', 'descripcion', 'fecha_limite', 'estado', 'notas']
    return df[cols]

def estilo_semaforo(val):
    color = 'black'
    if isinstance(val, str):
        if val.startswith('🔴'): color = 'red'
        elif val.startswith('🟠'): color = 'darkorange'
        elif val.startswith('🟢'): color = 'green'
        elif val == 'Completada' or val.startswith('✅'): color = 'gray'
        elif val == 'Pendiente': color = 'blue'
    return f'color: {color}'

# ---------- Vistas de la Aplicación ----------

# Helpers para filtrado de clientes por rol
def obtener_clientes_permitidos(tipo_persona=None):
    df_todos = db.obtener_clientes(tipo_persona)
    if st.session_state.logged_in_staff and st.session_state.logged_in_staff['rol'] == 'Auxiliar':
        asignaciones = db.obtener_asignaciones(st.session_state.logged_in_staff['id'])
        return df_todos[df_todos['id'].isin(asignaciones)]
    return df_todos


if seleccion == "Configuración de Marca":
    st.title("🎨 Configuración de Marca y Colores")
    st.write("Sube el logotipo de tu despacho. El sistema puede extraer los colores automáticamente o puedes elegirlos manualmente.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Logotipo")
        logo_file = st.file_uploader("Sube tu logo (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
        ruta_logo = os.path.join(ARCHIVOS_DIR, "logo_despacho.png")
        if logo_file:
            with open(ruta_logo, "wb") as f:
                f.write(logo_file.getbuffer())
            st.success("Logo guardado exitosamente.")
            
        if os.path.exists(ruta_logo):
            st.image(ruta_logo, width=200)
            if st.button("Extraer colores del Logo automáticamente"):
                c1, c2, c3 = bt.extraer_colores_de_imagen(ruta_logo)
                db.actualizar_configuracion(ruta_logo, c1, c2, c3)
                st.success("¡Colores extraídos y aplicados! Actualiza la página para ver los cambios.")
                
    with col2:
        st.subheader("2. Paleta de Colores (Manual)")
        conf = db.obtener_configuracion()
        if not conf: conf = {'logo': '', 'c1': '#000000', 'c2': '#FFCC00', 'c3': '#CC0000'}
        with st.form("color_form"):
            color1 = st.color_picker("Color Primario (Títulos, Botones Hover)", conf.get('c1', '#000000'))
            color2 = st.color_picker("Color Secundario (Botones principales, Alertas)", conf.get('c2', '#FFCC00'))
            color3 = st.color_picker("Color Terciario (Énfasis)", conf.get('c3', '#CC0000'))
            
            if st.form_submit_button("Guardar Colores"):
                db.actualizar_configuracion(conf.get('logo'), color1, color2, color3)
                st.success("Colores guardados. Actualiza la página para ver los cambios.")

if seleccion == "Mi Despacho (Finanzas)":
    st.title("💼 Dashboard Ejecutivo del Despacho")
    st.write("Resumen ejecutivo de la cobranza y rentabilidad de tu firma contable.")
    
    # --- Tarjetas (KPIs) ---
    honorarios_df = db.obtener_honorarios()
    
    total_cobrado = 0.0
    total_pendiente = 0.0
    tasa_morosidad = 0.0
    mejor_cliente = "N/A"
    
    if not honorarios_df.empty:
        total_facturado = honorarios_df['Monto'].sum()
        total_cobrado = honorarios_df[honorarios_df['Estado'] == 'Pagado']['Monto'].sum()
        total_pendiente = honorarios_df[honorarios_df['Estado'] == 'Pendiente']['Monto'].sum()
        if total_facturado > 0:
            tasa_morosidad = (total_pendiente / total_facturado) * 100
        if total_cobrado > 0:
            mejor_cliente = honorarios_df[honorarios_df['Estado'] == 'Pagado'].groupby('Cliente')['Monto'].sum().idxmax()
            
    clientes_tot = len(obtener_clientes_permitidos())
        
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Total Cobrado", f"${total_cobrado:,.2f}")
    m2.metric("⏳ Por Cobrar", f"${total_pendiente:,.2f}", delta=f"-{tasa_morosidad:.1f}% Morosidad", delta_color="inverse")
    m3.metric("👥 Clientes", clientes_tot)
    m4.metric("🏆 Top Cliente", mejor_cliente)
    st.divider()
    
    if honorarios_df.empty:
        st.info("Aún no tienes honorarios registrados. Ve a 'Control de Honorarios' para empezar a facturar.")
    else:
        # --- Gráficos Analíticos (Plotly) ---
        c_graf1, c_graf2 = st.columns(2)
        
        with c_graf1:
            st.subheader("Ingresos vs Cobranza Pendiente (Mensual)")
            # Agrupar por Mes y Estado
            cobranza_agrupada = honorarios_df.groupby(['Mes', 'Estado'])['Monto'].sum().reset_index()
            # Ordenar meses
            meses_orden = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
            cobranza_agrupada['OrdenMes'] = cobranza_agrupada['Mes'].map(meses_orden)
            cobranza_agrupada = cobranza_agrupada.sort_values(by='OrdenMes')
            
            fig = px.bar(cobranza_agrupada, x="Mes", y="Monto", color="Estado", barmode="group",
                         color_discrete_map={"Pagado": config['c1'], "Pendiente": config['c3']},
                         labels={"Monto": "Ingresos ($)"})
            st.plotly_chart(fig, use_container_width=True)

        with c_graf2:
            st.subheader("Estado de Obligaciones (Global)")
            obligaciones_df = db.obtener_obligaciones()
            if not obligaciones_df.empty:
                conteo_obs = obligaciones_df['estado'].value_counts().reset_index()
                conteo_obs.columns = ['Estado', 'Cantidad']
                # Asignar colores según estado
                color_map = {'Completada': '#198754', 'Pendiente': '#ffc107', 'Vencida': '#dc3545'}
                fig2 = px.pie(conteo_obs, values="Cantidad", names="Estado", hole=0.4,
                              color="Estado", color_discrete_map=color_map)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No hay obligaciones registradas para generar el gráfico.")
                 
        st.write("---")
        st.subheader("Detalle de Honorarios por Mes")
        
        # Agrupar por mes y año para la gráfica
        df_grafica = honorarios_df.copy()
        # Crear columna de ordenamiento temporal
        df_grafica['Orden'] = df_grafica['Año'].astype(str) + " " + df_grafica['Mes']
        
        df_agrupado = df_grafica.groupby(['Orden', 'Estado'])['Monto'].sum().reset_index()
        
        if not df_agrupado.empty:
             fig = px.bar(df_agrupado, x='Orden', y='Monto', color='Estado', 
                          color_discrete_map={'Pagado': '#2ecc71', 'Pendiente': '#e74c3c'},
                          title="Cobranza Mensual", barmode='stack')
             st.plotly_chart(fig, use_container_width=True)

elif seleccion == "Dashboard":
    st.title("📊 Panel Principal")
    st.write("Bienvenido a tu Sistema de Control Contable.")
    
    col1, col2, col3 = st.columns(3)
    
    clientes_df = obtener_clientes_permitidos()
    total_clientes = len(clientes_df)
    total_fisicas = len(clientes_df[clientes_df['tipo_persona'] == 'Física']) if not clientes_df.empty else 0
    total_morales = len(clientes_df[clientes_df['tipo_persona'] == 'Moral']) if not clientes_df.empty else 0
    
    obligaciones_df = db.obtener_obligaciones()
    pendientes = len(obligaciones_df[obligaciones_df['estado'] == 'Pendiente']) if not obligaciones_df.empty else 0

    with col1:
        st.metric(label="Total de Clientes", value=total_clientes)
    with col2:
        st.metric(label="Obligaciones Pendientes", value=pendientes)
    with col3:
        st.metric(label="Físicas / Morales", value=f"{total_fisicas} / {total_morales}")
        
    st.write("---")
    st.subheader("⚠️ Alertas de Obligaciones Próximas o Vencidas")
    if not obligaciones_df.empty:
        ob_semaforo = calcular_semaforo(obligaciones_df)
        alertas = ob_semaforo[(ob_semaforo['estado'] == 'Pendiente') & 
                              (ob_semaforo['semaforo'].str.startswith('🔴') | ob_semaforo['semaforo'].str.startswith('🟠'))]
        if alertas.empty:
            st.success("¡Todo al día! No hay obligaciones urgentes próximas a vencer.")
        else:
            st.dataframe(
                alertas.style.applymap(estilo_semaforo, subset=['semaforo', 'estado']),
                use_container_width=True, hide_index=True
            )
    else:
         st.info("Aún no tienes obligaciones registradas.")

elif seleccion in ["Personas Físicas", "Personas Morales"]:
    tipo_persona = "Física" if seleccion == "Personas Físicas" else "Moral"
    st.title(f"🏢 Módulo de Personas {tipo_persona}s")
    
    tab1, tab2, tab3 = st.tabs(["Directorio y Obligaciones", "Agregar Cliente Nuevo", "Carga Masiva (Excel)"])
    
    with tab3:
        st.subheader("Subir Plantilla Excel")
        st.write("Sube un archivo `.xlsx` con las columnas: `Nombre`, `RFC`, `TipoPersona` (Física/Moral), `Regimen` (Opcional), `Email`, `Telefono`.")
        archivo_masivo = st.file_uploader("Selecciona tu Excel", type=["xlsx"], key="masivo_up")
        if archivo_masivo:
            if st.button("Procesar y Guardar", type="primary"):
                res_num, res_msg = bt.procesar_carga_masiva_excel(archivo_masivo)
                if res_num > 0:
                    st.success(f"Se insertaron {res_num} clientes.")
                if res_msg:
                    st.warning(f"Errores encontrados:\n{res_msg}")
    
    with tab1:
        st.subheader(f"Lista de Personas {tipo_persona}s")
        clientes_df = obtener_clientes_permitidos(tipo_persona)
        
        if clientes_df.empty:
            st.info(f"No hay personas {tipo_persona.lower()}s registradas.")
        else:
            gb = GridOptionsBuilder.from_dataframe(clientes_df)
            gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
            gb.configure_side_bar()
            gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=False)
            gb.configure_selection('single')
            grid_options = gb.build()
            
            AgGrid(
                clientes_df,
                gridOptions=grid_options,
                enable_enterprise_modules=False,
                allow_unsafe_jscode=True,
                theme='streamlit'
            )
            
            st.write("---")
            with st.expander("Eliminar Cliente"):
                opciones_eliminar = dict(zip(clientes_df['nombre'], clientes_df['id']))
                cliente_a_eliminar = st.selectbox(f"Selecciona un cliente para eliminar:", list(opciones_eliminar.keys()), key=f"eliminar_cliente_{tipo_persona}")
                if st.button("Eliminar", key=f"btn_elim_{tipo_persona}"):
                    id_eliminar = opciones_eliminar[cliente_a_eliminar]
                    db.eliminar_cliente(id_eliminar)
                    st.success(f"Cliente '{cliente_a_eliminar}' eliminado exitosamente.")
                    st.rerun()
                
        st.write("---")
        st.subheader("Obligaciones (Semáforo Fiscal)")
        obligaciones_df = db.obtener_obligaciones(tipo_persona)
        if not obligaciones_df.empty:
             ob_semaforo = calcular_semaforo(obligaciones_df)
             st.dataframe(
                 ob_semaforo.style.applymap(estilo_semaforo, subset=['semaforo', 'estado']),
                 use_container_width=True, hide_index=True
             )

    with tab2:
        st.subheader(f"Registrar Nueva Persona {tipo_persona}")
        st.write("**Opcional: Sube una Constancia de Situación Fiscal (PDF) para autocompletar.**")
        pdf_file = st.file_uploader("Subir Constancia (PDF)", type=["pdf"])
        
        default_rfc, default_nombre, default_regimen = "", "", ""
        
        if pdf_file is not None:
             datos_extraidos, msj = pex.extraer_datos_constancia(pdf_file)
             if datos_extraidos["rfc"]:
                 st.success("¡Datos extraídos de la Constancia con éxito!")
                 default_rfc = datos_extraidos.get("rfc", "")
                 default_nombre = datos_extraidos.get("nombre", "")
                 default_regimen = datos_extraidos.get("regimen", "")
                 if datos_extraidos.get("tipo_persona") != tipo_persona:
                      st.warning(f"¡Atención! El RFC indica que es Persona {datos_extraidos.get('tipo_persona')}.")
             else:
                 st.error("No se pudieron extraer datos del PDF.")

        with st.form(f"nuevo_cliente_{tipo_persona}"):
            nombre = st.text_input("Nombre / Razón Social *", value=default_nombre)
            rfc = st.text_input("RFC *", value=default_rfc)
            
            if tipo_persona == "Física":
                regimenes = ["Sueldos y Salarios", "Actividad Empresarial y Profesional", "Régimen Simplificado de Confianza (RESICO)", "Arrendamiento", "Plataformas Tecnológicas", "Otro"]
            else:
                regimenes = ["Persona Moral - Régimen General", "Persona Moral - RESICO", "Organización Sin Fines de Lucro", "Otro"]
            
            try:
                reg_index = regimenes.index(default_regimen) if default_regimen in regimenes else 0
            except ValueError:
                reg_index = 0
                
            regimen = st.selectbox("Régimen Fiscal Principal", regimenes, index=reg_index)
            email = st.text_input("Correo Electrónico")
            telefono = st.text_input("Teléfono")
            enviar = st.form_submit_button("Guardar Cliente")
            
            if enviar:
                if not nombre or not rfc:
                    st.error("Los campos Nombre y RFC son obligatorios.")
                else:
                    exito, mensaje = db.agregar_cliente(nombre, rfc.upper(), tipo_persona, regimen, email, telefono)
                    if exito:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.error(mensaje)

elif seleccion == "Calendario General":
    st.title("📅 Calendario General de Obligaciones")
    
    tab1, tab2 = st.tabs(["Panel General", "Asignar Obligación"])
    
    with tab1:
        st.subheader("Todas las Obligaciones por Cumplir")
        obligaciones_df = db.obtener_obligaciones()
        
        if obligaciones_df.empty:
            st.info("No hay obligaciones asignadas.")
        else:
            ob_semaforo = calcular_semaforo(obligaciones_df)
            estado_filtro = st.selectbox("Filtrar por estado", ["Todos", "Pendiente", "Completada"])
            if estado_filtro != "Todos":
                ob_semaforo = ob_semaforo[ob_semaforo["estado"] == estado_filtro]
                
            st.dataframe(
                ob_semaforo.style.applymap(estilo_semaforo, subset=['semaforo', 'estado']),
                use_container_width=True, hide_index=True
            )
            
            st.write("---")
            st.subheader("Acciones Rápidas")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Actualizar Estado**")
                opciones_act = dict(zip(obligaciones_df['Cliente'] + " - " + obligaciones_df['descripcion'], obligaciones_df['id']))
                if opciones_act:
                    obl_a_act = st.selectbox("Selecciona la obligación:", list(opciones_act.keys()))
                    nuevo_estado = st.selectbox("Nuevo Estado:", ["Pendiente", "Completada"])
                    if st.button("Actualizar", key="btn_act_gral"):
                        db.actualizar_estado_obligacion(opciones_act[obl_a_act], nuevo_estado)
                        st.rerun()
            with col2:
                st.write("**Eliminar Obligación**")
                if opciones_act:
                    obl_a_elim = st.selectbox("Selecciona la obligación a eliminar:", list(opciones_act.keys()), key="sel_elim_gral")
                    if st.button("Eliminar", key="btn_elim_gral"):
                        db.eliminar_obligacion(opciones_act[obl_a_elim])
                        st.rerun()
                        
    with tab2:
        st.subheader("Asignar Nueva Obligación")
        clientes_df = obtener_clientes_permitidos()
        if clientes_df.empty:
            st.warning("Primero debes registrar clientes.")
        else:
            with st.form("nueva_obligacion"):
                clientes_df['nombre_display'] = clientes_df['nombre'] + " (" + clientes_df['tipo_persona'] + ")"
                nombres_clientes = dict(zip(clientes_df['nombre_display'], clientes_df['id']))
                cliente_seleccionado = st.selectbox("Cliente *", list(nombres_clientes.keys()))
                
                obligaciones_comunes = ["Declaración Mensual IVA e ISR", "Declaración Anual", "Cálculo de Nómina y Retenciones", "Envío de DIOT", "Pago SUA/IMSS", "Otro"]
                descripcion = st.selectbox("Tipo de Obligación", obligaciones_comunes)
                if descripcion == "Otro": descripcion = st.text_input("Especifica la obligación:")
                fecha_limite = st.date_input("Fecha Límite *")
                notas = st.text_area("Notas o Detalles (Opcional)")
                enviar_obl = st.form_submit_button("Asignar Obligación")
                
                if enviar_obl and descripcion:
                    db.agregar_obligacion(nombres_clientes[cliente_seleccionado], descripcion, fecha_limite, notas)
                    st.success(f"Obligación asignada exitosamente.")
                    st.rerun()

elif seleccion == "Cálculo de Impuestos y XML":
    st.title("🧮 Cálculo Automático de Impuestos y Nóminas (XML)")
    st.write("Sube los XMLs (CFDI) de Ingresos, Gastos y Nóminas del mes para calcular automáticamente el IVA, el ISR, retenciones y exportar tus papeles de trabajo.")
    
    clientes_df = obtener_clientes_permitidos()
    if clientes_df.empty:
        st.warning("No hay clientes registrados en el sistema.")
    else:
        clientes_df['nombre_display'] = clientes_df['nombre'] + " - " + clientes_df['rfc']
        opciones_cli = dict(zip(clientes_df['nombre_display'], clientes_df['id']))
        cliente_seleccionado = st.selectbox("Selecciona un Cliente:", list(opciones_cli.keys()))
        
        cliente_id = opciones_cli[cliente_seleccionado]
        datos_cliente = clientes_df[clientes_df['id'] == cliente_id].iloc[0]
        rfc_cliente = datos_cliente['rfc']
        tipo_persona = datos_cliente['tipo_persona']
        regimen_cliente = datos_cliente['regimen']
        
        st.write("---")
        st.subheader("1. Subir Facturas (XML)")
        archivos_xml = st.file_uploader("Sube todos los XMLs del mes (Ventas, Compras y Nóminas)", type=["xml"], accept_multiple_files=True)
        
        if archivos_xml:
             if st.button("Procesar y Calcular", type="primary"):
                  with st.spinner("Procesando XMLs..."):
                       try:
                           df_facturas = xp.procesar_lote_xmls(archivos_xml, rfc_cliente)
                           
                           if df_facturas.empty:
                                st.error("No se encontraron facturas válidas.")
                           else:
                                st.success(f"Se procesaron {len(df_facturas)} facturas correctamente.")
                                
                                # Botón Exportar a Excel (Papel de Trabajo)
                                output = io.BytesIO()
                                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                    df_facturas.to_excel(writer, index=False, sheet_name='Facturas_Mes')
                                excel_data = output.getvalue()
                                st.download_button(
                                    label="📊 Descargar Papel de Trabajo (Excel)",
                                    data=excel_data,
                                    file_name=f"Papel_Trabajo_{rfc_cliente}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                                
                                with st.expander("Ver Detalle de Facturas (Solo lectura)"):
                                     st.dataframe(df_facturas)
                                
                                st.write("---")
                                st.subheader("2. Resumen Financiero Mensual (Base Flujo / PUE)")
                                
                                resumen_mensual = xp.resumir_facturas(df_facturas)
                                if not resumen_mensual:
                                     st.warning("No se encontraron facturas PUE (Pagadas/Cobradas).")
                                else:
                                     resultados = tc.calcular_impuestos(resumen_mensual, regimen_cliente, tipo_persona)
                                     
                                     col1, col2 = st.columns(2)
                                     with col1:
                                          st.metric("Total Ingresos (Cobrados)", f"$ {resultados['Ingresos_Totales']:,.2f}")
                                          st.write("**Desglose de IVA**")
                                          st.write(f"IVA Cobrado: $ {resultados['IVA_Cobrado']:,.2f}")
                                          st.write(f"IVA Pagado: $ {resultados['IVA_Pagado']:,.2f}")
                                          st.write(f"IVA Retenido a Favor: $ {resultados['IVA_Retenido']:,.2f}")
                                          
                                     with col2:
                                          st.metric("Total Gastos y Nómina", f"$ {resultados['Gastos_Totales']:,.2f}")
                                          st.write("**Desglose Nóminas y Retenciones**")
                                          st.write(f"Sueldos Pagados: $ {resumen_mensual.get('Sueldos_Pagados', 0):,.2f}")
                                          st.write(f"ISR Retenido a Pagar (Nóminas): $ {resumen_mensual.get('ISR_Retenido_Nomina_Total', 0):,.2f}")
                                          st.write(f"IMSS Retenido a Pagar: $ {resumen_mensual.get('IMSS_Retenido_Nomina_Total', 0):,.2f}")
                                          
                                     st.write("---")
                                     st.subheader("3. Impuestos y Retenciones a Pagar")
                                     c1, c2, c3 = st.columns(3)
                                     with c1:
                                          if resultados['IVA_A_Favor'] > 0: st.success(f"IVA a Favor: $ {resultados['IVA_A_Favor']:,.2f}")
                                          else: st.error(f"IVA a Pagar: $ {resultados['IVA_A_Pagar']:,.2f}")
                                     with c2:
                                          if resultados['ISR_A_Favor'] > 0: st.success(f"ISR a Favor: $ {resultados['ISR_A_Favor']:,.2f}")
                                          else: st.error(f"ISR Propio a Pagar: $ {resultados['ISR_A_Pagar']:,.2f}")
                                     with c3:
                                          st.error(f"Retenciones Nómina a Pagar: $ {resumen_mensual.get('ISR_Retenido_Nomina_Total', 0) + resumen_mensual.get('IMSS_Retenido_Nomina_Total', 0):,.2f}")
                                          
                                     st.write("---")
                                     # Generar y descargar PDF
                                     pdf_bytes = rg.generar_pdf(datos_cliente, "Mes Actual", resultados, df_facturas)
                                     st.download_button("📄 Descargar Reporte en PDF para el Cliente", data=pdf_bytes, file_name=f"Reporte_Impuestos_{rfc_cliente}.pdf", mime="application/pdf", type="primary")
                                     
                                     # Generar y descargar TXT de DIOT (Carga Batch A29) y CONTPAQi
                                     st.write("---")
                                     st.subheader("5. Exportaciones Masivas (DIOT y CONTPAQi)")
                                     
                                     col_diot, col_cont = st.columns(2)
                                     with col_diot:
                                         st.write("**Declaración DIOT (A29)**")
                                         txt_diot = diot.generar_txt_diot(df_facturas, rfc_cliente)
                                         if txt_diot:
                                             st.download_button(
                                                 label="📥 Descargar TXT DIOT",
                                                 data=txt_diot,
                                                 file_name=f"DIOT_{rfc_cliente}.txt",
                                                 mime="text/plain"
                                             )
                                         else:
                                             st.info("Sin gastos PUE.")
                                             
                                     with col_cont:
                                         st.write("**Pólizas CONTPAQi**")
                                         txt_polizas = contpaqi.generar_polizas_contpaqi(df_facturas, rfc_cliente)
                                         if txt_polizas:
                                             st.download_button(
                                                 label="📥 Descargar TXT Pólizas",
                                                 data=txt_polizas,
                                                 file_name=f"Polizas_{rfc_cliente}.txt",
                                                 mime="text/plain"
                                             )
                                         else:
                                             st.info("Sin XMLs procesados.")
                                             
                       except Exception as e:
                           st.error(f"Ocurrió un error al procesar: {e}")
                           st.code(traceback.format_exc())

elif seleccion == "Conciliación Bancaria y DIOT":
    st.title("🏦 Conciliación Bancaria Inteligente")
    st.write("Cruza los movimientos de tu estado de cuenta bancario (Excel) contra los XMLs procesados del mes para encontrar diferencias.")
    
    st.info("Requisito: Primero procesa los XMLs en el módulo 'Cálculo de Impuestos y XML' y descarga el 'Papel de Trabajo (Excel)'. Usarás ese archivo aquí.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Sube el Papel de Trabajo (XMLs)")
        archivo_xmls = st.file_uploader("Papel de Trabajo (XMLs extraídos)", type=["xlsx"])
        
    with col2:
        st.subheader("2. Sube el Estado de Cuenta (Banco)")
        archivo_banco = st.file_uploader("Estado de Cuenta (Excel descargado del banco)", type=["xlsx", "xls"])
        
    if archivo_xmls and archivo_banco:
        if st.button("Realizar Conciliación", type="primary"):
            with st.spinner("Cruzando RFCs, Montos y Fechas..."):
                # Leer Papel de Trabajo
                df_xmls = pd.read_excel(archivo_xmls)
                
                # Leer y parsear banco genérico
                df_banco_limpio, msj = br.parsear_estado_cuenta(archivo_banco)
                
                if df_banco_limpio is None:
                    st.error(msj)
                else:
                    # Ejecutar algoritmo de conciliación
                    banco_conciliado, xmls_huerfanos, msj_con = br.conciliar_movimientos(df_banco_limpio, df_xmls)
                    
                    st.success("¡Conciliación Completada!")
                    
                    tab1, tab2, tab3 = st.tabs(["Movimientos Bancarios Conciliados", "Depósitos/Retiros Sin XML (Posible Discrepancia)", "XMLs (PUE) Sin Pago en Banco"])
                    
                    with tab1:
                        st.write("Movimientos del banco que encontraron un XML correspondiente por monto exacto:")
                        st.dataframe(banco_conciliado[banco_conciliado['Match'] != 'No Conciliado'], use_container_width=True)
                        
                    with tab2:
                        st.write("⚠️ Alerta Fiscal: Tienes movimientos de dinero en el banco pero NO encontramos un XML emitido/recibido por esa cantidad. Revisa si son traspasos, préstamos, ingresos no facturados, o comisiones.")
                        no_conciliados = banco_conciliado[banco_conciliado['Match'] == 'No Conciliado']
                        st.dataframe(no_conciliados, use_container_width=True)
                        st.metric("Total Retiros Sin XML", f"$ {no_conciliados['Retiro'].sum():,.2f}")
                        st.metric("Total Depósitos Sin XML", f"$ {no_conciliados['Deposito'].sum():,.2f}")
                        
                    with tab3:
                        st.write("⚠️ XMLs marcados como Pagados (PUE) que no aparecen reflejados en el banco por ese monto exacto. Podrían haber sido pagados en efectivo, compensación, o depositados en otra cuenta.")
                        if not xmls_huerfanos.empty:
                            st.dataframe(xmls_huerfanos[['Fecha', 'Serie_Folio', 'Tipo', 'Emisor_Nombre', 'Total']], use_container_width=True)

elif seleccion == "Descarga Masiva SAT (Simulador)":
    st.title("☁️ Conexión y Descarga Masiva del SAT")
    st.write("Módulo avanzado para conectar directamente con los servidores del SAT y descargar todos los XML (Emitidos y Recibidos) y Metadata.")
    
    st.info("""
    **Aviso Técnico y Legal:**
    La descarga masiva directa desde el portal del SAT (sin captcha) requiere conectarse al **Web Service Oficial del SAT**. 
    Para establecer este canal seguro, es **estrictamente obligatorio** firmar las peticiones electrónicas utilizando la e.firma (Archivo .CER, Archivo .KEY y Contraseña Privada) del contribuyente.
    
    Por razones de seguridad y cumplimiento normativo (Compliance), este entorno demo no almacena ni procesa archivos .KEY reales. 
    A continuación se muestra la interfaz que utilizarás cuando despliegues este sistema en tu servidor privado seguro.
    """)
    
    clientes_df = obtener_clientes_permitidos()
    if clientes_df.empty:
        st.warning("No hay clientes registrados.")
    else:
        clientes_df['nombre_display'] = clientes_df['nombre'] + " - " + clientes_df['rfc']
        opciones_cli = dict(zip(clientes_df['nombre_display'], clientes_df['id']))
        cliente_seleccionado = st.selectbox("Selecciona un Cliente para conectar al SAT:", list(opciones_cli.keys()))
        
        with st.form("descarga_sat"):
            st.subheader("Parámetros de Descarga (Web Service)")
            col1, col2 = st.columns(2)
            with col1:
                 fecha_inicio = st.date_input("Fecha Inicial")
                 tipo_descarga = st.selectbox("Tipo de Comprobantes", ["Emitidos", "Recibidos", "Ambos"])
            with col2:
                 fecha_fin = st.date_input("Fecha Final")
                 tipo_archivo = st.selectbox("Formato de Descarga", ["XML", "Metadata (TXT)"])
                 
            st.write("---")
            st.subheader("Firma de la Solicitud (e.firma obligatoria)")
            cer_file = st.file_uploader("Certificado (.CER)", type=["cer"])
            key_file = st.file_uploader("Llave Privada (.KEY)", type=["key"])
            password = st.text_input("Contraseña de la Llave Privada", type="password")
            
            if st.form_submit_button("Conectar y Solicitar Descarga (Simulación)"):
                if not cer_file or not key_file or not password:
                    st.error("Error: Para establecer la conexión SOAP con el Web Service del SAT necesitas subir la e.firma completa.")
                else:
                    with st.spinner("Autenticando con el SAT... Generando Token... Enviando Solicitud..."):
                        import time
                        time.sleep(3) # Simular conexión
                        st.success("¡Solicitud Aceptada por el SAT! (Simulación)")
                        st.info(f"El SAT ha recibido tu petición para descargar los XMLs {tipo_descarga} del {fecha_inicio} al {fecha_fin}. El paquete de archivos estará listo para descargar en unos minutos según la disponibilidad de sus servidores.")

elif seleccion == "Expediente de Cliente":
    st.title("📂 Historial, CRM y Archivo del Cliente")
    
    clientes_df = obtener_clientes_permitidos()
    if clientes_df.empty:
        st.warning("No hay clientes registrados en el sistema.")
    else:
        clientes_df['nombre_display'] = clientes_df['nombre'] + " - " + clientes_df['rfc']
        opciones_cli = dict(zip(clientes_df['nombre_display'], clientes_df['id']))
        cliente_seleccionado = st.selectbox("Buscar Cliente:", list(opciones_cli.keys()))
        
        cliente_id = opciones_cli[cliente_seleccionado]
        datos_cliente = clientes_df[clientes_df['id'] == cliente_id].iloc[0]
        rfc_cli = datos_cliente['rfc']
        
        st.write("---")
        
        # Tarjeta Principal del Cliente con Etiquetas CRM
        col_titulo, col_etiquetas = st.columns([2, 1])
        with col_titulo:
            st.subheader(f"👤 {datos_cliente['nombre']}")
            st.write(f"**RFC:** {rfc_cli} | **Régimen:** {datos_cliente['regimen']}")
            st.write(f"**Email:** {datos_cliente['email']} | **Teléfono:** {datos_cliente['telefono']}")
            
        with col_etiquetas:
            st.write("**🏷️ Etiquetas CRM:**")
            etiquetas_actuales = str(datos_cliente.get('etiquetas', ''))
            if pd.isna(etiquetas_actuales) or not etiquetas_actuales:
                etiquetas_lista = []
            else:
                etiquetas_lista = [e.strip() for e in etiquetas_actuales.split(',') if e.strip()]
                
            # Mostrar etiquetas como badges usando HTML de Streamlit
            if etiquetas_lista:
                 html_tags = "".join([f'<span style="background-color: #f0f2f6; border-radius: 12px; padding: 4px 10px; margin: 2px; font-size: 12px; border: 1px solid #d1d5db; display: inline-block;">{tag}</span>' for tag in etiquetas_lista])
                 st.markdown(html_tags, unsafe_allow_html=True)
            else:
                 st.caption("Sin etiquetas.")
                 
            with st.popover("Editar Etiquetas"):
                # Opciones sugeridas y texto libre
                opciones_tags = ["VIP", "Moroso", "Auditoría SAT", "Revisar Nómina", "Documentación Incompleta"]
                tags_seleccionados = st.multiselect("Selecciona o escribe etiquetas:", options=opciones_tags + etiquetas_lista, default=etiquetas_lista)
                if st.button("Actualizar Etiquetas"):
                     nuevo_string = ",".join(tags_seleccionados)
                     db.actualizar_etiquetas_cliente(cliente_id, nuevo_string)
                     st.rerun()

        # Pestañas para dividir la vista del Expediente
        tab_graficas, tab_boveda, tab_archivo, tab_notas = st.tabs([
             "📊 Finanzas y Gráficas", 
             "🔐 Bóveda de Accesos", 
             "📁 Archivo Digital",
             "📝 Bitácora (Notas)"
        ])
        
        with tab_graficas:
             st.subheader("Análisis Financiero Histórico")
             st.caption("Visualización de Ingresos vs Gastos a lo largo del año (Datos Demo).")
             meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
             ingresos_demo = [50000, 60000, 45000, 70000, 65000, 80000]
             gastos_demo = [30000, 40000, 35000, 50000, 40000, 60000]
             df_chart = pd.DataFrame({'Mes': meses, 'Ingresos': ingresos_demo, 'Gastos': gastos_demo})
             fig = px.bar(df_chart, x='Mes', y=['Ingresos', 'Gastos'], barmode='group', color_discrete_map={'Ingresos': 'green', 'Gastos': 'red'})
             st.plotly_chart(fig, use_container_width=True)
             
        with tab_boveda:
             st.subheader("Accesos y Contraseñas Seguras")
             cred_df = db.obtener_credenciales(cliente_id)
             with st.expander("Ver Accesos Guardados"):
                  if cred_df.empty: st.info("No hay accesos guardados.")
                  else:
                      for _, row in cred_df.iterrows():
                          with st.container(border=True):
                              ccol1, ccol2, ccol3 = st.columns([2, 2, 1])
                              with ccol1:
                                  st.write(f"**{row['tipo_acceso']}**: {row['usuario']}")
                              with ccol2:
                                  if st.checkbox("Mostrar Contraseña", key=f"show_pw_{row['id']}"): st.code(row['contrasena'])
                                  else: st.code("********")
                                  if row['notas']: st.caption(f"Notas: {row['notas']}")
                              with ccol3:
                                  if st.button("Eliminar", key=f"del_cred_{row['id']}"):
                                      db.eliminar_credencial(row['id'])
                                      st.rerun()
                                      
             with st.expander("Agregar Nuevo Acceso"):
                  with st.form("nueva_credencial"):
                      tipo_acceso = st.selectbox("Tipo de Acceso", ["CIEC (SAT)", "FIEL (Vencimiento)", "IMSS (IDSE)", "SIPARE", "Otro"])
                      usuario = st.text_input("Usuario / RFC")
                      contrasena = st.text_input("Contraseña", type="password")
                      notas = st.text_input("Notas / Vencimiento")
                      if st.form_submit_button("Guardar Acceso Seguramente") and tipo_acceso and contrasena:
                           db.agregar_credencial(cliente_id, tipo_acceso, usuario, contrasena, notas)
                           st.rerun()
                           
        with tab_archivo:
             st.subheader("Gestor Documental Seguro")
             st.write("Sube y administra los documentos oficiales importantes de este cliente.")
             
             # Crear directorio específico del cliente usando su RFC
             dir_cliente = os.path.join(ARCHIVOS_DIR, rfc_cli)
             os.makedirs(dir_cliente, exist_ok=True)
             
             col_upload, col_list = st.columns([1, 1])
             with col_upload:
                  st.write("**Subir Nuevo Documento**")
                  tipo_doc = st.selectbox("Tipo de Documento", ["Acta Constitutiva", "INE Representante Legal", "Comprobante de Domicilio", "Acuse SAT", "Contrato", "Otro"])
                  uploaded_doc = st.file_uploader("Seleccionar PDF", type=["pdf"], key="upload_doc")
                  if st.button("Guardar en Archivo") and uploaded_doc:
                       # Limpiar nombre de archivo seguro
                       safe_name = f"{tipo_doc.replace(' ', '_')}_{datetime.today().strftime('%Y%m%d')}.pdf"
                       file_path = os.path.join(dir_cliente, safe_name)
                       with open(file_path, "wb") as f:
                           f.write(uploaded_doc.getbuffer())
                       st.success("Documento guardado localmente.")
                       st.rerun()
                       
             with col_list:
                  st.write("**Documentos en el Archivo Digital**")
                  archivos = os.listdir(dir_cliente)
                  if not archivos:
                       st.info("La carpeta está vacía.")
                  else:
                       for f in archivos:
                            f_path = os.path.join(dir_cliente, f)
                            with st.container(border=True):
                                col_f1, col_f2 = st.columns([3, 1])
                                col_f1.write(f"📄 {f}")
                                with open(f_path, "rb") as file_data:
                                     col_f2.download_button("Descargar", data=file_data, file_name=f, mime="application/pdf", key=f"dl_{f}")
                                     
        with tab_notas:
             st.subheader("Muro de Notas (Bitácora)")
             
             with st.form("nueva_nota"):
                  nueva_nota = st.text_area("Escribe una nueva nota o recordatorio de interacción...")
                  if st.form_submit_button("Publicar Nota") and nueva_nota:
                       db.agregar_nota_crm(cliente_id, nueva_nota)
                       st.rerun()
                       
             # Mostrar historial de notas
             notas_df = db.obtener_notas_crm(cliente_id)
             if notas_df.empty:
                  st.caption("No hay notas registradas para este cliente.")
             else:
                  for _, n_row in notas_df.iterrows():
                       st.info(f"**{n_row['fecha']}** - {n_row['autor']}\n\n{n_row['contenido']}")
                       # Botón pequeño de eliminar
                       if st.button("Eliminar nota", key=f"del_nota_{n_row['id']}", type="tertiary"):
                            db.eliminar_nota_crm(n_row['id'])
                            st.rerun()

elif seleccion == "Portal del Cliente (Login)":
    st.title("🔐 Acceso para Clientes")
    st.write("Ingresa tu RFC y la contraseña proporcionada por tu contador para acceder a tu información fiscal.")
    
    with st.form("login_form"):
        rfc_login = st.text_input("RFC")
        pwd_login = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            if not rfc_login or not pwd_login:
                st.error("Por favor llena ambos campos.")
            else:
                cliente_data = db.verificar_login_cliente(rfc_login, pwd_login)
                if cliente_data:
                    st.session_state.logged_in_client = {'id': cliente_data[0], 'nombre': cliente_data[1], 'rfc': rfc_login.upper()}
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Verifica tu RFC y contraseña.")

elif seleccion == "Mi Portal (Cliente)":
    cliente_info = st.session_state.logged_in_client
    st.title(f"🏢 Bienvenido, {cliente_info['nombre']}")
    st.write(f"**RFC:** {cliente_info['rfc']}")
    
    tab1, tab2 = st.tabs(["Mis Obligaciones y Alertas", "Enviar Documentos al Contador"])
    
    with tab1:
        st.subheader("Semáforo Fiscal")
        st.write("Estas son tus obligaciones fiscales vigentes y su estado actual:")
        mis_obligaciones = db.obtener_obligaciones(cliente_id=cliente_info['id'])
        if mis_obligaciones.empty:
             st.info("No tienes obligaciones pendientes en este momento.")
        else:
             ob_semaforo = calcular_semaforo(mis_obligaciones)
             cols_to_show = ['semaforo', 'descripcion', 'fecha_limite', 'estado']
             st.dataframe(
                 ob_semaforo[cols_to_show].style.applymap(estilo_semaforo, subset=['semaforo', 'estado']),
                 use_container_width=True, hide_index=True
             )
             
    with tab2:
        st.subheader("Buzón Seguro")
        st.write("Sube tus estados de cuenta, facturas o comprobantes. El despacho los recibirá inmediatamente en tu expediente.")
        
        doc_upload = st.file_uploader("Seleccionar Archivo (PDF, Excel, Imágenes)", key="client_upload")
        if st.button("Enviar al Despacho") and doc_upload:
             dir_cliente = os.path.join(ARCHIVOS_DIR, cliente_info['rfc'])
             os.makedirs(dir_cliente, exist_ok=True)
             safe_name = f"PORTAL_{datetime.today().strftime('%Y%m%d_%H%M%S')}_{doc_upload.name.replace(' ', '_')}"
             file_path = os.path.join(dir_cliente, safe_name)
             
             with open(file_path, "wb") as f:
                 f.write(doc_upload.getbuffer())
                 
             db.registrar_documento_portal(cliente_info['id'], doc_upload.name, file_path)
             st.success("¡Documento enviado exitosamente! Tu contador ha sido notificado.")

elif seleccion == "🤖 Asistente Fiscal AI":
    st.title("🤖 Asistente Fiscal con Inteligencia Artificial")
    st.write("Pregúntame sobre topes de deducciones, viáticos, recargos o tasas de impuestos (RESICO).")
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("Escribe tu duda fiscal aquí... (Ej. '¿Cuál es el tope para deducir un automóvil?')"):
        # Agregar mensaje de usuario
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Generar respuesta de AI
        respuesta_ai = ai.obtener_respuesta_fiscal(prompt)
        
        # Mostrar y guardar respuesta
        with st.chat_message("assistant"):
            st.markdown(respuesta_ai)
        st.session_state.chat_history.append({"role": "assistant", "content": respuesta_ai})

elif seleccion == "Control de Honorarios":
    st.title("💼 Control de Honorarios del Despacho")
    st.write("Administra la cobranza de igualas mensuales o servicios extraordinarios de tus clientes.")
    
    clientes_df = obtener_clientes_permitidos()
    if clientes_df.empty:
        st.warning("Primero registra clientes en el Directorio.")
    else:
        tab1, tab2 = st.tabs(["Panel de Cobranza", "Registrar Nuevo Cargo"])
        
        with tab1:
            st.subheader("Estado de Cuenta de Clientes")
            honorarios_df = db.obtener_honorarios()
            
            if honorarios_df.empty:
                st.info("No hay honorarios registrados.")
            else:
                total_pendiente = honorarios_df[honorarios_df['Estado'] == 'Pendiente']['Monto'].sum()
                st.metric("Total por Cobrar (Deuda a favor del despacho)", f"$ {total_pendiente:,.2f}")
                
                filtro = st.selectbox("Filtrar", ["Todos", "Pendiente", "Pagado"])
                df_mostrar = honorarios_df if filtro == "Todos" else honorarios_df[honorarios_df['Estado'] == filtro]
                
                def color_cobranza(val):
                    color = 'green' if val == 'Pagado' else 'red'
                    return f'color: {color}'
                    
                st.dataframe(df_mostrar.style.applymap(color_cobranza, subset=['Estado']), use_container_width=True, hide_index=True)
                
                st.write("---")
                col1, col2 = st.columns(2)
                with col1:
                    op_act = dict(zip(df_mostrar['Cliente'] + " (" + df_mostrar['Mes'] + ") - $" + df_mostrar['Monto'].astype(str), df_mostrar['id']))
                    if op_act:
                        hon_act = st.selectbox("Marcar como:", list(op_act.keys()))
                        n_est = st.selectbox("Estado:", ["Pagado", "Pendiente"])
                        if st.button("Actualizar Pago"):
                            db.actualizar_estado_honorario(op_act[hon_act], n_est)
                            st.rerun()
                with col2:
                    if op_act:
                        hon_elim = st.selectbox("Eliminar registro:", list(op_act.keys()), key="del_hon")
                        if st.button("Eliminar"):
                            db.eliminar_honorario(op_act[hon_elim])
                            st.rerun()

        with tab2:
            st.subheader("Cargar Honorarios a Cliente")
            with st.form("nuevo_honorario"):
                clientes_df['nombre_display'] = clientes_df['nombre']
                dict_cli = dict(zip(clientes_df['nombre_display'], clientes_df['id']))
                cli_sel = st.selectbox("Cliente", list(dict_cli.keys()))
                
                meses_lista = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                mes = st.selectbox("Mes de la Iguala", meses_lista, index=datetime.today().month - 1)
                anio = st.number_input("Año", value=datetime.today().year, step=1)
                monto = st.number_input("Monto a Cobrar ($)", min_value=0.0, step=100.0)
                notas = st.text_input("Concepto (Ej. Iguala Mensual, Declaración Anual)")
                
                if st.form_submit_button("Registrar Cargo"):
                    db.agregar_honorario(dict_cli[cli_sel], mes, anio, monto, notas)
                    st.success("Cargo registrado exitosamente.")
                    st.rerun()

elif seleccion == "Gestión de Equipo (Admin)":
    st.title("👥 Gestión de Equipo (Roles y Accesos)")
    tab_users, tab_roles, tab_assign, tab_org = st.tabs(["Usuarios", "Roles y Permisos", "Asignación de Clientes", "Organigrama"])
    
    with tab_users:
        col_new, col_list = st.columns([1, 2])
        df_roles = db.obtener_roles()
        df_users = db.obtener_usuarios_despacho()
        
        with col_new:
            st.subheader("Registrar/Editar Usuario")
            
            # Lista de usuarios existentes
            opciones_user = ["--- Crear Nuevo ---"] + df_users['usuario'].tolist() if not df_users.empty else ["--- Crear Nuevo ---"]
            
            if 'user_sel_val' not in st.session_state:
                st.session_state.user_sel_val = "--- Crear Nuevo ---"
            if 'last_grid_user' not in st.session_state:
                st.session_state.last_grid_user = None
                
            # Siempre recalcular el índice basado en la variable de estado
            idx_user = 0
            if st.session_state.user_sel_val in opciones_user:
                idx_user = opciones_user.index(st.session_state.user_sel_val)
                
            # No usamos un callback on_change con widget key para no competir,
            # leemos el valor del selectbox, y si cambió, disparamos rerun.
            user_sel = st.selectbox("Seleccionar Acción", opciones_user, index=idx_user)
            if user_sel != st.session_state.user_sel_val:
                st.session_state.user_sel_val = user_sel
                # Mantenemos last_grid_user intacto. Así, si AgGrid sigue mandando 
                # su selección vieja (ej. "admin") en cada tecla presionada,
                # nuestro código sabrá que ya lo procesó y lo ignorará.
                st.rerun()
            
            # Valores por defecto
            def_nom, def_usr, def_rol_id, def_rep = "", "", 2, None
            is_edit = user_sel != "--- Crear Nuevo ---"
            
            def_estatus = "Activo"
            if is_edit:
                u_row = df_users[df_users['usuario'] == user_sel].iloc[0]
                def_nom, def_usr = u_row['nombre'], u_row['usuario']
                def_rol_id = int(u_row['rol_id'])
                def_rep = u_row['reporta_a_id']
                def_estatus = u_row['estatus'] if 'estatus' in u_row and pd.notna(u_row['estatus']) else "Activo"
            
            nombre_u = st.text_input("Nombre Completo", value=def_nom)
            usuario_u = st.text_input("Usuario (Login)", value=def_usr, disabled=is_edit)
            pass_label = "Nueva Contraseña (Dejar en blanco para no cambiar)" if is_edit else "Contraseña"
            pass_u = st.text_input(pass_label, type="password")
            
            # Selector de estatus
            if is_edit:
                estatus_u = st.selectbox("Estatus", ["Activo", "Inactivo"], index=0 if def_estatus == "Activo" else 1)
            else:
                estatus_u = "Activo" # Siempre Activo para nuevos

            # Opciones de rol y supervisor
            if not df_roles.empty:
                nombres_roles = df_roles['nombre_rol'].tolist()
                idx_rol = nombres_roles.index(df_roles[df_roles['id'] == def_rol_id]['nombre_rol'].values[0]) if def_rol_id in df_roles['id'].values else 0
                rol_sel = st.selectbox("Puesto / Rol", nombres_roles, index=idx_rol)
            else:
                rol_sel = None
                st.warning("No hay roles creados.")
            
            if not df_users.empty:
                # Determinar el nivel jerárquico del rol seleccionado
                nivel_rol_actual = 999
                if rol_sel and not df_roles.empty:
                    match_rol = df_roles[df_roles['nombre_rol'] == rol_sel]
                    if not match_rol.empty:
                        nivel_rol_actual = match_rol['nivel_jerarquia'].values[0]

                # Supervisor no puede ser uno mismo y debe tener un nivel jerárquico menor o igual (es decir, superior o igual jerárquicamente)

                # Para cruzar la jerarquía del supervisor, combinamos df_users con df_roles
                df_users_with_roles = df_users.merge(df_roles[['id', 'nivel_jerarquia']], left_on='rol_id', right_on='id', how='left', suffixes=('', '_rol'))

                opciones_super = [("Ninguno", None)]
                for _, row in df_users_with_roles.iterrows():
                    # Supervisor no puede ser uno mismo
                    if is_edit and row['usuario'] == user_sel:
                        continue
                    # Su nivel jerárquico debe ser estrictamente menor (más jerarquía)
                    if pd.notna(row['nivel_jerarquia']) and row['nivel_jerarquia'] < nivel_rol_actual:
                        opciones_super.append((row['nombre'], row['id']))

                idx_sup = 0
                for i, (_, s_id) in enumerate(opciones_super):
                    if s_id == def_rep:
                        idx_sup = i
                        break
                sup_sel = st.selectbox("Reporta a (Supervisor)", [x[0] for x in opciones_super], index=idx_sup)
            else:
                sup_sel = "Ninguno"
            
            if st.button("Guardar Usuario", type="primary"):
                    if nombre_u and usuario_u and rol_sel:
                        r_id = df_roles[df_roles['nombre_rol'] == rol_sel]['id'].values[0]
                        s_id = next((s_id for s_name, s_id in opciones_super if s_name == sup_sel), None) if not df_users.empty else None
                        
                        # Convertir tipos de numpy a tipos nativos de python si es necesario
                        r_id = int(r_id)
                        s_id = int(s_id) if s_id is not None else None

                        if is_edit:
                            ok, msg = db.actualizar_usuario_despacho(int(u_row['id']), nombre_u, usuario_u, r_id, s_id, pass_u if pass_u else None, estatus_u)
                            nuevo_usuario_id = int(u_row['id'])

                            # Si se marcó como inactivo, reasignar sus subordinados a su jefe
                            if estatus_u == "Inactivo" and def_estatus == "Activo":
                                subordinados = db.obtener_subordinados_directos(nuevo_usuario_id)
                                if subordinados:
                                    nombres_movidos = db.reasignar_subordinados(s_id, subordinados)
                                    nombres_str = ", ".join(nombres_movidos)
                                    st.warning(f"Usuario inactivado. Se han reasignado automáticamente {len(subordinados)} subordinados ({nombres_str}) a su jefe inmediato.")
                        else:
                            if not pass_u:
                                ok, msg = False, "Contraseña es requerida para nuevo usuario."
                            else:
                                ok, msg = db.agregar_usuario_despacho(nombre_u, usuario_u, pass_u, r_id, s_id, estatus_u)
                                # Para asignar subordinados, necesitamos el ID del nuevo usuario
                                if ok:
                                    nuevo_usuario_id = db.obtener_id_usuario_por_login(usuario_u)

                        if ok: 
                            # Lógica de autoasignación de subordinados:
                            # Si este usuario tiene un supervisor (s_id), y el nivel jerárquico de este usuario (nivel_rol_actual)
                            # es mayor (es decir, menos jerarquía) que el del supervisor.
                            # Debemos buscar quiénes le reportaban a ese supervisor (s_id) pero que tengan un nivel jerárquico MAYOR que el nivel_rol_actual.
                            # Y pasárselos a que reporten a este nuevo usuario.
                            roles_changed = not is_edit or int(u_row['rol_id']) != r_id

                            sup_changed = not is_edit or u_row['reporta_a_id'] != s_id

                            if (roles_changed or sup_changed) and s_id is not None and nuevo_usuario_id:
                                # nivel_rol_actual ya está definido arriba: es el nivel jerárquico del rol que se acaba de guardar.
                                df_actualizado = db.obtener_usuarios_despacho()
                                df_roles_act = db.obtener_roles()
                                df_combinado = df_actualizado.merge(df_roles_act[['id', 'nivel_jerarquia']], left_on='rol_id', right_on='id', how='left')

                                subordinados_a_mover = []
                                # Buscamos usuarios que actualmente reporten al jefe directo de este usuario (s_id)
                                for _, sub_row in df_combinado.iterrows():
                                    # Importante: No mover al usuario que acabamos de editar, ni a otros con igual o más jerarquía (nivel menor o igual)
                                    if sub_row['reporta_a_id'] == s_id and sub_row['id_x'] != nuevo_usuario_id:
                                        nivel_sub = sub_row['nivel_jerarquia']
                                        # Si el subordinado tiene más nivel (menos jerarquía, es decir, un número mayor)
                                        if pd.notna(nivel_sub) and nivel_sub > nivel_rol_actual:
                                            subordinados_a_mover.append(int(sub_row['id_x'])) # id_x es el id del usuario por el merge

                                # Actualizar esos subordinados para que reporten a nuevo_usuario_id
                                if subordinados_a_mover:
                                    nombres_movidos = db.reasignar_subordinados(nuevo_usuario_id, subordinados_a_mover)
                                    nombres_str = ", ".join(nombres_movidos)
                                    st.success(f"¡Puente jerárquico! Se auto-asignaron {len(subordinados_a_mover)} subordinados a este perfil: {nombres_str}.")

                            st.success(msg)
                            import time
                            time.sleep(1.5)
                            st.session_state.user_sel_val = "--- Crear Nuevo ---"
                            st.rerun()
                        else: st.error(msg)
                    else:
                        st.warning("Completa todos los campos básicos.")
                        
        with col_list:
            st.subheader("Directorio del Staff")
            if not df_users.empty:
                gb_users = GridOptionsBuilder.from_dataframe(df_users[['nombre', 'usuario', 'rol']])
                gb_users.configure_selection('single')
                go_users = gb_users.build()
                
                grid_users = AgGrid(
                    df_users[['nombre', 'usuario', 'rol']],
                    gridOptions=go_users,
                    theme='streamlit',
                    allow_unsafe_jscode=True,
                    update_mode='selection_changed',
                    fit_columns_on_grid_load=True
                )
                
                sel = grid_users['selected_rows']
                usuario_seleccionado = None
                if sel is not None:
                    if isinstance(sel, pd.DataFrame) and not sel.empty:
                        usuario_seleccionado = sel.iloc[0]['usuario']
                    elif isinstance(sel, list) and len(sel) > 0:
                        usuario_seleccionado = sel[0]['usuario']
                        
                # Solo reaccionamos si AgGrid tiene algo seleccionado Y ES DIFERENTE a lo último que nos dijo
                if usuario_seleccionado and usuario_seleccionado != st.session_state.last_grid_user:
                    st.session_state.last_grid_user = usuario_seleccionado
                    if st.session_state.user_sel_val != usuario_seleccionado:
                        st.session_state.user_sel_val = usuario_seleccionado
                        st.rerun()
            else:
                st.info("No hay usuarios registrados.")
                
    with tab_roles:
        col_rnew, col_rlist = st.columns([1, 2])
        todos_modulos = [
            "Dashboard", "Personas Físicas", "Personas Morales", "Cálculo de Impuestos y XML",
            "Conciliación Bancaria y DIOT", "Descarga Masiva SAT (Simulador)", "Exportación a CONTPAQi",
            "Calendario General", "Expediente de Cliente", "Control de Honorarios", "Notificaciones a Clientes",
            "Agenda y Citas", "Facturación (CFDI)", "Tablero Kanban (Staff)", "Envío de Líneas de Captura",
            "🤖 Asistente Fiscal AI", "Mi Despacho (Finanzas)", "Gestión de Equipo (Admin)", "Configuración de Marca"
        ]
        with col_rnew:
            st.subheader("Crear/Editar Puesto")
            
            opciones_r = ["--- Crear Nuevo ---"] + df_roles['nombre_rol'].tolist() if not df_roles.empty else ["--- Crear Nuevo ---"]
            
            if 'rol_sel_val' not in st.session_state:
                st.session_state.rol_sel_val = "--- Crear Nuevo ---"
            if 'last_grid_rol' not in st.session_state:
                st.session_state.last_grid_rol = None
                
            idx_rol_sel = 0
            if st.session_state.rol_sel_val in opciones_r:
                idx_rol_sel = opciones_r.index(st.session_state.rol_sel_val)
                
            r_sel = st.selectbox("Acción", opciones_r, index=idx_rol_sel)
            if r_sel != st.session_state.rol_sel_val:
                st.session_state.rol_sel_val = r_sel
                st.rerun()
                
            is_r_edit = r_sel != "--- Crear Nuevo ---"
            
            def_rn, def_rj, def_rperm = "", 5, []
            if is_r_edit:
                r_row = df_roles[df_roles['nombre_rol'] == r_sel].iloc[0]
                def_rn, def_rj = r_row['nombre_rol'], r_row['nivel_jerarquia']
                import json
                def_rperm = json.loads(r_row['permisos_json'])
            
            nom_r = st.text_input("Nombre del Puesto", value=def_rn)
            jer_r = st.number_input("Nivel Jerárquico (1=Jefe, 5=Operativo)", min_value=1, max_value=10, value=int(def_rj))
            
            st.write("**Permisos de Acceso:**")
            
            # Checkbox Seleccionar Todos
            seleccionar_todos = st.checkbox("☑️ **Seleccionar Todos los Módulos**", value=False)
            st.write("---")
            
            permisos_seleccionados = []
            for mod in todos_modulos:
                # Si "seleccionar todos" esta activo, forzamos value=True
                # Si no, usamos el valor por defecto que viene de la BD para este rol
                val_check = True if seleccionar_todos else (mod in def_rperm)
                if st.checkbox(mod, value=val_check):
                    permisos_seleccionados.append(mod)
            
            if st.button("Guardar Puesto", type="primary"):
                if nom_r:
                    if is_r_edit:
                        db.actualizar_rol(int(r_row['id']), nom_r, jer_r, permisos_seleccionados)
                        st.success("Rol actualizado.")
                        import time
                        time.sleep(1.5)
                        st.session_state.rol_sel_val = "--- Crear Nuevo ---"
                    else:
                        ok, m = db.agregar_rol(nom_r, jer_r, permisos_seleccionados)
                        if ok: 
                            st.success(m)
                            import time
                            time.sleep(1.5)
                            st.session_state.rol_sel_val = "--- Crear Nuevo ---"
                        else: st.error(m)
                    st.rerun()
                else:
                    st.warning("El nombre es obligatorio.")
    
        with col_rlist:
            st.subheader("Puestos Actuales")
            if not df_roles.empty:
                gb_roles = GridOptionsBuilder.from_dataframe(df_roles[['nombre_rol', 'nivel_jerarquia']])
                gb_roles.configure_selection('single')
                go_roles = gb_roles.build()
                
                grid_roles = AgGrid(
                    df_roles[['nombre_rol', 'nivel_jerarquia']],
                    gridOptions=go_roles,
                    theme='streamlit',
                    allow_unsafe_jscode=True,
                    update_mode='selection_changed',
                    fit_columns_on_grid_load=True
                )
                
                sel_r = grid_roles['selected_rows']
                rol_seleccionado = None
                if sel_r is not None:
                    if isinstance(sel_r, pd.DataFrame) and not sel_r.empty:
                        rol_seleccionado = sel_r.iloc[0]['nombre_rol']
                    elif isinstance(sel_r, list) and len(sel_r) > 0:
                        rol_seleccionado = sel_r[0]['nombre_rol']
                        
                if rol_seleccionado and rol_seleccionado != st.session_state.last_grid_rol:
                    st.session_state.last_grid_rol = rol_seleccionado
                    if st.session_state.rol_sel_val != rol_seleccionado:
                        st.session_state.rol_sel_val = rol_seleccionado
                        st.rerun()
            
    with tab_assign:
        st.subheader("Asignar Clientes a Empleados (Segregación de Datos)")
        # Excluir a los Admins (Nivel 1) porque ellos ven todo
        empleados_op = df_users[~df_users['rol'].str.contains('Admin', case=False, na=False)]
        if not empleados_op.empty:
            emp_sel_nombre = st.selectbox("Selecciona un Empleado", empleados_op['nombre'].tolist())
            emp_id = empleados_op[empleados_op['nombre'] == emp_sel_nombre]['id'].values[0]
            
            df_todos_clientes = db.obtener_clientes()
            clientes_asignados = db.obtener_asignaciones(emp_id)
            
            st.write(f"Clientes asignados a **{emp_sel_nombre}**:")
            cols_grid = st.columns(3)
            for idx, row in df_todos_clientes.iterrows():
                asignado = row['id'] in clientes_asignados
                with cols_grid[idx % 3]:
                    nuevo_estado = st.checkbox(f"{row['nombre']}", value=asignado, key=f"assign_{emp_id}_{row['id']}")
                    if nuevo_estado != asignado:
                        if nuevo_estado:
                            db.asignar_cliente_a_usuario(emp_id, row['id'])
                        else:
                            db.desasignar_cliente_de_usuario(emp_id, row['id'])
                        st.rerun()
        else:
            st.info("No hay empleados operativos registrados.")
            
    with tab_org:
        st.subheader("Organigrama del Despacho")
        if not df_users.empty and 'reporta_a_id' in df_users.columns:
            import graphviz
            import html

            # Solo consideramos usuarios Activos
            df_activos = df_users[df_users['estatus'] == 'Activo'] if 'estatus' in df_users.columns else df_users

            # Filtro de líder
            opciones_lider = ["-- Toda la Empresa --"] + df_activos['nombre'].tolist()
            lider_seleccionado = st.selectbox("Filtrar por rama de líder:", opciones_lider)

            # Lógica recursiva para obtener solo a los subordinados de esa rama
            valid_ids_org = set()
            if lider_seleccionado == "-- Toda la Empresa --":
                valid_ids_org = set(df_activos['id'].tolist())
            else:
                id_lider = df_activos[df_activos['nombre'] == lider_seleccionado]['id'].values[0]

                # Función recursiva para encontrar descendencia
                def obtener_descendencia(parent_id, current_set):
                    current_set.add(parent_id)
                    hijos = df_activos[df_activos['reporta_a_id'] == parent_id]['id'].tolist()
                    for hijo_id in hijos:
                        obtener_descendencia(hijo_id, current_set)

                obtener_descendencia(id_lider, valid_ids_org)

            # Filtrar dataframe a graficar
            df_graficar = df_activos[df_activos['id'].isin(valid_ids_org)]

            # Cruce con roles para obtener nivel de jerarquía (y decidir color)
            if not df_roles.empty:
                df_graficar = df_graficar.merge(df_roles[['id', 'nivel_jerarquia']], left_on='rol_id', right_on='id', how='left')
            else:
                df_graficar['nivel_jerarquia'] = 5 # Default si no hay roles

            # Colores base según jerarquía
            def obtener_color_por_jerarquia(nivel):
                # Tonos de azul y verde
                colores = {
                    1: '#1E3A8A', # Nivel 1 (Director) - Azul oscuro
                    2: '#2563EB', # Nivel 2 - Azul brillante
                    3: '#3B82F6', # Nivel 3 - Azul normal
                    4: '#059669', # Nivel 4 - Verde oscuro
                    5: '#10B981', # Nivel 5 - Verde
                    6: '#34D399', # Nivel 6 - Verde claro
                }
                # Para niveles mayores o desconocidos, gris oscuro
                return colores.get(nivel, '#4B5563')

            # Crear grafo jerárquico
            dot = graphviz.Digraph(comment='Organigrama')
            dot.attr('node', shape='box', style='filled', fontname='Helvetica', fontcolor='white')
            dot.attr('edge', arrowhead='vee', color='#666666')

            # Añadir nodos
            for _, r in df_graficar.iterrows():
                u_id = str(r['id_x'] if 'id_x' in df_graficar.columns else r['id'])
                nivel = r['nivel_jerarquia'] if pd.notna(r['nivel_jerarquia']) else 5

                # Formato HTML: Nombre en negritas y Puesto en cursivas, escapando caracteres
                safe_nombre = html.escape(r['nombre'])
                safe_rol = html.escape(r['rol'])
                label = f"<<B>{safe_nombre}</B><BR/><I>{safe_rol}</I>>"

                color_nodo = obtener_color_por_jerarquia(nivel)
                dot.node(u_id, label, fillcolor=color_nodo)

            # Añadir bordes (conexiones jerárquicas)
            for _, r in df_graficar.iterrows():
                u_id = str(r['id_x'] if 'id_x' in df_graficar.columns else r['id'])
                parent_id = r['reporta_a_id']
                if pd.notna(parent_id) and parent_id in valid_ids_org:
                    # El padre apunta al hijo
                    dot.edge(str(int(parent_id)), u_id)

            st.graphviz_chart(dot, use_container_width=True)

            # Ocultar la tabla preexistente
            with st.expander("Ver Datos en Tabla"):
                org_data = []
                valid_ids_table = df_users['id'].tolist()

                for _, r in df_users.iterrows():

                    sup_name = df_users[df_users['id'] == r['reporta_a_id']]['nombre'].values[0] if pd.notna(r['reporta_a_id']) and r['reporta_a_id'] in valid_ids_table else ""

                    org_data.append({"Nombre": r['nombre'], "Puesto": r['rol'], "Reporta_A": sup_name})

                df_org = pd.DataFrame(org_data)
                st.dataframe(df_org, use_container_width=True, hide_index=True)

if seleccion == "Descarga Masiva SAT (Simulador)":
    st.title("☁️ Conexión y Descarga Masiva del SAT")
    st.write("Módulo avanzado para conectar directamente con los servidores del SAT y descargar todos los XML (Emitidos y Recibidos) y Metadata.")
    
    st.info("""
    **Aviso Técnico y Legal:**
    La descarga masiva directa desde el portal del SAT (sin captcha) requiere conectarse al **Web Service Oficial del SAT**. 
    Para establecer este canal seguro, es **estrictamente obligatorio** firmar las peticiones electrónicas utilizando la e.firma (Archivo .CER, Archivo .KEY y Contraseña Privada) del contribuyente.
    
    Por razones de seguridad y cumplimiento normativo (Compliance), este entorno demo no almacena ni procesa archivos .KEY reales. 
    A continuación se muestra la interfaz que utilizarás cuando despliegues este sistema en tu servidor privado seguro.
    """)
    
    clientes_df = obtener_clientes_permitidos()
    if clientes_df.empty:
        st.warning("No hay clientes registrados.")
    else:
        clientes_df['nombre_display'] = clientes_df['nombre'] + " - " + clientes_df['rfc']
        opciones_cli = dict(zip(clientes_df['nombre_display'], clientes_df['id']))
        cliente_seleccionado = st.selectbox("Selecciona un Cliente para conectar al SAT:", list(opciones_cli.keys()))
        
        with st.form("descarga_sat"):
            st.subheader("Parámetros de Descarga (Web Service)")
            col1, col2 = st.columns(2)
            with col1:
                 fecha_inicio = st.date_input("Fecha Inicial")
                 tipo_descarga = st.selectbox("Tipo de Comprobantes", ["Emitidos", "Recibidos", "Ambos"])
            with col2:
                 fecha_fin = st.date_input("Fecha Final")
                 tipo_archivo = st.selectbox("Formato de Descarga", ["XML", "Metadata (TXT)"])
                 
            st.write("---")
            st.subheader("Firma de la Solicitud (e.firma obligatoria)")
            cer_file = st.file_uploader("Certificado (.CER)", type=["cer"])
            key_file = st.file_uploader("Llave Privada (.KEY)", type=["key"])
            password = st.text_input("Contraseña de la Llave Privada", type="password")
            
            if st.form_submit_button("Conectar y Solicitar Descarga (Simulación)"):
                if not cer_file or not key_file or not password:
                    st.error("Error: Para establecer la conexión SOAP con el Web Service del SAT necesitas subir la e.firma completa.")
                else:
                    with st.spinner("Autenticando con el SAT... Generando Token... Enviando Solicitud..."):
                        import time
                        time.sleep(3) # Simular conexión
                        st.success("¡Solicitud Aceptada por el SAT! (Simulación)")
                        st.info(f"El SAT ha recibido tu petición para descargar los XMLs {tipo_descarga} del {fecha_inicio} al {fecha_fin}. El paquete de archivos estará listo para descargar en unos minutos según la disponibilidad de sus servidores.")

elif seleccion == "Expediente de Cliente":
    st.title("📂 Historial, CRM y Archivo del Cliente")
    
    clientes_df = obtener_clientes_permitidos()
    if clientes_df.empty:
        st.warning("No hay clientes registrados en el sistema.")
    else:
        clientes_df['nombre_display'] = clientes_df['nombre'] + " - " + clientes_df['rfc']
        opciones_cli = dict(zip(clientes_df['nombre_display'], clientes_df['id']))
        cliente_seleccionado = st.selectbox("Buscar Cliente:", list(opciones_cli.keys()))
        
        cliente_id = opciones_cli[cliente_seleccionado]
        datos_cliente = clientes_df[clientes_df['id'] == cliente_id].iloc[0]
        rfc_cli = datos_cliente['rfc']
        
        st.write("---")
        
        # Tarjeta Principal del Cliente con Etiquetas CRM
        col_titulo, col_etiquetas = st.columns([2, 1])
        with col_titulo:
            st.subheader(f"👤 {datos_cliente['nombre']}")
            st.write(f"**RFC:** {rfc_cli} | **Régimen:** {datos_cliente['regimen']}")
            st.write(f"**Email:** {datos_cliente['email']} | **Teléfono:** {datos_cliente['telefono']}")
            
        with col_etiquetas:
            st.write("**🏷️ Etiquetas CRM:**")
            etiquetas_actuales = str(datos_cliente.get('etiquetas', ''))
            if pd.isna(etiquetas_actuales) or not etiquetas_actuales:
                etiquetas_lista = []
            else:
                etiquetas_lista = [e.strip() for e in etiquetas_actuales.split(',') if e.strip()]
                
            # Mostrar etiquetas como badges usando HTML de Streamlit
            if etiquetas_lista:
                 html_tags = "".join([f'<span style="background-color: #f0f2f6; border-radius: 12px; padding: 4px 10px; margin: 2px; font-size: 12px; border: 1px solid #d1d5db; display: inline-block;">{tag}</span>' for tag in etiquetas_lista])
                 st.markdown(html_tags, unsafe_allow_html=True)
            else:
                 st.caption("Sin etiquetas.")
                 
            with st.popover("Editar Etiquetas"):
                # Opciones sugeridas y texto libre
                opciones_tags = ["VIP", "Moroso", "Auditoría SAT", "Revisar Nómina", "Documentación Incompleta"]
                tags_seleccionados = st.multiselect("Selecciona o escribe etiquetas:", options=opciones_tags + etiquetas_lista, default=etiquetas_lista)
                if st.button("Actualizar Etiquetas"):
                     nuevo_string = ",".join(tags_seleccionados)
                     db.actualizar_etiquetas_cliente(cliente_id, nuevo_string)
                     st.rerun()

        # Pestañas para dividir la vista del Expediente
        tab_graficas, tab_boveda, tab_archivo, tab_notas = st.tabs([
             "📊 Finanzas y Gráficas", 
             "🔐 Bóveda de Accesos", 
             "📁 Archivo Digital",
             "📝 Bitácora (Notas)"
        ])
        
        with tab_graficas:
             st.subheader("Análisis Financiero Histórico")
             st.caption("Visualización de Ingresos vs Gastos a lo largo del año (Datos Demo).")
             meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
             ingresos_demo = [50000, 60000, 45000, 70000, 65000, 80000]
             gastos_demo = [30000, 40000, 35000, 50000, 40000, 60000]
             df_chart = pd.DataFrame({'Mes': meses, 'Ingresos': ingresos_demo, 'Gastos': gastos_demo})
             fig = px.bar(df_chart, x='Mes', y=['Ingresos', 'Gastos'], barmode='group', color_discrete_map={'Ingresos': 'green', 'Gastos': 'red'})
             st.plotly_chart(fig, use_container_width=True)
             
        with tab_boveda:
             st.subheader("Accesos y Contraseñas Seguras")
             cred_df = db.obtener_credenciales(cliente_id)
             with st.expander("Ver Accesos Guardados"):
                  if cred_df.empty: st.info("No hay accesos guardados.")
                  else:
                      for _, row in cred_df.iterrows():
                          with st.container(border=True):
                              ccol1, ccol2, ccol3 = st.columns([2, 2, 1])
                              with ccol1:
                                  st.write(f"**{row['tipo_acceso']}**: {row['usuario']}")
                              with ccol2:
                                  if st.checkbox("Mostrar Contraseña", key=f"show_pw_{row['id']}"): st.code(row['contrasena'])
                                  else: st.code("********")
                                  if row['notas']: st.caption(f"Notas: {row['notas']}")
                              with ccol3:
                                  if st.button("Eliminar", key=f"del_cred_{row['id']}"):
                                      db.eliminar_credencial(row['id'])
                                      st.rerun()
                                      
             with st.expander("Agregar Nuevo Acceso"):
                  with st.form("nueva_credencial"):
                      tipo_acceso = st.selectbox("Tipo de Acceso", ["CIEC (SAT)", "FIEL (Vencimiento)", "IMSS (IDSE)", "SIPARE", "Otro"])
                      usuario = st.text_input("Usuario / RFC")
                      contrasena = st.text_input("Contraseña", type="password")
                      notas = st.text_input("Notas / Vencimiento")
                      if st.form_submit_button("Guardar Acceso Seguramente") and tipo_acceso and contrasena:
                           db.agregar_credencial(cliente_id, tipo_acceso, usuario, contrasena, notas)
                           st.rerun()
                           
        with tab_archivo:
             st.subheader("Gestor Documental Seguro")
             st.write("Sube y administra los documentos oficiales importantes de este cliente.")
             
             # Crear directorio específico del cliente usando su RFC
             dir_cliente = os.path.join(ARCHIVOS_DIR, rfc_cli)
             os.makedirs(dir_cliente, exist_ok=True)
             
             col_upload, col_list = st.columns([1, 1])
             with col_upload:
                  st.write("**Subir Nuevo Documento**")
                  tipo_doc = st.selectbox("Tipo de Documento", ["Acta Constitutiva", "INE Representante Legal", "Comprobante de Domicilio", "Acuse SAT", "Contrato", "Otro"])
                  uploaded_doc = st.file_uploader("Seleccionar PDF", type=["pdf"], key="upload_doc")
                  if st.button("Guardar en Archivo") and uploaded_doc:
                       # Limpiar nombre de archivo seguro
                       safe_name = f"{tipo_doc.replace(' ', '_')}_{datetime.today().strftime('%Y%m%d')}.pdf"
                       file_path = os.path.join(dir_cliente, safe_name)
                       with open(file_path, "wb") as f:
                           f.write(uploaded_doc.getbuffer())
                       st.success("Documento guardado localmente.")
                       st.rerun()
                       
             with col_list:
                  st.write("**Documentos en el Archivo Digital**")
                  archivos = os.listdir(dir_cliente)
                  if not archivos:
                       st.info("La carpeta está vacía.")
                  else:
                       for f in archivos:
                            f_path = os.path.join(dir_cliente, f)
                            with st.container(border=True):
                                col_f1, col_f2 = st.columns([3, 1])
                                col_f1.write(f"📄 {f}")
                                with open(f_path, "rb") as file_data:
                                     col_f2.download_button("Descargar", data=file_data, file_name=f, mime="application/pdf", key=f"dl_{f}")
                                     
        with tab_notas:
             st.subheader("Muro de Notas (Bitácora)")
             
             with st.form("nueva_nota"):
                  nueva_nota = st.text_area("Escribe una nueva nota o recordatorio de interacción...")
                  if st.form_submit_button("Publicar Nota") and nueva_nota:
                       db.agregar_nota_crm(cliente_id, nueva_nota)
                       st.rerun()
                       
             # Mostrar historial de notas
             notas_df = db.obtener_notas_crm(cliente_id)
             if notas_df.empty:
                  st.caption("No hay notas registradas para este cliente.")
             else:
                  for _, n_row in notas_df.iterrows():
                       st.info(f"**{n_row['fecha']}** - {n_row['autor']}\n\n{n_row['contenido']}")
                       # Botón pequeño de eliminar
                       if st.button("Eliminar nota", key=f"del_nota_{n_row['id']}", type="tertiary"):
                            db.eliminar_nota_crm(n_row['id'])
                            st.rerun()

elif seleccion == "Portal del Cliente (Login)":
    st.title("🔐 Acceso para Clientes")
    st.write("Ingresa tu RFC y la contraseña proporcionada por tu contador para acceder a tu información fiscal.")
    
    with st.form("login_form"):
        rfc_login = st.text_input("RFC")
        pwd_login = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            if not rfc_login or not pwd_login:
                st.error("Por favor llena ambos campos.")
            else:
                cliente_data = db.verificar_login_cliente(rfc_login, pwd_login)
                if cliente_data:
                    st.session_state.logged_in_client = {'id': cliente_data[0], 'nombre': cliente_data[1], 'rfc': rfc_login.upper()}
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Verifica tu RFC y contraseña.")

elif seleccion == "Mi Portal (Cliente)":
    cliente_info = st.session_state.logged_in_client
    st.title(f"🏢 Bienvenido, {cliente_info['nombre']}")
    st.write(f"**RFC:** {cliente_info['rfc']}")
    
    tab1, tab2 = st.tabs(["Mis Obligaciones y Alertas", "Enviar Documentos al Contador"])
    
    with tab1:
        st.subheader("Semáforo Fiscal")
        st.write("Estas son tus obligaciones fiscales vigentes y su estado actual:")
        mis_obligaciones = db.obtener_obligaciones(cliente_id=cliente_info['id'])
        if mis_obligaciones.empty:
             st.info("No tienes obligaciones pendientes en este momento.")
        else:
             ob_semaforo = calcular_semaforo(mis_obligaciones)
             cols_to_show = ['semaforo', 'descripcion', 'fecha_limite', 'estado']
             st.dataframe(
                 ob_semaforo[cols_to_show].style.applymap(estilo_semaforo, subset=['semaforo', 'estado']),
                 use_container_width=True, hide_index=True
             )
             
    with tab2:
        st.subheader("Buzón Seguro")
        st.write("Sube tus estados de cuenta, facturas o comprobantes. El despacho los recibirá inmediatamente en tu expediente.")
        
        doc_upload = st.file_uploader("Seleccionar Archivo (PDF, Excel, Imágenes)", key="client_upload")
        if st.button("Enviar al Despacho") and doc_upload:
             dir_cliente = os.path.join(ARCHIVOS_DIR, cliente_info['rfc'])
             os.makedirs(dir_cliente, exist_ok=True)
             safe_name = f"PORTAL_{datetime.today().strftime('%Y%m%d_%H%M%S')}_{doc_upload.name.replace(' ', '_')}"
             file_path = os.path.join(dir_cliente, safe_name)
             
             with open(file_path, "wb") as f:
                 f.write(doc_upload.getbuffer())
                 
             db.registrar_documento_portal(cliente_info['id'], doc_upload.name, file_path)
             st.success("¡Documento enviado exitosamente! Tu contador ha sido notificado.")

elif seleccion == "🤖 Asistente Fiscal AI":
    st.title("🤖 Asistente Fiscal con Inteligencia Artificial")
    st.write("Pregúntame sobre topes de deducciones, viáticos, recargos o tasas de impuestos (RESICO).")
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("Escribe tu duda fiscal aquí... (Ej. '¿Cuál es el tope para deducir un automóvil?')"):
        # Agregar mensaje de usuario
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Generar respuesta de AI
        respuesta_ai = ai.obtener_respuesta_fiscal(prompt)
        
        # Mostrar y guardar respuesta
        with st.chat_message("assistant"):
            st.markdown(respuesta_ai)
        st.session_state.chat_history.append({"role": "assistant", "content": respuesta_ai})

    st.title("📲 Panel de Notificaciones (WhatsApp / Email)")
    st.write("Envía recordatorios masivos a tus clientes sobre pagos o estados de cuenta.")
    
    with st.form("form_notificaciones"):
        clientes = db.obtener_clientes()
        if not clientes.empty:
            destinatarios = st.multiselect("Seleccionar Destinatarios", clientes['nombre'].tolist())
            medio = st.selectbox("Medio de Envío", ["WhatsApp", "Email"])
            mensaje = st.text_area("Mensaje a enviar", "Hola,\n\nTe recordamos que se acerca la fecha límite para el pago de impuestos. Por favor, compártenos tus estados de cuenta para el cierre del mes.\n\nSaludos,\nEl Despacho Contable")
            
            if st.form_submit_button("Enviar (Simulación)"):
                if destinatarios and mensaje:
                    for dest in destinatarios:
                        cliente_id = clientes[clientes['nombre'] == dest]['id'].values[0]
                        db.registrar_notificacion(cliente_id, medio, mensaje)
                    st.success(f"¡Mensajes enviados a {len(destinatarios)} clientes por {medio}!")
                else:
                    st.warning("Selecciona al menos un destinatario y escribe un mensaje.")
        else:
            st.info("No hay clientes registrados.")
            
    st.subheader("Historial de Envíos")
    historial = db.obtener_notificaciones()
    if not historial.empty:
        st.dataframe(historial, hide_index=True)
    else:
        st.write("No hay notificaciones enviadas aún.")

# --- Nuevos Módulos Fase 8 ---

if seleccion == "Agenda y Citas":
    st.title("📅 Agenda del Despacho")
    st.write("Programa reuniones y entregas de documentos con tus clientes.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Nueva Cita")
        clientes = obtener_clientes_permitidos()
        if not clientes.empty:
            with st.form("form_cita"):
                cliente_sel = st.selectbox("Cliente", clientes['nombre'].tolist())
                titulo = st.text_input("Asunto / Título")
                f_cita = st.date_input("Fecha")
                h_cita = st.time_input("Hora")
                notas = st.text_area("Notas")
                
                if st.form_submit_button("Agendar Cita"):
                    if titulo:
                        cliente_id = clientes[clientes['nombre'] == cliente_sel]['id'].values[0]
                        dt_combinada = datetime.combine(f_cita, h_cita).strftime("%Y-%m-%d %H:%M:%S")
                        db.agregar_cita(cliente_id, titulo, dt_combinada, notas)
                        st.success("Cita agendada.")
                        st.rerun()
                    else:
                        st.warning("El título es obligatorio.")
        else:
            st.info("Registra clientes primero.")
            
    with col2:
        st.subheader("Próximas Citas")
        df_citas = db.obtener_citas()
        if not df_citas.empty:
            # Filtrar si es Auxiliar
            if st.session_state.logged_in_staff and st.session_state.logged_in_staff['rol'] == 'Auxiliar':
                permitidos = clientes['nombre'].tolist()
                df_citas = df_citas[df_citas['Cliente'].isin(permitidos)]
                
            for idx, row in df_citas.iterrows():
                with st.expander(f"🗓️ {row['fecha_hora']} - {row['titulo']} ({row['Cliente']})"):
                    st.write(f"**Notas:** {row['notas']}")
                    if st.button("Eliminar Cita", key=f"del_cita_{row['id']}"):
                        db.eliminar_cita(row['id'])
                        st.rerun()
        else:
            st.write("No hay citas programadas.")


if seleccion == "Facturación (CFDI)":
    st.title("🧾 Emisor de Facturas CFDI (Simulador)")
    st.write("Genera el PDF y XML de una factura para enviarla al cliente.")
    
    clientes = obtener_clientes_permitidos()
    if not clientes.empty:
        with st.form("factura_form"):
            cliente_sel = st.selectbox("Receptor (Cliente)", clientes['nombre'].tolist())
            concepto = st.text_input("Concepto (Ej. Honorarios Contables Mes de Abril)")
            monto = st.number_input("Subtotal (Antes de IVA)", min_value=1.0, value=1500.0)
            
            if st.form_submit_button("Generar Factura"):
                rfc_cliente = clientes[clientes['nombre'] == cliente_sel]['rfc'].values[0]
                pdf_bytes, xml_bytes = bt.simular_timbrado_factura(cliente_sel, rfc_cliente, monto, concepto)
                
                st.success("¡Factura timbrada exitosamente!")
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.download_button("Descargar PDF", data=pdf_bytes, file_name=f"Factura_{rfc_cliente}.pdf", mime="application/pdf")
                with col_d2:
                    st.download_button("Descargar XML", data=xml_bytes, file_name=f"Factura_{rfc_cliente}.xml", mime="application/xml")
    else:
        st.info("Debes registrar al menos un cliente.")


if seleccion == "Tablero Kanban (Staff)":
    st.title("📋 Tablero de Tareas (Kanban)")
    st.write("Gestiona el flujo de trabajo del despacho y asigna tareas a tu equipo.")
    
    # Agregar Tarea
    with st.expander("➕ Nueva Tarea"):
        with st.form("form_nueva_tarea"):
            clientes = obtener_clientes_permitidos()
            if not clientes.empty:
                c_sel = st.selectbox("Cliente", clientes['nombre'].tolist())
                desc = st.text_input("Descripción de la Tarea")
                
                # Asignación solo si es Admin
                asig_id = None
                if st.session_state.logged_in_staff['rol'] == 'Administrador':
                    usuarios = db.obtener_usuarios_despacho()
                    if not usuarios.empty:
                        u_sel = st.selectbox("Asignar a", usuarios['nombre'].tolist())
                        asig_id = usuarios[usuarios['nombre'] == u_sel]['id'].values[0]
                else:
                    asig_id = st.session_state.logged_in_staff['id']
                    
                if st.form_submit_button("Crear Tarea"):
                    c_id = clientes[clientes['nombre'] == c_sel]['id'].values[0]
                    db.crear_tarea_kanban(c_id, desc, asig_id)
                    st.success("Tarea creada.")
                    st.rerun()
            else:
                st.info("Agrega clientes primero.")
                
    st.divider()
    
    columnas = ["Por Revisar", "En Proceso", "Lista para Envío", "Finalizada"]
    cols = st.columns(len(columnas))
    
    for i, col_name in enumerate(columnas):
        with cols[i]:
            st.markdown(f"**{col_name}**")
            df_tareas = db.obtener_tareas_kanban(col_name)
            
            # Filtro por Auxiliar
            if st.session_state.logged_in_staff['rol'] == 'Auxiliar':
                mi_nombre = st.session_state.logged_in_staff['nombre']
                df_tareas = df_tareas[(df_tareas['Asignado'] == mi_nombre) | (df_tareas['Asignado'].isnull())]
                
            for _, row in df_tareas.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{row['Cliente']}**")
                    st.write(row['descripcion'])
                    st.caption(f"👤 {row['Asignado'] if row['Asignado'] else 'Sin asignar'}")
                    
                    # Movimientos
                    if i > 0:
                        if st.button("⬅️", key=f"L_{row['id']}"):
                            db.mover_tarea_kanban(row['id'], columnas[i-1])
                            st.rerun()
                    if i < len(columnas) - 1:
                        if st.button("➡️", key=f"R_{row['id']}"):
                            db.mover_tarea_kanban(row['id'], columnas[i+1])
                            st.rerun()
                    if st.button("🗑️", key=f"D_{row['id']}"):
                        db.eliminar_tarea_kanban(row['id'])
                        st.rerun()


if seleccion == "Envío de Líneas de Captura":
    st.title("💸 Envío de Líneas de Captura")
    st.write("Sube el Acuse de Recibo del SAT y el sistema notificará automáticamente al cliente para su pago.")
    
    col_izq, col_der = st.columns([1, 2])
    with col_izq:
        clientes = obtener_clientes_permitidos()
        if not clientes.empty:
            with st.form("form_linea_captura"):
                cliente_sel = st.selectbox("Cliente", clientes['nombre'].tolist())
                mes = st.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
                anio = st.number_input("Año", min_value=2020, max_value=2030, value=datetime.now().year)
                monto = st.number_input("Monto a Pagar ($)", min_value=0.0, format="%.2f")
                vencimiento = st.date_input("Fecha de Vencimiento", date.today() + pd.Timedelta(days=17))
                archivo_pdf = st.file_uploader("Subir Línea de Captura (PDF)", type=["pdf"])
                
                if st.form_submit_button("Subir y Notificar al Cliente"):
                    if archivo_pdf and monto >= 0:
                        c_id = clientes[clientes['nombre'] == cliente_sel]['id'].values[0]
                        nombre_archivo = f"Linea_{mes}_{anio}_{c_id}.pdf"
                        ruta_archivo = os.path.join(ARCHIVOS_DIR, nombre_archivo)
                        
                        with open(ruta_archivo, "wb") as f:
                            f.write(archivo_pdf.getbuffer())
                            
                        db.agregar_linea_captura(c_id, mes, anio, monto, vencimiento, ruta_archivo)
                        db.registrar_documento_portal(c_id, nombre_archivo, ruta_archivo) # También lo ve en su portal
                        
                        st.success(f"Línea de captura enviada al portal del cliente y notificación por correo simulada a {clientes[clientes['nombre'] == cliente_sel]['email'].values[0]}")
                        st.rerun()
                    else:
                        st.warning("Completa todos los campos y sube el PDF.")
        else:
            st.info("Registra clientes primero.")
            
    with col_der:
        st.subheader("Historial de Envíos")
        lineas_df = db.obtener_lineas_captura()
        
        # Filtro Staff
        if st.session_state.logged_in_staff['rol'] == 'Auxiliar':
            permitidos = clientes['nombre'].tolist()
            lineas_df = lineas_df[lineas_df['Cliente'].isin(permitidos)]
            
        if not lineas_df.empty:
            st.dataframe(lineas_df[['Cliente', 'mes', 'anio', 'monto', 'fecha_vencimiento', 'fecha_envio']], use_container_width=True, hide_index=True)
        else:
            st.write("Aún no se han enviado líneas de captura.")

