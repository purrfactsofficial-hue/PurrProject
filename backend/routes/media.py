from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import Episode, Video, get_db

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{episode_id}.mp4")
def stream_episode_media(episode_id: int, db: Session = Depends(get_db)):  # noqa: B008
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(404, "Episode not found")
    video = db.query(Video).filter(Video.episode_num == episode.number).first()
    if not video or not video.primary_file:
        raise HTTPException(404, "No video file found for this episode")
    path = Path(video.primary_file)
    if not path.is_file():
        raise HTTPException(404, f"File not found: {path}")
    return FileResponse(path, media_type="video/mp4")
