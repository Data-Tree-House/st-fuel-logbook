from typing import Any

import requests
import streamlit.components.v1 as components
from loguru import logger

from constants import settings as s


def load_umami() -> None:
    components.html(
        f'<script async defer src="{s.umami_host}" '  #
        f'data-website-id="{s.umami_website_id}"></script>'
    )


def umami_track_event(
    event_name: str,
    url: str | None = None,
    data: dict | None = None,
    timeout: float = 2.0,
    fail_silent: bool = True,
) -> None:

    payload: dict[str, Any] = {
        "type": "event",
        "payload": {
            "website": s.umami_website_id,
            "name": event_name,
        },
    }

    if url is not None:
        payload["payload"]["url"] = url

    if data is not None:
        payload["payload"]["data"] = data  # type: ignore

    headers = {
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10; K) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/143.0.0.0 Mobile Safari/537.36"
        ),
    }

    try:
        requests.post(
            f"{s.umami_host}/api/send",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
    except Exception as e:
        if fail_silent:
            # Fail silently (analytics should never break app)
            logger.warning(f"Failed to send event to Umami analytics: {e}")
        else:
            logger.exception(f"Failed to send event to Umami analytics: {e}")
            raise
