from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, Video, get_db
from routes.videos import router

TEST_DB = "sqlite:///:memory:"


@pytest.fixture()
def client():
    eng = create_engine(
        TEST_DB,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)

    app = FastAPI()
    app.include_router(router)

    def _db():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_db] = _db

    with TestClient(app) as c:
        yield c, eng

    Base.metadata.drop_all(eng)


FAKE_SCAN = [
    {
        "episode_num": 9, "name": "Pizza", "slug": "episode-9-pizza",
        "folder_path": "/purr/Episode 9 - Pizza",
        "primary_file": "/purr/Episode 9 - Pizza/output/en/Episode_9___Pizza_FULL.mp4",
        "duration_secs": 44.0, "size_bytes": 17_600_000,
        "thumbnail_path": "/thumbs/episode-9-pizza.jpg",
        "languages": ["en", "fr", "uk", "zh"], "status": "new",
    }
]


@patch("routes.videos.scan_episodes", return_value=FAKE_SCAN)
def test_scan_returns_episodes(mock_scan, client):
    c, _ = client
    resp = c.get("/videos/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Pizza"
    assert data["items"][0]["languages"] == ["en", "fr", "uk", "zh"]


@patch("routes.videos.scan_episodes", return_value=FAKE_SCAN)
def test_scan_persists_to_db(mock_scan, client):
    c, eng = client
    c.get("/videos/scan")
    with Session(eng) as s:
        assert s.query(Video).count() == 1
        assert s.query(Video).first().slug == "episode-9-pizza"


@patch("routes.videos.scan_episodes", return_value=FAKE_SCAN)
def test_scan_upsert_does_not_duplicate(mock_scan, client):
    c, eng = client
    c.get("/videos/scan")
    c.get("/videos/scan")
    with Session(eng) as s:
        assert s.query(Video).count() == 1


@patch("routes.videos.scan_episodes", return_value=FAKE_SCAN)
def test_scan_does_not_reset_status(mock_scan, client):
    c, eng = client
    c.get("/videos/scan")
    # Simulate Phase 2+ updating status
    with Session(eng) as s:
        v = s.query(Video).first()
        v.status = "scheduled"
        s.commit()
    c.get("/videos/scan")
    with Session(eng) as s:
        assert s.query(Video).first().status == "scheduled"


def _seed(eng, count: int, status: str = "new") -> None:
    with Session(eng) as s:
        for i in range(1, count + 1):
            s.add(Video(
                episode_num=i, name=f"Ep{i}", slug=f"ep-{i}",
                folder_path=f"/p/{i}", languages='["en"]',
                status=status, scanned_at=datetime.utcnow(),
            ))
        s.commit()


def test_list_default_pagination(client):
    c, eng = client
    _seed(eng, 15)
    data = c.get("/videos/list").json()
    assert data["total"] == 15
    assert data["pages"] == 2
    assert data["page"] == 1
    assert len(data["items"]) == 12


def test_list_page_2(client):
    c, eng = client
    _seed(eng, 15)
    data = c.get("/videos/list?page=2").json()
    assert len(data["items"]) == 3
    assert data["page"] == 2


def test_list_filter_by_status(client):
    c, eng = client
    _seed(eng, 5, status="new")
    with Session(eng) as s:
        for i in range(6, 9):
            s.add(Video(
                episode_num=i, name=f"Ep{i}", slug=f"ep-{i}",
                folder_path=f"/p/{i}", languages='["en"]',
                status="published", scanned_at=datetime.utcnow(),
            ))
        s.commit()

    assert c.get("/videos/list?status=new").json()["total"] == 5
    assert c.get("/videos/list?status=published").json()["total"] == 3
    assert c.get("/videos/list").json()["total"] == 8


def test_list_invalid_page_returns_422(client):
    c, _ = client
    assert c.get("/videos/list?page=0").status_code == 422
