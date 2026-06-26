# Phase 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working local web app (FastAPI + React/Vite) that scans the Purr episode folder and displays episode cards with thumbnails, durations, language chips, status, pagination, and filtering — launchable via `run.bat`.

**Architecture:** FastAPI backend scans `Episode N - Name` subdirectories, extracts metadata via ffprobe/ffmpeg, upserts to SQLite, and serves a paginated/filtered REST API. React frontend renders the Library page with Atelier design tokens. A `run.bat` starts both servers and opens the browser.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2, SQLite, APScheduler 3, uvicorn — React 18, Vite 5, react-router-dom v6, plain CSS

## Global Constraints

- Windows paths — use `pathlib.Path` everywhere, never string concatenation
- `VIDEO_REPO_PATH = C:\Users\yborodulina\Downloads\Purr` (set in `backend/.env`)
- ffprobe and ffmpeg must be on PATH (already installed)
- Backend port: 8000 · Frontend port: 5173
- Python venv at `backend/venv/` — activate with `venv\Scripts\activate`
- Thumbnails cached at `backend/thumbs/{slug}.jpg`; served at `GET /thumbs/{slug}.jpg`
- Status values: `new` | `draft` | `ready` | `scheduled` | `published` | `failed`
- Filter query param for list endpoint: omit (all) | `new` | `scheduled` | `published`
- Pagination default: 12 items per page
- Languages always sorted: `["en", "fr", "uk", "zh"]`
- Episode folders named exactly `Episode N - Name` (N is int, Name is any string)
- `Common parts` folder and anything not matching `Episode N - ` prefix is skipped
- Primary video for metadata: `output/en/*_FULL.mp4` (first glob match in that dir)
- Language detected present when: `output/{lang}/*_FULL.mp4` exists
- Re-scan must NOT overwrite `status` field — only initial insert sets `new`

---

### Task 1: Backend foundation — requirements, config, database

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/config.py`
- Create: `backend/database.py`
- Create: `backend/thumbs/.gitkeep`

**Interfaces:**
- Produces:
  - `from config import settings` → `settings.video_repo_path: Path`, `settings.thumbs_dir: Path`, `settings.database_url: str`, `settings.dev_mode: bool`
  - `from database import engine, Video, Base, create_tables, get_db`
  - `get_db()` → generator yielding `sqlalchemy.orm.Session` (FastAPI dependency)

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
python-dotenv==1.0.1
apscheduler==3.10.4
pydantic-settings==2.5.2
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 2: Create `backend/.env.example`**

```env
# Path to the folder containing episode directories
VIDEO_REPO_PATH=C:\Users\yborodulina\Downloads\Purr

# Set to true to disable real posting (always true in Phase 1)
DEV_MODE=true

# --- Phase 2+ (leave blank for now) ---
ANTHROPIC_API_KEY=

# YouTube OAuth secrets — one per language channel (fill in Phase 4)
YT_CLIENT_SECRET_EN=
YT_CLIENT_SECRET_UK=
YT_CLIENT_SECRET_ZH=
YT_CLIENT_SECRET_FR=

# Instagram Graph API tokens (fill in Phase 4)
IG_ACCESS_TOKEN_EN=
IG_ACCESS_TOKEN_UK=
IG_ACCESS_TOKEN_ZH=
IG_ACCESS_TOKEN_FR=

# TikTok cookie paths (fill in Phase 4)
TIKTOK_COOKIES_EN=
TIKTOK_COOKIES_UK=
TIKTOK_COOKIES_ZH=
TIKTOK_COOKIES_FR=

# Email alerts (fill in Phase 6)
EMAIL_ADDRESS=borodulina.iana@gmail.com
EMAIL_APP_PASSWORD=
```

- [ ] **Step 3: Create `backend/config.py`**

```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    video_repo_path: Path = Path(r"C:\Users\yborodulina\Downloads\Purr")
    database_url: str = "sqlite:///./purr.db"
    dev_mode: bool = True
    thumbs_dir: Path = Path("thumbs")

    anthropic_api_key: str = ""
    email_address: str = "borodulina.iana@gmail.com"
    email_app_password: str = ""


settings = Settings()
```

- [ ] **Step 4: Create `backend/database.py`**

```python
import json
from datetime import datetime
from typing import Generator

from sqlalchemy import Column, DateTime, Integer, Real, Text, create_engine
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
    duration_secs = Column(Real)
    size_bytes = Column(Integer)
    thumbnail_path = Column(Text)
    languages = Column(Text, default="[]")   # stored as JSON string
    status = Column(Text, default="new")
    scanned_at = Column(DateTime, default=datetime.utcnow)


engine = create_engine(
    settings.database_url, connect_args={"check_same_thread": False}
)


def create_tables() -> None:
    Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
```

- [ ] **Step 5: Create `backend/thumbs/.gitkeep`** (empty file so git tracks the directory)

- [ ] **Step 6: Set up venv and install**

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 7: Smoke-test config import**

```bash
# in backend/ with venv active
python -c "from config import settings; print(settings.video_repo_path)"
```

Expected output: `C:\Users\yborodulina\Downloads\Purr`

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: backend foundation — config, database model, requirements"
```

---

### Task 2: Video scanner service

**Files:**
- Create: `backend/services/__init__.py` (empty)
- Create: `backend/services/video_scanner.py`
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/test_scanner.py`

**Interfaces:**
- Consumes: `settings.video_repo_path: Path`, `settings.thumbs_dir: Path`
- Produces: `scan_episodes(repo_path: Path, thumbs_dir: Path) -> list[dict]`
  Each dict keys: `episode_num: int`, `name: str`, `slug: str`, `folder_path: str`,
  `primary_file: str | None`, `duration_secs: float | None`, `size_bytes: int | None`,
  `thumbnail_path: str | None`, `languages: list[str]`, `status: str`
- Produces: `parse_episode_folder(folder_name: str) -> tuple[int, str, str] | None`
- Produces: `detect_languages(episode_dir: Path) -> list[str]`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_scanner.py`:

```python
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.video_scanner import detect_languages, parse_episode_folder, scan_episodes


# ---------------------------------------------------------------------------
# parse_episode_folder
# ---------------------------------------------------------------------------

def test_parse_episode_folder_single_word():
    result = parse_episode_folder("Episode 9 - Pizza")
    assert result == (9, "Pizza", "episode-9-pizza")


def test_parse_episode_folder_multi_word():
    result = parse_episode_folder("Episode 12 - Great Wall")
    assert result == (12, "Great Wall", "episode-12-great-wall")


def test_parse_episode_folder_large_number():
    result = parse_episode_folder("Episode 19 - Cosmos")
    assert result == (19, "Cosmos", "episode-19-cosmos")


def test_parse_episode_folder_returns_none_for_common_parts():
    assert parse_episode_folder("Common parts") is None


def test_parse_episode_folder_returns_none_for_unrecognised():
    assert parse_episode_folder("random folder") is None


# ---------------------------------------------------------------------------
# detect_languages
# ---------------------------------------------------------------------------

def test_detect_languages_finds_all_four(tmp_path):
    for lang in ["en", "fr", "uk", "zh"]:
        d = tmp_path / "output" / lang
        d.mkdir(parents=True)
        (d / "Episode_9___Pizza_FULL.mp4").touch()
    assert sorted(detect_languages(tmp_path)) == ["en", "fr", "uk", "zh"]


def test_detect_languages_partial(tmp_path):
    for lang in ["en", "fr"]:
        d = tmp_path / "output" / lang
        d.mkdir(parents=True)
        (d / "Episode_9___Pizza_FULL.mp4").touch()
    assert sorted(detect_languages(tmp_path)) == ["en", "fr"]


def test_detect_languages_dir_exists_but_no_full_mp4(tmp_path):
    d = tmp_path / "output" / "en"
    d.mkdir(parents=True)
    (d / "scene1_FINAL.mp4").touch()   # not a FULL file
    assert detect_languages(tmp_path) == []


def test_detect_languages_no_output_dir(tmp_path):
    assert detect_languages(tmp_path) == []


# ---------------------------------------------------------------------------
# scan_episodes — integration-style with mocked subprocess
# ---------------------------------------------------------------------------

FAKE_FFPROBE = MagicMock(returncode=0, stdout='{"format":{"duration":"44.5","size":"17600000"}}', stderr="")
FAKE_FFMPEG  = MagicMock(returncode=0, stdout="", stderr="")


def _make_ep(root: Path, folder: str, langs: list[str]) -> None:
    ep = root / folder
    ep.mkdir()
    for lang in langs:
        d = ep / "output" / lang
        d.mkdir(parents=True)
        slug = folder.replace(" - ", "___").replace(" ", "_")
        (d / f"{slug}_FULL.mp4").touch()


@patch("services.video_scanner.subprocess.run")
def test_scan_finds_episode(mock_run, tmp_path):
    mock_run.side_effect = [FAKE_FFPROBE, FAKE_FFMPEG]
    _make_ep(tmp_path, "Episode 9 - Pizza", ["en", "fr", "uk", "zh"])
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()

    results = scan_episodes(tmp_path, thumbs)

    assert len(results) == 1
    ep = results[0]
    assert ep["episode_num"] == 9
    assert ep["name"] == "Pizza"
    assert ep["slug"] == "episode-9-pizza"
    assert sorted(ep["languages"]) == ["en", "fr", "uk", "zh"]
    assert ep["duration_secs"] == 44.5
    assert ep["size_bytes"] == 17_600_000
    assert ep["status"] == "new"


@patch("services.video_scanner.subprocess.run")
def test_scan_skips_common_parts(mock_run, tmp_path):
    mock_run.side_effect = [FAKE_FFPROBE, FAKE_FFMPEG]
    _make_ep(tmp_path, "Episode 9 - Pizza", ["en"])
    (tmp_path / "Common parts").mkdir()
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()

    results = scan_episodes(tmp_path, thumbs)
    assert len(results) == 1
    assert results[0]["name"] == "Pizza"


@patch("services.video_scanner.subprocess.run")
def test_scan_sorted_by_episode_num(mock_run, tmp_path):
    mock_run.side_effect = [
        FAKE_FFPROBE, FAKE_FFMPEG,
        FAKE_FFPROBE, FAKE_FFMPEG,
    ]
    _make_ep(tmp_path, "Episode 19 - Cosmos", ["en"])
    _make_ep(tmp_path, "Episode 2 - Venus", ["en"])
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()

    results = scan_episodes(tmp_path, thumbs)
    assert results[0]["episode_num"] == 2
    assert results[1]["episode_num"] == 19
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd backend
venv\Scripts\activate
pytest tests/test_scanner.py -v
```

Expected: `ImportError: cannot import name 'scan_episodes' from 'services.video_scanner'`

- [ ] **Step 3: Create `backend/services/__init__.py`** (empty file)

- [ ] **Step 4: Create `backend/tests/__init__.py`** (empty file)

- [ ] **Step 5: Implement `backend/services/video_scanner.py`**

```python
import json
import re
import subprocess
from pathlib import Path

_EPISODE_RE = re.compile(r"^Episode (\d+) - (.+)$")
_LANGS = ["en", "fr", "uk", "zh"]


def parse_episode_folder(folder_name: str) -> tuple[int, str, str] | None:
    m = _EPISODE_RE.match(folder_name)
    if not m:
        return None
    num = int(m.group(1))
    name = m.group(2)
    slug = f"episode-{num}-{name.lower().replace(' ', '-')}"
    return num, name, slug


def detect_languages(episode_dir: Path) -> list[str]:
    output_dir = episode_dir / "output"
    if not output_dir.is_dir():
        return []
    found = []
    for lang in _LANGS:
        lang_dir = output_dir / lang
        if lang_dir.is_dir() and any(lang_dir.glob("*_FULL.mp4")):
            found.append(lang)
    return found


def _primary_video(episode_dir: Path) -> Path | None:
    en_dir = episode_dir / "output" / "en"
    if en_dir.is_dir():
        matches = list(en_dir.glob("*_FULL.mp4"))
        if matches:
            return matches[0]
    return None


def _extract_metadata(video: Path) -> tuple[float | None, int | None]:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None, None
    fmt = json.loads(result.stdout).get("format", {})
    duration = float(fmt["duration"]) if "duration" in fmt else None
    size = int(fmt["size"]) if "size" in fmt else None
    return duration, size


def _extract_thumbnail(video: Path, thumb: Path) -> bool:
    result = subprocess.run(
        ["ffmpeg", "-i", str(video), "-ss", "00:00:01", "-vframes", "1",
         "-q:v", "2", str(thumb), "-y"],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def scan_episodes(repo_path: Path, thumbs_dir: Path) -> list[dict]:
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    episodes = []

    for entry in sorted(repo_path.iterdir()):
        if not entry.is_dir():
            continue
        parsed = parse_episode_folder(entry.name)
        if parsed is None:
            continue
        episode_num, name, slug = parsed

        primary = _primary_video(entry)
        duration, size, thumb_path = None, None, None

        if primary and primary.exists():
            duration, size = _extract_metadata(primary)
            thumb_file = thumbs_dir / f"{slug}.jpg"
            if _extract_thumbnail(primary, thumb_file):
                thumb_path = f"/thumbs/{slug}.jpg"

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
            "status": "new",
        })

    episodes.sort(key=lambda e: e["episode_num"])
    return episodes
```

- [ ] **Step 6: Run tests — confirm they pass**

```bash
pytest tests/test_scanner.py -v
```

Expected: all 11 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/services/ backend/tests/
git commit -m "feat: video scanner — episode parsing, language detection, ffprobe metadata"
```

---

### Task 3: Videos API route

**Files:**
- Create: `backend/routes/__init__.py` (empty)
- Create: `backend/routes/videos.py`
- Create: `backend/tests/test_videos_route.py`

**Interfaces:**
- Consumes:
  - `scan_episodes(repo_path, thumbs_dir) -> list[dict]` (Task 2)
  - `get_db() -> Session`, `Video`, `Base` (Task 1)
  - `settings.video_repo_path`, `settings.thumbs_dir` (Task 1)
- Produces: `router: APIRouter` with prefix `/videos`
  - `GET /videos/scan` → `PagedResponse`
  - `GET /videos/list?status=&page=1&per_page=12` → `PagedResponse`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_videos_route.py`:

```python
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database import Base, Video, get_db
from routes.videos import router

TEST_DB = "sqlite:///:memory:"


@pytest.fixture()
def client():
    eng = create_engine(TEST_DB, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)

    app = FastAPI()
    app.include_router(router)

    def _db():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_db] = _db

    with TestClient(app) as c:
        yield c, eng

    Base.metadata.drop_all(eng)


FAKE_SCAN = [
    {
        "episode_num": 9, "name": "Pizza", "slug": "episode-9-pizza",
        "folder_path": "/purr/Episode 9 - Pizza",
        "primary_file": "/purr/Episode 9 - Pizza/output/en/Episode_9___Pizza_FULL.mp4",
        "duration_secs": 44.0, "size_bytes": 17_600_000,
        "thumbnail_path": "/thumbs/episode-9-pizza.jpg",
        "languages": ["en", "fr", "uk", "zh"], "status": "new",
    }
]


@patch("routes.videos.scan_episodes", return_value=FAKE_SCAN)
def test_scan_returns_episodes(mock_scan, client):
    c, _ = client
    resp = c.get("/videos/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Pizza"
    assert data["items"][0]["languages"] == ["en", "fr", "uk", "zh"]


@patch("routes.videos.scan_episodes", return_value=FAKE_SCAN)
def test_scan_persists_to_db(mock_scan, client):
    c, eng = client
    c.get("/videos/scan")
    with Session(eng) as s:
        assert s.query(Video).count() == 1
        assert s.query(Video).first().slug == "episode-9-pizza"


@patch("routes.videos.scan_episodes", return_value=FAKE_SCAN)
def test_scan_upsert_does_not_duplicate(mock_scan, client):
    c, eng = client
    c.get("/videos/scan")
    c.get("/videos/scan")
    with Session(eng) as s:
        assert s.query(Video).count() == 1


@patch("routes.videos.scan_episodes", return_value=FAKE_SCAN)
def test_scan_does_not_reset_status(mock_scan, client):
    c, eng = client
    c.get("/videos/scan")
    # Simulate Phase 2+ updating status
    with Session(eng) as s:
        v = s.query(Video).first()
        v.status = "scheduled"
        s.commit()
    c.get("/videos/scan")
    with Session(eng) as s:
        assert s.query(Video).first().status == "scheduled"


def _seed(eng, count: int, status: str = "new") -> None:
    with Session(eng) as s:
        for i in range(1, count + 1):
            s.add(Video(
                episode_num=i, name=f"Ep{i}", slug=f"ep-{i}",
                folder_path=f"/p/{i}", languages='["en"]',
                status=status, scanned_at=datetime.utcnow(),
            ))
        s.commit()


def test_list_default_pagination(client):
    c, eng = client
    _seed(eng, 15)
    data = c.get("/videos/list").json()
    assert data["total"] == 15
    assert data["pages"] == 2
    assert data["page"] == 1
    assert len(data["items"]) == 12


def test_list_page_2(client):
    c, eng = client
    _seed(eng, 15)
    data = c.get("/videos/list?page=2").json()
    assert len(data["items"]) == 3
    assert data["page"] == 2


def test_list_filter_by_status(client):
    c, eng = client
    _seed(eng, 5, status="new")
    with Session(eng) as s:
        for i in range(6, 9):
            s.add(Video(
                episode_num=i, name=f"Ep{i}", slug=f"ep-{i}",
                folder_path=f"/p/{i}", languages='["en"]',
                status="published", scanned_at=datetime.utcnow(),
            ))
        s.commit()

    assert c.get("/videos/list?status=new").json()["total"] == 5
    assert c.get("/videos/list?status=published").json()["total"] == 3
    assert c.get("/videos/list").json()["total"] == 8


def test_list_invalid_page_returns_422(client):
    c, _ = client
    assert c.get("/videos/list?page=0").status_code == 422
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_videos_route.py -v
```

Expected: `ImportError` for `routes.videos`

- [ ] **Step 3: Create `backend/routes/__init__.py`** (empty)

- [ ] **Step 4: Implement `backend/routes/videos.py`**

```python
import json
import math
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import Video, get_db
from services.video_scanner import scan_episodes

router = APIRouter(prefix="/videos", tags=["videos"])


class EpisodeOut(BaseModel):
    id: int
    episode_num: int
    name: str
    slug: str
    folder_path: str
    primary_file: Optional[str] = None
    duration_secs: Optional[float] = None
    size_bytes: Optional[int] = None
    thumbnail_path: Optional[str] = None
    languages: list[str] = []
    status: str
    scanned_at: Optional[str] = None

    model_config = {"from_attributes": True}


class PagedResponse(BaseModel):
    items: list[EpisodeOut]
    total: int
    page: int
    pages: int
    per_page: int


def _to_out(v: Video) -> EpisodeOut:
    return EpisodeOut(
        id=v.id,
        episode_num=v.episode_num,
        name=v.name,
        slug=v.slug,
        folder_path=v.folder_path,
        primary_file=v.primary_file,
        duration_secs=v.duration_secs,
        size_bytes=v.size_bytes,
        thumbnail_path=v.thumbnail_path,
        languages=json.loads(v.languages or "[]"),
        status=v.status,
        scanned_at=v.scanned_at.isoformat() if v.scanned_at else None,
    )


@router.get("/scan", response_model=PagedResponse)
def scan(db: Annotated[Session, Depends(get_db)]) -> PagedResponse:
    episodes = scan_episodes(settings.video_repo_path, settings.thumbs_dir)
    now = datetime.utcnow()

    for ep in episodes:
        existing = db.query(Video).filter(Video.slug == ep["slug"]).first()
        if existing:
            # Update metadata but never overwrite status (Phase 2+ manages that)
            for key in ("episode_num", "name", "folder_path", "primary_file",
                        "duration_secs", "size_bytes", "thumbnail_path"):
                setattr(existing, key, ep[key])
            existing.languages = json.dumps(ep["languages"])
            existing.scanned_at = now
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
                status="new",
                scanned_at=now,
            ))

    db.commit()

    all_videos = db.query(Video).order_by(Video.episode_num).all()
    per_page = 12
    return PagedResponse(
        items=[_to_out(v) for v in all_videos],
        total=len(all_videos),
        page=1,
        pages=max(1, math.ceil(len(all_videos) / per_page)),
        per_page=per_page,
    )


@router.get("/list", response_model=PagedResponse)
def list_videos(
    db: Annotated[Session, Depends(get_db)],
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=100),
) -> PagedResponse:
    q = db.query(Video)
    if status:
        q = q.filter(Video.status == status)
    total = q.count()
    pages = max(1, math.ceil(total / per_page))
    items = (
        q.order_by(Video.episode_num)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return PagedResponse(
        items=[_to_out(v) for v in items],
        total=total,
        page=page,
        pages=pages,
        per_page=per_page,
    )
```

- [ ] **Step 5: Run tests — confirm they pass**

```bash
pytest tests/test_videos_route.py -v
```

Expected: all 9 tests PASS

- [ ] **Step 6: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS (scanner + route tests combined)

- [ ] **Step 7: Commit**

```bash
git add backend/routes/ backend/tests/test_videos_route.py
git commit -m "feat: videos API — scan, list with pagination and status filter"
```

---

### Task 4: Stub routes, scheduler, and main.py

**Files:**
- Create: `backend/routes/captions.py`
- Create: `backend/routes/schedule.py`
- Create: `backend/routes/analytics.py`
- Create: `backend/scheduler.py`
- Create: `backend/main.py`
- Create: `backend/.env` (copy from .env.example)

**Interfaces:**
- Produces: `uvicorn main:app` on port 8000 responding to `/health`, `/videos/scan`, `/videos/list`, `/thumbs/{file}`

- [ ] **Step 1: Create `backend/routes/captions.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/captions", tags=["captions"])


@router.get("/")
def captions_stub():
    return {"detail": "Phase 2 — not yet implemented"}
```

- [ ] **Step 2: Create `backend/routes/schedule.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/queue")
def queue_stub():
    return {"items": [], "detail": "Phase 3 — not yet implemented"}
```

- [ ] **Step 3: Create `backend/routes/analytics.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary_stub():
    return {"detail": "Phase 5 — not yet implemented"}
```

- [ ] **Step 4: Create `backend/scheduler.py`**

```python
from apscheduler.schedulers.background import BackgroundScheduler

from config import settings

_scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    if settings.dev_mode:
        return
    _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
```

- [ ] **Step 5: Create `backend/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import create_tables
from routes import analytics, captions, schedule, videos
from scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    settings.thumbs_dir.mkdir(parents=True, exist_ok=True)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="PurrFacts API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router)
app.include_router(captions.router)
app.include_router(schedule.router)
app.include_router(analytics.router)

app.mount("/thumbs", StaticFiles(directory=str(settings.thumbs_dir)), name="thumbs")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Create `backend/.env` from example**

```bash
cd backend
copy .env.example .env
```

The default `VIDEO_REPO_PATH=C:\Users\yborodulina\Downloads\Purr` is already correct.

- [ ] **Step 7: Start the backend and verify**

```bash
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

- Open `http://localhost:8000/health` → `{"status":"ok"}`
- Open `http://localhost:8000/videos/scan` → JSON with 19 episodes (takes 20–60s while ffprobe+ffmpeg runs on all episodes)
- Open `http://localhost:8000/videos/list` → same 19 episodes from DB (instant, no re-scan)

- [ ] **Step 8: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/routes/captions.py backend/routes/schedule.py backend/routes/analytics.py backend/scheduler.py backend/main.py backend/.env.example
git commit -m "feat: FastAPI app — CORS, static files, stub routes, APScheduler"
```

(Do not commit `backend/.env` — it contains paths and will hold secrets later.)

---

### Task 5: Frontend scaffold and design tokens

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/tokens.css`

**Interfaces:**
- Produces: `npm run dev` at localhost:5173 with proxy `/api/*` → `http://localhost:8000/*`
- Produces: CSS variables on `:root` consumed by all components

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "purrfacts-studio",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.2",
    "vite": "^5.4.8"
  }
}
```

- [ ] **Step 2: Create `frontend/vite.config.js`**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

- [ ] **Step 3: Create `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PurrFacts Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Hanken+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>
```

- [ ] **Step 4: Create `frontend/src/tokens.css`**

```css
:root {
  --paper: #F6F2EA;
  --paper-2: #FBF8F2;
  --ink: #2A2622;
  --ink-soft: #6F675E;
  --yarn: #9C9388;
  --pink: #DE839C;
  --pink-deep: #C35D78;
  --gold: #C29A26;
  --gold-deep: #A07E16;
  --line: #D9CFC0;
  --ok: #5E9A78;
  --radius: 14px;
  --font-display: 'Fraunces', serif;
  --font-body: 'Hanken Grotesk', system-ui, sans-serif;
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html { scroll-behavior: smooth; }

body {
  font-family: var(--font-body);
  background: var(--paper);
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
  line-height: 1.4;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.5;
  mix-blend-mode: multiply;
  background-image: radial-gradient(circle at 1px 1px, rgba(160,140,110,.06) 1px, transparent 0);
  background-size: 5px 5px;
  z-index: 0;
}

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; }
}
```

- [ ] **Step 5: Create `frontend/src/main.jsx`**

```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './tokens.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
)
```

- [ ] **Step 6: Install and start**

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` → blank page is correct (App.jsx not yet created). No console errors other than missing root component.

Stop with Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: frontend scaffold — Vite, React 18, Atelier design tokens"
```

---

### Task 6: App shell, Nav, and placeholder pages

**Files:**
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/App.css`
- Create: `frontend/src/components/Nav.jsx`
- Create: `frontend/src/components/Nav.css`
- Create: `frontend/src/pages/Episode.jsx`
- Create: `frontend/src/pages/Queue.jsx`
- Create: `frontend/src/pages/Dashboard.jsx`
- Create: `frontend/src/pages/Settings.jsx`

**Interfaces:**
- Produces: `<App>` renders sidebar + routed `<main>` for five pages
- Nav uses `react-router-dom` `NavLink` for active state

- [ ] **Step 1: Create `frontend/src/App.css`**

```css
.app {
  display: grid;
  grid-template-columns: 236px 1fr;
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

.main-content {
  padding: 30px 38px 60px;
  min-width: 0;
}

@media (max-width: 780px) {
  .app { grid-template-columns: 1fr; }
  .main-content { padding: 22px 18px 50px; }
}
```

- [ ] **Step 2: Create `frontend/src/App.jsx`**

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
          <Route path="/episode" element={<Episode />} />
          <Route path="/queue" element={<Queue />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
```

- [ ] **Step 3: Create `frontend/src/components/Nav.css`**

```css
.side {
  padding: 26px 18px;
  border-right: 2px dashed var(--line);
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-bottom: 34px;
  padding-left: 6px;
}

.bell {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #F2D873, var(--gold));
  box-shadow: inset 0 -2px 4px rgba(120,90,0,.35);
  position: relative;
  flex: none;
}

.bell::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 62%;
  transform: translateX(-50%);
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #7a5d05;
}

.brand-text h1 {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 20px;
  letter-spacing: -0.01em;
  line-height: 1;
}

.brand-text small {
  display: block;
  font-size: 10.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--yarn);
  margin-top: 3px;
  font-weight: 600;
}

.side nav a {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--ink-soft);
  text-decoration: none;
  font-weight: 600;
  font-size: 14.5px;
  margin-bottom: 3px;
  position: relative;
}

.side nav a .ic {
  width: 17px;
  text-align: center;
  opacity: 0.8;
}

.side nav a:hover {
  background: #efe8db;
  color: var(--ink);
}

.side nav a.active {
  color: var(--ink);
  background: #efe8db;
}

.side nav a.active::after {
  content: "";
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 5px;
  height: 0;
  border-bottom: 2.5px dashed var(--pink);
}

.side-foot {
  position: absolute;
  bottom: 24px;
  left: 18px;
  right: 18px;
  font-size: 11.5px;
  color: var(--yarn);
  border-top: 2px dashed var(--line);
  padding-top: 14px;
}

.side-foot b { color: var(--ink-soft); font-weight: 600; }

@media (max-width: 780px) {
  .side {
    position: static;
    height: auto;
    border-right: none;
    border-bottom: 2px dashed var(--line);
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 16px 20px;
  }
  .side nav { display: flex; gap: 2px; overflow: auto; }
  .side nav a { margin: 0; white-space: nowrap; }
  .brand { margin-bottom: 0; }
  .side-foot { display: none; }
}
```

- [ ] **Step 4: Create `frontend/src/components/Nav.jsx`**

```jsx
import { NavLink } from 'react-router-dom'
import './Nav.css'

const NAV_ITEMS = [
  { to: '/', icon: '▦', label: 'Library' },
  { to: '/episode', icon: '✎', label: 'Episode' },
  { to: '/queue', icon: '◴', label: 'Queue' },
  { to: '/dashboard', icon: '◷', label: 'Dashboard' },
  { to: '/settings', icon: '⚙', label: 'Settings' },
]

export default function Nav() {
  return (
    <aside className="side">
      <div className="brand">
        <div className="bell" aria-hidden="true" />
        <div className="brand-text">
          <h1>PurrFacts</h1>
          <small>Studio</small>
        </div>
      </div>
      <nav>
        {NAV_ITEMS.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => isActive ? 'active' : undefined}
          >
            <span className="ic">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="side-foot">
        Signed in as<br /><b>borodulina.iana</b>
      </div>
    </aside>
  )
}
```

- [ ] **Step 5: Create placeholder pages**

`frontend/src/pages/Episode.jsx`:
```jsx
export default function Episode() {
  return <p style={{ padding: 40, color: 'var(--ink-soft)' }}>Episode editor — Phase 2</p>
}
```

`frontend/src/pages/Queue.jsx`:
```jsx
export default function Queue() {
  return <p style={{ padding: 40, color: 'var(--ink-soft)' }}>Queue — Phase 3</p>
}
```

`frontend/src/pages/Dashboard.jsx`:
```jsx
export default function Dashboard() {
  return <p style={{ padding: 40, color: 'var(--ink-soft)' }}>Analytics — Phase 5</p>
}
```

`frontend/src/pages/Settings.jsx`:
```jsx
export default function Settings() {
  return <p style={{ padding: 40, color: 'var(--ink-soft)' }}>Settings — Phase 6</p>
}
```

- [ ] **Step 6: Verify in browser**

Start `npm run dev`. Open `http://localhost:5173`.

Expected: sidebar with bell logo + 5 nav links renders on the Atelier cream background. Clicking each link changes the active state and shows the placeholder text. At ≤780px the sidebar becomes a scrollable top bar.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat: App shell with Atelier Nav and placeholder pages"
```

---

### Task 7: api.js and Library page

**Files:**
- Create: `frontend/src/api.js`
- Create: `frontend/src/pages/Library.jsx`
- Create: `frontend/src/pages/Library.css`

**Interfaces:**
- Produces: `scanVideos() -> Promise<PagedResponse>`, `listVideos({status?, page?, perPage?}) -> Promise<PagedResponse>`
- `PagedResponse` shape: `{ items: EpisodeOut[], total: number, page: number, pages: number, per_page: number }`
- `EpisodeOut` shape: `{ id, episode_num, name, slug, thumbnail_path, duration_secs, size_bytes, languages, status }`

- [ ] **Step 1: Create `frontend/src/api.js`**

```js
const BASE = '/api'

async function request(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export function scanVideos() {
  return request('/videos/scan')
}

export function listVideos({ status, page = 1, perPage = 12 } = {}) {
  const params = new URLSearchParams({ page, per_page: perPage })
  if (status) params.set('status', status)
  return request(`/videos/list?${params}`)
}
```

- [ ] **Step 2: Create `frontend/src/pages/Library.css`**

```css
.library-top {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.eyebrow {
  font-size: 11.5px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--pink-deep);
  font-weight: 700;
}

.library-title {
  font-family: var(--font-display);
  font-size: 40px;
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.02;
  margin-top: 4px;
}

.library-title em {
  font-style: italic;
  color: var(--gold-deep);
}

.scan-btn {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  background: var(--gold);
  color: #fff;
  border: none;
  cursor: pointer;
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 14px;
  padding: 12px 18px;
  border-radius: 11px;
  box-shadow: 0 2px 0 var(--gold-deep);
  transition: transform 0.12s, box-shadow 0.12s;
}

.scan-btn:hover  { transform: translateY(-1px); box-shadow: 0 3px 0 var(--gold-deep); }
.scan-btn:active { transform: translateY(1px);  box-shadow: 0 1px 0 var(--gold-deep); }
.scan-btn:focus-visible { outline: 3px solid var(--pink); outline-offset: 2px; }
.scan-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

.meta-row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin: 18px 0 22px;
  font-size: 13px;
  color: var(--ink-soft);
}

.path-badge {
  font-family: var(--font-display);
  font-size: 13px;
  background: var(--paper-2);
  border: 2px dashed var(--line);
  padding: 6px 11px;
  border-radius: 9px;
  color: var(--ink);
}

.dot-ok {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ok);
  display: inline-block;
  box-shadow: 0 0 0 3px rgba(94,154,120,.18);
  margin-right: 6px;
}

.filters {
  margin-left: auto;
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}

.chip {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink-soft);
  background: var(--paper-2);
  border: 2px dashed var(--line);
  padding: 6px 12px;
  border-radius: 20px;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}

.chip:hover { background: #efe8db; }
.chip.on    { color: #fff; background: var(--ink); border-color: var(--ink); }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(248px, 1fr));
  gap: 20px;
}

.skeleton-card {
  background: var(--paper-2);
  border: 2px dashed var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}

.skeleton-thumb {
  aspect-ratio: 16 / 10;
  background: linear-gradient(90deg, var(--line) 25%, #e8e0d4 50%, var(--line) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-body {
  padding: 13px 14px 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-line {
  height: 14px;
  border-radius: 7px;
  background: var(--line);
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.state-box {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 20px;
  color: var(--ink-soft);
}

.state-box h2 {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 12px;
}

.state-box p  { font-size: 14px; line-height: 1.8; }

.state-box code {
  font-size: 12px;
  background: var(--paper-2);
  border: 1.5px dashed var(--line);
  padding: 2px 7px;
  border-radius: 5px;
  color: var(--ink);
}

@media (max-width: 780px) {
  .library-title { font-size: 30px; }
  .filters { margin-left: 0; }
}
```

- [ ] **Step 3: Create `frontend/src/pages/Library.jsx`**

```jsx
import { useCallback, useEffect, useState } from 'react'
import { listVideos, scanVideos } from '../api.js'
import Pagination from '../components/Pagination.jsx'
import VideoCard from '../components/VideoCard.jsx'
import './Library.css'

const FILTERS = [
  { label: 'All',       value: '' },
  { label: 'New',       value: 'new' },
  { label: 'Scheduled', value: 'scheduled' },
  { label: 'Posted',    value: 'published' },
]

const REPO_PATH = 'C:\\Users\\yborodulina\\Downloads\\Purr'

export default function Library() {
  const [episodes,     setEpisodes]     = useState([])
  const [total,        setTotal]        = useState(0)
  const [pages,        setPages]        = useState(1)
  const [page,         setPage]         = useState(1)
  const [activeFilter, setActiveFilter] = useState('')
  const [loading,      setLoading]      = useState(false)
  const [scanning,     setScanning]     = useState(false)
  const [error,        setError]        = useState(null)
  const [lastScanned,  setLastScanned]  = useState(null)

  const loadList = useCallback(async (status, p) => {
    setLoading(true)
    setError(null)
    try {
      const data = await listVideos({ status: status || undefined, page: p })
      setEpisodes(data.items)
      setTotal(data.total)
      setPages(data.pages)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleScan = useCallback(async () => {
    setScanning(true)
    setError(null)
    try {
      await scanVideos()
      setLastScanned(new Date())
      setPage(1)
      await loadList(activeFilter, 1)
    } catch (err) {
      setError(err.message)
    } finally {
      setScanning(false)
    }
  }, [activeFilter, loadList])

  // Scan once on mount
  useEffect(() => { handleScan() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleFilter = (value) => {
    setActiveFilter(value)
    setPage(1)
    loadList(value, 1)
  }

  const handlePage = (p) => {
    setPage(p)
    loadList(activeFilter, p)
  }

  const isBusy = loading || scanning

  return (
    <div>
      <div className="library-top">
        <div>
          <div className="eyebrow">Your worktable</div>
          <h1 className="library-title">Library <em>·</em> rendered clips</h1>
        </div>
        <button className="scan-btn" onClick={handleScan} disabled={isBusy}>
          {scanning ? 'Scanning…' : '↻ Scan folder'}
        </button>
      </div>

      <div className="meta-row">
        <span className="path-badge">{REPO_PATH}</span>
        {!error && !isBusy && total > 0 && (
          <span>
            <span className="dot-ok" />
            Connected · {total} clip{total !== 1 ? 's' : ''}
            {lastScanned && ' · scanned just now'}
          </span>
        )}
        <div className="filters">
          {FILTERS.map(({ label, value }) => (
            <button
              key={value}
              className={`chip${activeFilter === value ? ' on' : ''}`}
              onClick={() => handleFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid">
        {isBusy ? (
          Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="skeleton-card">
              <div className="skeleton-thumb" />
              <div className="skeleton-body">
                <div className="skeleton-line" style={{ width: '60%' }} />
                <div className="skeleton-line" style={{ width: '80%' }} />
                <div className="skeleton-line" style={{ width: '40%' }} />
              </div>
            </div>
          ))
        ) : error ? (
          <div className="state-box">
            <h2>Can't reach the backend</h2>
            <p>
              Start it with:<br />
              <code>cd backend &amp;&amp; venv\Scripts\activate &amp;&amp; uvicorn main:app --reload</code>
            </p>
          </div>
        ) : episodes.length === 0 ? (
          <div className="state-box">
            <h2>No episodes found</h2>
            <p>
              No rendered episodes found in:<br />
              <code>{REPO_PATH}</code><br /><br />
              Check that <code>VIDEO_REPO_PATH</code> is set correctly in <code>backend/.env</code>
            </p>
          </div>
        ) : (
          episodes.map((ep) => <VideoCard key={ep.id} episode={ep} />)
        )}
      </div>

      {!isBusy && !error && pages > 1 && (
        <Pagination page={page} pages={pages} onPage={handlePage} />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api.js frontend/src/pages/Library.jsx frontend/src/pages/Library.css
git commit -m "feat: Library page — scan, filter chips, pagination, loading/error/empty states"
```

---

### Task 8: VideoCard, StatusTag, and Pagination components

**Files:**
- Create: `frontend/src/components/StatusTag.jsx`
- Create: `frontend/src/components/StatusTag.css`
- Create: `frontend/src/components/VideoCard.jsx`
- Create: `frontend/src/components/VideoCard.css`
- Create: `frontend/src/components/Pagination.jsx`
- Create: `frontend/src/components/Pagination.css`

**Interfaces:**
- `<StatusTag status="new|draft|ready|scheduled|published|failed" />`
- `<VideoCard episode={EpisodeOut} />` where `EpisodeOut` is `{ id, episode_num, name, slug, thumbnail_path, duration_secs, size_bytes, languages, status }`
- `<Pagination page={number} pages={number} onPage={(p: number) => void} />` — renders `null` when `pages <= 1`

- [ ] **Step 1: Create `frontend/src/components/StatusTag.css`**

```css
.status-tag {
  font-size: 11.5px;
  font-weight: 700;
  padding: 4px 9px;
  border-radius: 7px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tag-sched { color: var(--ok);        background: rgba(94,154,120,.13); }
.tag-ready { color: var(--gold-deep); background: rgba(194,154,38,.15); }
.tag-draft { color: var(--ink-soft);  background: #ece4d7; }
.tag-new   { color: var(--pink-deep); background: rgba(222,131,156,.16); }
```

- [ ] **Step 2: Create `frontend/src/components/StatusTag.jsx`**

```jsx
import './StatusTag.css'

const STATUS_CONFIG = {
  new:       { label: 'New render',     cls: 'tag-new' },
  draft:     { label: 'Draft',          cls: 'tag-draft' },
  ready:     { label: 'Captions ready', cls: 'tag-ready' },
  scheduled: { label: 'Scheduled',      cls: 'tag-sched' },
  published: { label: 'Posted',         cls: 'tag-sched' },
  failed:    { label: 'Failed',         cls: 'tag-draft' },
}

export default function StatusTag({ status }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft
  return (
    <span className={`status-tag ${cfg.cls}`}>● {cfg.label}</span>
  )
}
```

- [ ] **Step 3: Create `frontend/src/components/VideoCard.css`**

```css
.card {
  background: var(--paper-2);
  border: 2px dashed var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.14s, box-shadow 0.14s, border-color 0.14s;
}

.card:hover {
  transform: translateY(-3px);
  border-color: var(--pink);
  box-shadow: 0 10px 22px -12px rgba(120,90,60,.4);
}

.thumb {
  aspect-ratio: 16 / 10;
  position: relative;
  overflow: hidden;
  border-bottom: 2px dashed var(--line);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-fallback {
  position: absolute;
  inset: 0;
}

.ep-badge {
  position: absolute;
  left: 9px;
  top: 9px;
  background: rgba(251,248,242,.92);
  color: var(--ink-soft);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 3px 8px;
  border-radius: 7px;
  text-transform: uppercase;
}

.dur {
  position: absolute;
  right: 9px;
  bottom: 9px;
  background: rgba(42,38,34,.86);
  color: #fff;
  font-size: 11.5px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 7px;
  font-variant-numeric: tabular-nums;
}

.card-body {
  padding: 13px 14px 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}

.card-name {
  font-family: var(--font-display);
  font-size: 18.5px;
  font-weight: 600;
  letter-spacing: -0.01em;
  line-height: 1.1;
}

.card-sub {
  font-size: 12px;
  color: var(--yarn);
  font-weight: 500;
}

.langs {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.lang-chip {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.05em;
  color: var(--ink-soft);
  background: #efe8db;
  border-radius: 6px;
  padding: 3px 6px;
  text-transform: uppercase;
}

.card-status {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 11px;
  border-top: 2px dashed var(--line);
}

.open-btn {
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 12.5px;
  color: var(--ink);
  background: none;
  border: none;
  cursor: default;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  opacity: 0.55;
  transition: opacity 0.12s, gap 0.12s;
}

.card:hover .open-btn {
  opacity: 1;
  gap: 7px;
  color: var(--pink-deep);
}

.open-btn:focus-visible {
  outline: 2px solid var(--pink);
  outline-offset: 3px;
  border-radius: 4px;
  opacity: 1;
}
```

- [ ] **Step 4: Create `frontend/src/components/VideoCard.jsx`**

```jsx
import StatusTag from './StatusTag.jsx'
import './VideoCard.css'

const GRADIENTS = [
  'linear-gradient(135deg,#f3dbe2,#e9c9d3)',
  'linear-gradient(135deg,#d9e7ec,#c5dbe4)',
  'linear-gradient(135deg,#ece0c9,#e0d0b0)',
  'linear-gradient(135deg,#f0d8c4,#e7c2a6)',
  'linear-gradient(135deg,#eee2c0,#e3d09a)',
  'linear-gradient(135deg,#e8e4dc,#d8d2c6)',
  'linear-gradient(135deg,#dce6ec,#c9dbe6)',
  'linear-gradient(135deg,#e6dcea,#d6c6e0)',
  'linear-gradient(135deg,#f2ddc6,#ecca9f)',
]

function fmtDuration(secs) {
  if (!secs) return null
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function fmtSize(bytes) {
  if (!bytes) return null
  return `${(bytes / 1_000_000).toFixed(1)} MB`
}

export default function VideoCard({ episode }) {
  const { episode_num, name, thumbnail_path, duration_secs, size_bytes, languages, status } = episode
  const gradient = GRADIENTS[(episode_num - 1) % GRADIENTS.length]
  const duration = fmtDuration(duration_secs)
  const size = fmtSize(size_bytes)

  return (
    <article className="card">
      <div className="thumb">
        {thumbnail_path ? (
          <img
            src={`/api${thumbnail_path}`}
            alt={name}
            onError={(e) => { e.currentTarget.style.display = 'none' }}
          />
        ) : null}
        <div
          className="thumb-fallback"
          style={{ background: gradient }}
          aria-hidden="true"
        />
        <span className="ep-badge">Ep {episode_num}</span>
        {duration && <span className="dur">{duration}</span>}
      </div>

      <div className="card-body">
        <div className="card-name">{name}</div>
        <div className="card-sub">
          Episode {episode_num}{size ? ` · ${size}` : ''} · mp4
        </div>
        <div className="langs">
          {languages.map((lang) => (
            <span key={lang} className="lang-chip">{lang.toUpperCase()}</span>
          ))}
        </div>
        <div className="card-status">
          <StatusTag status={status} />
          <button className="open-btn" tabIndex={-1} aria-hidden="true">Open →</button>
        </div>
      </div>
    </article>
  )
}
```

- [ ] **Step 5: Create `frontend/src/components/Pagination.css`**

```css
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin-top: 32px;
  flex-wrap: wrap;
}

.page-btn {
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-soft);
  background: var(--paper-2);
  border: 2px dashed var(--line);
  padding: 7px 12px;
  border-radius: 9px;
  cursor: pointer;
  min-width: 38px;
  text-align: center;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
}

.page-btn:hover    { background: #efe8db; color: var(--ink); }
.page-btn.active   { background: var(--ink); border-color: var(--ink); color: #fff; }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-btn:focus-visible { outline: 2px solid var(--pink); outline-offset: 2px; }
```

- [ ] **Step 6: Create `frontend/src/components/Pagination.jsx`**

```jsx
import './Pagination.css'

export default function Pagination({ page, pages, onPage }) {
  if (pages <= 1) return null

  return (
    <nav className="pagination" aria-label="Page navigation">
      <button
        className="page-btn"
        onClick={() => onPage(page - 1)}
        disabled={page === 1}
        aria-label="Previous page"
      >
        ‹
      </button>

      {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
        <button
          key={p}
          className={`page-btn${p === page ? ' active' : ''}`}
          onClick={() => onPage(p)}
          aria-current={p === page ? 'page' : undefined}
        >
          {p}
        </button>
      ))}

      <button
        className="page-btn"
        onClick={() => onPage(page + 1)}
        disabled={page === pages}
        aria-label="Next page"
      >
        ›
      </button>
    </nav>
  )
}
```

- [ ] **Step 7: Verify in browser (backend must be running)**

With both servers running, open `http://localhost:5173`.

Expected:
- Skeleton grid shows during scan (~10–60s depending on episode count)
- 19 episode cards appear in the Atelier grid
- Each card: thumbnail or gradient, episode badge, duration, name, size · mp4, language chips (EN FR UK ZH), "New render" pink tag
- "Scan folder" button re-scans; skeleton shows again
- Filter "New" → 19 cards. "Scheduled" / "Posted" → 0 cards (correct — none scheduled yet)
- With 19 items and 12-per-page: 2 pages shown; page 2 has 7 cards
- Stop the backend → reload → error state appears with start command
- Responsive: at narrow width sidebar collapses to top, grid becomes 1 column

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: VideoCard, StatusTag, Pagination components — Library fully wired"
```

---

### Task 9: run.bat and acceptance sign-off

**Files:**
- Create: `run.bat`

- [ ] **Step 1: Create `run.bat`**

```bat
@echo off
echo Starting PurrFacts Studio...
start "PurrFacts Backend"  cmd /k "cd /d "%~dp0backend"  && venv\Scripts\activate && uvicorn main:app --reload --port 8000"
timeout /t 4 >nul
start "PurrFacts Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
timeout /t 3 >nul
start http://localhost:5173
```

- [ ] **Step 2: Double-click `run.bat` from Explorer**

Expected: two terminal windows open (backend + frontend), then browser opens at `http://localhost:5173`, Library skeleton appears, 19 cards load.

- [ ] **Step 3: Tick acceptance checklist**

- [ ] `run.bat` opens both terminals and the browser
- [ ] Library shows 19 episode cards (one per folder, Common parts absent)
- [ ] Each card shows thumbnail (or gradient fallback), duration, size, episode name, language chips
- [ ] "Scan folder" button re-scans and refreshes cards
- [ ] Filter chips (All / New / Scheduled / Posted) narrow the grid correctly
- [ ] Pagination: page 2 shows remaining 7 cards; hidden on page-1-only grids
- [ ] Empty state: stop backend, clear DB manually, restart — see "No episodes found" message with path
- [ ] Error state: stop backend, reload — see "Can't reach the backend" message with start command
- [ ] Atelier cream background, Fraunces display font, dashed borders throughout
- [ ] Responsive: sidebar collapses at ≤780px; visible focus rings on keyboard tab

- [ ] **Step 4: Final commit**

```bash
git add run.bat
git commit -m "feat: run.bat one-click launcher — Phase 1 complete"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Episode scanner: `parse_episode_folder`, `detect_languages`, `scan_episodes` with ffprobe/ffmpeg
- ✅ SQLite via SQLAlchemy — all columns from spec
- ✅ `GET /videos/scan` — disk walk, upsert DB, returns all results
- ✅ `GET /videos/list` — paginated + status-filtered from DB
- ✅ `GET /health`
- ✅ `GET /thumbs/{file}` via StaticFiles mount
- ✅ Stub routes: captions, schedule, analytics
- ✅ APScheduler (DEV_MODE — no posting)
- ✅ CORS for `http://localhost:5173`
- ✅ Frontend scaffold: Vite 5, React 18, react-router-dom v6
- ✅ `tokens.css` with all Atelier variables verbatim
- ✅ App shell + Nav — 5 routes, sticky sidebar, responsive
- ✅ Library page: scan on mount, filter chips, pagination, loading skeletons, error + empty states
- ✅ `VideoCard`: thumbnail with gradient fallback, ep badge, duration, size, lang chips, status tag
- ✅ `StatusTag`: all 6 status values with correct colours
- ✅ `Pagination`: numbered pages, prev/next, hidden at ≤1 page, accessible
- ✅ Re-scan does NOT overwrite `status` (tested in `test_scan_does_not_reset_status`)
- ✅ `run.bat` with `%~dp0` so it works from any directory
- ✅ `backend/.env` excluded from commits (only `.env.example` committed)

**Placeholder scan:** None found.

**Type consistency:**
- `scan_episodes()` returns `list[dict]` — `routes/videos.py` iterates `ep["slug"]`, `ep["languages"]`, etc. ✅
- `EpisodeOut` fields match `_to_out()` assignments ✅
- `VideoCard` destructures `episode_num, name, thumbnail_path, duration_secs, size_bytes, languages, status` — all present in `EpisodeOut` ✅
- `Pagination` props `page/pages/onPage` — used consistently in `Library.jsx` ✅
- `listVideos({ status, page, perPage })` — `per_page` sent as query param, backend reads `per_page` ✅
