from pathlib import Path

from tiktokautouploader import upload_tiktok  # noqa: PLC0415


def publish_tiktok(caption, video_path: Path, settings, lang: str) -> str:
    """Upload a local MP4 to TikTok via session cookies. Returns post reference string."""
    cookie_file = getattr(settings, f"tiktok_cookies_{lang}")
    description = f"{caption.body} {' '.join(caption.hashtags)}"

    result = upload_tiktok(
        video=str(video_path),
        description=description,
        hashtags=caption.hashtags,
        cookies=cookie_file,
    )
    return str(result) if result else f"tiktok-{lang}-{video_path.stem}"
