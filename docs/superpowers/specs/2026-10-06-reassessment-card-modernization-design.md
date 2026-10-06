# Reassessment Card Modernization — Design

**Date:** 2026-10-06  
**Status:** proposed for implementation planning  
**Base revision:** `d85596038cc42a0d2f6c417fc7e4e2eff8e6a89e`  
**Related pilot:** `primary-legacy-v1`

## 1. Context

The active Legacy Reassessment Pilot intentionally updates only fresh human evidence. That separation was correct for protecting review quality, but it is narrower than the original product goal: old work cards should be brought forward so that, after the user revisits them, they look like cards processed under the current media pipeline rather than cards left with legacy metadata/semantic state.

The gap is visible on `grand-budapest-hotel-2014`: current primary and partner feedback are now explicit and useful, while provider metadata and the work semantic fingerprint still reflect the older enrichment state.

The modernization cycle must close that gap without undoing the reassessment safeguards and without using user reaction as an automatic substitute for work semantics.

## 2. Goal

For every work that reaches terminal human reassessment in `primary-legacy-v1`, perform a resumable follow-up that:

1. keeps the reassessed viewer evidence authoritative and unchanged;
2. refreshes factual provider metadata for that specific work using the current provider pipeline;
3. independently re-evaluates the work semantic fingerprint against the current controlled vocabulary;
4. records durable modernization provenance so a fresh conversation can tell whether the work is complete, due, or blocked;
5. never asks the user to reassess the same work again merely because modernization was incomplete or later retried.

A human-reassessed item and a fully modernized item are therefore distinct states.

## 3. Non-goals

This cycle does not:

- change recommendation formulas, affinity weights, Stage B benchmark rules, or taste calibration;
- infer work traits directly from whether the user liked or disliked the work;
- rewrite `primary`, `partner`, or `couple` feedback while performing metadata/semantic modernization;
- change the controlled vocabulary itself;
- require global metadata refreshes of the entire library for each reassessed work;
- make metadata/semantic failure reopen a human reassessment item;
- treat modernization as a reason to reset the existing 15-review taste-reanalysis cadence.

## 4. Separation of concerns

The four-layer model remains authoritative:

1. factual work metadata;
2. work semantic fingerprint;
3. viewer/group evidence;
4. inferred taste hypotheses.

Legacy reassessment still owns layer 3. Card modernization owns layers 1 and 2. Scheduled taste reanalysis continues to own layer 4.

A statement such as “the absurd humor did not work for me” may immediately produce viewer feedback `humor.absurd -> negative` when supported by the user’s words. It does **not** by itself prove that `humor.absurd` belongs in the work fingerprint. Work semantics must be produced independently through the current semantic-enrichment procedure using current factual/source context and the controlled vocabulary.

## 5. Recommended architecture

Use a three-step follow-up after human completion rather than one monolithic operation.

### 5.1 Step A — human reassessment

Existing behavior remains unchanged:

- `complete_reassessment_item` finalizes fresh `primary` evidence and terminal human lifecycle state;
- optional clearly attributed partner evidence is handled afterward through ordinary feedback operations;
- the item must never be shown again automatically once human status is `reviewed`.

### 5.2 Step B — single-work metadata refresh

Add a new narrow typed operation:

`refresh_work_metadata`

It refreshes exactly one existing canonical work and reuses the current provider-resolution/merge logic from `media/service/refresh.py`.

Requirements:

- exactly one `work_ref`;
- no bulk scope;
- no viewer, semantic, preference, pilot-ledger, schema, vocabulary, or workflow mutation;
- provider identity must resolve safely under the existing identity-compatibility rules;
- stable canonical TMDB identity is the preferred direct route;
- stable IMDb resolution may be accepted when unique and identity-compatible;
- ambiguous or conflicting identity fails closed and leaves the work blockable for modernization;
- the operation is eligible for guarded auto-merge because its path scope is one work plus normal generated/receipt artifacts and identity checks are deterministic.

The existing `refresh_metadata(scope=all_movies)` remains the manual bulk-maintenance route and is not repurposed for this workflow.

### 5.3 Step C — semantic fingerprint refresh

After the metadata refresh is authoritative on `main`, re-read the canonical work and current `media/vocabulary.yaml`.

Use the existing `set_semantic_fingerprint` operation to replace the work semantic traits with the best current fingerprint supported by the refreshed factual/source context and the controlled vocabulary.

Rules:

- semantic traits describe the work, never the viewer;
- user feedback may guide what distinctions are worth examining, but may not be copied into work semantics merely because the user stated them;
- only current vocabulary terms are permitted;
- an empty trait set is valid if the current evidence does not justify any controlled terms;
- the semantic operation may be an applied no-op when the existing fingerprint already matches the current result; that still counts as an explicit semantic check for modernization provenance.

This design deliberately reuses `set_semantic_fingerprint` rather than creating a second semantic-write mechanism.

## 6. Modernization state in the reassessment ledger

Do not create a second pilot ledger. Extend the existing `media/pilots/legacy-reassessment-primary.json` item lifecycle with a separate modernization sub-state that does not alter the terminal human reassessment state.

Conceptually:

```json
{
  "status": "reviewed",
  "outcome": "changed",
  "modernization": {
    "status": "completed",
    "metadata_operation_id": "...",
    "semantic_operation_id": "...",
    "completed_at": "...",
    "work_digest": "sha256:...",
    "vocabulary_digest": "sha256:..."
  }
}
```

Modernization interpretation:

- human item not yet `reviewed`: modernization is not applicable;
- human item `reviewed` and no modernization object: modernization is due;
- `modernization.status = blocked`: a deterministic modernization attempt cannot proceed without resolving the recorded blocker;
- `modernization.status = completed`: this pilot epoch has completed the current modernization pass.

Allowed modernization transitions are:

- absent/due → `blocked`;
- absent/due → `completed`;
- `blocked` → `completed` after the blocker is resolved.

`completed` is terminal for this modernization epoch. None of these transitions may alter or reopen the human `reviewed` state, outcome, exposure provenance, or reviewed timestamp. A later vocabulary/provenance migration may define a new enrichment epoch rather than rewriting this historical completion marker.

## 7. Modernization ledger operation

Add one narrow ledger-only typed operation:

`record_reassessment_modernization`

It records one of two outcomes for one already-reviewed work:

- `completed` — authoritative metadata refresh and semantic refresh both succeeded;
- `blocked` — modernization cannot safely continue because of a deterministic blocker that requires resolution outside the normal automatic flow.

Common inputs include:

- `operation_id`;
- `pilot_id`;
- `work_id`;
- `outcome`;
- current `expected_ledger_digest`;
- current `expected_work_digest`.

For `completed`, inputs additionally include:

- `metadata_operation_id`;
- `semantic_operation_id`;
- current `vocabulary_digest`.

For `blocked`, inputs additionally include a narrow blocker code such as:

- `provider_identity_missing`;
- `provider_identity_ambiguous`;
- `provider_identity_conflict`;
- `semantic_context_insufficient`.

The implementation may add another blocker code only when a concrete fail-closed condition requires it; free-form blocker strings are not accepted.

Preconditions for all outcomes:

- pilot and work match the frozen cohort;
- human item status is `reviewed`;
- current ledger digest matches;
- current work digest matches;
- an already `completed` modernization cannot be rewritten.

Additional preconditions for `completed`:

- referenced metadata receipt exists, is `applied`, is a `refresh_work_metadata` operation for the same work, and occurred after human completion;
- referenced semantic receipt exists, is `applied`, is `set_semantic_fingerprint` for the same work, and occurred after the referenced metadata operation;
- the supplied vocabulary digest matches current `media/vocabulary.yaml` bytes.

Additional preconditions for `blocked`:

- blocker code is from the controlled set;
- the block does not claim a successful metadata/semantic completion;
- the current work remains otherwise untouched by the ledger operation.

Effects:

- mutate only the exact reassessment ledger path plus the normal operation receipt;
- record the modernization outcome and provenance;
- never mutate canonical work/viewer data itself.

## 8. Read-only modernization context

Add a read-only helper/CLI surface:

`reassessment-modernization-context`

It returns reviewed works that still need modernization attention, ordered by human completion time and frozen order as deterministic tie-breaker.

For each work it exposes only operational/factual fields needed by the agent, such as:

- work id/title/year;
- human reviewed timestamp;
- current metadata provider identity and fetch timestamp;
- current semantic trait count;
- current work digest;
- current vocabulary digest;
- modernization status and blocker code when present.

It does not expose or alter user feedback as an input to semantic truth.

Default selection returns due items first, then blocked items only when the caller explicitly requests retry/recovery or the blocker is known to be resolved. Completed items do not re-enter automatically.

On startup, this context is checked before creating a new reassessment session. Due modernization from already-reviewed items should be drained first so an interrupted conversation resumes the full end-to-end workflow rather than silently accumulating stale cards.

## 9. Conversation workflow

After this design is active, the normal per-work flow becomes:

1. reserve/reuse the current reassessment session;
2. present the neutral unanchored card;
3. collect fresh user response;
4. atomically complete `primary` reassessment;
5. process any net-new attributed partner feedback separately;
6. run `refresh_work_metadata` for the same work;
7. re-read the refreshed canonical work and current vocabulary;
8. derive and apply `set_semantic_fingerprint` independently;
9. record `record_reassessment_modernization(outcome=completed)`;
10. only then present the next reassessment card, unless modernization is genuinely blocked.

If modernization fails because of provider identity or another deterministic blocker:

- do not undo or reopen the human reassessment;
- do not ask the user to repeat the review;
- when the blocker maps to the controlled blocker set, record `record_reassessment_modernization(outcome=blocked)`;
- report the blocker only if user action is required;
- continue the human session when safe;
- leave the blocked item available for explicit recovery without placing it back into the normal human queue.

## 10. Backfill for already-reviewed works

When this feature lands, existing terminal human items without a modernization marker are automatically considered due.

The first backfill set is therefore at least:

- `gattaca-1997`;
- `grand-budapest-hotel-2014`.

No human reassessment is repeated. The agent runs only metadata refresh, semantic refresh, and modernization recording for them.

The exact due set must come from the current ledger at execution time rather than being hard-coded in code or prompts.

## 11. Session close and taste reanalysis

Human session close remains based on resolution of the reserved reassessment items. Modernization does not change the meaning of `reviewed`, `changed`, `confirmed_unchanged`, or `deferred`.

Operationally, the agent should try to modernize each reviewed item before moving to the next card. However, modernization failure must not make the human session impossible to close.

Closed-session audit/progress should be extended with modernization counts only if doing so can be derived deterministically without changing existing Stage A baseline semantics. At minimum, current pilot status/read models should expose:

- human reviewed count;
- reviewed-but-modernization-due count;
- modernization blocked count;
- modernization completed count.

Scheduled taste reanalysis remains triggered by fresh human review milestones (15 newly reviewed works, end main pass, explicit request). Modernization alone does not increment that cadence.

## 12. Concurrency and trust

All new writes use the existing typed command / deterministic transaction / path-policy / exact-head Media Check / privileged auto-merge model.

`refresh_work_metadata` protects against stale work state with an expected work digest so a concurrent feedback or other work mutation causes fail-closed/replay rather than overwriting current data.

`record_reassessment_modernization` serializes on both current ledger digest and current work digest.

The existing reassessment transition validator must preserve all human anti-loop invariants while allowing only the new monotonic modernization sub-state transitions.

Normal non-pilot operations still may not mutate the pilot ledger. Only the dedicated modernization recording operation may add or advance modernization provenance there.

## 13. Validation and tests

Required tests include:

1. reviewed item without modernization is returned as due;
2. pending/in-progress/deferred human item is not eligible for modernization recording;
3. single-work metadata refresh changes only the selected work and allowed derived/receipt paths;
4. stale expected work digest fails closed;
5. metadata identity conflict/ambiguity fails closed without altering the work;
6. semantic refresh cannot write unknown vocabulary terms or reaction-kind terms;
7. viewer feedback is unchanged across metadata/semantic modernization;
8. completed modernization requires matching applied metadata and semantic receipts for the same work;
9. semantic receipt must occur after metadata refresh;
10. vocabulary digest mismatch fails completed modernization;
11. blocked modernization accepts only controlled blocker codes and cannot modify human completion state;
12. blocked modernization may advance to completed but completed cannot be rewritten or reopened;
13. modernization recording cannot revert or rewrite human `reviewed` state/outcome/exposure;
14. completed modernization does not automatically re-enter the due queue;
15. startup/resume prefers due modernization before reserving a fresh human batch;
16. Gattaca/Grand Budapest-style pre-existing reviewed items become due without repeating human reassessment;
17. all existing reassessment, operation-path, doctor, rebuild, audit, and matcher tests remain green.

## 14. Documentation changes

Update living documentation so the user-facing process is described as one end-to-end workflow while internal evidence boundaries remain explicit:

- `media/AGENTS.md`;
- `media/START_PROMPT.md`;
- `docs/runbooks/media-legacy-reassessment.md`;
- `docs/status/current.md`;
- `docs/reference/media-commands.md` and invariants as needed.

The key user-level invariant becomes:

> After a legacy work is reassessed, the system should bring the card through current metadata and semantic enrichment rules without asking the user to repeat the review. Human reassessment, work modernization, and taste reanalysis remain separate evidence layers even though they are orchestrated as one conversation flow.

## 15. Rollout

Implement and activate the modernization contract before continuing the live reassessment beyond the currently reviewed items.

After merge:

1. recover current pilot state from `main`;
2. run modernization context;
3. modernize all already-reviewed/due items without human re-prompting;
4. verify their markers are authoritative on `main`;
5. resume the existing open human session at its next unresolved item;
6. for every later reviewed item, perform modernization before advancing to the next card when possible.
