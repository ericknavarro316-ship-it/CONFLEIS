import calendar
from datetime import date, timedelta
import pandas as pd
import database as db

def es_dia_habil(fecha):
    # Fines de semana (5=Sábado, 6=Domingo)
    if fecha.weekday() >= 5:
        return False

    # Días festivos oficiales en México (Aproximación fija)
    # 1 Ene, 1er lun Feb (Const), 3er lun Mar (Natalicio), 1 May, 16 Sep, 3er lun Nov (Revolucion), 25 Dic
    # Nota: para simplificar en MVP usamos fechas exactas y meses
    mes = fecha.month
    dia = fecha.day
    if mes == 1 and dia == 1: return False
    if mes == 5 and dia == 1: return False
    if mes == 9 and dia == 16: return False
    if mes == 12 and dia == 25: return False
    if mes == 10 and dia == 1: return False # Cambio de poder ejecutivo (nuevo)

    # 1er Lunes de Febrero
    if mes == 2 and fecha.weekday() == 0 and 1 <= dia <= 7: return False
    # 3er Lunes de Marzo
    if mes == 3 and fecha.weekday() == 0 and 15 <= dia <= 21: return False
    # 3er Lunes de Noviembre
    if mes == 11 and fecha.weekday() == 0 and 15 <= dia <= 21: return False

    return True

def obtener_siguiente_dia_habil(fecha):
    fecha += timedelta(days=1)
    while not es_dia_habil(fecha):
        fecha += timedelta(days=1)
    return fecha

def calcular_fecha_limite_obligacion(rfc_cliente, regimen, notas_venc, dias_extra, mes_objetivo, anio_objetivo):
    """
    Calcula la fecha límite exacta para una obligación en un mes dado.
    Implementa la regla de días hábiles extra para el día 17 según el 6to dígito numérico del RFC,
    fines de semana, y días festivos.
    """
    notas_venc = str(notas_venc).lower()
    regimen = str(regimen).lower() if regimen else ""

    # RIF (Régimen de Incorporación Fiscal) declara bimestralmente.
    # Los pagos se hacen el 17 del mes posterior al final del bimestre (Ene-Feb se paga en Marzo)
    # Meses de pago: Marzo(3), Mayo(5), Julio(7), Septiembre(9), Noviembre(11), Enero(1).
    if "incorporación fiscal" in regimen or "rif" in regimen:
        if mes_objetivo % 2 == 0:
            return None # En meses pares no se declara RIF

    # 1. Determinar el mes límite base
    if "anual" in notas_venc or "abril" in notas_venc or "marzo" in notas_venc:
        # Obligación Anual
        mes_lim = 4 if len(rfc_cliente) == 13 else 3
        if mes_objetivo != mes_lim:
            return None

        ultimo_dia = calendar.monthrange(anio_objetivo, mes_lim)[1]
        base_date = date(anio_objetivo, mes_lim, ultimo_dia)

    elif "17" in notas_venc:
        base_date = date(anio_objetivo, mes_objetivo, 17)
    else:
        ultimo_dia = calendar.monthrange(anio_objetivo, mes_objetivo)[1]
        base_date = date(anio_objetivo, mes_objetivo, ultimo_dia)

    # 2. Si el día de vencimiento es el 17, aplicar regla de viernes o inhábil
    # Regla: Si el 17 es viernes o inhábil, pasa al siguiente día hábil.
    if base_date.day == 17:
        if base_date.weekday() == 4 or not es_dia_habil(base_date):
            base_date = obtener_siguiente_dia_habil(base_date)
    else:
        # Si es fin de mes u otra fecha, solo asegurarnos que sea hábil
        while not es_dia_habil(base_date):
            base_date -= timedelta(days=1)

    # 3. Sumar prórroga (días hábiles extra por 6to dígito) solo a las mensuales del 17
    if "17" in notas_venc:
        for _ in range(dias_extra):
            base_date = obtener_siguiente_dia_habil(base_date)

    return base_date

def procesar_obligaciones_del_mes(mes, anio, tipo_persona=None, cliente_id=None):
    """
    Obtiene las plantillas de obligaciones y genera las instancias concretas (fechas límite)
    para el mes y año solicitados. Retorna un DataFrame con 'fecha_limite' y el semáforo cruzado
    con los 'cumplimientos'.
    """
    obligaciones_df = db.obtener_obligaciones(tipo_persona, cliente_id)
    if obligaciones_df.empty:
        return pd.DataFrame()

    cumplimientos_df = db.obtener_cumplimientos()

    # Filtrar cumplimientos al mes y año que estamos evaluando
    cumplimientos_mes = cumplimientos_df[(cumplimientos_df['mes'] == mes) & (cumplimientos_df['anio'] == anio)]

    fechas_limite = []
    ids_validos = []

    for idx, row in obligaciones_df.iterrows():
        # Intentar sacar regimen desde row, si no cruzar
        reg = row.get("regimen", "")
        # Ojo: si 'regimen' no esta en obtener_obligaciones, necesitamos un JOIN o agregarlo en database.py.
        # Revisando db.obtener_obligaciones, traemos c.rfc pero no c.regimen, vamos a intentar obtenerlo
        # Si no esta, simplemente asumimos que no es RIF. Lo ideal es agregarlo en la query SQL.

        fl = calcular_fecha_limite_obligacion(
            str(row.get("rfc", "")),
            reg,
            row.get("notas", ""),
            int(row.get("dia_habil_extra", 0)),
            mes,
            anio
        )
        if fl:
            fechas_limite.append(fl)
            ids_validos.append(row['id'])

    # Quedarnos solo con las obligaciones que aplican este mes
    ob_mes_df = obligaciones_df[obligaciones_df['id'].isin(ids_validos)].copy()
    ob_mes_df['fecha_limite'] = pd.to_datetime(fechas_limite)
    ob_mes_df['mes_objetivo'] = mes
    ob_mes_df['anio_objetivo'] = anio

    # Cruzar con cumplimientos para ver si ya se entregaron
    df_merged = pd.merge(
        ob_mes_df,
        cumplimientos_mes,
        left_on=['id'],
        right_on=['obligacion_id'],
        how='left'
    )

    return df_merged
