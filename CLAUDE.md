# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Start everything (Windows)

```bat
run.bat
```

Opens two terminals (backend on :8000, frontend on :5173) and launches the browser.

### Backend

```bash
cd backend
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

uvicorn main:app --reload --port 8000

# Run all tests
pytest tests/ -v

# Run a single test
pytest tests/test_captions_route.py::test_import_valid_returns_12 -v

# Coverage report (90% threshold enforced on pre-push)
pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=90 -q

# Lint + format (also runs in pre-commit hook)
venv\Scripts\python -m ruff check .
venv\Scripts\python -m ruff check . --fix   # auto-fix
venv\Scripts\python -m ruff format .
```

### Frontend

```bash
cd frontend
npm run dev            # dev server on :5173
npm run build          # production build to frontend/dist/
npm run test           # vitest watch mode
npm run test:run       # vitest single run
npm run coverage       # vitest run + coverage report (90% threshold)
npm run lint           # ESLint check
npm run lint:fix       # ESLint auto-fix
npm run format         # Prettier write
npm run format:check   # Prettier check only
```

### Markdown (project root)

```bash
npm run lint:md        # markdownlint-cli2 check
npm run lint:md:fix    # markdownlint-cli2 auto-fix
```

## Architecture

**PurrFacts Studio** is a two-process app: a FastAPI backend (SQLite, port 8000) and a React/Vite frontend (port 5173). The frontend proxies `/api/*` to the backend via Vite config — all `fetch` calls in `api.js` use `/api` paths.

### Backend layout

```text
backend/
  main.py              # FastAPI app, lifespan startup (DB tables, scheduler, thumbs dir)
  config.py            # Pydantic Settings — reads VIDEO_REPO_PATH, DATABASE_URL from .env
  database.py          # SQLAlchemy models: Video, Caption
  routes/
    videos.py          # GET /videos/{scan,list,{id},stream}
    captions.py        # POST /captions/import/{id}, GET /captions/{id}, POST /captions/save
    schedule.py        # stub
    analytics.py       # stub
  services/
    video_scanner.py   # walks VIDEO_REPO_PATH, runs ffprobe/ffmpeg, detects languages
    caption_importer.py # loads captions.json, validates schema, upserts 12 Caption rows
  schemas/             # JSON Schema for captions.json
  tests/               # pytest — all use in-memory SQLite, TestClient from httpx
  thumbs/              # generated thumbnail JPGs served at /thumbs/
```

### Frontend layout

```text
frontend/src/
  api.js               # all fetch wrappers (scanVideos, listVideos, getVideo, importCaptions, getCaptions, saveCaption)
  App.jsx              # React Router: / → Library, /episode/:id → Episode
  tokens.css           # design tokens (--paper, --ink, --yarn, --pink, --gold, etc.)
  pages/
    Library.jsx        # video grid, scan button, status filter, pagination
    Episode.jsx        # video detail, import button, CaptionGrid
  components/
    CaptionGrid.jsx    # 4 languages × 3 platforms editable table, auto-save on blur
    VideoCard.jsx      # thumbnail card in the grid
    StatusTag.jsx      # status badge
    Pagination.jsx
```

### Data model

**Video**: episode_num, name, slug, folder_path, primary_file, duration_secs, size_bytes, thumbnail_path, languages (JSON string), status, scanned_at

**Caption**: video_id (FK), language, platform, title, caption, hashtags (space-joined string), source ("skill" | "manual"), updated_at — unique on (video_id, language, platform)

### Key invariants

- **Caption import is atomic**: `import_captions()` service never calls `db.commit()`; the route owns the single commit that covers both the 12 Caption rows and `video.status = "ready"`.
- **Manual rows are protected**: rows with `source="manual"` are skipped on re-import unless `?force=true`.
- **Status flow**: scanner sets "draft" (no captions.json) or "ready" (captions.json present). Rescan never downgrades "scheduled", "published", "failed", or "ready".
- **422 opt-in**: `post()` in `api.js` throws on non-2xx by default; pass `{ allow422: true }` for import endpoint which deliberately returns 422 with a structured payload on validation errors.
- **captions.json shape**: `schema_version`, `episode`, `languages` → 4 langs (en, uk, zh, fr) × 3 platforms (youtube, tiktok, instagram) = 12 cells. YouTube has `title` + `description` + `hashtags`; TikTok and Instagram have `caption` + `hashtags`.
- **Hashtags stored** as a space-joined string in DB; deserialized back to `list[str]` in `CaptionOut`.

## Code Style

- **File length**: hard cap of 300 lines per file — split responsibilities rather than grow a file.
- **Principles**: DRY and SOLID; one clear responsibility per module, service, or component.
- **Elegance over cleverness**: prefer obvious, readable code over terse one-liners.
- **Validation at boundaries**: validate at the API layer (Pydantic models) and component entry points; trust internal functions once input is clean.
- **Error handling**: every route returns a structured error (HTTPException with `detail`); frontend surfaces errors inline, not via `console.error` alone.
- No comments unless the *why* is non-obvious; well-named identifiers explain the *what*.

## Testing Standards

- **TDD**: write the failing test first, then the minimum implementation to pass it.
- **Coverage target**: 90% line coverage on backend; run `pytest tests/ --cov=. --cov-report=term-missing` from `backend/`.
- **Backend tests**: pytest + `unittest.mock.MagicMock` for DB and services + TestClient; one test file per route or service file.
- **Frontend integration tests**: Vitest + React Testing Library on mocked API data, covering every high-priority user flow (scan → Library populated, Library card → Episode page, Import captions → grid filled, cell edit → saved badge).
- Mock the database layer in all tests (backend and frontend) — tests must be fast, isolated, and independent of any real DB or file system.

### Video folder convention

Episodes live under `VIDEO_REPO_PATH` (configured in `.env`) as `Episode N - Name/`. Scanner expects:

- `output/en/` subdirectory with a file matching `*FULL*.mp4` as the primary video
- Optional `output/{fr,uk,zh}/` for language detection
- Optional `captions.json` at the episode root
