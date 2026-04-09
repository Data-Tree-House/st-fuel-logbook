import requests
from dirty_equals import IsStr
from streamlit.testing.v1 import AppTest

from constants import settings as s

components_dir = s.root_dir / "components"


def test_logo_streamlit_component():
    def script():
        from components.logo import top_logo

        top_logo()

    at = AppTest.from_function(script)
    at.run(timeout=30)
    assert not at.exception


def test_logo_images_exist():
    banner_path = s.root_dir / s.logo_banner_path
    circle_path = s.root_dir / s.logo_circle_path

    assert banner_path.is_file(), f"Banner image not found at {banner_path}"
    assert circle_path.is_file(), f"Circle image not found at {circle_path}"


def test_homepage_up():
    response = requests.get(s.datatreehouse_url, timeout=30)
    assert response.status_code == 200, f"Homepage not reachable at {s.datatreehouse_url}"


def test_buy_a_coffee_image_exist():
    buy_us_a_coffee_path = s.root_dir / s.buy_us_a_coffee_path

    assert buy_us_a_coffee_path.is_file(), f"Buy us a coffee image not found at {buy_us_a_coffee_path}"


def test_snapscan_link_is_a_link():
    response = requests.get(s.snapscan_url, timeout=30, headers={"User-Agent": "I-Am-Bot"})
    assert response.status_code == 200, f"Snapscan link not reachable at {s.snapscan_url}"


def test_buy_us_a_coffee_component():
    def script():
        from components.coffee import buy_us_a_coffee

        buy_us_a_coffee()

    at = AppTest.from_function(script)
    at.run(timeout=30)
    assert not at.exception

    assert at.sidebar.markdown[0].value == IsStr(regex=r"^\[\!\[[^\]]*\]\([^\)]*\)\]\([^\)]*\)$")
