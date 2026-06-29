from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import Episode, Video, get_db

router = APIRouter(prefix="/media", tags=["media"])

_VALID_LANGUAGES = {"en", "uk", "zh", "fr"}


@router.get("/{episode_id}/{language}.mp4")
def stream_episode_media(episode_id: int, language: str, db: Session = Depends(get_db)):  # noqa: B008
    if language not in _VALID_LANGUAGES:
        raise HTTPException(400, f"Invalid language: {language}")
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(404, "Episode not found")
    video = db.query(Video).filter(Video.episode_num == episode.number).first()
    if not video:
        raise HTTPException(404, "No video file found for this episode")
    lang_dir = Path(video.folder_path) / "output" / language
    mp4s = sorted(lang_dir.glob("*FULL*.mp4"))
    if not mp4s:
        raise HTTPException(404, f"No {language} video file found")
    return FileResponse(mp4s[0], media_type="video/mp4")
