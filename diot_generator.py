import pandas as pd

def generar_txt_diot(df_facturas, rfc_cliente):
    """
    Genera el archivo de texto plano (Carga Batch) para la DIOT (A29).
    Filtra solo los Gastos (Compras) del cliente (donde el cliente es el receptor).
    
    El layout oficial de la DIOT (simplificado para operaciones al 16%) es:
    1: Tipo de Tercero (04 = Nacional, 05 = Extranjero, 15 = Global)
    2: Tipo de Operación (85 = Otros)
    3: RFC del Tercero
    4: Número de ID Fiscal (Solo extranjeros)
    5: Nombre del Extranjero (Solo extranjeros)
    6: País de Residencia (Solo extranjeros)
    7: Nacionalidad (Solo extranjeros)
    8: Valor de los actos o actividades pagados a la tasa del 15% o 16% (Base)
    9: Valor... 15% o 16% (Otras operaciones)
    10: Monto del IVA no acreditable (Tasa 15% o 16%)
    ... (Muchos campos de tasas 10%, 11%, 8%, 0%, Exentos)
    21: IVA Retenido por el contribuyente
    """
    if df_facturas.empty:
        return ""
        
    # Filtrar solo Gastos PUE (Pagados en el mes)
    df_gastos = df_facturas[(df_facturas['Clasificacion_Contable'] == 'Gasto (Deducción)') & 
                            (df_facturas['Metodo_Pago'] == 'PUE')]
                            
    if df_gastos.empty:
        return ""

    # Agrupar por RFC del Proveedor (Emisor)
    # La DIOT pide el total pagado en el mes por cada RFC
    agrupado = df_gastos.groupby('Emisor_RFC').agg({
        'SubTotal': 'sum',
        'IVA_Trasladado': 'sum',
        'IVA_Retenido': 'sum'
    }).reset_index()

    lineas_txt = []
    
    for index, row in agrupado.iterrows():
        rfc_proveedor = row['Emisor_RFC']
        base_16 = row['SubTotal'] # Asumiendo que todo el subtotal es gravado al 16% para este MVP
        iva_retenido = row['IVA_Retenido']
        
        # Redondear valores enteros para la DIOT
        base_16_int = int(round(base_16, 0))
        iva_retenido_int = int(round(iva_retenido, 0))
        
        # Ignorar si no hay base ni retenciones
        if base_16_int == 0 and iva_retenido_int == 0:
            continue
            
        # Determinar Tipo de Tercero
        # Si la longitud del RFC es diferente a 12 o 13, o es XEXX010101000, es extranjero o global.
        # Simplificación: Asumimos todos 04 Nacionales por ahora.
        tipo_tercero = "04"
        if rfc_proveedor.upper() == "XEXX010101000":
             tipo_tercero = "05" # Extranjero
        elif rfc_proveedor.upper() == "XAXX010101000":
             tipo_tercero = "15" # Global
             
        tipo_operacion = "85" # 85 Otros (Prestación de Servicios Profesionales, Arrendamiento, etc.)
        
        # Construir la línea separada por pipes '|'
        # El formato tiene 22 o 24 campos dependiendo de la versión exacta, usamos el estándar de 22.
        # Campos 1 al 7
        linea = f"{tipo_tercero}|{tipo_operacion}|{rfc_proveedor}|||||"
        # Campo 8: Base 16%
        linea += f"{base_16_int}|"
        # Campos 9 al 20 vacíos (Otras tasas, importaciones, 0%, Exentos)
        linea += "||||||||||||"
        # Campo 21: IVA Retenido
        linea += f"{iva_retenido_int}|"
        # Campo 22: Devoluciones (vacío)
        linea += "|"
        
        lineas_txt.append(linea)
        
    # Unir todas las líneas con saltos de línea
    # Importante: El archivo TXT de la DIOT no debe llevar espacios ni caracteres raros
    contenido_txt = "\n".join(lineas_txt)
    
    return contenido_txt
