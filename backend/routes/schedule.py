from datetime import UTC, datetime
from datetime import date as Date
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from config import POSTING_SLOTS

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
