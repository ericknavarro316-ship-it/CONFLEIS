import sqlite3
from datetime import datetime
import pandas as pd
import os

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
            etiquetas TEXT DEFAULT ''
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
        return True, "Cliente agregado exitosamente."
    except sqlite3.IntegrityError:
        return False, f"El RFC {rfc} ya existe en la base de datos."
    finally:
        conn.close()

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

def actualizar_etiquetas_cliente(cliente_id, nuevas_etiquetas):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE clientes SET etiquetas = ? WHERE id = ?", (nuevas_etiquetas, cliente_id))
    conn.commit()
    conn.close()

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
