from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

_scheduler = BackgroundScheduler()


def check_and_post(engine=None, dev_mode=None) -> None:
    """
    Find due scheduled posts and flip them to published in DEV_MODE.

    Finds ScheduledPost rows with status='scheduled' and scheduled_for <= now (UTC naive).
    In DEV_MODE: flips each to status='published' with
        platform_post_id = f"dev-{post.id}-{int(datetime.now(UTC).timestamp())}"
    Uses delayed imports to avoid circular imports.
    Accepts optional engine and dev_mode params for testability.
    """
    from config import settings
    from database import engine as default_engine
    from models.scheduled_post import ScheduledPost

    _engine = engine or default_engine
    _dev_mode = dev_mode if dev_mode is not None else settings.dev_mode
    if not _dev_mode:
        return  # Phase 4 will add real publishing here

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
            post.status = "published"
            post.platform_post_id = f"dev-{post.id}-{int(now_utc.timestamp())}"
        db.commit()


def start_scheduler() -> None:
    _scheduler.add_job(
        check_and_post, "interval", seconds=60, id="check_and_post", replace_existing=True
    )
    _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
