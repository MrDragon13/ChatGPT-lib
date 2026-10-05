# Media Legacy Reassessment & Intelligence Backfill — Design

**Date:** 2026-10-05  
**Status:** proposed for implementation planning after user review  
**Base revision:** `35afaca898eae6937066f230906b41af0e1f6690`

## 1. Context

Media Intelligence Stage A fixed directional correctness and observability, but a material part of the personal media history predates the current structured review pipeline. Many older `primary` records were created when the product behaved closer to a review page: they may have free-form `feedback.summary`, missing structured feedback signals, inferred/approximate ratings or reactions, and no semantic fingerprint.

Those historical records are useful evidence, but they did not pass through the same intake/enrichment/reanalysis flow as modern reviews. Blindly converting old text into new explicit signals would manufacture ground truth. Conversely, simply editing the text would leave those works structurally second-class and would miss the opportunity to improve semantic coverage and taste evidence.

This design adds a finite, resumable **Legacy Reassessment / Intelligence Backfill pilot** for `primary` only. The user revisits each work once, with a short memory aid. Fresh user input becomes current explicit evidence; historical values remain in standard feedback history. Work semantics are handled separately from user reaction. Taste hypotheses are reanalyzed in batches rather than after every film.

## 2. Goals

The pilot must:

1. let the user systematically revisit the full initial `primary` review/viewing cohort without losing place;
2. present enough spoiler-free context to remember each film before asking for a reassessment;
3. preserve old v1-era feedback through existing `history` semantics rather than duplicating it into a new legacy field;
4. turn only newly confirmed user statements into explicit rating/reaction/feedback signals;
5. catch up missing work-level semantic fingerprints without confusing subjective reaction with work traits;
6. reanalyze `primary` taste hypotheses once per short session from current raw/explicit evidence;
7. prevent the same work from being automatically reassessed repeatedly;
8. remain compatible with the existing typed media write pipeline and guarded merge boundaries;
9. produce documentation and operational guidance sufficient to resume the pilot in a later conversation;
10. create high-quality confirmed evidence that Stage B can later sample for evaluation/ground-truth design.

## 3. Non-goals

This pilot does **not**:

- redesign recommendation ranking or affinity weights;
- choose Stage B benchmark metrics or model formulas;
- introduce deterministic assessment scoring/probabilities;
- reassess `partner` or `couple` data;
- mass-expand the controlled vocabulary;
- infer explicit preferences from old text without current confirmation;
- treat explicit similarity as equivalent to liking;
- perform bulk provider metadata maintenance;
- add a composite `reassess_legacy_work` mutation that bypasses existing typed operations;
- automatically reopen a completed reassessment when later media data changes.

## 4. Existing contracts preserved

The design keeps the current four-layer separation:

1. factual work metadata;
2. work semantic fingerprint;
3. user evidence such as rating/reaction/feedback;
4. inferred taste hypotheses.

The existing write pipeline remains authoritative for canonical media changes. Reassessment orchestration may decide which existing operation to invoke, but canonical media mutations still use typed operations, deterministic transaction, validation/rebuild, exact-head check and guarded merge.

Relevant existing operations remain:

- `edit_viewing_feedback` for current `primary` rating/reaction/feedback correction;
- `set_semantic_fingerprint` for work-level controlled-vocabulary traits;
- `set_inferred_preferences` for a target-wide replacement of inferred taste hypotheses.

No free-form canonical YAML patch is introduced.

## 5. High-level architecture

The pilot has three distinct pieces.

### 5.1 Deterministic reassessment queue helper

A new read-oriented helper/CLI builds reassessment cards from canonical state plus pilot ledger state. It is responsible for cohort membership, ordering, memory-jog data, current review state and semantic-coverage flags. It does not mutate canonical works and does not create taste hypotheses.

### 5.2 Separate pilot ledger

Pilot lifecycle state is stored outside canonical works at the normative path:

`media/pilots/legacy-reassessment-primary.json`

Pilot status does not become a field in every canonical work. The ledger stores operational state only; it does not duplicate rating, reaction, feedback summary/signals or semantic fingerprint content.

Ledger maintenance is pilot/developer state, not a canonical media mutation. The initial implementation uses deterministic ledger tooling and a separate pilot-state commit/PR boundary; ledger writes are not normal media auto-merge operations. A future dedicated typed pilot-state operation is out of scope.

### 5.3 Agent-orchestrated session

The agent runs the user interaction:

- selects the next ledger item;
- presents a compact memory card;
- interprets only the user’s fresh response as new explicit evidence;
- uses existing typed media operations for media mutations;
- performs semantic catch-up only when warranted;
- advances pilot lifecycle state;
- runs one `primary` taste reanalysis at session end.

## 6. Finite cohort and queue membership

The pilot is finite. At initialization the helper freezes `cohort_revision` and ordered `cohort_work_ids`.

The initial cohort is intentionally broad because historical provenance is not precise enough to identify every v1 record safely. It includes canonical works present at the cohort revision that have meaningful `primary` viewing/review evidence, including watched works even when structured feedback is sparse. Explicitly `unwatched` records with no meaningful review evidence are excluded.

A frozen cohort is preferred over a fuzzy legacy detector because the user intends to go through the set comprehensively. Diagnostic flags may explain why a work looks sparse, but they never determine whether a reviewed work can re-enter the same pilot epoch.

A later **explicit** cohort refresh may append newly discovered historical candidates. It may not remove completion history or automatically re-add a reviewed work.

## 7. Ledger contract

The ledger is versioned and target-specific. Initial schema:

```json
{
  "schema_version": 1,
  "pilot_id": "primary-legacy-v1",
  "target": "primary",
  "cohort_revision": "35afaca898eae6937066f230906b41af0e1f6690",
  "cohort_work_ids": [],
  "items": {
    "work-id": {
      "status": "pending",
      "last_action_at": null,
      "session_id": null,
      "feedback_before_digest": null,
      "semantic_before_digest": null,
      "feedback_completed": false,
      "semantic_required": null,
      "semantic_completed": false,
      "reviewed_at": null,
      "reviewed_revision": null
    }
  }
}
```

Timestamps are UTC ISO-8601. Digests are deterministic hashes of the relevant canonical component before the active reassessment step; they are resume aids, not media truth.

Allowed lifecycle statuses:

- `pending` — in the frozen cohort, not yet reassessed;
- `in_progress` — selected into an active session and not fully completed;
- `reviewed` — fresh reassessment successfully completed for this pilot epoch;
- `deferred` — user cannot currently remember/reassess it or explicitly skips it for later.

State-specific requirements:

- `pending`: no active `session_id`; completion flags false/null;
- `in_progress`: `session_id`, pre-state digests and completion flags are populated as stages run;
- `reviewed`: `feedback_completed=true`, semantic requirement resolved, `reviewed_at` and `reviewed_revision` populated;
- `deferred`: no media completion requirement; later deferred-pass selection may move it to `in_progress`.

No additional lifecycle meaning may be inferred from missing fields.

## 8. Anti-loop / idempotence contract

This is a hard invariant.

### 8.1 One automatic reassessment per work per pilot epoch

For `pilot_id = primary-legacy-v1`, once an item reaches `reviewed`, the queue helper must never automatically return it to `pending` or show it for reassessment again.

This remains true even if:

- the work still looks legacy-like to a diagnostic heuristic;
- its semantic fingerprint remains smaller than another work’s;
- later normal feedback edits change the work;
- a future detector implementation becomes more aggressive.

A repeat reassessment requires explicit user action or a new pilot epoch/version.

### 8.2 Ledger lifecycle outranks diagnostics

Diagnostics answer “why might this record deserve catch-up?” Ledger state answers “has this pilot already handled it?”. Ledger lifecycle always wins for automatic queue eligibility.

### 8.3 In-session duplicate guard

The session runner maintains `seen_work_ids`. A work cannot be presented twice within one active session regardless of ledger refreshes or underlying media writes.

### 8.4 Resume does not repeat completed human work

If an item is `in_progress` and canonical state proves that fresh feedback was already successfully written, resume continues from the first unfinished technical stage rather than asking the user to rate the film again. `feedback_before_digest` plus the current canonical component and completion flag provide this reconciliation evidence.

### 8.5 Later changes do not reopen the item

A helper may compute informational `changed_after_review` by comparing current state with `reviewed_revision`/digests, but that condition is never an automatic reopen trigger.

## 9. Queue ordering

The user intends to complete the whole cohort, so ordering is a convenience rather than a coverage mechanism.

Deterministic ordering:

1. unfinished `in_progress` items;
2. `pending` items;
3. stop the main pass when no pending work remains;
4. only then begin a separate `deferred` pass.

Within `pending`, use stable impact-first ordering: structured-feedback sparsity first, then missing semantic fingerprint, then stable work ID. This is pilot workflow priority only, not a recommendation-quality score.

## 10. Reassessment card / memory jog

Every presented work includes a short spoiler-free memory aid before the question.

Required card content:

- title and year;
- 1–2 sentence spoiler-free memory jog based primarily on saved synopsis;
- current `primary` rating, if any;
- current reaction, if any;
- current/legacy feedback summary, if any;
- whether structured feedback signals exist;
- whether semantic fingerprint is present.

Director or one principal actor may be added when useful for recognition, but the card remains concise and must not become a plot recap.

Example:

> **Бэтмен (2022)** — мрачный детективный Бэтмен расследует серию убийств элиты Готэма.  
> Старая запись: **6/10**, «Не особо понравился». Structured signals: нет.  
> Semantic fingerprint: есть.  
> Как ты сейчас его оцениваешь?

The memory jog is read-only context, not evidence about user taste.

## 11. One-item reassessment flow

### 11.1 Select

The helper returns the next item according to ledger state and deterministic ordering. Before the question, the active item is recorded as `in_progress` with `session_id` and pre-state component digests.

### 11.2 Present

The agent shows the card and asks for a fresh opinion in natural language. It does not turn the interaction into a long questionnaire.

Normal prompt:

> «Как ты сейчас оцениваешь этот фильм? Можешь написать оценку и что понравилось/не понравилось — я разложу это по текущей структуре.»

At most one short clarification may be asked when a materially important distinction remains ambiguous.

### 11.3 Defer

If the user says “не помню”, “пропустить” or equivalent:

- do not change canonical media data;
- do not lower existing confidence merely because memory is weak now;
- set the pilot item to `deferred`;
- continue with the next pending item.

### 11.4 Normalize fresh explicit evidence

Only the current user response may create new explicit evidence.

When clearly supported, the agent may derive:

- rating using the existing 1–10 / 0.5-step contract;
- reaction;
- replacement feedback summary;
- structured feedback signals using controlled vocabulary terms.

The old v1 summary is context only. If the user explicitly confirms it, it may be represented again as current explicit evidence. Otherwise it must not be silently promoted.

### 11.5 Write feedback

Use existing `edit_viewing_feedback` for `primary` and change only components justified by the fresh response.

Existing mutation behavior records changed components in `history.previous` and `history.current`. Therefore current feedback can become the fresh opinion while historical v1 content remains auditable without a new `legacy_review` field.

After exact-main success, set `feedback_completed=true` in pilot state.

### 11.6 Semantic catch-up

Evaluate work semantics separately after feedback.

- Missing semantic fingerprint means `semantic_required=true`.
- Existing fingerprint is not rebuilt solely because it has fewer traits than another work; absent a concrete gap, `semantic_required=false`.
- No arbitrary minimum trait count is introduced.
- New traits must use the existing controlled vocabulary.
- Vocabulary expansion is a separate architecture/developer change.
- User reaction may guide attention but cannot itself prove a work trait.

Example:

- “мне было затянуто” may support user feedback `reaction.pacing_dragging`;
- it does **not** automatically prove work trait `pacing.slow`.

If required, write semantic traits with existing `set_semantic_fingerprint`. After exact-main success set `semantic_completed=true`. If `semantic_required=false`, semantic completion is considered satisfied without a mutation.

### 11.7 Complete item

An item becomes `reviewed` only when:

- `feedback_completed=true`; and
- `semantic_required` is resolved; and
- either `semantic_required=false` or `semantic_completed=true`; and
- the corresponding canonical state is present on current `main`.

Then populate `reviewed_at` and exact `reviewed_revision`.

A technical failure leaves the item `in_progress` and resume starts from the first incomplete stage.

## 12. Structured feedback rules

The pilot is intentionally conservative.

- `source: explicit` is used only for meaning actually stated or clearly confirmed in the current reassessment.
- `strength: 1..3` reflects expressed intensity of reaction, not model confidence.
- If sentiment/term mapping is materially ambiguous, omit the signal rather than fabricate ground truth.
- Work traits and reaction-kind terms remain distinct.
- Explicit similarity is not inferred merely because works share traits or ratings.
- Ephemeral mood/current-context comments do not become stable preferences.

## 13. Session lifecycle

Default reassessment session size is **5 works**.

At session start, the pilot ledger reserves the selected batch as `in_progress` under one `session_id` before the first human question. This makes an interrupted session resumable without relying on conversational memory.

The user may continue beyond five, but five is the default operational chunk.

At the end of any session with at least one newly reviewed item, run one `primary` taste reanalysis. The pilot-state update reconciles final `reviewed`/`deferred` states after canonical writes are visible on `main`.

User-facing session summary remains brief:

- reviewed/deferred counts;
- whether semantic catch-up occurred;
- what materially changed in understanding of `primary` taste after reanalysis.

Infrastructure details stay hidden in normal use unless requested.

## 14. Batched taste reanalysis

Taste reanalysis happens once per session, not after each work.

The agent rebuilds candidate hypotheses from current raw/explicit evidence. Previous inferred hypotheses are not independent evidence and must not self-reinforce.

If evidence supports a changed hypothesis set, persist the full replacement via existing `set_inferred_preferences` for `primary`.

A weaker or empty hypothesis set is valid if fresh evidence no longer supports older conclusions. Old hypotheses are not retained merely for continuity.

`partner` and `couple` explicit state are not rewritten by this pilot. Existing derived profile rebuild behavior remains derived behavior, not new explicit group evidence.

## 15. Ground-truth relationship to Stage B

Fresh reassessment produces high-value **confirmed explicit evidence**, but the pilot does not automatically declare every reviewed work part of the Stage B decision benchmark.

Stage B later defines benchmark selection, stratification and leakage rules. Reassessed works become eligible source material.

Historical v1 text remains historical evidence; current reassessment becomes current explicit evidence. This distinction stays visible in history/provenance.

## 16. Failure and resume semantics

The workflow is fail-closed around canonical writes.

- Failed feedback mutation does not advance the item to `reviewed`.
- Successful feedback followed by failed semantic catch-up leaves the item `in_progress`; resume starts at semantic catch-up.
- Failed pilot-ledger persistence never rolls back canonical media. The next session reconciles exact canonical state against stored pre-state digests/completion state before repeating a human step.
- Unknown/ambiguous work identity blocks mutation until resolved.
- Provider metadata failure cannot corrupt reassessment of an already canonical work.

Canonical media is source of truth; the ledger is operational state.

## 17. Security and write-boundary requirements

This project is an architecture/tooling change and follows the manual developer route during implementation.

Runtime reassessment preserves current safety boundaries:

- no arbitrary model-authored shell or YAML patch for canonical media;
- normal media writes use typed request schemas and deterministic services;
- semantic writes validate controlled vocabulary;
- pilot-state tooling writes only `media/pilots/legacy-reassessment-primary.json` and must validate its schema/state transitions;
- pilot ledger changes are not normal media auto-merge operations in this design;
- any path-policy or privileged-workflow change receives the same trusted-main/fail-closed review standard as Stage A;
- no model/provider secrets enter browser/static data paths.

## 18. Documentation deliverables

Documentation is part of completion, not follow-up cleanup.

Implementation updates:

- `media/AGENTS.md` — agent-level legacy reassessment route and UX contract;
- `docs/architecture/intelligence.md` — reassessment evidence/semantic separation and batched reanalysis;
- `docs/architecture/write-pipeline.md` — pilot ledger/tooling boundary because it is intentionally separate from canonical typed writes;
- `docs/reference/` — reassessment queue/ledger helper and CLI contract;
- a dedicated pilot runbook — initialize/start/resume session, card format, statuses, deferred pass, taste reanalysis and completion/archive procedure;
- `docs/status/current.md` — implemented capability and limitations;
- executable documentation/contract tests wherever the repository already enforces synchronization.

The runbook must let a new conversation resume the process without hidden conversational memory.

## 19. Testing requirements

### Queue/cohort

- deterministic frozen cohort generation;
- inclusion of intended `primary` historical/watched evidence;
- exclusion of clearly `unwatched` no-evidence records;
- no `partner`/`couple` reassessment targets;
- stable ordering and tie-breaking;
- explicit refresh can append candidates but cannot erase completion.

### Ledger lifecycle

- valid `pending -> in_progress -> reviewed`;
- valid `pending -> deferred`;
- valid `deferred -> in_progress` only during deferred pass/explicit selection;
- reviewed item cannot automatically reopen in same `pilot_id`;
- deferred items do not reappear during main pending pass;
- `in_progress` items resume first;
- same-session `seen_work_ids` prevents duplicate presentation;
- diagnostics cannot override `reviewed`;
- invalid state transitions fail closed.

### Reassessment card

- deterministic card payload;
- spoiler-free synopsis-based memory-jog source behavior;
- current rating/reaction/summary and signal/fingerprint presence are represented correctly;
- card generation is read-only.

### Feedback/history

- replacement preserves prior value in standard history;
- only justified components change;
- user silence about a component does not clear it;
- old summary is not automatically converted to new explicit signals.

### Semantic separation

- reaction terms are not written as work traits;
- missing fingerprint produces `semantic_required=true`;
- existing fingerprint is not declared insufficient by arbitrary trait-count threshold;
- unknown vocabulary terms fail validation rather than being invented.

### Resume/idempotence

- interrupted after feedback/before semantics resumes at semantics;
- completed human feedback is not asked again because a technical stage failed;
- changed-after-review is informational and does not reopen automatically;
- ledger/canonical disagreement reconciles toward canonical truth without losing anti-loop state.

### Reanalysis

- one session produces at most one `primary` reanalysis step;
- old inferred hypotheses are not independent evidence;
- partner/couple explicit state is not mutated.

### Full gates

Completed developer change runs at least:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Web checks are required only if implementation changes web/broker-visible behavior.

## 20. Rollout

1. Implement queue/cohort/ledger foundations and documentation without changing existing recommendation behavior.
2. Initialize `primary-legacy-v1` from the exact current revision and inspect the frozen cohort.
3. Run a live pilot session of about five works.
4. Verify history preservation, resume and anti-loop behavior from real output.
5. Continue repeated sessions through the frozen pending cohort.
6. Run the deferred pass only after pending is exhausted.
7. Archive/freeze the completed ledger and use confirmed evidence as input to Stage B evaluation/ground-truth design.

## 21. Success criteria

The design is successful when:

- a new conversation can resume at the correct next work;
- each cohort work is automatically presented at most once per pilot epoch unless explicitly reopened;
- every reviewed item has fresh current explicit feedback and preserved historical context;
- semantic catch-up improves missing work semantics without converting subjective reaction into factual traits;
- `primary` taste reanalysis occurs in session-sized batches rather than per-film churn;
- partner/couple data remains untouched;
- canonical mutations continue through existing typed operations and verification gates;
- documentation explains architecture and day-to-day pilot operation;
- confirmed reassessment evidence can feed Stage B without treating old inferred labels as ground truth.
