# Phase 2 — Implementation Plan (Import & Review)

**Decision that reshapes this phase:** the `/purrfacts-scenario` skill now writes all 12
publishing descriptions when it builds an episode. The platform no longer calls Claude to
*generate* captions — it **imports** the skill's output, shows it for review, and saves it
for scheduling. One source of truth, no API key or cost inside the app.

**Goal:** Open an episode → its 12 descriptions load into an editable grid → review, tweak,
save → ready to schedule.

**Time:** 2–3 days. Less than the original Phase 2 (no AI service to build).

---

## The contract — `captions.json`

The skill drops one file per episode into the episode folder:

```
C:\Users\yborodulina\Downloads\Purr\Episode_Pizza\captions.json
```

```json
{
  "episode": "Pizza",
  "episode_number": 8,
  "topic_tags": { "en": "#FoodFacts", "uk": "#ФактиПроЇжу", "zh": "#食物趣聞", "fr": "#FaitsCulinaires" },
  "languages": {
    "en": {
      "youtube":   { "title": "...", "description": "...", "hashtags": ["#KidsLearning","#FunFacts","#FoodFacts","#KidsCartoon","#Shorts"] },
      "tiktok":    { "caption": "...", "hashtags": ["#KidsCartoon","#FunFacts","#FoodFacts","#KidsLearning","#CartoonForKids"] },
      "instagram": { "caption": "...", "hashtags": ["#KidsAnimation","#FunFacts","#FoodFacts","#LearnWithKids","#KidsCartoon"] }
    },
    "uk": { "youtube": {…}, "tiktok": {…}, "instagram": {…} },
    "zh": { "youtube": {…}, "tiktok": {…}, "instagram": {…} },
    "fr": { "youtube": {…}, "tiktok": {…}, "instagram": {…} }
  }
}
```

**Field rules (must match the skill's output exactly):**
- `youtube` → `title` + `description` + `hashtags` (always includes `#Shorts`)
- `tiktok` → `caption` (one line) + `hashtags` (≤5)
- `instagram` → `caption` (1–2 sentences) + `hashtags` (exactly 5)
- `#PurrFacts` present on every platform's hashtag list
- Numbers written as words in any spoken-script fields (TTS rule) — captions can use digits

**Assumption stated:** one `captions.json` per **episode folder**, covering all 4 languages.
The platform maps each language block to that language's video file in the same folder.
If you'd rather have one file per language video, say so and the importer changes one line.

---

## Backend

### Files
- [ ] `services/caption_importer.py` — find + parse `captions.json`, validate against the schema
- [ ] `routes/captions.py` — replace the old `/generate` stub with:
  - `POST /captions/import/{video_id}` — read the episode's `captions.json`, upsert all 12 rows
  - `GET  /captions/{video_id}` — return the saved grid (already stubbed)
  - `POST /captions/save` — persist edits, mark row `source='manual'` (already stubbed)
- [ ] Extend `video_scanner.py` — flag whether a `captions.json` exists for each episode
  (drives the Library status: present → "Captions ready", absent → "Draft")

### What `caption_importer.py` does
1. Locate `captions.json` in the video's episode folder
2. Validate: all 4 languages present, each with 3 platforms, required fields per platform
3. For each language × platform → upsert a `captions` row
   (`title` set for YouTube only; `hashtags` stored as a joined string)
4. Return a summary: imported / skipped / validation errors

### Validation messages (interface voice, not apologies)
- Missing file → "No captions.json in Episode_Pizza. Run /purrfacts-scenario for this
  episode, then Import."
- Missing language → "captions.json is missing the `uk` block. Fix the file and re-import."
- Missing #PurrFacts → warn, don't block: "fr/tiktok is missing #PurrFacts."

### Caption model (already updated)
`captions` now has `title` (YouTube), `caption` (description or caption text),
`hashtags`, and `source` ('skill' | 'manual').

---

## Frontend (Atelier direction)

### `pages/Episode.jsx`
- Episode header: name, episode number, the video preview (HTML5 `<video>` from the local path)
- "Import descriptions" button → calls `/captions/import/{id}`
- The review grid (see below)
- "Save & continue to scheduling" → persists, routes to the date picker (Phase 3)

### `components/CaptionGrid.jsx` — the 4×3 review grid
- Rows = languages (EN, UK, ZH, FR), columns = platforms (YouTube, Instagram, TikTok)
- Each cell is an editable card, stitched-seam border (Atelier `.stitched`):
  - YouTube cell: **Title** field + **Description** textarea + hashtag chips
  - TikTok / Instagram cell: **Caption** textarea + hashtag chips
  - Character counters (YouTube title ≤100, IG caption guidance)
  - A small "edited" mark when `source='manual'`
- Empty state (no import yet): the worktable is blank with a single line —
  "No descriptions imported. Click Import to pull them from this episode's captions.json."

### Status flow back to Library
- `captions.json` found + imported → card shows **Captions ready**
- video present, no captions → **Draft**
- once Phase 3 schedules it → **Scheduled**

---

## What the skill must output (the other half of the contract)

When you update `/purrfacts-scenario`, add a final step that writes `captions.json` with the
exact structure above. The platform importer and the skill writer must agree on:
- the filename `captions.json`
- the `languages.{lang}.{platform}` nesting
- the per-platform field names (`title`/`description` vs `caption`)

A drift on any of those three is the only thing that can break the import. Lock them together.

---

## Acceptance

- [ ] Run `/purrfacts-scenario` for Pizza → `captions.json` lands in the episode folder
- [ ] Open Pizza in the platform → Import → 12 cells fill, correctly localized
- [ ] Edit one cell, Save → reload shows the edit, row marked `manual`
- [ ] Delete `captions.json`, re-open another episode → clear empty-state message
- [ ] Malformed JSON → import fails with a specific, actionable message (not a stack trace)
- [ ] Library status updates: imported episodes read "Captions ready"

---

## Build order for the Claude Code session

1. `caption_importer.py` + the three `/captions` routes → confirm import works from a hand-written `captions.json`
2. `video_scanner.py` captions-present flag → Library status reflects it
3. `Episode.jsx` + `CaptionGrid.jsx` → grid renders the imported 12
4. Edit + save + `source='manual'` marking
5. Empty / error / malformed states
6. Tick acceptance

Phase 3 (scheduling) then reads these saved captions straight from the database — no changes
needed on its side, because the `captions` table is identical whether rows came from the skill
or were typed by hand.
