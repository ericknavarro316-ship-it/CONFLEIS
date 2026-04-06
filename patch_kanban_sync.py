import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

search = """                    if i < len(columnas) - 1:
                        if st.button("➡️", key=f"R_{row['id']}"):
                            db.mover_tarea_kanban(row['id'], columnas[i+1])
                            st.rerun()"""

replace = """                    if i < len(columnas) - 1:
                        if st.button("➡️", key=f"R_{row['id']}"):
                            db.mover_tarea_kanban(row['id'], columnas[i+1])

                            # Integración Kanban -> Calendario (Auto Completar)
                            if columnas[i+1] == "Finalizada":
                                import pandas as pd
                                if 'obligacion_id' in row and pd.notna(row['obligacion_id']):
                                    from datetime import date
                                    o_id = int(row['obligacion_id'])
                                    m_obj = int(row['mes_objetivo'])
                                    a_obj = int(row['anio_objetivo'])
                                    hoy_str = date.today().strftime('%Y-%m-%d')
                                    # Evitar duplicados si ya está completada
                                    cumps = db.obtener_cumplimientos()
                                    ya_completada = False
                                    if not cumps.empty:
                                        match = cumps[(cumps['obligacion_id'] == o_id) & (cumps['mes'] == m_obj) & (cumps['anio'] == a_obj)]
                                        if not match.empty: ya_completada = True

                                    if not ya_completada:
                                        db.registrar_cumplimiento(o_id, m_obj, a_obj, hoy_str)

                            st.rerun()"""

content = content.replace(search, replace)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
