import datetime

import streamlit as st
from loguru import logger
from sqlalchemy.orm import Session

from constants import settings
from utils import primary_text
from utils.db import get_engine, get_preferences, upsert_user
from utils.model import FuelEntry, validate_fuel_consistency
from utils.types import Preferences, StreamlitUser

engine = get_engine()

# =============== // CONSTANTS // ===============

available_currencies = {
    "ZAR": 0,
}

available_fuel_types = {
    "Unleaded Petrol 95": 0,
    "Unleaded Petrol 93": 1,
    "Diesel 10ppm": 2,
    "Diesel 50ppm": 3,
    "Diesel 500ppm": 4,
}


# =============== // ACCOUNT CREATION FOR NEW USERS // ===============

upsert_user(
    logged_in_user=StreamlitUser(
        sub=str(st.user.sub),
        name=str(st.user.name),
        email=str(st.user.email),
        picture=str(st.user.picture),
    )
)

# =============== // FETCH PREFERENCES // ===============

st.markdown(f"## Welcome back, {primary_text(st.user.name)} 👋")
with st.spinner("Fetching preferences...", show_time=True):
    preferences: Preferences = get_preferences()


# =============== // FORM FOR NEW ENTRY // ===============

with st.form("fuel_entry_form"):
    st.markdown("### Record Fuel Entry")
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Date", value=datetime.datetime.now(settings.tz))
    with col2:
        time = st.time_input("Time", value=datetime.datetime.now(settings.tz).time())

    odometer = st.number_input(
        f"Odometer ({primary_text('km')})",
        min_value=0.0,
        step=1.0,
        format="%.1f",
    )

    trip = st.number_input(
        f"Trip Distance ({primary_text('km')})",
        min_value=0.0,
        step=1.0,
        format="%.1f",
    )

    col1, col2 = st.columns(2)
    with col1:
        filled = st.number_input(
            f"Fuel Filled ({primary_text('litres')})",
            min_value=0.0,
            step=0.1,
            format="%.2f",
        )
    with col2:
        fuel_type = st.selectbox(
            "Fuel Type",
            options=list(available_fuel_types.keys()),
            index=available_fuel_types.get(preferences["last_fuel_type"], 0),
        )

    col1, col2 = st.columns(2)
    with col1:
        price = st.number_input(
            "Price",
            min_value=0.0,
            step=0.01,
            format="%.2f",
        )
    with col2:
        currency = st.selectbox(
            "Currency",
            options=list(available_currencies.keys()),
            index=available_currencies.get(preferences["last_currency"], 0),
        )

    vehicle = st.selectbox(
        "Vehicle",
        options=list(preferences["all_vehicles"].keys()),
        accept_new_options=True,
        index=preferences["all_vehicles"].get(preferences["last_vehicle"], 0),
    )

    location = st.text_input(
        "Location",
        placeholder="e.g., Cape Town",
        value=preferences["last_location"],
    )

    submitted = st.form_submit_button(
        "Save Entry",
        use_container_width=True,
        type="primary",
    )

    if submitted:
        with st.spinner("Submitting...", show_time=True):
            # Combine date and time into a timezone-aware datetime
            entry_datetime = settings.tz.localize(datetime.datetime.combine(date, time))

            # Create new fuel entry
            try:
                with Session(engine) as session:
                    validate_fuel_consistency(
                        session=session,
                        user_id=str(st.user.sub),
                        vehicle=vehicle,
                        fuel_type=fuel_type,
                    )

                    new_entry = FuelEntry(
                        user_id=st.user.sub,
                        entry_datetime=entry_datetime,
                        odometer_km=odometer,
                        trip_km=trip,
                        fuel_litres=filled,
                        price=price,
                        currency=currency,
                        fuel_type=fuel_type,
                        vehicle=vehicle,
                        location=location if location else None,
                    )
                    session.add(new_entry)
                    session.commit()

                    price_per_litre = new_entry.price_per_litre
                    fuel_consumption = new_entry.fuel_consumption
            except ValueError as e:
                logger.error(f"Validation error while saving fuel entry: {e!s}")
                st.error(f"❌ Error: {e!s}")
                st.stop()
            except Exception:
                logger.exception("An unexpected error occurred while saving the fuel entry.")
                st.error("❌ An unexpected error occurred!")
                st.stop()

            logger.info("Fuel entry saved successfully.")
            st.success("✅ Entry saved successfully!")
            if filled > 0:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Price per Litre", f"{primary_text(currency)} {price_per_litre:.2f} {primary_text('/ L')}"
                    )
                with col2:
                    if trip > 0:
                        st.metric("Fuel Consumption", f"{fuel_consumption:.2f} {primary_text('km/L')}")


if submitted and st.button(
    "⛽ New Entry",
    use_container_width=True,
):
    st.rerun()

st.page_link(
    "stats.py",
    label="View Statistics",
    icon=":material/analytics:",
    width="stretch",
)

st.page_link(
    "bulk.py",
    label="Bulk Upload",
    icon=":material/upload_file:",
    width="stretch",
)
