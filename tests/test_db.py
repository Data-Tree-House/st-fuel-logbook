from unittest.mock import patch

from sqlalchemy.engine import Engine

# Patch st.cache_resource to a no-op so get_engine can be called outside Streamlit.
with patch("streamlit.cache_resource", lambda f: f):
    from db.client import get_engine


def test_get_engine_returns_engine():
    with patch("db.client.settings") as mock_settings:
        mock_settings.db_connection_string = "sqlite:///:memory:"
        mock_settings.db_echo = False

        engine = get_engine()

    assert isinstance(engine, Engine)
    engine.dispose()


def test_get_engine_can_connect():
    with patch("db.client.settings") as mock_settings:
        mock_settings.db_connection_string = "sqlite:///:memory:"
        mock_settings.db_echo = False

        engine = get_engine()

    with engine.connect() as conn:
        assert conn is not None

    engine.dispose()
