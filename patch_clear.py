import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the button behavior. The problem is that st_calendar dictates state.
# st.rerun() won't clear the component unless we force it to remount by changing its key.
# A simple way to force component reset in Streamlit is to append a counter to the key and increment it.

# Let's add a session state variable for the calendar key suffix
setup_state = """
import os
import calendar
from PIL import Image

if 'cal_key_suffix' not in st.session_state:
    st.session_state['cal_key_suffix'] = 0
"""

content = content.replace("import os\nimport calendar", setup_state)

search_cal_key = """            calendar_dict = st_calendar(events=events, options=calendar_options, key="general_calendar")"""
replace_cal_key = """            calendar_dict = st_calendar(events=events, options=calendar_options, key=f"general_calendar_{st.session_state['cal_key_suffix']}")"""

content = content.replace(search_cal_key, replace_cal_key)

search_rerun1 = """                if col_btn.button("Ver todo el mes", use_container_width=True):
                    st.rerun()"""
replace_rerun1 = """                if col_btn.button("Ver todo el mes", use_container_width=True, key="btn_clear_1"):
                    st.session_state['cal_key_suffix'] += 1
                    st.rerun()"""

search_rerun2 = """                if col_btn.button("Ver todo el mes", use_container_width=True):
                    st.rerun()"""
replace_rerun2 = """                if col_btn.button("Ver todo el mes", use_container_width=True, key="btn_clear_2"):
                    st.session_state['cal_key_suffix'] += 1
                    st.rerun()"""

# Replace first occurrence
content = content.replace(search_rerun1, replace_rerun1, 1)
# Replace second occurrence
content = content.replace(search_rerun2, replace_rerun2, 1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
