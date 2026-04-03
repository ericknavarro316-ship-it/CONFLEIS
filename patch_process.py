import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. We will extract the date generation logic into a new helper function `procesar_obligaciones_del_mes`
# that we'll add right above `calcular_semaforo`.
new_func = """
def procesar_obligaciones_del_mes(df_obligaciones, mes_objetivo=None, anio_objetivo=None):
    if df_obligaciones.empty:
        return df_obligaciones

    from datetime import date, timedelta
    import calendar
    import pandas as pd

    hoy = date.today()
    m = mes_objetivo if mes_objetivo else hoy.month
    y = anio_objetivo if anio_objetivo else hoy.year

    # Cargar días festivos desde BD para el cálculo
    import database as db
    df_festivos = db.obtener_dias_festivos()
    festivos_lista = df_festivos['fecha'].tolist() if not df_festivos.empty else []

    fechas_limite = []
    para_mes = []
    para_anio = []

    for _, row in df_obligaciones.iterrows():
        notas_venc = row.get("notas", "")
        if not isinstance(notas_venc, str):
            notas_venc = ""

        rfc_cliente = str(row.get("rfc", ""))
        dias_extra = int(row.get("dia_habil_extra", 0))

        if "17" in notas_venc:
            base_date = date(y, m, 17)
        elif "anual" in notas_venc.lower() or "abril" in notas_venc.lower() or "marzo" in notas_venc.lower():
            mes_lim = 4 if len(rfc_cliente) == 13 else 3
            base_date = date(y, mes_lim, 30 if mes_lim == 4 else 31)
        else:
            ultimo_dia = calendar.monthrange(y, m)[1]
            base_date = date(y, m, ultimo_dia)

        while base_date.weekday() >= 5 or base_date.strftime('%Y-%m-%d') in festivos_lista:
            base_date += timedelta(days=1)

        for _ in range(dias_extra):
            base_date += timedelta(days=1)
            while base_date.weekday() >= 5 or base_date.strftime('%Y-%m-%d') in festivos_lista:
                base_date += timedelta(days=1)

        fechas_limite.append(base_date)
        para_mes.append(m)
        para_anio.append(y)

    df_out = df_obligaciones.copy()
    df_out['fecha_limite'] = pd.to_datetime(fechas_limite)
    df_out['mes_objetivo'] = para_mes
    df_out['anio_objetivo'] = para_anio

    # Cruzar con cumplimientos
    cumplimientos_df = db.obtener_cumplimientos()
    if not cumplimientos_df.empty:
        df_merged = pd.merge(
            df_out,
            cumplimientos_df,
            left_on=['id', 'mes_objetivo', 'anio_objetivo'],
            right_on=['obligacion_id', 'mes', 'anio'],
            how='left'
        )
        return df_merged
    else:
        df_out['fecha_de_entrega'] = pd.NA
        return df_out

def calcular_semaforo(df):"""

content = content.replace("def calcular_semaforo(df):", new_func)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
