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

The existing write pipeline remains authoritative for canonical media changes. Reassessment orchestration may decide which existing operation to invoke, but canonical media mutations still use the existing typed operations, deterministic transaction, validation/rebuild, exact-head check and guarded merge path.

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

Pilot lifecycle state is stored outside canonical works in a dedicated pilot ledger, expected under a path such as:

`media/pilots/legacy-reassessment-primary.json`

The exact path may be finalized during implementation planning, but the boundary is normative: pilot status does not become a field in every canonical work.

The ledger stores only operational state. It must not duplicate rating, reaction, feedback summary/signals or semantic fingerprint content.

The initial implementation treats ledger maintenance as pilot/developer state, not as a canonical media mutation. It is updated by deterministic tooling and reviewed/committed separately from normal media writes. A future dedicated typed pilot-state operation may be designed if operational friction justifies it; that is explicitly out of scope for this pilot implementation.

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

The pilot is finite. At pilot initialization, the helper records a frozen `cohort_revision` and an ordered `cohort_work_ids` set.

The initial cohort is intentionally broad because historical provenance is not precise enough to identify every v1 record safely. It includes canonical works that existed at the cohort revision and have meaningful `primary` viewing/review evidence, including watched works even when structured feedback is sparse. Explicitly `unwatched` records with no meaningful review evidence are excluded.

This broad frozen cohort is preferred over a fuzzy “legacy detector” as the primary source of membership because the user intends to go through the set comprehensively. Diagnostic flags still explain why a work looks legacy/sparse, but they do not control whether a reviewed work can re-enter the same pilot epoch.

A later explicit cohort refresh may append newly discovered historical candidates, but it must never remove completion history or automatically re-add a reviewed work.

## 7. Ledger contract

The ledger is versioned and target-specific. Conceptually it contains:

```json
{
  "schema_version": 1,
  "pilot_id": "primary-legacy-v1",
  "target": "primary",
  "cohort_revision": "<git sha>",
  "cohort_work_ids": ["..."],
  "items": {
    "work-id": {
      "status": "pending",
      "last_action_at": null
    }
  }
}
```

Allowed lifecycle statuses:

- `pending` — in the frozen cohort, not yet reassessed;
- `in_progress` — selected into an active session and not fully completed;
- `reviewed` — fresh reassessment successfully completed for this pilot epoch;
- `deferred` — user cannot currently remember/reassess it or explicitly skips it for later.

Implementation may add narrow technical fields needed for deterministic resume, such as pre-session component digests, completion flags or last successful stage. Such fields remain operational metadata only.

## 8. Anti-loop / idempotence contract

This is a hard invariant.

### 8.1 One automatic reassessment per work per pilot epoch

For `pilot_id = primary-legacy-v1`, once an item reaches `reviewed`, the queue helper must never automatically return it to `pending` or show it for reassessment again.

This remains true even if:

- the work still looks “legacy-like” to a diagnostic heuristic;
- its semantic fingerprint remains smaller than another work’s;
- later normal feedback edits change the work;
- a future detector implementation becomes more aggressive.

A repeat reassessment requires explicit user action or a new pilot epoch/version.

### 8.2 Ledger lifecycle outranks diagnostics

Diagnostics answer “why might this record deserve catch-up?” Ledger state answers “has this pilot already handled it?”. Ledger lifecycle always wins for automatic queue eligibility.

### 8.3 In-session duplicate guard

The session runner maintains `seen_work_ids`. A work cannot be presented twice within one active session regardless of ledger refreshes or underlying media writes.

### 8.4 Resume does not force the user to repeat a completed human step

If an item is `in_progress` and fresh feedback is already successfully present on `main`, resume continues from the first unfinished technical stage rather than asking the user to remember and rate the film again.

### 8.5 Later changes do not reopen the item

The ledger may expose an informational `changed_after_review` condition by comparing stored revision/digest metadata, but that condition is never an automatic reopen trigger.

## 9. Queue ordering

The user intends to complete the whole cohort, so ordering is a convenience rather than a coverage mechanism.

Recommended deterministic ordering:

1. unfinished `in_progress` items;
2. `pending` items;
3. stop the main pass when no pending work remains;
4. only then start a separate `deferred` pass.

Within `pending`, a stable impact-first ordering may prioritize sparse structured feedback or missing semantics, with stable work ID as final tie-breaker. Exact priority weights are not a product-quality model and must not become a hidden recommendation score.

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

Director or one principal actor may be added when useful for recognition, but the card must remain concise and must not become a plot recap.

Example shape:

> **Бэтмен (2022)** — мрачный детективный Бэтмен расследует серию убийств элиты Готэма.  
> Старая запись: **6/10**, «Не особо понравился». Structured signals: нет.  
> Semantic fingerprint: есть.  
> Как ты сейчас его оцениваешь?

The memory jog is read-only context, not evidence about the user’s taste.

## 11. One-item reassessment flow

### 11.1 Select

The helper returns the next eligible item according to ledger state and deterministic ordering. The session runner marks/selects it as `in_progress` before relying on it as active work.

### 11.2 Present

The agent shows the reassessment card and asks for a fresh opinion in natural language. It does not turn the interaction into a long questionnaire.

A normal prompt is sufficient:

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

The agent may derive, when clearly supported:

- rating, using the existing 1–10 / 0.5-step contract;
- reaction;
- replacement feedback summary;
- structured feedback signals using controlled vocabulary terms.

The old v1 summary is context only. If the user explicitly confirms it, it may be represented again as current explicit evidence. Otherwise it must not be silently promoted.

### 11.5 Write feedback

Use existing `edit_viewing_feedback` for `primary` and change only components justified by the fresh response.

Existing mutation behavior already records changed components in `history.previous` and `history.current`. Therefore the current feedback can become the fresh opinion while historical v1 content remains auditable without a new `legacy_review` field.

### 11.6 Semantic catch-up

After feedback is current, evaluate work semantics separately.

- Missing semantic fingerprint is an unambiguous catch-up signal.
- Existing fingerprint is not rebuilt solely because it has fewer traits than another work.
- No arbitrary “minimum trait count” is introduced in this pilot.
- New semantic traits must use the existing controlled vocabulary.
- Vocabulary expansion is a separate architecture/developer change.
- User reaction may guide attention but cannot itself prove a work trait.

Example:

- “мне было затянуто” may support user feedback `reaction.pacing_dragging`;
- it does **not** automatically prove work trait `pacing.slow`.

If semantic catch-up is required, write it with existing `set_semantic_fingerprint`.

### 11.7 Complete item

An item becomes `reviewed` only when:

- the fresh feedback step is successfully represented on current `main`; and
- every semantic step required for that item is either successfully completed or deterministically determined unnecessary.

A technical failure leaves the item `in_progress` with enough operational metadata to resume without repeating already completed user work.

## 12. Structured feedback rules

The pilot is intentionally conservative.

- `source: explicit` is used only for meaning actually stated or clearly confirmed in the current reassessment.
- `strength: 1..3` reflects the expressed intensity of the user reaction, not model confidence.
- If sentiment/term mapping is materially ambiguous, omit the signal rather than fabricate ground truth.
- Work traits and reaction-kind terms remain distinct.
- Explicit similarity is not inferred merely because two works share traits or ratings.
- Ephemeral comments about mood/current context do not become stable preferences.

## 13. Session lifecycle

Default reassessment session size: **5 works**.

The user may continue beyond five, but five is the default operational chunk because it is long enough to collect several fresh signals and short enough to keep the interaction manageable.

At the end of any session with at least one newly reviewed item, run one `primary` taste reanalysis.

The session summary should be user-facing and brief:

- how many works were reviewed/deferred;
- whether any semantic catch-up occurred;
- after reanalysis, what materially changed in the system’s understanding of `primary` taste.

Infrastructure details remain hidden in normal use unless the user asks.

## 14. Batched taste reanalysis

Taste reanalysis happens once per session, not after each work.

The agent rebuilds candidate hypotheses from current raw/explicit evidence. Previous inferred hypotheses are not independent evidence and must not self-reinforce.

If the evidence supports a changed hypothesis set, persist the full replacement via existing `set_inferred_preferences` for `primary`.

A weaker or empty hypothesis set is valid if the fresh evidence no longer supports older conclusions. Old hypotheses are not retained merely for continuity.

`partner` and `couple` inferred state are not rewritten by this pilot. Any existing group/profile rebuild effects already defined by current infrastructure remain derived behavior, not new explicit group evidence.

## 15. Ground-truth relationship to Stage B

Fresh reassessment produces high-value **confirmed explicit evidence**, but the pilot does not automatically declare every reviewed work part of the Stage B decision benchmark.

Stage B will later define benchmark selection, stratification and leakage rules. Reassessed works become eligible source material for that process.

Historical v1 text remains historical evidence; current reassessment becomes current explicit evidence. This distinction must remain visible in provenance/history.

## 16. Failure and resume semantics

The workflow is fail-closed around canonical writes.

- A failed feedback mutation does not advance the item to `reviewed`.
- A successful feedback mutation followed by failed semantic catch-up leaves the item `in_progress` and resume continues after feedback.
- A failed ledger update must not cause canonical media data to be rolled back; instead the next session reconciles ledger state against current canonical state before asking the user to repeat anything.
- Unknown/ambiguous work identity blocks mutation until resolved.
- Provider metadata failure is not allowed to corrupt a reassessment of an already canonical work.

Because the ledger is operational state rather than media truth, canonical media state always wins when reconciling an interrupted session.

## 17. Security and write-boundary requirements

This project is an architecture/tooling change and follows the manual developer route during implementation.

Runtime reassessment must preserve current safety boundaries:

- no arbitrary model-authored shell or YAML patch for canonical media;
- normal media writes use typed request schemas and deterministic services;
- semantic writes must validate controlled vocabulary;
- pilot tooling must not broaden privileged auto-merge trust implicitly;
- if any path policy changes are required, they receive the same trusted-main/fail-closed review standard as Stage A;
- no model/provider secrets are introduced into browser/static data paths.

## 18. Documentation deliverables

Documentation is part of completion, not follow-up cleanup.

Implementation must update as applicable:

- `media/AGENTS.md` — add the agent-level legacy reassessment route and user-experience contract;
- `docs/architecture/intelligence.md` — document reassessment evidence/semantic separation and batched reanalysis;
- `docs/architecture/write-pipeline.md` — only if pilot ledger/tooling changes write-boundary semantics;
- `docs/reference/` — document the reassessment queue/ledger helper and any CLI contract;
- a dedicated pilot runbook — start/resume session, card format, statuses, deferred pass, batch reanalysis and completion procedure;
- `docs/status/current.md` — after implementation, describe the capability and its limitations;
- executable documentation/contract tests wherever the repository already enforces synchronization.

The pilot runbook must be sufficient for a new conversation to resume the process without relying on hidden conversational memory.

## 19. Testing requirements

At minimum, implementation must cover:

### Queue/cohort

- deterministic frozen cohort generation;
- inclusion of intended `primary` historical/watched evidence;
- exclusion of clearly `unwatched` no-evidence records;
- exclusion of `partner`/`couple` as reassessment targets;
- stable ordering and tie-breaking.

### Ledger lifecycle

- valid `pending -> in_progress -> reviewed` transition;
- valid `pending -> deferred` transition;
- reviewed item cannot automatically reopen in the same `pilot_id`;
- deferred items do not reappear during the main pending pass;
- `in_progress` items resume first;
- `seen_work_ids` prevents same-session duplicate presentation;
- new diagnostic flags do not override `reviewed`.

### Reassessment card

- deterministic card payload;
- spoiler-free synopsis excerpt source behavior;
- current rating/reaction/summary and structured-signal presence are represented correctly;
- card generation does not mutate state.

### Feedback/history

- reassessment replacement preserves prior value in standard history;
- only justified components change;
- user silence about a component does not clear it;
- old summary is not automatically converted into new explicit signals.

### Semantic separation

- reaction terms are not written as work traits;
- missing fingerprint is surfaced as catch-up need;
- existing fingerprint is not declared insufficient by arbitrary trait-count threshold;
- unknown vocabulary terms fail validation rather than being invented.

### Resume/idempotence

- interrupted after feedback / before semantic catch-up resumes at semantic stage;
- completed human feedback is not asked again solely because a later technical stage failed;
- changed-after-review is informational and does not reopen automatically.

### Reanalysis

- one session produces one `primary` reanalysis step;
- old inferred hypotheses are not accepted as independent evidence;
- partner/couple explicit state is not mutated.

### Full gates

The completed developer change runs the repository’s full authoritative development verification, including at least:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Web checks are required if implementation changes web/broker-visible behavior.

## 20. Rollout

1. Implement queue/cohort/ledger foundations and documentation first, behavior-neutral to existing media routes.
2. Initialize `primary-legacy-v1` from a fixed current revision and inspect the generated cohort before using it.
3. Run a small live pilot session of approximately five works.
4. Verify resume, anti-loop and history behavior from real pilot output.
5. Continue through the frozen cohort in repeated sessions.
6. After the main pending pass, handle deferred items separately.
7. When the cohort is exhausted, freeze/archive the pilot ledger and use the confirmed evidence as input to Stage B evaluation/ground-truth design.

## 21. Success criteria

The design is successful when:

- the user can resume in a new conversation and immediately continue at the correct next work;
- each cohort work is automatically presented at most once per pilot epoch unless explicitly reopened;
- every reviewed item has fresh current explicit feedback and preserved historical context;
- semantic catch-up improves missing work semantics without converting subjective reaction into factual traits;
- `primary` taste reanalysis occurs in session-sized batches rather than per-film churn;
- partner/couple data remains untouched by the pilot;
- canonical mutations continue to use existing typed operations and verification gates;
- documentation fully explains both architecture and day-to-day pilot operation;
- the resulting confirmed evidence can feed Stage B without treating old inferred labels as ground truth.
