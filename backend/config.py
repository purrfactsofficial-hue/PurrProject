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

    # YouTube — one Cloud project per language channel
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token_en: str = ""
    youtube_refresh_token_uk: str = ""
    youtube_refresh_token_zh: str = ""
    youtube_refresh_token_fr: str = ""

    # TikTok — sessionid cookie files per language account
    tiktok_cookies_en: str = ""
    tiktok_cookies_uk: str = ""
    tiktok_cookies_zh: str = ""
    tiktok_cookies_fr: str = ""
    tiktok_cookie_warn_days: int = 21

    # Instagram — long-lived tokens + Business user IDs
    instagram_token_en: str = ""
    instagram_token_uk: str = ""
    instagram_token_zh: str = ""
    instagram_token_fr: str = ""
    instagram_user_id_en: str = ""
    instagram_user_id_uk: str = ""
    instagram_user_id_zh: str = ""
    instagram_user_id_fr: str = ""

    # Instagram public URL mode: "tunnel" (default) or "r2"
    ig_public_url_mode: str = "tunnel"
    r2_public_base: str = ""

    # COPPA — must be True for kids' content
    made_for_kids: bool = True


settings = Settings()

POSTING_SLOTS: dict[str, tuple[int, int, str]] = {
    "en": (20, 0, "America/New_York"),
    "uk": (20, 0, "Europe/Kyiv"),
    "zh": (20, 0, "Asia/Hong_Kong"),
    "fr": (20, 0, "Europe/Paris"),
}

USER_TZ: str = "America/Los_Angeles"
