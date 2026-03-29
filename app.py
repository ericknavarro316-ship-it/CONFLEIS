import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
import pdf_extractor as pex

# Configuración de página
st.set_page_config(page_title="Sistema Contable de Despacho", page_icon="📈", layout="wide")

# Inicializar Base de Datos
db.init_db()

# Menú lateral
st.sidebar.title("Navegación")
opciones = ["Dashboard", "Personas Físicas", "Personas Morales", "Calendario General"]
seleccion = st.sidebar.radio("Ir a:", opciones)

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
            st.subheader("Eliminar Cliente")
            opciones_eliminar = dict(zip(clientes_df['nombre'], clientes_df['id']))
            cliente_a_eliminar = st.selectbox(f"Selecciona un cliente para eliminar:", list(opciones_eliminar.keys()), key=f"eliminar_cliente_{tipo_persona}")
            if st.button("Eliminar", key=f"btn_elim_{tipo_persona}"):
                id_eliminar = opciones_eliminar[cliente_a_eliminar]
                db.eliminar_cliente(id_eliminar)
                st.success(f"Cliente '{cliente_a_eliminar}' eliminado exitosamente.")
                st.rerun()
                
        # Mostrar Obligaciones filtradas
        st.write("---")
        st.subheader("Obligaciones de este Módulo")
        obligaciones_df = db.obtener_obligaciones(tipo_persona)
        if not obligaciones_df.empty:
             def color_estado(val):
                 color = 'green' if val == 'Completada' else 'red'
                 return f'color: {color}'
                 
             st.dataframe(
                 obligaciones_df.style.applymap(color_estado, subset=['estado']),
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
                 
                 # Si el PDF era de un tipo diferente al que estamos intentando agregar
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
            
            # Si el pdf extrajo un regimen que no está, lo ponemos en "Otro" y dejamos que el usuario lo cambie o agregue
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
            # Filtro por estado
            estado_filtro = st.selectbox("Filtrar por estado", ["Todos", "Pendiente", "Completada"])
            if estado_filtro != "Todos":
                obligaciones_df = obligaciones_df[obligaciones_df["estado"] == estado_filtro]
            
            # Resaltar filas según su estado o fecha
            def color_estado(val):
                color = 'green' if val == 'Completada' else 'red'
                return f'color: {color}'
                
            st.dataframe(
                obligaciones_df.style.applymap(color_estado, subset=['estado']),
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
