# Viewing History Design

## Goal

Add a third primary web surface, **«История»**, alongside **«Сегодня»** and **«Медиатека»**. It should let the user see films/shows associated with the currently selected target (`primary`, `partner`, or a group such as `couple`) ordered by the most recent time that viewing/review feedback was added or updated.

The screen must preserve the current target model: switching **Я / Партнёр / Вместе** changes the history to that target, just as it changes the rest of the web experience.

## User-visible behavior

- Add **«История»** to the primary navigation.
- Add a hash route `#/history?target=<target>`.
- Show one row/card per work, newest activity first.
- Each item shows:
  - activity date/time when available;
  - poster;
  - Russian title (fallback to original title/id);
  - year;
  - rating and/or reaction when present;
  - short feedback summary when present.
- Clicking an item opens the existing work detail page with the same active target.
- When an existing review is changed, that work moves to the top according to the new update timestamp.
- Empty history gets a concise empty state rather than falling back to unrelated works.

## Target semantics

History follows the same target lookup already used by the detail page:

- viewer target (`primary`, `partner`) reads `work.viewer_signals[target]`;
- group target (`couple`) reads `work.group_signals[target]`.

A viewer work is eligible when its target signal contains meaningful viewing/review state (`viewing`, `rating`, `reaction`, or `feedback`). A group work is eligible when its group signal contains review state (`rating`, `reaction`, or `feedback`), because group targets intentionally cannot carry `viewing` state.

This keeps the behavior aligned with the existing data model instead of inventing aggregate group history from member signals.

## Activity timestamp

Canonical target signals already support `history[]` entries with an exact service-generated `at` timestamp and `previous/current` snapshots. The web manifest already exports `viewer_signals` and `group_signals`, so no new web-export channel is required.

For sorting, derive the work's latest target activity as follows:

1. Use the newest valid `history[].at` entry for that target when present.
2. For a current signal with no history entry (legacy/first-write data), fall back to `work.provenance.updated_at`, then `created_at`.
3. If only a date is available, treat it as day precision and use work id as a deterministic tie-breaker.

To make future first-time feedback precise, change `apply_feedback_updates()` so **every actual target update**, including the first one, appends a `history` entry. For first writes, `previous` is `{}` and `current` contains the components written in that operation. Existing schema already permits this, so no canonical schema migration is required.

The history page only needs the latest activity per work; it does not expose every historical revision of a review in this version.

## Frontend structure

Create `web/src/features/history/` with:

- `HistoryPage.tsx` — page rendering and links;
- `selectors.ts` — target signal selection, latest-activity derivation, deterministic sorting, and display model;
- `history.css` — responsive timeline/list styling;
- unit tests for selectors/page behavior.

Update:

- `web/src/app/router.tsx` with `historyHref()` and `/history` route;
- `web/src/app/AppShell.tsx` with the new primary navigation link.

Reuse existing poster URL helpers, typography/tokens, target switching, and work detail links. Do not introduce a new design system or navigation pattern.

## Canonical mutation change

Update `media/service/mutate.py` so `apply_feedback_updates()` appends a history event whenever one or more of `viewing`, `rating`, `reaction`, or `feedback` actually changes, regardless of whether that component existed before.

History entries remain service-owned; commands do not accept timestamps from the model/user. No changes are required to the command schema or vocabulary.

## Compatibility

- Existing canonical YAML remains valid.
- Existing history entries remain valid.
- Legacy signals without `history` remain visible through the provenance fallback.
- Metadata refreshes can still change work-level `provenance.updated_at`; once a target has an exact history event, that target history timestamp takes precedence, so future ordering is not affected by TMDB refreshes.
- This design intentionally does not attempt to reconstruct exact historical timestamps that were never stored.

## Testing

Backend tests:

- first feedback write creates a history entry with exact `at`;
- subsequent update appends another history entry;
- no-op update does not append history;
- existing validation/rebuild behavior remains green.

Frontend tests:

- `historyHref()` preserves target;
- selected viewer/group signal is respected;
- latest exact history timestamp wins over provenance;
- provenance fallback works for legacy signals;
- entries sort newest-first with deterministic tie-breaking;
- changing target changes visible history;
- clicking a history item preserves target in the work URL;
- empty state renders correctly.

Verification before completion:

- Python test suite and media validation/rebuild/doctor checks;
- web unit tests and TypeScript typecheck;
- production web build;
- Playwright responsive/a11y checks, including the new navigation item/history route where applicable.

## Out of scope

- Editing reviews from the history page.
- A full audit UI showing every previous review revision.
- Reconstructing exact timestamps for legacy records from Git history.
- Combining viewer histories into a synthetic `couple` history when no group signal exists.
- Pagination/virtualization unless the current dataset demonstrates a real performance need.
