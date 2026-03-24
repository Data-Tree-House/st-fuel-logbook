import streamlit as st
from loguru import logger
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from constants import settings
from utils import model
from utils.types import Preferences, StreamlitUser


@st.cache_resource
def get_engine() -> Engine:
    return create_engine(
        settings.db_connection_string,
        echo=("sqlite" in settings.db_connection_string),
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if "sqlite" in settings.db_connection_string else {},
    )


def upsert_user(
    logged_in_user: StreamlitUser,
):
    with Session(get_engine()) as session:
        stmt = select(model.User).where(model.User.id == logged_in_user["sub"])
        user: model.User | None = session.execute(stmt).scalar_one_or_none()
        if user:
            st.session_state.user = user
        else:
            logger.info(f"Creating new user {logged_in_user['email']}")
            with st.spinner("Creating user...", show_time=True):
                new_user = model.User(
                    id=logged_in_user["sub"],
                    name=logged_in_user["name"],
                    email=logged_in_user["email"],
                    picture=logged_in_user["picture"],
                )
                session.add(new_user)
                session.commit()
                st.session_state.user = new_user


def get_preferences() -> Preferences:
    last_fuel_type = ""
    last_location = ""
    last_currency = ""
    last_vehicle = ""
    all_vehicles: dict[str, int] = {}

    with Session(get_engine()) as session:
        stmt = (
            select(model.FuelEntry)
            .where(model.FuelEntry.user_id == st.session_state.user.id)
            .order_by(model.FuelEntry.entry_datetime.desc())
        )
        last_entry: model.FuelEntry | None = session.execute(stmt).scalars().first()
        if last_entry:
            last_fuel_type = last_entry.fuel_type
            last_location = last_entry.location
            last_currency = last_entry.currency
            last_vehicle = last_entry.vehicle

        stmt = select(model.FuelEntry.vehicle).where(model.FuelEntry.user_id == st.session_state.user.id).distinct()
        all_vehicles: dict[str, int] = {
            r: i for i, r in enumerate([row[0] for row in session.execute(stmt).all() if row[0]])
        }

    return {
        "all_vehicles": all_vehicles,
        "last_currency": last_currency,
        "last_fuel_type": last_fuel_type,
        "last_location": last_location,
        "last_vehicle": last_vehicle,
    }
