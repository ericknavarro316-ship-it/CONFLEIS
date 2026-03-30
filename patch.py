with open("app.py", "r") as f:
    content = f.read()

# Replace with st.form("form_rol") with just nothing or a container, and change form_submit_button to button
search_block = """        with col_rnew:
            st.subheader("Crear/Editar Puesto")
            with st.form("form_rol"):
                opciones_r = ["--- Crear Nuevo ---"] + df_roles['nombre_rol'].tolist() if not df_roles.empty else ["--- Crear Nuevo ---"]
                r_sel = st.selectbox("Acción", opciones_r)"""

replace_block = """        with col_rnew:
            st.subheader("Crear/Editar Puesto")
            
            opciones_r = ["--- Crear Nuevo ---"] + df_roles['nombre_rol'].tolist() if not df_roles.empty else ["--- Crear Nuevo ---"]
            if 'form_rol_accion' not in st.session_state:
                st.session_state.form_rol_accion = "--- Crear Nuevo ---"
            r_sel = st.selectbox("Acción", opciones_r, key="form_rol_accion")"""

content = content.replace(search_block, replace_block)

search_block2 = """                if st.form_submit_button("Guardar Puesto"):"""
replace_block2 = """                if st.button("Guardar Puesto", type="primary"):"""

content = content.replace(search_block2, replace_block2)

# Fix indentation of the block that was inside `with st.form`
# We need to unindent everything between the end of replace_block and the end of replace_block2
lines = content.split('\n')
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if line.startswith('            if \'form_rol_accion\' not in st.session_state:'):
        start_idx = i + 2 # the line after r_sel
    if line.startswith('                if st.button("Guardar Puesto"'):
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    for i in range(start_idx, end_idx):
        if lines[i].startswith('    '): # ensure it's indented at least 4 spaces before stripping
             lines[i] = lines[i][4:]
             
content = '\n'.join(lines)

with open("app.py", "w") as f:
    f.write(content)
