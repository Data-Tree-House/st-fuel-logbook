from dirty_equals import IsStr

from utils import PRIMARY_COLOR, SECONDARY_COLOR, coloured_text, primary_text, secondary_text
from utils.palette import google_text

coloured_text_regex = r"^:color\[(.+?)\]\{foreground='(#[0-9A-Fa-f]{3}|#[0-9A-Fa-f]{6})'\}$"


def test_coloured_text():
    input_str = "Hello"
    color = "#F36441"

    assert coloured_text(input_str, color) == IsStr(
        regex=coloured_text_regex,
    )

    # non-string gets turned into string
    input_str = [10]
    assert coloured_text(input_str, color) == IsStr(  # type: ignore
        regex=coloured_text_regex,
    )


def test_primary_text():
    input_str = "Hello"

    out = primary_text(input_str)
    assert out == IsStr(
        regex=coloured_text_regex,
    )

    assert PRIMARY_COLOR in out


def test_secondary_test():
    input_str = "Hello"

    out = secondary_text(input_str)
    assert out == IsStr(
        regex=coloured_text_regex,
    )

    assert SECONDARY_COLOR in out


def test_coloured_text_with_empty():
    color = "#F36441"

    # Empty string
    assert coloured_text("", color) == ""


def test_coloured_text_with_bad_hex():
    input_str = "Hello"

    # Empty color hex
    assert coloured_text(input_str, "") == input_str

    # Non-string color hex
    assert coloured_text(input_str, 123) == input_str  # type: ignore


def test_google_text():
    out = google_text()

    assert "G" in out
    assert "o" in out
    assert "g" in out
    assert "l" in out
    assert "e" in out

    assert "#4285F4" in out  # blue
    assert "#DB4437" in out  # red
    assert "#F4B400" in out  # yellow
    assert "#0F9D58" in out  # green

    assert out.count(":color[") == 6
