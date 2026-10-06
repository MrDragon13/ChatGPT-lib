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
2. A metadata or semantic receipt for another work, an untrusted/wrong-kind `no_change` receipt, or receipts in the wrong order must not attest modernization completion. Covered in Task 5.
3. `blocked → completed` must be legal while `completed → blocked/completed rewrite` remains illegal and human reassessment fields remain immutable. Covered in Task 5.
4. Existing reviewed items created before this feature must appear as modernization-due without migration or human re-prompt. Covered in Task 4 and Task 7.
5. Trusted automation must treat the new provider operation, idempotent no-change checks, and ledger operation with the same exact-head/path/stale-state discipline as existing applied operations. Covered in Task 3 and Task 5.

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
- `blocked` requires blocker code and rejects completion operation ids/digest fields that claim success;
- all operation/session-style ids use canonical lowercase UUID validation.

- [ ] **Step 2: Run targeted tests and verify RED**

Run: `python -m pytest tests/media/test_command_contracts.py -q`

Expected: FAIL because the operations/schemas/dataclasses are not registered.

- [ ] **Step 3: Add dataclasses, schemas, and parser branches**

Register both operations in `_SCHEMA_BY_OPERATION`, add them to `MediaCommand`, and parse conditional fields without adding any free-form blocker text.

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
- Modify: `tests/media/test_cli.py`

**Interfaces:**
- Produces: `plan_refresh_work_metadata(repo: YamlRepository, command: RefreshWorkMetadataCommand, provider: MetadataProvider | None, *, now: datetime | None = None) -> MutationPlan`.
- Reuses existing `_resolve_candidate`, `_identity_compatible`, `_merge_external`, and `_refreshed_document` logic instead of copying provider reconciliation.
- Receipt `details` must include `work_id`, `expected_work_digest`, and the resulting/current `work_digest` even when canonical data is already current and the operation result is `no_change`.

- [ ] **Step 1: Write failing planner tests**

Cover:
- stable TMDB identity refreshes exactly one selected work;
- unique IMDb resolution is accepted when identity-compatible;
- missing/ambiguous/conflicting identity fails closed through existing metadata preflight error semantics;
- stale `expected_work_digest` is rejected before provider result can overwrite the file;
- viewer signals and semantic fingerprint survive metadata refresh byte-for-structure unchanged;
- another work is never modified;
- already-current provider data produces a `no_change` plan with binding details for the selected work.

- [ ] **Step 2: Run targeted tests and verify RED**

Run: `python -m pytest tests/media/test_refresh_work_metadata.py -q`

Expected: FAIL because planner/command dispatch does not exist.

- [ ] **Step 3: Extract/reuse one-work refresh primitives and add planner**

Use the canonical work file bytes for the stale digest check. Preserve manual overrides through the existing `_refreshed_document` merge rules. Set index rebuild only when the canonical work actually changes; do not rebuild taste profiles for factual metadata alone unless existing generated contracts require it. Always emit binding planner details for trusted receipt verification.

- [ ] **Step 4: Wire transaction and CLI provider detection**

Add `RefreshWorkMetadataCommand` to `MutableCommand`, `_plan`, CLI imports, and `needs_provider`. Provider absence must return the existing provider-unavailable error path.

- [ ] **Step 5: Verify planner and CLI GREEN**

Run:
- `python -m pytest tests/media/test_refresh_work_metadata.py -q`
- `python -m pytest tests/media/test_cli.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

Commit message: `feat: add single-work metadata refresh`

---

### Task 3: Extend trusted path and workflow policy for the new operations

**Files:**
- Modify: `media/config/operation_path_policy.json`
- Modify: `media/service/path_policy.py`
- Modify: `.github/workflows/media-command.yml`
- Modify: `.github/workflows/media-auto-merge.yml`
- Modify: `.github/workflows/media-check.yml`
- Modify: `tests/media/test_operation_path_policy.py` (or the existing path-policy contract file if named differently)
- Modify: `tests/media/test_auto_merge_dispatch_contract.py`

**Interfaces:**
- `refresh_work_metadata` allowed paths: exactly one canonical work when changed, normal generated index if changed, and one operation receipt; `auto_merge: true`.
- `record_reassessment_modernization` allowed paths: exact pilot ledger plus one operation receipt; `auto_merge: true`.
- `verify_operation_specific_paths` uses planner `details.work_id` to reject a work path not matching the selected work.
- Trusted auto-merge accepts `status: no_change` only for `refresh_work_metadata` and `set_semantic_fingerprint`; all other existing operation status rules remain unchanged.

- [ ] **Step 1: Write failing policy/workflow contract tests**

Assert:
- `refresh_work_metadata` cannot modify a second work, preferences, semantics code, vocabulary, or pilot ledger;
- `record_reassessment_modernization` cannot modify canonical works/generated files;
- `Media Command` marks `refresh_work_metadata` provider-dependent;
- auto-merge recognizes `record_reassessment_modernization` as a pilot-ledger transition and `refresh_work_metadata` as a normal stale-work guarded write;
- trusted `no_change` receipts for `refresh_work_metadata` and `set_semantic_fingerprint` can pass eligibility with receipt-only output plus transient request deletion;
- `no_change` for unrelated operations is still rejected by auto-merge;
- `Media Check` allows only the dedicated modernization operation to create the modernization ledger transition.

- [ ] **Step 2: Run targeted tests and verify RED**

Run: `python -m pytest tests/media/test_auto_merge_dispatch_contract.py tests/media/test_operation_path_policy.py -q`

Expected: FAIL on missing policies/workflow branches.

- [ ] **Step 3: Add declarative policy and operation-specific path checks**

Keep the wildcard grammar unchanged. Add only the narrow new entries and selected-work shape validation. Receipt-only `no_change` output must still pass the declared allowed-path policy.

- [ ] **Step 4: Harden workflows**

In trusted `main` workflow code:
- provider dispatch recognizes `refresh_work_metadata`;
- before merging `refresh_work_metadata`, compare the current-main raw work SHA-256 with receipt `details.expected_work_digest`;
- include `record_reassessment_modernization` in the pilot-ledger operation allowlist;
- accept `no_change` only when `OP_KIND` is `refresh_work_metadata` or `set_semantic_fingerprint`, the trusted receipt binds to the operation, and exact-head Media Check succeeded;
- retain exact-head Media Check before every merge.

- [ ] **Step 5: Run targeted tests and verify GREEN**

Run: `python -m pytest tests/media/test_auto_merge_dispatch_contract.py tests/media/test_operation_path_policy.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

Commit message: `security: trust reassessment modernization writes`

---

### Task 4: Add resumable modernization context

**Files:**
- Modify: `media/service/reassessment.py`
- Modify: `media/cli.py`
- Create: `tests/media/test_reassessment_modernization_context.py`

**Interfaces:**
- Produces: `build_reassessment_modernization_context(repo: CanonicalRepository, document: Mapping[str, Any], *, include_blocked: bool = False, limit: int = 20) -> dict[str, Any]`.
- CLI: `python -m media.cli reassessment-modernization-context --limit N [--include-blocked] --format json`.
- Output includes `pilot_id`, current `ledger_digest`, current `vocabulary_digest`, and factual/operational cards only.

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

Run: `python -m pytest tests/media/test_reassessment_modernization_context.py -q`

Expected: FAIL because the context/CLI does not exist.

- [ ] **Step 3: Implement digest helpers and context builder**

Reuse `file_sha256`. Compute work digest from the actual canonical YAML bytes and vocabulary digest from exact `media/vocabulary.yaml` bytes so later write guards refer to authoritative content.

- [ ] **Step 4: Add CLI surface**

Require an active ledger just like `reassessment-context`. This is read-only and must not enter `MediaCommand`.

- [ ] **Step 5: Verify GREEN**

Run:
- `python -m pytest tests/media/test_reassessment_modernization_context.py -q`
- `python -m pytest tests/media/test_cli.py -q`

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
- Modify: existing reassessment transition/snapshot validation tests

**Interfaces:**
- Produces: `plan_record_reassessment_modernization(repo: YamlRepository, command: RecordReassessmentModernizationCommand, *, now: datetime | None = None) -> MutationPlan`.
- The planner reads current ledger, canonical work bytes, current vocabulary bytes, and referenced `.media/operations/<id>.json` receipts through repository-relative paths.
- Receipt details include `work_id`, `outcome`, `expected_ledger_digest`, `expected_work_digest`, and the resulting modernization record.
- Metadata and semantic evidence receipts may each have `status: applied` or trusted `status: no_change`.

- [ ] **Step 1: Write failing mutation tests**

For `completed`, assert rejection when:
- work is not human `reviewed`;
- ledger/work digest is stale;
- metadata receipt is missing, has a status other than `applied|no_change`, has the wrong operation/work, lacks binding details, or predates human review;
- semantic receipt is missing, has a status other than `applied|no_change`, refers to the wrong work, or occurs before metadata receipt;
- vocabulary digest is stale;
- modernization is already completed.

Also assert successful completion when metadata and/or semantic receipts are authoritative `no_change` receipts for the correct work and in the correct order.

For `blocked`, assert:
- only controlled blocker codes are accepted;
- canonical work is untouched;
- absent→blocked and blocked→completed work;
- completed cannot be rewritten;
- human status/outcome/exposure/reviewed timestamp never change.

- [ ] **Step 2: Run targeted tests and verify RED**

Run: `python -m pytest tests/media/test_reassessment_modernization_mutate.py -q`

Expected: FAIL because planner/validation does not exist.

- [ ] **Step 3: Implement planner and transaction dispatch**

Write only `media/pilots/legacy-reassessment-primary.json` through `json_documents`. Preserve all existing human lifecycle fields byte-for-value. Use current receipt timestamps/operation/details rather than trusting caller claims; accept only the two allowed successful/check statuses defined by the spec.

- [ ] **Step 4: Extend snapshot validator**

Validate modernization object shape and invariants independently in normal repository validation:
- only reviewed items may have it;
- controlled statuses/blockers;
- completed provenance fields/digests are present;
- blocked contains no fake completion ids;
- completed is internally terminal.

- [ ] **Step 5: Extend base→head transition validator**

Permit only absent→blocked, absent→completed, blocked→completed. Reject deletion, completed rewrite, blocker rewrite loops, or any simultaneous mutation to protected human reassessment fields.

- [ ] **Step 6: Verify GREEN**

Run targeted modernization tests plus existing reassessment validation/transition test files.

Expected: PASS.

- [ ] **Step 7: Commit**

Commit message: `feat: track reassessment modernization outcomes`

---

### Task 6: Update living agent/runbook contracts for end-to-end orchestration

**Files:**
- Modify: `media/AGENTS.md`
- Modify: `media/START_PROMPT.md`
- Modify: `docs/runbooks/media-legacy-reassessment.md`
- Modify: `docs/status/current.md`
- Modify: `docs/reference/media-commands.md`
- Modify: `docs/reference/invariants.md` if needed for the new stale-work/terminal-state invariant
- Modify: `tests/media/test_agent_ux_contract.py`
- Modify: `tests/media/test_reassessment_docs_contract.py`

**Interfaces:**
- Startup ordering: recover repository state → drain ordinary due modernization for already-reviewed items → resume existing human session or reserve next batch.
- Per-item ordering after a fresh answer: primary completion → optional partner follow-up → metadata refresh → independent semantic refresh → modernization marker → next human card.
- If deterministic modernization is blocked, record blocker, do not reopen human reassessment, and continue the session when safe.

- [ ] **Step 1: Write failing executable docs tests**

Pin these phrases/semantics rather than prose layout:
- human reassessment and work modernization are separate layers but one user-facing flow;
- no repeat human prompt for modernization retry;
- viewer feedback cannot be copied directly into work semantics;
- due modernization is recovered before new human batch reservation;
- next card normally waits for modernization completion/block recording for the previous reviewed item;
- trusted `no_change` metadata/semantic checks count as successful modernization evidence;
- taste reanalysis cadence remains 15/end-main/manual, not per modernization.

- [ ] **Step 2: Run docs tests and verify RED**

Run: `python -m pytest tests/media/test_agent_ux_contract.py tests/media/test_reassessment_docs_contract.py -q`

Expected: FAIL on the old “reassessment is not semantic enrichment” terminal-flow wording.

- [ ] **Step 3: Update living docs**

Keep the evidence-separation statement, but replace the false implication that reassessment conversation ends after human evidence. Describe modernization as a follow-up, not as mutation inside `complete_reassessment_item`.

- [ ] **Step 4: Verify docs GREEN**

Run the two docs test files again.

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `docs: make reassessment modernization end to end`

---

### Task 7: Full verification, guarded integration, and live backfill

**Files:**
- No new architecture files unless verification exposes a concrete defect.
- Runtime data after merge: operation receipts, the already-reviewed work files only when metadata/semantics actually change, and modernization fields in `media/pilots/legacy-reassessment-primary.json`.

**Interfaces:**
- Uses `reassessment-modernization-context` as the source of truth for due items.
- Uses normal operation branches/requests for `refresh_work_metadata`, `set_semantic_fingerprint`, and `record_reassessment_modernization`.
- `applied` and trusted `no_change` metadata/semantic receipts are both acceptable authoritative steps.

- [ ] **Step 1: Run the full pre-merge gate**

Run:
- `python -m pytest -q`
- `python -m media.tools.validate .`
- `python -m media.cli rebuild --check`
- `python -m media.cli web-export --output /tmp/media-web-manifest.json --format json`
- `python -m media.cli doctor --format json`

Expected: all green/ok.

- [ ] **Step 2: Review exact diff and trust scope**

Confirm no migration changed existing viewer feedback, no vocabulary change exists, and no pilot item changed human terminal fields.

- [ ] **Step 3: Merge implementation only after exact-head CI is green**

Use the repository’s normal guarded development PR process. Do not mix live data backfill into the architecture PR.

- [ ] **Step 4: Re-read current `main` and modernization context**

Do not hard-code the due set. Verify that already-reviewed items such as `gattaca-1997` and `grand-budapest-hotel-2014` appear due if still unmodernized.

- [ ] **Step 5: Modernize each due reviewed item sequentially**

For each due item:
1. apply `refresh_work_metadata` with the fresh current work digest;
2. wait until its `applied` or trusted `no_change` receipt is authoritative on `main`;
3. re-read canonical work and current vocabulary;
4. derive the current semantic fingerprint independently of viewer sentiment;
5. apply `set_semantic_fingerprint` and wait for its `applied` or trusted `no_change` receipt on authoritative `main`;
6. apply `record_reassessment_modernization(outcome=completed)` with fresh ledger/work/vocabulary digests;
7. on a deterministic provider/semantic blocker, record `outcome=blocked` with the controlled code instead of fabricating data.

- [ ] **Step 6: Verify backfill and resume human session**

Run read-only contexts again. Confirm no completed modernization item is due, the existing reassessment session still contains its unresolved human items, and the next human card is not one already reviewed.

- [ ] **Step 7: Final full validation after backfill**

Run validate/rebuild/doctor and verify the exact current-main work cards and ledger markers.
