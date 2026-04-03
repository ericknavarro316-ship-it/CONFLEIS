import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

search = """            if calendar_dict.get("dateClick"):
                filtro_fecha = calendar_dict["dateClick"]["date"].split("T")[0]
                st.info(f"Mostrando actividades para la fecha: {filtro_fecha}")
                df_mostrar = df_mostrar[df_mostrar['fecha_limite'].dt.strftime('%Y-%m-%d') == filtro_fecha]
            elif calendar_dict.get("eventClick"):
                evento = calendar_dict["eventClick"]["event"]["extendedProps"]
                filtro_fecha = evento["fecha_limite"]
                st.info(f"Mostrando actividades para la fecha: {filtro_fecha}")
                df_mostrar = df_mostrar[df_mostrar['fecha_limite'].dt.strftime('%Y-%m-%d') == filtro_fecha]
            else:
                st.info(f"Mostrando tareas pendientes para {mes_seleccionado_nombre} {anio_actual}.")
                df_mostrar = df_mostrar[pd.isna(df_mostrar['fecha_de_entrega'])].sort_values('fecha_limite')"""

replace = """            if calendar_dict.get("dateClick"):
                filtro_fecha = calendar_dict["dateClick"]["date"].split("T")[0]
                col_info, col_btn = st.columns([3, 1])
                col_info.info(f"Mostrando actividades para la fecha: {filtro_fecha}")
                if col_btn.button("Ver todo el mes", use_container_width=True):
                    st.rerun()
                df_mostrar = df_mostrar[df_mostrar['fecha_limite'].dt.strftime('%Y-%m-%d') == filtro_fecha]
            elif calendar_dict.get("eventClick"):
                evento = calendar_dict["eventClick"]["event"]["extendedProps"]
                filtro_fecha = evento["fecha_limite"]
                col_info, col_btn = st.columns([3, 1])
                col_info.info(f"Mostrando actividades para la fecha: {filtro_fecha}")
                if col_btn.button("Ver todo el mes", use_container_width=True):
                    st.rerun()
                df_mostrar = df_mostrar[df_mostrar['fecha_limite'].dt.strftime('%Y-%m-%d') == filtro_fecha]
            else:
                st.info(f"Mostrando tareas pendientes para {mes_seleccionado_nombre} {anio_actual}.")
                df_mostrar = df_mostrar[pd.isna(df_mostrar['fecha_de_entrega'])].sort_values('fecha_limite')"""

content = content.replace(search, replace)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
