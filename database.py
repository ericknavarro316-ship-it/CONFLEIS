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

def obtener_obligaciones(tipo_persona=None):
    conn = sqlite3.connect(DB_NAME)
    if tipo_persona:
         query = '''
             SELECT o.id, c.nombre as Cliente, o.descripcion, o.fecha_limite, o.estado, o.notas
             FROM obligaciones o
             JOIN clientes c ON o.cliente_id = c.id
             WHERE c.tipo_persona = ?
             ORDER BY o.fecha_limite ASC
         '''
         df = pd.read_sql_query(query, conn, params=(tipo_persona,))
    else:
        query = '''
            SELECT o.id, c.nombre as Cliente, o.descripcion, o.fecha_limite, o.estado, o.notas
            FROM obligaciones o
            JOIN clientes c ON o.cliente_id = c.id
            ORDER BY o.fecha_limite ASC
        '''
        df = pd.read_sql_query(query, conn)
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
