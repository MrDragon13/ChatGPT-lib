# Media Legacy Review Reassessment & Explicit Evidence Backfill — Design

**Date:** 2026-10-05  
**Status:** proposed for implementation planning after written-spec review  
**Base revision:** `35afaca898eae6937066f230906b41af0e1f6690`  
**Stage A baseline:** `media/baselines/intelligence-stage-a.json`  
**Stage A canonical input digest:** `sha256:98e9dc4521e69ee5273e302fc40cc1e5fc3d53b119e2c7637475ac45cce43fbf`

## 1. Context

Media Intelligence Stage A made recommendation directionality and observability safer, but a large part of the `primary` history predates the modern structured review flow. Many records were created when the product behaved closer to a review page: old ratings may be inferred, feedback may be free-form, and explicit structured signals are sparse.

The pilot exists to recover **fresh, current, explicit human evidence** from those historical records without contaminating it with old values, without manufacturing semantics from user reaction, and without allowing the same work to loop back into reassessment automatically.

This revision deliberately separates human reassessment from semantic enrichment. Semantic fingerprints are not updated during this pilot; vocabulary/provenance work is a separate later cycle.

## 2. Goals

The pilot must:

1. revisit the historical `primary` viewed cohort exactly once per pilot epoch;
2. collect fresh user evidence without anchoring on the old rating/review by default;
3. preserve historical feedback through existing `history` behavior when a mutation occurs;
4. support `confirmed_unchanged` as a first-class outcome when the user independently confirms already-current explicit data;
5. persist progress safely enough that an interrupted session does not make the user repeat completed human work;
6. prevent automatic reassessment loops;
7. prioritize early pilot coverage across contrasting evidence strata rather than letting the large cluster of `8/10` ratings dominate the first sessions;
8. keep semantic enrichment out of scope until vocabulary/provenance work is ready;
9. measure pilot progress against the frozen Stage A baseline after every session;
10. preserve the existing typed-operation / deterministic-transaction / guarded-merge trust model;
11. produce enough documentation that the pilot can be resumed correctly in a later conversation;
12. leave a durable pilot ledger that Stage B can use to relate reassessed works back to their pre-pilot state.

## 3. Non-goals

This pilot does **not**:

- redesign recommendation ranking, affinity weighting or assessment scoring;
- define Stage B benchmark metrics or leakage policy;
- update work semantic fingerprints;
- revise or expand the 42-term controlled vocabulary;
- add semantic provenance fields such as `vocab_version`, `enriched_at` or `enriched_by`;
- reassess `partner` or `couple` evidence;
- infer explicit preference from historical text without fresh confirmation;
- bulk-refresh provider metadata;
- treat similarity as preference;
- include collection reassessment in v1;
- automatically reopen an already reviewed work because later data changes.

## 4. Core evidence separation

The existing four-layer model remains authoritative:

1. factual work metadata;
2. work semantic fingerprint;
3. user evidence — viewing/rating/reaction/feedback;
4. inferred taste hypotheses.

This pilot changes only layer 3 and, at milestone boundaries, may regenerate layer 4 through the existing inferred-preference route.

Layer 2 is explicitly deferred.

## 5. Why semantic enrichment is separated

Current semantic coverage is still sparse and the semantic contract is not yet versioned for enrichment provenance. Therefore writing fingerprints during human sessions would couple confirmed human evidence to a semantic layer that is expected to change.

The sequence becomes:

1. **Legacy Review Reassessment / Explicit Evidence Backfill** — this pilot;
2. semantic vocabulary/provenance work;
3. targeted semantic enrichment batch;
4. Stage B evaluation/ground-truth design and implementation.

The reassessment pilot must not call `set_semantic_fingerprint`.

## 6. Pilot identity and ledger location

The pilot ledger path is fixed:

`media/pilots/legacy-reassessment-primary.json`

The initial pilot identity is:

`primary-legacy-v1`

The ledger is operational pilot state, not canonical taste/media truth. Ratings, reactions, feedback summaries/signals and semantic fingerprints are never duplicated into it.

The ledger is versioned and retained after completion. It is archived only later, as a separate developer change, after Stage B no longer needs it as an active pilot artifact.

## 7. Frozen cohort

The cohort is frozen from canonical state at pilot initialization against base revision `35afaca898eae6937066f230906b41af0e1f6690`.

Membership is defined by **viewing status**, not by presence of feedback text.

Included statuses:

- `watched`;
- `partial`;
- `dropped`;
- `forgotten`.

Excluded status:

- `unwatched`, regardless of whether a legacy summary such as “Не смотрел.” is present.

Only canonical works are in v1. Collections are excluded even though collection ratings contribute to profile aggregates today.

### 7.1 Special cases

`forgotten` remains in the cohort because the old record is meaningful historical evidence. If the memory jog does not restore enough recall, the user may defer it without changing canonical media data.

`dropped` remains in the cohort because an abandoned viewing can be highly informative. It must not be normalized to `disliked` automatically; the fresh user response determines reaction/feedback.

`partial` is handled similarly to `dropped`: the viewing state itself is not treated as a sentiment.

### 7.2 Collections open question

Collection reassessment is explicitly deferred. The current Stage A baseline contains collection-level `primary` ratings that participate in profile aggregates. Stage B must decide whether collections need a separate confirmation pass, exclusion from benchmark selection, or another treatment.

## 8. Frozen strata and queue order

Because pilot completion is not guaranteed, early sessions should already contain a useful cross-section of taste evidence.

At cohort initialization, each item is assigned a frozen stratum based on pre-pilot state:

- `special` — `dropped`, `forgotten`, or `partial`;
- `low` — rating `<= 6.5`;
- `medium_low` — rating `7.0–7.5`;
- `central` — rating `8.0–8.5`;
- `high` — rating `>= 9.0`;
- `unrated_viewed` — included viewed state with no numeric rating.

Queue order is deterministic **stratified round-robin**, not “all extremes first” and not “all sparse records first”. The helper cycles across non-empty strata and uses stable work id as the final tie-breaker inside a stratum unless a more explicit frozen ordering key is defined in implementation.

Lifecycle still outranks stratum order:

1. resumable `in_progress` items;
2. fresh `pending` items in frozen stratified order;
3. stop the main pass when `pending` is exhausted;
4. only then begin a separate `deferred` pass.

This gives useful early diversity while still guaranteeing whole-cohort coverage when the pilot completes.

## 9. Unanchored reassessment contract

The first human response must be collected without showing the previous rating or previous feedback by default.

### 9.1 Phase A — unanchored prompt

The card shown before the first response contains:

- title;
- year;
- 1–2 sentence spoiler-free memory jog derived primarily from saved synopsis;
- optional director or one principal actor when useful for recognition.

It must **not** show:

- old rating;
- old reaction;
- old feedback summary/signals.

Example:

> **Бэтмен (2022)** — мрачный детектив о расследовании серии убийств в Готэме.  
> Как ты сейчас его оцениваешь? Если помнишь — что понравилось или не понравилось?

### 9.2 Historical recall is optional and second-phase

After the user has given a fresh opinion, the agent may show the previous record if doing so can help recover details or confirm whether a prior reason still applies.

If the fresh response is already sufficient, the old record need not be shown at all.

If the user explicitly asks before answering “что я раньше ставил/писал?”, the agent may reveal the old record, but the pilot must record that the response was exposed to prior evidence.

Each item stores:

`prior_exposure: none | before_response | after_response`

This provenance lets Stage B distinguish independently elicited reassessment from reassessment that may have been anchored by historical values.

## 10. Memory-jog contract

The memory jog exists only to identify the work, not to steer evaluation.

Rules:

- spoiler-free;
- 1–2 sentences;
- primarily based on stored synopsis/metadata;
- no evaluative adjectives invented by the agent;
- no old user opinion;
- no recommendation/taste hypothesis language;
- director/actor only when useful for recognition.

If stored synopsis is insufficient or missing, the agent should use available factual metadata rather than fabricate plot detail.

## 11. Ledger state model

Conceptual top-level shape:

```json
{
  "schema_version": 1,
  "pilot_id": "primary-legacy-v1",
  "pilot_status": "active",
  "target": "primary",
  "base_revision": "35afaca898eae6937066f230906b41af0e1f6690",
  "baseline_path": "media/baselines/intelligence-stage-a.json",
  "baseline_canonical_input_digest": "sha256:98e9dc4521e69ee5273e302fc40cc1e5fc3d53b119e2c7637475ac45cce43fbf",
  "cohort_revision": "35afaca898eae6937066f230906b41af0e1f6690",
  "cohort_work_ids": ["..."],
  "items": {},
  "sessions": []
}
```

Per-item lifecycle statuses:

- `pending`;
- `in_progress`;
- `reviewed`;
- `deferred`.

Per-item completion outcomes:

- `changed` — fresh explicit evidence caused a canonical feedback mutation;
- `confirmed_unchanged` — user independently confirmed already-current explicit evidence and no canonical feedback mutation was necessary;
- `deferred` — user could not or chose not to reassess now.

`reviewed` is a lifecycle state; `changed` / `confirmed_unchanged` are result categories.

`confirmed_unchanged` is valid only when the existing canonical evidence is already explicit and semantically matches the fresh response. If the old score is identical but its provenance is `inferred` or `explicit_approx`, current confirmation must still mutate canonical provenance to `explicit`, so the outcome is `changed`.

## 12. Hard anti-loop invariant

For one `pilot_id`, a work may be automatically human-reassessed at most once.

Once status is `reviewed`, the queue helper must never automatically re-add the item to `pending`, even if:

- later diagnostics change;
- ordinary feedback changes later;
- a future detector would classify the item differently;
- later model/vocabulary work changes semantic coverage.

Repeating human reassessment requires explicit user action or a new pilot epoch/version.

The session runner also keeps an in-memory `seen_work_ids` guard so one work cannot be shown twice in one session.

## 13. New typed pilot-state operations

Manual ledger merges around each session are intentionally avoided. Pilot state gets narrow typed operations that pass through the existing deterministic command pipeline and trusted path-policy system.

Three operations are introduced.

### 13.1 `reserve_reassessment_session`

Purpose: reserve the next batch before any human reassessment write is allowed.

Inputs conceptually include:

- `operation_id`;
- `pilot_id`;
- `session_id`;
- ordered work ids to reserve;
- expected ledger revision/digest.

Effects:

- only the exact pilot ledger path;
- normal `.media/operations/<operation-id>.json` audit record.

For each reserved item it stores at minimum:

- `status: in_progress`;
- `session_id`;
- reservation timestamp;
- pre-review digest of the relevant `primary` viewing/rating/reaction/feedback state;
- frozen stratum/order metadata if not already present.

### 13.2 `complete_reassessment_item`

Purpose: atomically persist one human reassessment result and advance the ledger.

Preconditions:

- matching item exists in the ledger;
- status is `in_progress`;
- `session_id` matches;
- reservation is already present on current `main`;
- current relevant feedback state matches the reserved pre-review digest, unless an explicit reconciliation path is invoked later by separate design.

If the digest does not match because another canonical feedback edit happened after reservation, the command fails closed rather than overwriting concurrent state.

Effects are one deterministic transaction:

- optionally mutate exactly the resolved canonical work feedback components;
- update derived index/profile artifacts already required by the existing feedback transaction;
- advance the ledger item to `reviewed` with `outcome: changed` or `confirmed_unchanged`, or to `deferred` with `outcome: deferred`;
- record `prior_exposure` for reviewed outcomes;
- record operation provenance sufficient to audit the result;
- write `.media/operations/<operation-id>.json`.

`confirmed_unchanged` is valid even when the canonical work file does not change.

A defer outcome changes only ledger lifecycle state and never edits canonical media evidence.

### 13.3 `close_reassessment_session`

Purpose: durably close a session and append its measured progress snapshot after all intended item completions/deferments for that session have settled on `main`.

Preconditions:

- matching `session_id` exists;
- there are no unresolved reserved items that the caller is attempting to silently skip; any intentionally unfinished items remain explicitly `in_progress` and keep the session non-closed;
- audit is computed from current canonical state, not supplied as untrusted arbitrary metrics by the caller.

Effects:

- run/derive the canonical Stage A intelligence audit against current repository state;
- append one immutable session summary/progress snapshot to the ledger;
- mark the session closed;
- write `.media/operations/<operation-id>.json`.

It does not mutate works, preferences, semantics or generated taste state.

If the user stops mid-session, the session remains open and resumes later; it is not force-closed merely to obtain an audit snapshot.

## 14. Reservation-before-write invariant

This is mandatory and tested:

> No canonical reassessment feedback write may occur for a work unless its `in_progress` reservation for the active `session_id` is already visible on current `main`.

The agent must not start collecting a batch under the assumption that a reservation PR “will merge later”. Reservation is part of the durable precondition.

This ensures interruption recovery does not depend on reconstructing missing pre-review state after canonical feedback has changed.

## 15. Why atomic feedback + ledger completion is required

Using `edit_viewing_feedback` and then a separate ledger update creates an avoidable split-brain window: feedback can merge while pilot state still says `in_progress` without a durable completion marker.

The pilot therefore uses the new completion command to combine:

- optional feedback mutation;
- ledger completion/defer transition;
- operation audit record.

This is one business operation: “the user completed or deferred reassessment of this reserved work”.

The implementation should reuse existing feedback mutation primitives rather than duplicate their rules, so history behavior and target/profile rebuilding remain consistent with Stage A.

## 16. Fresh explicit evidence normalization

Only the current user response may create new explicit evidence.

The agent may normalize clearly supported values into:

- viewing state if the user explicitly corrects it;
- rating;
- reaction;
- replacement feedback summary;
- structured feedback signals using existing vocabulary terms.

Rules:

- old v1 text is historical context only;
- `source: explicit` requires current confirmation;
- strength reflects expressed intensity, not model confidence;
- ambiguous structured term mapping is omitted rather than guessed;
- `dropped`/`partial` do not imply sentiment;
- similarity is never created from shared traits/ratings alone;
- ephemeral mood comments do not become stable preference.

## 17. History behavior

When completion changes a feedback component, existing feedback mutation semantics must preserve the old value in `history.previous` and the new value in `history.current`.

No extra `legacy_review` field is introduced.

For `confirmed_unchanged`, no artificial no-op feedback history entry should be created merely to prove confirmation; the ledger outcome provides the confirmation provenance.

## 18. Session lifecycle

Default batch size: **5 works**.

A normal session is:

1. build next deterministic batch from ledger/strata;
2. reserve it durably on `main` with `reserve_reassessment_session`;
3. present each item unanchored;
4. collect fresh response;
5. optionally expose historical record after response or on user request;
6. atomically complete or defer each item;
7. when the whole reserved batch is resolved, close the session with `close_reassessment_session`, which records the Stage A audit snapshot;
8. run taste-hypothesis reanalysis only if a milestone condition is met.

An interrupted session resumes `in_progress` items first. Items already completed are never asked again. An interrupted session is not closed until its reserved items are resolved.

## 19. Session audit and progress measurement

Every closed session records the canonical Stage A audit through `close_reassessment_session`.

The ledger stores a compact immutable session snapshot rather than duplicating the whole audit JSON.

Snapshot fields should include at least:

- `session_id`;
- completion timestamp;
- newly reviewed count;
- newly deferred count;
- total reviewed/deferred counts;
- `primary` work rating counts by source, especially `explicit` vs `inferred`;
- `primary` structured-feedback coverage numerator/denominator;
- current canonical input digest;
- audit schema version;
- audit source/base revision provenance sufficient to compare to the Stage A baseline.

Semantic coverage is not expected to improve in this pilot and is not a success criterion.

The audit snapshot makes progress measurable and gives Stage B a timeline of explicit-evidence conversion.

## 20. Taste-hypothesis reanalysis cadence

Inferred hypotheses are explanation-only for numeric affinity aggregation after Stage A, so recalculating them after every 5-work session would create unnecessary LLM churn.

Reanalysis is triggered only:

- every **15 newly reviewed works** since the previous reanalysis;
- at the end of the main `pending` pass;
- on explicit user request.

The reanalysis rebuilds hypotheses from current raw/explicit evidence and replaces the target set through existing `set_inferred_preferences`.

Previous inferred hypotheses are never treated as independent confirming evidence.

A weaker or empty replacement set is valid.

## 21. Ground-truth relationship to Stage B

A reviewed item becomes high-quality confirmed explicit evidence, but not automatically a Stage B decision-benchmark member.

Stage B will later define benchmark selection/stratification/leakage rules.

Useful reassessment provenance available to Stage B includes:

- original frozen cohort identity;
- pre-review digest;
- completion outcome (`changed` vs `confirmed_unchanged`);
- `prior_exposure` (`none`, `before_response`, `after_response`);
- session membership/order;
- operation provenance;
- post-session audit progression.

This lets Stage B preferentially choose unanchored confirmations or analyze how often historical inferred/explicit values moved.

## 22. Failure and resume semantics

The workflow is fail-closed.

- reservation must be merged before reassessment writes;
- completion without matching reservation fails;
- completion against a changed pre-review digest fails as a concurrency conflict;
- a failed completion leaves the item `in_progress`;
- a failed defer leaves the item `in_progress`;
- a session with unresolved `in_progress` items cannot be closed;
- a successfully reviewed item cannot be completed a second time automatically;
- unknown/ambiguous work identity blocks mutation;
- canonical work evidence is never reconstructed from ledger copies because the ledger does not duplicate evidence content.

Because completion is atomic across optional feedback mutation + ledger transition, interruption cannot create “feedback changed but completion marker missing” as an expected success path.

## 23. Path-policy and trust boundary

The implementation is a developer change and must receive manual review.

Existing operations must remain unable to mutate:

`media/pilots/legacy-reassessment-primary.json`

The new pilot operations receive only narrow allowlists.

Conceptually:

`reserve_reassessment_session`:

- `media/pilots/legacy-reassessment-primary.json`;
- `.media/operations/*.json`.

`complete_reassessment_item`:

- `media/pilots/legacy-reassessment-primary.json`;
- exactly one resolved `media/data/works/*.yaml` work when feedback changes;
- existing derived `media/generated/index.jsonl` / profile paths required by reused feedback primitives;
- `.media/operations/*.json`.

`close_reassessment_session`:

- `media/pilots/legacy-reassessment-primary.json`;
- `.media/operations/*.json`.

The declarative policy may need wildcard paths, but runtime planning must enforce the exact resolved work/entity set. Privileged workflow trust remains based on policy from trusted `main`, not PR-head executable code.

No semantic/vocabulary path is authorized by the reassessment operations.

## 24. Archive lifecycle

At pilot completion:

- set `pilot_status: completed`;
- store final audit snapshot;
- preserve the full ledger in place while Stage B is being designed/constructed.

Only after Stage B no longer requires an active ledger path should a separate developer change move it under an archive location such as:

`media/pilots/archive/legacy-reassessment-primary-v1.json`

Archive movement must not alter the historical contents beyond archival metadata required by the chosen format.

## 25. Documentation deliverables

Documentation is part of completion.

Implementation must update as applicable:

- `media/AGENTS.md` — reassessment route, unanchored-first UX, reservation/completion rules, deferred behavior;
- `docs/architecture/intelligence.md` — confirmed explicit evidence, separation from semantics, milestone reanalysis;
- `docs/architecture/write-pipeline.md` — new pilot typed operations and atomic completion boundary;
- `docs/reference/media-commands.md` — schemas/behavior for pilot operations;
- a pilot runbook under `docs/` covering start/resume/session close/deferred pass/audit/reanalysis;
- `docs/status/current.md` — current capability and limitations;
- this design spec;
- implementation plan after written-spec approval.

The runbook must emphasize that old ratings/reviews are hidden before the first response unless the user asks for them.

## 26. Test requirements

Implementation is incomplete without tests for the following.

### 26.1 Cohort and ordering

- `unwatched` never enters the cohort even when summary text is non-empty;
- `watched`, `partial`, `dropped`, `forgotten` are handled according to contract;
- frozen strata are deterministic;
- stratified round-robin order is deterministic;
- deferred items do not interrupt the main pending pass;
- reviewed items never re-enter automatically.

### 26.2 Unanchored UX payload

- pre-response card does not expose old rating/reaction/feedback;
- post-response history exposure is allowed;
- user-requested pre-response exposure records `prior_exposure: before_response`;
- default independent reassessment records `none` or `after_response` as appropriate.

### 26.3 Reservation and atomic completion

- no completion is accepted before the reservation is visible in the repository state being processed;
- wrong `session_id` fails closed;
- changed pre-review digest fails closed;
- completion updates work + ledger atomically in the deterministic transaction;
- an identical numeric score with old `inferred`/`explicit_approx` provenance mutates provenance to `explicit` and yields `changed`;
- `confirmed_unchanged` advances ledger without creating artificial feedback history;
- completing an already reviewed item fails/idempotently reports terminal state without a second human reassessment;
- defer changes ledger only;
- session close fails while reserved items remain unresolved;
- session close computes progress from canonical state and appends exactly one immutable snapshot.

### 26.4 Path policy / security

- all pre-existing Stage A operations reject `media/pilots/legacy-reassessment-primary.json`;
- `reserve_reassessment_session` cannot mutate work/generated/preferences/vocabulary/schema paths;
- `complete_reassessment_item` cannot mutate semantic/vocabulary/schema/workflow paths;
- `close_reassessment_session` cannot mutate work/generated/preferences/vocabulary/schema paths;
- operation path policy matcher corpus remains green;
- privileged auto-merge remains fail-closed for unknown operations/paths.

### 26.5 Audit/progress

- session close runs/consumes canonical audit output deterministically;
- progress snapshot reflects explicit/inferred rating changes and structured-feedback coverage;
- baseline references are preserved;
- semantic coverage is not required to move.

### 26.6 Repository validation

Full gate:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Additionally, docs/contract tests must accept the new pilot directory, ledger schema and command references.

## 27. Observability and stop conditions

Primary progress measures are:

- proportion of frozen cohort in `reviewed`;
- `changed` vs `confirmed_unchanged` counts;
- `prior_exposure` distribution;
- conversion of `primary` ratings from inferred to explicit where applicable;
- structured-feedback coverage growth;
- deferred backlog size.

The main pilot pass is complete when no `pending` or resumable `in_progress` items remain.

The deferred pass is complete when the user either reviews or explicitly leaves remaining deferred items unresolved for this pilot epoch.

Completion does not require semantic coverage growth.

## 28. Open issues intentionally deferred

The following are not decided by this pilot implementation:

1. semantic vocabulary revision;
2. semantic fingerprint provenance/versioning (`vocab_version`, `enriched_at`, `enriched_by`);
3. targeted semantic enrichment policy;
4. collection reassessment / benchmark treatment;
5. Stage B benchmark sampling and leakage controls;
6. deterministic assessment model/formula selection;
7. partner/couple reassessment.

## 29. Recommended implementation shape

The recommended implementation is deliberately narrow:

- deterministic cohort/queue/read-model helper;
- versioned pilot ledger at the exact path above;
- `reserve_reassessment_session` typed operation;
- `complete_reassessment_item` typed operation that reuses existing feedback mutation primitives;
- `close_reassessment_session` typed operation that computes/persists immutable audit progress;
- compact session audit snapshots;
- milestone-triggered existing taste reanalysis;
- documentation and tests as first-class deliverables.

No semantic enrichment code is added to this cycle.

## 30. Final architecture summary

The pilot flow is:

**frozen viewed cohort → stratified round-robin → durable reservation on `main` → unanchored memory jog + fresh response → optional historical recall → atomic explicit-feedback/ledger completion (or defer) → durable session close + audit snapshot → inferred-hypothesis reanalysis every 15 reviewed works / end of main pass → deferred pass → completed immutable ledger for Stage B.**

The central safety properties are:

- no old rating anchoring by default;
- no semantic/user-reaction conflation;
- no canonical reassessment write before durable reservation;
- no split completion between feedback and ledger;
- no automatic reassessment loop;
- no silent overwrite after concurrent feedback changes;
- measurable progress against the frozen Stage A baseline.
