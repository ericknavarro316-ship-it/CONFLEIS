import pandas as pd
import math

def parsear_estado_cuenta(archivo_excel):
    """
    Lee un archivo Excel genérico de un estado de cuenta bancario.
    Se asume que tiene columnas como 'Fecha', 'Concepto', 'Cargo', 'Abono'.
    Devuelve un DataFrame limpio.
    """
    try:
        # Intentar leer asumiendo que las columnas principales están en la fila 0
        df_banco = pd.read_excel(archivo_excel)
        
        # Buscar columnas comunes
        cols_banco = [c.lower() for c in df_banco.columns]
        
        fecha_col = next((c for c in df_banco.columns if 'fecha' in c.lower()), None)
        concepto_col = next((c for c in df_banco.columns if 'concepto' in c.lower() or 'descrip' in c.lower()), None)
        cargo_col = next((c for c in df_banco.columns if 'cargo' in c.lower() or 'retiro' in c.lower()), None)
        abono_col = next((c for c in df_banco.columns if 'abono' in c.lower() or 'deposito' in c.lower() or 'ingreso' in c.lower()), None)
        
        if not all([fecha_col, concepto_col]):
             return None, "No se encontraron columnas de 'Fecha' o 'Concepto' en el Excel."
             
        # Limpiar DataFrame
        df_limpio = df_banco[[fecha_col, concepto_col]].copy()
        
        if cargo_col: df_limpio['Retiro'] = df_banco[cargo_col].fillna(0).astype(float)
        else: df_limpio['Retiro'] = 0.0
        
        if abono_col: df_limpio['Deposito'] = df_banco[abono_col].fillna(0).astype(float)
        else: df_limpio['Deposito'] = 0.0
        
        # Convertir a datetime
        df_limpio['Fecha'] = pd.to_datetime(df_limpio[fecha_col], errors='coerce').dt.date
        df_limpio['Concepto'] = df_limpio[concepto_col].astype(str)
        
        # Eliminar filas donde no hay montos o son nulos
        df_limpio = df_limpio[(df_limpio['Retiro'] > 0) | (df_limpio['Deposito'] > 0)]
        df_limpio = df_limpio.dropna(subset=['Fecha'])
        
        return df_limpio, "Éxito"
    except Exception as e:
        return None, f"Error al procesar Excel: {str(e)}"

def conciliar_movimientos(df_banco, df_xmls):
    """
    Realiza el cruce o 'match' automático entre los movimientos del banco
    y los totales de las facturas XML procesadas.
    Criterios: 1) Monto exacto, 2) Fecha cercana (opcional), 3) Nombre/Folio en Concepto.
    """
    if df_banco is None or df_banco.empty or df_xmls is None or df_xmls.empty:
        return pd.DataFrame(), pd.DataFrame(), "Faltan datos para conciliar."
        
    # Inicializar columnas de conciliación en el Banco
    df_banco['Match'] = "No Conciliado"
    df_banco['Factura_Referencia'] = ""
    
    # Separar XMLs por Ventas (Ingresos) y Gastos (Egresos)
    ventas = df_xmls[df_xmls['Clasificacion_Contable'].str.contains('Venta|Ingreso', na=False, case=False)]
    gastos = df_xmls[df_xmls['Clasificacion_Contable'].str.contains('Gasto|Deducci', na=False, case=False)]
    
    # Copias locales de las listas de XML para irlas marcando
    ventas_pendientes = ventas.copy()
    ventas_pendientes['Conciliado'] = False
    
    gastos_pendientes = gastos.copy()
    gastos_pendientes['Conciliado'] = False
    
    # Iterar sobre cada movimiento bancario
    for index, row in df_banco.iterrows():
        monto_deposito = round(row['Deposito'], 2)
        monto_retiro = round(row['Retiro'], 2)
        concepto = row['Concepto'].lower()
        
        # --- BUSCAR MATCH PARA DEPÓSITOS (Ventas Cobradas) ---
        if monto_deposito > 0:
            # Buscar por monto exacto en ventas no conciliadas
            match_exacto = ventas_pendientes[
                (ventas_pendientes['Conciliado'] == False) & 
                (abs(ventas_pendientes['Total'] - monto_deposito) < 0.1) # Tolerancia de centavos
            ]
            
            if not match_exacto.empty:
                 # Seleccionar el primero si hay varios, idealmente refinaríamos por folio en el concepto
                 # Buscar si el folio está en el concepto
                 folio_match = None
                 for i, v_row in match_exacto.iterrows():
                     serie_folio = str(v_row['Serie_Folio']).lower()
                     if serie_folio and serie_folio in concepto:
                         folio_match = i
                         break
                         
                 idx_match = folio_match if folio_match is not None else match_exacto.index[0]
                 
                 fact_ref = f"{ventas_pendientes.loc[idx_match, 'Serie_Folio']} - {ventas_pendientes.loc[idx_match, 'Receptor_Nombre'][:15]}"
                 df_banco.at[index, 'Match'] = "Conciliado Exacto (Monto)"
                 df_banco.at[index, 'Factura_Referencia'] = fact_ref
                 ventas_pendientes.at[idx_match, 'Conciliado'] = True
                 continue
                 
        # --- BUSCAR MATCH PARA RETIROS (Gastos Pagados) ---
        elif monto_retiro > 0:
            # Buscar por monto exacto en gastos no conciliados
            match_exacto = gastos_pendientes[
                (gastos_pendientes['Conciliado'] == False) & 
                (abs(gastos_pendientes['Total'] - monto_retiro) < 0.1)
            ]
            
            if not match_exacto.empty:
                 folio_match = None
                 for i, g_row in match_exacto.iterrows():
                     serie_folio = str(g_row['Serie_Folio']).lower()
                     emisor_nombre = str(g_row['Emisor_Nombre']).lower()
                     # Buscar folio o alguna palabra clave del emisor en el concepto
                     if serie_folio in concepto or (emisor_nombre[:10] in concepto and len(emisor_nombre) > 5):
                         folio_match = i
                         break
                         
                 idx_match = folio_match if folio_match is not None else match_exacto.index[0]
                 
                 fact_ref = f"{gastos_pendientes.loc[idx_match, 'Serie_Folio']} - {gastos_pendientes.loc[idx_match, 'Emisor_Nombre'][:15]}"
                 df_banco.at[index, 'Match'] = "Conciliado Exacto (Monto)"
                 df_banco.at[index, 'Factura_Referencia'] = fact_ref
                 gastos_pendientes.at[idx_match, 'Conciliado'] = True
                 continue

    # Resumen de XMLs no encontrados en el banco (Posibles "No Cobrados/No Pagados" pero que son PUE)
    xmls_sin_banco = pd.concat([
        ventas_pendientes[ventas_pendientes['Conciliado'] == False],
        gastos_pendientes[gastos_pendientes['Conciliado'] == False]
    ])
    
    return df_banco, xmls_sin_banco, "Conciliación Finalizada"
