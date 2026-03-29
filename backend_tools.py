import pandas as pd
import database as db
import io
import os
from colorthief import ColorThief
from fpdf import FPDF
from datetime import datetime

# --- Lógica de Extracción de Colores ---
def extraer_colores_de_imagen(ruta_imagen):
    """
    Usa ColorThief para extraer la paleta de colores dominante de una imagen.
    Retorna (color1, color2, color3) en formato Hex.
    """
    try:
        color_thief = ColorThief(ruta_imagen)
        # Extraer paleta de 3 colores
        paleta = color_thief.get_palette(color_count=3, quality=1)
        
        # Función auxiliar para convertir RGB a HEX
        def rgb2hex(r, g, b):
            return f"#{r:02x}{g:02x}{b:02x}"
            
        hex_colors = [rgb2hex(c[0], c[1], c[2]) for c in paleta]
        
        # Rellenar con negro si no se extrajeron suficientes colores
        while len(hex_colors) < 3:
            hex_colors.append("#000000")
            
        return hex_colors[0], hex_colors[1], hex_colors[2]
    except Exception as e:
        print(f"Error extrayendo colores: {e}")
        return "#000000", "#FFCC00", "#CC0000" # Valores por defecto

# --- Lógica de Facturación Simulada ---
def simular_timbrado_factura(cliente_nombre, cliente_rfc, monto, concepto):
    """
    Genera un PDF y un XML que simula una factura timbrada por el SAT.
    """
    uuid_simulado = "ABCD1234-EF56-7890-1234-567890ABCDEF"
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subtotal = float(monto)
    iva = subtotal * 0.16
    total = subtotal + iva
    
    # --- Generar PDF ---
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Encabezado
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Factura CFDI (Simulada)", ln=True, align='C')
    pdf.ln(10)
    
    # Datos del Emisor (El Cliente)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=f"Emisor: {cliente_nombre}", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"RFC: {cliente_rfc}", ln=True)
    pdf.cell(200, 10, txt=f"Fecha de Emisión: {fecha_actual}", ln=True)
    pdf.cell(200, 10, txt=f"Folio Fiscal (UUID): {uuid_simulado}", ln=True)
    pdf.ln(10)
    
    # Conceptos
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, txt="Concepto", border=1)
    pdf.cell(50, 10, txt="Importe", border=1, ln=True, align='R')
    pdf.set_font("Arial", size=12)
    pdf.cell(140, 10, txt=concepto, border=1)
    pdf.cell(50, 10, txt=f"${subtotal:,.2f}", border=1, ln=True, align='R')
    pdf.ln(5)
    
    # Totales
    pdf.cell(140, 10, txt="Subtotal:", align='R')
    pdf.cell(50, 10, txt=f"${subtotal:,.2f}", ln=True, align='R')
    pdf.cell(140, 10, txt="IVA (16%):", align='R')
    pdf.cell(50, 10, txt=f"${iva:,.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, txt="TOTAL:", align='R')
    pdf.cell(50, 10, txt=f"${total:,.2f}", ln=True, align='R')
    
    # Sello digital simulado
    pdf.ln(15)
    pdf.set_font("Arial", size=8)
    pdf.multi_cell(0, 5, txt="Sello Digital del CFDI:\nxXXxxXXXxxxxXXXXxXXxxxXXxXxxxXxxxxXxxXxxXxxXXxxXXXXxxxXXXXXxxxxXxxXxXXXXxXxXX")
    
    # Save to BytesIO
    pdf_output = pdf.output(dest='S').encode('latin1')
    
    # --- Generar XML ---
    xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0" Fecha="{fecha_actual}" SubTotal="{subtotal:.2f}" Moneda="MXN" Total="{total:.2f}" TipoDeComprobante="I" Exportacion="01">
  <cfdi:Emisor Rfc="{cliente_rfc}" Nombre="{cliente_nombre}" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="XAXX010101000" Nombre="PUBLICO EN GENERAL" UsoCFDI="S01" DomicilioFiscalReceptor="00000" RegimenFiscalReceptor="616"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="84111500" Cantidad="1" ClaveUnidad="E48" Descripcion="{concepto}" ValorUnitario="{subtotal:.2f}" Importe="{subtotal:.2f}" ObjetoImp="02">
      <cfdi:Impuestos>
        <cfdi:Traslados>
          <cfdi:Traslado Base="{subtotal:.2f}" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="{iva:.2f}"/>
        </cfdi:Traslados>
      </cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="{iva:.2f}">
    <cfdi:Traslados>
      <cfdi:Traslado Base="{subtotal:.2f}" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="{iva:.2f}"/>
    </cfdi:Traslados>
  </cfdi:Impuestos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" Version="1.1" UUID="{uuid_simulado}" FechaTimbrado="{fecha_actual}" RfcProvCertif="SAT970701NN3" SelloCFD="xXXxxXXX..." NoCertificadoSAT="00001111222233334444" SelloSAT="yYYyyYYY..."/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""
    return pdf_output, xml_content.encode('utf-8')

# --- Lógica de Carga Masiva (Excel) ---
def procesar_carga_masiva_excel(file_bytes):
    """
    Lee un archivo excel con las columnas: Nombre, RFC, TipoPersona, Regimen, Email, Telefono
    Y los inserta en la base de datos de clientes.
    Retorna la cantidad de registros insertados y errores.
    """
    try:
        df = pd.read_excel(file_bytes)
        # Columnas requeridas mínimas
        req_cols = ['Nombre', 'RFC', 'TipoPersona']
        for c in req_cols:
            if c not in df.columns:
                return 0, f"Error: Faltó la columna requerida '{c}' en el Excel."
        
        insertados = 0
        errores = []
        
        for idx, row in df.iterrows():
            nombre = str(row['Nombre']).strip()
            rfc = str(row['RFC']).strip().upper()
            tipo_persona = str(row['TipoPersona']).strip()
            
            # Opcionales
            regimen = str(row.get('Regimen', ''))
            email = str(row.get('Email', ''))
            telefono = str(row.get('Telefono', ''))
            
            if pd.isna(nombre) or pd.isna(rfc) or pd.isna(tipo_persona):
                errores.append(f"Fila {idx+2}: Faltan datos obligatorios.")
                continue
                
            ok, msg = db.agregar_cliente(nombre, rfc, tipo_persona, regimen, email, telefono, "")
            if ok:
                insertados += 1
            else:
                errores.append(f"Fila {idx+2} ({rfc}): {msg}")
                
        return insertados, "\n".join(errores)
    except Exception as e:
        return 0, f"Error procesando el Excel: {e}"
