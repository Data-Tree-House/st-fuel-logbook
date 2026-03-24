from pathlib import Path

from PIL import Image
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve(strict=True).parent


class Settings(BaseSettings):
    db_connection_string: str

    default_picture: str = "https://gravatar.com/avatar/580b828f66630050b21aeaf8c20b89b3?s=400&d=mp&r=x"

    root_dir: Path = ROOT_DIR
    static_dir: Path = ROOT_DIR / "static"

    favicon: Image.Image = Image.open(ROOT_DIR / "static" / "datatreehouse.circle.png")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()  # type: ignore
