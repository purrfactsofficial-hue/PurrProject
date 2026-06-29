from datetime import datetime

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


def _create_post(
    eng, episode_id=1, lang="en", plat="youtube", status="scheduled", scheduled_for=None
):
    sf = scheduled_for or datetime(2025, 7, 5, 0, 0, 0)
    with Session(eng) as s:
        p = ScheduledPost(
            episode_id=episode_id, language=lang, platform=plat, status=status, scheduled_for=sf
        )
        s.add(p)
        s.commit()
        return p.id


# ── GET /queue ────────────────────────────────────────────────────────────────


def test_get_queue_returns_items_sorted_by_scheduled_for(client):
    c, eng = client
    _create_post(eng, scheduled_for=datetime(2025, 7, 5, 0, 0, 0))
    _create_post(eng, lang="uk", scheduled_for=datetime(2025, 7, 4, 17, 0, 0))
    resp = c.get("/schedule/queue")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    # uk slot (17:00) comes before en slot (next day 00:00)
    assert items[0]["language"] == "uk"
    assert items[1]["language"] == "en"


def test_get_queue_includes_episode_name(client):
    c, eng = client
    _create_post(eng)
    resp = c.get("/schedule/queue")
    items = resp.json()["items"]
    assert items[0]["episode_name"] == "Pizza"


def test_get_queue_empty_returns_empty_list(client):
    c, _ = client
    resp = c.get("/schedule/queue")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ── DELETE /{id} ──────────────────────────────────────────────────────────────


def test_cancel_scheduled_post(client):
    c, eng = client
    pid = _create_post(eng)
    resp = c.delete(f"/schedule/{pid}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    with Session(eng) as s:
        assert s.query(ScheduledPost).get(pid).status == "cancelled"


def test_cancel_published_post_returns_409(client):
    c, eng = client
    pid = _create_post(eng, status="published")
    resp = c.delete(f"/schedule/{pid}")
    assert resp.status_code == 409


def test_cancel_nonexistent_post_returns_404(client):
    c, _ = client
    resp = c.delete("/schedule/9999")
    assert resp.status_code == 404


# ── POST /{id}/retry ──────────────────────────────────────────────────────────


def test_retry_failed_post_resets_to_scheduled(client):
    c, eng = client
    pid = _create_post(eng, status="failed")
    resp = c.post(f"/schedule/{pid}/retry")
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"
    with Session(eng) as s:
        assert s.query(ScheduledPost).get(pid).status == "scheduled"


def test_retry_non_failed_post_returns_409(client):
    c, eng = client
    pid = _create_post(eng, status="scheduled")
    resp = c.post(f"/schedule/{pid}/retry")
    assert resp.status_code == 409


def test_retry_nonexistent_post_returns_404(client):
    c, _ = client
    resp = c.post("/schedule/9999/retry")
    assert resp.status_code == 404


# ── PATCH /{id} ───────────────────────────────────────────────────────────────


def test_reschedule_post_updates_scheduled_for(client):
    c, eng = client
    pid = _create_post(eng, lang="en", scheduled_for=datetime(2025, 7, 5, 0, 0, 0))
    resp = c.patch(f"/schedule/{pid}", json={"date": "2025-08-01"})
    assert resp.status_code == 200
    with Session(eng) as s:
        post = s.query(ScheduledPost).get(pid)
        # Aug 1 — EDT: 8 PM Eastern = 00:00 UTC Aug 2
        assert post.scheduled_for == datetime(2025, 8, 2, 0, 0, 0)


def test_reschedule_published_post_returns_409(client):
    c, eng = client
    pid = _create_post(eng, status="published")
    resp = c.patch(f"/schedule/{pid}", json={"date": "2025-08-01"})
    assert resp.status_code == 409


def test_reschedule_nonexistent_post_returns_404(client):
    c, _ = client
    resp = c.patch("/schedule/9999", json={"date": "2025-08-01"})
    assert resp.status_code == 404


# ── PATCH /episode/{id} ───────────────────────────────────────────────────────


def test_reschedule_episode_moves_all_scheduled_posts(client):
    c, eng = client
    # Create 3 scheduled posts for episode 1 across different languages
    _create_post(eng, lang="en", scheduled_for=datetime(2025, 7, 5, 0, 0, 0))
    _create_post(eng, lang="uk", plat="tiktok", scheduled_for=datetime(2025, 7, 4, 17, 0, 0))
    _create_post(eng, lang="fr", plat="instagram", scheduled_for=datetime(2025, 7, 4, 18, 0, 0))
    resp = c.patch("/schedule/episode/1", json={"date": "2025-12-15"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["moved"] == 3
    assert "posts" in data
    assert len(data["posts"]) == 3
    # Check that each post has the required fields
    for post in data["posts"]:
        assert "id" in post
        assert "episode_id" in post
        assert "episode_name" in post
        assert "language" in post
        assert "platform" in post
        assert "status" in post
        assert "scheduled_for" in post
    with Session(eng) as s:
        posts = s.query(ScheduledPost).all()
        # All should have new Dec 15 slots
        slots = {p.scheduled_for for p in posts}
        assert datetime(2025, 12, 16, 1, 0, 0) in slots  # EN winter
        assert datetime(2025, 12, 15, 18, 0, 0) in slots  # UK winter
        assert datetime(2025, 12, 15, 19, 0, 0) in slots  # FR winter


def test_reschedule_episode_skips_non_scheduled_posts(client):
    c, eng = client
    _create_post(eng, lang="en", status="published")
    _create_post(eng, lang="uk", status="scheduled")
    resp = c.patch("/schedule/episode/1", json={"date": "2025-12-15"})
    data = resp.json()
    assert data["moved"] == 1  # only the scheduled one
    assert len(data["posts"]) == 1  # and posts list should have 1 item


def test_reschedule_episode_no_posts_returns_404(client):
    c, _ = client
    resp = c.patch("/schedule/episode/1", json={"date": "2025-12-15"})
    assert resp.status_code == 404
