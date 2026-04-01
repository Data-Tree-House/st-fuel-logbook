import streamlit as st

from utils.graphs import st_plot_fuel_litres_over_time

st.set_page_config(
    page_title="Fuel Statistics",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st_plot_fuel_litres_over_time()
