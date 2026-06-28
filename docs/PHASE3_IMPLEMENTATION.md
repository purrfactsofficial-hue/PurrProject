# Phase 3 — Implementation Plan (Scheduler + Queue)

**Goal:** Open a captioned episode → pick a date → the system fills the right 8 PM-per-timezone
slot for each channel → one click schedules the posts → the Queue page shows them as a live
table you can cancel or reschedule.

**Time:** 2–3 days. The `/create`, `/queue`, cancel, and retry endpoints already exist; this
phase adds validation, rescheduling, the DST fix (done), and the two frontend pages.

---

## 0 · Foundation fix already applied — DST-correct times

The scaffold used fixed UTC offsets, which are only right in summer. Replaced with a
local-hour + IANA-timezone model (`POSTING_SLOTS` in `config.py`) resolved per date via
`zoneinfo`. Verified:

| Language | Slot | Summer (Jul) UTC | Winter (Dec) UTC |
|---|---|---|---|
| EN (America/New_York) | 8 PM | 00:00 (+1 day) | 01:00 (+1 day) |
| UK (Europe/Kyiv) | 8 PM | 17:00 | 18:00 |
| ZH (Asia/Hong_Kong) | 8 PM | 12:00 | 12:00 (no DST) |
| FR (Europe/Paris) | 8 PM | 18:00 | 19:00 |

Every channel now fires at a true 8 PM local on any date. `compute_utc_slot(date, lang)`
lives in `routes/schedule.py`.

---

## 1 · Cadence & scope (from your decisions)

- **One post per channel per day**, evening slot only. The afternoon slot is deferred until
  after week three, so the scheduler creates a single time per language for now.
- **English-first launch.** Scheduling must support a **subset** of languages/platforms, not
  only all 12 at once — so you can ship English while the others stay in draft.
  `/schedule/create` already accepts `languages` and `platforms` arrays; the UI just needs to
  expose the selection.

---

## 2 · Backend — to finish

### Validation before scheduling (`routes/schedule.py`)

- [ ] **Captions present:** for each selected `language × platform`, confirm a `captions` row
  exists. If any are missing → return `409` with a list:
  `"Can't schedule — no caption for uk/tiktok, zh/instagram. Import or write them first."`
  Never half-schedule.
- [ ] **No past slots:** if `compute_utc_slot(date, lang)` is already in the past, skip that
  language and report it: `"FR 8 PM has already passed for that date — pick the next day."`
- [ ] **Double-booking guard (soft):** if a channel already has a `scheduled`/`published` post
  on the same local date, include a warning (don't block — you may intentionally post twice
  later): `"EN/youtube already has a post that day."`

### Reschedule endpoint (new)

- [ ] `PATCH /schedule/{post_id}` body `{ "date": "YYYY-MM-DD" }` → recompute the UTC slot for
  that post's language and update `scheduled_for`. Reject if the post is already `published`.
- [ ] `PATCH /schedule/episode/{video_id}` body `{ "date": "..." }` → move every still-scheduled
  post for that episode to a new date in one call (bulk reschedule).

### Already done

- [x] `POST /schedule/create` — inserts posts at DST-correct slots
- [x] `GET /schedule/queue` — all posts sorted by time
- [x] `DELETE /schedule/{post_id}` — cancel
- [x] `POST /schedule/{post_id}/retry` — reset failed → scheduled

---

## 3 · Frontend — Episode page scheduling step (Atelier)

After the caption grid (Phase 2), add a scheduling panel:

- [ ] **Language / platform selector** — four language toggles × three platform toggles,
  defaulting to whatever has captions. English-only is one tap.
- [ ] **Date picker** — pick the episode's post date. Show a **"next free date"** hint per
  channel so you don't double-book (one-a-day cadence).
- [ ] **Slot preview** — a small read-out of exactly when each selected channel will fire, in
  *both* the audience's local time and **your Pacific time**, e.g.
  `UK · 8:00 PM Kyiv → 10:00 AM your time`. This ties scheduling back to the live-reply windows.
- [ ] **"Schedule selected"** button → `POST /schedule/create` with the chosen arrays →
  on success, route to the Queue.
- [ ] Validation errors render inline in interface voice (no stack traces).

---

## 4 · Frontend — `pages/Queue.jsx` (Atelier)

The operations table — the page you'll glance at daily.

- [ ] **Table** of all posts sorted by `scheduled_for`, grouped by date with a stitched-seam
  divider per day.
- [ ] **Columns:** time (audience-local + your-time), episode, language, platform, channel,
  status, actions.
- [ ] **Status badges** (extend the Atelier tag styles):
  `scheduled` (gold) · `publishing` (pulsing pink) · `published` (green) · `failed` (red) ·
  `cancelled` (muted).
- [ ] **Row actions:** cancel (→ DELETE), reschedule (date popover → PATCH). Failed rows show
  the error + a retry button (wired fully in Phase 4).
- [ ] **Filters:** status, language, platform — reuse the Library chip component.
- [ ] **Auto-refresh:** poll `/schedule/queue` every 30 s so status changes appear without a
  manual reload.

---

## 5 · Observability in Phase 3 (before real posting exists)

The scheduler runs in `DEV_MODE`, so `check_and_post` flips due posts to `published` with a
fake `platform_post_id` at their scheduled minute. That means you can fully exercise the Queue
now: schedule a slot two minutes out, watch it go `scheduled → publishing → published` live —
without any platform integration. Real publishing replaces the DEV_MODE branch in Phase 4.

---

## 6 · Acceptance

- [ ] Schedule the Pizza episode (all four languages) for a summer date → Queue shows the posts
  at EN +1 day 00:00, UK 17:00, ZH 12:00, FR 18:00 UTC.
- [ ] Schedule the same for a December date → UK 18:00, FR 19:00, EN +1 day 01:00, ZH 12:00.
- [ ] Try to schedule a language with a missing caption → blocked with a message naming the cell.
- [ ] Schedule English only → exactly the EN posts appear; other languages untouched.
- [ ] Cancel one row → it flips to `cancelled`; reschedule another → its time updates.
- [ ] A slot two minutes out flips to `published` on its own (DEV_MODE), proving the loop.
- [ ] Queue shows each time in both audience-local and your Pacific time.

---

## 7 · Build order for the Claude Code session

1. Caption-presence + past-slot validation in `/schedule/create` → confirm with a missing cell
2. `PATCH` reschedule endpoints → confirm a post moves dates
3. Episode-page scheduling panel (selector + date + slot preview) → schedule English-only
4. `Queue.jsx` table + status badges + filters → renders from `/queue`
5. Cancel + reschedule controls → round-trip to the API
6. 30 s polling → watch a DEV_MODE post publish itself
7. Tick acceptance

Phase 4 then swaps the DEV_MODE branch for the real YouTube / Instagram / TikTok services — the
Queue, statuses, and scheduling logic stay exactly as built here.
