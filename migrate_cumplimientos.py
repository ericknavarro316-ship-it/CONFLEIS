import sqlite3

def migrate():
    conn = sqlite3.connect('despacho.db')
    cursor = conn.cursor()

    # Create cumplimientos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cumplimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            obligacion_id INTEGER,
            mes INTEGER NOT NULL,
            anio INTEGER NOT NULL,
            fecha_de_entrega DATE NOT NULL,
            FOREIGN KEY (obligacion_id) REFERENCES obligaciones (id) ON DELETE CASCADE,
            UNIQUE(obligacion_id, mes, anio)
        )
    ''')

    conn.commit()
    print("Migration complete. Added 'cumplimientos' table.")
    conn.close()

if __name__ == "__main__":
    migrate()