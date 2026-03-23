import os

import streamlit.components.v1 as components


def load_umami(
    website_id: str | None = os.getenv("UMAMI_WEBSITE_ID"),
    umami_host: str = os.getenv("UMAMI_HOST", "https://umami.datatreehouse.org/script.js"),
) -> None:
    if website_id:
        components.html(
            f'<script async defer src="{umami_host}" '  #
            f'data-website-id="{website_id}"></script>'
        )
