import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

search = """            hoy = date.today()

            col_mes, col_anio = st.columns(2)"""

replace = """            hoy = date.today()

            # Cargar días festivos desde BD
            df_festivos = db.obtener_dias_festivos()
            festivos_lista = df_festivos['fecha'].tolist() if not df_festivos.empty else []

            col_mes, col_anio = st.columns(2)"""

content = content.replace(search, replace)

search_calc = """                while base_date.weekday() >= 5:
                    base_date += timedelta(days=1)

                for _ in range(dias_extra):
                    base_date += timedelta(days=1)
                    while base_date.weekday() >= 5:
                        base_date += timedelta(days=1)"""

replace_calc = """                while base_date.weekday() >= 5 or base_date.strftime('%Y-%m-%d') in festivos_lista:
                    base_date += timedelta(days=1)

                for _ in range(dias_extra):
                    base_date += timedelta(days=1)
                    while base_date.weekday() >= 5 or base_date.strftime('%Y-%m-%d') in festivos_lista:
                        base_date += timedelta(days=1)"""

content = content.replace(search_calc, replace_calc)

search_ui = """    with col2:
        st.subheader("2. Colores")"""

replace_ui = """    with col2:
        st.subheader("2. Colores")"""

# wait, I need to add the UI configuration for holidays to "Configuración de Marca"
search_ui = """    st.write("---")
    st.subheader("Vista Previa del Dashboard")"""

replace_ui = """    st.write("---")
    st.subheader("🏖️ Configuración de Días Festivos")
    st.write("Agrega los días que tu despacho no labora. El sistema los saltará automáticamente al calcular los vencimientos fiscales.")

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        with st.form("form_festivo"):
            f_fecha = st.date_input("Fecha inhábil")
            f_desc = st.text_input("Motivo (ej. Viernes Santo)")
            if st.form_submit_button("Agregar Día Inhábil"):
                if f_desc:
                    db.agregar_dia_festivo(f_fecha.strftime('%Y-%m-%d'), f_desc)
                    st.success("Día inhábil guardado.")
                    st.rerun()
                else:
                    st.error("Ingresa un motivo.")

    with col_f2:
        df_festivos = db.obtener_dias_festivos()
        if not df_festivos.empty:
            st.dataframe(df_festivos[['fecha', 'descripcion']], hide_index=True)
            with st.expander("Eliminar un día festivo"):
                op_elim = dict(zip(df_festivos['fecha'] + " - " + df_festivos['descripcion'], df_festivos['id']))
                f_elim = st.selectbox("Selecciona:", list(op_elim.keys()))
                if st.button("Eliminar"):
                    db.eliminar_dia_festivo(op_elim[f_elim])
                    st.rerun()
        else:
            st.info("No hay días festivos registrados.")

    st.write("---")
    st.subheader("Vista Previa del Dashboard")"""

content = content.replace(search_ui, replace_ui)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
