from datetime import UTC, datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

_scheduler = BackgroundScheduler()
_MAX_RETRIES = 3
_RETRY_BACKOFF_MINUTES = 5


def _resolve_video_path(post, db: Session, settings) -> Path:
    from models.episode import Episode
    from models.video import Video

    episode = db.query(Episode).filter(Episode.id == post.episode_id).one()
    video = db.query(Video).filter(Video.episode_num == episode.number).one()
    lang_dir = Path(video.folder_path) / "output" / post.language
    mp4s = sorted(lang_dir.glob("*FULL*.mp4"))
    if not mp4s:
        raise FileNotFoundError(f"No FULL mp4 in {lang_dir}")
    return mp4s[0]


def _dispatch(post, caption, video_path: Path, settings) -> str:
    """Route to the correct platform service. Returns platform_post_id."""
    if post.platform == "youtube":
        from services.youtube import publish_youtube

        return publish_youtube(caption, video_path, settings, post.language)
    elif post.platform == "tiktok":
        from services.tiktok import publish_tiktok

        return publish_tiktok(caption, video_path, settings, post.language)
    elif post.platform == "instagram":
        from services.instagram import publish_instagram
        from services.public_url import public_url_context

        with public_url_context(video_path, post.episode_id, settings, post.language) as public_url:
            return publish_instagram(caption, public_url, settings, post.language)
    else:
        raise ValueError(f"Unknown platform: {post.platform}")


def _process_post(post, db: Session, dev_mode: bool, now_utc: datetime, settings) -> None:
    """Attempt to publish one post; update its status in-place."""
    if dev_mode:
        post.status = "published"
        post.platform_post_id = f"dev-{post.id}-{int(now_utc.timestamp())}"
        post.published_at = now_utc
        return

    from models.caption import Caption

    try:
        caption = (
            db.query(Caption)
            .filter_by(episode_id=post.episode_id, language=post.language, platform=post.platform)
            .one()
        )
        video_path = _resolve_video_path(post, db, settings)
        platform_post_id = _dispatch(post, caption, video_path, settings)
        post.status = "published"
        post.platform_post_id = platform_post_id
        post.published_at = now_utc
        post.error_message = None
    except Exception as exc:
        post.retry_count = (post.retry_count or 0) + 1
        post.error_message = str(exc)
        if post.retry_count >= _MAX_RETRIES:
            post.status = "failed"
        else:
            post.status = "scheduled"
            post.scheduled_for = now_utc + timedelta(minutes=_RETRY_BACKOFF_MINUTES)


def check_and_post(engine=None, dev_mode=None) -> None:
    from config import settings
    from database import engine as default_engine
    from models.scheduled_post import ScheduledPost

    _engine = engine or default_engine
    _dev_mode = dev_mode if dev_mode is not None else settings.dev_mode

    now_utc = datetime.now(UTC).replace(tzinfo=None)

    with Session(_engine) as db:
        due = (
            db.query(ScheduledPost)
            .filter(
                ScheduledPost.status == "scheduled",
                ScheduledPost.scheduled_for <= now_utc,
            )
            .all()
        )
        for post in due:
            post.status = "publishing"
        db.commit()

        for post in due:
            _process_post(post, db, _dev_mode, now_utc, settings)
            db.commit()


def publish_post_by_id(post_id: int, engine=None) -> None:
    """Immediately dispatch a single post (used by the Publish now route)."""
    from config import settings
    from database import engine as default_engine
    from models.scheduled_post import ScheduledPost

    _engine = engine or default_engine
    now_utc = datetime.now(UTC).replace(tzinfo=None)

    with Session(_engine) as db:
        post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).one()
        _process_post(post, db, settings.dev_mode, now_utc, settings)
        db.commit()


def start_scheduler() -> None:
    _scheduler.add_job(
        check_and_post, "interval", seconds=60, id="check_and_post", replace_existing=True
    )
    _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
