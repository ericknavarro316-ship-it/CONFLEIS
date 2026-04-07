import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

search = """            st.write(f"**Email:** {datos_cliente['email']} | **Teléfono:** {datos_cliente['telefono']}")

            # Mostrar Empleado y Supervisor
            # Si hay un servicio principal, mostrar el encargado (asumiendo que el que está asignado es el operativo)
            asignaciones_str = "No asignado"
            supervisor_str = "N/A"
            df_usuarios = db.obtener_usuarios_despacho()
            if not df_usuarios.empty:
                # Buscar en asignaciones
                conn = db.sqlite3.connect(db.DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT usuario_id FROM asignaciones_clientes WHERE cliente_id = ?", (cliente_id,))
                rows = cursor.fetchall()
                conn.close()
                if rows:
                     ids_asignados = [row[0] for row in rows]
                     asignados = df_usuarios[df_usuarios['id'].isin(ids_asignados)]
                     if not asignados.empty:
                          nombres_asignados = asignados['nombre'].tolist()
                          asignaciones_str = ", ".join(nombres_asignados)

                          # Tomar el supervisor del primer asignado
                          primer_asig = asignados.iloc[0]
                          if pd.notna(primer_asig['reporta_a_id']):
                               superv = df_usuarios[df_usuarios['id'] == primer_asig['reporta_a_id']]
                               if not superv.empty:
                                    supervisor_str = superv['nombre'].values[0]

            st.markdown(f"**Responsable(s):** {asignaciones_str} | **Supervisor:** {supervisor_str}")"""

replace = """            st.write(f"**Email:** {datos_cliente['email']} | **Teléfono:** {datos_cliente['telefono']}")

            # Mostrar Empleado y Supervisor
            asignaciones_str = "No asignado"
            supervisor_str = "N/A"
            ids_asignados = []
            df_usuarios = db.obtener_usuarios_despacho()
            if not df_usuarios.empty:
                # Buscar en asignaciones
                conn = db.sqlite3.connect(db.DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT usuario_id FROM asignaciones_clientes WHERE cliente_id = ?", (cliente_id,))
                rows = cursor.fetchall()
                conn.close()
                if rows:
                     ids_asignados = [row[0] for row in rows]
                     asignados = df_usuarios[df_usuarios['id'].isin(ids_asignados)]
                     if not asignados.empty:
                          nombres_asignados = asignados['nombre'].tolist()
                          asignaciones_str = ", ".join(nombres_asignados)

                          # Tomar el supervisor del primer asignado
                          primer_asig = asignados.iloc[0]
                          if pd.notna(primer_asig['reporta_a_id']):
                               superv = df_usuarios[df_usuarios['id'] == primer_asig['reporta_a_id']]
                               if not superv.empty:
                                    supervisor_str = superv['nombre'].values[0]

            st.markdown(f"**Responsable(s):** {asignaciones_str} | **Supervisor:** {supervisor_str}")

            # Formulario de edición rápida
            with st.popover("✏️ Editar Perfil del Cliente"):
                with st.form(f"edit_profile_{cliente_id}"):
                    nuevo_email = st.text_input("Email", value=datos_cliente['email'])
                    nuevo_telefono = st.text_input("Teléfono", value=datos_cliente['telefono'])

                    opciones_responsables = df_usuarios['nombre'].tolist() if not df_usuarios.empty else []
                    seleccionados_nombres = []
                    if ids_asignados and not df_usuarios.empty:
                         seleccionados_nombres = df_usuarios[df_usuarios['id'].isin(ids_asignados)]['nombre'].tolist()

                    nuevos_resp = st.multiselect("Responsables Asignados", options=opciones_responsables, default=seleccionados_nombres)

                    if st.form_submit_button("Guardar Cambios"):
                        # Actualizar email y telefono
                        conn = db.sqlite3.connect(db.DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE clientes SET email = ?, telefono = ? WHERE id = ?", (nuevo_email, nuevo_telefono, cliente_id))
                        conn.commit()

                        # Actualizar asignaciones
                        cursor.execute("DELETE FROM asignaciones_clientes WHERE cliente_id = ?", (cliente_id,))
                        if nuevos_resp:
                            ids_nuevos = df_usuarios[df_usuarios['nombre'].isin(nuevos_resp)]['id'].tolist()
                            for uid in ids_nuevos:
                                cursor.execute("INSERT INTO asignaciones_clientes (usuario_id, cliente_id) VALUES (?, ?)", (int(uid), cliente_id))
                        conn.commit()
                        conn.close()
                        st.success("Perfil actualizado.")
                        st.rerun()"""

content = content.replace(search, replace)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
