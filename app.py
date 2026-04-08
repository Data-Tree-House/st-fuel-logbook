# ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~
#
# Author: Johandielangman
#
# ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~


import streamlit as st
from loguru import logger

import components as c
import utils as u
from constants import settings
from db import crud, get_engine

# TODO: add sigterm handlers

# =============== // INITIALIZE APPLICATION // ===============

st.set_page_config(
    page_title="Fuel Logbook",
    layout="centered",
    initial_sidebar_state="collapsed",
    page_icon=settings.favicon,
)
u.load_umami()

if "init" not in st.session_state:
    logger.info("Initializing new session session")
    crud.create_all_tables(engine=get_engine())
    st.session_state.init = True


# =============== // REDIRECT TO AUTH // ===============

if not st.user.is_logged_in:
    c.login()

# =============== // PAGE NAVIGATION // ===============

pages = {
    "": [
        st.Page(
            "home.py",
            title="Fuel Entry",
            icon=":material/local_gas_station:",
        ),
        st.Page(
            "stats.py",
            title="Statistics",
            icon=":material/analytics:",
        ),
    ],
    "Manage": [
        st.Page(
            "new_car.py",
            title="New Car",
            icon=":material/directions_car:",
        ),
        st.Page(
            "bulk.py",
            title="Bulk Upload",
            icon=":material/upload_file:",
        ),
    ],
}
page = st.navigation(pages)
page.run()

# =============== // SIDEBAR AND LOGOUT // ===============

c.top_logo()
c.profile()
if st.user.is_logged_in:
    c.logout()
c.buy_us_a_coffee()
