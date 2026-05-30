import streamlit as st

from constants import settings as s


def buy_us_a_coffee():
    with st.sidebar:
        st.divider()
        st.markdown(
            f"[![buy-us-a-coffee](./app/{s.buy_us_a_coffee_path})]({s.snapscan_url})",
            width=350,
        )
