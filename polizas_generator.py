import pandas as pd
from datetime import datetime

def generar_polizas_contpaqi(df_facturas, rfc_cliente):
    """
    Genera un archivo TXT con el layout estándar de CONTPAQi Contabilidad.
    Estructura simplificada:
    - Registro de Póliza: P | Fecha(YYYYMMDD) | Tipo | Número | Concepto | Diario | 1 (Sin Ajuste) | Concepto Adicional
    - Registro de Movimiento: M | Cuenta | Referencia | Tipo (1=Cargo, 2=Abono) | Importe | 0 | Concepto | Diario
    
    Tipo de Póliza CONTPAQi: 1=Ingresos, 2=Egresos, 3=Diario
    
    Por cada factura, generamos una póliza de "Provisión" (Diario).
    """
    if df_facturas.empty:
        return ""
        
    lineas_txt = []
    numero_poliza = 1
    
    for index, row in df_facturas.iterrows():
        try:
            # Parsear fecha de YYYY-MM-DD a YYYYMMDD
            dt = datetime.fromisoformat(row['Fecha'])
            fecha_contpaqi = dt.strftime("%Y%m%d")
        except:
            continue # Si no hay fecha válida, saltamos

        serie_folio = str(row.get('Serie_Folio', ''))
        subtotal = round(float(row.get('SubTotal', 0)), 2)
        iva = round(float(row.get('IVA_Trasladado', 0)), 2)
        total = round(float(row.get('Total', 0)), 2)
        tipo = row.get('Tipo', '')
        clasificacion = row.get('Clasificacion_Contable', '')
        
        # Ignorar si no hay valores monetarios
        if total == 0:
            continue
            
        concepto_poliza = f"Prov. Fac {serie_folio}"
        
        # 1. ENCABEZADO DE PÓLIZA (P)
        # Tipo 3 = Diario (Provisión)
        linea_p = f"P {fecha_contpaqi} 3 {numero_poliza} 1 0 {concepto_poliza} 11  "
        lineas_txt.append(linea_p)
        
        # Cuentas Contables Ficticias (En producción, el cliente las mapearía)
        cta_clientes = "105-01-000"
        cta_proveedores = "201-01-000"
        cta_ventas = "401-01-000"
        cta_compras = "501-01-000"
        cta_iva_trasladado_no_cobrado = "209-01-000"
        cta_iva_acreditable_no_pagado = "119-01-000"

        # 2. DETALLE DE MOVIMIENTOS (M)
        if "Venta" in clasificacion:
            # Provisión de Ingreso
            # Cargo a Clientes (1)
            lineas_txt.append(f"M {cta_clientes} {serie_folio} 1 {total} 0 {concepto_poliza} ")
            # Abono a Ventas (2)
            lineas_txt.append(f"M {cta_ventas} {serie_folio} 2 {subtotal} 0 {concepto_poliza} ")
            # Abono a IVA Trasladado (2)
            if iva > 0:
                lineas_txt.append(f"M {cta_iva_trasladado_no_cobrado} {serie_folio} 2 {iva} 0 {concepto_poliza} ")
                
        elif "Gasto" in clasificacion:
            # Provisión de Gasto
            # Cargo a Gastos/Compras (1)
            lineas_txt.append(f"M {cta_compras} {serie_folio} 1 {subtotal} 0 {concepto_poliza} ")
            # Cargo a IVA Acreditable (1)
            if iva > 0:
                lineas_txt.append(f"M {cta_iva_acreditable_no_pagado} {serie_folio} 1 {iva} 0 {concepto_poliza} ")
            # Abono a Proveedores (2)
            lineas_txt.append(f"M {cta_proveedores} {serie_folio} 2 {total} 0 {concepto_poliza} ")
            
        else:
            # Si no es venta ni gasto, descartamos para no desbalancear
            lineas_txt.pop() # Borramos el encabezado que acabamos de meter
            continue
            
        numero_poliza += 1

    # CONTPAQi usa ANSI o UTF-8 sin BOM para TXT.
    return "\n".join(lineas_txt)