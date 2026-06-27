"""Mocked unit tests covering uncovered branches in services/caption_importer.py.

Lines targeted: 27, 68-70, 74-75, 87, 93, 101-104, 107-108, 113, 119, 135.
"""

import json
from unittest.mock import MagicMock, patch

import jsonschema

from services.caption_importer import (
    ImportResult,
    _custom_checks,
    _custom_warnings,
    _schema_error_message,
    import_captions,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_LANGS = ["en", "uk", "zh", "fr"]
_ALL_PLATFORMS = ["youtube", "tiktok", "instagram"]


def _valid_lang_block(title: str = "Title", hashtag_count: int = 5) -> dict:
    """Return a fully-valid language block."""
    ig_tags = [f"#Tag{i}" for i in range(hashtag_count)]
    return {
        "youtube": {
            "title": title,
            "description": "Some description",
            "hashtags": ["#PurrFacts", "#Shorts", "#KidsLearning"],
        },
        "tiktok": {
            "caption": "Tiktok caption",
            "hashtags": ["#PurrFacts"],
        },
        "instagram": {
            "caption": "IG caption",
            "hashtags": ig_tags,
        },
    }


def _full_valid_data() -> dict:
    return {
        "languages": {lang: _valid_lang_block() for lang in _ALL_LANGS},
    }


# ---------------------------------------------------------------------------
# ImportResult.ok  (line 27)
# ---------------------------------------------------------------------------


def test_import_result_ok_true():
    """.ok is True when there are no errors."""
    result = ImportResult()
    assert result.ok is True


def test_import_result_ok_false():
    """.ok is False when errors have been recorded."""
    result = ImportResult(errors=["something went wrong"])
    assert result.ok is False


# ---------------------------------------------------------------------------
# SchemaError branch  (lines 68-70)
# ---------------------------------------------------------------------------


def test_import_captions_schema_error(tmp_path):
    """jsonschema.SchemaError is caught and recorded as an import error."""
    captions_file = tmp_path / "captions.json"
    captions_file.write_text(
        json.dumps({"schema_version": "1.0", "episode": "Test", "languages": {}}),
        encoding="utf-8",
    )
    db = MagicMock()

    with patch(
        "services.caption_importer.jsonschema.validate",
        side_effect=jsonschema.SchemaError("broken schema"),
    ):
        result = import_captions(str(tmp_path), 1, db)

    assert result.errors
    assert "Internal schema error" in result.errors[0]
    assert not result.ok


# ---------------------------------------------------------------------------
# _custom_checks blocking import  (lines 74-75)
# ---------------------------------------------------------------------------


def test_import_captions_custom_checks_block(tmp_path):
    """When _custom_checks finds errors, import_captions returns early with those errors."""
    captions_file = tmp_path / "captions.json"
    # Data with only 'en' — _custom_checks will flag missing uk/zh/fr
    data = {
        "schema_version": "1.0",
        "episode": "Test",
        "languages": {"en": _valid_lang_block()},
    }
    captions_file.write_text(json.dumps(data), encoding="utf-8")
    db = MagicMock()

    # Bypass schema validation so _custom_checks gets to run
    with patch("services.caption_importer.jsonschema.validate"):
        result = import_captions(str(tmp_path), 1, db)

    assert result.errors
    assert any("uk" in e or "zh" in e or "fr" in e for e in result.errors)
    # db.add must NOT have been called — import was blocked
    db.add.assert_not_called()


# ---------------------------------------------------------------------------
# _schema_error_message  (lines 87, 93)
# ---------------------------------------------------------------------------


class _FakeValidationError:
    """Minimal stand-in for jsonschema.ValidationError."""

    def __init__(self, absolute_path, validator, message):
        self.absolute_path = absolute_path
        self.validator = validator
        self.message = message


def test_schema_error_message_const_validator():
    """Returns the version-mismatch message when validator=='const'. (line 87)"""
    exc = _FakeValidationError(absolute_path=[], validator="const", message="Expected 1.0")
    msg = _schema_error_message(exc, "", {"schema_version": "2.0"})
    assert "1.x" in msg
    assert "2.0" in msg


def test_schema_error_message_schema_version_in_path():
    """Returns the version-mismatch message when 'schema_version' is in absolute_path."""
    exc = _FakeValidationError(
        absolute_path=["schema_version"], validator="required", message="const check"
    )
    msg = _schema_error_message(exc, "schema_version", {"schema_version": "3.0"})
    assert "1.x" in msg


def test_schema_error_message_empty_path():
    """Returns bare exc.message when path is empty/falsy. (line 93)"""
    exc = _FakeValidationError(
        absolute_path=[], validator="required", message="field X is required"
    )
    msg = _schema_error_message(exc, "", {})
    assert msg == "field X is required"


# ---------------------------------------------------------------------------
# _custom_checks — missing language block  (lines 101-104)
# ---------------------------------------------------------------------------


def test_custom_checks_missing_language_block():
    """Produces an error for each language block absent from the data."""
    data = {
        "languages": {
            "en": _valid_lang_block(),
            # uk, zh, fr missing
        }
    }
    errors = _custom_checks(data)
    langs_in_errors = {e.split("`")[1] for e in errors if "missing" in e}
    assert "uk" in langs_in_errors
    assert "zh" in langs_in_errors
    assert "fr" in langs_in_errors


# ---------------------------------------------------------------------------
# _custom_checks — missing platform block  (lines 107-108)
# ---------------------------------------------------------------------------


def test_custom_checks_missing_platform_block():
    """Produces an error when a platform block is absent from a lang block."""
    data = _full_valid_data()
    # Remove instagram from 'en'
    del data["languages"]["en"]["instagram"]
    errors = _custom_checks(data)
    assert any("en" in e and "instagram" in e for e in errors)


# ---------------------------------------------------------------------------
# _custom_checks — instagram hashtag count != 5  (line 113)
# ---------------------------------------------------------------------------


def test_custom_checks_instagram_wrong_hashtag_count():
    """Produces an error when instagram has fewer than 5 hashtags."""
    data = _full_valid_data()
    data["languages"]["en"]["instagram"]["hashtags"] = ["#A", "#B", "#C", "#PurrFacts"]
    errors = _custom_checks(data)
    assert any("en/instagram" in e and "hashtag" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# _custom_checks — youtube title too long  (line 119)
# ---------------------------------------------------------------------------


def test_custom_checks_youtube_title_too_long():
    """Produces an error when a youtube title exceeds 100 characters."""
    data = _full_valid_data()
    data["languages"]["fr"]["youtube"]["title"] = "X" * 101
    errors = _custom_checks(data)
    assert any("fr/youtube" in e and "101" in e for e in errors)


# ---------------------------------------------------------------------------
# _custom_warnings — youtube missing #Shorts  (line 135)
# ---------------------------------------------------------------------------


def test_custom_warnings_youtube_missing_shorts():
    """Produces a warning when youtube hashtags omit #Shorts."""
    data = _full_valid_data()
    # Replace #Shorts with something else in all youtube blocks
    for lang in _ALL_LANGS:
        data["languages"][lang]["youtube"]["hashtags"] = ["#PurrFacts", "#KidsLearning", "#Edu"]
    warnings = _custom_warnings(data)
    shorts_warnings = [w for w in warnings if "Shorts" in w]
    assert len(shorts_warnings) == 4  # one per language
    assert all("youtube" in w for w in shorts_warnings)
