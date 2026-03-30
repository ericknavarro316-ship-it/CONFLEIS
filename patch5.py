with open("app.py", "r") as f:
    content = f.read()

search = """        with col_new:
            st.subheader("Registrar/Editar Usuario")
            with st.form("form_usuario"):
                # Lista de usuarios existentes
                opciones_user = ["--- Crear Nuevo ---"] + df_users['usuario'].tolist() if not df_users.empty else ["--- Crear Nuevo ---"]
                user_sel = st.selectbox("Seleccionar Acción", opciones_user)"""

replace = """        with col_new:
            st.subheader("Registrar/Editar Usuario")
            
            # Lista de usuarios existentes
            opciones_user = ["--- Crear Nuevo ---"] + df_users['usuario'].tolist() if not df_users.empty else ["--- Crear Nuevo ---"]
            if 'form_user_accion' not in st.session_state:
                st.session_state.form_user_accion = "--- Crear Nuevo ---"
            user_sel = st.selectbox("Seleccionar Acción", opciones_user, key="form_user_accion")"""

content = content.replace(search, replace)

search2 = """                if st.form_submit_button("Guardar Usuario"):"""
replace2 = """            if st.button("Guardar Usuario", type="primary"):"""

content = content.replace(search2, replace2)

search3 = """                        if ok: 
                            st.success(msg)
                            import time
                            time.sleep(1.5)
                            st.rerun()
                        else: st.error(msg)
                    else:
                        st.warning("Completa todos los campos básicos.")"""
replace3 = """                        if ok: 
                            st.success(msg)
                            import time
                            time.sleep(1.5)
                            st.session_state.form_user_accion = "--- Crear Nuevo ---"
                            st.rerun()
                        else: st.error(msg)
                    else:
                        st.warning("Completa todos los campos básicos.")"""
content = content.replace(search3, replace3)

with open("app.py", "w") as f:
    f.write(content)
