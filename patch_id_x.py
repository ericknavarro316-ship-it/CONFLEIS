import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# In procesar_obligaciones_del_mes, ensure we always output a column named 'id_x' for the obligation ID
# to maintain compatibility with the UI.

search_func = """    # Cruzar con cumplimientos
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
        return df_out"""

replace_func = """    # Cruzar con cumplimientos
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
        df_out['id_x'] = df_out['id']
        return df_out"""

content = content.replace(search_func, replace_func)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
