import os
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from config import settings as app_settings
from database import ScheduledPost, get_db
from scheduler import publish_post_by_id

router = APIRouter(prefix="/schedule", tags=["schedule"])

_PLATFORMS = ("youtube", "tiktok", "instagram")
_LANGUAGES = ("en", "uk", "zh", "fr")


def _check_credential(lang: str, platform: str) -> dict:
    if platform == "youtube":
        token = getattr(app_settings, f"youtube_refresh_token_{lang}", "")
        ok = bool(token)
        return {
            "lang": lang,
            "platform": platform,
            "status": "ok" if ok else "error",
            "detail": "" if ok else "Refresh token not configured",
        }
    elif platform == "tiktok":
        cookie_path = getattr(app_settings, f"tiktok_cookies_{lang}", "")
        if not cookie_path:
            return {
                "lang": lang,
                "platform": platform,
                "status": "error",
                "detail": "Cookie file path not configured",
            }
        if not os.path.isfile(cookie_path):
            return {
                "lang": lang,
                "platform": platform,
                "status": "error",
                "detail": f"Cookie file not found: {cookie_path}",
            }
        age_days = (datetime.now(UTC).timestamp() - os.path.getmtime(cookie_path)) / 86400
        if age_days > app_settings.tiktok_cookie_warn_days:
            return {
                "lang": lang,
                "platform": platform,
                "status": "warning",
                "detail": f"Cookie file is {int(age_days)} days old — re-export soon",
            }
        return {"lang": lang, "platform": platform, "status": "ok", "detail": ""}
    else:  # instagram
        token = getattr(app_settings, f"instagram_token_{lang}", "")
        ok = bool(token)
        return {
            "lang": lang,
            "platform": platform,
            "status": "ok" if ok else "error",
            "detail": "" if ok else "Token not configured",
        }


@router.get("/health")
def get_health():
    return {
        "channels": [
            _check_credential(lang, platform) for lang in _LANGUAGES for platform in _PLATFORMS
        ]
    }


@router.post("/{post_id}/publish", status_code=202)
def publish_now(
    post_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),  # noqa: B008
):
    post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    if post.status == "published":
        raise HTTPException(409, "Post is already published")
    if post.status == "publishing":
        raise HTTPException(409, "Post is already being published")
    post.status = "publishing"
    db.commit()
    background_tasks.add_task(publish_post_by_id, post_id)
    return {"status": "publishing"}
