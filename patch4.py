with open("app.py", "r") as f:
    content = f.read()

search = """            if st.button("Guardar Puesto", type="primary"):
                if nom_r:
                    if is_r_edit:
                        db.actualizar_rol(int(r_row['id']), nom_r, jer_r, permisos_seleccionados)
                        st.success("Rol actualizado.")
                        import time
                        time.sleep(1.5)
                    else:
                        ok, m = db.agregar_rol(nom_r, jer_r, permisos_seleccionados)
                        if ok: 
                            st.success(m)
                            import time
                            time.sleep(1.5)
                        else: st.error(m)
                    st.rerun()
                else:
                    st.warning("El nombre es obligatorio.")"""

replace = """            if st.button("Guardar Puesto", type="primary"):
                if nom_r:
                    if is_r_edit:
                        db.actualizar_rol(int(r_row['id']), nom_r, jer_r, permisos_seleccionados)
                        st.success("Rol actualizado.")
                        import time
                        time.sleep(1.5)
                        st.session_state.form_rol_accion = "--- Crear Nuevo ---"
                    else:
                        ok, m = db.agregar_rol(nom_r, jer_r, permisos_seleccionados)
                        if ok: 
                            st.success(m)
                            import time
                            time.sleep(1.5)
                            st.session_state.form_rol_accion = "--- Crear Nuevo ---"
                        else: st.error(m)
                    st.rerun()
                else:
                    st.warning("El nombre es obligatorio.")"""

content = content.replace(search, replace)
with open("app.py", "w") as f:
    f.write(content)
