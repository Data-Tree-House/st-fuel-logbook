import streamlit as st

from constants import settings
from utils import primary_text


def metrics():
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                f"{primary_text('Entries')}",
                value=0,
            )
            st.metric(
                f"{primary_text('Total km')}",
                value=0,
            )
        with col2:
            st.metric(
                f"{primary_text('Total Fuel Usage')}",
                value=0,
                format="%.0f",
            )
            st.metric(
                f"{primary_text('Total Expense')}",
                value=0,
                format="%.0f",
            )


def profile():
    with st.sidebar:
        try:
            profile_picture = st.session_state.user.picture or settings.default_picture
        except Exception:
            profile_picture = settings.default_picture

        col1, col2 = st.columns([0.4, 0.6])
        with col1:
            st.image(
                f"{profile_picture}",
                width="content",
            )
        with col2:
            st.markdown(f"{st.user.name}")
            st.markdown(f"{st.user.email}")

        metrics()
