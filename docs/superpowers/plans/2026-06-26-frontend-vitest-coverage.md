# Frontend Vitest+RTL Coverage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write Vitest + React Testing Library tests for every source file in `frontend/src/` (except `main.jsx`) and reach ≥ 90% coverage on all four metrics.

**Architecture:** One test file per source file, all in `src/__tests__/`. API (`src/api.js`) is mocked with `vi.mock` in every consumer test; tested directly in `api.test.js` by stubbing `globalThis.fetch`. Pages are rendered in `MemoryRouter`; `useParams` is mocked for Episode.

**Tech Stack:** Vitest 2, React Testing Library 16, @testing-library/user-event 14, jsdom 25, @vitest/coverage-v8 2.

## Global Constraints

- No TypeScript — plain `.js` / `.jsx`
- No real HTTP requests — all `fetch` calls mocked
- `"type": "module"` in package.json — ESM-only, no `require()`
- vitest config excludes `src/main.jsx` from coverage
- Coverage thresholds: statements 90, branches 90, functions 90, lines 90
- All test files live under `frontend/src/__tests__/`
- Run coverage: `npm run coverage` (from `frontend/` dir)

---

### Task 1: api.test.js — test all six API functions via mocked fetch

**Files:**
- Create: `frontend/src/__tests__/api.test.js`

- [ ] Write test file with fetch stubbed via `vi.stubGlobal`
- [ ] Run coverage and verify api.js hits 90%+
- [ ] Commit

---

### Task 2: Simple component tests — StatusTag, Pagination, VideoCard

**Files:**
- Create: `frontend/src/__tests__/StatusTag.test.jsx`
- Create: `frontend/src/__tests__/Pagination.test.jsx`
- Create: `frontend/src/__tests__/VideoCard.test.jsx`

- [ ] Write StatusTag tests (all 6 statuses + unknown fallback)
- [ ] Write Pagination tests (null when pages≤1, buttons, prev/next disabled, active)
- [ ] Write VideoCard tests (thumbnail, no thumbnail, duration, size, languages, status)
- [ ] Run coverage
- [ ] Commit

---

### Task 3: CaptionGrid.test.jsx — grid render, blur-save, edited badge, errors

**Files:**
- Create: `frontend/src/__tests__/CaptionGrid.test.jsx`

Mock: `vi.mock('../api.js')`

- [ ] Write empty-captions test
- [ ] Write grid-render test (4 lang rows, 3 platform headers)
- [ ] Write blur-save test (change textarea, blur → saveCaption called)
- [ ] Write "edited" badge test (after successful save)
- [ ] Write save-error test
- [ ] Write YouTube-title test (title input present for youtube column)
- [ ] Run coverage
- [ ] Commit

---

### Task 4: Library.test.jsx — load, scan, filter, pagination, error, empty

**Files:**
- Create: `frontend/src/__tests__/Library.test.jsx`

Mock: `vi.mock('../api.js')`

- [ ] Write auto-scan-on-mount test
- [ ] Write episodes-render test
- [ ] Write scan-button test
- [ ] Write status-filter test
- [ ] Write pagination test
- [ ] Write error-state test
- [ ] Write empty-state test
- [ ] Run coverage
- [ ] Commit

---

### Task 5: Episode.test.jsx — load, import, errors, invalid id

**Files:**
- Create: `frontend/src/__tests__/Episode.test.jsx`

Mock: `vi.mock('../api.js')`, `vi.mock('react-router-dom', ...)`

- [ ] Write loads-video-and-captions test
- [ ] Write import-button test
- [ ] Write import-result-display test
- [ ] Write import-error (result.detail) test
- [ ] Write invalid-id test
- [ ] Write video-error test
- [ ] Run coverage
- [ ] Commit

---

### Task 6: App.test.jsx — route smoke tests

**Files:**
- Create: `frontend/src/__tests__/App.test.jsx`

Mock: `vi.mock('./api.js')` (and react-router-dom useParams for episode route)

- [ ] Write route tests for /, /queue, /dashboard, /settings
- [ ] Run full coverage — confirm all metrics ≥ 90%
- [ ] Commit everything: `git add frontend/src/__tests__/ frontend/src/setupTests.js`

---
