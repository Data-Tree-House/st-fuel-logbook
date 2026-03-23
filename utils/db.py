import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from constants import settings


@st.cache_resource
def get_engine() -> Engine:
    return create_engine(
        settings.db_connection_string,
        echo=("sqlite" in settings.db_connection_string),
        pool_pre_ping=True,
        connect_args={"check_same_thread": False} if "sqlite" in settings.db_connection_string else {},
    )
