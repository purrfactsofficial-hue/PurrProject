import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, Caption, Episode, ScheduledPost, get_db
from routes.schedule import router

TEST_DB = "sqlite:///:memory:"


@pytest.fixture()
def client():
    eng = create_engine(TEST_DB, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)

    app = FastAPI()
    app.include_router(router)

    def _db():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_db] = _db

    with Session(eng) as s:
        s.add(Episode(id=1, number=9, topic="Pizza", slug="pizza", category="food", status="ready"))
        for lang in ["en", "uk", "zh", "fr"]:
            for plat in ["youtube", "tiktok", "instagram"]:
                s.add(
                    Caption(
                        episode_id=1,
                        language=lang,
                        platform=plat,
                        body=f"Cap {lang}/{plat}",
                        hashtags=[],
                    )
                )
        s.commit()

    with TestClient(app) as c:
        yield c, eng

    Base.metadata.drop_all(eng)


# ── POST /create ──────────────────────────────────────────────────────────────

_FUTURE_DATE = "2027-07-04"  # always in the future relative to test execution


def test_create_schedule_happy_path(client):
    c, eng = client
    resp = c.post(
        "/schedule/create",
        json={
            "episode_id": 1,
            "date": _FUTURE_DATE,
            "languages": ["en", "uk"],
            "platforms": ["youtube", "tiktok"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 4  # 2 langs × 2 platforms
    assert data["warnings"] == []
    with Session(eng) as s:
        assert s.query(ScheduledPost).count() == 4


def test_create_schedule_missing_caption_returns_409(client):
    c, eng = client
    # Remove en/youtube caption to simulate missing cell
    with Session(eng) as s:
        s.query(Caption).filter_by(episode_id=1, language="en", platform="youtube").delete()
        s.commit()
    resp = c.post(
        "/schedule/create",
        json={
            "episode_id": 1,
            "date": _FUTURE_DATE,
            "languages": ["en"],
            "platforms": ["youtube"],
        },
    )
    assert resp.status_code == 409
    assert "en/youtube" in resp.json()["detail"]
    # Nothing should have been scheduled
    with Session(eng) as s:
        assert s.query(ScheduledPost).count() == 0


def test_create_schedule_past_slot_excluded(client):
    c, _ = client
    # Use a date far in the past so every slot has passed
    resp = c.post(
        "/schedule/create",
        json={
            "episode_id": 1,
            "date": "2020-01-01",
            "languages": ["en"],
            "platforms": ["youtube"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 0
    assert any("already passed" in e for e in data["errors"])


def test_create_schedule_double_booking_warns(client):
    c, eng = client
    # Schedule once
    c.post(
        "/schedule/create",
        json={
            "episode_id": 1,
            "date": _FUTURE_DATE,
            "languages": ["en"],
            "platforms": ["youtube"],
        },
    )
    # Schedule same lang/platform/date again (different call, same slot)
    resp = c.post(
        "/schedule/create",
        json={
            "episode_id": 1,
            "date": _FUTURE_DATE,
            "languages": ["en"],
            "platforms": ["youtube"],
        },
    )
    assert resp.status_code == 200
    assert any("already has a post" in w for w in resp.json()["warnings"])


def test_create_schedule_unknown_episode_returns_404(client):
    c, _ = client
    resp = c.post(
        "/schedule/create",
        json={
            "episode_id": 999,
            "date": _FUTURE_DATE,
            "languages": ["en"],
            "platforms": ["youtube"],
        },
    )
    assert resp.status_code == 404


def test_create_schedule_english_only_creates_correct_count(client):
    c, eng = client
    resp = c.post(
        "/schedule/create",
        json={
            "episode_id": 1,
            "date": _FUTURE_DATE,
            "languages": ["en"],
            "platforms": ["youtube", "tiktok", "instagram"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 3
    with Session(eng) as s:
        posts = s.query(ScheduledPost).all()
        assert all(p.language == "en" for p in posts)
