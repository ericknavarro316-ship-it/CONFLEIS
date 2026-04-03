import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

search = """            if df_mostrar.empty:
                st.write("No hay tareas para esta selección.")
            else:
                cols_mostrar = ['Cliente', 'descripcion', 'fecha_limite', 'semaforo']
                df_ui = df_mostrar[cols_mostrar].copy()
                df_ui['fecha_limite'] = df_ui['fecha_limite'].dt.strftime('%Y-%m-%d')

                st.dataframe(
                    df_ui.style.map(estilo_semaforo, subset=['semaforo']),
                    use_container_width=True, hide_index=True
                )

                # Acciones Rápidas (Marcar como Completada)
                pendientes = df_mostrar[pd.isna(df_mostrar['fecha_de_entrega'])]
                if not pendientes.empty:
                    st.write("**Marcar Obligación como Completada Hoy**")
                    opciones_act = dict(zip(pendientes['Cliente'] + " - " + pendientes['descripcion'], zip(pendientes['id_x'], pendientes['mes_objetivo'], pendientes['anio_objetivo'])))

                    with st.form("completar_tarea"):
                        obl_a_act = st.selectbox("Selecciona la obligación completada:", list(opciones_act.keys()))
                        fecha_ent = st.date_input("Fecha de Entrega", value=hoy)
                        btn_compl = st.form_submit_button("Registrar Cumplimiento")
                        if btn_compl:
                            obl_id, obl_mes, obl_anio = opciones_act[obl_a_act]
                            db.registrar_cumplimiento(obl_id, obl_mes, obl_anio, fecha_ent)
                            st.success("Cumplimiento registrado.")
                            st.rerun()"""

replace = """            if df_mostrar.empty:
                st.write("No hay tareas para esta selección.")
            else:
                st.write("**Marcado Rápido**")
                cols_mostrar = ['Cliente', 'descripcion', 'fecha_limite', 'semaforo', 'id_x', 'mes_objetivo', 'anio_objetivo']
                df_ui = df_mostrar[cols_mostrar].copy()
                df_ui['fecha_limite'] = df_ui['fecha_limite'].dt.strftime('%Y-%m-%d')
                df_ui.insert(0, 'Completar', False)

                # Column configuration for editable dataframe
                column_config = {
                    "Completar": st.column_config.CheckboxColumn(
                        "✅ Completar", help="Marca para establecer como completada hoy", default=False
                    ),
                    "id_x": None,
                    "mes_objetivo": None,
                    "anio_objetivo": None
                }

                df_edited = st.data_editor(
                    df_ui,
                    column_config=column_config,
                    disabled=["Cliente", "descripcion", "fecha_limite", "semaforo"],
                    hide_index=True,
                    use_container_width=True,
                    key="data_editor_tareas"
                )

                # Acciones Rápidas (Marcar como Completada)
                tareas_marcadas = df_edited[df_edited['Completar'] == True]
                if not tareas_marcadas.empty:
                    st.write("---")
                    st.write(f"Has marcado **{len(tareas_marcadas)}** tareas para completar.")
                    col_fecha, col_btn = st.columns([1, 1])
                    with col_fecha:
                        fecha_ent = st.date_input("Fecha de Entrega para las marcadas", value=hoy)
                    with col_btn:
                        st.write("") # Espaciador
                        st.write("")
                        if st.button("Guardar Cumplimientos", type="primary"):
                            for _, row in tareas_marcadas.iterrows():
                                db.registrar_cumplimiento(row['id_x'], row['mes_objetivo'], row['anio_objetivo'], fecha_ent.strftime('%Y-%m-%d'))
                            st.success(f"{len(tareas_marcadas)} tareas completadas exitosamente.")
                            st.rerun()"""

content = content.replace(search, replace)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
