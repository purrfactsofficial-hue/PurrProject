"""Unit tests for main.py — app setup, lifespan, health endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok():
    """GET /health returns 200 {"status": "ok"}."""
    with patch("main.create_tables"):
        import main  # noqa: PLC0415 — intentional deferred import

        with TestClient(main.app) as client:
            resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_lifespan_calls_create_tables():
    """create_tables() is invoked during app startup."""
    with patch("main.create_tables") as mock_create:
        import main  # noqa: PLC0415

        with TestClient(main.app):
            pass  # just enter/exit the lifespan

    mock_create.assert_called()
