import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the dashboard call
search1 = """    if not obligaciones_df.empty:
        ob_semaforo = calcular_semaforo(obligaciones_df)"""
replace1 = """    if not obligaciones_df.empty:
        obligaciones_df = procesar_obligaciones_del_mes(obligaciones_df)
        ob_semaforo = calcular_semaforo(obligaciones_df)"""
content = content.replace(search1, replace1)

# Fix the Personas Físicas/Morales call
search2 = """        obligaciones_df = db.obtener_obligaciones(tipo_persona)
        if not obligaciones_df.empty:
             ob_semaforo = calcular_semaforo(obligaciones_df)"""
replace2 = """        obligaciones_df = db.obtener_obligaciones(tipo_persona)
        if not obligaciones_df.empty:
             obligaciones_df = procesar_obligaciones_del_mes(obligaciones_df)
             ob_semaforo = calcular_semaforo(obligaciones_df)"""
content = content.replace(search2, replace2)

# Fix the Calendario General call to use the new function
# Let's replace the whole block in Calendario General
search3_start = "            hoy = date.today()"
search3_end = "            ob_semaforo = calcular_semaforo(df_merged)"

import sys

try:
    idx_start = content.index(search3_start)
    idx_end = content.index(search3_end) + len(search3_end)
    block = content[idx_start:idx_end]

    replace3 = """            hoy = date.today()

            # Cargar días festivos desde BD
            df_festivos = db.obtener_dias_festivos()
            festivos_lista = df_festivos['fecha'].tolist() if not df_festivos.empty else []

            col_mes, col_anio = st.columns(2)
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

            with col_mes:
                mes_seleccionado_nombre = st.selectbox("Mes a visualizar:", meses_nombres, index=hoy.month - 1)
                mes_actual = meses_nombres.index(mes_seleccionado_nombre) + 1
            with col_anio:
                anio_actual = st.selectbox("Año a visualizar:", range(hoy.year - 1, hoy.year + 3), index=1)

            df_merged = procesar_obligaciones_del_mes(obligaciones_df, mes_objetivo=mes_actual, anio_objetivo=anio_actual)
            ob_semaforo = calcular_semaforo(df_merged)"""

    content = content.replace(block, replace3)
except ValueError:
    pass

# Fix Mi Portal call
search4_start = "             fechas_limite = []"
search4_end = "             ob_semaforo = calcular_semaforo(mis_obligaciones)"

try:
    idx_start4 = content.index(search4_start)
    idx_end4 = content.index(search4_end) + len(search4_end)
    block4 = content[idx_start4:idx_end4]

    replace4 = """             mis_obligaciones = procesar_obligaciones_del_mes(mis_obligaciones)
             ob_semaforo = calcular_semaforo(mis_obligaciones)"""

    content = content.replace(block4, replace4)
except ValueError:
    pass

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
