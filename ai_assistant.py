import re

def obtener_respuesta_fiscal(pregunta):
    """
    Mock AI Assistant for Mexican Tax Law.
    Analyzes keywords in the user's question and returns a pre-defined but legally sound response.
    In a real scenario, this would use OpenAI's API.
    """
    pregunta = pregunta.lower()
    
    if re.search(r'deducci(o|ó)n.*autom(o|ó)vil|tope.*auto|deducir.*coche|veh(i|í)culo', pregunta):
        return """**Tope de Deducción de Automóviles (LISR Art. 36)**
Para 2024, el monto máximo deducible para inversiones en automóviles es de **$175,000.00 MXN** (sin incluir IVA). 
Tratándose de vehículos híbridos o eléctricos, el tope aumenta a **$250,000.00 MXN**.
Recuerda que solo será deducible en la proporción en que el bien sea estrictamente indispensable para tu actividad."""

    if re.search(r'vi(a|á)ticos|alimentos|gastos.*viaje', pregunta):
        return """**Deducción de Viáticos y Gastos de Viaje (LISR Art. 28)**
Para que los gastos de viaje sean deducibles, deben destinarse a hospedaje, alimentación, transporte, uso o goce temporal de automóviles y pago de kilometraje, y aplicarse fuera de una faja de 50 kilómetros que circunde al establecimiento del contribuyente.
- **Alimentación en territorio nacional:** Hasta $750.00 MXN diarios por beneficiario.
- **Alimentación en el extranjero:** Hasta $1,500.00 MXN diarios por beneficiario.
Es obligatorio que se acompañen con el comprobante de transporte u hospedaje correspondiente."""

    if re.search(r'multa|recargo|declaraci(o|ó)n.*tarde|extempor(a|á)nea', pregunta):
        return """**Declaraciones Extemporáneas y Multas (CFF)**
Si presentas una declaración de forma extemporánea *de manera espontánea* (antes de que el SAT te envíe un requerimiento), **no hay multa**, solo deberás pagar la actualización y los recargos correspondientes sobre el impuesto omitido.
Si el SAT ya te requirió, la multa por cada obligación no declarada puede oscilar entre $1,810 y $22,400 MXN, dependiendo del caso."""

    if re.search(r'resico.*(f(i|í)sica|moral).*tasa|porcentaje.*resico', pregunta):
        return """**Tasas de ISR en RESICO (LISR)**
**Personas Físicas:**
La tasa aplicable depende de los ingresos mensuales cobrados:
- Hasta $25,000: 1.00%
- Hasta $50,000: 1.10%
- Hasta $83,333.33: 1.50%
- Hasta $208,333.33: 2.00%
- Hasta $2,833,333.33: 2.50%

**Personas Morales:**
Pagan una tasa fija del **30%** sobre la base del flujo de efectivo (Ingresos efectivamente cobrados menos Deducciones efectivamente pagadas)."""

    if re.search(r'fecha.*anual|cuando.*presentar.*anual', pregunta):
        return """**Fechas Límite para Declaración Anual**
- **Personas Morales:** A más tardar el **31 de marzo** del año siguiente al ejercicio que se declara.
- **Personas Físicas:** Durante el mes de **abril** del año siguiente al ejercicio que se declara.
*Nota: Si la fecha límite cae en día inhábil, se prorroga al siguiente día hábil.*"""

    return """🤖 Soy tu Asistente Fiscal AI. Por ahora en esta versión demo, estoy entrenado para responder rápidamente dudas comunes sobre:
- Topes de deducción de automóviles.
- Reglas de viáticos y gastos de viaje.
- Multas y declaraciones extemporáneas.
- Tasas de ISR en RESICO.
- Fechas de declaraciones anuales.

*Para respuestas a medida, en la versión de producción estaré conectado a ChatGPT entrenado con el CFF, LISR y LIVA actualizados.*"""
