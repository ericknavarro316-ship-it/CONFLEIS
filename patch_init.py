import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I failed to add the initialization properly earlier.
# The initialization should be early in the file.
search = """# Inicializar Base de Datos
db.init_db()"""

replace = """# Inicializar Base de Datos
db.init_db()

if 'cal_key_suffix' not in st.session_state:
    st.session_state['cal_key_suffix'] = 0"""

content = content.replace(search, replace)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
