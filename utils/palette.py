from typing import Any

PRIMARY_COLOR = "F36441"


def primary_text(text: Any) -> str:
    return f":color[{text}]{{foreground='#{PRIMARY_COLOR}'}}"


def google_text() -> str:
    # https://usbrandcolors.com/google-colors/
    colors = ["4285F4", "DB4437", "F4B400", "4285F4", "0F9D58", "DB4437"]
    letters = ["G", "o", "o", "g", "l", "e"]

    coloured_letters = [
        f":color[{letter}]{{foreground='#{color}'}}"  #
        for letter, color in zip(letters, colors, strict=True)
    ]

    return "".join(coloured_letters)
