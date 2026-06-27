# Phase 1 — Implementation Plan

**Goal:** Double-click `run.bat` → browser opens → the Library page lists every `.mp4`
in your Purr folder with thumbnails, durations, and status. Nothing posts yet; this is the
foundation everything else mounts onto.

**Time:** 1–3 working days, mostly review + testing. Claude Code does the typing.

---

## 0 · Prerequisites (one-time, ~20 min)

| Need | Check | Install |
|---|---|---|
| Python 3.11+ | `python --version` | python.org |
| Node 18+ | `node --version` | nodejs.org |
| FFmpeg + ffprobe on PATH | `ffprobe -version` | you already have this |

---

## 1 · Backend — already scaffolded

These files exist from our build session and are ready to drop in:

```text
backend/
├── config.py            ✅ env vars, channel names, posting hours
├── database.py          ✅ SQLite models (videos, captions, posts, analytics, followers, notifications)
├── scheduler.py         ✅ APScheduler (runs in DEV_MODE — no real posting yet)
├── services/
│   └── video_scanner.py ✅ ffprobe duration + ffmpeg thumbnail
├── routes/
│   ├── videos.py        ✅ /videos/scan, /save, /list, topic update
│   ├── captions.py      ✅ stub (Phase 2)
│   ├── schedule.py      ✅ /schedule/create, /queue, cancel, retry
│   └── analytics.py     ✅ summary, followers, posts
└── requirements.txt     ✅
```

### Still to write for Phase 1

**`backend/main.py`** — the entry point that ties it together:

- Create FastAPI app
- Enable CORS for `http://localhost:5173` (the Vite dev server)
- `create_tables()` on startup
- Mount all four routers
- `start_scheduler()` on startup, `stop_scheduler()` on shutdown
- A `GET /health` endpoint returning `{"status":"ok"}`

**`backend/.env.example`** — template listing every key (copy to `.env` and fill in).
For Phase 1 only `VIDEO_REPO_PATH` matters; the rest can stay blank until later phases.

### Run the backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then set VIDEO_REPO_PATH
uvicorn main:app --reload --port 8000
```

Verify: open `http://localhost:8000/videos/scan` → JSON list of your clips.

---

## 2 · Frontend — to build

Stack: **React + Vite + plain CSS** (no UI framework — the design direction you pick is
custom, and a framework would fight it). Routing via `react-router-dom`.

```text
frontend/
├── package.json
├── vite.config.js          # proxy /api → localhost:8000
├── index.html
└── src/
    ├── main.jsx            # React root + router
    ├── App.jsx             # layout shell: nav + <Outlet/>
    ├── api.js              # fetch wrapper, base URL /api
    ├── tokens.css          # ← design tokens from your chosen direction (A/B/C)
    ├── pages/
    │   ├── Library.jsx     # Phase 1 — the live page
    │   ├── Episode.jsx     # placeholder
    │   ├── Queue.jsx       # placeholder
    │   ├── Dashboard.jsx   # placeholder
    │   └── Settings.jsx    # placeholder
    └── components/
        ├── Nav.jsx         # sidebar or topbar (depends on direction)
        ├── VideoCard.jsx   # the card from the mockup
        └── StatusTag.jsx   # status pill / tally / button-eyes
```

### Library.jsx behaviour

1. On mount, call `GET /api/videos/scan`
2. Show a loading state while scanning (ffprobe takes ~1s per clip)
3. Render the grid of `VideoCard`s from the response
4. "Scan folder" button re-runs the scan
5. Empty state: if the folder has no `.mp4`s, show a clear message with the path it looked in
6. Error state: if the backend is unreachable, say so and how to start it

### Run the frontend

```bash
cd frontend
npm install
npm run dev          # opens localhost:5173
```

---

## 3 · The design handoff (after you pick A / B / C)

The mockup you choose becomes `tokens.css` — one file holding the palette, fonts, radius,
and the signature element's styles. Every component reads from it. Concretely:

- **Colors** → CSS custom properties on `:root` (e.g. `--gold`, `--pink`, `--ink`, `--paper`)
- **Fonts** → the Google Fonts `<link>` in `index.html` + `--font-display` / `--font-body`
- **Signature** → the one distinctive treatment ported as a reusable class:
  - A = `.stitched` dashed-seam borders
  - B = `.tally` channel signal dots + mono timecodes
  - C = `.lang-spine` color bar + `.eye` button-eye status dots

Picking a direction is the only thing blocking the frontend build — the React structure is
identical across all three; only `tokens.css` and the `Nav` layout change.

---

## 4 · One-click launcher

**`run.bat`** at the project root:

```bat
@echo off
echo Starting PurrFacts Platform...
start "backend"  cmd /k "cd backend && venv\Scripts\activate && uvicorn main:app --reload --port 8000"
timeout /t 4 >nul
start "frontend" cmd /k "cd frontend && npm run dev"
timeout /t 3 >nul
start http://localhost:5173
```

---

## 5 · Acceptance checklist

Phase 1 is done when all of these are true:

- [ ] `run.bat` launches both servers and opens the browser
- [ ] Library shows every `.mp4` under `C:\Users\yborodulina\Downloads\Purr`
- [ ] Each card shows a real thumbnail (first frame), duration, file size, episode name
- [ ] "Scan folder" refreshes the list
- [ ] Empty + error states read clearly and tell you what to do
- [ ] Page is responsive to mobile width and keyboard-navigable (visible focus)
- [ ] Chosen design direction's tokens drive every color and font

---

## 6 · Build order for the Claude Code session

1. `main.py` + `.env.example` → confirm `/videos/scan` returns JSON
2. Vite scaffold + `tokens.css` from chosen mockup + `App.jsx` shell + `Nav`
3. `api.js` + `Library.jsx` + `VideoCard.jsx` → grid renders from the API
4. Loading / empty / error states
5. `run.bat` → full launch test against the real folder
6. Tick the acceptance checklist

Once this runs against your real clips, Phase 2 (Claude caption generation) snaps onto the
same Episode page the cards already link to.
