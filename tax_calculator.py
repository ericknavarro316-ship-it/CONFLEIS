import pandas as pd

def calcular_isr_resico_fisicas(ingresos_mensuales):
    """
    Calcula el ISR mensual para Personas Físicas en RESICO.
    Tarifas 2023/2024:
    Hasta 25,000 -> 1.00%
    Hasta 50,000 -> 1.10%
    Hasta 83,333.33 -> 1.50%
    Hasta 208,333.33 -> 2.00%
    Hasta 2,833,333.33 -> 2.50%
    """
    if ingresos_mensuales <= 25000:
        tasa = 0.01
    elif ingresos_mensuales <= 50000:
        tasa = 0.011
    elif ingresos_mensuales <= 83333.33:
        tasa = 0.015
    elif ingresos_mensuales <= 208333.33:
        tasa = 0.02
    else:
        tasa = 0.025
        
    isr_determinado = ingresos_mensuales * tasa
    return isr_determinado, tasa

def calcular_isr_actividad_empresarial_simplificado(ingresos, deducciones):
    """
    Calculo simplificado ilustrativo (Base de efectivo).
    Asume 30% de utilidad fiscal teórica sobre la diferencia,
    o utiliza la tarifa mensual del art 96 (Simplificado al 30% para este MVP).
    """
    utilidad = ingresos - deducciones
    if utilidad <= 0:
        return 0.0, 0.0
    
    # Tarifa plana simplificada para este prototipo (30%)
    tasa = 0.30
    isr_determinado = utilidad * tasa
    return isr_determinado, tasa

def calcular_impuestos(resumen_facturas, regimen, tipo_persona):
    """
    Toma el resumen mensual de XMLs procesados y calcula los impuestos:
    - IVA: (IVA Cobrado) - (IVA Pagado) - (IVA Retenido)
    - ISR: Según Régimen (RESICO o Actividad Empresarial)
    """
    ingresos = resumen_facturas.get("Total_Ingresos_PUE", 0)
    gastos = resumen_facturas.get("Total_Gastos_PUE", 0)
    
    iva_cobrado = resumen_facturas.get("IVA_Cobrado", 0)
    iva_pagado = resumen_facturas.get("IVA_Pagado", 0)
    
    isr_retenido = resumen_facturas.get("ISR_Retenido_Cobrado", 0)
    iva_retenido = resumen_facturas.get("IVA_Retenido_Cobrado", 0)
    
    # --- CÁLCULO DE IVA ---
    iva_a_cargo = iva_cobrado - iva_pagado - iva_retenido
    if iva_a_cargo < 0:
         iva_resultado = {"A Pagar": 0.0, "A Favor": abs(iva_a_cargo)}
    else:
         iva_resultado = {"A Pagar": iva_a_cargo, "A Favor": 0.0}
         
    # --- CÁLCULO DE ISR ---
    isr_a_pagar = 0.0
    tasa_aplicada = 0.0
    
    if "RESICO" in regimen and tipo_persona == "Física":
         isr_determinado, tasa_aplicada = calcular_isr_resico_fisicas(ingresos)
         isr_a_pagar = isr_determinado - isr_retenido
    elif "RESICO" in regimen and tipo_persona == "Moral":
         # RESICO Moral es sobre flujo, utilidad * 30%
         utilidad = ingresos - gastos
         if utilidad > 0:
             isr_determinado = utilidad * 0.30
         else:
             isr_determinado = 0.0
         tasa_aplicada = 0.30
         isr_a_pagar = isr_determinado - isr_retenido
    else:
         # Actividad Empresarial (Simplificado MVP)
         isr_determinado, tasa_aplicada = calcular_isr_actividad_empresarial_simplificado(ingresos, gastos)
         isr_a_pagar = isr_determinado - isr_retenido
         
    # Evitar pagar ISR negativo (es a favor)
    isr_a_favor = 0.0
    if isr_a_pagar < 0:
         isr_a_favor = abs(isr_a_pagar)
         isr_a_pagar = 0.0
         
    resultados = {
        "Ingresos_Totales": round(ingresos, 2),
        "Gastos_Totales": round(gastos, 2),
        "Utilidad_Fiscal_Base": round(ingresos - gastos, 2),
        "IVA_Cobrado": round(iva_cobrado, 2),
        "IVA_Pagado": round(iva_pagado, 2),
        "IVA_Retenido": round(iva_retenido, 2),
        "IVA_A_Pagar": round(iva_resultado["A Pagar"], 2),
        "IVA_A_Favor": round(iva_resultado["A Favor"], 2),
        "ISR_Determinado": round(isr_determinado, 2),
        "Tasa_ISR_Aplicada": f"{tasa_aplicada * 100}%",
        "ISR_Retenido": round(isr_retenido, 2),
        "ISR_A_Pagar": round(isr_a_pagar, 2),
        "ISR_A_Favor": round(isr_a_favor, 2),
        "Total_Impuestos_A_Pagar": round(iva_resultado["A Pagar"] + isr_a_pagar, 2)
    }
    
    return resultados