import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

search_ui = """            if st.form_submit_button("Guardar Colores"):
                db.actualizar_configuracion(conf.get('logo'), color1, color2, color3)
                st.success("Colores guardados. Actualiza la página para ver los cambios.")"""

replace_ui = search_ui + """

    st.write("---")
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
"""

content = content.replace(search_ui, replace_ui)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
