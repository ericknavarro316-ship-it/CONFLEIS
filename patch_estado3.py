import re
import pandas as pd

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

search_kpi1 = """            if not obligaciones_df.empty:
                conteo_obs = obligaciones_df['estado'].value_counts().reset_index()
                conteo_obs.columns = ['Estado', 'Cantidad']
                # Asignar colores según estado
                color_map = {'Completada': '#198754', 'Pendiente': '#ffc107', 'Vencida': '#dc3545'}
                fig2 = px.pie(conteo_obs, values="Cantidad", names="Estado", hole=0.4,
                              color="Estado", color_discrete_map=color_map)
                st.plotly_chart(fig2, use_container_width=True)"""

replace_kpi1 = """            if not obligaciones_df.empty:
                df_dash = procesar_obligaciones_del_mes(obligaciones_df)
                def get_status(row):
                    if pd.notna(row['fecha_de_entrega']): return 'Completada'
                    if pd.notna(row.get('semaforo', '')) and 'Vencida' in str(row.get('semaforo', '')): return 'Vencida'
                    return 'Pendiente'
                df_dash['Estado'] = df_dash.apply(get_status, axis=1)
                conteo_obs = df_dash['Estado'].value_counts().reset_index()
                conteo_obs.columns = ['Estado', 'Cantidad']
                color_map = {'Completada': '#198754', 'Pendiente': '#ffc107', 'Vencida': '#dc3545'}
                fig2 = px.pie(conteo_obs, values="Cantidad", names="Estado", hole=0.4,
                              color="Estado", color_discrete_map=color_map)
                st.plotly_chart(fig2, use_container_width=True)"""

content = content.replace(search_kpi1, replace_kpi1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
