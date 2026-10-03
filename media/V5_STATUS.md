# Media Intelligence v5 — continuity handoff

Status date: 2026-10-03

## Current state

Media Intelligence v5 has completed the planned implementation phases and the Phase E pilot. The canonical source of truth remains Git/YAML; generated profiles, index, database, taste contexts, and the web manifest remain derived read models.

The normal user write path is still one strict typed command on a same-repository `media/op-*` branch, processed by deterministic Python, followed by an exact-head dispatch-only `Media Check`, guarded auto-merge when eligible, and exact-merge-SHA Pages publication.

## Phase E / Task 11 — semantic and taste pilot

Representative semantic fingerprints were enriched first, then inferred preferences were reanalysed from raw/explicit evidence rather than from previous inferred output.

### primary

- Published through PR #57.
- Inferred hypotheses intentionally remain medium-confidence:
  - intrigue + active problem solving;
  - engaging execution.
- Evidence includes concrete works such as `knives-out-2019`, `sherlock-bbc`, `ready-player-one-2018`, `deja-vu-2006`, and `game-night-2018`.
- Previous inferred hypotheses were not used as independent evidence for replacement hypotheses.

### partner

- Published through PR #59.
- Kept deliberately sparse because raw partner evidence is sparse.
- One low-confidence hypothesis only: `visuals.strong`.
- Do not expand partner taste merely to make the profile look complete.

### couple

- Published through PR #60.
- One low-confidence shared hypothesis only: `entertainment.engaging`.
- Evidence combines real signals from both targets on `deja-vu-2006` and a second joint signal on `game-night-2018`.
- `visuals.strong` was intentionally not promoted to a couple hypothesis because the raw evidence contains a real disagreement. Couple reasoning must expose such disagreement rather than average it away.

## Pipeline regressions found by the pilot

The production pilot exposed two workflow defects and both were fixed with RED → GREEN regression coverage before the pilot continued:

1. PR #56 — canonical v5 outputs such as `media/preferences/inferred/**` were not staged with generated profiles, which could make exact-head `rebuild --check` detect stale generated output.
2. PR #58 — optional output directories such as `media/data/interactions` could make `git add` fail when the directory did not yet exist. Optional canonical paths are now staged conditionally while newly created outputs are still captured.

The successful primary retry after those fixes served as the production regression test of the corrected staging path.

## Phase E / Task 12 — recommendation smoke

### Internal-only route

Read-only smoke for `primary` used the local library as the candidate boundary. `accountant-2016` (`The Accountant` / `Расплата`) is locally stored and explicitly `unwatched` for primary, so it is a valid internal candidate. Its crime/thriller premise is compatible with the current medium-confidence inferred pattern around intrigue/problem solving.

Important wording rule: that fit is an inferred pattern, not an explicit statement by the user.

### External discovery route

External discovery was exercised with current provider/web facts and candidates outside the local catalog. `Black Bag` and `Relay` were used as representative discovery candidates. The local library acted as memory, evidence, and exclusion state rather than the candidate boundary.

External recommendations do not need to be added to the canonical library merely because they were suggested.

### Explainability

Recommendation explanations should separate:

- explicit user evidence;
- inferred taste hypotheses and their confidence;
- factual/semantic traits of the candidate;
- ephemeral request constraints.

Never phrase an inferred hypothesis as something the user explicitly said. For `couple`, surface agreement/disagreement from the underlying member evidence instead of presenting a hidden averaged preference.

No recommendation interaction was persisted during this engineering smoke because no real user selected, rejected, deferred, or marked a candidate as already watched/not interested.

## Verification evidence

Task 11 media operations completed through their authoritative exact-head gates and successful Pages publications:

- primary — Media Check #296, Pages #40;
- partner — Media Check #297, Pages #41;
- couple — Media Check #298, Pages #42.

A fresh Task 12 verification-only PR #61 was created from the post-pilot `main` solely to run `Web Check` and was closed without merge. Web Check #201 completed successfully for:

- real manifest export;
- web unit tests;
- TypeScript typecheck;
- production build;
- broker URL embedding assertion;
- static artifact scan;
- Chromium responsive/motion/accessibility/edit-feedback checks;
- review screenshots.

The whole-spec review also rechecked the core invariants covered by tests: one rating produces only weak trait evidence; repeated independent correlations may raise confidence; clear removes only named feedback components; taste context is read-only; couple disagreement is exposed without a hidden score; Phase D UI separates explicit/inferred taste and film fingerprint from personal reactions.

## Known limitations / next-version candidates

- Partner evidence is still sparse; confidence should remain conservative until real observations accumulate.
- Semantic fingerprint coverage is representative rather than exhaustive. Enrich more works when recommendation quality needs it, not as filler.
- Recommendation interaction history is effectively empty until real recommendation lifecycle events occur. Persist only meaningful `recommended`, `selected`, `already_watched`, `not_tonight`, or `not_interested` events.
- External discovery currently relies on the agent/server-side intelligence boundary. Static Pages must remain useful without live model/provider access.
- Do not turn temporary mood/runtime constraints or `not_tonight` into stable taste.
- If future recommendation ranking becomes more automatic, preserve provenance and explanation rather than collapsing evidence into one opaque score.

## Safe resume point

Start from current `main`, read `media/AGENTS.md`, then prefer the shortest route that matches the user intent:

- read/lookup → local derived read models;
- internal recommendation → local candidates only;
- general recommendation → external discovery by default, local data for taste/exclusions;
- normal data write → one typed media operation;
- taste reanalysis → replacement inferred hypotheses from raw/explicit evidence only;
- semantic enrichment → film traits only, never implicit viewer preference;
- architecture/vocabulary/maintenance → explicit developer/manual path.

Before claiming a new release or workflow change complete, run the full relevant validation again and verify the post-merge Pages result.
