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
