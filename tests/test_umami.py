from unittest.mock import patch

import pytest
import requests
from dirty_equals import IsStr
from loguru import logger
from streamlit.testing.v1 import AppTest

from constants import settings as s
from utils.umami import umami_track_event

components_dir = s.root_dir / "components"


def test_load_umami():
    def script():
        import streamlit as st

        from utils.umami import load_umami

        load_umami()
        st.markdown("Hello!")

    at = AppTest.from_function(script)
    at.run(timeout=30)
    assert not at.exception


def test_umami_track_event():
    umami_track_event(
        event_name="test",
    )


@pytest.mark.parametrize(
    "input_data",
    [
        pytest.param(
            {
                "event_name": "test_1",
                "url": "/",
                "data": {"test": "hello-world"},
                "timeout": 2,
            },
            id="All arguments",
        ),
        pytest.param(
            {
                "event_name": "test_1",
                "url": "/my/path/to/endpoint",
            },
            id="Specify path",
        ),
    ],
)
def test_umami_event_with_arguments(
    input_data: dict,
):
    try:
        umami_track_event(**input_data)
    except Exception as e:
        pytest.fail(f"umami_track_event raised an exception with input {input_data}: {e}")


@pytest.mark.parametrize(
    "exc_class",
    [
        pytest.param(requests.Timeout, id="Timeout"),
        pytest.param(requests.ConnectionError, id="ConnectionError"),
        pytest.param(requests.HTTPError, id="HTTPError"),
    ],
)
def test_umami_track_event_network_errors_logged(exc_class):
    messages: list[str] = []
    handler_id = logger.add(
        lambda msg: messages.append(msg.strip()),
        level="WARNING",
        format="{message}",
    )

    try:
        with patch("utils.umami.requests.post", side_effect=exc_class()):
            umami_track_event(event_name="test_network_error", fail_silent=True)
    finally:
        logger.remove(handler_id)

    assert len(messages) == 1
    assert messages[0] == IsStr(regex=r".*Failed to send event to Umami analytics.*")


def test_umami_track_event_raises_when_not_silent():
    with (
        patch("utils.umami.requests.post", side_effect=requests.Timeout()),
        pytest.raises(requests.Timeout),
    ):
        umami_track_event(event_name="test_raises", fail_silent=False)
