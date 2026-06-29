from datetime import UTC, datetime
from datetime import date as Date
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import POSTING_SLOTS, USER_TZ
from database import Caption, Episode, ScheduledPost, get_db

router = APIRouter(prefix="/schedule", tags=["schedule"])

_TZ_LABELS: dict[str, str] = {
    "en": "New York",
    "uk": "Kyiv",
    "zh": "Hong Kong",
    "fr": "Paris",
}


def compute_utc_slot(post_date: Date, lang: str) -> datetime:
    hour, minute, tz_name = POSTING_SLOTS[lang]
    local_dt = datetime(
        post_date.year,
        post_date.month,
        post_date.day,
        hour,
        minute,
        tzinfo=ZoneInfo(tz_name),
    )
    return local_dt.astimezone(UTC).replace(tzinfo=None)


@router.get("/slots")
def get_slots(episode_id: int = Query(...), date: Date = Query(...), db: Session = Depends(get_db)):  # noqa: B008
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(404, "Episode not found")
    post_date = date
    slots = []
    for lang, (_hour, _minute, _tz_name) in POSTING_SLOTS.items():
        utc_dt = compute_utc_slot(post_date, lang)
        pacific_dt = utc_dt.replace(tzinfo=UTC).astimezone(ZoneInfo(USER_TZ))
        p_hour = pacific_dt.hour % 12 or 12
        am_pm = "AM" if pacific_dt.hour < 12 else "PM"
        slots.append(
            {
                "language": lang,
                "audience_time": "8:00 PM",
                "audience_tz": _TZ_LABELS[lang],
                "your_time": f"{p_hour}:{pacific_dt.minute:02d} {am_pm}",
                "your_tz": "Pacific",
            }
        )
    return {"slots": slots}


class CreateScheduleBody(BaseModel):
    episode_id: int
    date: str
    languages: list[str]
    platforms: list[str]


@router.post("/create")
def create_schedule(body: CreateScheduleBody, db: Session = Depends(get_db)):  # noqa: B008
    post_date = Date.fromisoformat(body.date)
    now_utc = datetime.now(UTC).replace(tzinfo=None)

    episode = db.query(Episode).filter(Episode.id == body.episode_id).first()
    if not episode:
        raise HTTPException(404, "Episode not found")

    missing = [
        f"{lang}/{plat}"
        for lang in body.languages
        for plat in body.platforms
        if not db.query(Caption)
        .filter_by(episode_id=body.episode_id, language=lang, platform=plat)
        .first()
    ]
    if missing:
        raise HTTPException(
            409,
            f"Can't schedule — no caption for {', '.join(missing)}. Import or write them first.",
        )

    errors: list[str] = []
    warnings: list[str] = []
    posts: list[ScheduledPost] = []

    for lang in body.languages:
        slot_utc = compute_utc_slot(post_date, lang)
        if slot_utc < now_utc:
            errors.append(
                f"{lang.upper()} 8 PM has already passed for that date — pick the next day."
            )
            continue
        for plat in body.platforms:
            existing = (
                db.query(ScheduledPost)
                .filter(
                    ScheduledPost.language == lang,
                    ScheduledPost.platform == plat,
                    ScheduledPost.status.in_(["scheduled", "published"]),
                    ScheduledPost.scheduled_for == slot_utc,
                )
                .first()
            )
            if existing:
                warnings.append(f"{lang.upper()}/{plat} already has a post that day.")
            posts.append(
                ScheduledPost(
                    episode_id=body.episode_id,
                    language=lang,
                    platform=plat,
                    status="scheduled",
                    scheduled_for=slot_utc,
                )
            )

    for p in posts:
        db.add(p)
    db.commit()

    return {"created": len(posts), "errors": errors, "warnings": warnings}


class PostOut(BaseModel):
    id: int
    episode_id: int
    episode_name: str
    language: str
    platform: str
    status: str
    scheduled_for: str
    platform_post_id: str | None
    error_message: str | None


@router.get("/queue")
def get_queue(db: Session = Depends(get_db)):  # noqa: B008
    rows = (
        db.query(ScheduledPost, Episode.topic)
        .join(Episode, Episode.id == ScheduledPost.episode_id)
        .order_by(ScheduledPost.scheduled_for)
        .all()
    )
    items = [
        PostOut(
            id=p.id,
            episode_id=p.episode_id,
            episode_name=topic,
            language=p.language,
            platform=p.platform,
            status=p.status,
            scheduled_for=p.scheduled_for.isoformat() + "Z",
            platform_post_id=p.platform_post_id,
            error_message=p.error_message,
        )
        for p, topic in rows
    ]
    return {"items": [i.model_dump() for i in items]}


@router.post("/{post_id}/retry")
def retry_post(post_id: int, db: Session = Depends(get_db)):  # noqa: B008
    post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    if post.status != "failed":
        raise HTTPException(409, f"Only failed posts can be retried (status: {post.status})")
    post.status = "scheduled"
    post.retry_count = 0
    post.error_message = None
    db.commit()
    return {"status": "scheduled"}


class RescheduleBody(BaseModel):
    date: str


@router.patch("/episode/{episode_id}")
def reschedule_episode(episode_id: int, body: RescheduleBody, db: Session = Depends(get_db)):  # noqa: B008
    posts = db.query(ScheduledPost).filter_by(episode_id=episode_id, status="scheduled").all()
    if not posts:
        raise HTTPException(404, "No scheduled posts found for this episode")
    new_date = Date.fromisoformat(body.date)
    for p in posts:
        p.scheduled_for = compute_utc_slot(new_date, p.language)
    db.commit()

    # Query posts with episode join to construct PostOut objects
    rows = (
        db.query(ScheduledPost, Episode.topic)
        .filter_by(episode_id=episode_id, status="scheduled")
        .join(Episode, Episode.id == ScheduledPost.episode_id)
        .all()
    )
    posts_out = [
        PostOut(
            id=p.id,
            episode_id=p.episode_id,
            episode_name=topic,
            language=p.language,
            platform=p.platform,
            status=p.status,
            scheduled_for=p.scheduled_for.isoformat() + "Z",
            platform_post_id=p.platform_post_id,
            error_message=p.error_message,
        )
        for p, topic in rows
    ]
    return {"moved": len(posts), "posts": [p.model_dump() for p in posts_out]}


@router.patch("/{post_id}")
def reschedule_post(post_id: int, body: RescheduleBody, db: Session = Depends(get_db)):  # noqa: B008
    post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    if post.status == "published":
        raise HTTPException(409, "Cannot reschedule a published post")
    new_date = Date.fromisoformat(body.date)
    post.scheduled_for = compute_utc_slot(new_date, post.language)
    db.commit()
    db.refresh(post)
    episode = db.query(Episode).filter(Episode.id == post.episode_id).first()
    return PostOut(
        id=post.id,
        episode_id=post.episode_id,
        episode_name=episode.topic if episode else "Unknown",
        language=post.language,
        platform=post.platform,
        status=post.status,
        scheduled_for=post.scheduled_for.isoformat() + "Z",
        platform_post_id=post.platform_post_id,
        error_message=post.error_message,
    ).model_dump()


@router.delete("/{post_id}")
def cancel_post(post_id: int, db: Session = Depends(get_db)):  # noqa: B008
    post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    if post.status == "published":
        raise HTTPException(409, "Cannot cancel a published post")
    post.status = "cancelled"
    db.commit()
    return {"status": "cancelled"}
