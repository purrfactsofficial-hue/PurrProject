from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, Episode, ScheduledPost, get_db
from main import app

TEST_DB = "sqlite:///:memory:"


@pytest.fixture
def client_db():
    eng = create_engine(TEST_DB, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(Episode(id=1, number=1, topic="T", slug="t", category="space"))
        s.commit()

    def override():
        with Session(eng) as db:
            yield db

    app.dependency_overrides[get_db] = override
    yield TestClient(app), eng
    app.dependency_overrides.clear()


# ── publish now ───────────────────────────────────────────────────────────────


def test_publish_now_returns_202_and_sets_publishing(client_db):
    client, eng = client_db
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
    with Session(eng) as s:
        s.add(
            ScheduledPost(
                episode_id=1,
                language="en",
                platform="youtube",
                status="scheduled",
                scheduled_for=past,
            )
        )
        s.commit()
        post_id = s.query(ScheduledPost).first().id

    with patch("routes.schedule_publish.publish_post_by_id"):
        resp = client.post(f"/schedule/{post_id}/publish")

    assert resp.status_code == 202
    assert resp.json()["status"] == "publishing"


def test_publish_now_returns_404_for_missing_post(client_db):
    client, _ = client_db
    resp = client.post("/schedule/9999/publish")
    assert resp.status_code == 404


def test_publish_now_rejects_already_published(client_db):
    client, eng = client_db
    with Session(eng) as s:
        s.add(
            ScheduledPost(
                episode_id=1,
                language="en",
                platform="youtube",
                status="published",
                scheduled_for=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        s.commit()
        post_id = s.query(ScheduledPost).first().id

    resp = client.post(f"/schedule/{post_id}/publish")
    assert resp.status_code == 409


# ── health ────────────────────────────────────────────────────────────────────


def test_health_returns_12_channels(client_db):
    client, _ = client_db
    resp = client.get("/schedule/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "channels" in data
    assert len(data["channels"]) == 12  # 4 langs × 3 platforms
    ch = data["channels"][0]
    assert set(ch.keys()) >= {"lang", "platform", "status", "detail"}
    assert ch["status"] in ("ok", "warning", "error")


def test_health_shows_error_for_unconfigured_youtube(client_db):
    client, _ = client_db
    resp = client.get("/schedule/health")
    channels = resp.json()["channels"]
    yt_en = next(c for c in channels if c["lang"] == "en" and c["platform"] == "youtube")
    # In test env, YOUTUBE_REFRESH_TOKEN_EN is empty → should be error
    assert yt_en["status"] == "error"


# ── retry resets retry_count ─────────────────────────────────────────────────


def test_retry_resets_retry_count(client_db):
    client, eng = client_db
    with Session(eng) as s:
        s.add(
            ScheduledPost(
                episode_id=1,
                language="en",
                platform="youtube",
                status="failed",
                retry_count=3,
                error_message="timeout",
                scheduled_for=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        s.commit()
        post_id = s.query(ScheduledPost).first().id

    resp = client.post(f"/schedule/{post_id}/retry")
    assert resp.status_code == 200
    with Session(eng) as s:
        post = s.query(ScheduledPost).filter_by(id=post_id).first()
        assert post.retry_count == 0
        assert post.status == "scheduled"
