with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()

search_crear = """def crear_tarea_kanban(cliente_id, descripcion, asignado_a=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO kanban_tareas (cliente_id, descripcion, asignado_a) VALUES (?, ?, ?)", (cliente_id, descripcion, asignado_a))"""

replace_crear = """def crear_tarea_kanban(cliente_id, descripcion, asignado_a=None, obligacion_id=None, mes_objetivo=None, anio_objetivo=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO kanban_tareas (cliente_id, descripcion, asignado_a, obligacion_id, mes_objetivo, anio_objetivo) VALUES (?, ?, ?, ?, ?, ?)",
        (cliente_id, descripcion, asignado_a, obligacion_id, mes_objetivo, anio_objetivo)
    )"""

content = content.replace(search_crear, replace_crear)

search_obtener = """        SELECT k.id, c.nombre as Cliente, k.descripcion, k.columna, u.nombre as Asignado, k.fecha_creacion, c.id as cliente_id
        FROM kanban_tareas k"""

replace_obtener = """        SELECT k.id, c.nombre as Cliente, k.descripcion, k.columna, u.nombre as Asignado, k.fecha_creacion, c.id as cliente_id, k.obligacion_id, k.mes_objetivo, k.anio_objetivo
        FROM kanban_tareas k"""

content = content.replace(search_obtener, replace_obtener)

with open('database.py', 'w', encoding='utf-8') as f:
    f.write(content)
