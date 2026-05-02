import streamlit as st

from constants import settings as s


def top_logo():
    st.logo(
        s.logo_banner_path,
        icon_image=s.logo_circle_path,
        size="large",
        link=s.datatreehouse_url,
    )
