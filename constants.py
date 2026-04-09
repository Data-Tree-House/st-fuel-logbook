from datetime import tzinfo
from pathlib import Path

import pytz
from PIL import Image
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve(strict=True).parent


class Settings(BaseSettings):
    # =============== // Database Configurations // ===============
    # dialect[+driver]://user:password@host/dbname[?key=value..]
    # e.g. engine = create_engine("postgresql+psycopg2://scott:tiger@localhost/test")
    db_connection_string: str
    db_echo: bool = False

    default_picture: str = "https://gravatar.com/avatar/580b828f66630050b21aeaf8c20b89b3?s=400&d=mp&r=x"

    root_dir: Path = ROOT_DIR
    static_dir: Path = ROOT_DIR / "static"

    favicon: Image.Image = Image.open(ROOT_DIR / "static" / "datatreehouse.circle.png")

    logo_banner_path: str = "static/datatreehouse.banner.png"
    logo_circle_path: str = "static/datatreehouse.banner.png"
    buy_us_a_coffee_path: str = "static/buy-us-a-coffee.png"

    datatreehouse_url: str = "https://datatreehouse.org"
    snapscan_url: str = "https://pos.snapscan.io/qr/Ew6rBAsV"

    tz: tzinfo = pytz.timezone("Africa/Johannesburg")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()  # type: ignore
