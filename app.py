import streamlit as st
import pandas as pd
from datetime import datetime, date
import database as db
import pdf_extractor as pex

# Configuración de página
st.set_page_config(page_title="Sistema Contable de Despacho", page_icon="📈", layout="wide")

# Inicializar Base de Datos
db.init_db()

# Importar nuevos módulos
import xml_processor as xp
import tax_calculator as tc
import report_generator as rg
import traceback

# Menú lateral
st.sidebar.title("Navegación")
opciones = ["Dashboard", "Personas Físicas", "Personas Morales", "Cálculo de Impuestos y XML", "Calendario General", "Expediente de Cliente"]
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
    
    # Reordenar columnas para mostrar el semáforo al principio
    cols = ['id', 'Cliente', 'semaforo', 'descripcion', 'fecha_limite', 'estado', 'notas']
    return df[cols]

def estilo_semaforo(val):
    """Aplica colores CSS según el semáforo o el estado."""
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
    
    # KPIs rápidos
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
        # Filtrar solo las que están pendientes y que vencen en <= 3 días o ya vencieron
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

def mostrar_modulo_clientes(tipo_persona):
    """
    Función para renderizar la pantalla de Físicas o Morales.
    """
    st.title(f"🏢 Módulo de Personas {tipo_persona}s")
    
    tab1, tab2 = st.tabs(["Directorio y Obligaciones", "Agregar Cliente Nuevo"])
    
    with tab1:
        st.subheader(f"Lista de Personas {tipo_persona}s")
        clientes_df = db.obtener_clientes(tipo_persona)
        
        if clientes_df.empty:
            st.info(f"No hay personas {tipo_persona.lower()}s registradas.")
        else:
            st.dataframe(clientes_df, use_container_width=True, hide_index=True)
            
            # Opción para eliminar cliente
            st.write("---")
            with st.expander("Eliminar Cliente"):
                opciones_eliminar = dict(zip(clientes_df['nombre'], clientes_df['id']))
                cliente_a_eliminar = st.selectbox(f"Selecciona un cliente para eliminar:", list(opciones_eliminar.keys()), key=f"eliminar_cliente_{tipo_persona}")
                if st.button("Eliminar", key=f"btn_elim_{tipo_persona}"):
                    id_eliminar = opciones_eliminar[cliente_a_eliminar]
                    db.eliminar_cliente(id_eliminar)
                    st.success(f"Cliente '{cliente_a_eliminar}' eliminado exitosamente.")
                    st.rerun()
                
        # Mostrar Obligaciones filtradas
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
        
        # Valores por defecto para el formulario
        default_rfc = ""
        default_nombre = ""
        default_regimen = ""
        
        if pdf_file is not None:
             datos_extraidos, msj = pex.extraer_datos_constancia(pdf_file)
             if datos_extraidos["rfc"]:
                 st.success("¡Datos extraídos de la Constancia con éxito!")
                 default_rfc = datos_extraidos.get("rfc", "")
                 default_nombre = datos_extraidos.get("nombre", "")
                 default_regimen = datos_extraidos.get("regimen", "")
                 
                 # Si el PDF era de un tipo diferente
                 if datos_extraidos.get("tipo_persona") != tipo_persona:
                      st.warning(f"¡Atención! El RFC indica que es Persona {datos_extraidos.get('tipo_persona')}, pero estás en el módulo de Personas {tipo_persona}s. Se guardará como Persona {tipo_persona} según este formulario.")
             else:
                 st.error("No se pudieron extraer datos del PDF. Tal vez el formato es incorrecto o es una imagen escaneada.")

        with st.form(f"nuevo_cliente_{tipo_persona}"):
            nombre = st.text_input("Nombre / Razón Social *", value=default_nombre)
            rfc = st.text_input("RFC *", value=default_rfc)
            
            if tipo_persona == "Física":
                regimenes = [
                    "Sueldos y Salarios", 
                    "Actividad Empresarial y Profesional", 
                    "Régimen Simplificado de Confianza (RESICO)",
                    "Arrendamiento",
                    "Plataformas Tecnológicas",
                    "Otro"
                ]
            else:
                regimenes = [
                    "Persona Moral - Régimen General",
                    "Persona Moral - RESICO",
                    "Organización Sin Fines de Lucro",
                    "Otro"
                ]
            
            try:
                reg_index = regimenes.index(default_regimen) if default_regimen in regimenes else 0
            except ValueError:
                reg_index = 0
                
            regimen = st.selectbox("Régimen Fiscal Principal", regimenes, index=reg_index)
            if default_regimen and default_regimen not in regimenes:
                 st.info(f"Régimen detectado en PDF: {default_regimen}. Por favor selecciona o confirma arriba.")
            
            email = st.text_input("Correo Electrónico")
            telefono = st.text_input("Teléfono")
            
            enviar = st.form_submit_button("Guardar Cliente")
            
            if enviar:
                if not nombre or not rfc:
                    st.error("Los campos Nombre y RFC son obligatorios.")
                else:
                    if len(rfc) < 12 or len(rfc) > 13:
                        st.warning("El RFC suele tener 12 (Morales) o 13 (Físicas) caracteres.")
                    
                    exito, mensaje = db.agregar_cliente(nombre, rfc.upper(), tipo_persona, regimen, email, telefono)
                    if exito:
                        st.success(mensaje)
                        st.rerun()
                    else:
                        st.error(mensaje)

if seleccion == "Personas Físicas":
     mostrar_modulo_clientes("Física")

elif seleccion == "Personas Morales":
     mostrar_modulo_clientes("Moral")

elif seleccion == "Calendario General":
    st.title("📅 Calendario General de Obligaciones")
    
    tab1, tab2 = st.tabs(["Panel General", "Asignar Obligación"])
    
    with tab1:
        st.subheader("Todas las Obligaciones por Cumplir")
        obligaciones_df = db.obtener_obligaciones() # Sin filtro de tipo
        
        if obligaciones_df.empty:
            st.info("No hay obligaciones asignadas. Ve a la pestaña 'Asignar Obligación'.")
        else:
            ob_semaforo = calcular_semaforo(obligaciones_df)
            
            # Filtro por estado
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
                opciones_act = dict(zip(
                    obligaciones_df['Cliente'] + " - " + obligaciones_df['descripcion'], 
                    obligaciones_df['id']
                ))
                if opciones_act:
                    obl_a_act = st.selectbox("Selecciona la obligación:", list(opciones_act.keys()))
                    nuevo_estado = st.selectbox("Nuevo Estado:", ["Pendiente", "Completada"])
                    if st.button("Actualizar", key="btn_act_gral"):
                        id_act = opciones_act[obl_a_act]
                        db.actualizar_estado_obligacion(id_act, nuevo_estado)
                        st.success("Estado actualizado exitosamente.")
                        st.rerun()
            
            with col2:
                st.write("**Eliminar Obligación**")
                if opciones_act:
                    obl_a_elim = st.selectbox("Selecciona la obligación a eliminar:", list(opciones_act.keys()), key="sel_elim_gral")
                    if st.button("Eliminar", key="btn_elim_gral"):
                        id_elim = opciones_act[obl_a_elim]
                        db.eliminar_obligacion(id_elim)
                        st.success("Obligación eliminada exitosamente.")
                        st.rerun()
                        
    with tab2:
        st.subheader("Asignar Nueva Obligación")
        clientes_df = db.obtener_clientes()
        
        if clientes_df.empty:
            st.warning("Primero debes registrar clientes.")
        else:
            with st.form("nueva_obligacion"):
                # Mostrar el tipo de persona al lado del nombre
                clientes_df['nombre_display'] = clientes_df['nombre'] + " (" + clientes_df['tipo_persona'] + ")"
                nombres_clientes = dict(zip(clientes_df['nombre_display'], clientes_df['id']))
                cliente_seleccionado = st.selectbox("Cliente *", list(nombres_clientes.keys()))
                
                obligaciones_comunes = [
                    "Declaración Mensual IVA e ISR",
                    "Declaración Anual",
                    "Cálculo de Nómina y Retenciones",
                    "Envío de DIOT",
                    "Pago SUA/IMSS",
                    "Declaración Informativa Múltiple",
                    "Otro"
                ]
                descripcion = st.selectbox("Tipo de Obligación", obligaciones_comunes)
                if descripcion == "Otro":
                    descripcion = st.text_input("Especifica la obligación:")
                
                fecha_limite = st.date_input("Fecha Límite *")
                notas = st.text_area("Notas o Detalles (Opcional)")
                
                enviar_obl = st.form_submit_button("Asignar Obligación")
                
                if enviar_obl:
                    cliente_id = nombres_clientes[cliente_seleccionado]
                    if not descripcion:
                        st.error("Debes especificar la descripción de la obligación.")
                    else:
                        db.agregar_obligacion(cliente_id, descripcion, fecha_limite, notas)
                        st.success(f"Obligación asignada exitosamente.")
                        st.rerun()

elif seleccion == "Expediente de Cliente":
    st.title("📂 Historial y Expediente del Cliente")
    
    clientes_df = db.obtener_clientes()
    if clientes_df.empty:
        st.warning("No hay clientes registrados en el sistema.")
    else:
        # Buscador de clientes
        clientes_df['nombre_display'] = clientes_df['nombre'] + " - " + clientes_df['rfc']
        opciones_cli = dict(zip(clientes_df['nombre_display'], clientes_df['id']))
        cliente_seleccionado = st.selectbox("Buscar Cliente:", list(opciones_cli.keys()))
        
        cliente_id = opciones_cli[cliente_seleccionado]
        datos_cliente = clientes_df[clientes_df['id'] == cliente_id].iloc[0]
        
        st.write("---")
        
        # Tarjeta de Info del Cliente
        st.subheader(f"👤 {datos_cliente['nombre']}")
        col1, col2 = st.columns(2)
        with col1:
             st.write(f"**RFC:** {datos_cliente['rfc']}")
             st.write(f"**Tipo:** Persona {datos_cliente['tipo_persona']}")
             st.write(f"**Régimen:** {datos_cliente['regimen']}")
        with col2:
             st.write(f"**Email:** {datos_cliente['email']}")
             st.write(f"**Teléfono:** {datos_cliente['telefono']}")
             st.write(f"**Registrado desde:** {datos_cliente['fecha_registro']}")
             
        st.write("---")
        
        # Bóveda de Accesos
        st.subheader("🔐 Bóveda de Accesos y Contraseñas")
        cred_df = db.obtener_credenciales(cliente_id)
        
        with st.expander("Ver Accesos Guardados"):
             if cred_df.empty:
                 st.info("No hay accesos guardados para este cliente.")
             else:
                 for _, row in cred_df.iterrows():
                     with st.container(border=True):
                         ccol1, ccol2, ccol3 = st.columns([2, 2, 1])
                         with ccol1:
                             st.write(f"**Portal/Acceso:** {row['tipo_acceso']}")
                             st.write(f"**Usuario:** {row['usuario']}")
                         with ccol2:
                             # Campo de contraseña oculto que se muestra con checkbox
                             mostrar_pw = st.checkbox("Mostrar Contraseña", key=f"show_pw_{row['id']}")
                             if mostrar_pw:
                                 st.code(row['contrasena'])
                             else:
                                 st.code("********")
                             if row['notas']:
                                 st.caption(f"Notas: {row['notas']}")
                         with ccol3:
                             if st.button("Eliminar", key=f"del_cred_{row['id']}"):
                                 db.eliminar_credencial(row['id'])
                                 st.rerun()
                                 
        with st.expander("Agregar Nuevo Acceso"):
             with st.form("nueva_credencial"):
                 tipo_acceso = st.selectbox("Tipo de Acceso", ["CIEC (SAT)", "FIEL (Vencimiento)", "IMSS (IDSE)", "SIPARE", "Portal Estatal", "Otro"])
                 if tipo_acceso == "Otro" or tipo_acceso == "FIEL (Vencimiento)":
                      notas_acceso = st.text_input("Especificar Detalles / Fecha de Vencimiento")
                 else:
                      notas_acceso = ""
                      
                 usuario = st.text_input("Usuario / RFC")
                 contrasena = st.text_input("Contraseña", type="password")
                 notas_gen = st.text_area("Notas Adicionales")
                 
                 # Concatenar notas
                 notas_finales = f"{notas_acceso} - {notas_gen}".strip(" - ")
                 
                 if st.form_submit_button("Guardar Acceso de Forma Segura"):
                      if not tipo_acceso or not contrasena:
                          st.error("El tipo de acceso y la contraseña son obligatorios.")
                      else:
                          db.agregar_credencial(cliente_id, tipo_acceso, usuario, contrasena, notas_finales)
                          st.success("Acceso guardado.")
                          st.rerun()

        st.write("---")
        
        # Historial de Obligaciones del Cliente
        st.subheader("📋 Historial de Obligaciones")
        obs_cliente = db.obtener_obligaciones(cliente_id=cliente_id)
        
        if obs_cliente.empty:
             st.info("Este cliente no tiene obligaciones registradas.")
        else:
             ob_semaforo_cli = calcular_semaforo(obs_cliente)
             # Ocultar la columna cliente porque ya sabemos de quién es
             cols_to_show = [c for c in ob_semaforo_cli.columns if c not in ['id', 'Cliente']]
             st.dataframe(
                 ob_semaforo_cli[cols_to_show].style.applymap(estilo_semaforo, subset=['semaforo', 'estado']),
                 use_container_width=True, hide_index=True
             )

elif seleccion == "Cálculo de Impuestos y XML":
    st.title("🧮 Cálculo Automático de Impuestos (XML)")
    st.write("Sube los XMLs (CFDI) de Ingresos y Gastos del mes para calcular automáticamente el IVA y el ISR, y generar el reporte del cliente.")
    
    clientes_df = db.obtener_clientes()
    if clientes_df.empty:
        st.warning("No hay clientes registrados en el sistema.")
    else:
        # Selector de cliente
        clientes_df['nombre_display'] = clientes_df['nombre'] + " - " + clientes_df['rfc']
        opciones_cli = dict(zip(clientes_df['nombre_display'], clientes_df['id']))
        cliente_seleccionado = st.selectbox("Selecciona un Cliente:", list(opciones_cli.keys()))
        
        cliente_id = opciones_cli[cliente_seleccionado]
        datos_cliente = clientes_df[clientes_df['id'] == cliente_id].iloc[0]
        rfc_cliente = datos_cliente['rfc']
        tipo_persona = datos_cliente['tipo_persona']
        regimen_cliente = datos_cliente['regimen']
        
        st.write(f"**Régimen:** {regimen_cliente} | **Tipo:** {tipo_persona}")
        
        st.write("---")
        
        # Subir archivos XML
        st.subheader("1. Subir Facturas (XML)")
        archivos_xml = st.file_uploader(
             "Sube todos los XMLs del mes (Ventas y Compras)", 
             type=["xml"], 
             accept_multiple_files=True
        )
        
        if archivos_xml:
             if st.button("Procesar y Calcular"):
                  with st.spinner("Procesando XMLs..."):
                       # 1. Procesar XMLs
                       try:
                           df_facturas = xp.procesar_lote_xmls(archivos_xml, rfc_cliente)
                           
                           if df_facturas.empty:
                                st.error("No se encontraron facturas válidas o relacionadas a este RFC.")
                           else:
                                st.success(f"Se procesaron {len(df_facturas)} facturas correctamente.")
                                
                                # 2. Mostrar detalle de facturas
                                with st.expander("Ver Detalle de Facturas (Solo lectura)"):
                                     st.dataframe(df_facturas)
                                
                                # 3. Resumir y Calcular Impuestos
                                st.write("---")
                                st.subheader("2. Resumen Financiero Mensual (Base Flujo / PUE)")
                                
                                resumen_mensual = xp.resumir_facturas(df_facturas)
                                if not resumen_mensual:
                                     st.warning("No se encontraron facturas PUE (Pagadas/Cobradas) para calcular impuestos base flujo.")
                                else:
                                     resultados = tc.calcular_impuestos(resumen_mensual, regimen_cliente, tipo_persona)
                                     
                                     col1, col2 = st.columns(2)
                                     with col1:
                                          st.metric("Total Ingresos (Cobrados)", f"$ {resultados['Ingresos_Totales']:,.2f}")
                                          st.metric("Utilidad / Base Gravable", f"$ {resultados['Utilidad_Fiscal_Base']:,.2f}")
                                          
                                          st.write("**Desglose de IVA**")
                                          st.write(f"IVA Cobrado: $ {resultados['IVA_Cobrado']:,.2f}")
                                          st.write(f"IVA Pagado: $ {resultados['IVA_Pagado']:,.2f}")
                                          st.write(f"IVA Retenido: $ {resultados['IVA_Retenido']:,.2f}")
                                          
                                     with col2:
                                          st.metric("Total Gastos (Pagados)", f"$ {resultados['Gastos_Totales']:,.2f}")
                                          st.write("**Desglose de ISR**")
                                          st.write(f"ISR Determinado: $ {resultados['ISR_Determinado']:,.2f} (Tasa: {resultados['Tasa_ISR_Aplicada']})")
                                          st.write(f"ISR Retenido: $ {resultados['ISR_Retenido']:,.2f}")
                                          
                                     st.write("---")
                                     st.subheader("3. Impuestos a Pagar / a Favor")
                                     
                                     c1, c2, c3 = st.columns(3)
                                     
                                     with c1:
                                          if resultados['IVA_A_Favor'] > 0:
                                               st.success(f"IVA a Favor: $ {resultados['IVA_A_Favor']:,.2f}")
                                          else:
                                               st.error(f"IVA a Pagar: $ {resultados['IVA_A_Pagar']:,.2f}")
                                               
                                     with c2:
                                          if resultados['ISR_A_Favor'] > 0:
                                               st.success(f"ISR a Favor: $ {resultados['ISR_A_Favor']:,.2f}")
                                          else:
                                               st.error(f"ISR a Pagar: $ {resultados['ISR_A_Pagar']:,.2f}")
                                               
                                     with c3:
                                          st.metric(
                                              "TOTAL IMPUESTOS A PAGAR", 
                                              f"$ {resultados['Total_Impuestos_A_Pagar']:,.2f}",
                                              delta="A pagar al SAT",
                                              delta_color="inverse"
                                          )
                                          
                                     # 4. Generar Reporte PDF
                                     st.write("---")
                                     st.subheader("4. Generar Reporte para el Cliente")
                                     
                                     # Extraer un mes y año representativo de la primera factura
                                     try:
                                          mes_str = df_facturas.iloc[0]["Mes_Anio"]
                                     except:
                                          mes_str = "Mes Actual"
                                          
                                     pdf_bytes = rg.generar_pdf(datos_cliente, mes_str, resultados, df_facturas)
                                     
                                     st.download_button(
                                          label="📄 Descargar Reporte en PDF",
                                          data=pdf_bytes,
                                          file_name=f"Reporte_Impuestos_{rfc_cliente}_{mes_str}.pdf",
                                          mime="application/pdf",
                                          type="primary"
                                     )
                       except Exception as e:
                           st.error(f"Ocurrió un error al procesar: {e}")
                           st.code(traceback.format_exc())
