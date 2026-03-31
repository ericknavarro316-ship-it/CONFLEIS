import streamlit as st
import pandas as pd

if 'my_val' not in st.session_state:
    st.session_state.my_val = 'A'

opts = ['A', 'B', 'C']
idx = opts.index(st.session_state.my_val)

col1, col2 = st.columns(2)

with col1:
    sel = st.selectbox("Select", opts, index=idx)
    if sel != st.session_state.my_val:
        st.session_state.my_val = sel
        st.rerun()
    st.write("Current val:", st.session_state.my_val)
    if st.button("Reset"):
        st.session_state.my_val = 'A'
        st.rerun()

with col2:
    df = pd.DataFrame({'val': ['A', 'B', 'C']})
    event = st.dataframe(df, on_select="rerun", selection_mode="single-row")
    if event and len(event.selection.rows) > 0:
        row_idx = event.selection.rows[0]
        val_sel = df.iloc[row_idx]['val']
        if st.session_state.my_val != val_sel:
            st.session_state.my_val = val_sel
            st.rerun()
