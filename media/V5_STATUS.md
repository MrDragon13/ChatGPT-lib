# Media Intelligence v5.1 — continuity handoff

Status date: 2026-10-03

## Current state

Media Intelligence v5 completed its planned implementation phases and Phase E pilot. Media Intelligence v5.1 is now being implemented in draft PR #68 for two additions: read-only candidate assessment and explicit target-specific work similarity.

The canonical source of truth remains Git/YAML; generated profiles, index, database, taste contexts, recommendation contexts, and the web manifest remain derived read models. The normal user write path remains one strict typed command on a same-repository `media/op-*` branch, processed by deterministic Python, followed by an exact-head dispatch-only `Media Check`, guarded auto-merge when eligible, and exact-merge-SHA Pages publication.

## v5.1 implementation — Task 1–4

Task 1–4 are complete and GREEN in PR #68.

### Task 1 — contracts and canonical validation

- Added strict typed operations `set_work_similarity` and `remove_work_similarity`.
- Added read-only `assess_candidate` request contract.
- Persistent external similarity refs require stable TMDB/IMDb identity; title-only persistent guesses are rejected.
- Added canonical `work-similarity` schema and validation for target/work/vocabulary identity, self-links, duplicate/reversed pairs, and deterministic ordering.

### Task 2 — persistence, reconciliation, workflow policy

- Explicit similarity is stored under `media/data/relations/similarity/` as one target-specific unordered pair.
- Canonical↔canonical, canonical↔external and external↔external endpoint normalization is supported.
- Repeated assertion is an upsert of the current relation; removal is idempotent and independent of endpoint order.
- Adding a canonical work reconciles matching stable external endpoints in the same transaction; self-links collapse and collisions resolve deterministically.
- Media Command stages relation outputs. Guarded auto-merge has explicit similarity-only set/remove arms, while work-creation routes allow only deterministic similarity reconciliation paths.

### Task 3 — read models and candidate assessment

- Taste context exposes explicit similarity evidence separately from affinities/preferences.
- Recommendation context can attach candidate-level similarity evidence without changing candidate rank or inventing a score.
- `assess_candidate` assembles target taste context, candidate identity/fingerprint when available, and matching explicit similarities.
- Assessment is read-only. The Python layer assembles evidence; the cinema assistant produces the qualitative fit/confidence explanation. No opaque deterministic match score or fake precise probability is persisted.
- External assessment can remain external and does not create a canonical work.

### Task 4 — manifest v3 and web projection

- The exporter now emits manifest v3.
- Each web work receives target-keyed explicit similarities as a derived projection.
- One canonical undirected relation is projected symmetrically onto both canonical work pages.
- canonical↔external similarity is shown only on the canonical page as a lightweight external card; it does not fabricate a local route or canonical work.
- Work detail renders `Похожие фильмы` → `По твоему мнению` for the active target.
- Frontend accepts manifest v1/v2/v3 during staged static deployment overlap.

Task 4 exact-head evidence: Media Dev Check #91 and Web Check #215 both passed on the same head. Web Check included real manifest export, unit tests, TypeScript typecheck, production build, broker URL assertion, static credential scan, responsive/motion/accessibility/edit-feedback browser checks, review screenshots, and artifact upload.

A browser regression found during Task 4 was fixed by RED → GREEN: the exporter had moved to v3 while the manifest loader still accepted only v1/v2. A dedicated v3 loader regression test now protects that boundary.

## Task 5 — agent/docs contract synchronization

Current work is synchronizing `media/AGENTS.md`, `media/START_PROMPT.md`, `media/README.md`, this status file, and the scenario catalog with the implemented v5.1 routes.

Required agent semantics:

- `set_work_similarity` records one explicit target-specific undirected relation;
- `remove_work_similarity` removes the same unordered pair rather than creating a negative relation;
- `assess_candidate` is read-only and returns evidence for a qualitative answer;
- explicit similarity is useful evidence/hint for recommendations and explanations, but is not a stable preference by itself;
- an external similarity/assessment endpoint does not create a canonical work;
- at most one short blocking identity clarification is allowed when a stable external identity cannot be resolved safely.

After Task 5 is GREEN, Task 6 is exact-head integration verification, whole-branch review, PR handoff, and only then marking PR #68 ready for review.

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
- explicit similarity evidence when relevant;
- ephemeral request constraints.

Never phrase an inferred hypothesis as something the user explicitly said. Similarity does not imply liking. For `couple`, surface agreement/disagreement from the underlying member evidence instead of presenting a hidden averaged preference.

No recommendation interaction was persisted during this engineering smoke because no real user selected, rejected, deferred, or marked a candidate as already watched/not interested.

## Historical verification evidence

Task 11 media operations completed through their authoritative exact-head gates and successful Pages publications:

- primary — Media Check #296, Pages #40;
- partner — Media Check #297, Pages #41;
- couple — Media Check #298, Pages #42.

A fresh Task 12 verification-only PR #61 was created from the post-pilot `main` solely to run `Web Check` and was closed without merge. Web Check #201 completed successfully for real manifest export, web unit tests, TypeScript typecheck, production build, broker URL embedding assertion, static artifact scan, Chromium responsive/motion/accessibility/edit-feedback checks, and review screenshots.

## Known limitations / next-version candidates

- Partner evidence is still sparse; confidence should remain conservative until real observations accumulate.
- Semantic fingerprint coverage is representative rather than exhaustive. Enrich more works when recommendation quality needs it, not as filler.
- Recommendation interaction history is effectively empty until real recommendation lifecycle events occur. Persist only meaningful `recommended`, `selected`, `already_watched`, `not_tonight`, or `not_interested` events.
- External discovery/current external facts still rely on the agent/server-side intelligence boundary. Static Pages must remain useful without live model/provider access.
- Explicit similarity currently has current-assertion semantics, not append-only opinion history.
- Derived/system similarity is intentionally not persisted as canonical explicit similarity and is not shown as a separate web section until a real derived source exists.
- Candidate assessment intentionally has no deterministic prediction score; the agent must preserve provenance and uncertainty in the explanation.
- Do not turn temporary mood/runtime constraints, `not_tonight`, or one similarity assertion into stable taste.

## Safe resume point

For the active v5.1 implementation, resume from PR #68 and verify its current exact head before changing anything. Task 1–4 are complete; do not redo them. Finish Task 5 docs/contracts, then execute Task 6 exact-head verification and whole-branch review.

For normal media use after v5.1 is merged, start from current `main`, read `media/AGENTS.md`, then prefer the shortest route matching intent:

- read/lookup → local derived read models;
- candidate assessment → read-only `assess_candidate`, qualitative evidence-based answer;
- explicit similarity write/remove → `set_work_similarity` / `remove_work_similarity`;
- internal recommendation → local candidates only;
- general recommendation → external discovery by default, local data for taste/exclusions/similarity anchors;
- normal data write → one typed media operation;
- taste reanalysis → replacement inferred hypotheses from raw/explicit evidence only;
- semantic enrichment → film traits only, never implicit viewer preference;
- architecture/vocabulary/maintenance → explicit developer/manual path.

Before claiming a new release or workflow change complete, run the full relevant validation again and verify the post-merge Pages result.
