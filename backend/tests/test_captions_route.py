import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, Caption, Video, get_db
from routes.captions import router

TEST_DB = "sqlite:///:memory:"

IMPORT_OK = {
    "schema_version": "1.0",
    "episode": "Pizza",
    "languages": {
        lang: {
            "youtube": {
                "title": f"T {lang}",
                "description": f"D {lang}",
                "hashtags": ["#A", "#Shorts", "#PurrFacts"],
            },
            "tiktok": {"caption": f"C {lang}", "hashtags": ["#PurrFacts"]},
            "instagram": {
                "caption": f"I {lang}",
                "hashtags": ["#A", "#B", "#C", "#D", "#PurrFacts"],
            },
        }
        for lang in ["en", "uk", "zh", "fr"]
    },
}


@pytest.fixture()
def client(tmp_path):
    eng = create_engine(TEST_DB, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)

    app = FastAPI()
    app.include_router(router)

    def _db():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_db] = _db

    with Session(eng) as s:
        s.add(
            Video(
                id=1,
                episode_num=9,
                name="Pizza",
                slug="episode-9-pizza",
                folder_path=str(tmp_path),
                languages='["en","uk","zh","fr"]',
                status="draft",
                scanned_at=datetime.now(UTC),
            )
        )
        s.commit()

    with TestClient(app) as c:
        yield c, eng, tmp_path

    Base.metadata.drop_all(eng)


def _write(folder: Path, data: dict) -> None:
    (folder / "captions.json").write_text(json.dumps(data), encoding="utf-8")


def test_import_valid_returns_12(client):
    c, _, folder = client
    _write(folder, IMPORT_OK)
    resp = c.post("/captions/import/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 12
    assert data["errors"] == []


def test_import_missing_file_returns_422(client):
    c, _, _ = client
    resp = c.post("/captions/import/1")
    assert resp.status_code == 422
    assert resp.json()["errors"]


def test_import_unknown_video_returns_404(client):
    c, _, _ = client
    resp = c.post("/captions/import/999")
    assert resp.status_code == 404


def test_import_sets_video_status_ready(client):
    c, eng, folder = client
    _write(folder, IMPORT_OK)
    c.post("/captions/import/1")
    with Session(eng) as s:
        assert s.query(Video).first().status == "ready"


def test_get_captions_returns_rows(client):
    c, _, folder = client
    _write(folder, IMPORT_OK)
    c.post("/captions/import/1")
    resp = c.get("/captions/1")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 12
    yt_en = next(r for r in rows if r["language"] == "en" and r["platform"] == "youtube")
    assert yt_en["title"] == "T en"
    assert yt_en["hashtags"] == ["#A", "#Shorts", "#PurrFacts"]
    assert yt_en["source"] == "skill"


def test_get_captions_empty_before_import(client):
    c, _, _ = client
    resp = c.get("/captions/1")
    assert resp.status_code == 200
    assert resp.json() == []


def test_save_caption_marks_manual(client):
    c, eng, folder = client
    _write(folder, IMPORT_OK)
    c.post("/captions/import/1")
    resp = c.post(
        "/captions/save",
        json={
            "video_id": 1,
            "language": "en",
            "platform": "tiktok",
            "caption": "My edit",
            "hashtags": ["#PurrFacts"],
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "saved"}
    with Session(eng) as s:
        row = s.query(Caption).filter_by(video_id=1, language="en", platform="tiktok").first()
        assert row.caption == "My edit"
        assert row.source == "manual"


def test_save_caption_not_found_returns_404(client):
    c, _, _ = client
    resp = c.post(
        "/captions/save",
        json={
            "video_id": 1,
            "language": "en",
            "platform": "tiktok",
            "caption": "X",
            "hashtags": ["#PurrFacts"],
        },
    )
    assert resp.status_code == 404


def test_reimport_skips_manual_row(client):
    c, _, folder = client
    _write(folder, IMPORT_OK)
    c.post("/captions/import/1")
    c.post(
        "/captions/save",
        json={
            "video_id": 1,
            "language": "en",
            "platform": "tiktok",
            "caption": "My edit",
            "hashtags": ["#PurrFacts"],
        },
    )
    resp = c.post("/captions/import/1")
    assert resp.json()["skipped_manual"] == 1
    rows = c.get("/captions/1").json()
    tiktok_en = next(r for r in rows if r["language"] == "en" and r["platform"] == "tiktok")
    assert tiktok_en["caption"] == "My edit"
    assert tiktok_en["source"] == "manual"


def test_reimport_force_overwrites_manual(client):
    c, _, folder = client
    _write(folder, IMPORT_OK)
    c.post("/captions/import/1")
    c.post(
        "/captions/save",
        json={
            "video_id": 1,
            "language": "en",
            "platform": "tiktok",
            "caption": "My edit",
            "hashtags": ["#PurrFacts"],
        },
    )
    resp = c.post("/captions/import/1?force=true")
    assert resp.json()["skipped_manual"] == 0
    assert resp.json()["imported"] == 12


def test_get_captions_unknown_video_returns_404(client):
    c, _, _ = client
    resp = c.get("/captions/9999")
    assert resp.status_code == 404
