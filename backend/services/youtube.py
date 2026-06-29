from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
_TOKEN_URI = "https://oauth2.googleapis.com/token"
_CATEGORY_EDUCATION = "27"


def publish_youtube(caption, video_path: Path, settings, lang: str) -> str:
    """Upload a local MP4 as a YouTube Short. Returns the videoId."""
    refresh_token = getattr(settings, f"youtube_refresh_token_{lang}")
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=_TOKEN_URI,
        client_id=settings.youtube_client_id,
        client_secret=settings.youtube_client_secret,
        scopes=_SCOPES,
    )
    yt = build("youtube", "v3", credentials=creds)
    description = f"{caption.body}\n{' '.join(caption.hashtags)}"
    body = {
        "snippet": {
            "title": caption.title or caption.body[:100],
            "description": description,
            "tags": caption.hashtags,
            "categoryId": _CATEGORY_EDUCATION,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": settings.made_for_kids,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    response = yt.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    return response["id"]
