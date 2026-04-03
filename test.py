import sqlite3
DB_NAME = 'despacho.db'
def init():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

init()
print("done")
