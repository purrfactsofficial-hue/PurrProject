# Phase 2 — Caption Import & Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import `captions.json` (written by the `/purrfacts-scenario` skill) into the platform's database, display all 12 cells in an editable 4×3 grid, and let the user save manual edits.

**Architecture:** The backend gains a `captions` DB table, a pure-function importer service, and three `/captions` routes. The frontend gets a real Episode page (replacing the stub) with a CaptionGrid component. Status transitions ("Draft" / "Captions ready") are driven by the scanner's `has_captions` flag and the import route.

**Tech Stack:** FastAPI + SQLAlchemy 2 (SQLite) + pytest/httpx · React 18 + React Router 6 + Vite

## Global Constraints

- `jsonschema` package must be added to `backend/requirements.txt`
- All 12 import cells (4 langs × 3 platforms) upsert atomically — zero rows written if any validation error
- `source = "manual"` rows survive re-import unless `force=True`
- `#PurrFacts` missing → warning (not error); Instagram ≠ 5 hashtags → error
- Status values already defined in `StatusTag.jsx`: `"new"` | `"draft"` | `"ready"` | `"scheduled"` | `"published"` | `"failed"`
- Design tokens in `frontend/src/tokens.css`: `--paper`, `--paper-2`, `--ink`, `--ink-soft`, `--yarn`, `--pink`, `--pink-deep`, `--gold`, `--line`, `--ok`, `--radius`, `--font-display`, `--font-body`
- No emojis in code; no comments explaining WHAT the code does
- Run all backend tests from `backend/` directory: `pytest tests/ -v`

---

## File Map

| Path | Action | Responsibility |
|---|---|---|
| `backend/requirements.txt` | Modify | Add `jsonschema==4.23.0` |
| `backend/database.py` | Modify | Add `Caption` model + `ForeignKey`, `UniqueConstraint` imports |
| `backend/schemas/captions.schema.json` | Create | JSON Schema (from SPEC §5) the importer validates against |
| `backend/services/caption_importer.py` | Create | `import_captions()` — load, validate, upsert 12 rows |
| `backend/routes/captions.py` | Replace | `POST /captions/import/{video_id}`, `GET /captions/{video_id}`, `POST /captions/save` |
| `backend/services/video_scanner.py` | Modify | Add `has_captions` flag to scan result |
| `backend/routes/videos.py` | Modify | Use `has_captions` for status; add `GET /videos/{id}` and `GET /videos/{id}/stream` |
| `backend/tests/test_caption_importer.py` | Create | Unit tests for importer (in-memory SQLite) |
| `backend/tests/test_captions_route.py` | Create | Route tests for all three endpoints |
| `backend/tests/test_scanner.py` | Modify | Add `has_captions` tests |
| `frontend/src/App.jsx` | Modify | Add `/episode/:id` route |
| `frontend/src/api.js` | Modify | Add `post()`, `getVideo()`, `importCaptions()`, `getCaptions()`, `saveCaption()` |
| `frontend/src/pages/Library.jsx` | Modify | Wrap VideoCards in `<Link to="/episode/{id}">` |
| `frontend/src/pages/Episode.jsx` | Replace | Full episode page: header, video preview, import button, grid, footer |
| `frontend/src/pages/Episode.css` | Create | Episode page styles |
| `frontend/src/components/CaptionGrid.jsx` | Create | 4×3 editable grid with per-cell auto-save |
| `frontend/src/components/CaptionGrid.css` | Create | Grid layout + stitched cell style |

---

## Task 1: Caption DB Model + JSON Schema File

**Files:**
- Modify: `backend/database.py`
- Modify: `backend/requirements.txt`
- Create: `backend/schemas/captions.schema.json`

**Interfaces:**
- Produces: `Caption` SQLAlchemy model with columns `id`, `video_id`, `language`, `platform`, `title`, `caption`, `hashtags`, `source`, `updated_at`; unique constraint on `(video_id, language, platform)`

- [ ] **Step 1: Add jsonschema to requirements.txt**

Replace the contents of `backend/requirements.txt` with:

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
python-dotenv==1.0.1
apscheduler==3.10.4
pydantic-settings==2.5.2
pytest==8.3.3
httpx==0.27.2
jsonschema==4.23.0
```

- [ ] **Step 2: Install the new dependency**

Run: `pip install jsonschema==4.23.0`
Expected: `Successfully installed jsonschema-4.23.0` (or already satisfied)

- [ ] **Step 3: Add Caption model to database.py**

The full updated `backend/database.py`:

```python
import json
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from config import settings


class Base(DeclarativeBase):
    pass


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_num = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    folder_path = Column(Text, nullable=False)
    primary_file = Column(Text)
    duration_secs = Column(Float)
    size_bytes = Column(Integer)
    thumbnail_path = Column(Text)
    languages = Column(Text, default="[]")
    status = Column(Text, default="new")
    scanned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Caption(Base):
    __tablename__ = "captions"
    __table_args__ = (UniqueConstraint("video_id", "language", "platform"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    language = Column(Text, nullable=False)
    platform = Column(Text, nullable=False)
    title = Column(Text)
    caption = Column(Text, nullable=False)
    hashtags = Column(Text, nullable=False)
    source = Column(Text, nullable=False, default="skill")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


engine = create_engine(
    settings.database_url, connect_args={"check_same_thread": False}
)


def create_tables() -> None:
    Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
```

- [ ] **Step 4: Create backend/schemas/ directory and captions.schema.json**

Create `backend/schemas/captions.schema.json` with the exact schema from the spec:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version", "episode", "languages"],
  "properties": {
    "schema_version": { "type": "string", "const": "1.0" },
    "episode": { "type": "string", "minLength": 1 },
    "episode_number": { "type": "integer", "minimum": 0 },
    "topic_tags": {
      "type": "object",
      "properties": {
        "en": { "type": "string", "pattern": "^#" },
        "uk": { "type": "string", "pattern": "^#" },
        "zh": { "type": "string", "pattern": "^#" },
        "fr": { "type": "string", "pattern": "^#" }
      }
    },
    "languages": {
      "type": "object",
      "required": ["en", "uk", "zh", "fr"],
      "additionalProperties": false,
      "properties": {
        "en": { "$ref": "#/$defs/lang" },
        "uk": { "$ref": "#/$defs/lang" },
        "zh": { "$ref": "#/$defs/lang" },
        "fr": { "$ref": "#/$defs/lang" }
      }
    }
  },
  "$defs": {
    "hashtag": { "type": "string", "pattern": "^#\\S+$" },
    "lang": {
      "type": "object",
      "required": ["youtube", "tiktok", "instagram"],
      "properties": {
        "youtube": {
          "type": "object",
          "required": ["title", "description", "hashtags"],
          "properties": {
            "title": { "type": "string", "minLength": 1, "maxLength": 100 },
            "description": { "type": "string", "minLength": 1, "maxLength": 5000 },
            "hashtags": {
              "type": "array", "minItems": 3, "maxItems": 6,
              "items": { "$ref": "#/$defs/hashtag" },
              "allOf": [
                { "contains": { "const": "#Shorts" } },
                { "contains": { "const": "#PurrFacts" } }
              ]
            }
          }
        },
        "tiktok": {
          "type": "object",
          "required": ["caption", "hashtags"],
          "properties": {
            "caption": { "type": "string", "minLength": 1, "maxLength": 150 },
            "hashtags": {
              "type": "array", "minItems": 1, "maxItems": 5,
              "items": { "$ref": "#/$defs/hashtag" },
              "contains": { "const": "#PurrFacts" }
            }
          }
        },
        "instagram": {
          "type": "object",
          "required": ["caption", "hashtags"],
          "properties": {
            "caption": { "type": "string", "minLength": 1, "maxLength": 2200 },
            "hashtags": {
              "type": "array", "minItems": 5, "maxItems": 5,
              "items": { "$ref": "#/$defs/hashtag" },
              "contains": { "const": "#PurrFacts" }
            }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 5: Write the smoke test**

Create `backend/tests/test_db_model.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, Caption, Video


def _engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def test_caption_row_persists():
    eng = _engine()
    with Session(eng) as s:
        v = Video(
            episode_num=9, name="Pizza", slug="episode-9-pizza",
            folder_path="/fake", languages='["en"]', status="draft",
            scanned_at=datetime.now(timezone.utc),
        )
        s.add(v)
        s.flush()
        c = Caption(
            video_id=v.id, language="en", platform="youtube",
            title="Why Pizza Looks Like a Flag",
            caption="Did you know the first Margherita matched the Italian flag?",
            hashtags="#KidsLearning #Shorts #PurrFacts",
            source="skill",
            updated_at=datetime.now(timezone.utc),
        )
        s.add(c)
        s.commit()
        row = s.query(Caption).first()
        assert row.language == "en"
        assert row.platform == "youtube"
        assert row.source == "skill"


def test_caption_unique_constraint_enforced():
    import pytest
    from sqlalchemy.exc import IntegrityError
    eng = _engine()
    with Session(eng) as s:
        v = Video(
            episode_num=9, name="Pizza", slug="episode-9-pizza",
            folder_path="/fake", languages='["en"]', status="draft",
            scanned_at=datetime.now(timezone.utc),
        )
        s.add(v)
        s.flush()
        for _ in range(2):
            s.add(Caption(
                video_id=v.id, language="en", platform="youtube",
                title="T", caption="C", hashtags="#PurrFacts", source="skill",
                updated_at=datetime.now(timezone.utc),
            ))
        with pytest.raises(IntegrityError):
            s.commit()
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_db_model.py -v`
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/database.py backend/schemas/captions.schema.json backend/tests/test_db_model.py
git commit -m "feat: Caption DB model, JSON schema file, jsonschema dep"
```

---

## Task 2: caption_importer.py

**Files:**
- Create: `backend/services/caption_importer.py`
- Create: `backend/tests/test_caption_importer.py`

**Interfaces:**
- Consumes: `Caption` and `Video` from `database`; `Session` from `sqlalchemy.orm`
- Produces: `import_captions(episode_folder: str, video_id: int, db: Session, force: bool = False) -> ImportResult`
  - `ImportResult` has fields `imported: int`, `skipped_manual: int`, `warnings: list[str]`, `errors: list[str]`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_caption_importer.py`:

```python
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
    assert result.imported == 12
    assert result.skipped_manual == 0
    assert result.errors == []
    assert db.query(Caption).count() == 12


def test_reimport_overwrites_skill_rows(tmp_path, db):
    _write(tmp_path, VALID_CAPTIONS)
    import_captions(str(tmp_path), 1, db)
    modified = json.loads(json.dumps(VALID_CAPTIONS))
    modified["languages"]["en"]["youtube"]["title"] = "Updated Title"
    _write(tmp_path, modified)
    result = import_captions(str(tmp_path), 1, db)
    assert result.imported == 12
    row = db.query(Caption).filter_by(video_id=1, language="en", platform="youtube").first()
    assert row.title == "Updated Title"


def test_manual_row_skipped_on_reimport(tmp_path, db):
    _write(tmp_path, VALID_CAPTIONS)
    import_captions(str(tmp_path), 1, db)
    row = db.query(Caption).filter_by(video_id=1, language="en", platform="tiktok").first()
    row.caption = "My hand-edit"
    row.source = "manual"
    db.commit()
    result = import_captions(str(tmp_path), 1, db)
    assert result.skipped_manual == 1
    assert result.imported == 11
    row = db.query(Caption).filter_by(video_id=1, language="en", platform="tiktok").first()
    assert row.caption == "My hand-edit"


def test_force_overwrites_manual_rows(tmp_path, db):
    _write(tmp_path, VALID_CAPTIONS)
    import_captions(str(tmp_path), 1, db)
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
```

- [ ] **Step 2: Run tests to confirm all fail**

Run: `pytest tests/test_caption_importer.py -v`
Expected: ERROR or ImportError — `services/caption_importer.py` does not exist yet

- [ ] **Step 3: Implement caption_importer.py**

Create `backend/services/caption_importer.py`:

```python
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
from sqlalchemy.orm import Session

from database import Caption

_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "captions.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

_LANGS = ["en", "uk", "zh", "fr"]
_PLATFORMS = ["youtube", "tiktok", "instagram"]


@dataclass
class ImportResult:
    imported: int = 0
    skipped_manual: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def import_captions(
    episode_folder: str,
    video_id: int,
    db: Session,
    force: bool = False,
) -> ImportResult:
    result = ImportResult()
    folder = Path(episode_folder)
    captions_file = folder / "captions.json"

    if not captions_file.exists():
        result.errors.append(
            f"No captions.json in {folder.name}. "
            "Run /purrfacts-scenario for this episode, then Import."
        )
        return result

    raw = captions_file.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        result.errors.append(
            "captions.json has a UTF-8 BOM. Save the file as UTF-8 without BOM and re-import."
        )
        return result

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        result.errors.append(
            f"captions.json won't parse — line {exc.lineno}: {exc.msg}. Fix and re-import."
        )
        return result

    try:
        jsonschema.validate(data, _SCHEMA)
    except jsonschema.ValidationError as exc:
        path = "/".join(str(p) for p in exc.absolute_path)
        result.errors.append(_schema_error_message(exc, path, data))
        return result
    except jsonschema.SchemaError as exc:
        result.errors.append(f"Internal schema error: {exc.message}")
        return result

    custom_errors = _custom_checks(data)
    if custom_errors:
        result.errors.extend(custom_errors)
        return result

    result.warnings.extend(_custom_warnings(data))

    rows_to_write = _build_rows(data, video_id)
    _upsert_rows(rows_to_write, db, result, force)
    db.commit()
    return result


def _schema_error_message(exc: jsonschema.ValidationError, path: str, data: dict) -> str:
    schema_version = data.get("schema_version", "")
    if "schema_version" in exc.absolute_path or exc.validator == "const":
        return (
            f"captions.json is version {schema_version}; "
            "this platform reads 1.x. Update the skill or the platform."
        )
    if path:
        return f"`{path}`: {exc.message}"
    return exc.message


def _custom_checks(data: dict) -> list[str]:
    errors = []
    langs = data.get("languages", {})
    for lang in _LANGS:
        if lang not in langs:
            errors.append(
                f"captions.json is missing the `{lang}` block. Add it and re-import."
            )
            continue
        for platform in _PLATFORMS:
            if platform not in langs[lang]:
                errors.append(f"`{lang}` has no `{platform}` block.")
                continue
            block = langs[lang][platform]
            if platform == "instagram":
                count = len(block.get("hashtags", []))
                if count != 5:
                    errors.append(
                        f"`{lang}/instagram` has {count} hashtags; Instagram requires exactly 5."
                    )
            if platform == "youtube":
                title = block.get("title", "")
                if len(title) > 100:
                    errors.append(
                        f"`{lang}/youtube` title is {len(title)} chars (max 100)."
                    )
    return errors


def _custom_warnings(data: dict) -> list[str]:
    warnings = []
    langs = data.get("languages", {})
    for lang in _LANGS:
        for platform in _PLATFORMS:
            block = langs.get(lang, {}).get(platform, {})
            hashtags = block.get("hashtags", [])
            if "#PurrFacts" not in hashtags:
                warnings.append(f"`{lang}/{platform}` is missing #PurrFacts.")
            if platform == "youtube" and "#Shorts" not in hashtags:
                warnings.append(f"`{lang}/youtube` is missing #Shorts.")
    return warnings


def _build_rows(data: dict, video_id: int) -> list[dict]:
    rows = []
    for lang in _LANGS:
        lang_block = data["languages"][lang]
        for platform in _PLATFORMS:
            block = lang_block[platform]
            if platform == "youtube":
                title = block["title"]
                caption = block["description"]
            else:
                title = None
                caption = block["caption"]
            hashtags = " ".join(block["hashtags"])
            rows.append({
                "video_id": video_id,
                "language": lang,
                "platform": platform,
                "title": title,
                "caption": caption,
                "hashtags": hashtags,
            })
    return rows


def _upsert_rows(rows: list[dict], db: Session, result: ImportResult, force: bool) -> None:
    now = datetime.now(timezone.utc)
    for r in rows:
        existing = (
            db.query(Caption)
            .filter_by(video_id=r["video_id"], language=r["language"], platform=r["platform"])
            .first()
        )
        if existing is None:
            db.add(Caption(
                video_id=r["video_id"],
                language=r["language"],
                platform=r["platform"],
                title=r["title"],
                caption=r["caption"],
                hashtags=r["hashtags"],
                source="skill",
                updated_at=now,
            ))
            result.imported += 1
        elif existing.source == "manual" and not force:
            result.skipped_manual += 1
        else:
            existing.title = r["title"]
            existing.caption = r["caption"]
            existing.hashtags = r["hashtags"]
            existing.source = "skill"
            existing.updated_at = now
            result.imported += 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_caption_importer.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add backend/services/caption_importer.py backend/tests/test_caption_importer.py
git commit -m "feat: caption_importer service with full validation and upsert"
```

---

## Task 3: /captions Routes

**Files:**
- Replace: `backend/routes/captions.py`
- Create: `backend/tests/test_captions_route.py`

**Interfaces:**
- Consumes: `import_captions` from Task 2; `Caption`, `Video`, `get_db` from `database`
- Produces:
  - `POST /captions/import/{video_id}?force=false` → `{ imported, skipped_manual, warnings, errors }` (200) or same shape with errors (422)
  - `GET /captions/{video_id}` → `[{ id, language, platform, title, caption, hashtags: [str], source }]`
  - `POST /captions/save` body `{ video_id, language, platform, title?, caption, hashtags: [str] }` → `{ status: "saved" }`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_captions_route.py`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, Caption, Video, get_db
from routes.captions import router

TEST_DB = "sqlite:///:memory:"

IMPORT_OK = {
    "schema_version": "1.0", "episode": "Pizza",
    "languages": {
        lang: {
            "youtube": {"title": f"T {lang}", "description": f"D {lang}", "hashtags": ["#A", "#Shorts", "#PurrFacts"]},
            "tiktok": {"caption": f"C {lang}", "hashtags": ["#PurrFacts"]},
            "instagram": {"caption": f"I {lang}", "hashtags": ["#A", "#B", "#C", "#D", "#PurrFacts"]},
        }
        for lang in ["en", "uk", "zh", "fr"]
    },
}


@pytest.fixture()
def client(tmp_path):
    eng = create_engine(TEST_DB, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)

    app = FastAPI()
    app.include_router(router)

    def _db():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_db] = _db

    with Session(eng) as s:
        s.add(Video(
            id=1, episode_num=9, name="Pizza", slug="episode-9-pizza",
            folder_path=str(tmp_path), languages='["en","uk","zh","fr"]',
            status="draft", scanned_at=datetime.now(timezone.utc),
        ))
        s.commit()

    with TestClient(app) as c:
        yield c, eng, tmp_path

    Base.metadata.drop_all(eng)


def _write(folder: Path, data: dict) -> None:
    (folder / "captions.json").write_text(json.dumps(data), encoding="utf-8")


def test_import_valid_returns_12(client):
    c, _, folder = client
    _write(folder, IMPORT_OK)
    resp = c.post("/captions/import/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 12
    assert data["errors"] == []


def test_import_missing_file_returns_422(client):
    c, _, _ = client
    resp = c.post("/captions/import/1")
    assert resp.status_code == 422
    assert resp.json()["errors"]


def test_import_unknown_video_returns_404(client):
    c, _, _ = client
    resp = c.post("/captions/import/999")
    assert resp.status_code == 404


def test_import_sets_video_status_ready(client):
    c, eng, folder = client
    _write(folder, IMPORT_OK)
    c.post("/captions/import/1")
    with Session(eng) as s:
        assert s.query(Video).first().status == "ready"


def test_get_captions_returns_rows(client):
    c, _, folder = client
    _write(folder, IMPORT_OK)
    c.post("/captions/import/1")
    resp = c.get("/captions/1")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 12
    yt_en = next(r for r in rows if r["language"] == "en" and r["platform"] == "youtube")
    assert yt_en["title"] == "T en"
    assert yt_en["hashtags"] == ["#A", "#Shorts", "#PurrFacts"]
    assert yt_en["source"] == "skill"


def test_get_captions_empty_before_import(client):
    c, _, _ = client
    resp = c.get("/captions/1")
    assert resp.status_code == 200
    assert resp.json() == []


def test_save_caption_marks_manual(client):
    c, eng, folder = client
    _write(folder, IMPORT_OK)
    c.post("/captions/import/1")
    resp = c.post("/captions/save", json={
        "video_id": 1, "language": "en", "platform": "tiktok",
        "caption": "My edit", "hashtags": ["#PurrFacts"],
    })
    assert resp.status_code == 200
    assert resp.json() == {"status": "saved"}
    with Session(eng) as s:
        row = s.query(Caption).filter_by(video_id=1, language="en", platform="tiktok").first()
        assert row.caption == "My edit"
        assert row.source == "manual"


def test_save_caption_not_found_returns_404(client):
    c, _, _ = client
    resp = c.post("/captions/save", json={
        "video_id": 1, "language": "en", "platform": "tiktok",
        "caption": "X", "hashtags": ["#PurrFacts"],
    })
    assert resp.status_code == 404


def test_reimport_skips_manual_row(client):
    c, _, folder = client
    _write(folder, IMPORT_OK)
    c.post("/captions/import/1")
    c.post("/captions/save", json={
        "video_id": 1, "language": "en", "platform": "tiktok",
        "caption": "My edit", "hashtags": ["#PurrFacts"],
    })
    resp = c.post("/captions/import/1")
    assert resp.json()["skipped_manual"] == 1
    rows = c.get("/captions/1").json()
    tiktok_en = next(r for r in rows if r["language"] == "en" and r["platform"] == "tiktok")
    assert tiktok_en["caption"] == "My edit"
    assert tiktok_en["source"] == "manual"


def test_reimport_force_overwrites_manual(client):
    c, _, folder = client
    _write(folder, IMPORT_OK)
    c.post("/captions/import/1")
    c.post("/captions/save", json={
        "video_id": 1, "language": "en", "platform": "tiktok",
        "caption": "My edit", "hashtags": ["#PurrFacts"],
    })
    resp = c.post("/captions/import/1?force=true")
    assert resp.json()["skipped_manual"] == 0
    assert resp.json()["imported"] == 12
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/test_captions_route.py -v`
Expected: ERRORS — `router` doesn't have the real routes yet

- [ ] **Step 3: Implement the routes**

Replace `backend/routes/captions.py` entirely:

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Caption, Video, get_db
from services.caption_importer import import_captions

router = APIRouter(prefix="/captions", tags=["captions"])


class CaptionOut(BaseModel):
    id: int
    language: str
    platform: str
    title: str | None
    caption: str
    hashtags: list[str]
    source: str

    model_config = {"from_attributes": True}


class SaveBody(BaseModel):
    video_id: int
    language: str
    platform: str
    title: str | None = None
    caption: str
    hashtags: list[str]


@router.post("/import/{video_id}")
def import_captions_route(
    video_id: int,
    force: bool = Query(False),
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if video is None:
        raise HTTPException(404, detail="Video not found")
    result = import_captions(video.folder_path, video_id, db, force=force)
    payload = {
        "imported": result.imported,
        "skipped_manual": result.skipped_manual,
        "warnings": result.warnings,
        "errors": result.errors,
    }
    if result.errors:
        return JSONResponse(status_code=422, content=payload)
    video.status = "ready"
    db.commit()
    return payload


@router.get("/{video_id}", response_model=list[CaptionOut])
def get_captions(video_id: int, db: Session = Depends(get_db)):
    rows = db.query(Caption).filter(Caption.video_id == video_id).all()
    return [
        CaptionOut(
            id=r.id,
            language=r.language,
            platform=r.platform,
            title=r.title,
            caption=r.caption,
            hashtags=r.hashtags.split() if r.hashtags else [],
            source=r.source,
        )
        for r in rows
    ]


@router.post("/save")
def save_caption(body: SaveBody, db: Session = Depends(get_db)):
    row = (
        db.query(Caption)
        .filter_by(video_id=body.video_id, language=body.language, platform=body.platform)
        .first()
    )
    if row is None:
        raise HTTPException(404, detail="Caption not found. Import first.")
    row.title = body.title
    row.caption = body.caption
    row.hashtags = " ".join(body.hashtags)
    row.source = "manual"
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "saved"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_captions_route.py -v`
Expected: 11 passed

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/routes/captions.py backend/tests/test_captions_route.py
git commit -m "feat: /captions import, get, and save routes"
```

---

## Task 4: Scanner has_captions Flag + Status Update

**Files:**
- Modify: `backend/services/video_scanner.py`
- Modify: `backend/routes/videos.py`
- Modify: `backend/tests/test_scanner.py`

**Interfaces:**
- `scan_episodes()` now includes `"has_captions": bool` in every returned dict
- `videos.py` scan route uses `has_captions` to set initial status and update existing episodes

- [ ] **Step 1: Write failing tests for the scanner**

Add these tests at the bottom of `backend/tests/test_scanner.py`:

```python
def test_scan_detects_captions_json_present(tmp_path):
    _make_ep(tmp_path, "Episode 9 - Pizza", ["en"])
    (tmp_path / "Episode 9 - Pizza" / "captions.json").write_text("{}", encoding="utf-8")
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()
    with patch("services.video_scanner.subprocess.run") as mock_run:
        mock_run.side_effect = [FAKE_FFPROBE, FAKE_FFMPEG]
        results = scan_episodes(tmp_path, thumbs)
    assert results[0]["has_captions"] is True


def test_scan_detects_captions_json_absent(tmp_path):
    _make_ep(tmp_path, "Episode 9 - Pizza", ["en"])
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()
    with patch("services.video_scanner.subprocess.run") as mock_run:
        mock_run.side_effect = [FAKE_FFPROBE, FAKE_FFMPEG]
        results = scan_episodes(tmp_path, thumbs)
    assert results[0]["has_captions"] is False
```

- [ ] **Step 2: Run new tests to confirm they fail**

Run: `pytest tests/test_scanner.py::test_scan_detects_captions_json_present tests/test_scanner.py::test_scan_detects_captions_json_absent -v`
Expected: FAILED — `has_captions` key missing

- [ ] **Step 3: Add has_captions to video_scanner.py**

In `backend/services/video_scanner.py`, update the `episodes.append(...)` block (lines 84–96):

```python
        episodes.append({
            "episode_num": episode_num,
            "name": name,
            "slug": slug,
            "folder_path": str(entry),
            "primary_file": str(primary) if primary else None,
            "duration_secs": duration,
            "size_bytes": size,
            "thumbnail_path": thumb_path,
            "languages": detect_languages(entry),
            "has_captions": (entry / "captions.json").exists(),
            "status": "new",
        })
```

- [ ] **Step 4: Run scanner tests**

Run: `pytest tests/test_scanner.py -v`
Expected: all pass

- [ ] **Step 5: Update videos.py scan route to use has_captions**

In `backend/routes/videos.py`, replace the upsert block inside the `scan()` function (the `for ep in episodes:` loop):

```python
    for ep in episodes:
        has_captions = ep.get("has_captions", False)
        new_status = "ready" if has_captions else "draft"
        existing = db.query(Video).filter(Video.slug == ep["slug"]).first()
        if existing:
            for key in ("episode_num", "name", "folder_path", "primary_file",
                        "duration_secs", "size_bytes", "thumbnail_path"):
                setattr(existing, key, ep[key])
            existing.languages = json.dumps(ep["languages"])
            existing.scanned_at = now
            if existing.status not in ("scheduled", "published", "failed"):
                existing.status = new_status
        else:
            db.add(Video(
                episode_num=ep["episode_num"],
                name=ep["name"],
                slug=ep["slug"],
                folder_path=ep["folder_path"],
                primary_file=ep["primary_file"],
                duration_secs=ep["duration_secs"],
                size_bytes=ep["size_bytes"],
                thumbnail_path=ep["thumbnail_path"],
                languages=json.dumps(ep["languages"]),
                status=new_status,
                scanned_at=now,
            ))
```

- [ ] **Step 6: Update existing scan test that checks status is preserved**

The existing test `test_scan_does_not_reset_status` checks that "scheduled" status is preserved — this still holds. But the FAKE_SCAN dict in `test_videos_route.py` doesn't have `has_captions`. Update `FAKE_SCAN` in `backend/tests/test_videos_route.py`:

```python
FAKE_SCAN = [
    {
        "episode_num": 9, "name": "Pizza", "slug": "episode-9-pizza",
        "folder_path": "/purr/Episode 9 - Pizza",
        "primary_file": "/purr/Episode 9 - Pizza/output/en/Episode_9___Pizza_FULL.mp4",
        "duration_secs": 44.0, "size_bytes": 17_600_000,
        "thumbnail_path": "/thumbs/episode-9-pizza.jpg",
        "languages": ["en", "fr", "uk", "zh"],
        "has_captions": False,
        "status": "new",
    }
]
```

- [ ] **Step 7: Run full test suite**

Run: `pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add backend/services/video_scanner.py backend/routes/videos.py backend/tests/test_scanner.py backend/tests/test_videos_route.py
git commit -m "feat: scanner has_captions flag, scan route drives draft/ready status"
```

---

## Task 5: GET /videos/{id} + Stream + Frontend Wiring

**Files:**
- Modify: `backend/routes/videos.py` — add `GET /videos/{id}` and `GET /videos/{id}/stream`
- Modify: `frontend/src/api.js` — add `post()`, `getVideo()`, `importCaptions()`, `getCaptions()`, `saveCaption()`
- Modify: `frontend/src/App.jsx` — add `/episode/:id` route
- Modify: `frontend/src/pages/Library.jsx` — wrap VideoCards in `<Link>`

**Interfaces:**
- `GET /videos/{id}` → same `EpisodeOut` shape as in the list
- `GET /videos/{id}/stream` → streaming `video/mp4` (FileResponse)
- `importCaptions(videoId, force?)` → always returns parsed JSON (caller checks `.errors`)
- `saveCaption({ videoId, language, platform, title, caption, hashtags })` → `{ status: "saved" }`

- [ ] **Step 1: Add /videos/{id} and /videos/{id}/stream to videos.py**

At the end of `backend/routes/videos.py`, after the `list_videos` function, add:

```python
from fastapi import HTTPException
from fastapi.responses import FileResponse


@router.get("/{video_id}", response_model=EpisodeOut)
def get_video(
    video_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> EpisodeOut:
    v = db.query(Video).filter(Video.id == video_id).first()
    if v is None:
        raise HTTPException(404, detail="Video not found")
    return _to_out(v)


@router.get("/{video_id}/stream")
def stream_video(
    video_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    v = db.query(Video).filter(Video.id == video_id).first()
    if v is None:
        raise HTTPException(404, detail="Video not found")
    if not v.primary_file:
        raise HTTPException(404, detail="No video file for this episode")
    path = Path(v.primary_file)
    if not path.exists():
        raise HTTPException(404, detail="Video file not found on disk")
    return FileResponse(path, media_type="video/mp4")
```

Also add `Path` to the existing imports at the top of `videos.py`:

```python
from pathlib import Path
```

And add `HTTPException` and `FileResponse` to their respective imports (FastAPI and fastapi.responses).

Note: `HTTPException` is already likely in scope from FastAPI. Check — if not, add: `from fastapi import APIRouter, Depends, HTTPException, Query`
And add: `from fastapi.responses import FileResponse`

- [ ] **Step 2: Write a quick route test for GET /videos/{id}**

Add to `backend/tests/test_videos_route.py`:

```python
def test_get_video_by_id(client):
    c, eng = client
    with Session(eng) as s:
        s.add(Video(
            episode_num=9, name="Pizza", slug="episode-9-pizza",
            folder_path="/fake", languages='["en"]',
            status="draft", scanned_at=datetime.now(timezone.utc),
        ))
        s.commit()
        vid_id = s.query(Video).first().id
    resp = c.get(f"/videos/{vid_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Pizza"


def test_get_video_not_found(client):
    c, _ = client
    assert c.get("/videos/9999").status_code == 404
```

- [ ] **Step 3: Run backend tests**

Run: `pytest tests/ -v`
Expected: all pass

- [ ] **Step 4: Update frontend/src/api.js**

Replace the entire file:

```js
const BASE = '/api'

async function request(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: body != null ? { 'Content-Type': 'application/json' } : {},
    body: body != null ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok && res.status !== 422) throw Object.assign(new Error(`${res.status} ${res.statusText}`), { data })
  return data
}

export function scanVideos() {
  return request('/videos/scan')
}

export function listVideos({ status, page = 1, perPage = 12 } = {}) {
  const params = new URLSearchParams({ page, per_page: perPage })
  if (status) params.set('status', status)
  return request(`/videos/list?${params}`)
}

export function getVideo(id) {
  return request(`/videos/${id}`)
}

export function importCaptions(videoId, force = false) {
  return post(`/captions/import/${videoId}?force=${force}`)
}

export function getCaptions(videoId) {
  return request(`/captions/${videoId}`)
}

export function saveCaption({ videoId, language, platform, title = null, caption, hashtags }) {
  return post('/captions/save', { video_id: videoId, language, platform, title, caption, hashtags })
}
```

- [ ] **Step 5: Update frontend/src/App.jsx to add /episode/:id route**

Replace the contents of `frontend/src/App.jsx`:

```jsx
import { Route, Routes } from 'react-router-dom'
import Nav from './components/Nav.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Episode from './pages/Episode.jsx'
import Library from './pages/Library.jsx'
import Queue from './pages/Queue.jsx'
import Settings from './pages/Settings.jsx'
import './App.css'

export default function App() {
  return (
    <div className="app">
      <Nav />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Library />} />
          <Route path="/episode/:id" element={<Episode />} />
          <Route path="/queue" element={<Queue />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
```

- [ ] **Step 6: Make VideoCards clickable in Library.jsx**

In `frontend/src/pages/Library.jsx`, add the import at the top:

```jsx
import { Link } from 'react-router-dom'
```

Then in the grid's `episodes.map(...)` block (currently line ~126), wrap each VideoCard:

```jsx
episodes.map((ep) => (
  <Link key={ep.id} to={`/episode/${ep.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
    <VideoCard episode={ep} />
  </Link>
))
```

Remove the `key={ep.id}` from `<VideoCard>` since it moves to `<Link>`.

- [ ] **Step 7: Manual test — confirm Library cards navigate to Episode stub**

1. Start the backend: `cd backend && uvicorn main:app --reload`
2. Start the frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173`
4. Click any episode card → should navigate to `/episode/{id}` (currently shows stub text)
5. Confirm the URL changes and the stub page renders

- [ ] **Step 8: Commit**

```bash
git add backend/routes/videos.py backend/tests/test_videos_route.py frontend/src/api.js frontend/src/App.jsx frontend/src/pages/Library.jsx
git commit -m "feat: GET /videos/{id} + stream, frontend routing, Library card links"
```

---

## Task 6: Episode.jsx + CaptionGrid.jsx

**Files:**
- Replace: `frontend/src/pages/Episode.jsx`
- Create: `frontend/src/pages/Episode.css`
- Create: `frontend/src/components/CaptionGrid.jsx`
- Create: `frontend/src/components/CaptionGrid.css`

**Interfaces:**
- Consumes: `getVideo(id)`, `getCaptions(videoId)`, `importCaptions(videoId)`, `saveCaption({...})` from `api.js`
- `CaptionGrid` props: `videoId: number`, `captions: CaptionRow[]`
  - `CaptionRow`: `{ id, language, platform, title, caption, hashtags: string[], source }`

- [ ] **Step 1: Create CaptionGrid.css**

Create `frontend/src/components/CaptionGrid.css`:

```css
.caption-empty {
  padding: 40px;
  color: var(--ink-soft);
  font-style: italic;
  text-align: center;
}

.caption-grid-wrap {
  overflow-x: auto;
}

.caption-grid {
  display: grid;
  grid-template-columns: 60px repeat(3, 1fr);
  gap: 12px;
  min-width: 700px;
  padding: 8px 0;
}

.caption-grid-header {
  display: contents;
}

.grid-corner {
  /* empty top-left corner */
}

.platform-label {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-soft);
  text-align: center;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--line);
}

.caption-row {
  display: contents;
}

.lang-label {
  display: flex;
  align-items: flex-start;
  padding-top: 12px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
}

.caption-cell {
  background: var(--paper-2);
  border-radius: var(--radius);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 140px;
  position: relative;
}

.caption-cell.stitched {
  border: 2px dashed var(--line);
}

.caption-cell.edited {
  border-color: var(--gold);
}

.cell-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--ink-soft);
  text-transform: uppercase;
}

.cell-title {
  font-family: var(--font-body);
  font-size: 13px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 5px 8px;
  background: var(--paper);
  color: var(--ink);
  width: 100%;
  outline: none;
}

.cell-title:focus {
  border-color: var(--pink);
}

.cell-text {
  font-family: var(--font-body);
  font-size: 13px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 5px 8px;
  background: var(--paper);
  color: var(--ink);
  width: 100%;
  resize: vertical;
  outline: none;
  line-height: 1.5;
}

.cell-text:focus {
  border-color: var(--pink);
}

.char-count {
  font-size: 10px;
  color: var(--yarn);
  align-self: flex-end;
}

.hashtag-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 2px;
}

.hashtag-chip {
  font-size: 11px;
  background: var(--line);
  color: var(--ink-soft);
  border-radius: 20px;
  padding: 2px 8px;
}

.cell-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}

.edited-mark {
  font-size: 10px;
  color: var(--gold-deep);
  font-weight: 600;
  letter-spacing: 0.05em;
}

.saving-mark {
  font-size: 10px;
  color: var(--ink-soft);
}
```

- [ ] **Step 2: Create CaptionGrid.jsx**

Create `frontend/src/components/CaptionGrid.jsx`:

```jsx
import { useEffect, useRef, useState } from 'react'
import { saveCaption } from '../api.js'
import './CaptionGrid.css'

const LANGS = ['en', 'uk', 'zh', 'fr']
const PLATFORMS = ['youtube', 'tiktok', 'instagram']
const PLATFORM_LABELS = { youtube: 'YouTube', tiktok: 'TikTok', instagram: 'Instagram' }

function buildGrid(captions) {
  const g = {}
  for (const lang of LANGS) {
    g[lang] = {}
    for (const platform of PLATFORMS) {
      g[lang][platform] = null
    }
  }
  for (const c of captions) {
    if (g[c.language]) g[c.language][c.platform] = c
  }
  return g
}

function CaptionCell({ cell, videoId, language, platform }) {
  const [title, setTitle] = useState(cell?.title ?? '')
  const [text, setText] = useState(cell?.caption ?? '')
  const [saving, setSaving] = useState(false)
  const [isManual, setIsManual] = useState(cell?.source === 'manual')
  const dirty = useRef(false)

  useEffect(() => {
    setTitle(cell?.title ?? '')
    setText(cell?.caption ?? '')
    setIsManual(cell?.source === 'manual')
    dirty.current = false
  }, [cell])

  const handleSave = async () => {
    if (!dirty.current || !cell) return
    setSaving(true)
    try {
      await saveCaption({
        videoId,
        language,
        platform,
        title: platform === 'youtube' ? title : null,
        caption: text,
        hashtags: cell.hashtags,
      })
      setIsManual(true)
    } finally {
      setSaving(false)
      dirty.current = false
    }
  }

  if (!cell) {
    return <div className="caption-cell stitched" style={{ opacity: 0.4 }}>—</div>
  }

  const titleLimit = platform === 'youtube' ? 100 : null
  const textLimit = platform === 'tiktok' ? 150 : platform === 'instagram' ? 2200 : 5000

  return (
    <div className={`caption-cell stitched${isManual ? ' edited' : ''}`}>
      {platform === 'youtube' && (
        <>
          <span className="cell-label">Title</span>
          <input
            className="cell-title"
            value={title}
            maxLength={100}
            onChange={(e) => { setTitle(e.target.value); dirty.current = true }}
            onBlur={handleSave}
          />
          {titleLimit && <span className="char-count">{title.length}/{titleLimit}</span>}
          <span className="cell-label">Description</span>
        </>
      )}
      {platform !== 'youtube' && <span className="cell-label">Caption</span>}
      <textarea
        className="cell-text"
        value={text}
        rows={platform === 'youtube' ? 4 : 3}
        onChange={(e) => { setText(e.target.value); dirty.current = true }}
        onBlur={handleSave}
      />
      <span className="char-count">{text.length}/{textLimit}</span>
      <div className="hashtag-chips">
        {cell.hashtags.map((h) => <span key={h} className="hashtag-chip">{h}</span>)}
      </div>
      <div className="cell-footer">
        {isManual && <span className="edited-mark">edited</span>}
        {saving && <span className="saving-mark">saving…</span>}
      </div>
    </div>
  )
}

export default function CaptionGrid({ videoId, captions }) {
  if (!captions.length) {
    return (
      <p className="caption-empty">
        No descriptions imported. Click Import to pull them from this episode&apos;s captions.json.
      </p>
    )
  }

  const grid = buildGrid(captions)

  return (
    <div className="caption-grid-wrap">
      <div className="caption-grid">
        <div className="grid-corner" />
        {PLATFORMS.map((p) => (
          <div key={p} className="platform-label">{PLATFORM_LABELS[p]}</div>
        ))}
        {LANGS.map((lang) => (
          <div key={lang} className="caption-row">
            <span className="lang-label">{lang.toUpperCase()}</span>
            {PLATFORMS.map((platform) => (
              <CaptionCell
                key={platform}
                cell={grid[lang][platform]}
                videoId={videoId}
                language={lang}
                platform={platform}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create Episode.css**

Create `frontend/src/pages/Episode.css`:

```css
.episode-page {
  max-width: 1100px;
  padding: 32px 40px 60px;
}

.ep-header {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.back-btn {
  background: none;
  border: none;
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--ink-soft);
  cursor: pointer;
  padding: 6px 0;
  white-space: nowrap;
}

.back-btn:hover {
  color: var(--ink);
}

.ep-eyebrow {
  font-size: 12px;
  color: var(--ink-soft);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.ep-title {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 600;
  color: var(--ink);
}

.import-btn {
  margin-left: auto;
  background: var(--pink);
  color: white;
  border: none;
  border-radius: var(--radius);
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  padding: 10px 20px;
  cursor: pointer;
  white-space: nowrap;
}

.import-btn:hover {
  background: var(--pink-deep);
}

.import-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ep-video {
  width: 100%;
  max-width: 420px;
  border-radius: var(--radius);
  background: var(--ink);
  margin-bottom: 28px;
  display: block;
}

.import-result {
  border-radius: var(--radius);
  padding: 12px 16px;
  margin-bottom: 20px;
  font-size: 14px;
}

.import-result.ok {
  background: #eaf4ee;
  color: var(--ok);
  border: 1px solid #c0ddc9;
}

.import-result.error {
  background: #fdeeed;
  color: #b04040;
  border: 1px solid #f5c0bc;
}

.import-result p {
  margin: 0;
  line-height: 1.5;
}

.ep-section-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 500;
  color: var(--ink);
  margin-bottom: 16px;
}

.ep-footer {
  margin-top: 36px;
  display: flex;
  justify-content: flex-end;
}

.save-btn {
  background: var(--gold);
  color: var(--ink);
  border: none;
  border-radius: var(--radius);
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  padding: 12px 24px;
  cursor: pointer;
}

.save-btn:hover {
  background: var(--gold-deep);
  color: white;
}

.ep-loading,
.ep-error {
  padding: 40px;
  color: var(--ink-soft);
}

.ep-error {
  color: #b04040;
}
```

- [ ] **Step 4: Replace Episode.jsx**

Replace `frontend/src/pages/Episode.jsx` entirely:

```jsx
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getCaptions, getVideo, importCaptions } from '../api.js'
import CaptionGrid from '../components/CaptionGrid.jsx'
import './Episode.css'

export default function Episode() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [episode, setEpisode] = useState(null)
  const [captions, setCaptions] = useState([])
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getVideo(id)
      .then(setEpisode)
      .catch((err) => setError(err.message))
    getCaptions(id)
      .then(setCaptions)
      .catch(() => setCaptions([]))
  }, [id])

  const handleImport = async () => {
    setImporting(true)
    setImportResult(null)
    try {
      const result = await importCaptions(id)
      setImportResult(result)
      if (!result.errors?.length) {
        const updated = await getCaptions(id)
        setCaptions(updated)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setImporting(false)
    }
  }

  if (error) return <div className="ep-error">{error}</div>
  if (!episode) return <div className="ep-loading">Loading…</div>

  return (
    <div className="episode-page">
      <div className="ep-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Library</button>
        <div>
          <div className="ep-eyebrow">Episode {episode.episode_num}</div>
          <h1 className="ep-title">{episode.name}</h1>
        </div>
        <button className="import-btn" onClick={handleImport} disabled={importing}>
          {importing ? 'Importing…' : 'Import descriptions'}
        </button>
      </div>

      {episode.primary_file && (
        <video
          className="ep-video"
          src={`/api/videos/${id}/stream`}
          controls
          preload="metadata"
        />
      )}

      {importResult && (
        <div className={`import-result ${importResult.errors?.length ? 'error' : 'ok'}`}>
          {importResult.errors?.length ? (
            importResult.errors.map((e, i) => <p key={i}>{e}</p>)
          ) : (
            <p>
              Imported {importResult.imported} descriptions.
              {importResult.warnings?.map((w, i) => (
                <span key={i}> · {w}</span>
              ))}
            </p>
          )}
        </div>
      )}

      <h2 className="ep-section-title">Publishing descriptions</h2>
      <CaptionGrid videoId={parseInt(id, 10)} captions={captions} />

      <div className="ep-footer">
        <button className="save-btn" onClick={() => navigate('/queue')}>
          Save &amp; continue to scheduling →
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Manual test — full Episode page flow**

1. Ensure backend + frontend are running (`uvicorn main:app --reload` + `npm run dev`)
2. Navigate to Library → click an episode card → lands on Episode page
3. Verify: episode name, episode number display correctly
4. Click "Import descriptions" on an episode that has no `captions.json` → red error box with the "No captions.json..." message
5. Create a hand-written `captions.json` in one episode folder (use the worked example from `SPEC_captions_contract.md` §13)
6. Click "Import descriptions" for that episode → green "Imported 12 descriptions" message
7. Verify the 4×3 grid fills in with all languages and platforms
8. Edit one cell's text → blur out of the field → "saving…" flash → "edited" badge appears
9. Reload the page → edited cell still shows the edited text and "edited" badge
10. Click "Save & continue to scheduling →" → navigates to Queue page

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Episode.jsx frontend/src/pages/Episode.css frontend/src/components/CaptionGrid.jsx frontend/src/components/CaptionGrid.css
git commit -m "feat: Episode page with CaptionGrid — import, edit, save"
```

---

## Acceptance Checklist

Run through these once all 6 tasks are committed:

- [ ] `POST /captions/import/{id}` on a valid `captions.json` → `imported: 12`, no errors
- [ ] Re-import same file → `imported: 12` again (skill rows overwrite)
- [ ] Edit `en/tiktok` via `/captions/save`, re-import → `skipped_manual: 1`, cell still shows edit
- [ ] Re-import with `force=true` → manual cell overwritten, `imported: 12`
- [ ] Remove `uk` block from `captions.json` → error, zero rows written
- [ ] Instagram with 4 hashtags → error names `{lang}/instagram`, zero rows written
- [ ] YouTube list missing `#Shorts` → warning only, import still succeeds
- [ ] BOM-prefixed file → error with fix instruction
- [ ] Unknown field `notes` → ignored, import succeeds
- [ ] Library cards navigate to Episode page
- [ ] Episode page shows "No descriptions imported." when no captions in DB
- [ ] After import, 4×3 grid fills correctly
- [ ] Cell edit auto-saves on blur; "edited" badge persists on reload
- [ ] Library card shows status "Captions ready" (status = `ready`) after scan detects `captions.json`
- [ ] `pytest tests/ -v` → all green
