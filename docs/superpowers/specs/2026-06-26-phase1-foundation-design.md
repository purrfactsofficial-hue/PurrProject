# Phase 1 — Foundation Design Spec
_Date: 2026-06-26_

## Goal
Double-click `run.bat` → browser opens at localhost:5173 → Library page lists every rendered episode with thumbnail, duration, languages, and status. No posting yet. This is the scaffold everything else mounts onto.

---

## Folder Structure (source of truth)

```
C:\Users\yborodulina\Downloads\Purr\
  Episode 9 - Pizza\
    1.mp4  3.mp4  4.mp4        ← source scene clips (ignored by scanner)
    audio\  scripts\
    output\
      en\  Episode_9___Pizza_FULL.mp4  ← video to post (EN)
      fr\  Episode_9___Pizza_FULL.mp4  ← video to post (FR)
      uk\  Episode_9___Pizza_FULL.mp4  ← video to post (UK)
      zh\  Episode_9___Pizza_FULL.mp4  ← video to post (ZH)
  Episode 10 - Ice Cream\
    ...same structure...
  Common parts\                         ← skipped by scanner
```

One card in the Library = one episode folder. The `output/{lang}/*_FULL.mp4` files are the videos that get posted.

---

## Backend

### Stack
- Python 3.11+, FastAPI, SQLite via SQLAlchemy, APScheduler (stub), uvicorn

### Episode scanner (`services/video_scanner.py`)
Walks `VIDEO_REPO_PATH`, skips `Common parts` and anything without an `Episode N - ` prefix.

Per episode:
- **Parse** folder name → `episode_num` (int), `name` (str), `slug` (kebab-case)
- **Primary video** → `output/en/*_FULL.mp4` (used for thumbnail + metadata)
- **Thumbnail** → ffmpeg first-frame extract → saved to `backend/thumbs/{slug}.jpg`
- **Duration + size** → ffprobe on primary video
- **Languages** → which of `en fr uk zh` have a `*_FULL.mp4` in their `output/` subfolder
- **Status** → `new` (Phase 1 default; Phase 2+ updates this)

### Data model (`database.py`) — `videos` table
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| episode_num | INTEGER | |
| name | TEXT | "Pizza" |
| slug | TEXT UNIQUE | "episode-9-pizza" |
| folder_path | TEXT | absolute path |
| primary_file | TEXT | path to EN FULL.mp4 |
| duration_secs | REAL | |
| size_bytes | INTEGER | from EN FULL.mp4 |
| thumbnail_path | TEXT | relative path under /thumbs/ |
| languages | TEXT | JSON list ["en","fr","uk","zh"] |
| status | TEXT | new / draft / ready / scheduled / published / failed |
| scanned_at | DATETIME | |

### API endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/health` | `{"status":"ok"}` |
| GET | `/videos/scan` | Walk disk, extract metadata, upsert DB, return all episodes |
| GET | `/videos/list` | Query DB with `?status=&page=1&per_page=12` |
| GET | `/thumbs/{filename}` | Serve thumbnail file (StaticFiles mount) |

Stub routes for Phase 2+ (return empty/placeholder): `/captions/*`, `/schedule/*`, `/analytics/*`.

### `main.py`
- FastAPI app
- CORS for `http://localhost:5173`
- `create_tables()` on startup
- Mount all routers under `/` (no prefix — frontend hits `/api/...` via Vite proxy)
- APScheduler start/stop lifecycle (DEV_MODE, no real posting)
- StaticFiles mount: `/thumbs` → `./thumbs/`

### `config.py`
Reads from `.env` via python-dotenv. Key var for Phase 1: `VIDEO_REPO_PATH`. Others (API keys, channel IDs, posting hours) present but not used until later phases.

### `requirements.txt`
```
fastapi
uvicorn[standard]
sqlalchemy
python-dotenv
apscheduler
```
(ffprobe/ffmpeg expected on PATH)

---

## Frontend

### Stack
React 18 + Vite, plain CSS (no UI framework), react-router-dom v6.

### Design — Atelier direction (ui_A_atelier.html)
All CSS variables ported verbatim into `tokens.css`:
`--paper`, `--paper-2`, `--ink`, `--ink-soft`, `--yarn`, `--pink`, `--pink-deep`, `--gold`, `--gold-deep`, `--line`, `--ok`, `--radius`

Fonts: Fraunces (serif display) + Hanken Grotesk (body). Dashed borders as the signature aesthetic.

### File structure
```
frontend/
  package.json
  vite.config.js          # proxy /api → localhost:8000
  index.html
  src/
    main.jsx              # React root + BrowserRouter
    App.jsx               # sidebar layout + <Outlet/>
    api.js                # fetch wrapper, base /api
    tokens.css
    pages/
      Library.jsx         # live page
      Episode.jsx         # placeholder
      Queue.jsx           # placeholder
      Dashboard.jsx       # placeholder
      Settings.jsx        # placeholder
    components/
      Nav.jsx             # sidebar (sticky, dashed border)
      VideoCard.jsx       # thumbnail, duration badge, ep badge, name, langs, status
      StatusTag.jsx       # colored pill: new/draft/ready/scheduled/posted
      Pagination.jsx      # numbered page controls
```

### Library page behaviour
1. On mount → `GET /api/videos/scan` (first load always rescans)
2. Loading skeleton while scan runs (~1s per clip)
3. Render grid of `VideoCard`s
4. Filter chips: **All · New · Scheduled · Posted** — clicking hits `/api/videos/list?status=X&page=1`
5. Pagination: 12 cards/page, numbered controls below grid, hidden when ≤1 page
6. "Scan folder" button → re-calls `/api/videos/scan`
7. Empty state: shows `VIDEO_REPO_PATH`, says "No episodes found in this folder"
8. Error state: "Can't reach the backend — start it with `cd backend && uvicorn main:app --reload`"

### VideoCard
- Thumbnail `<img>` with gradient colour fallback (one colour per episode slot, cycling 9 tints from the mockup)
- Episode badge top-left, duration badge bottom-right (overlaid on thumb)
- Name (Fraunces), size · format line, language chips (EN UK ZH FR)
- Status tag + "Open →" button (placeholder, no nav yet)
- Hover: lift + pink dashed border

---

## Launcher

`run.bat` at project root:
```bat
@echo off
echo Starting PurrFacts...
start "backend"  cmd /k "cd backend && venv\Scripts\activate && uvicorn main:app --reload --port 8000"
timeout /t 4 >nul
start "frontend" cmd /k "cd frontend && npm run dev"
timeout /t 3 >nul
start http://localhost:5173
```

---

## Acceptance criteria
- [ ] `run.bat` opens both terminals and the browser
- [ ] Library shows 19 episode cards (one per folder, skipping Common parts)
- [ ] Each card: real thumbnail, duration, size, episode name, language chips
- [ ] "Scan folder" button refreshes the list
- [ ] Filter chips (All / New / Scheduled / Posted) narrow the grid
- [ ] Pagination shows page numbers; hides when only 1 page
- [ ] Empty + error states are clear and actionable
- [ ] Atelier design tokens drive all colours and fonts
- [ ] Responsive to mobile width; visible keyboard focus
