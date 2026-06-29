from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    video_repo_path: Path = Path(r"C:\Users\yborodulina\Downloads\Purr")
    database_url: str = "sqlite:///./purr.db"
    dev_mode: bool = True
    thumbs_dir: Path = Path("thumbs")

    anthropic_api_key: str = ""
    email_address: str = "borodulina.iana@gmail.com"
    email_app_password: str = ""


settings = Settings()

POSTING_SLOTS: dict[str, tuple[int, int, str]] = {
    "en": (20, 0, "America/New_York"),
    "uk": (20, 0, "Europe/Kyiv"),
    "zh": (20, 0, "Asia/Hong_Kong"),
    "fr": (20, 0, "Europe/Paris"),
}

USER_TZ: str = "America/Los_Angeles"
