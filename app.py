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

# Configuración de página
st.set_page_config(page_title="Sistema Contable de Despacho", page_icon="📈", layout="wide")

# Inicializar Base de Datos
db.init_db()

# Menú lateral
st.sidebar.title("Navegación")
opciones = [
    "Dashboard", 
    "Personas Físicas", 
    "Personas Morales", 
    "Cálculo de Impuestos y XML", 
    "Calendario General", 
    "Expediente de Cliente",
    "Control de Honorarios"
]
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

if seleccion == "Dashboard":
    st.title("📊 Panel Principal")
    st.write("Bienvenido a tu Sistema de Control Contable.")
    
    col1, col2, col3 = st.columns(3)
    
    clientes_df = db.obtener_clientes()
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
    
    tab1, tab2 = st.tabs(["Directorio y Obligaciones", "Agregar Cliente Nuevo"])
    
    with tab1:
        st.subheader(f"Lista de Personas {tipo_persona}s")
        clientes_df = db.obtener_clientes(tipo_persona)
        
        if clientes_df.empty:
            st.info(f"No hay personas {tipo_persona.lower()}s registradas.")
        else:
            st.dataframe(clientes_df, use_container_width=True, hide_index=True)
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
        clientes_df = db.obtener_clientes()
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
    
    clientes_df = db.obtener_clientes()
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
                                     pdf_bytes = rg.generar_pdf(datos_cliente, "Mes Actual", resultados, df_facturas)
                                     st.download_button("📄 Descargar Reporte en PDF para el Cliente", data=pdf_bytes, file_name=f"Reporte_Impuestos_{rfc_cliente}.pdf", mime="application/pdf", type="primary")
                       except Exception as e:
                           st.error(f"Ocurrió un error al procesar: {e}")
                           st.code(traceback.format_exc())

elif seleccion == "Expediente de Cliente":
    st.title("📂 Historial y Análisis del Cliente")
    
    clientes_df = db.obtener_clientes()
    if clientes_df.empty:
        st.warning("No hay clientes registrados en el sistema.")
    else:
        clientes_df['nombre_display'] = clientes_df['nombre'] + " - " + clientes_df['rfc']
        opciones_cli = dict(zip(clientes_df['nombre_display'], clientes_df['id']))
        cliente_seleccionado = st.selectbox("Buscar Cliente:", list(opciones_cli.keys()))
        
        cliente_id = opciones_cli[cliente_seleccionado]
        datos_cliente = clientes_df[clientes_df['id'] == cliente_id].iloc[0]
        
        st.write("---")
        st.subheader(f"👤 {datos_cliente['nombre']}")
        col1, col2 = st.columns(2)
        with col1:
             st.write(f"**RFC:** {datos_cliente['rfc']} | **Régimen:** {datos_cliente['regimen']}")
        with col2:
             st.write(f"**Email:** {datos_cliente['email']} | **Teléfono:** {datos_cliente['telefono']}")
             
        # Mock Gráfica Financiera
        st.write("---")
        st.subheader("📊 Análisis Financiero Histórico")
        st.caption("Visualización de Ingresos vs Gastos a lo largo del año (Datos Demo). En el futuro, esto se alimentará del histórico de XMLs procesados.")
        
        # Generar datos demo para Plotly
        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
        ingresos_demo = [50000, 60000, 45000, 70000, 65000, 80000]
        gastos_demo = [30000, 40000, 35000, 50000, 40000, 60000]
        df_chart = pd.DataFrame({'Mes': meses, 'Ingresos': ingresos_demo, 'Gastos': gastos_demo})
        
        fig = px.bar(df_chart, x='Mes', y=['Ingresos', 'Gastos'], barmode='group', color_discrete_map={'Ingresos': 'green', 'Gastos': 'red'})
        st.plotly_chart(fig, use_container_width=True)
             
        st.write("---")
        st.subheader("🔐 Bóveda de Accesos y Contraseñas")
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

elif seleccion == "Control de Honorarios":
    st.title("💼 Control de Honorarios del Despacho")
    st.write("Administra la cobranza de igualas mensuales o servicios extraordinarios de tus clientes.")
    
    clientes_df = db.obtener_clientes()
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
