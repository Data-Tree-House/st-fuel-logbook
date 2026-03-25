import streamlit as st

from utils import google_text, primary_text, st_plot_fuel_efficiency


def login():
    with st.container(border=True, horizontal_alignment="center"):
        st.markdown(f"### Welcome to your {primary_text('Fuel Logbook')}", text_alignment="center")

        st.markdown("##### Wanna see what your fuel usage looks like?", text_alignment="center")
        st.markdown("Then sign in to your account to find out!", text_alignment="center")

        st_plot_fuel_efficiency()

        if st.button(f"Sign in with {google_text()}"):
            st.login("google")
    st.stop()


def logout():
    if st.sidebar.button("Log out"):
        st.logout()
