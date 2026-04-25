from typing import TypedDict

PRIMARY_COLOR = "#F36441"
SECONDARY_COLOR = "#203b56"


class Palette(TypedDict):
    primary: str
    secondary: str


dth_palette: Palette = {
    "primary": PRIMARY_COLOR,
    "secondary": SECONDARY_COLOR,
}


def coloured_text(
    text: str,
    color_hex: str,
) -> str:
    if not text:
        return ""

    if not color_hex or not isinstance(color_hex, str):
        return text

    return f":color[{text}]{{foreground='{color_hex}'}}"


def primary_text(
    text: str,
) -> str:
    return coloured_text(text, f"{PRIMARY_COLOR}")


def secondary_text(
    text: str,
) -> str:
    return coloured_text(text, f"{SECONDARY_COLOR}")


def google_text() -> str:
    # https://usbrandcolors.com/google-colors/
    google_blue = "#4285F4"
    google_red = "#DB4437"
    google_yellow = "#F4B400"
    google_green = "#0F9D58"

    return "".join(
        [
            coloured_text(letter, color)
            for letter, color in [
                ("G", google_blue),
                ("o", google_red),
                ("o", google_yellow),
                ("g", google_blue),
                ("l", google_green),
                ("e", google_red),
            ]
        ]
    )
