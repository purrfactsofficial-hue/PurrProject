import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, Caption, Video
from services.caption_importer import ImportResult, import_captions

TEST_DB = "sqlite:///:memory:"

VALID_CAPTIONS = {
    "schema_version": "1.0",
    "episode": "Pizza",
    "episode_number": 9,
    "languages": {
        "en": {
            "youtube": {"title": "Pizza title EN", "description": "Pizza desc EN", "hashtags": ["#KidsLearning", "#Shorts", "#PurrFacts"]},
            "tiktok": {"caption": "Pizza tiktok EN", "hashtags": ["#PurrFacts"]},
            "instagram": {"caption": "Pizza ig EN", "hashtags": ["#A", "#B", "#C", "#D", "#PurrFacts"]},
        },
        "uk": {
            "youtube": {"title": "Pizza title UK", "description": "Pizza desc UK", "hashtags": ["#НавчанняДляДітей", "#Shorts", "#PurrFacts"]},
            "tiktok": {"caption": "Pizza tiktok UK", "hashtags": ["#PurrFacts"]},
            "instagram": {"caption": "Pizza ig UK", "hashtags": ["#A", "#B", "#C", "#D", "#PurrFacts"]},
        },
        "zh": {
            "youtube": {"title": "Pizza title ZH", "description": "Pizza desc ZH", "hashtags": ["#兒童教育", "#Shorts", "#PurrFacts"]},
            "tiktok": {"caption": "Pizza tiktok ZH", "hashtags": ["#PurrFacts"]},
            "instagram": {"caption": "Pizza ig ZH", "hashtags": ["#A", "#B", "#C", "#D", "#PurrFacts"]},
        },
        "fr": {
            "youtube": {"title": "Pizza title FR", "description": "Pizza desc FR", "hashtags": ["#ApprendreEnSamusant", "#Shorts", "#PurrFacts"]},
            "tiktok": {"caption": "Pizza tiktok FR", "hashtags": ["#PurrFacts"]},
            "instagram": {"caption": "Pizza ig FR", "hashtags": ["#A", "#B", "#C", "#D", "#PurrFacts"]},
        },
    },
}


@pytest.fixture()
def db():
    eng = create_engine(TEST_DB, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(Video(
            id=1, episode_num=9, name="Pizza", slug="episode-9-pizza",
            folder_path="/fake", languages='["en","uk","zh","fr"]',
            status="draft", scanned_at=datetime.now(timezone.utc),
        ))
        s.commit()
        yield s


def _write(folder: Path, data: dict) -> None:
    (folder / "captions.json").write_text(json.dumps(data), encoding="utf-8")


def test_valid_import_returns_12(tmp_path, db):
    _write(tmp_path, VALID_CAPTIONS)
    result = import_captions(str(tmp_path), 1, db)
    db.commit()
    assert result.imported == 12
    assert result.skipped_manual == 0
    assert result.errors == []
    assert db.query(Caption).count() == 12


def test_reimport_overwrites_skill_rows(tmp_path, db):
    _write(tmp_path, VALID_CAPTIONS)
    import_captions(str(tmp_path), 1, db)
    db.commit()
    modified = json.loads(json.dumps(VALID_CAPTIONS))
    modified["languages"]["en"]["youtube"]["title"] = "Updated Title"
    _write(tmp_path, modified)
    result = import_captions(str(tmp_path), 1, db)
    db.commit()
    assert result.imported == 12
    row = db.query(Caption).filter_by(video_id=1, language="en", platform="youtube").first()
    assert row.title == "Updated Title"


def test_manual_row_skipped_on_reimport(tmp_path, db):
    _write(tmp_path, VALID_CAPTIONS)
    import_captions(str(tmp_path), 1, db)
    db.commit()
    row = db.query(Caption).filter_by(video_id=1, language="en", platform="tiktok").first()
    row.caption = "My hand-edit"
    row.source = "manual"
    db.commit()
    result = import_captions(str(tmp_path), 1, db)
    db.commit()
    assert result.skipped_manual == 1
    assert result.imported == 11
    row = db.query(Caption).filter_by(video_id=1, language="en", platform="tiktok").first()
    assert row.caption == "My hand-edit"


def test_force_overwrites_manual_rows(tmp_path, db):
    _write(tmp_path, VALID_CAPTIONS)
    import_captions(str(tmp_path), 1, db)
    db.commit()
    row = db.query(Caption).filter_by(video_id=1, language="en", platform="tiktok").first()
    row.source = "manual"
    db.commit()
    result = import_captions(str(tmp_path), 1, db, force=True)
    assert result.skipped_manual == 0
    assert result.imported == 12


def test_missing_file_returns_error(tmp_path, db):
    result = import_captions(str(tmp_path), 1, db)
    assert result.errors
    assert "captions.json" in result.errors[0]
    assert db.query(Caption).count() == 0


def test_malformed_json_returns_error(tmp_path, db):
    (tmp_path / "captions.json").write_text("{bad json", encoding="utf-8")
    result = import_captions(str(tmp_path), 1, db)
    assert result.errors
    assert "parse" in result.errors[0].lower() or "line" in result.errors[0].lower()
    assert db.query(Caption).count() == 0


def test_missing_language_block_returns_error(tmp_path, db):
    bad = json.loads(json.dumps(VALID_CAPTIONS))
    del bad["languages"]["uk"]
    _write(tmp_path, bad)
    result = import_captions(str(tmp_path), 1, db)
    assert result.errors
    assert "uk" in result.errors[0]
    assert db.query(Caption).count() == 0


def test_instagram_wrong_hashtag_count_returns_error(tmp_path, db):
    bad = json.loads(json.dumps(VALID_CAPTIONS))
    bad["languages"]["fr"]["instagram"]["hashtags"] = ["#A", "#B", "#C", "#PurrFacts"]
    _write(tmp_path, bad)
    result = import_captions(str(tmp_path), 1, db)
    assert result.errors
    assert "fr/instagram" in result.errors[0]
    assert db.query(Caption).count() == 0


def test_missing_purrfacts_adds_warning(tmp_path, db):
    warn = json.loads(json.dumps(VALID_CAPTIONS))
    warn["languages"]["en"]["tiktok"]["hashtags"] = ["#FunFacts"]
    _write(tmp_path, warn)
    result = import_captions(str(tmp_path), 1, db)
    assert result.errors == []
    assert result.imported == 12
    assert any("en/tiktok" in w and "#PurrFacts" in w for w in result.warnings)


def test_unknown_extra_field_ignored(tmp_path, db):
    extra = json.loads(json.dumps(VALID_CAPTIONS))
    extra["notes"] = "some extra field"
    _write(tmp_path, extra)
    result = import_captions(str(tmp_path), 1, db)
    assert result.errors == []
    assert result.imported == 12


def test_bom_prefix_returns_error(tmp_path, db):
    content = json.dumps(VALID_CAPTIONS).encode("utf-8-sig")
    (tmp_path / "captions.json").write_bytes(content)
    result = import_captions(str(tmp_path), 1, db)
    assert result.errors
    assert "BOM" in result.errors[0] or "UTF-8" in result.errors[0] or "parse" in result.errors[0].lower()
