# Reassessment Card Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every terminal legacy reassessment item resumably pass through current single-work metadata refresh and independent semantic refresh, then record durable modernization provenance without reopening human reassessment.

**Architecture:** Keep the existing human reassessment lifecycle unchanged and add a separate modernization sub-state on each reviewed ledger item. Reuse existing provider resolution/merge logic and `set_semantic_fingerprint`; add only a narrow one-work metadata operation, a read-only modernization context, and one ledger-only modernization outcome operation. All writes continue through the typed command → deterministic planner → path policy → exact-head check → guarded auto-merge trust model.

**Tech Stack:** Python 3.12, dataclasses, JSON Schema, pytest, existing YAML repository/transaction services, GitHub Actions trust workflows.

**Spec:** `docs/superpowers/specs/2026-10-06-reassessment-card-modernization-design.md`

## Global Constraints

- Human reassessment `status: reviewed` remains terminal and must never be reopened by modernization.
- Modernization owns factual metadata and work semantics only; it must not mutate viewer/group feedback or taste hypotheses.
- Viewer reaction is not semantic truth. `set_semantic_fingerprint` remains an independent semantic write using current vocabulary terms only.
- `refresh_metadata(scope=all_movies)` remains the manual bulk-maintenance route; modernization adds a distinct one-work operation.
- Every mutating operation must fail closed on stale authoritative state.
- `refresh_work_metadata` and `set_semantic_fingerprint` may legitimately produce authoritative `status: no_change`; those trusted receipts are valid modernization evidence when all path/exact-head guards pass.
- A modernization failure must not require the user to repeat the human review.
- Scheduled taste reanalysis cadence remains based only on human review milestones.
- Existing Stage A reassessment anti-loop, historical-exposure, audit, and guarded-merge invariants remain intact.

## Review Focus

1. A concurrent feedback edit between planning and `refresh_work_metadata` must produce a stale-work failure rather than overwrite the new feedback. Covered in Task 2.
2. A metadata or semantic receipt for another work, an untrusted/wrong-kind `no_change` receipt, or receipts in the wrong order must not attest modernization completion. Covered in Tasks 3 and 5.
3. `blocked → completed` must be legal while `completed → blocked/completed rewrite` remains illegal and human reassessment fields remain immutable. Covered in Task 5.
4. Existing reviewed items created before this feature must appear as modernization-due without migration or human re-prompt. Covered in Tasks 4 and 7.
5. Trusted automation must treat the new provider operation, idempotent no-change checks, and ledger operation with the same exact-head/path/stale-state discipline as existing applied operations. Covered in Tasks 3 and 5.

---

### Task 1: Add typed modernization command contracts

**Files:**
- Modify: `media/domain/commands.py`
- Modify: `media/commands/schema.py`
- Create: `media/commands/schemas/refresh_work_metadata.schema.json`
- Create: `media/commands/schemas/record_reassessment_modernization.schema.json`
- Modify: `tests/media/test_command_contracts.py`

**Interfaces:**
- Produces: `RefreshWorkMetadataCommand(schema_version, operation_id, work_ref, expected_work_digest)`.
- Produces: `RecordReassessmentModernizationCommand(schema_version, operation_id, pilot_id, work_id, outcome, expected_ledger_digest, expected_work_digest, metadata_operation_id=None, semantic_operation_id=None, vocabulary_digest=None, blocker_code=None)`.
- `outcome` is exactly `completed | blocked`.
- `blocker_code` is exactly one of `provider_identity_missing`, `provider_identity_ambiguous`, `provider_identity_conflict`, `semantic_context_insufficient`.

- [ ] **Step 1: Write failing parser/schema tests**

Add tests asserting:
- valid `refresh_work_metadata` requires one `work_ref` plus `expected_work_digest` matching `^sha256:[0-9a-f]{64}$`;
- valid `record_reassessment_modernization` parses both `completed` and `blocked` variants;
- `completed` requires metadata operation id, semantic operation id, and vocabulary digest and rejects blocker code;
- `blocked` requires blocker code and rejects completion fields that claim success;
- operation ids use canonical lowercase UUID validation.

- [ ] **Step 2: Run targeted tests and verify RED**

Run: `python -m pytest tests/media/test_command_contracts.py -q`

Expected: FAIL because the operations/schemas/dataclasses are not registered.

- [ ] **Step 3: Add dataclasses, schemas, and parser branches**

Register both operations in `_SCHEMA_BY_OPERATION`, add them to `MediaCommand`, and parse conditional fields without adding free-form blocker text.

- [ ] **Step 4: Run targeted tests and verify GREEN**

Run: `python -m pytest tests/media/test_command_contracts.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add reassessment modernization commands`

---

### Task 2: Implement stale-safe single-work metadata refresh

**Files:**
- Modify: `media/service/refresh.py`
- Modify: `media/service/transaction.py`
- Modify: `media/cli.py`
- Create: `tests/media/test_refresh_work_metadata.py`
- Modify: `tests/media/test_refresh_transaction.py`
- Modify: `tests/media/test_cli.py`

**Interfaces:**
- Produces: `plan_refresh_work_metadata(repo: YamlRepository, command: RefreshWorkMetadataCommand, provider: MetadataProvider | None, *, now: datetime | None = None) -> MutationPlan`.
- Reuses existing `_resolve_candidate`, `_identity_compatible`, `_merge_external`, and `_refreshed_document` logic instead of copying provider reconciliation.
- Receipt `details` always include `work_id`, `expected_work_digest`, and resulting/current `work_digest`, including `no_change`.

- [ ] **Step 1: Write failing planner tests**

Cover:
- stable TMDB identity refreshes exactly one selected work;
- unique IMDb resolution is accepted when identity-compatible;
- missing/ambiguous/conflicting identity fails closed through existing metadata preflight semantics;
- stale `expected_work_digest` is rejected before provider data can overwrite the file;
- viewer signals and semantic fingerprint survive metadata refresh unchanged;
- another work is never modified;
- already-current provider data yields a `no_change` result with binding details.

- [ ] **Step 2: Run targeted tests and verify RED**

Run: `python -m pytest tests/media/test_refresh_work_metadata.py tests/media/test_refresh_transaction.py -q`

Expected: FAIL because planner/command dispatch does not exist.

- [ ] **Step 3: Add the one-work planner**

Use the exact canonical work bytes for the stale digest check. Preserve manual overrides through existing merge rules. Set index rebuild only when the canonical work changes. Always return binding details for the receipt.

- [ ] **Step 4: Wire transaction and CLI provider detection**

Add `RefreshWorkMetadataCommand` to `MutableCommand`, `_plan`, CLI imports, and `needs_provider`. Provider absence uses the existing provider-unavailable path.

- [ ] **Step 5: Verify planner and CLI GREEN**

Run:
- `python -m pytest tests/media/test_refresh_work_metadata.py tests/media/test_refresh_transaction.py -q`
- `python -m pytest tests/media/test_cli.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

Commit message: `feat: add single-work metadata refresh`

---

### Task 3: Bind idempotent semantic checks and harden trusted automation

**Files:**
- Modify: `media/service/intelligence.py`
- Modify: `media/config/operation_path_policy.json`
- Modify: `media/service/path_policy.py`
- Modify: `.github/workflows/media-command.yml`
- Modify: `.github/workflows/media-auto-merge.yml`
- Modify: `.github/workflows/media-check.yml`
- Modify: `tests/media/test_semantic_fingerprint.py`
- Modify: `tests/media/test_path_policy.py`
- Modify: `tests/media/test_reassessment_path_policy.py`
- Modify: `tests/media/test_auto_merge_dispatch_contract.py`
- Modify: `tests/media/test_reassessment_workflow_contract.py`

**Interfaces:**
- `plan_set_semantic_fingerprint(...)` always sets receipt details containing `work_id`, including `no_change`.
- `refresh_work_metadata` allowed paths: selected canonical work when changed, generated index when changed, and receipt; `auto_merge: true`.
- `record_reassessment_modernization` allowed paths: exact pilot ledger plus receipt; `auto_merge: true`.
- `verify_operation_specific_paths` uses `details.work_id` to reject mismatched work-file paths.
- Trusted auto-merge accepts `status: no_change` only for `refresh_work_metadata` and `set_semantic_fingerprint`.

- [ ] **Step 1: Write failing semantic receipt tests**

Add `tests/media/test_semantic_fingerprint.py` coverage proving both changed and unchanged semantic plans expose `details.work_id` and unchanged viewer data.

- [ ] **Step 2: Write failing path/workflow tests**

Assert:
- `refresh_work_metadata` cannot modify a second work, preferences, vocabulary, or pilot ledger;
- `record_reassessment_modernization` cannot modify canonical works/generated files;
- `Media Command` marks `refresh_work_metadata` provider-dependent;
- trusted `no_change` receipts for `refresh_work_metadata` and `set_semantic_fingerprint` can reach exact-head check/merge;
- `no_change` for unrelated operations remains rejected;
- before merge, `refresh_work_metadata` compares current-main work SHA with `details.expected_work_digest`;
- before merge, `record_reassessment_modernization` compares both current-main ledger digest and the referenced current-main work digest with receipt details;
- `Media Check` accepts the dedicated modernization ledger transition and still rejects ledger mutation under unrelated operations.

- [ ] **Step 3: Run targeted tests and verify RED**

Run:
`python -m pytest tests/media/test_semantic_fingerprint.py tests/media/test_path_policy.py tests/media/test_reassessment_path_policy.py tests/media/test_auto_merge_dispatch_contract.py tests/media/test_reassessment_workflow_contract.py -q`

Expected: FAIL on missing details/policies/workflow branches.

- [ ] **Step 4: Add semantic receipt binding**

Return planner `details={"work_id": record.id}` (plus only deterministic fields needed later) from `plan_set_semantic_fingerprint` whether the traits changed or not.

- [ ] **Step 5: Add declarative policy and operation-specific path checks**

Keep wildcard grammar unchanged. Add only narrow new policy entries and selected-work shape validation. Receipt-only no-change output must remain policy-valid.

- [ ] **Step 6: Harden workflows**

In trusted workflow code:
- provider dispatch recognizes `refresh_work_metadata`;
- `refresh_work_metadata` validates current-main work digest immediately before merge;
- `record_reassessment_modernization` is added to the pilot-ledger allowlist and validates both current-main ledger and work digests immediately before merge;
- `no_change` is accepted only for the two explicitly idempotent modernization check operations;
- exact-head Media Check remains mandatory.

- [ ] **Step 7: Verify GREEN**

Run the same targeted suite from Step 3.

Expected: PASS.

- [ ] **Step 8: Commit**

Commit message: `security: trust reassessment modernization writes`

---

### Task 4: Add resumable modernization context

**Files:**
- Modify: `media/service/reassessment.py`
- Modify: `media/cli.py`
- Create: `tests/media/test_reassessment_modernization_context.py`
- Modify: `tests/media/test_reassessment_cli.py`

**Interfaces:**
- Produces: `build_reassessment_modernization_context(repo: CanonicalRepository, document: Mapping[str, Any], *, include_blocked: bool = False, limit: int = 20) -> dict[str, Any]`.
- CLI: `python -m media.cli reassessment-modernization-context --limit N [--include-blocked] --format json`.
- Output includes `pilot_id`, `ledger_digest`, `vocabulary_digest`, and factual/operational cards only.

- [ ] **Step 1: Write failing context tests**

Assert:
- `reviewed` with no modernization object is due;
- `pending`, `in_progress`, and `deferred` are not due;
- `completed` never re-enters automatically;
- `blocked` is excluded by default and included only with `include_blocked=true`;
- pre-feature reviewed items are due without migration;
- ordering is `reviewed_at`, then frozen `order_rank`, then work id;
- cards expose title/year/provider identity/fetched timestamp/semantic trait count/work digest/vocabulary digest but not viewer feedback/history.

- [ ] **Step 2: Run targeted tests and verify RED**

Run: `python -m pytest tests/media/test_reassessment_modernization_context.py tests/media/test_reassessment_cli.py -q`

Expected: FAIL because the context/CLI does not exist.

- [ ] **Step 3: Implement digest helpers and context builder**

Reuse `file_sha256`. Compute work digest from exact canonical YAML bytes and vocabulary digest from exact `media/vocabulary.yaml` bytes.

- [ ] **Step 4: Add CLI surface**

Require an active ledger like `reassessment-context`. Keep it read-only and outside `MediaCommand`.

- [ ] **Step 5: Verify GREEN**

Run the same targeted suite from Step 2.

Expected: PASS.

- [ ] **Step 6: Commit**

Commit message: `feat: expose reassessment modernization context`

---

### Task 5: Implement modernization ledger outcomes and transition validation

**Files:**
- Modify: `media/service/reassessment_mutate.py`
- Modify: `media/service/reassessment_validation.py`
- Modify: `media/service/transaction.py`
- Modify: `media/tools/validate_reassessment_transition.py`
- Create: `tests/media/test_reassessment_modernization_mutate.py`
- Modify: `tests/media/test_reassessment_mutations.py`
- Modify: `tests/media/test_reassessment_completion_validation.py`
- Modify: `tests/media/test_reassessment_transition.py`
- Modify: `tests/media/test_reassessment_security_review_regressions.py`

**Interfaces:**
- Produces: `plan_record_reassessment_modernization(repo_root: Path, repo: YamlRepository, command: RecordReassessmentModernizationCommand, *, now: datetime | None = None) -> MutationPlan`.
- `repo_root` is the authoritative transaction workspace root (the temporary repo during execution); the planner reads the current ledger, canonical work bytes, vocabulary bytes, and referenced `.media/operations/<id>.json` receipts from that root rather than treating receipts as `YamlRepository` state.
- Receipt details include `work_id`, `outcome`, `expected_ledger_digest`, `expected_work_digest`, and resulting modernization record.
- Metadata and semantic evidence receipts may each have `status: applied` or trusted `status: no_change`.

- [ ] **Step 1: Write failing completion tests**

For `completed`, reject when:
- work is not human `reviewed`;
- ledger/work digest is stale;
- metadata receipt is missing, status is not `applied|no_change`, operation/work binding is wrong, or it predates human review;
- semantic receipt is missing, status is not `applied|no_change`, `details.work_id` is wrong/missing, or it occurs before metadata receipt;
- vocabulary digest is stale;
- modernization is already completed.

Also prove successful completion when either evidence receipt is a valid authoritative `no_change` receipt.

- [ ] **Step 2: Write failing blocked/transition tests**

Assert:
- only controlled blocker codes are accepted;
- absent→blocked and blocked→completed are legal;
- completed cannot be rewritten or reopened;
- blocked→blocked rewrite is rejected;
- canonical work is untouched;
- human status/outcome/exposure/reviewed timestamp never change.

- [ ] **Step 3: Run targeted tests and verify RED**

Run:
`python -m pytest tests/media/test_reassessment_modernization_mutate.py tests/media/test_reassessment_mutations.py tests/media/test_reassessment_completion_validation.py tests/media/test_reassessment_transition.py tests/media/test_reassessment_security_review_regressions.py -q`

Expected: FAIL because planner/validation does not exist.

- [ ] **Step 4: Implement planner and transaction dispatch**

Write only `media/pilots/legacy-reassessment-primary.json` through `json_documents`. Preserve human lifecycle fields byte-for-value. Use receipt timestamps/operation/details from authoritative repository state rather than trusting caller claims.

- [ ] **Step 5: Extend snapshot validator**

Validate:
- only reviewed items may carry modernization;
- controlled statuses/blockers;
- completed provenance fields/digests present;
- blocked has no fake completion ids;
- completed is terminal.

- [ ] **Step 6: Extend base→head transition validator**

Permit only absent→blocked, absent→completed, blocked→completed. Reject deletion, blocked rewrite loops, completed rewrite, or any simultaneous protected human-state mutation.

- [ ] **Step 7: Verify GREEN**

Run the same targeted suite from Step 3.

Expected: PASS.

- [ ] **Step 8: Commit**

Commit message: `feat: track reassessment modernization outcomes`

---

### Task 6: Update living agent/runbook contracts for end-to-end orchestration

**Files:**
- Modify: `media/AGENTS.md`
- Modify: `media/START_PROMPT.md`
- Modify: `docs/runbooks/media-legacy-reassessment.md`
- Modify: `docs/status/current.md`
- Modify: `docs/reference/media-commands.md`
- Modify: `docs/reference/invariants.md`
- Modify: `tests/media/test_agent_ux_contract.py`
- Modify: `tests/media/test_reassessment_docs_contract.py`
- Modify: `tests/media/test_documentation_system.py`

**Interfaces:**
- Startup ordering: recover repository state → drain ordinary due modernization for already-reviewed items → resume existing human session or reserve next batch.
- Per-item ordering after a fresh answer: primary completion → optional partner follow-up → metadata refresh → independent semantic refresh → modernization marker → next human card.
- If deterministic modernization is blocked, record blocker, do not reopen human reassessment, and continue the session when safe.

- [ ] **Step 1: Write failing executable docs tests**

Pin semantics:
- human reassessment and work modernization are separate layers but one user-facing flow;
- no repeat human prompt for modernization retry;
- viewer feedback cannot be copied directly into work semantics;
- due modernization is recovered before new human batch reservation;
- next card normally waits for modernization completion/block recording for the previous reviewed item;
- trusted `no_change` metadata/semantic checks count as successful modernization evidence;
- taste reanalysis cadence remains 15/end-main/manual, not per modernization.

- [ ] **Step 2: Run docs tests and verify RED**

Run: `python -m pytest tests/media/test_agent_ux_contract.py tests/media/test_reassessment_docs_contract.py tests/media/test_documentation_system.py -q`

Expected: FAIL on the old terminal-flow wording.

- [ ] **Step 3: Update living docs**

Keep evidence separation, but replace the implication that the conversation flow ends after human evidence. Describe modernization as a follow-up, not as mutation inside `complete_reassessment_item`.

- [ ] **Step 4: Verify docs GREEN**

Run the same targeted suite from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `docs: make reassessment modernization end to end`

---

### Task 7: Full verification, guarded integration, and live backfill

**Files:**
- No new architecture files unless verification exposes a concrete defect.
- Runtime data after merge: operation receipts, already-reviewed work files only when metadata/semantics actually change, and modernization fields in `media/pilots/legacy-reassessment-primary.json`.

**Interfaces:**
- Uses `reassessment-modernization-context` as source of truth for due items.
- Uses normal operation branches/requests for `refresh_work_metadata`, `set_semantic_fingerprint`, and `record_reassessment_modernization`.
- `applied` and trusted `no_change` metadata/semantic receipts are both acceptable authoritative steps.

- [ ] **Step 1: Run full pre-merge gate**

Run:
- `python -m pytest -q`
- `python -m media.tools.validate .`
- `python -m media.cli rebuild --check`
- `python -m media.cli web-export --output /tmp/media-web-manifest.json --format json`
- `python -m media.cli doctor --format json`

Expected: all green/ok.

- [ ] **Step 2: Review exact diff and trust scope**

Confirm no migration changed viewer feedback, no vocabulary change exists, and no pilot item changed human terminal fields.

- [ ] **Step 3: Merge implementation only after exact-head CI is green**

Use the repository’s normal guarded development PR process. Do not mix live data backfill into the architecture PR.

- [ ] **Step 4: Re-read current `main` and modernization context**

Do not hard-code the due set. Verify already-reviewed items such as `gattaca-1997` and `grand-budapest-hotel-2014` appear due if still unmodernized.

- [ ] **Step 5: Modernize each due reviewed item sequentially**

For each due item:
1. apply `refresh_work_metadata` with fresh current work digest;
2. wait until its `applied` or trusted `no_change` receipt is authoritative on `main`;
3. re-read canonical work and current vocabulary;
4. derive semantic fingerprint independently of viewer sentiment;
5. apply `set_semantic_fingerprint` and wait for its `applied` or trusted `no_change` receipt on `main`;
6. apply `record_reassessment_modernization(outcome=completed)` with fresh ledger/work/vocabulary digests;
7. on deterministic provider/semantic blocker, record `outcome=blocked` instead of fabricating data.

- [ ] **Step 6: Verify backfill and resume human session**

Run read-only contexts again. Confirm completed modernization items are no longer due, the existing reassessment session still contains unresolved human items, and the next human card is not already reviewed.

- [ ] **Step 7: Final validation after backfill**

Run validate/rebuild/doctor and verify exact current-main work cards and ledger markers.
