from datetime import date, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, Caption, Episode, get_db
from routes.schedule import compute_utc_slot, router

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


# ── compute_utc_slot ──────────────────────────────────────────────────────────


def test_compute_utc_slot_summer_en():
    # July 4 — EDT (UTC-4): 8 PM Eastern = 00:00 UTC next day
    assert compute_utc_slot(date(2025, 7, 4), "en") == datetime(2025, 7, 5, 0, 0, 0)


def test_compute_utc_slot_summer_uk():
    # July 4 — EEST (UTC+3): 8 PM Kyiv = 17:00 UTC
    assert compute_utc_slot(date(2025, 7, 4), "uk") == datetime(2025, 7, 4, 17, 0, 0)


def test_compute_utc_slot_summer_zh():
    # July 4 — HKT (UTC+8): 8 PM HK = 12:00 UTC
    assert compute_utc_slot(date(2025, 7, 4), "zh") == datetime(2025, 7, 4, 12, 0, 0)


def test_compute_utc_slot_summer_fr():
    # July 4 — CEST (UTC+2): 8 PM Paris = 18:00 UTC
    assert compute_utc_slot(date(2025, 7, 4), "fr") == datetime(2025, 7, 4, 18, 0, 0)


def test_compute_utc_slot_winter_en():
    # Dec 15 — EST (UTC-5): 8 PM Eastern = 01:00 UTC next day
    assert compute_utc_slot(date(2025, 12, 15), "en") == datetime(2025, 12, 16, 1, 0, 0)


def test_compute_utc_slot_winter_uk():
    # Dec 15 — EET (UTC+2): 8 PM Kyiv = 18:00 UTC
    assert compute_utc_slot(date(2025, 12, 15), "uk") == datetime(2025, 12, 15, 18, 0, 0)


def test_compute_utc_slot_winter_zh():
    # Dec 15 — HKT (UTC+8, no DST): 8 PM HK = 12:00 UTC
    assert compute_utc_slot(date(2025, 12, 15), "zh") == datetime(2025, 12, 15, 12, 0, 0)


def test_compute_utc_slot_winter_fr():
    # Dec 15 — CET (UTC+1): 8 PM Paris = 19:00 UTC
    assert compute_utc_slot(date(2025, 12, 15), "fr") == datetime(2025, 12, 15, 19, 0, 0)


# ── GET /slots ────────────────────────────────────────────────────────────────


def test_get_slots_returns_four_entries(client):
    c, _ = client
    resp = c.get("/schedule/slots?episode_id=1&date=2025-07-04")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["slots"]) == 4
    langs = {s["language"] for s in data["slots"]}
    assert langs == {"en", "uk", "zh", "fr"}


def test_get_slots_audience_time_always_8pm(client):
    c, _ = client
    resp = c.get("/schedule/slots?episode_id=1&date=2025-07-04")
    for slot in resp.json()["slots"]:
        assert slot["audience_time"] == "8:00 PM"


def test_get_slots_your_time_is_pacific(client):
    c, _ = client
    resp = c.get("/schedule/slots?episode_id=1&date=2025-07-04")
    for slot in resp.json()["slots"]:
        assert slot["your_tz"] == "Pacific"
        # Your time must be a valid time string like "10:00 AM" or "5:00 PM"
        assert " AM" in slot["your_time"] or " PM" in slot["your_time"]
