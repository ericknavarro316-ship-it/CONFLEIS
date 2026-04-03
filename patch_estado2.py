import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

search_kpi1 = """            if not obligaciones_df.empty:
                conteo_obs = obligaciones_df['estado'].value_counts().reset_index()
                conteo_obs.columns = ['Estado', 'Total']
                # Asignar colores según estado
                color_discrete_map = {'Pendiente': 'red', 'Completada': 'green'}
                fig_obs = px.pie(conteo_obs, values='Total', names='Estado', title="Estado de Obligaciones", color='Estado', color_discrete_map=color_discrete_map)
                st.plotly_chart(fig_obs, use_container_width=True)"""

replace_kpi1 = """            if not obligaciones_df.empty:
                df_dash = procesar_obligaciones_del_mes(obligaciones_df)
                df_dash['Estado'] = df_dash['fecha_de_entrega'].apply(lambda x: 'Pendiente' if pd.isna(x) else 'Completada')
                conteo_obs = df_dash['Estado'].value_counts().reset_index()
                conteo_obs.columns = ['Estado', 'Total']
                color_discrete_map = {'Pendiente': 'red', 'Completada': 'green'}
                fig_obs = px.pie(conteo_obs, values='Total', names='Estado', title="Estado de Obligaciones", color='Estado', color_discrete_map=color_discrete_map)
                st.plotly_chart(fig_obs, use_container_width=True)"""

content = content.replace(search_kpi1, replace_kpi1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
