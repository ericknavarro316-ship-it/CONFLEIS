import pdfplumber
import re

def split_joined_words(text):
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

def extraer_datos_constancia(pdf_file):
    """
    Extrae Nombre/Razón Social, RFC, Régimen y otros datos de un PDF de
    Constancia de Situación Fiscal usando expresiones regulares.
    """
    datos = {
        "rfc": "",
        "nombre": "",
        "regimen": "", # Will store a list as a string
        "tipo_persona": "",
        "codigo_postal": "",
        "domicilio": "",
        "curp": "",
        "actividad_economica": "", # Will store a list as a string
        "fecha_inicio_operaciones": "",
        "estatus_padron": "",
        "fecha_generacion": "",
        "obligaciones": [] # List of dicts
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

    texto_espaciado = split_joined_words(texto)

    # Fecha Generacion
    fecha_gen_match = re.search(r"(?:Lugar y Fecha de Emisión|Fecha, hora y lugar de emisión)[^\d]*(\d{2}\s*DE\s*[a-zA-Z]+\s*DE\s*\d{4})", texto, re.IGNORECASE)
    if fecha_gen_match:
        val = fecha_gen_match.group(1).replace('\n', ' ')
        datos["fecha_generacion"] = re.sub(r'\s+', ' ', val).upper()
    else:
        alt_fecha_match = re.search(r"emisión:\s*.*?(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
        if alt_fecha_match:
             datos["fecha_generacion"] = alt_fecha_match.group(1)
        else:
             match = re.search(r"A\s*(\d{2}\s*DE\s*[a-zA-Z]+\s*DE[\s\n]*\d{4})", texto[:1000], re.IGNORECASE)
             if match:
                 val = match.group(1).replace('\n', ' ')
                 datos["fecha_generacion"] = re.sub(r'\s+', ' ', val).upper()
             else:
                 match = re.search(r"(\d{2}\s*DE\s*[a-zA-Z]+\s*DE[\s\n]*\d{4})", texto[:50], re.IGNORECASE)
                 if match:
                     val = match.group(1).replace('\n', ' ')
                     datos["fecha_generacion"] = re.sub(r'\s+', ' ', val).upper()

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

    # Buscar CURP
    if datos["tipo_persona"] == "Física":
        curp_match = re.search(r"CURP:\s*([A-Z]{4}\d{6}[HM][A-Z]{5}[0-9A-Z]\d)", texto, re.IGNORECASE)
        if curp_match:
            datos["curp"] = curp_match.group(1).upper()

    # Buscar Nombre
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

    if datos["nombre"]:
        datos["nombre"] = re.sub(r'\s+', ' ', datos["nombre"])

    # Estatus en el padrón
    estatus_match = re.search(r"Estatus\s*en\s*el\s*padrón:\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
    if estatus_match:
        datos["estatus_padron"] = estatus_match.group(1).strip()

    # Fecha de inicio de operaciones
    fecha_inicio_match = re.search(r"Fecha\s*inicio\s*de\s*operaciones:\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
    if not fecha_inicio_match:
        fecha_inicio_match = re.search(r"Fecha\s*de\s*inicio\s*de\s*operaciones:\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
    if fecha_inicio_match:
        val = fecha_inicio_match.group(1).strip()
        val = re.sub(r"(\d{2})DE([A-Z]+)DE(\d{4})", r"\1 DE \2 DE \3", val, flags=re.IGNORECASE)
        datos["fecha_inicio_operaciones"] = val

    # Domicilio y Código Postal
    cp_match = re.search(r"Código\s*Postal:\s*(\d{5})", texto_espaciado, re.IGNORECASE)
    if not cp_match:
        cp_match = re.search(r"C\.P\.\s*(\d{5})", texto_espaciado, re.IGNORECASE)
    if cp_match:
        datos["codigo_postal"] = cp_match.group(1)

    # Extraer todo el bloque de Domicilio Registrado
    dom_block = re.search(r"Datos del domicilio registrado(.*?)(?:Actividades Económicas|Características|Regímenes)", texto_espaciado, re.IGNORECASE | re.DOTALL)
    if dom_block:
        dom_lines = dom_block.group(1).strip()
        # Remove pagination headers/footers
        dom_lines = re.sub(r'Página\s*\[\d+\]\s*de\s*\[\d+\]', '', dom_lines, flags=re.IGNORECASE)
        dom_lines = re.sub(r'\s+', ' ', dom_lines)
        datos["domicilio"] = dom_lines.strip()

    # Buscar Régimen Fiscal - Ahora extraemos TODOS
    regimenes = []
    block_match = re.search(r"Regímenes:(.*?)(?:Obligaciones|Sus\s*datos\s*personales)", texto_espaciado, re.IGNORECASE | re.DOTALL)
    if block_match:
        block = block_match.group(1)
        for line in block.split('\n'):
            line = line.strip()
            match = re.search(r"^(.*?)\s+\d{2}/\d{2}/\d{4}", line)
            if match:
                regimen = match.group(1).strip()
                # Skip the column headers if they end up being matched
                if "Fecha Inicio" not in regimen and regimen != "Régimen":
                    regimenes.append(regimen)
    else:
        # Fallback
        regimen_match = re.search(r"Régimen\s+([^\n]+)", texto_espaciado, re.IGNORECASE)
        if regimen_match:
             regimen_texto = regimen_match.group(1).strip()
             if "Capital" not in regimen_texto and "Fiscal" not in regimen_texto:
                regimenes.append(regimen_texto)

    if regimenes:
        datos["regimen"] = "\n".join(regimenes)

    # Buscar Actividades Económicas - Ahora extraemos TODAS
    actividades = []
    act_block = re.search(r"Actividades\s*Económicas:(.*?)Regímenes:", texto_espaciado, re.IGNORECASE | re.DOTALL)
    if act_block:
        block = act_block.group(1)
        for line in block.split('\n'):
            line = line.strip()
            # Try to match with the percentage included
            match = re.search(r"^\d+\s+(.*?)\s+(\d+)\s+\d{2}/\d{2}/\d{4}", line)
            if match:
                act = match.group(1).strip()
                pct = match.group(2).strip()
                if act:
                    act = re.sub(r'\d+$', '', act).strip()
                    actividades.append(f"{act} ({pct}%)")
            else:
                # Fallback without percentage
                match_fallback = re.search(r"^\d+\s+(.*?)(?:\s+\d+|\d+)\s+\d{2}/\d{2}/\d{4}", line)
                if match_fallback:
                    act = match_fallback.group(1).strip()
                    if act:
                        act = re.sub(r'\d+$', '', act).strip()
                        actividades.append(act)
    else:
        act_alt_match = re.search(r"Actividad\s*Económica:\s*([^\n]+)", texto_espaciado, re.IGNORECASE)
        if act_alt_match:
             actividades.append(act_alt_match.group(1).strip())

    if actividades:
        datos["actividad_economica"] = "\n".join(actividades)

    # Extraer Obligaciones
    obl_block = re.search(r"Obligaciones:(.*?)(?:Sus\s*datos\s*personales|Cadena\s*Original)", texto_espaciado, re.IGNORECASE | re.DOTALL)
    if obl_block:
        block = obl_block.group(1)
        lines = [line.strip() for line in block.split('\n') if line.strip()]

        if lines and "Descripción de la Obligación" in lines[0]:
            lines = lines[1:]

        current_text = ""
        raw_obligations = []
        for line in lines:
            if re.search(r"\d{2}/\d{2}/\d{4}$", line):
                current_text += (" " + line if current_text else line)
                cleaned = re.sub(r'\s*\d{2}/\d{2}/\d{4}(\s+\d{2}/\d{2}/\d{4})?$', '', current_text).strip()
                cleaned = re.sub(r'Página\s*\[\d+\]\s*de\s*\[\d+\]', '', cleaned, flags=re.IGNORECASE)

                vencimiento_match = re.search(r"(A\s*más\s*tardar|Dentro\s*de|A\s*mas\s*tardar|Dentro\s*del)(.*?)$", cleaned, re.IGNORECASE)
                if vencimiento_match:
                    desc_obl = cleaned[:vencimiento_match.start()].strip()
                    desc_venc = vencimiento_match.group(0).strip()
                    raw_obligations.append({
                        "descripcion": desc_obl,
                        "vencimiento": desc_venc
                    })
                else:
                    raw_obligations.append({
                        "descripcion": cleaned,
                        "vencimiento": ""
                    })
                current_text = ""
            else:
                current_text += (" " + line if current_text else line)

        # Phase 1: Fix broken descriptions due to wrapped columns
        for i in range(1, len(raw_obligations)):
            desc = raw_obligations[i]["descripcion"]

            # NOEMI: the description string might contain "Confianza." which belongs to previous description
            match_noemi = re.search(r"^(Confianza\.|Régimen Simplificado de|Régimen General|Ley|Morales\.)(.*)", desc, re.IGNORECASE)
            if match_noemi:
                 raw_obligations[i-1]["descripcion"] += " " + match_noemi.group(1).strip()
                 desc = match_noemi.group(2).strip()

            # Now `desc` might be " inmediato posterior a aquél al que corresponda elpago Ajuste anual..."
            # Check if desc starts with leftover of previous vencimiento
            match_venc_left = re.search(r"^(inmediato\s*posterior.*?pago\.?|posterior.*?corresponda\.?|ejercicio\.?|general\s*posterior.*?corresponda\.?)\s*(.*)", desc, re.IGNORECASE)
            if match_venc_left:
                raw_obligations[i-1]["vencimiento"] += " " + match_venc_left.group(1).strip()
                desc = match_venc_left.group(2).strip()

            # If desc starts with "pago" and it's not a capital Pago provisional...
            if desc.lower().startswith("pago ") and not re.search(r"^Pago\s+(provisional|definitivo)", desc, re.IGNORECASE):
                match_pago = re.search(r"^(pago)\s+(Ajuste|Declaración|Entero|Retención)(.*)", desc, re.IGNORECASE)
                if match_pago:
                    raw_obligations[i-1]["vencimiento"] += " " + match_pago.group(1).strip()
                    desc = match_pago.group(2).strip() + " " + match_pago.group(3).strip()

            raw_obligations[i]["descripcion"] = desc

        # Phase 2: Fix trailing keywords in vencimiento that belong to NEXT description
        for i in range(len(raw_obligations) - 1):
             v = raw_obligations[i]["vencimiento"]
             end_match = re.search(r"(.*)\s+(Pago|Entero|Declaración|Ajuste)$", v, re.IGNORECASE)
             if end_match:
                 raw_obligations[i]["vencimiento"] = end_match.group(1).strip()
                 raw_obligations[i+1]["descripcion"] = end_match.group(2).strip() + " " + raw_obligations[i+1]["descripcion"]

        # Final cleanup
        final_obs = []
        for ob in raw_obligations:
            desc = re.sub(r'\s+', ' ', ob["descripcion"]).strip()
            venc = re.sub(r'\s+', ' ', ob["vencimiento"]).strip()

            # Clean up the word "pago" if it got stuck to "elpago" (split_joined_words doesn't always work if lowercase)
            venc = venc.replace("elpago", "el pago")

            if desc or venc:
                final_obs.append({"descripcion": desc, "vencimiento": venc})

        datos["obligaciones"] = final_obs

    return datos, "Extracción exitosa"
