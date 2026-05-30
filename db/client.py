import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from constants import settings


@st.cache_resource
def get_engine() -> Engine:
    """Manages the database connection pool and dialect.
    Created once, reused for the entire application lifetime.

    Refs:
        - https://docs.sqlalchemy.org/en/21/core/engines.html#engine-creation-api

    Used to make sessions. NB Each thread/request should have its own session

    Returns:
        Engine: Manages the database connection pool and dialect
    """
    connect_args = {}

    if "sqlite" in settings.db_connection_string:
        connect_args = {"check_same_thread": False}

    return create_engine(
        settings.db_connection_string,
        echo=settings.db_echo,
        echo_pool=settings.db_echo,
        pool_pre_ping=True,
        pool_size=5,
        pool_recycle=3600,
        connect_args=connect_args,
    )
