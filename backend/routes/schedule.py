from datetime import UTC, datetime
from datetime import date as Date
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import POSTING_SLOTS
from database import Caption, Episode, ScheduledPost, get_db

router = APIRouter(prefix="/schedule", tags=["schedule"])

_TZ_LABELS: dict[str, str] = {
    "en": "New York",
    "uk": "Kyiv",
    "zh": "Hong Kong",
    "fr": "Paris",
}
_USER_TZ = "America/Los_Angeles"


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
def get_slots(episode_id: int = Query(...), date: Date = Query(...)):  # noqa: B008
    post_date = date
    slots = []
    for lang, (_hour, _minute, _tz_name) in POSTING_SLOTS.items():
        utc_dt = compute_utc_slot(post_date, lang)
        pacific_dt = utc_dt.replace(tzinfo=UTC).astimezone(ZoneInfo(_USER_TZ))
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
