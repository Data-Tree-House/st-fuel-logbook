import datetime

import streamlit as st
from loguru import logger

from db import crud, get_engine
from db.model import FuelTypeLiteral
from utils import primary_text

is_first_car: bool = str(st.query_params.get("first_car", "false")).lower() == "true"
available_fuel_types: list[FuelTypeLiteral] = [
    "Unleaded Petrol 95",
    "Unleaded Petrol 93",
    "Diesel 10ppm",
    "Diesel 50ppm",
    "Diesel 500ppm",
]

if is_first_car:
    st.markdown(f"### Add your {primary_text('first')} car!")
else:
    st.markdown(f"### Add a new {primary_text('car')}!")

submitted = None

with st.form("new_car_form"):
    nickname = st.text_input(
        f"Nickname {primary_text('*')}",
        placeholder="e.g., Red Beast",
        max_chars=50,
        help="A short nickname for the car (required).",
    )

    fuel_type = st.selectbox(
        f"Fuel Type {primary_text('*')}",
        options=available_fuel_types,
        index=None,
        placeholder="Select a fuel type...",
        help="Select the type of fuel your car uses (required).",
    )

    st.markdown("The details below are all optional! You can always come back later!")

    registration_number = st.text_input(
        "Registration Number",
        placeholder="e.g., XL 12 SR GP",
        max_chars=10,
        help="Vehicle registration number (optional).",
    )

    vin_number = st.text_input(
        "VIN Number",
        placeholder="e.g., 1FALP42X9PF111111",
        max_chars=17,
        help="Vehicle Identification Number (VIN) (optional).",
    )

    model_description = st.text_input(
        "Model Description",
        placeholder="e.g., Ford Focus 1.0 EcoBoost Ambiente 5dr",
        max_chars=255,
        help="Full model description of the car (optional).",
    )

    color = st.text_input(
        "Color",
        placeholder="e.g., Racing Red",
        max_chars=50,
        help="Color of the car (optional).",
    )

    registration_date = st.date_input(
        "Registration Date",
        value=None,
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.datetime.now(tz=datetime.UTC).date(),
        help="Date the car was first registered (optional).",
    )

    submitted = st.form_submit_button(
        "Add Car" if not is_first_car else "Add my first car!",
        use_container_width=True,
        type="primary",
    )

    if submitted:
        if not nickname:
            st.error("❌ Please provide a nickname for your car.")
            st.stop()
        if fuel_type is None:
            st.error("❌ Please select a fuel type.")
            st.stop()

        with st.spinner("Saving...", show_time=True):
            try:
                crud.new_car(
                    user_id=str(st.user.sub),
                    nickname=nickname,
                    fuel_type=fuel_type,
                    engine=get_engine(),
                    registration_number=registration_number or None,
                    vin_number=vin_number or None,
                    model_description=model_description or None,
                    color=color or None,
                    registration_date=registration_date if isinstance(registration_date, datetime.date) else None,
                )
            except Exception:
                logger.exception("An unexpected error occurred while saving the car.")
                st.error("❌ An unexpected error occurred!")
                st.stop()

        logger.info(f"New car '{nickname}' saved for user {st.user.sub}.")
        st.success(f"✅ Car {primary_text(nickname)} added successfully!")

if not is_first_car or (submitted and is_first_car):
    st.page_link(
        "pages/home.py",
        label="Log a Fuel Entry",
        icon=":material/local_gas_station:",
        width="stretch",
    )
