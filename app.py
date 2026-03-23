# ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~
#
# Author: Johandielangman
#
# ~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~


import streamlit as st

from utils.db import get_engine
from utils.model import Base
from utils.umami import load_umami

load_umami()


if "init" not in st.session_state:
    engine = get_engine()
    Base.metadata.create_all(engine)
    st.session_state.init = True


st.logo(
    "static/streamlit.png",
    icon_image="static/datatreehouse.circle.png",
    size="large",
    link="https://datatreehouse.org",
)


if not st.user.is_logged_in:
    with st.container(border=True):
        st.markdown("### Welcome to your Fuel Logbook! ⛽")
        st.markdown("To get the most out of this app, please log in with a Google account")
        if st.button("Log in with Google"):
            st.login("google")
    st.stop()

pages = [
    st.Page("home.py", title="Home", icon=":material/home:"),
    st.Page("stats.py", title="Statistics", icon=":material/analytics:"),
]
page = st.navigation(pages)
page.run()

if st.user.is_logged_in and st.sidebar.button("Log out"):
    st.logout()
st.sidebar.markdown("[![buy-us-a-coffee](./app/static/buy-us-a-coffee.png)](https://pos.snapscan.io/qr/Ew6rBAsV)")
