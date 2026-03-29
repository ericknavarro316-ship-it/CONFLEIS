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
            fecha_registro DATE DEFAULT CURRENT_DATE
        )
    ''')
    
    # Check if we need to migrate existing data (if we already had a DB without tipo_persona)
    cursor.execute("PRAGMA table_info(clientes)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'tipo_persona' not in columns:
        try:
             cursor.execute("ALTER TABLE clientes ADD COLUMN tipo_persona TEXT NOT NULL DEFAULT 'Física'")
        except Exception as e:
             pass

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
    
    conn.commit()
    conn.close()

# --- Funciones para Clientes ---

def agregar_cliente(nombre, rfc, tipo_persona, regimen, email, telefono):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO clientes (nombre, rfc, tipo_persona, regimen, email, telefono)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, rfc, tipo_persona, regimen, email, telefono))
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
    
    # Construcción de query dinámica basada en los filtros
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
    
    # Asegurar que fecha_limite sea datetime para cálculos de semáforo
    if not df.empty:
        df['fecha_limite'] = pd.to_datetime(df['fecha_limite']).dt.date
        
    conn.close()
    return df

def actualizar_estado_obligacion(obligacion_id, nuevo_estado):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE obligaciones
        SET estado = ?
        WHERE id = ?
    ''', (nuevo_estado, obligacion_id))
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
