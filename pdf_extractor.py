import pdfplumber
import re

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

    # Buscar Fecha de Generación de la constancia
    # Usualmente aparece al principio o al final como "Lugar y Fecha de Emisión"
    fecha_gen_match = re.search(r"(?:Lugar y Fecha de Emisión|Fecha, hora y lugar de emisión)[^\d]*(\d{2} de [A-Za-z]+ de \d{4})", texto, re.IGNORECASE)
    if fecha_gen_match:
        datos["fecha_generacion"] = fecha_gen_match.group(1)
    else:
        # Intento alternativo de buscar una fecha genérica cerca de la emisión
        alt_fecha_match = re.search(r"emisión:\s*.*?(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
        if alt_fecha_match:
             datos["fecha_generacion"] = alt_fecha_match.group(1)

    # Buscar RFC
    # Un RFC tiene 3 letras para Morales o 4 para Físicas, 6 números, y 3 caracteres alfanuméricos.
    rfc_match = re.search(r"RFC:\s*([A-ZÑ&]{3,4}\d{6}[A-V1-9][A-Z1-9][0-9A-Z])", texto, re.IGNORECASE)
    if not rfc_match:
         # Intento alternativo por si el formato es distinto
         rfc_match = re.search(r"([A-ZÑ&]{3,4}\d{6}[A-V1-9][A-Z1-9][0-9A-Z])", texto)
         
    if rfc_match:
        datos["rfc"] = rfc_match.group(1).upper()
        # Determinar si es física o moral por la longitud del RFC (13 física, 12 moral)
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
    # A menudo aparece cerca de "Nombre, denominación o razón social:"
    nombre_match = re.search(r"Nombre \(s\):\s*([^\n]+)", texto, re.IGNORECASE)
    apellidos_match = re.search(r"Primer Apellido:\s*([^\n]+)\nSegundo Apellido:\s*([^\n]+)", texto, re.IGNORECASE)
    razon_match = re.search(r"Denominación/Razón Social:\s*([^\n]+)", texto, re.IGNORECASE)
    
    if razon_match:
         datos["nombre"] = razon_match.group(1).strip()
    elif nombre_match and apellidos_match:
         nombre = nombre_match.group(1).strip()
         ap1 = apellidos_match.group(1).strip()
         ap2 = apellidos_match.group(2).strip()
         datos["nombre"] = f"{nombre} {ap1} {ap2}".strip()

    # Buscar Estatus en el padrón
    estatus_match = re.search(r"Estatus en el padrón:\s*([^\n]+)", texto, re.IGNORECASE)
    if estatus_match:
        datos["estatus_padron"] = estatus_match.group(1).strip()

    # Buscar Fecha de inicio de operaciones
    fecha_inicio_match = re.search(r"Fecha de inicio de operaciones:\s*([\d/]+)", texto, re.IGNORECASE)
    if fecha_inicio_match:
        datos["fecha_inicio_operaciones"] = fecha_inicio_match.group(1).strip()

    # Buscar Código Postal
    cp_match = re.search(r"Código Postal:\s*(\d{5})", texto, re.IGNORECASE)
    if cp_match:
        datos["codigo_postal"] = cp_match.group(1)
    else:
        # Buscar en formato C.P.
        cp_alt_match = re.search(r"C\.P\.\s*(\d{5})", texto, re.IGNORECASE)
        if cp_alt_match:
            datos["codigo_postal"] = cp_alt_match.group(1)

    # Buscar Régimen Fiscal
    # Busca la palabra Régimen y extrae la línea o las palabras cercanas
    # En la CSF suele venir bajo "Regímenes:"
    regimen_match = re.search(r"Regímenes:\n*Régimen\s+([^\n]+)", texto, re.IGNORECASE)
    if not regimen_match:
         regimen_match = re.search(r"Régimen\s+([^\n]+)", texto, re.IGNORECASE)

    if regimen_match:
         regimen_texto = regimen_match.group(1).strip()
         # Filtrar basura si encuentra algo como "Régimen Capital" (Común en morales)
         if "Capital" not in regimen_texto and "Fiscal" not in regimen_texto:
            datos["regimen"] = regimen_texto
         else:
             # Buscar en una tabla de Regímenes (suelen tener una fecha al final, pero buscamos la descripción)
             regimen_match2 = re.search(r"(?:Régimen\s+)?([A-Za-z\s]+)\s+\d{2}/\d{2}/\d{4}", texto)
             if regimen_match2 and len(regimen_match2.group(1).strip()) > 5:
                  datos["regimen"] = regimen_match2.group(1).strip()

    # Buscar Actividad Económica
    # En la CSF suele venir en una tabla "Actividades Económicas:"
    # Intentamos capturar la primera actividad que tenga un porcentaje (ej. 100)
    actividad_match = re.search(r"Actividades Económicas:\n*(?:Orden\s+Actividad Económica\s+Porcentaje\s+Fecha Inicio\s+Fecha Fin\n)?(?:\d+\s+)?([^\n\d]+(?:\d{1,2}(?!\d)[^\n\d]+)*)\s+\d+\s+\d{2}/\d{2}/\d{4}", texto, re.IGNORECASE)
    if actividad_match:
        datos["actividad_economica"] = actividad_match.group(1).strip()
    else:
        # Fallback genérico para actividad económica
        act_alt_match = re.search(r"Actividad Económica:\s*([^\n]+)", texto, re.IGNORECASE)
        if act_alt_match:
             datos["actividad_economica"] = act_alt_match.group(1).strip()

    return datos, "Extracción exitosa"
