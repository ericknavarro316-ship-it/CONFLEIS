import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

df = pd.DataFrame({'nombre': ['A', 'B'], 'rol': ['Admin', 'User']})

gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_selection('single')
go = gb.build()

grid = AgGrid(df, gridOptions=go, update_mode='selection_changed')

st.write("Type of selected_rows:", type(grid['selected_rows']))
st.write("Value:", grid['selected_rows'])
if grid['selected_rows'] is not None and len(grid['selected_rows']) > 0:
    st.write(grid['selected_rows'])

