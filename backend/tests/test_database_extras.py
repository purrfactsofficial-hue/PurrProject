"""Mocked unit tests for database.py uncovered lines (53, 57-58)."""

from unittest.mock import MagicMock, patch


def test_create_tables_calls_metadata_create_all():
    """create_tables() delegates to Base.metadata.create_all(engine). (line 53)"""
    with patch("database.Base.metadata.create_all") as mock_create_all:
        from database import create_tables  # noqa: PLC0415

        create_tables()

    mock_create_all.assert_called_once()


def test_get_db_yields_a_session():
    """get_db() is a generator that yields a Session. (lines 57-58)"""
    mock_session = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_session)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    with patch("database.Session", return_value=mock_ctx):
        from database import get_db  # noqa: PLC0415

        gen = get_db()
        session = next(gen)

    assert session is mock_session
