import pdfplumber
import re

def extraer_datos_constancia(pdf_file):
    """
    Extrae Nombre/Razón Social, RFC y Régimen de un PDF de 
    Constancia de Situación Fiscal usando expresiones regulares.
    """
    datos = {
        "rfc": "",
        "nombre": "",
        "regimen": "",
        "tipo_persona": ""
    }
    
    texto = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                texto += page.extract_text() + "\n"
    except Exception as e:
        return datos, f"Error al leer el PDF: {str(e)}"

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

    # Buscar Régimen Fiscal
    # Busca la palabra Régimen y extrae la línea o las palabras cercanas
    regimen_match = re.search(r"Régimen\s+([^\n]+)", texto, re.IGNORECASE)
    if regimen_match:
         regimen_texto = regimen_match.group(1).strip()
         # Filtrar basura si encuentra algo como "Régimen Capital" (Común en morales)
         if "Capital" not in regimen_texto:
            datos["regimen"] = regimen_texto
         else:
             # Buscar de nuevo
             regimen_match2 = re.search(r"Régimen:\s*([^\n]+)", texto, re.IGNORECASE)
             if regimen_match2:
                  datos["regimen"] = regimen_match2.group(1).strip()

    return datos, "Extracción exitosa"
