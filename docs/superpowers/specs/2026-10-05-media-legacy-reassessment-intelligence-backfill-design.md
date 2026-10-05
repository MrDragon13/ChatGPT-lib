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

1. revisit the historical `primary` viewed cohort at most once automatically per pilot epoch;
2. collect fresh user evidence without anchoring on the old rating/review by default;
3. preserve historical feedback through existing `history` behavior when a mutation occurs;
4. support `confirmed_unchanged` as a first-class outcome when the user independently confirms already-current explicit data;
5. persist progress so an interrupted session does not make the user repeat completed human work;
6. enforce anti-loop monotonicity independently in command planning and CI transition validation;
7. prioritize early pilot coverage across contrasting evidence strata while remaining taste-neutral inside each stratum;
8. keep semantic enrichment out of scope until vocabulary/provenance work is ready;
9. measure pilot progress against the frozen Stage A baseline after every closed session;
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

The ledger is retained after completion and archived only later, as a separate developer change, after Stage B no longer needs it as an active pilot artifact.

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

## 8. Frozen strata and taste-neutral queue order

Because pilot completion is not guaranteed, early sessions should already contain a useful cross-section of taste evidence.

At cohort initialization, each item is assigned a frozen stratum based on pre-pilot state:

- `special` — `dropped`, `forgotten`, or `partial`;
- `low` — rating `<= 6.5`;
- `medium_low` — rating `7.0–7.5`;
- `central` — rating `8.0–8.5`;
- `high` — rating `>= 9.0`;
- `unrated_viewed` — included viewed state with no numeric rating.

Inside each stratum the frozen order key is:

```text
sha256(pilot_id + "\0" + work_id)
```

The resulting rank/order is persisted in the frozen cohort definition. `work_id` is used only as a deterministic collision tie-breaker.

Queue order is deterministic **stratified round-robin** across non-empty strata. It is neither alphabetical nor “all extremes first”.

Lifecycle outranks stratum order:

1. resumable `in_progress` items;
2. fresh `pending` items in frozen stratified order;
3. stop the main pass when `pending` is exhausted;
4. only then begin a separate `deferred` pass.

The frozen stratum, hash order key and rank are immutable for the pilot epoch.

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
- old feedback summary/signals;
- evaluative or vocabulary-like traits such as “slow”, “dark”, “engaging”, “strong visuals”, even when a semantic fingerprint already contains them.

Example:

> **Бэтмен (2022)** — Брюс Уэйн расследует серию убийств в Готэме, связанных с загадками, оставленными преступником.  
> Как ты сейчас его оцениваешь? Если помнишь — что понравилось или не понравилось?

### 9.2 Historical recall is optional and second-phase

After the user has given a fresh opinion, the agent may show the previous record if doing so can help recover details or confirm whether a prior reason still applies.

If the fresh response is already sufficient, the old record need not be shown at all.

If the user explicitly asks before answering “что я раньше ставил/писал?”, the agent may reveal the old record, but the pilot must record that the response was exposed to prior evidence.

Instead of a single ambiguous exposure enum, each reviewed item stores:

```json
{
  "historical_exposure": {
    "timing": "none | before_initial_response | after_initial_response",
    "before_finalization": false
  }
}
```

Examples:

- history never shown: `timing=none`, `before_finalization=false`;
- user asks for old rating before giving any fresh opinion: `before_initial_response`, `true`;
- user first gives an independent opinion, then sees history and refines the final feedback: `after_initial_response`, `true`;
- history is shown only after the canonical reassessment is already finalized: `after_initial_response`, `false`.

This lets Stage B distinguish independent initial elicitation from fully unexposed final evidence.

## 10. Memory-jog contract

The memory jog exists only to identify the work, not to steer evaluation.

Rules:

- spoiler-free;
- 1–2 sentences;
- primarily based on stored synopsis/metadata;
- premise/identity facts rather than semantic/taste descriptors;
- no evaluative adjectives invented by the agent;
- no old user opinion;
- no recommendation/taste hypothesis language;
- director/actor only when useful for recognition.

If stored synopsis is insufficient or missing, the agent uses available factual metadata rather than fabricating plot detail.

## 11. Ledger state model and mutability regions

The ledger has three logically distinct regions even if they are serialized in one JSON file:

1. **frozen cohort definition** — immutable after pilot initialization;
2. **pilot lifecycle state** — mutable only through allowed monotonic transitions;
3. **closed session snapshots** — append-only and immutable after close.

Conceptual shape:

```json
{
  "schema_version": 1,
  "pilot_id": "primary-legacy-v1",
  "pilot_status": "active",
  "target": "primary",
  "base_revision": "35afaca898eae6937066f230906b41af0e1f6690",
  "baseline_path": "media/baselines/intelligence-stage-a.json",
  "baseline_canonical_input_digest": "sha256:98e9dc4521e69ee5273e302fc40cc1e5fc3d53b119e2c7637475ac45cce43fbf",
  "frozen_cohort": {
    "cohort_revision": "35afaca898eae6937066f230906b41af0e1f6690",
    "work_ids": ["..."],
    "items": {
      "work-id": {
        "viewing_status": "watched",
        "stratum": "central",
        "order_key": "sha256:...",
        "order_rank": 0,
        "pre_pilot_feedback_digest": "sha256:..."
      }
    }
  },
  "items": {},
  "sessions": [],
  "scheduled_reanalysis": {
    "last_completed": null
  }
}
```

Per-item lifecycle statuses:

- `pending`;
- `in_progress`;
- `reviewed`;
- `deferred`.

Per-item completion outcomes:

- `changed` — fresh explicit evidence caused a canonical feedback/provenance mutation;
- `confirmed_unchanged` — user independently confirmed already-current explicit evidence and no canonical feedback mutation was necessary;
- `deferred` — user could not or chose not to reassess now.

`reviewed` is a lifecycle state; `changed` / `confirmed_unchanged` are result categories.

`confirmed_unchanged` is valid only when the existing canonical evidence is already explicit and semantically matches the fresh response. If the numeric score is identical but its provenance is `inferred` or `explicit_approx`, current confirmation must mutate canonical provenance to `explicit`, so the outcome is `changed`.

## 12. Hard anti-loop and monotonicity invariants

For one `pilot_id`, a work may be automatically human-reassessed at most once.

Once status is `reviewed`, the queue helper must never automatically re-add the item to `pending`, `in_progress` or `deferred`, even if later diagnostics, ordinary feedback or model/vocabulary state change.

Repeating human reassessment requires explicit user action in a separately designed override path or a new pilot epoch/version.

The session runner also keeps an in-memory `seen_work_ids` guard so one work cannot be shown twice in one session.

Anti-loop protection is enforced twice:

1. command/service preconditions;
2. independent CI transition validation comparing trusted base state to candidate head state.

A bug in command planning must therefore still be caught before guarded merge.

## 13. Ledger snapshot validation

Ordinary repository validation checks the current ledger snapshot independently of how it was produced.

At minimum it validates:

- `pilot_id`, target, baseline refs and frozen cohort structure;
- frozen cohort is non-empty and work IDs are unique;
- frozen cohort work IDs exist canonically and their frozen membership status is one of the allowed cohort statuses;
- frozen stratum/order metadata is complete and internally consistent;
- each `reviewed` item has a terminal outcome, `historical_exposure`, `reviewed_at` and operation provenance;
- `confirmed_unchanged` does not require or fabricate a feedback-history mutation;
- closed sessions contain no items still reserved to that session as `in_progress`;
- closed session counters agree with ledger lifecycle state at close;
- `pilot_status: completed` is impossible while the main pass still has `pending` or resumable `in_progress` items.

Snapshot validation belongs in normal `validate` / repository validation because it requires only one repository state.

## 14. Base→head transition validation

Pilot-operation PRs additionally run a dedicated transition validator over **trusted base ledger → candidate head ledger**.

The transition validator is distinct from snapshot validation because it requires two revisions.

It rejects at least:

- changes to `pilot_id`, `base_revision`, baseline references or the frozen cohort definition;
- changes to frozen stratum/order/pre-pilot reference metadata;
- `reviewed` reverting to any non-terminal state;
- rewriting terminal completion outcome, exposure provenance or completion timestamp;
- deletion or mutation of previously closed session snapshots;
- reordering/replacing the historical closed-session sequence;
- illegal status transitions outside the operation contract;
- mutation of scheduled-reanalysis history backwards.

For normal pilot-operation PRs the validator implementation already lives on trusted `main`; the operation PR is restricted to data/operation paths and cannot alter validator code in the same auto-merged change.

## 15. Serialized typed pilot operations

Manual ledger merges around each session are intentionally avoided. Pilot state gets narrow typed operations through the existing deterministic command pipeline and trusted path-policy system.

Every operation that mutates the ledger carries:

`expected_ledger_digest`

computed from the exact current ledger bytes/state on authoritative `main`.

The write is rejected if current `main` no longer matches that digest.

### 15.1 `reserve_reassessment_session`

Purpose: reserve the next batch before any human reassessment write is allowed.

Inputs conceptually include:

- `operation_id`;
- `pilot_id`;
- `session_id`;
- ordered work ids to reserve;
- `expected_ledger_digest`.

Effects:

- exact pilot ledger path;
- normal `.media/operations/<operation-id>.json` audit record.

For each reserved item it stores at minimum:

- `status: in_progress`;
- `session_id`;
- reservation timestamp;
- pre-review digest of the relevant current `primary` viewing/rating/reaction/feedback state.

Frozen stratum/order metadata comes from the immutable cohort definition and is not rewritten by reservation.

### 15.2 `complete_reassessment_item`

Purpose: atomically persist one human reassessment result and advance the ledger.

Preconditions:

- matching item exists in the ledger;
- status is `in_progress`;
- `session_id` matches;
- reservation is already present on current `main`;
- `expected_ledger_digest` matches current authoritative ledger state;
- current relevant feedback state matches the reserved pre-review digest.

If another pilot write changed the ledger or another canonical feedback edit changed the work after reservation, the command fails closed rather than overwriting concurrent state.

Effects are one deterministic transaction:

- optionally mutate exactly the reserved canonical work feedback components;
- update derived index/profile artifacts already required by the existing feedback transaction;
- advance the ledger item to `reviewed` with `outcome: changed` or `confirmed_unchanged`, or to `deferred` with `outcome: deferred`;
- record `historical_exposure` for reviewed outcomes;
- record operation provenance sufficient to audit the result;
- write `.media/operations/<operation-id>.json`.

`confirmed_unchanged` is valid even when the canonical work file does not change.

A defer outcome changes only ledger lifecycle state and never edits canonical media evidence.

### 15.3 `close_reassessment_session`

Purpose: durably close a fully resolved session and append its measured progress snapshot.

Inputs conceptually include:

- `operation_id`;
- `pilot_id`;
- `session_id`;
- `expected_ledger_digest`;
- optional `scheduled_reanalysis_operation_id` when a scheduled milestone reanalysis was required and completed before close.

Preconditions:

- matching session exists;
- `expected_ledger_digest` matches current authoritative ledger state;
- all items reserved to the session are resolved (`reviewed` or `deferred`);
- if a scheduled reanalysis is due, the referenced `set_inferred_preferences` operation is already successfully present on current `main`, targets `primary`, and is newer than the previously recorded scheduled reanalysis.

Effects:

- run/derive the canonical Stage A intelligence audit from current repository state;
- append one immutable session summary/progress snapshot;
- mark the session closed;
- when applicable, persist `scheduled_reanalysis.last_completed = {reviewed_count, operation_id, completed_at}`;
- write `.media/operations/<operation-id>.json`.

It does not itself generate hypotheses or mutate canonical works. Scheduled reanalysis continues to use the existing `set_inferred_preferences` operation.

If the user stops mid-session, the session remains open and resumes later; it is not force-closed merely to obtain an audit snapshot.

## 16. Strict serialization rule

All ledger-mutating writes are serialized against authoritative `main`.

Rule:

> The next pilot write request may be created only after the previous pilot write has succeeded and its resulting ledger state is visible on current `main`.

The next user question may be asked while the previous operation settles, but the next ledger-mutating request must wait for the resulting `main` ledger digest.

Two `complete_reassessment_item` requests constructed from the same ledger digest cannot both succeed. The first accepted write changes the digest; the second must fail closed as stale.

Typical operational cost for a full 5-work session is approximately:

- 1 reservation PR;
- 5 item completion/defer PRs;
- 1 close PR;
- plus 1 existing `set_inferred_preferences` PR on scheduled milestone sessions.

For a cohort around 55 works this is roughly 77 pilot-operation PRs plus a small number of milestone reanalysis PRs. This is an explicit correctness-first pilot cost.

Ledger-only reservation/close changes do not need a Pages publish for product correctness. If the current publish workflow supports a safe trusted path-based skip, implementation should avoid unnecessary Pages publications for ledger-only merges; this optimization is not a prerequisite for pilot correctness.

## 17. Reservation-before-write invariant

This is mandatory and tested:

> No canonical reassessment feedback write may occur for a work unless its `in_progress` reservation for the active `session_id` is already visible on current `main`.

The agent must not start a write under the assumption that a reservation PR “will merge later”. Reservation is a durable precondition.

This ensures interruption recovery does not depend on reconstructing missing pre-review state after canonical feedback has changed.

## 18. Why atomic feedback + ledger completion is required

Using `edit_viewing_feedback` and then a separate ledger update creates an avoidable split-brain window: feedback can merge while pilot state still says `in_progress` without a durable completion marker.

The pilot therefore uses `complete_reassessment_item` to combine:

- optional feedback mutation;
- ledger completion/defer transition;
- operation audit record.

This is one business operation: “the user completed or deferred reassessment of this reserved work”.

The implementation reuses existing feedback mutation primitives rather than duplicating their rules, so history behavior and target/profile rebuilding remain consistent with Stage A.

## 19. Fresh explicit evidence normalization

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

## 20. History behavior

When completion changes a feedback component, existing feedback mutation semantics preserve the old value in `history.previous` and the new value in `history.current`.

No extra `legacy_review` field is introduced.

For `confirmed_unchanged`, no artificial no-op feedback history entry is created merely to prove confirmation; the ledger outcome provides the confirmation provenance.

## 21. Session lifecycle

Default batch size: **5 works**.

A normal session is:

1. build the next deterministic batch from lifecycle + frozen stratified order;
2. reserve it durably on `main` with `reserve_reassessment_session`;
3. present each item unanchored;
4. collect fresh response;
5. optionally expose historical record after the initial response or on user request;
6. atomically complete or defer the item;
7. wait for each pilot write to become authoritative on `main` before issuing the next pilot write;
8. when the reserved batch is fully resolved, determine whether scheduled taste reanalysis is due;
9. if due, run existing `set_inferred_preferences` and wait for its successful result on `main`;
10. close the session with `close_reassessment_session`, recording the Stage A audit snapshot and, when applicable, scheduled-reanalysis state.

An interrupted session resumes `in_progress` items first. Items already completed are never asked again. An interrupted session is not closed until its reserved items are resolved.

## 22. Session audit and progress measurement

Every closed session records the canonical Stage A audit through `close_reassessment_session`.

The ledger stores a compact immutable session snapshot rather than duplicating the whole audit JSON.

Snapshot fields include at least:

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

`media/pilots/` is explicitly **outside** the Stage A intelligence canonical-input inventory. Therefore ledger-only changes must not change `canonical_input_digest`.

This exclusion is a tested contract, not an accidental implementation detail.

Semantic coverage is not expected to improve in this pilot and is not a success criterion.

## 23. Taste-hypothesis reanalysis cadence and persistent state

Inferred hypotheses are explanation-only for numeric affinity aggregation after Stage A, so recalculating them after every 5-work session would create unnecessary LLM churn.

Scheduled reanalysis is due only:

- every **15 newly reviewed works** since the previous scheduled reanalysis;
- at the end of the main `pending` pass.

The ledger persists:

```json
{
  "scheduled_reanalysis": {
    "last_completed": {
      "reviewed_count": 15,
      "operation_id": "...",
      "completed_at": "..."
    }
  }
}
```

Due calculation is therefore deterministic across conversations:

```text
reviewed_total - last_completed.reviewed_count >= 15
```

If no scheduled reanalysis has completed yet, the previous count is zero.

Scheduled reanalysis rebuilds hypotheses from current raw/explicit evidence and replaces the target set through existing `set_inferred_preferences`.

Previous inferred hypotheses are never treated as independent confirming evidence. A weaker or empty replacement set is valid.

An explicit user-requested reanalysis may occur at any time, but **does not reset or advance the scheduled 15-review cadence**. Only a scheduled milestone reanalysis referenced and verified by `close_reassessment_session` advances `scheduled_reanalysis.last_completed`.

## 24. Expected profile drift

The pilot intentionally changes the evidence base. Therefore generated profile changes are expected, not automatically regressions.

Expected effects include:

- ratings moving from `source: inferred` or `explicit_approx` to `source: explicit` even when the numeric score stays the same;
- substantial growth in structured direct feedback signals;
- changes in generated profiles/affinities caused by new direct evidence;
- later milestone changes in inferred hypotheses.

Longitudinal pilot comparisons must be interpreted relative to the frozen Stage A baseline/base revision, not relative to whichever generated profile happened to exist immediately before a session.

## 25. Ground-truth relationship to Stage B

A reviewed item becomes high-quality confirmed explicit evidence, but not automatically a Stage B decision-benchmark member.

Stage B will later define benchmark selection/stratification/leakage rules.

Useful reassessment provenance available to Stage B includes:

- immutable frozen cohort identity/order;
- pre-review digest;
- completion outcome (`changed` vs `confirmed_unchanged`);
- `historical_exposure` timing/finalization flags;
- session membership/order;
- operation provenance;
- post-session audit progression.

This lets Stage B select fully unexposed final evidence when needed, or separately analyze independently elicited initial answers that were later refined after historical recall.

## 26. Failure and resume semantics

The workflow is fail-closed.

- reservation must be merged before reassessment writes;
- every pilot write must match current `expected_ledger_digest`;
- completion without matching reservation fails;
- completion against a changed pre-review feedback digest fails as a concurrency conflict;
- stale parallel pilot writes fail;
- a failed completion leaves the item `in_progress`;
- a failed defer leaves the item `in_progress`;
- a session with unresolved reserved items cannot be closed;
- a successfully reviewed item cannot be completed a second time automatically;
- closed session snapshots cannot be rewritten;
- frozen cohort definition cannot change after initialization;
- unknown/ambiguous work identity blocks mutation;
- canonical work evidence is never reconstructed from ledger copies because the ledger does not duplicate evidence content.

Because completion is atomic across optional feedback mutation + ledger transition, interruption cannot create “feedback changed but completion marker missing” as an expected success path.

## 27. Path-policy and trust boundary

The implementation is a developer change and receives manual review.

Existing operations must remain unable to mutate:

`media/pilots/legacy-reassessment-primary.json`

The new pilot operations receive only narrow allowlists.

Conceptually:

`reserve_reassessment_session`:

- `media/pilots/legacy-reassessment-primary.json`;
- `.media/operations/*.json`.

`complete_reassessment_item`:

- `media/pilots/legacy-reassessment-primary.json`;
- at most one `media/data/works/*.yaml` path, and it must resolve to the reserved work id;
- existing derived `media/generated/index.jsonl` / profile paths required by reused feedback primitives;
- `.media/operations/*.json`.

`close_reassessment_session`:

- `media/pilots/legacy-reassessment-primary.json`;
- `.media/operations/*.json`.

Runtime planning and CI changed-file validation both enforce that `complete_reassessment_item` changes **no more than one canonical work**, and that any changed work is exactly the reserved item. A second matching `media/data/works/*.yaml` path is rejected even though the declarative wildcard can syntactically match it.

The path-policy grammar is not generalized with a new max-files DSL solely for this pilot; operation-specific constraints and tests are sufficient until another use case justifies a generic mechanism.

Privileged workflow trust remains based on policy from trusted `main`, not PR-head executable code. No semantic/vocabulary path is authorized by reassessment operations.

## 28. Archive lifecycle

At pilot completion:

- set `pilot_status: completed`;
- store final audit snapshot;
- preserve the full ledger in place while Stage B is being designed/constructed.

Only after Stage B no longer requires an active ledger path should a separate developer change move it under an archive location such as:

`media/pilots/archive/legacy-reassessment-primary-v1.json`

Archive movement must not alter historical contents beyond explicit archival metadata required by the chosen format.

## 29. Documentation deliverables

Documentation is part of completion.

Implementation must update as applicable:

- `media/AGENTS.md` — reassessment route, unanchored-first UX, serialized reservation/completion/close rules, deferred behavior;
- `docs/architecture/intelligence.md` — confirmed explicit evidence, semantic separation, expected profile drift, milestone reanalysis;
- `docs/architecture/write-pipeline.md` — pilot typed operations, ledger serialization, base→head transition validation and atomic completion boundary;
- `docs/reference/media-commands.md` — schemas/behavior for pilot operations;
- a pilot runbook under `docs/` covering start/resume/session close/deferred pass/audit/reanalysis;
- `docs/status/current.md` — current capability and limitations;
- this design spec;
- implementation plan after written-spec approval.

The runbook emphasizes that old ratings/reviews and semantic descriptors are hidden before the first response unless the user explicitly asks for historical data.

## 30. Test requirements

Implementation is incomplete without tests for the following.

### 30.1 Cohort and ordering

- `unwatched` never enters the cohort even when summary text is non-empty;
- `watched`, `partial`, `dropped`, `forgotten` are handled according to contract;
- frozen strata are deterministic;
- `sha256(pilot_id + "\0" + work_id)` order is deterministic and persisted;
- stratified round-robin order is deterministic;
- deferred items do not interrupt the main pending pass;
- reviewed items never re-enter automatically;
- frozen cohort work ids/strata/order/reference data cannot change after initialization.

### 30.2 Unanchored UX payload

- pre-response card does not expose old rating/reaction/feedback or evaluative semantic traits;
- neutral memory-jog payload uses premise/identity facts;
- post-initial-response history exposure is allowed;
- user-requested pre-response exposure records `before_initial_response` + `before_finalization=true`;
- exposure after independent initial answer but before finalization records `after_initial_response` + `true`;
- exposure after finalization records `after_initial_response` + `false`;
- default no-history path records `none` + `false`.

### 30.3 Reservation, serialization and atomic completion

- no completion is accepted before reservation is visible in repository state;
- wrong `session_id` fails closed;
- changed pre-review feedback digest fails closed;
- stale `expected_ledger_digest` fails closed for reserve, complete and close;
- two completes based on the same ledger digest cannot both succeed;
- completion updates work + ledger atomically in deterministic transaction;
- identical numeric score with old `inferred`/`explicit_approx` provenance mutates provenance to `explicit` and yields `changed`;
- `confirmed_unchanged` advances ledger without artificial feedback history;
- completing an already reviewed item cannot reopen/reassess it;
- defer changes ledger only;
- session close fails while reserved items remain unresolved;
- session close appends exactly one immutable snapshot.

### 30.4 Snapshot and transition validation

- invalid terminal reviewed item fails snapshot validation;
- closed session with unresolved reservation fails snapshot validation;
- empty/duplicate/invalid frozen cohort fails snapshot validation;
- base→head validator rejects cohort/base/baseline mutation;
- base→head validator rejects `reviewed` rollback;
- base→head validator rejects mutation/deletion of closed session snapshots;
- base→head validator rejects scheduled-reanalysis state moving backwards;
- valid monotonic pilot transitions pass.

### 30.5 Path policy / security

- all pre-existing Stage A operations reject `media/pilots/legacy-reassessment-primary.json`;
- `reserve_reassessment_session` cannot mutate work/generated/preferences/vocabulary/schema paths;
- `complete_reassessment_item` cannot mutate semantic/vocabulary/schema/workflow paths;
- completion changing more than one `media/data/works/*.yaml` path fails;
- completion changing a work different from the reserved work fails;
- `close_reassessment_session` cannot mutate work/generated/preferences/vocabulary/schema paths;
- operation path-policy matcher corpus remains green;
- privileged auto-merge remains fail-closed for unknown operations/paths.

### 30.6 Audit/progress and reanalysis state

- ledger-only mutation leaves Stage A `canonical_input_digest` unchanged;
- `media/pilots/` is excluded from audit input inventory;
- session close computes audit output deterministically;
- progress snapshot reflects explicit/inferred rating changes and structured-feedback coverage;
- baseline references are preserved;
- semantic coverage is not required to move;
- scheduled reanalysis due calculation survives a new process/conversation;
- manual user-requested reanalysis does not reset scheduled cadence;
- close accepts a scheduled milestone only when referenced `set_inferred_preferences` operation is already valid on current `main`.

### 30.7 Repository validation

Full gate:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Additionally, docs/contract tests accept the new pilot directory, ledger schema and command references.

## 31. Observability and stop conditions

Primary progress measures are:

- proportion of frozen cohort in `reviewed`;
- `changed` vs `confirmed_unchanged` counts;
- historical exposure distribution;
- conversion of `primary` ratings from inferred/approximate to explicit where applicable;
- structured-feedback coverage growth;
- deferred backlog size.

The main pilot pass is complete when no `pending` or resumable `in_progress` items remain.

The deferred pass is complete when the user either reviews or explicitly leaves remaining deferred items unresolved for this pilot epoch.

Completion does not require semantic coverage growth.

## 32. Open issues intentionally deferred

The following are not decided by this pilot implementation:

1. semantic vocabulary revision;
2. semantic fingerprint provenance/versioning (`vocab_version`, `enriched_at`, `enriched_by`);
3. targeted semantic enrichment policy;
4. collection reassessment / benchmark treatment;
5. Stage B benchmark sampling and leakage controls;
6. deterministic assessment model/formula selection;
7. partner/couple reassessment.

## 33. Recommended implementation shape

The recommended implementation is deliberately narrow:

- deterministic cohort/queue/read-model helper;
- versioned pilot ledger at the exact path above;
- snapshot validator for one-state ledger invariants;
- base→head transition validator for monotonicity/immutability;
- `reserve_reassessment_session` typed operation;
- `complete_reassessment_item` typed operation reusing existing feedback mutation primitives;
- `close_reassessment_session` typed operation computing/persisting immutable audit progress and scheduled-reanalysis state;
- serialized pilot writes by `expected_ledger_digest`;
- compact session audit snapshots;
- milestone-triggered existing taste reanalysis;
- documentation and tests as first-class deliverables.

No semantic enrichment code is added to this cycle.

## 34. Final architecture summary

The pilot flow is:

**immutable viewed cohort + frozen hash order → stratified round-robin → durable reservation on `main` → neutral unanchored memory jog + fresh response → optional historical recall with explicit exposure provenance → serialized atomic explicit-feedback/ledger completion (or defer) → scheduled reanalysis when due → durable session close + audit snapshot → deferred pass → completed immutable ledger for Stage B.**

The central safety properties are:

- no old rating anchoring by default;
- no evaluative semantic anchoring in the memory jog;
- no semantic/user-reaction conflation;
- no canonical reassessment write before durable reservation;
- no concurrent pilot writes against stale ledger state;
- no split completion between feedback and ledger;
- no automatic reassessment loop;
- no silent mutation of frozen cohort or closed sessions;
- no silent overwrite after concurrent feedback changes;
- measurable progress against the frozen Stage A baseline.