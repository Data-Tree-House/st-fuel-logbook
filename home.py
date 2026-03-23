import datetime
from typing import Any

import pytz
import streamlit as st
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from utils import PRIMARY_COLOR
from utils.db import get_engine
from utils.model import FuelEntry, User, validate_fuel_consistency

st.set_page_config(
    page_title="Fuel Logbook",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TIMEZONE = pytz.timezone("Africa/Johannesburg")

engine = get_engine()
with Session(engine) as session:
    stmt = select(User).where(User.id == st.user.sub)
    user = session.execute(stmt).scalar_one_or_none()
    if user:
        st.session_state.user = user
    else:
        with st.spinner("Creating user..."):
            new_user = User(
                id=st.user.sub,
                name=st.user.name,
                email=st.user.email,
                picture=st.user.picture,
            )
            session.add(new_user)
            session.commit()
            st.session_state.user = new_user


def fancy_text(text: Any) -> str:
    return f":color[{text}]{{foreground='#{PRIMARY_COLOR}'}}"


st.markdown(f"## Welcome back, {fancy_text(st.user.name)} 👋")

# Fetch the last fuel entry's data. It will probably be the same!
last_fuel_type = None
last_location = None
last_currency = None
last_vehicle = None
all_vehicles: list[str] = []
with Session(engine) as session:
    stmt = select(FuelEntry).where(FuelEntry.user_id == st.user.sub).order_by(FuelEntry.entry_datetime.desc())
    last_entry = session.execute(stmt).scalars().first()
    if last_entry:
        last_fuel_type = last_entry.fuel_type
        last_location = last_entry.location
        last_currency = last_entry.currency
        last_vehicle = last_entry.vehicle

    stmt = select(FuelEntry.vehicle).where(FuelEntry.user_id == st.user.sub).distinct()
    all_vehicles = [row[0] for row in session.execute(stmt).all() if row[0]]


with st.form("fuel_entry_form"):
    st.markdown("### Record Fuel Entry")

    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Date", value=datetime.datetime.now(TIMEZONE))
    with col2:
        time = st.time_input("Time", value=datetime.datetime.now(TIMEZONE).time())

    odometer = st.number_input(
        f"Odometer ({fancy_text('km')})",
        min_value=0.0,
        step=1.0,
        format="%.1f",
    )

    trip = st.number_input(
        f"Trip Distance ({fancy_text('km')})",
        min_value=0.0,
        step=1.0,
        format="%.1f",
    )

    col1, col2 = st.columns(2)
    with col1:
        filled = st.number_input(
            f"Fuel Filled ({fancy_text('litres')})",
            min_value=0.0,
            step=0.1,
            format="%.2f",
        )
    with col2:
        options = {
            "Petrol": 0,
            "Diesel": 1,
        }
        fuel_type = st.selectbox(
            "Fuel Type",
            options=list(options.keys()),
            index=options.get(str(last_fuel_type), 0),
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
        options = {
            "ZAR": 0,
        }
        currency = st.selectbox(
            "Currency",
            options=list(options.keys()),
            index=options.get(str(last_currency), 0),
        )

    vehicle = st.selectbox(
        "Vehicle",
        options=all_vehicles,
        accept_new_options=True,
        index=all_vehicles.index(last_vehicle) if last_vehicle in all_vehicles else -1,
    )

    location = st.text_input(
        "Location",
        placeholder="e.g., Cape Town",
        value=last_location if last_location else "",
    )

    submitted = st.form_submit_button(
        "Save Entry",
        use_container_width=True,
        type="primary",
    )

    if submitted:
        with st.spinner("Submitting..."):
            # Combine date and time into a timezone-aware datetime
            entry_datetime = TIMEZONE.localize(datetime.datetime.combine(date, time))

            # Create new fuel entry
            try:
                with Session(engine) as session:
                    validate_fuel_consistency(
                        session=session,
                        user_id=st.session_state.user.id,
                        vehicle=vehicle,
                        fuel_type=fuel_type,
                    )

                    new_entry = FuelEntry(
                        user_id=st.session_state.user.id,
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

                    # Calculate metrics
                    price_per_litre = new_entry.price_per_litre
                    fuel_consumption = new_entry.fuel_consumption
            except ValueError as e:
                st.error(f"❌ Error: {e!s}")
                st.stop()
            except Exception:
                logger.exception("An unexpected error occurred while saving the fuel entry.")
                st.error("❌ An unexpected error occurred!")
                st.stop()

            st.success("✅ Entry saved successfully!")
            if filled > 0:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Price per Litre", f"{fancy_text(currency)} {price_per_litre:.2f}")
                with col2:
                    if trip > 0:
                        st.metric("Fuel Consumption", f"{fuel_consumption:.2f} {fancy_text('km/L')}")


if submitted and st.button(
    "⛽ New Entry",
    use_container_width=True,
):
    st.rerun()

st.page_link(
    "stats.py",
    label="View Statistics",
    icon=":material/analytics:",
    use_container_width=True,
)
