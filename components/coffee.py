import streamlit as st


def buy_us_a_coffee():
    with st.sidebar:
        st.divider()
        st.markdown(
            "[![buy-us-a-coffee](./app/static/buy-us-a-coffee.png)](https://pos.snapscan.io/qr/Ew6rBAsV)",
            width=350,
        )
