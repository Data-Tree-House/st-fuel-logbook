# ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~
#
# Author: Johandielangman
#
# ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~


import streamlit as st
from loguru import logger

import components as c
import utils as u

# =============== // INITIALIZE APPLICATION // ===============

st.set_page_config(
    page_title="Fuel Logbook",
    layout="centered",
    initial_sidebar_state="collapsed",
)
u.load_umami()

if "init" not in st.session_state:
    logger.info("Initializing new session session")
    engine = u.get_engine()
    u.model.Base.metadata.create_all(engine)
    st.session_state.init = True


# =============== // REDIRECT TO AUTH // ===============

if not st.user.is_logged_in:
    c.login()

# =============== // PAGE NAVIGATION // ===============

pages = [
    st.Page(
        "home.py",
        title="Home",
        icon=":material/home:",
    ),
    st.Page(
        "stats.py",
        title="Statistics",
        icon=":material/analytics:",
    ),
]
page = st.navigation(pages)
page.run()

# =============== // SIDEBAR AND LOGOUT // ===============

c.top_logo()
c.profile()
if st.user.is_logged_in:
    c.logout()
c.buy_us_a_coffee()
