import sqlite3
from datetime import datetime
import pandas as pd
import os
import bcrypt

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    try:
        if hashed is None or password is None: return False
        if not hashed.startswith('$2'):
            # Fallback temporal si la bd no ha sido totalmente migrada
            return password == hashed
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return password == hashed

DB_NAME = "despacho.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla de Clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            rfc TEXT NOT NULL UNIQUE,
            tipo_persona TEXT NOT NULL,
            regimen TEXT,
            email TEXT,
            telefono TEXT,
            fecha_registro DATE DEFAULT CURRENT_DATE,
            etiquetas TEXT DEFAULT '',
            password_portal TEXT DEFAULT ''
        )
    ''')
    
    # Migración de columnas si ya existía la BD
    cursor.execute("PRAGMA table_info(clientes)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'tipo_persona' not in columns:
        try: cursor.execute("ALTER TABLE clientes ADD COLUMN tipo_persona TEXT NOT NULL DEFAULT 'Física'")
        except: pass
    if 'etiquetas' not in columns:
        try: cursor.execute("ALTER TABLE clientes ADD COLUMN etiquetas TEXT DEFAULT ''")
        except: pass
    if 'password_portal' not in columns:
        try: cursor.execute("ALTER TABLE clientes ADD COLUMN password_portal TEXT DEFAULT ''")
        except: pass

    # Tabla de Documentos Compartidos (Cliente -> Contador)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documentos_portal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            nombre_archivo TEXT NOT NULL,
            ruta_archivo TEXT NOT NULL,
            fecha_subida DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
        )
    ''')

    # Tabla de Obligaciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS obligaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            descripcion TEXT NOT NULL,
            fecha_limite DATE NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Pendiente',
            notas TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
        )
    ''')
    
    # Tabla de Credenciales (Bóveda Segura)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credenciales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            tipo_acceso TEXT NOT NULL,
            usuario TEXT,
            contrasena TEXT,
            notas TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
        )
    ''')
    
    # Tabla de Honorarios (Control del Despacho)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS honorarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            mes TEXT NOT NULL,
            anio INTEGER NOT NULL,
            monto REAL NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Pendiente',
            fecha_pago DATE,
            notas TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
        )
    ''')
    
    # Tabla de Notas CRM (Bitácora de interacciones)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notas_crm (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            contenido TEXT NOT NULL,
            autor TEXT DEFAULT 'Contador',
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
        )
    ''')
    
    # Tabla de Roles y Permisos (Puestos del Despacho)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles_despacho (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_rol TEXT NOT NULL UNIQUE,
            nivel_jerarquia INTEGER DEFAULT 5,
            permisos_json TEXT NOT NULL DEFAULT '[]'
        )
    ''')

    # Tabla Bitácora de Equipo (Log)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bitacora_equipo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            autor TEXT NOT NULL,
            accion TEXT NOT NULL,
            detalle TEXT
        )
    ''')

    # Tabla de Usuarios del Despacho (Socio, Auxiliar, Gerente)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios_despacho (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            usuario TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL,
            rol_id INTEGER NOT NULL DEFAULT 2,
            reporta_a_id INTEGER,
            FOREIGN KEY (rol_id) REFERENCES roles_despacho (id) ON DELETE RESTRICT,
            FOREIGN KEY (reporta_a_id) REFERENCES usuarios_despacho (id) ON DELETE SET NULL
        )
    ''')

    # --- MIGRACIÓN (Si ya existía la tabla anterior con `rol` en texto) ---
    cursor.execute("PRAGMA table_info(usuarios_despacho)")
    columns_users = [col[1] for col in cursor.fetchall()]
    if 'rol_id' not in columns_users:
        try: cursor.execute("ALTER TABLE usuarios_despacho ADD COLUMN rol_id INTEGER NOT NULL DEFAULT 2")
        except: pass
    if 'reporta_a_id' not in columns_users:
        try: cursor.execute("ALTER TABLE usuarios_despacho ADD COLUMN reporta_a_id INTEGER")
        except: pass
    
    # Tabla de Asignaciones (Auxiliar -> Cliente)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asignaciones_clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            cliente_id INTEGER,
            FOREIGN KEY (usuario_id) REFERENCES usuarios_despacho (id) ON DELETE CASCADE,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
        )
    ''')
    
    # Tabla de Notificaciones (Historial/Cola)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            tipo TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            fecha_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
            estado TEXT DEFAULT 'Enviado',
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
        )
    ''')
    
    # Tabla de Citas/Agenda
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            titulo TEXT NOT NULL,
            fecha_hora DATETIME NOT NULL,
            notas TEXT,
            estado TEXT DEFAULT 'Programada',
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
        )
    ''')
    
    # Tabla de Configuración (Logo y Colores)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            logo_ruta TEXT,
            color_primario TEXT DEFAULT '#000000',
            color_secundario TEXT DEFAULT '#FFCC00',
            color_terciario TEXT DEFAULT '#CC0000'
        )
    ''')
    
    # Tabla Kanban (Tareas del Staff)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kanban_tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            descripcion TEXT NOT NULL,
            columna TEXT DEFAULT 'Por Revisar',
            asignado_a INTEGER,
            fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE,
            FOREIGN KEY (asignado_a) REFERENCES usuarios_despacho (id) ON DELETE SET NULL
        )
    ''')
    
    # Tabla Líneas de Captura (Impuestos SAT)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lineas_captura (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            mes TEXT NOT NULL,
            anio INTEGER NOT NULL,
            monto REAL NOT NULL,
            fecha_vencimiento DATE NOT NULL,
            archivo_ruta TEXT NOT NULL,
            estado_envio TEXT DEFAULT 'Enviado',
            fecha_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    
    # Insert default config if none exists
    cursor.execute("SELECT COUNT(*) FROM configuracion")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO configuracion (id) VALUES (1)")
        conn.commit()
    
    # Insertar Roles por defecto si no existen
    import json
    # Add estatus if it doesn't exist
    try:
        cursor.execute("ALTER TABLE usuarios_despacho ADD COLUMN estatus TEXT DEFAULT 'Activo'")
    except sqlite3.OperationalError:
        pass # Column already exists

    cursor.execute("SELECT COUNT(*) FROM roles_despacho")
    if cursor.fetchone()[0] == 0:
        todos_los_modulos = json.dumps([
            "Dashboard", "Mi Despacho (Finanzas)", "Gestión de Equipo (Admin)", "Configuración de Marca", "Personas Físicas", 
            "Personas Morales", "Cálculo de Impuestos y XML", "Conciliación Bancaria y DIOT", "Descarga Masiva SAT (Simulador)",
            "Exportación a CONTPAQi", "Calendario General", "Expediente de Cliente", "Control de Honorarios", 
            "🤖 Asistente Fiscal AI", "Notificaciones a Clientes", "Agenda y Citas", "Facturación (CFDI)", 
            "Tablero Kanban (Staff)", "Envío de Líneas de Captura"
        ])
        modulos_basicos = json.dumps([
            "Dashboard", "Personas Físicas", "Personas Morales", "Cálculo de Impuestos y XML", 
            "Conciliación Bancaria y DIOT", "Descarga Masiva SAT (Simulador)", "Calendario General", 
            "🤖 Asistente Fiscal AI", "Agenda y Citas", "Facturación (CFDI)", "Tablero Kanban (Staff)", "Envío de Líneas de Captura"
        ])
        cursor.execute("INSERT INTO roles_despacho (id, nombre_rol, nivel_jerarquia, permisos_json) VALUES (1, 'Administrador', 1, ?)", (todos_los_modulos,))
        cursor.execute("INSERT INTO roles_despacho (id, nombre_rol, nivel_jerarquia, permisos_json) VALUES (2, 'Auxiliar', 3, ?)", (modulos_basicos,))
        conn.commit()

    # Actualizar admin existente a nuevo sistema de roles o crear uno nuevo
    cursor.execute("SELECT COUNT(*) FROM usuarios_despacho WHERE usuario='admin'")
    if cursor.fetchone()[0] == 0:
        hash_pwd = hash_password("admin")
        cursor.execute("INSERT INTO usuarios_despacho (nombre, usuario, contrasena, rol_id) VALUES ('Administrador General', 'admin', ?, 1)", (hash_pwd,))
        conn.commit()
    else:
        cursor.execute("UPDATE usuarios_despacho SET rol_id = 1 WHERE usuario='admin'")
        conn.commit()

    conn.close()

# --- Funciones para Roles de Acceso (RBAC) ---
def agregar_rol(nombre_rol, nivel_jerarquia, modulos_permitidos):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    import json
    permisos_json = json.dumps(modulos_permitidos)
    try:
        cursor.execute("INSERT INTO roles_despacho (nombre_rol, nivel_jerarquia, permisos_json) VALUES (?, ?, ?)", (nombre_rol, nivel_jerarquia, permisos_json))
        conn.commit()
        return True, "Puesto/Rol creado exitosamente."
    except sqlite3.IntegrityError:
        return False, "El nombre de este puesto ya existe."
    finally:
        conn.close()

def obtener_roles():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM roles_despacho ORDER BY nivel_jerarquia ASC", conn)
    conn.close()
    return df

def actualizar_rol(rol_id, nombre_rol, nivel_jerarquia, modulos_permitidos):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    import json
    permisos_json = json.dumps(modulos_permitidos)
    cursor.execute("UPDATE roles_despacho SET nombre_rol = ?, nivel_jerarquia = ?, permisos_json = ? WHERE id = ?", (nombre_rol, nivel_jerarquia, permisos_json, rol_id))
    conn.commit()
    conn.close()

# --- Funciones para Usuarios y Asignaciones ---

def verificar_login_equipo(usuario, contrasena):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    query = '''
        SELECT u.id, u.nombre, r.nombre_rol, u.contrasena, r.permisos_json
        FROM usuarios_despacho u
        JOIN roles_despacho r ON u.rol_id = r.id
        WHERE u.usuario = ?
    '''
    cursor.execute(query, (usuario,))
    resultado = cursor.fetchone()
    conn.close()
    import json
    if resultado and check_password(contrasena, resultado[3]):
        permisos = json.loads(resultado[4]) if resultado[4] else []
        return (resultado[0], resultado[1], resultado[2], permisos)
    return None

def obtener_usuarios_despacho():
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT u.id, u.nombre, u.usuario, r.nombre_rol as rol, u.rol_id, u.reporta_a_id, u.estatus
        FROM usuarios_despacho u
        JOIN roles_despacho r ON u.rol_id = r.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def agregar_usuario_despacho(nombre, usuario, contrasena, rol_id, reporta_a_id=None, estatus='Activo'):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        hash_pwd = hash_password(contrasena)
        cursor.execute("INSERT INTO usuarios_despacho (nombre, usuario, contrasena, rol_id, reporta_a_id, estatus) VALUES (?, ?, ?, ?, ?, ?)", (nombre, usuario, hash_pwd, rol_id, reporta_a_id, estatus))
        conn.commit()
        return True, "Usuario agregado."
    except sqlite3.IntegrityError:
        return False, "El nombre de usuario ya existe."
    finally:
        conn.close()

def obtener_id_usuario_por_login(usuario_login):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios_despacho WHERE usuario=?", (usuario_login,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def obtener_subordinados_directos(supervisor_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios_despacho WHERE reporta_a_id = ? AND estatus = 'Activo'", (supervisor_id,))
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res

def reasignar_subordinados(nuevo_supervisor_id, subordinados_ids):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    nombres_reasignados = []

    # Obtener los nombres antes de actualizar para el mensaje
    placeholders = ', '.join('?' for _ in subordinados_ids)
    cursor.execute(f"SELECT nombre FROM usuarios_despacho WHERE id IN ({placeholders})", tuple(subordinados_ids))
    for row in cursor.fetchall():
        nombres_reasignados.append(row[0])

    for sub_id in subordinados_ids:
        cursor.execute("UPDATE usuarios_despacho SET reporta_a_id = ? WHERE id = ?", (nuevo_supervisor_id, sub_id))
    conn.commit()
    conn.close()
    return nombres_reasignados

def actualizar_usuario_despacho(user_id, nombre, usuario, rol_id, reporta_a_id=None, nueva_contrasena=None, estatus='Activo'):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        if nueva_contrasena:
            hash_pwd = hash_password(nueva_contrasena)
            cursor.execute("UPDATE usuarios_despacho SET nombre=?, usuario=?, rol_id=?, reporta_a_id=?, contrasena=?, estatus=? WHERE id=?",
                           (nombre, usuario, rol_id, reporta_a_id, hash_pwd, estatus, user_id))
        else:
            cursor.execute("UPDATE usuarios_despacho SET nombre=?, usuario=?, rol_id=?, reporta_a_id=?, estatus=? WHERE id=?",
                           (nombre, usuario, rol_id, reporta_a_id, estatus, user_id))
        conn.commit()
        return True, "Usuario actualizado exitosamente."
    except sqlite3.IntegrityError:
        return False, "El nombre de usuario ya existe en otro registro."
    finally:
        conn.close()

def eliminar_usuario_despacho(usuario_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios_despacho WHERE id = ?", (usuario_id,))
    conn.commit()
    conn.close()

def asignar_cliente_a_usuario(usuario_id, cliente_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM asignaciones_clientes WHERE usuario_id = ? AND cliente_id = ?", (usuario_id, cliente_id))
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO asignaciones_clientes (usuario_id, cliente_id) VALUES (?, ?)", (usuario_id, cliente_id))
        conn.commit()
    conn.close()

def desasignar_cliente_de_usuario(usuario_id, cliente_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM asignaciones_clientes WHERE usuario_id = ? AND cliente_id = ?", (usuario_id, cliente_id))
    conn.commit()
    conn.close()
    
def obtener_asignaciones(usuario_id):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT cliente_id FROM asignaciones_clientes WHERE usuario_id = ?", conn, params=(usuario_id,))
    conn.close()
    return df['cliente_id'].tolist() if not df.empty else []

# --- Funciones para Notificaciones ---

def registrar_notificacion(cliente_id, tipo, mensaje):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notificaciones (cliente_id, tipo, mensaje) VALUES (?, ?, ?)", (cliente_id, tipo, mensaje))
    conn.commit()
    conn.close()

def obtener_notificaciones():
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT n.id, c.nombre as Cliente, n.tipo as Medio, n.mensaje as Mensaje, n.fecha_envio, n.estado 
        FROM notificaciones n
        JOIN clientes c ON n.cliente_id = c.id
        ORDER BY n.fecha_envio DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- Funciones para Citas y Configuración ---

def agregar_cita(cliente_id, titulo, fecha_hora, notas=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO citas (cliente_id, titulo, fecha_hora, notas) VALUES (?, ?, ?, ?)", (cliente_id, titulo, fecha_hora, notas))
    conn.commit()
    conn.close()

def obtener_citas():
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT a.id, c.nombre as Cliente, a.titulo, a.fecha_hora, a.notas, a.estado
        FROM citas a
        JOIN clientes c ON a.cliente_id = c.id
        ORDER BY a.fecha_hora ASC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def eliminar_cita(cita_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM citas WHERE id = ?", (cita_id,))
    conn.commit()
    conn.close()

def obtener_configuracion():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT logo_ruta, color_primario, color_secundario, color_terciario FROM configuracion WHERE id = 1")
    resultado = cursor.fetchone()
    conn.close()
    return {'logo': resultado[0], 'c1': resultado[1], 'c2': resultado[2], 'c3': resultado[3]} if resultado else None

def actualizar_configuracion(logo_ruta, c1, c2, c3):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE configuracion 
        SET logo_ruta = ?, color_primario = ?, color_secundario = ?, color_terciario = ? 
        WHERE id = 1
    ''', (logo_ruta, c1, c2, c3))
    conn.commit()
    conn.close()

# --- Funciones para Kanban y Líneas de Captura ---

def crear_tarea_kanban(cliente_id, descripcion, asignado_a=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO kanban_tareas (cliente_id, descripcion, asignado_a) VALUES (?, ?, ?)", (cliente_id, descripcion, asignado_a))
    conn.commit()
    conn.close()

def obtener_tareas_kanban(columna=None):
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT k.id, c.nombre as Cliente, k.descripcion, k.columna, u.nombre as Asignado, k.fecha_creacion, c.id as cliente_id
        FROM kanban_tareas k
        JOIN clientes c ON k.cliente_id = c.id
        LEFT JOIN usuarios_despacho u ON k.asignado_a = u.id
    '''
    if columna:
        query += f" WHERE k.columna = '{columna}'"
    query += " ORDER BY k.fecha_creacion ASC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def mover_tarea_kanban(tarea_id, nueva_columna):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE kanban_tareas SET columna = ? WHERE id = ?", (nueva_columna, tarea_id))
    conn.commit()
    conn.close()

def eliminar_tarea_kanban(tarea_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM kanban_tareas WHERE id = ?", (tarea_id,))
    conn.commit()
    conn.close()

def agregar_linea_captura(cliente_id, mes, anio, monto, fecha_vencimiento, archivo_ruta):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO lineas_captura (cliente_id, mes, anio, monto, fecha_vencimiento, archivo_ruta)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (cliente_id, mes, anio, monto, fecha_vencimiento, archivo_ruta))
    conn.commit()
    
    # Registrar la notificación automática
    mensaje = f"Línea de captura del mes {mes}/{anio} por un monto de ${float(monto):,.2f} con vencimiento el {fecha_vencimiento} ha sido generada y enviada a su correo/portal."
    cursor.execute("INSERT INTO notificaciones (cliente_id, tipo, mensaje, estado) VALUES (?, 'Sistema Automático', ?, 'Enviado (Portal)')", (cliente_id, mensaje))
    conn.commit()
    conn.close()

def obtener_lineas_captura(cliente_id=None):
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT l.id, c.nombre as Cliente, l.mes, l.anio, l.monto, l.fecha_vencimiento, l.archivo_ruta, l.fecha_envio
        FROM lineas_captura l
        JOIN clientes c ON l.cliente_id = c.id
    '''
    params = []
    if cliente_id:
        query += " WHERE l.cliente_id = ?"
        params.append(cliente_id)
    query += " ORDER BY l.fecha_envio DESC"
    
    df = pd.read_sql_query(query, conn, params=tuple(params))
    conn.close()
    return df

def eliminar_linea_captura(linea_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lineas_captura WHERE id = ?", (linea_id,))
    conn.commit()
    conn.close()


# --- Funciones para Clientes ---

def agregar_cliente(nombre, rfc, tipo_persona, regimen, email, telefono, etiquetas=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO clientes (nombre, rfc, tipo_persona, regimen, email, telefono, etiquetas)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nombre, rfc, tipo_persona, regimen, email, telefono, etiquetas))
        conn.commit()
        obtener_clientes.clear()
        return True, "Cliente agregado exitosamente."
    except sqlite3.IntegrityError:
        return False, f"El RFC {rfc} ya existe en la base de datos."
    finally:
        conn.close()

import streamlit as st

@st.cache_data(ttl=300)
def obtener_clientes(tipo_persona=None):
    conn = sqlite3.connect(DB_NAME)
    if tipo_persona:
         df = pd.read_sql_query("SELECT * FROM clientes WHERE tipo_persona = ?", conn, params=(tipo_persona,))
    else:
         df = pd.read_sql_query("SELECT * FROM clientes", conn)
    conn.close()
    return df

def eliminar_cliente(cliente_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conn.commit()
    conn.close()
    obtener_clientes.clear()

def actualizar_etiquetas_cliente(cliente_id, nuevas_etiquetas):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE clientes SET etiquetas = ? WHERE id = ?", (nuevas_etiquetas, cliente_id))
    conn.commit()
    conn.close()
    obtener_clientes.clear()

def actualizar_password_portal(cliente_id, nuevo_password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    hash_pwd = hash_password(nuevo_password)
    cursor.execute("UPDATE clientes SET password_portal = ? WHERE id = ?", (hash_pwd, cliente_id))
    conn.commit()
    conn.close()
    
def verificar_login_cliente(rfc, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, password_portal FROM clientes WHERE rfc = ?", (rfc.upper(),))
    resultado = cursor.fetchone()
    conn.close()
    if resultado and check_password(password, resultado[2]):
        return (resultado[0], resultado[1])
    return None

def registrar_documento_portal(cliente_id, nombre_archivo, ruta_archivo):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO documentos_portal (cliente_id, nombre_archivo, ruta_archivo) VALUES (?, ?, ?)", (cliente_id, nombre_archivo, ruta_archivo))
    conn.commit()
    conn.close()
    
def obtener_documentos_portal(cliente_id):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM documentos_portal WHERE cliente_id = ? ORDER BY fecha_subida DESC", conn, params=(cliente_id,))
    conn.close()
    return df

# --- Funciones para Obligaciones ---

def agregar_obligacion(cliente_id, descripcion, fecha_limite, notas=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO obligaciones (cliente_id, descripcion, fecha_limite, notas)
        VALUES (?, ?, ?, ?)
    ''', (cliente_id, descripcion, fecha_limite, notas))
    conn.commit()
    conn.close()

def obtener_obligaciones(tipo_persona=None, cliente_id=None):
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT o.id, c.nombre as Cliente, o.descripcion, o.fecha_limite, o.estado, o.notas
        FROM obligaciones o
        JOIN clientes c ON o.cliente_id = c.id
        WHERE 1=1
    '''
    params = []
    if tipo_persona:
        query += " AND c.tipo_persona = ?"
        params.append(tipo_persona)
    if cliente_id:
        query += " AND c.id = ?"
        params.append(cliente_id)
        
    query += " ORDER BY o.fecha_limite ASC"
    df = pd.read_sql_query(query, conn, params=tuple(params))
    
    if not df.empty:
        df['fecha_limite'] = pd.to_datetime(df['fecha_limite']).dt.date
    conn.close()
    return df

def actualizar_estado_obligacion(obligacion_id, nuevo_estado):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE obligaciones SET estado = ? WHERE id = ?", (nuevo_estado, obligacion_id))
    conn.commit()
    conn.close()

def eliminar_obligacion(obligacion_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM obligaciones WHERE id = ?", (obligacion_id,))
    conn.commit()
    conn.close()

# --- Funciones para Credenciales (Bóveda Segura) ---

def agregar_credencial(cliente_id, tipo_acceso, usuario, contrasena, notas=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO credenciales (cliente_id, tipo_acceso, usuario, contrasena, notas)
        VALUES (?, ?, ?, ?, ?)
    ''', (cliente_id, tipo_acceso, usuario, contrasena, notas))
    conn.commit()
    conn.close()

def obtener_credenciales(cliente_id):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM credenciales WHERE cliente_id = ?", conn, params=(cliente_id,))
    conn.close()
    return df

def eliminar_credencial(credencial_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM credenciales WHERE id = ?", (credencial_id,))
    conn.commit()
    conn.close()

# --- Funciones para Honorarios (Control del Despacho) ---

def agregar_honorario(cliente_id, mes, anio, monto, notas=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO honorarios (cliente_id, mes, anio, monto, notas)
        VALUES (?, ?, ?, ?, ?)
    ''', (cliente_id, mes, anio, monto, notas))
    conn.commit()
    conn.close()

def obtener_honorarios(cliente_id=None):
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT h.id, c.nombre as Cliente, h.mes as Mes, h.anio as Año, h.monto as Monto, 
               h.estado as Estado, h.fecha_pago, h.notas, c.id as cliente_id
        FROM honorarios h
        JOIN clientes c ON h.cliente_id = c.id
        WHERE 1=1
    '''
    params = []
    if cliente_id:
        query += " AND c.id = ?"
        params.append(cliente_id)
        
    query += " ORDER BY h.anio DESC, h.mes DESC"
    df = pd.read_sql_query(query, conn, params=tuple(params))
    conn.close()
    return df

def actualizar_estado_honorario(honorario_id, nuevo_estado):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    fecha_pago = datetime.today().strftime('%Y-%m-%d') if nuevo_estado == 'Pagado' else None
    cursor.execute("UPDATE honorarios SET estado = ?, fecha_pago = ? WHERE id = ?", (nuevo_estado, fecha_pago, honorario_id))
    conn.commit()
    conn.close()

def eliminar_honorario(honorario_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM honorarios WHERE id = ?", (honorario_id,))
    conn.commit()
    conn.close()

# --- Funciones para Notas CRM (Bitácora) ---

def agregar_nota_crm(cliente_id, contenido, autor="Contador"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notas_crm (cliente_id, contenido, autor) VALUES (?, ?, ?)", (cliente_id, contenido, autor))
    conn.commit()
    conn.close()

def obtener_notas_crm(cliente_id):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM notas_crm WHERE cliente_id = ? ORDER BY fecha DESC", conn, params=(cliente_id,))
    conn.close()
    return df

def eliminar_nota_crm(nota_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notas_crm WHERE id = ?", (nota_id,))
    conn.commit()
    conn.close()


# --- Funciones para Bitácora de Equipo ---
def registrar_bitacora_equipo(autor, accion, detalle):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bitacora_equipo (autor, accion, detalle) VALUES (?, ?, ?)", (autor, accion, detalle))
    conn.commit()
    conn.close()

def obtener_bitacora_equipo():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, datetime(fecha, 'localtime') as fecha_local, autor, accion, detalle FROM bitacora_equipo ORDER BY fecha DESC", conn)
    conn.close()
    return df
