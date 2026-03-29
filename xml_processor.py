import xmltodict
import pandas as pd
from datetime import datetime

def extraer_datos_xml(xml_content):
    """
    Extrae los datos relevantes de un XML del SAT (CFDI 3.3 o 4.0).
    Acepta el contenido del archivo en bytes o string.
    """
    try:
        # Convertir a string si viene en bytes
        if isinstance(xml_content, bytes):
            # Intentar decodificar con utf-8, si falla, ignorar errores
            xml_content = xml_content.decode('utf-8', errors='ignore')
            
        doc = xmltodict.parse(xml_content)
        
        # El nodo principal suele ser cfdi:Comprobante
        comprobante = None
        for key in doc.keys():
            if 'Comprobante' in key:
                comprobante = doc[key]
                break
                
        if not comprobante:
            return None, "No es un CFDI válido del SAT."

        # Extraer atributos principales (dependiendo de la versión del CFDI, los atributos pueden usar @)
        version = comprobante.get('@Version', comprobante.get('@version', ''))
        tipo = comprobante.get('@TipoDeComprobante', comprobante.get('@tipoDeComprobante', ''))
        fecha = comprobante.get('@Fecha', comprobante.get('@fecha', ''))
        serie = comprobante.get('@Serie', comprobante.get('@serie', ''))
        folio = comprobante.get('@Folio', comprobante.get('@folio', ''))
        subtotal = float(comprobante.get('@SubTotal', comprobante.get('@subTotal', 0)))
        total = float(comprobante.get('@Total', comprobante.get('@total', 0)))
        metodo_pago = comprobante.get('@MetodoPago', comprobante.get('@metodoPago', ''))
        moneda = comprobante.get('@Moneda', comprobante.get('@moneda', 'MXN'))
        tipo_cambio = float(comprobante.get('@TipoCambio', comprobante.get('@tipoCambio', 1)))

        # Emisor y Receptor
        emisor = None
        receptor = None
        impuestos_nodo = None
        
        for key, value in comprobante.items():
            if 'Emisor' in key:
                emisor = value
            elif 'Receptor' in key:
                receptor = value
            elif 'Impuestos' in key and isinstance(value, dict):
                 # El nodo global de impuestos al final del CFDI
                 impuestos_nodo = value
                 
        rfc_emisor = emisor.get('@Rfc', emisor.get('@rfc', '')) if emisor else ''
        nombre_emisor = emisor.get('@Nombre', emisor.get('@nombre', '')) if emisor else ''
        
        rfc_receptor = receptor.get('@Rfc', receptor.get('@rfc', '')) if receptor else ''
        nombre_receptor = receptor.get('@Nombre', receptor.get('@nombre', '')) if receptor else ''
        uso_cfdi = receptor.get('@UsoCFDI', receptor.get('@usoCFDI', '')) if receptor else ''

        # Impuestos
        iva_trasladado = 0.0
        isr_retenido = 0.0
        iva_retenido = 0.0
        
        if impuestos_nodo:
             # Traslados
             traslados_nodo = impuestos_nodo.get('cfdi:Traslados', impuestos_nodo.get('Traslados'))
             if traslados_nodo:
                  traslados = traslados_nodo.get('cfdi:Traslado', traslados_nodo.get('Traslado', []))
                  # Si es solo un traslado, xmltodict lo parsea como dict, no list
                  if isinstance(traslados, dict):
                       traslados = [traslados]
                       
                  for t in traslados:
                       imp = t.get('@Impuesto', t.get('@impuesto', ''))
                       importe = float(t.get('@Importe', t.get('@importe', 0)))
                       if imp == '002': # 002 es IVA
                            iva_trasladado += importe
                            
             # Retenciones
             retenciones_nodo = impuestos_nodo.get('cfdi:Retenciones', impuestos_nodo.get('Retenciones'))
             if retenciones_nodo:
                  retenciones = retenciones_nodo.get('cfdi:Retencion', retenciones_nodo.get('Retencion', []))
                  if isinstance(retenciones, dict):
                       retenciones = [retenciones]
                       
                  for r in retenciones:
                       imp = r.get('@Impuesto', r.get('@impuesto', ''))
                       importe = float(r.get('@Importe', r.get('@importe', 0)))
                       if imp == '001': # 001 es ISR
                            isr_retenido += importe
                       elif imp == '002': # 002 es IVA
                            iva_retenido += importe

        # Convertir a MXN si es otra moneda
        if moneda != 'MXN' and tipo_cambio > 0:
             subtotal *= tipo_cambio
             total *= tipo_cambio
             iva_trasladado *= tipo_cambio
             isr_retenido *= tipo_cambio
             iva_retenido *= tipo_cambio

        # Complemento de Nómina (Tipo 'N')
        es_nomina = (tipo.upper() == 'N')
        sueldos_pagados = 0.0
        isr_retenido_nomina = 0.0
        imss_retenido_nomina = 0.0
        
        if es_nomina:
            complemento = comprobante.get('cfdi:Complemento', comprobante.get('Complemento'))
            if complemento:
                nomina = complemento.get('nomina12:Nomina', complemento.get('Nomina'))
                if nomina:
                    sueldos_pagados = float(nomina.get('@TotalPercepciones', nomina.get('@totalPercepciones', 0)))
                    
                    deducciones = nomina.get('nomina12:Deducciones', nomina.get('Deducciones'))
                    if deducciones:
                        deduccion_lista = deducciones.get('nomina12:Deduccion', deducciones.get('Deduccion', []))
                        if isinstance(deduccion_lista, dict):
                            deduccion_lista = [deduccion_lista]
                            
                        for d in deduccion_lista:
                            tipo_deduccion = d.get('@TipoDeduccion', d.get('@tipoDeduccion', ''))
                            importe_deduccion = float(d.get('@Importe', d.get('@importe', 0)))
                            
                            if tipo_deduccion == '002': # ISR
                                isr_retenido_nomina += importe_deduccion
                            elif tipo_deduccion == '001': # IMSS
                                imss_retenido_nomina += importe_deduccion

        # Solo extraer el mes y año de la fecha para reportes
        try:
             # Formato CFDI suele ser: 2023-10-25T14:30:00
             dt = datetime.fromisoformat(fecha)
             mes_anio = dt.strftime("%Y-%m")
        except:
             mes_anio = "Desconocido"
             
        # Definir tipo simplificado
        tipo_str = "Otro"
        if tipo.upper() == 'I': tipo_str = "Ingreso"
        elif tipo.upper() == 'E': tipo_str = "Egreso"
        elif tipo.upper() == 'N': tipo_str = "Nómina"

        datos = {
            "Fecha": fecha,
            "Mes_Anio": mes_anio,
            "Serie_Folio": f"{serie}{folio}",
            "Tipo": tipo_str,
            "Metodo_Pago": metodo_pago if not es_nomina else "PUE", # Nóminas usualmente se consideran efectivamente pagadas
            "Emisor_RFC": rfc_emisor,
            "Emisor_Nombre": nombre_emisor,
            "Receptor_RFC": rfc_receptor,
            "Receptor_Nombre": nombre_receptor,
            "Uso_CFDI": uso_cfdi,
            "SubTotal": round(subtotal, 2),
            "IVA_Trasladado": round(iva_trasladado, 2),
            "ISR_Retenido": round(isr_retenido, 2),
            "IVA_Retenido": round(iva_retenido, 2),
            "Total": round(total, 2),
            "Sueldos_Pagados": round(sueldos_pagados, 2),
            "ISR_Retenido_Nomina": round(isr_retenido_nomina, 2),
            "IMSS_Retenido_Nomina": round(imss_retenido_nomina, 2)
        }
        
        return datos, "Éxito"
    except Exception as e:
        return None, f"Error al parsear XML: {str(e)}"

def procesar_lote_xmls(archivos_xml, rfc_cliente):
    """
    Procesa una lista de archivos XML (UploadedFiles de Streamlit)
    y los clasifica como Ingresos o Gastos para un cliente en particular.
    Devuelve un DataFrame.
    """
    resultados = []
    
    for archivo in archivos_xml:
        # Leer el contenido
        contenido = archivo.read()
        datos, msj = extraer_datos_xml(contenido)
        
        if datos:
             # Clasificar si es Ingreso (Venta) o Gasto (Compra)
             # Es Ingreso si el cliente es el Emisor y es tipo 'I'
             # Es Gasto si el cliente es el Receptor y es tipo 'I' (factura que le emitieron)
             
             es_emisor = (datos["Emisor_RFC"].upper() == rfc_cliente.upper())
             es_receptor = (datos["Receptor_RFC"].upper() == rfc_cliente.upper())
             
             clasificacion = "Desconocido"
             
             if datos["Tipo"] == "Ingreso":
                  if es_emisor:
                       clasificacion = "Venta (Ingreso)"
                  elif es_receptor:
                       clasificacion = "Gasto (Deducción)"
                       
             elif datos["Tipo"] == "Egreso":
                  # Notas de crédito
                  if es_emisor:
                       clasificacion = "Nota de Crédito Emitida (Resta a Ventas)"
                  elif es_receptor:
                       clasificacion = "Nota de Crédito Recibida (Resta a Gastos)"
                       
             elif datos["Tipo"] == "Nómina":
                  if es_emisor:
                       clasificacion = "Nómina Emitida (Gasto)"
                  elif es_receptor:
                       clasificacion = "Nómina Recibida (Ingreso Asalariado)"
             
             datos["Clasificacion_Contable"] = clasificacion
             datos["Archivo"] = archivo.name
             resultados.append(datos)
             
    if resultados:
         return pd.DataFrame(resultados)
    else:
         return pd.DataFrame()

def resumir_facturas(df_facturas):
     """
     Toma el DataFrame de facturas y agrupa los totales por clasificación.
     Solo toma en cuenta facturas PUE (Pagadas). Las PPD requieren complementos de pago (fuera del alcance básico).
     """
     if df_facturas.empty:
          return {}
          
     # Filtrar solo PUE para cálculo simplificado de impuestos en base a flujo de efectivo
     df_pue = df_facturas[df_facturas["Metodo_Pago"] == "PUE"]
     
     resumen = {
          "Total_Ingresos_PUE": 0.0,
          "Total_Gastos_PUE": 0.0,
          "IVA_Cobrado": 0.0,
          "IVA_Pagado": 0.0,
          "ISR_Retenido_Cobrado": 0.0,
          "IVA_Retenido_Cobrado": 0.0,
          "Sueldos_Pagados": 0.0,
          "ISR_Retenido_Nomina_Total": 0.0,
          "IMSS_Retenido_Nomina_Total": 0.0
     }
     
     # Ingresos
     ventas = df_pue[df_pue["Clasificacion_Contable"] == "Venta (Ingreso)"]
     resumen["Total_Ingresos_PUE"] = ventas["SubTotal"].sum()
     resumen["IVA_Cobrado"] = ventas["IVA_Trasladado"].sum()
     resumen["ISR_Retenido_Cobrado"] = ventas["ISR_Retenido"].sum()
     resumen["IVA_Retenido_Cobrado"] = ventas["IVA_Retenido"].sum()
     
     # Gastos
     gastos = df_pue[df_pue["Clasificacion_Contable"] == "Gasto (Deducción)"]
     resumen["Total_Gastos_PUE"] = gastos["SubTotal"].sum()
     resumen["IVA_Pagado"] = gastos["IVA_Trasladado"].sum()
     
     # Nóminas Emitidas
     nominas = df_facturas[df_facturas["Clasificacion_Contable"] == "Nómina Emitida (Gasto)"]
     if not nominas.empty:
          resumen["Sueldos_Pagados"] = nominas["Sueldos_Pagados"].sum()
          resumen["ISR_Retenido_Nomina_Total"] = nominas["ISR_Retenido_Nomina"].sum()
          resumen["IMSS_Retenido_Nomina_Total"] = nominas["IMSS_Retenido_Nomina"].sum()
          # Sumar sueldos al total de gastos (deducción permitida)
          resumen["Total_Gastos_PUE"] += resumen["Sueldos_Pagados"]
     
     return resumen
