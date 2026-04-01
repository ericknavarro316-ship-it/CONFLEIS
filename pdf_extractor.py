import pdfplumber
import re

def split_joined_words(text):
    # Agrega espacio entre minúscula y mayúscula
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

def extraer_datos_constancia(pdf_file):
    """
    Extrae Nombre/Razón Social, RFC, Régimen y otros datos de un PDF de
    Constancia de Situación Fiscal usando expresiones regulares.
    """
    datos = {
        "rfc": "",
        "nombre": "",
        "regimen": "",
        "tipo_persona": "",
        "codigo_postal": "",
        "curp": "",
        "actividad_economica": "",
        "fecha_inicio_operaciones": "",
        "estatus_padron": "",
        "fecha_generacion": ""
    }
    
    texto = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    texto += extracted + "\n"
    except Exception as e:
        return datos, f"Error al leer el PDF: {str(e)}"

    # Añadir espacios donde se juntaron palabras minúscula y mayúscula para facilitar lectura
    texto_espaciado = split_joined_words(texto)

    # Buscar Fecha de Generación de la constancia (al inicio, para no confundir con operaciones)
    fecha_gen_match = re.search(r"(?:Lugar y Fecha de Emisión|Fecha, hora y lugar de emisión)[^\d]*(\d{2}\s*DE\s*[a-zA-Z]+\s*DE\s*\d{4})", texto, re.IGNORECASE)
    if fecha_gen_match:
        val = fecha_gen_match.group(1).replace('\n', ' ')
        datos["fecha_generacion"] = re.sub(r'\s+', ' ', val).upper()
    else:
        alt_fecha_match = re.search(r"emisión:\s*.*?(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
        if alt_fecha_match:
             datos["fecha_generacion"] = alt_fecha_match.group(1)
        else:
             # Look for "16 DE FEBRERO DE \n social \n 2026" or similar
             match = re.search(r"(\d{2}\s*DE\s*[a-zA-Z]+\s*DE(?:\s|\n|[a-zA-Z])*?\d{4})", texto[:1000], re.IGNORECASE)
             if match:
                 val = match.group(1)
                 # Remove random text like "social" that might have gotten injected
                 val = re.sub(r'[a-zA-Z]+$', '', val.split('20')[0]).strip() + ' 20' + val.split('20')[1] if '20' in val else val
                 val = re.sub(r'\s+', ' ', val)
                 # Clean any remaining non-date words in between like "social"
                 val = re.sub(r'DE\s+[a-zA-Z]+\s+20', 'DE 20', val, flags=re.IGNORECASE)
                 datos["fecha_generacion"] = val.upper().strip()

    # Buscar RFC
    rfc_match = re.search(r"RFC:\s*([A-ZÑ&]{3,4}\d{6}[A-V1-9][A-Z1-9][0-9A-Z])", texto, re.IGNORECASE)
    if not rfc_match:
         rfc_match = re.search(r"([A-ZÑ&]{3,4}\d{6}[A-V1-9][A-Z1-9][0-9A-Z])", texto)
         
    if rfc_match:
        datos["rfc"] = rfc_match.group(1).upper()
        if len(datos["rfc"]) == 13:
             datos["tipo_persona"] = "Física"
        else:
             datos["tipo_persona"] = "Moral"

    # Buscar CURP (solo físicas)
    if datos["tipo_persona"] == "Física":
        curp_match = re.search(r"CURP:\s*([A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]\d)", texto, re.IGNORECASE)
        if curp_match:
            datos["curp"] = curp_match.group(1).upper()

    # Buscar Nombre, Denominación o Razón Social
    razon_match = re.search(r"Denominación(?:/Razón\s*Social|/RazónSocial)?:\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
    nombre_match = re.search(r"Nombre\(s\):\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
    apellidos_match1 = re.search(r"Primer\s*Apellido:\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
    apellidos_match2 = re.search(r"Segundo\s*Apellido:\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
    
    if razon_match:
         datos["nombre"] = razon_match.group(1).strip()
    elif nombre_match:
         nombre = nombre_match.group(1).strip()
         ap1 = apellidos_match1.group(1).strip() if apellidos_match1 else ""
         ap2 = apellidos_match2.group(1).strip() if apellidos_match2 else ""
         datos["nombre"] = f"{nombre} {ap1} {ap2}".strip()

    # Formatear el nombre agregando espacios en CamelCase si el PDF juntó palabras
    if datos["nombre"]:
        datos["nombre"] = re.sub(r'\s+', ' ', datos["nombre"])

    # Buscar Estatus en el padrón
    estatus_match = re.search(r"Estatus\s*en\s*el\s*padrón:\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
    if estatus_match:
        datos["estatus_padron"] = estatus_match.group(1).strip()

    # Buscar Fecha de inicio de operaciones
    fecha_inicio_match = re.search(r"Fecha\s*inicio\s*de\s*operaciones:\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
    if not fecha_inicio_match:
        fecha_inicio_match = re.search(r"Fecha\s*de\s*inicio\s*de\s*operaciones:\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
    if fecha_inicio_match:
        val = fecha_inicio_match.group(1).strip()
        val = re.sub(r"(\d{2})DE([A-Z]+)DE(\d{4})", r"\1 DE \2 DE \3", val, flags=re.IGNORECASE)
        datos["fecha_inicio_operaciones"] = val

    # Buscar Código Postal
    cp_match = re.search(r"Código\s*Postal:\s*(\d{5})", texto_espaciado, re.IGNORECASE)
    if not cp_match:
        cp_match = re.search(r"C\.P\.\s*(\d{5})", texto_espaciado, re.IGNORECASE)
    if cp_match:
        datos["codigo_postal"] = cp_match.group(1)

    # Buscar Régimen Fiscal
    block_match = re.search(r"Regímenes:(.*?)Obligaciones:", texto_espaciado, re.IGNORECASE | re.DOTALL)
    if block_match:
        block = block_match.group(1)
        for line in block.split('\n'):
            line = line.strip()
            match = re.search(r"^(.*?)\s+\d{2}/\d{2}/\d{4}", line)
            if match:
                regimen = match.group(1).strip()
                if "Fecha Inicio" not in regimen and regimen != "Régimen":
                    datos["regimen"] = regimen
                    break # Tomamos el primero
    else:
        # Fallback
        regimen_match = re.search(r"Régimen\s+([^\n]+)", texto_espaciado, re.IGNORECASE)
        if regimen_match:
             regimen_texto = regimen_match.group(1).strip()
             if "Capital" not in regimen_texto and "Fiscal" not in regimen_texto:
                datos["regimen"] = regimen_texto

    # Buscar Actividad Económica
    act_block = re.search(r"Actividades\s*Económicas:(.*?)Regímenes:", texto_espaciado, re.IGNORECASE | re.DOTALL)
    if act_block:
        block = act_block.group(1)
        for line in block.split('\n'):
            line = line.strip()
            # Match start with digit and end with date, extracting string in middle
            match = re.search(r"^\d+\s+(.*?)(?:\s+\d+|\d+)\s+\d{2}/\d{2}/\d{4}", line)
            if match:
                act = match.group(1).strip()
                if act:
                    # Remove trailing percentage if it stuck to the text
                    act = re.sub(r'\d+$', '', act).strip()
                    datos["actividad_economica"] = act
                    break
    else:
        act_alt_match = re.search(r"Actividad\s*Económica:\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
        if act_alt_match:
             datos["actividad_economica"] = act_alt_match.group(1).strip()

    return datos, "Extracción exitosa"
