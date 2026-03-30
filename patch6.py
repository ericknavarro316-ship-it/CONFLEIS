import re
with open("app.py", "r") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith('            if \'form_user_accion\' not in st.session_state:'):
        start_idx = i + 2
    if line.startswith('            if st.button("Guardar Usuario", type="primary"):'):
        end_idx = i
        break
        
if start_idx != -1 and end_idx != -1:
    for i in range(start_idx, end_idx):
        if lines[i].startswith('    '):
            lines[i] = lines[i][4:]
            
with open("app.py", "w") as f:
    f.writelines(lines)
