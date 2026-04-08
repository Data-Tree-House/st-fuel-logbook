import datetime
from collections.abc import Sequence

import streamlit as st
from loguru import logger
from sqlalchemy.orm import Session

from constants import settings
from db import crud, get_engine, m
from utils import primary_text

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

crud.upsert_user(
    sub=str(st.user.sub),
    name=str(st.user.name),
    email=str(st.user.email),
    picture=str(st.user.picture),
    engine=get_engine(),
)

# =============== // FORM FOR NEW ENTRY // ===============


def new_car_layout():
    st.markdown(f"Please {primary_text('add a car')} to start logging fuel entries.")
    st.page_link(
        "pages/new_car.py",
        label="Add my first car",
        icon=":material/directions_car:",
        width="stretch",
        query_params={"first_car": "true"},
    )


def new_fuel_entry_layout():
    with st.form("fuel_entry_form"):
        st.markdown(f"### Record a {primary_text('Fuel Entry')}")
        st.markdown(f"Welcome back, {st.user.name}👋")
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

        filled = st.number_input(
            f"Fuel Filled ({primary_text('litres')})",
            min_value=0.0,
            step=0.1,
            format="%.2f",
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
                index=available_currencies.get("ZAR", 0),
            )

        location = st.text_input(
            "Location",
            placeholder="e.g., Cape Town",
            value="Durbanville",
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
                    with Session(get_engine()) as session:
                        new_entry = m.FuelEntry(
                            user_id=st.user.sub,
                            entry_datetime=entry_datetime,
                            odometer_km=odometer,
                            trip_km=trip,
                            fuel_litres=filled,
                            price=price,
                            currency=currency,
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
        "pages/stats.py",
        label="View Statistics",
        icon=":material/analytics:",
        width="stretch",
    )
    st.page_link(
        "pages/new_car.py",
        label="Add a New Car",
        icon=":material/directions_car:",
        width="stretch",
    )
    st.page_link(
        "pages/bulk.py",
        label="Bulk Upload",
        icon=":material/upload_file:",
        width="stretch",
    )


cars: Sequence[m.Car] | None = crud.get_cars(
    user_id=str(st.user.sub),
    engine=get_engine(),
)

if cars is None:
    st.markdown(f"## Welcome to {primary_text('Fuel Logbook')} 👋")
    new_car_layout()
else:
    new_fuel_entry_layout()
