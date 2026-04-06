import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

search = """            df_merged = procesar_obligaciones_del_mes(obligaciones_df, mes_objetivo=mes_actual, anio_objetivo=anio_actual)
            ob_semaforo = calcular_semaforo(df_merged)

            # Preparar eventos para el calendario"""

replace = """            df_merged = procesar_obligaciones_del_mes(obligaciones_df, mes_objetivo=mes_actual, anio_objetivo=anio_actual)
            ob_semaforo = calcular_semaforo(df_merged)

            # --- Integración Kanban ---
            with st.expander("Integración con Kanban"):
                st.write(f"Vuelca las obligaciones pendientes de {mes_seleccionado_nombre} {anio_actual} al Tablero Kanban de tu equipo.")
                if st.button(f"Generar Tarjetas Kanban para {mes_seleccionado_nombre}", type="primary", use_container_width=True):
                    pendientes_kanban = df_merged[pd.isna(df_merged['fecha_de_entrega'])]
                    if pendientes_kanban.empty:
                        st.info("No hay obligaciones pendientes para generar en Kanban.")
                    else:
                        tareas_generadas = 0
                        # Validar las tareas existentes para no duplicar
                        df_tareas_existentes = db.obtener_tareas_kanban()
                        # Buscar admin (fallback)
                        admin_id = None
                        df_usr = db.obtener_usuarios_despacho()
                        if not df_usr.empty:
                            df_admin = df_usr[df_usr['rol'] == 'Administrador']
                            if not df_admin.empty:
                                admin_id = int(df_admin.iloc[0]['id'])

                        # Obtener asignaciones
                        import sqlite3
                        conn_k = sqlite3.connect(db.DB_NAME)
                        df_asig = pd.read_sql_query("SELECT * FROM asignaciones_clientes", conn_k)
                        conn_k.close()

                        for _, row in pendientes_kanban.iterrows():
                            o_id = int(row['id_x'])
                            c_id = int(row['cliente_id'])
                            desc = f"{row['descripcion']} ({mes_seleccionado_nombre} {anio_actual})"

                            # Validar si ya existe
                            if not df_tareas_existentes.empty:
                                if not df_tareas_existentes[(df_tareas_existentes['obligacion_id'] == o_id) &
                                                            (df_tareas_existentes['mes_objetivo'] == mes_actual) &
                                                            (df_tareas_existentes['anio_objetivo'] == anio_actual)].empty:
                                    continue # Ya existe

                            # Decidir a quién asignar
                            asig_val = admin_id
                            if not df_asig.empty:
                                asigs_cliente = df_asig[df_asig['cliente_id'] == c_id]
                                if not asigs_cliente.empty:
                                    asig_val = int(asigs_cliente.iloc[0]['usuario_id'])

                            db.crear_tarea_kanban(c_id, desc, asig_val, o_id, mes_actual, anio_actual)
                            tareas_generadas += 1

                        if tareas_generadas > 0:
                            st.success(f"Se generaron {tareas_generadas} tarjetas en la columna 'Por Revisar' del Tablero Kanban.")
                        else:
                            st.info("Todas las tareas pendientes de este mes ya estaban generadas en Kanban.")

            # Preparar eventos para el calendario"""

content = content.replace(search, replace)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
