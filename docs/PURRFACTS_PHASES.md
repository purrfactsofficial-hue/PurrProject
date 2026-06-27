<!-- markdownlint-disable MD024 -->
# PurrFacts Platform — Phase-by-Phase Build Plan

A localhost web app that runs the full PurrFacts posting pipeline: pick a video →
generate captions in 4 languages → schedule across 12 channels → auto-post at the right
time per timezone → track analytics → email follower-milestone alerts.

Each phase is a self-contained Claude Code session. Work through them in order.
Check off tasks as you complete them. Don't start a phase until the previous one runs.

---

## Stack reference

| Layer | Choice |
|---|---|
| Backend | Python FastAPI (localhost:8000) |
| Frontend | React + Vite (localhost:5173) |
| Database | SQLite (`purr.db`) |
| Scheduler | APScheduler (embedded in FastAPI) |
| YouTube | google-api-python-client |
| Instagram | Graph API direct (requests) |
| TikTok | tiktokautouploader (Playwright stealth) |
| Captions | Anthropic API (claude-sonnet-4-6) |
| Email | smtplib + Gmail SMTP |

Languages: `en`, `uk`, `zh`, `fr` · Platforms: `youtube`, `instagram`, `tiktok` · 12 channels total.

Posting times (8 PM local → UTC): EN 00:00 (+1 day) · UK 17:00 · ZH 12:00 · FR 18:00.

---

## Phase 1 — Foundation

**Goal:** A running app skeleton you double-click to open. Browse local videos in a grid.

**Status: IN PROGRESS** (backend scaffold built — see existing files)

### Backend

- [x] `requirements.txt`
- [x] `config.py` — all env vars + channel names + posting hours
- [x] `database.py` — SQLAlchemy models + SQLite setup
- [x] `services/video_scanner.py` — ffprobe metadata + thumbnail extraction
- [x] `routes/videos.py` — scan, save, list, update topic
- [x] `routes/captions.py` — stub (filled in Phase 2)
- [x] `routes/schedule.py` — schedule create, queue, cancel, retry
- [x] `routes/analytics.py` — summary, followers, posts
- [x] `scheduler.py` — APScheduler jobs (posting in DEV_MODE for now)
- [ ] `main.py` — FastAPI app, CORS, mount routes, start scheduler on boot
- [ ] `.env.example` — template for all secrets

### Frontend

- [ ] Vite + React scaffold (`package.json`, `vite.config.js`)
- [ ] `App.jsx` — router + sidebar nav (Library, Episode, Queue, Dashboard, Settings)
- [ ] `pages/Library.jsx` — video grid, calls `/videos/scan`
- [ ] `components/VideoCard.jsx` — thumbnail, episode name, duration badge
- [ ] Shared API client (`api.js` with axios base URL)

### Glue

- [ ] `run.bat` — starts backend + frontend, opens browser
- [ ] `README.md` — setup steps (pip install, npm install, fill .env)

**Acceptance:** Double-click `run.bat` → browser opens at localhost:5173 → Library page
shows every .mp4 in the Purr folder with thumbnails and durations.

---

## Phase 2 — Captions

**Goal:** Select a video, click "Generate", get 12 editable captions from Claude in ~10s.

### Backend

- [ ] `services/claude_captions.py` — Anthropic API call, structured JSON output
- [ ] Caption prompt with per-platform rules (IG 5 tags, TikTok 1 line, YouTube SEO + #Shorts)
- [ ] `routes/captions.py` — fill in `/generate` to call the service and save results
- [ ] Per-language topic-tag handling (passed in request)

### Frontend

- [ ] `pages/Episode.jsx` — video preview + caption workspace
- [ ] `components/CaptionBlock.jsx` — editable textarea per language/platform cell
- [ ] 4×3 grid layout (language rows × platform columns)
- [ ] "Generate all" button + per-cell approve/edit + "Save & continue"

**Acceptance:** Pick the Pizza video → Generate → 12 captions appear correctly localized,
each editable, #PurrFacts on every one → Save persists them to the database.

---

## Phase 3 — Scheduler + Queue

**Goal:** Pick a date, system fills the right 8 PM-per-timezone slots, one click schedules 12 posts.

### Backend

- [x] `routes/schedule.py` `/create` — auto-calc UTC times per language
- [x] `/queue`, cancel, retry endpoints
- [ ] Validation: block scheduling if captions missing for a language/platform

### Frontend

- [ ] Date picker on Episode page → "Schedule all 12"
- [ ] `pages/Queue.jsx` — table of all posts sorted by time
- [ ] Status badges: scheduled / publishing / published / failed / cancelled
- [ ] Cancel + reschedule controls per row

**Acceptance:** Schedule the Pizza episode for a date → Queue shows 12 rows with correct
UTC times (EN next-day 00:00, UK 17:00, ZH 12:00, FR 18:00) → cancel one → it updates.

---

## Phase 4 — Posting engine

**Goal:** Posts actually publish at their scheduled time. Real platform integrations.

### Backend

- [ ] `services/youtube.py` — OAuth refresh + resumable upload, category 27, #Shorts
- [ ] `services/instagram.py` — container create → poll FINISHED → publish (3-step)
- [ ] `services/tiktok.py` — tiktokautouploader wrapper, cookie auth per account
- [ ] Public video URL for Instagram (Cloudflare R2 upload helper)
- [ ] Wire `_publish_post()` in `scheduler.py` to the real services (remove DEV_MODE)
- [ ] Retry logic: 3 attempts, 5-min backoff, then mark failed

### Frontend

- [ ] Queue page: live status updates (poll every 30s)
- [ ] Failed-post detail + manual retry button

**Acceptance:** Schedule a test post 2 minutes out → it publishes to the real channel →
Queue flips to "published" with the platform post ID saved.

**Gotchas to remember:**

- YouTube: one Google Cloud project per channel (quota is per-project, 6 uploads/day each)
- Instagram: needs the video at a public URL at upload time
- TikTok: cookies expire ~every few weeks — Settings should warn at 21 days

---

## Phase 5 — Analytics dashboard

**Goal:** Auto-pull stats every 6h, show charts + tables in a dashboard.

### Backend

- [ ] `services/analytics_pull.py` — YouTube Analytics API, IG Insights, TikTok stats
- [ ] Wire `pull_analytics()` job in scheduler
- [ ] Store snapshots in `analytics` table

### Frontend

- [ ] `pages/Dashboard.jsx`
- [ ] Summary row — 4 metric cards (total views, total followers, best episode, best language)
- [ ] Views-over-time line chart (4 languages, last 30 days) — recharts
- [ ] Platform comparison bar chart (YT vs TikTok vs IG per language)
- [ ] Episode performance table (views, completion rate, best platform, trend)
- [ ] Filters: date range, language, platform

**Acceptance:** Dashboard loads with real numbers → charts render → filters update them live.

---

## Phase 6 — Follower tracking + email alerts

**Goal:** Email <borodulina.iana@gmail.com> on every follower milestone.

Thresholds: every 100 up to 1,000, then every 500 above 1,000. Per channel.

### Backend

- [x] Milestone logic + duplicate-prevention in `scheduler.py`
- [ ] `services/email_notify.py` — Gmail SMTP sender + message template
- [ ] Follower count pull added to `analytics_pull.py` → `followers` table
- [ ] Gmail App Password setup documented

### Frontend

- [ ] `pages/Settings.jsx` — email address, thresholds, API key status
- [ ] Follower growth charts (12 small multiples, one per channel)

**Acceptance:** Manually insert a follower snapshot above a milestone → within one cycle,
an email arrives → `notifications_sent` records it → no duplicate on the next cycle.

---

## Phase 7 — Polish

**Goal:** Make it pleasant to use daily.

- [ ] Dark mode
- [ ] Analytics CSV export
- [ ] TikTok cookie-age warning banner (>21 days)
- [ ] `CLAUDE.md` briefing so Claude Code can run a full episode end-to-end autonomously
- [ ] Error toasts + empty states throughout

**Acceptance:** A full episode goes from Library → published across 12 channels in under
2 minutes of your time, and the dashboard tells you how it's doing.

---

## Build order summary

| Phase | What you get | Est. days |
|---|---|---|
| 1 | App opens, browse videos | 1–3 |
| 2 | AI captions in 4 languages | 4–5 |
| 3 | Schedule 12 posts in a click | 6–8 |
| 4 | Posts actually publish | 9–14 |
| 5 | Analytics dashboard | 15–19 |
| 6 | Milestone emails | 20–21 |
| 7 | Polish | 22–25 |

Claude Code does the typing each phase; you review, run, and confirm the acceptance
criteria before moving on.
