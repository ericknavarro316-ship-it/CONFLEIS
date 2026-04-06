with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()

search = """        CREATE TABLE IF NOT EXISTS kanban_tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            descripcion TEXT NOT NULL,
            columna TEXT DEFAULT 'Por Revisar',
            asignado_a INTEGER,
            fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE,
            FOREIGN KEY (asignado_a) REFERENCES usuarios_despacho (id) ON DELETE SET NULL
        )"""

replace = """        CREATE TABLE IF NOT EXISTS kanban_tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            descripcion TEXT NOT NULL,
            columna TEXT DEFAULT 'Por Revisar',
            asignado_a INTEGER,
            fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            obligacion_id INTEGER,
            mes_objetivo INTEGER,
            anio_objetivo INTEGER,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE,
            FOREIGN KEY (asignado_a) REFERENCES usuarios_despacho (id) ON DELETE SET NULL
        )"""

content = content.replace(search, replace)

# Add migration to init_db so future startups upgrade the db automatically if needed
migration_search = """    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kanban_tareas ("""

migration_replace = """    # Add migration for Kanban integration if columns are missing
    try:
        cursor.execute("ALTER TABLE kanban_tareas ADD COLUMN obligacion_id INTEGER")
        cursor.execute("ALTER TABLE kanban_tareas ADD COLUMN mes_objetivo INTEGER")
        cursor.execute("ALTER TABLE kanban_tareas ADD COLUMN anio_objetivo INTEGER")
    except:
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kanban_tareas ("""

content = content.replace(migration_search, migration_replace)

with open('database.py', 'w', encoding='utf-8') as f:
    f.write(content)
