import sqlite3

def upgrade_kanban_table():
    conn = sqlite3.connect('despacho.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE kanban_tareas ADD COLUMN obligacion_id INTEGER;")
        cursor.execute("ALTER TABLE kanban_tareas ADD COLUMN mes_objetivo INTEGER;")
        cursor.execute("ALTER TABLE kanban_tareas ADD COLUMN anio_objetivo INTEGER;")
        print("Columns added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Migration error (columns might already exist): {e}")
    conn.commit()
    conn.close()

upgrade_kanban_table()
