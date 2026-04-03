import streamlit as st
from streamlit_calendar import calendar

calendar_options = {
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth"
    },
    "initialView": "dayGridMonth"
}

st_calendar_dict = calendar(events=[], options=calendar_options)
st.write(st_calendar_dict)
