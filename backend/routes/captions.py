from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Caption, Video, get_db
from services.caption_importer import import_captions

router = APIRouter(prefix="/captions", tags=["captions"])


class CaptionOut(BaseModel):
    id: int
    language: str
    platform: str
    title: str | None
    caption: str
    hashtags: list[str]
    source: str

    model_config = {"from_attributes": True}


class SaveBody(BaseModel):
    video_id: int
    language: str
    platform: str
    title: str | None = None
    caption: str
    hashtags: list[str]


@router.post("/import/{video_id}")
def import_captions_route(
    video_id: int,
    force: bool = Query(False),
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if video is None:
        raise HTTPException(404, detail="Video not found")
    result = import_captions(video.folder_path, video_id, db, force=force)
    payload = {
        "imported": result.imported,
        "skipped_manual": result.skipped_manual,
        "warnings": result.warnings,
        "errors": result.errors,
    }
    if result.errors:
        return JSONResponse(status_code=422, content=payload)
    video.status = "ready"
    db.commit()
    return payload


@router.get("/{video_id}", response_model=list[CaptionOut])
def get_captions(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if video is None:
        raise HTTPException(404, detail="Video not found")
    rows = db.query(Caption).filter(Caption.video_id == video_id).all()
    return [
        CaptionOut(
            id=r.id,
            language=r.language,
            platform=r.platform,
            title=r.title,
            caption=r.caption,
            hashtags=r.hashtags.split() if r.hashtags else [],
            source=r.source,
        )
        for r in rows
    ]


@router.post("/save")
def save_caption(body: SaveBody, db: Session = Depends(get_db)):
    row = (
        db.query(Caption)
        .filter_by(video_id=body.video_id, language=body.language, platform=body.platform)
        .first()
    )
    if row is None:
        raise HTTPException(404, detail="Caption not found. Import first.")
    row.title = body.title
    row.caption = body.caption
    row.hashtags = " ".join(body.hashtags)
    row.source = "manual"
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "saved"}
