with open("app.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.startswith('                if st.button("Guardar Puesto"'):
        lines[i] = line[4:]
        
    if line.startswith('                    if nom_r:'):
        for j in range(i, i+17):
            lines[j] = lines[j][4:]
        break

with open("app.py", "w") as f:
    f.writelines(lines)
