from typing import Any

PRIMARY_COLOR = "F36441"


def coloured_text(text: Any, color_hex: str) -> str:
    return f":color[{text}]{{foreground='{color_hex}'}}"


def primary_text(text: Any) -> str:
    return coloured_text(text, f"#{PRIMARY_COLOR}")


def google_text() -> str:
    # https://usbrandcolors.com/google-colors/
    colors = ["4285F4", "DB4437", "F4B400", "4285F4", "0F9D58", "DB4437"]
    letters = ["G", "o", "o", "g", "l", "e"]

    coloured_letters = [
        f":color[{letter}]{{foreground='#{color}'}}"  #
        for letter, color in zip(letters, colors, strict=True)
    ]

    return "".join(coloured_letters)
