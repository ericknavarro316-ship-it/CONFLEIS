import json
import database as db

# Crear función para obtener info del organigrama en el script
def inject_organigrama(app_file):
    with open(app_file, 'r') as f:
        content = f.read()

    new_module = '''
elif seleccion == "Gestión de Equipo (Admin)":
    st.title("👥 Gestión de Equipo (Roles y Accesos)")
    tab_users, tab_roles, tab_assign, tab_org = st.tabs(["Usuarios", "Roles y Permisos", "Asignación de Clientes", "Organigrama"])
    
    with tab_users:
        col_new, col_list = st.columns([1, 2])
        df_roles = db.obtener_roles()
        df_users = db.obtener_usuarios_despacho()
        
        with col_new:
            st.subheader("Registrar/Editar Usuario")
            with st.form("form_usuario"):
                # Lista de usuarios existentes
                opciones_user = ["--- Crear Nuevo ---"] + df_users['usuario'].tolist() if not df_users.empty else ["--- Crear Nuevo ---"]
                user_sel = st.selectbox("Seleccionar Acción", opciones_user)
                
                # Valores por defecto
                def_nom, def_usr, def_rol_id, def_rep = "", "", 2, None
                is_edit = user_sel != "--- Crear Nuevo ---"
                
                if is_edit:
                    u_row = df_users[df_users['usuario'] == user_sel].iloc[0]
                    def_nom, def_usr = u_row['nombre'], u_row['usuario']
                    def_rol_id = int(u_row['rol_id'])
                    def_rep = u_row['reporta_a_id']
                
                nombre_u = st.text_input("Nombre Completo", value=def_nom)
                usuario_u = st.text_input("Usuario (Login)", value=def_usr, disabled=is_edit)
                pass_label = "Nueva Contraseña (Dejar en blanco para no cambiar)" if is_edit else "Contraseña"
                pass_u = st.text_input(pass_label, type="password")
                
                # Opciones de rol y supervisor
                if not df_roles.empty:
                    nombres_roles = df_roles['nombre_rol'].tolist()
                    idx_rol = nombres_roles.index(df_roles[df_roles['id'] == def_rol_id]['nombre_rol'].values[0]) if def_rol_id in df_roles['id'].values else 0
                    rol_sel = st.selectbox("Puesto / Rol", nombres_roles, index=idx_rol)
                else:
                    rol_sel = None
                    st.warning("No hay roles creados.")
                
                if not df_users.empty:
                    # Supervisor no puede ser uno mismo
                    opciones_super = [("Ninguno", None)] + [(row['nombre'], row['id']) for _, row in df_users.iterrows() if not is_edit or row['usuario'] != user_sel]
                    idx_sup = 0
                    for i, (_, s_id) in enumerate(opciones_super):
                        if s_id == def_rep:
                            idx_sup = i
                            break
                    sup_sel = st.selectbox("Reporta a (Supervisor)", [x[0] for x in opciones_super], index=idx_sup)
                else:
                    sup_sel = "Ninguno"
                
                if st.form_submit_button("Guardar Usuario"):
                    if nombre_u and usuario_u and rol_sel:
                        r_id = df_roles[df_roles['nombre_rol'] == rol_sel]['id'].values[0]
                        s_id = next((s_id for s_name, s_id in opciones_super if s_name == sup_sel), None) if not df_users.empty else None
                        
                        if is_edit:
                            ok, msg = db.actualizar_usuario_despacho(int(u_row['id']), nombre_u, usuario_u, r_id, s_id, pass_u if pass_u else None)
                        else:
                            if not pass_u:
                                ok, msg = False, "Contraseña es requerida para nuevo usuario."
                            else:
                                ok, msg = db.agregar_usuario_despacho(nombre_u, usuario_u, pass_u, r_id, s_id)
                        if ok: st.success(msg); st.rerun()
                        else: st.error(msg)
                    else:
                        st.warning("Completa todos los campos básicos.")
                        
        with col_list:
            st.subheader("Directorio del Staff")
            if not df_users.empty:
                st.dataframe(df_users[['nombre', 'usuario', 'rol']], use_container_width=True, hide_index=True)
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
            with st.form("form_rol"):
                opciones_r = ["--- Crear Nuevo ---"] + df_roles['nombre_rol'].tolist() if not df_roles.empty else ["--- Crear Nuevo ---"]
                r_sel = st.selectbox("Acción", opciones_r)
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
                permisos_seleccionados = []
                for mod in todos_modulos:
                    if st.checkbox(mod, value=(mod in def_rperm)):
                        permisos_seleccionados.append(mod)
                
                if st.form_submit_button("Guardar Puesto"):
                    if nom_r:
                        if is_r_edit:
                            db.actualizar_rol(int(r_row['id']), nom_r, jer_r, permisos_seleccionados)
                            st.success("Rol actualizado.")
                        else:
                            ok, m = db.agregar_rol(nom_r, jer_r, permisos_seleccionados)
                            if ok: st.success(m)
                            else: st.error(m)
                        st.rerun()
                    else:
                        st.warning("El nombre es obligatorio.")
        
        with col_rlist:
            st.subheader("Puestos Actuales")
            if not df_roles.empty:
                st.dataframe(df_roles[['nombre_rol', 'nivel_jerarquia']], use_container_width=True, hide_index=True)
            
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
            # Crear nodos simples
            org_data = []
            for _, r in df_users.iterrows():
                sup_name = df_users[df_users['id'] == r['reporta_a_id']]['nombre'].values[0] if pd.notna(r['reporta_a_id']) else ""
                org_data.append({"Nombre": r['nombre'], "Puesto": r['rol'], "Reporta_A": sup_name})
            
            df_org = pd.DataFrame(org_data)
            st.dataframe(df_org, use_container_width=True, hide_index=True)
            st.info("💡 En una versión futura podemos integrar un gráfico interactivo (Ej. Treemap) usando Plotly con esta estructura.")
'''

    # Encontrar bloque original de Gestión de Equipo y reemplazarlo
    start_str = 'if seleccion == "Gestión de Equipo (Admin)":'
    end_str = 'if seleccion == "Descarga Masiva SAT (Simulador)":'
    
    start_idx = content.find(start_str)
    end_idx = content.find(end_str)
    
    if start_idx != -1 and end_idx != -1:
        new_content = content[:start_idx] + new_module + "\n" + content[end_idx:]
        with open(app_file, 'w') as f:
            f.write(new_content)
        print("Módulo de Gestión de Equipo reemplazado con éxito.")
    else:
        print("No se encontró el bloque para reemplazar.")

inject_organigrama('app.py')
