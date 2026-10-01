# Viewing History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a target-aware «История» web screen that orders watched/reviewed works by the latest exact feedback activity and keeps future first-write timestamps precise.

**Architecture:** Reuse the canonical per-target `history[]` journal already present in viewer/group signals. The backend mutation path will append a history event on every real feedback change, including the first write; the frontend will derive one latest activity item per work for the active target, with work-level provenance only as a legacy fallback. A focused `history` feature will own selection/sorting/rendering while existing router, target switching, work links, and design tokens remain unchanged.

**Tech Stack:** Python 3 + pytest + JSON Schema/YAML media model; React + TypeScript + React Router + Vitest; Vite; Playwright.

**Spec:** `docs/superpowers/specs/2026-10-01-viewing-history-design.md`

## Global Constraints

- Add «История» alongside «Сегодня» and «Медиатека» and preserve the current active target (`primary`, `partner`, or group such as `couple`).
- Viewer history reads `work.viewer_signals[target]`; group history reads `work.group_signals[target]` and never synthesizes a group timeline from member viewers.
- Sort newest-first by the newest valid target `history[].at`; use work `provenance.updated_at`, then `created_at`, only when no valid exact history timestamp exists.
- Existing canonical YAML and history entries must remain valid; no schema version bump and no vocabulary change.
- Future first-time feedback changes must create a service-owned history event; commands must not accept user/model timestamps.
- Metadata refresh timestamps must not outrank an existing exact target history timestamp.
- The page shows one item per work, not every historical revision.
- Do not add pagination/virtualization unless current data demonstrates a need.

## Review Focus

- Malformed or non-string `history[].at` entries must be ignored without hiding an otherwise valid legacy work; selector tests cover fallback behavior.
- Multiple history entries with identical timestamps must still yield deterministic ordering; selector tests pin work-id tie-breaking.
- A target signal containing only `history` but no current viewing/rating/reaction/feedback must not appear as a phantom history item; selector tests cover eligibility.
- Group targets must not accidentally inherit member `viewer_signals`; selector tests use distinct viewer/group fixtures.
- A no-op feedback command must not append duplicate history activity; backend tests cover unchanged updates.

---

### Task 1: Record exact activity for every feedback mutation

**Files:**
- Modify: `media/service/mutate.py`
- Test: `tests/media/test_mutations.py`

**Interfaces:**
- Consumes: existing `apply_feedback_updates(repo, document, updates, *, now=None)` and `_at(now)`.
- Produces: invariant that every changed target signal contains a newly appended `history` entry shaped as `{at, previous, current}`, including first writes where `previous == {}`.

- [ ] **Step 1: Write failing backend tests**

Add `test_first_signal_component_write_appends_history_entry()` using a fixture work/target that does not yet contain the supplied component. Assert `history[-1]["at"] == "2026-10-01T00:00:00Z"`, `previous == {}`, and `current` contains exactly the written component. Add `test_noop_feedback_does_not_append_history()` that executes the same current value and asserts history length is unchanged.

- [ ] **Step 2: Run the focused tests and confirm the first-write test fails**

Run: `python -m pytest tests/media/test_mutations.py -q`
Expected: FAIL on first-write history assertion with current implementation; existing mutation tests remain diagnostic.

- [ ] **Step 3: Implement the minimal mutation change**

In `apply_feedback_updates(...)`, append the history entry whenever `component_changed` is true, not only when `had_existing_component` is true. Preserve the current `previous` collection behavior so first writes naturally use `{}` and mixed updates retain snapshots only for components that already existed.

- [ ] **Step 4: Run focused backend tests**

Run: `python -m pytest tests/media/test_mutations.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add media/service/mutate.py tests/media/test_mutations.py
git commit -m "feat: timestamp first feedback activity"
```

### Task 2: Build the target-aware history selector

**Files:**
- Create: `web/src/features/history/selectors.ts`
- Create: `web/src/features/history/selectors.test.ts`

**Interfaces:**
- Consumes: `WebManifest`, `WebWork`, `TargetId`, existing TMDB image helper behavior, and current signal shapes stored as `Record<string, unknown>`.
- Produces: `HistoryItemModel` and `buildHistoryItems(manifest: WebManifest, target: TargetId): HistoryItemModel[]`.

`HistoryItemModel` fields: `id`, `title`, `year`, `posterUrl`, `rating`, `reaction`, `feedbackSummary`, `activityAt`, `activityPrecision: "exact" | "day"`.

- [ ] **Step 1: Write failing selector tests**

Cover: viewer target selection; group target selection distinct from member viewers; exact newest `history[].at` wins over provenance; malformed timestamps fall back to provenance; legacy signal without history uses `updated_at` then `created_at`; signal with only `history` is ineligible; newest-first ordering; equal timestamp/date uses ascending work id as deterministic tie-breaker; missing optional display fields do not throw.

- [ ] **Step 2: Run selector tests and confirm failure**

Run: `cd web && npm test -- --run src/features/history/selectors.test.ts`
Expected: FAIL because the history selector module does not exist.

- [ ] **Step 3: Implement selector interfaces**

Create helpers local to `selectors.ts` for safe record/string/number extraction, target signal selection, eligible current-state detection, valid history timestamp parsing, provenance fallback, and title/poster derivation. `buildHistoryItems()` must return exactly one model per eligible work and sort by activity descending, then `id` ascending.

- [ ] **Step 4: Run selector tests**

Run: `cd web && npm test -- --run src/features/history/selectors.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/history/selectors.ts web/src/features/history/selectors.test.ts
git commit -m "feat: derive viewing history timeline"
```

### Task 3: Add history routing and primary navigation

**Files:**
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/router.test.ts`
- Modify: `web/src/app/AppShell.tsx`
- Create: `web/src/features/history/HistoryPage.tsx`
- Create: `web/src/features/history/history.css`

**Interfaces:**
- Consumes: `buildHistoryItems(...)` from Task 2 and existing `workHref(...)`.
- Produces: `historyHref(target: TargetId): string`, route `/history`, and the primary-nav «История» destination.

- [ ] **Step 1: Write the failing router test**

Import `historyHref` and assert `historyHref("couple") === "#/history?target=couple"`.

- [ ] **Step 2: Run router test and confirm failure**

Run: `cd web && npm test -- --run src/app/router.test.ts`
Expected: FAIL because `historyHref` is not exported.

- [ ] **Step 3: Add the route helper and route**

Implement `historyHref(target: TargetId): string` using `URLSearchParams({ target })`, import `HistoryPage`, and register `<Route path="/history" element={<HistoryPage />} />`.

- [ ] **Step 4: Add the navigation link and page shell**

In `AppShell.tsx`, add «История» between «Сегодня» and «Медиатека» using `historyHref(target)`. Implement `HistoryPage` to read `{manifest, target}` from `useAppContext()`, call `buildHistoryItems`, render a page heading/intro, an empty state when no items exist, and linked items using `workHref(item.id, target)`. Import `history.css` from the page.

- [ ] **Step 5: Run router test and typecheck**

Run: `cd web && npm test -- --run src/app/router.test.ts && npm run typecheck`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web/src/app/router.tsx web/src/app/router.test.ts web/src/app/AppShell.tsx web/src/features/history/HistoryPage.tsx web/src/features/history/history.css
git commit -m "feat: add viewing history route"
```

### Task 4: Pin history page behavior and responsive presentation

**Files:**
- Create: `web/src/features/history/history.test.tsx`
- Modify: `web/src/features/history/HistoryPage.tsx`
- Modify: `web/src/features/history/history.css`
- Modify: `web/e2e/responsive.spec.ts`
- Modify: `web/e2e/a11y.spec.ts`

**Interfaces:**
- Consumes: history route/page from Task 3 and selector output from Task 2.
- Produces: tested target-sensitive UI, preserved target work links, empty state, and responsive/a11y coverage for the new surface.

- [ ] **Step 1: Write failing component tests**

Render the page with controlled app/router fixtures and assert: newest item appears before older item; displayed rating/reaction/summary use the selected target; switching fixture target changes visible items; item href preserves `target`; empty model renders the concise empty state.

- [ ] **Step 2: Run history component tests**

Run: `cd web && npm test -- --run src/features/history/history.test.tsx`
Expected: FAIL until page markup/test hooks and formatting satisfy the assertions.

- [ ] **Step 3: Complete history item markup and styling**

Keep one semantic link/article per work. Display activity date/time, poster when available, title/year, and only the rating/reaction/summary fields that exist. Use existing CSS variables/tokens and current responsive breakpoints/patterns; do not introduce a new global design primitive.

- [ ] **Step 4: Extend browser checks**

In `responsive.spec.ts`, visit `#/history?target=primary` at existing viewport cases and assert no horizontal overflow plus visible primary navigation/history content. In `a11y.spec.ts`, include the history route in the existing accessibility pass and ensure the new navigation/item links have accessible names.

- [ ] **Step 5: Run focused web verification**

Run: `cd web && npm test -- --run src/features/history/history.test.tsx src/features/history/selectors.test.ts src/app/router.test.ts && npm run typecheck`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web/src/features/history/history.test.tsx web/src/features/history/HistoryPage.tsx web/src/features/history/history.css web/e2e/responsive.spec.ts web/e2e/a11y.spec.ts
git commit -m "test: cover viewing history experience"
```

### Task 5: Full regression and release verification

**Files:**
- Modify only if verification exposes a feature-specific regression.

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: evidence that canonical media integrity, web tests/build, and browser checks remain green.

- [ ] **Step 1: Run complete Python/media verification**

Run:
```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```
Expected: full suite passes; validation succeeds; rebuild reports current/no generated diff; doctor reports all checks healthy.

- [ ] **Step 2: Run complete web verification**

Run:
```bash
cd web
npm test -- --run
npm run typecheck
npm run build
npm run scan:dist
npx playwright test
```
Expected: all unit tests, typecheck, production build, static scan, responsive/motion/review/a11y browser checks pass.

- [ ] **Step 3: Inspect generated/static diff boundaries**

Confirm no canonical media data was rewritten solely by this feature, no runtime database/artifact entered version control, and only planned backend/frontend/docs files changed.

- [ ] **Step 4: Commit any verification-only fixes if needed**

If and only if verification required a feature-specific correction, commit that correction with a focused message and rerun the failing command plus the full relevant suite. Otherwise make no empty commit.
