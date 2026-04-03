import re

with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()

search = """    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cumplimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            obligacion_id INTEGER,
            mes INTEGER,
            anio INTEGER,
            fecha_de_entrega TEXT,
            FOREIGN KEY (obligacion_id) REFERENCES obligaciones(id)
        )
    ''')"""

replace = search + """
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dias_festivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            descripcion TEXT
        )
    ''')
    cursor.execute("SELECT count(*) FROM dias_festivos")
    if cursor.fetchone()[0] == 0:
        festivos = [
            ('2026-01-01', 'Año Nuevo'),
            ('2026-02-05', 'Día de la Constitución'),
            ('2026-03-21', 'Natalicio de Benito Juárez'),
            ('2026-05-01', 'Día del Trabajo'),
            ('2026-09-16', 'Día de la Independencia'),
            ('2026-11-20', 'Día de la Revolución'),
            ('2026-12-25', 'Navidad'),
        ]
        cursor.executemany("INSERT INTO dias_festivos (fecha, descripcion) VALUES (?, ?)", festivos)
"""

content = content.replace(search, replace)

funcs = """
def obtener_dias_festivos():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM dias_festivos ORDER BY fecha ASC", conn)
    conn.close()
    return df

def agregar_dia_festivo(fecha, descripcion):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO dias_festivos (fecha, descripcion) VALUES (?, ?)", (fecha, descripcion))
    conn.commit()
    conn.close()

def eliminar_dia_festivo(id_festivo):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dias_festivos WHERE id = ?", (id_festivo,))
    conn.commit()
    conn.close()
"""

content += funcs

with open('database.py', 'w', encoding='utf-8') as f:
    f.write(content)
