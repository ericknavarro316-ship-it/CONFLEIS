import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

search = """            from datetime import date, timedelta
            import calendar
            hoy = date.today()
            mes_actual = hoy.month
            anio_actual = hoy.year

            fechas_limite = []"""

replace = """            from datetime import date, timedelta
            import calendar
            hoy = date.today()

            col_mes, col_anio = st.columns(2)
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

            with col_mes:
                mes_seleccionado_nombre = st.selectbox("Mes a visualizar:", meses_nombres, index=hoy.month - 1)
                mes_actual = meses_nombres.index(mes_seleccionado_nombre) + 1
            with col_anio:
                anio_actual = st.selectbox("Año a visualizar:", range(hoy.year - 1, hoy.year + 3), index=1)

            fechas_limite = []"""

content = content.replace(search, replace)

search2 = """            else:
                st.info("Mostrando las próximas 10 tareas pendientes.")
                df_mostrar = df_mostrar[pd.isna(df_mostrar['fecha_de_entrega'])].sort_values('fecha_limite').head(10)"""

replace2 = """            else:
                st.info(f"Mostrando tareas pendientes para {mes_seleccionado_nombre} {anio_actual}.")
                df_mostrar = df_mostrar[pd.isna(df_mostrar['fecha_de_entrega'])].sort_values('fecha_limite')"""

content = content.replace(search2, replace2)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
