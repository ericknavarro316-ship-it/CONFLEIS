import re
import pandas as pd

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix line 564 (conteo_obs): previously used 'estado' directly from obligaciones_df.
# We now need to process it and use the computed semaforo or pd.isna(fecha_de_entrega)
search_kpi1 = """            if not obligaciones_df.empty:
                conteo_obs = obligaciones_df['estado'].value_counts().reset_index()
                conteo_obs.columns = ['Estado', 'Total']
                # Asignar colores según estado
                color_discrete_map = {'Pendiente': 'red', 'Completada': 'green'}
                fig_obs = px.pie(conteo_obs, values='Total', names='Estado', title="Estado de Obligaciones", color='Estado', color_discrete_map=color_discrete_map)"""

replace_kpi1 = """            if not obligaciones_df.empty:
                df_dash = procesar_obligaciones_del_mes(obligaciones_df)
                df_dash['Estado'] = df_dash['fecha_de_entrega'].apply(lambda x: 'Pendiente' if pd.isna(x) else 'Completada')
                conteo_obs = df_dash['Estado'].value_counts().reset_index()
                conteo_obs.columns = ['Estado', 'Total']
                color_discrete_map = {'Pendiente': 'red', 'Completada': 'green'}
                fig_obs = px.pie(conteo_obs, values='Total', names='Estado', title="Estado de Obligaciones", color='Estado', color_discrete_map=color_discrete_map)"""

content = content.replace(search_kpi1, replace_kpi1)

# 2. Fix line 602 (pendientes = ...)
search_kpi2 = """    pendientes = len(obligaciones_df[obligaciones_df['estado'] == 'Pendiente']) if not obligaciones_df.empty else 0"""
replace_kpi2 = """    if not obligaciones_df.empty:
        df_pend = procesar_obligaciones_del_mes(obligaciones_df)
        pendientes = len(df_pend[pd.isna(df_pend['fecha_de_entrega'])])
    else:
        pendientes = 0"""

content = content.replace(search_kpi2, replace_kpi2)

# 3. Fix line 657 (alertas = ob_semaforo[estado == pendiente])
search_alert = """        alertas = ob_semaforo[(ob_semaforo['estado'] == 'Pendiente') &
                              (ob_semaforo['semaforo'].str.startswith('🔴') | ob_semaforo['semaforo'].str.startswith('🟠'))]"""
replace_alert = """        alertas = ob_semaforo[(pd.isna(ob_semaforo['fecha_de_entrega'])) &
                              (ob_semaforo['semaforo'].str.startswith('🔴') | ob_semaforo['semaforo'].str.startswith('🟠') | ob_semaforo['semaforo'].str.startswith('🟡'))]"""

content = content.replace(search_alert, replace_alert)

# 4. Fix line 663 (subset=['semaforo', 'estado'])
search_subset1 = """                alertas.style.map(estilo_semaforo, subset=['semaforo', 'estado']),"""
replace_subset1 = """                alertas.style.map(estilo_semaforo, subset=['semaforo']),"""
content = content.replace(search_subset1, replace_subset1)

# 5. Fix line 726 (subset=['semaforo', 'estado'])
search_subset2 = """                 ob_semaforo.style.map(estilo_semaforo, subset=['semaforo', 'estado']),"""
replace_subset2 = """                 ob_semaforo.style.map(estilo_semaforo, subset=['semaforo']),"""
content = content.replace(search_subset2, replace_subset2)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
