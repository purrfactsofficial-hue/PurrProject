"""Unit tests for the stream video endpoint (routes/videos.py lines 144–157)."""

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from database import get_db
from routes.videos import router


def _make_app(mock_db: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app, raise_server_exceptions=False)


def test_stream_video_not_found():
    """Returns 404 when the video_id is not in the database."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    client = _make_app(db)
    resp = client.get("/videos/999/stream")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_stream_no_primary_file():
    """Returns 404 when the video row has no primary_file."""
    db = MagicMock()
    video = MagicMock()
    video.primary_file = None
    db.query.return_value.filter.return_value.first.return_value = video
    client = _make_app(db)
    resp = client.get("/videos/1/stream")
    assert resp.status_code == 404
    assert "No video file" in resp.json()["detail"]


def test_stream_file_missing_on_disk(tmp_path):
    """Returns 404 when primary_file is set but the file does not exist on disk."""
    db = MagicMock()
    video = MagicMock()
    video.primary_file = str(tmp_path / "nonexistent.mp4")
    db.query.return_value.filter.return_value.first.return_value = video
    client = _make_app(db)
    resp = client.get("/videos/1/stream")
    assert resp.status_code == 404
    assert "not found on disk" in resp.json()["detail"]


def test_stream_returns_file(tmp_path):
    """Returns 200 with video content when the file exists."""
    video_file = tmp_path / "episode.mp4"
    video_file.write_bytes(b"\x00" * 16)  # minimal fake mp4 bytes

    db = MagicMock()
    video = MagicMock()
    video.primary_file = str(video_file)
    db.query.return_value.filter.return_value.first.return_value = video
    client = _make_app(db)
    resp = client.get("/videos/1/stream")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("video/mp4")
