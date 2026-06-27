import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import Video, get_db
from services.video_scanner import scan_episodes

router = APIRouter(prefix="/videos", tags=["videos"])


class EpisodeOut(BaseModel):
    id: int
    episode_num: int
    name: str
    slug: str
    folder_path: str
    primary_file: str | None = None
    duration_secs: float | None = None
    size_bytes: int | None = None
    thumbnail_path: str | None = None
    languages: list[str] = []
    status: str
    scanned_at: str | None = None

    model_config = {"from_attributes": True}


class PagedResponse(BaseModel):
    items: list[EpisodeOut]
    total: int
    page: int
    pages: int
    per_page: int


def _to_out(v: Video) -> EpisodeOut:
    return EpisodeOut(
        id=v.id,
        episode_num=v.episode_num,
        name=v.name,
        slug=v.slug,
        folder_path=v.folder_path,
        primary_file=v.primary_file,
        duration_secs=v.duration_secs,
        size_bytes=v.size_bytes,
        thumbnail_path=v.thumbnail_path,
        languages=json.loads(v.languages or "[]"),
        status=v.status,
        scanned_at=v.scanned_at.isoformat() if v.scanned_at else None,
    )


@router.get("/scan", response_model=PagedResponse)
def scan(db: Annotated[Session, Depends(get_db)]) -> PagedResponse:
    episodes = scan_episodes(settings.video_repo_path, settings.thumbs_dir)
    now = datetime.now(UTC)

    for ep in episodes:
        has_captions = ep.get("has_captions", False)
        new_status = "ready" if has_captions else "draft"
        existing = db.query(Video).filter(Video.slug == ep["slug"]).first()
        if existing:
            for key in (
                "episode_num",
                "name",
                "folder_path",
                "primary_file",
                "duration_secs",
                "size_bytes",
                "thumbnail_path",
            ):
                setattr(existing, key, ep[key])
            existing.languages = json.dumps(ep["languages"])
            existing.scanned_at = now
            if existing.status not in ("scheduled", "published", "failed", "ready"):
                existing.status = new_status
        else:
            db.add(
                Video(
                    episode_num=ep["episode_num"],
                    name=ep["name"],
                    slug=ep["slug"],
                    folder_path=ep["folder_path"],
                    primary_file=ep["primary_file"],
                    duration_secs=ep["duration_secs"],
                    size_bytes=ep["size_bytes"],
                    thumbnail_path=ep["thumbnail_path"],
                    languages=json.dumps(ep["languages"]),
                    status=new_status,
                    scanned_at=now,
                )
            )

    db.commit()

    all_videos = db.query(Video).order_by(Video.episode_num).all()
    total = len(all_videos)
    return PagedResponse(
        items=[_to_out(v) for v in all_videos],
        total=total,
        page=1,
        pages=1,
        per_page=max(total, 1),
    )


@router.get("/list", response_model=PagedResponse)
def list_videos(
    db: Annotated[Session, Depends(get_db)],
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=100),
) -> PagedResponse:
    q = db.query(Video)
    if status:
        q = q.filter(Video.status == status)
    total = q.count()
    pages = max(1, math.ceil(total / per_page))
    items = q.order_by(Video.episode_num).offset((page - 1) * per_page).limit(per_page).all()
    return PagedResponse(
        items=[_to_out(v) for v in items],
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
    )


@router.get("/{video_id}", response_model=EpisodeOut)
def get_video(
    video_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> EpisodeOut:
    v = db.query(Video).filter(Video.id == video_id).first()
    if v is None:
        raise HTTPException(404, detail="Video not found")
    return _to_out(v)


@router.get("/{video_id}/stream")
def stream_video(
    video_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    v = db.query(Video).filter(Video.id == video_id).first()
    if v is None:
        raise HTTPException(404, detail="Video not found")
    if not v.primary_file:
        raise HTTPException(404, detail="No video file for this episode")
    path = Path(v.primary_file)
    if not path.exists():
        raise HTTPException(404, detail="Video file not found on disk")
    return FileResponse(path, media_type="video/mp4")
