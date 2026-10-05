# Media Legacy Review Reassessment & Explicit Evidence Backfill Implementation Plan

> **For MrDragon13:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship a resumable, unanchored `primary` legacy-review reassessment pilot that converts historical evidence into fresh explicit evidence exactly once per pilot epoch, with durable anti-loop guarantees, deterministic progress measurement, and no semantic-fingerprint work in this cycle.

**Architecture:** Add a versioned pilot ledger outside canonical media truth; expose a deterministic read model for safe pre-response cards; add three narrow typed operations (`reserve_reassessment_session`, `complete_reassessment_item`, `close_reassessment_session`) that serialize on an exact ledger digest; reuse the existing feedback mutation primitives inside atomic completion; enforce ledger snapshot invariants in normal validation and base→head monotonicity in exact-head CI; activate the pilot only after the trusted foundation is merged.

**Tech Stack:** Python 3.12, dataclasses, JSON Schema, YAML/JSON repository files, pytest, GitHub Actions, existing deterministic media transaction/path-policy pipeline.

---

## Delivery shape

Implement this as **two manually reviewed PRs**, not one large activation change.

- **PR A — Foundation & Trust:** command contracts, JSON mutation support, reassessment service/read model, pilot planners, snapshot validator, transition validator, path-policy/workflow changes, tests, and documentation. **Do not create `media/pilots/legacy-reassessment-primary.json` yet.**
- **PR B — Pilot Activation:** generate the frozen `primary-legacy-v1` ledger from Stage A revision `35afaca898eae6937066f230906b41af0e1f6690`, verify the Stage A audit digest is unchanged by the ledger, update current status/runbook with the actual cohort summary, and merge manually.

This sequencing matters: the first mutable pilot ledger must not exist on `main` until the trusted validators and auto-merge restrictions that protect it already exist on `main`.

### Execution prerequisites

1. Merge the approved design/spec + this plan as a documentation-only change.
2. Start PR A from the resulting `main` in an isolated worktree/feature branch.
3. Use TDD for every behavior change: failing targeted test → minimal implementation → targeted green test → commit.
4. Do not begin PR B until PR A is merged and its exact merge SHA has passed the full developer gate.

---

# PR A — Foundation & Trust

## Task 1: Extend the mutation plan so ledger-only JSON operations are first-class

**Why first:** current `MutationPlan.documents` are always emitted through `dump_yaml`, and `execute_command()` treats `changed_entities` as a proxy for “anything changed”. A ledger-only JSON operation would otherwise serialize incorrectly or be reported as `no_change`.

**Files:**
- Modify: `media/domain/changeset.py`
- Modify: `media/service/transaction.py`
- Test: `tests/media/test_transaction.py`

**Step 1 — Write failing tests**

Add tests proving:

1. a plan with no `changed_entities` but one JSON document is `planned/applied`, not `no_change`;
2. JSON documents are written as deterministic UTF-8 JSON with sorted keys and a trailing newline, not YAML;
3. existing entity mutations and genuine no-op plans retain current behavior.

Use a minimal fake planner/command seam if needed; do not introduce reassessment semantics in this task.

**Step 2 — Run the targeted test**

```bash
python -m pytest -q tests/media/test_transaction.py
```

Expected: new tests fail because `MutationPlan` has no JSON-document channel and `changed_entities` still controls application.

**Step 3 — Implement the minimal transaction refactor**

In `media/domain/changeset.py`:

- add `json_documents: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)`;
- add a pure `has_changes` property returning true when `documents`, `json_documents`, or `jsonl_appends` is non-empty.

In `media/service/transaction.py`:

- include `json_documents` in preview paths;
- serialize them with a small deterministic JSON writer (`ensure_ascii=False`, `sort_keys=True`, `indent=2`, trailing newline);
- use `plan.has_changes` rather than `plan.changed_entities` for validation/write/status decisions;
- keep rebuild behavior controlled by existing `rebuild_index` / `rebuild_profile_targets` fields;
- include JSON paths in changed-path calculation and receipt output.

Do **not** change path-policy semantics here.

**Step 4 — Run targeted tests**

```bash
python -m pytest -q tests/media/test_transaction.py
```

Expected: PASS.

**Step 5 — Commit**

```bash
git add media/domain/changeset.py media/service/transaction.py tests/media/test_transaction.py
git commit -m "refactor: support json-only media mutations"
```

---

## Task 2: Define the three typed pilot command contracts

**Files:**
- Create: `media/commands/schemas/reserve_reassessment_session.schema.json`
- Create: `media/commands/schemas/complete_reassessment_item.schema.json`
- Create: `media/commands/schemas/close_reassessment_session.schema.json`
- Modify: `media/commands/schema.py`
- Modify: `media/domain/commands.py`
- Test: `tests/media/test_command_contracts.py`

**Contract decisions to encode, not defer:**

### `reserve_reassessment_session`

Required fields:

- `schema_version: 1`
- `operation_id` UUID
- `operation: "reserve_reassessment_session"`
- `pilot_id: "primary-legacy-v1"`
- `session_id` UUID
- `work_ids`: unique array, 1–5 canonical IDs
- `expected_ledger_digest`: `sha256:<64 hex>`

### `complete_reassessment_item`

Required fields:

- `schema_version: 1`
- `operation_id` UUID
- `operation: "complete_reassessment_item"`
- `pilot_id: "primary-legacy-v1"`
- `session_id` UUID
- `work_id` canonical ID (ID only; no fuzzy title/provider resolution)
- `expected_ledger_digest`
- `outcome: changed | confirmed_unchanged | deferred`

For reviewed outcomes require `historical_exposure`:

```json
{
  "timing": "none | before_initial_response | after_initial_response",
  "before_finalization": true
}
```

For `changed`, allow one narrow `feedback_edit` object with optional `set` / `clear` over only `viewing`, `rating`, `reaction`, `feedback`; target is implicitly `primary`; **do not permit `purge`**.

For `confirmed_unchanged` and `deferred`, forbid `feedback_edit`.

For `deferred`, forbid `historical_exposure` because there is no finalized reassessment evidence.

### `close_reassessment_session`

Required fields:

- `schema_version: 1`
- `operation_id` UUID
- `operation: "close_reassessment_session"`
- `pilot_id: "primary-legacy-v1"`
- `session_id` UUID
- `expected_ledger_digest`
- optional `scheduled_reanalysis_operation_id` UUID

**Step 1 — Write failing schema/parser tests**

Cover valid examples and failures for:

- non-UUID session/operation IDs;
- duplicate/empty/>5 reserve work IDs;
- malformed ledger digest;
- `deferred` carrying feedback changes;
- `confirmed_unchanged` carrying feedback changes;
- `changed` without an edit;
- pilot command attempting a non-`primary-legacy-v1` pilot id;
- feedback edit attempting `purge` or arbitrary target.

**Step 2 — Run**

```bash
python -m pytest -q tests/media/test_command_contracts.py
```

Expected: FAIL for new operations.

**Step 3 — Add dataclasses/parser branches**

Use explicit dataclasses in `media/domain/commands.py`; add them to the mutable command union later in Task 6. Keep schema parsing boring and typed; no ledger reads in command parsing.

**Step 4 — Run targeted tests**

```bash
python -m pytest -q tests/media/test_command_contracts.py
```

Expected: PASS.

**Step 5 — Commit**

```bash
git add media/commands/schemas media/commands/schema.py media/domain/commands.py tests/media/test_command_contracts.py
git commit -m "feat: define reassessment pilot commands"
```

---

## Task 3: Add the pilot ledger schema, deterministic digests, and frozen cohort builder

**Files:**
- Create: `media/schemas/reassessment-pilot.schema.json`
- Create: `media/service/reassessment.py`
- Create: `media/tools/reassessment.py`
- Test: `tests/media/test_reassessment_pilot.py`

**Step 1 — Write failing tests for pure helpers**

Test:

- ledger digest is `sha256` of exact deterministic ledger bytes and changes after any ledger mutation;
- relevant feedback-state digest is stable across mapping key order and covers only `primary` viewing/rating/reaction/feedback state used for concurrency checks;
- a whole-work-file SHA-256 helper is deterministic and can be reproduced from raw repository bytes for privileged pre-merge defense-in-depth;
- cohort membership includes `watched`, `partial`, `dropped`, `forgotten` and excludes `unwatched` regardless of summary text;
- frozen strata match the approved boundaries;
- `order_key == sha256(pilot_id + "\0" + work_id)`;
- order inside each stratum is by hash key then work id;
- final queue is deterministic stratified round-robin;
- all initial lifecycle items are `pending`;
- frozen cohort stores `viewing_status`, `stratum`, `order_key`, `order_rank`, `pre_pilot_feedback_digest`.

**Step 2 — Run**

```bash
python -m pytest -q tests/media/test_reassessment_pilot.py
```

Expected: FAIL.

**Step 3 — Implement pure service functions**

In `media/service/reassessment.py`, keep filesystem I/O small and logic pure. Recommended seams:

```python
PILOT_ID = "primary-legacy-v1"
LEDGER_REL_PATH = "media/pilots/legacy-reassessment-primary.json"
ALLOWED_COHORT_VIEWING = {"watched", "partial", "dropped", "forgotten"}

def ledger_bytes(document: Mapping[str, Any]) -> bytes: ...
def ledger_digest_bytes(payload: bytes) -> str: ...
def file_sha256(payload: bytes) -> str: ...
def feedback_state_digest(signal: Mapping[str, Any] | None) -> str: ...
def frozen_stratum(signal: Mapping[str, Any]) -> str: ...
def frozen_order_key(pilot_id: str, work_id: str) -> str: ...
def build_frozen_cohort(repo: YamlRepository, *, pilot_id: str) -> dict[str, Any]: ...
def build_initial_ledger(...baseline refs...) -> dict[str, Any]: ...
```

The builder must not inspect generated index/profile as truth.

**Step 4 — Add developer-only initializer/summary CLI**

`media/tools/reassessment.py` should support at least:

```bash
python -m media.tools.reassessment init \
  --repo-root <source-repo> \
  --output <ledger.json> \
  --base-revision <sha> \
  --baseline-path media/baselines/intelligence-stage-a.json

python -m media.tools.reassessment summary <ledger.json>
```

The initializer reads canonical works from `--repo-root`, copies the baseline canonical-input digest/schema provenance from the named baseline, writes deterministic JSON to `--output`, and refuses to overwrite an existing output unless an explicit developer-only flag is supplied. `summary` reports cohort/stratum/status counts without mutating anything.

Do not expose pilot initialization as an auto-merge typed operation.

**Step 5 — Run tests**

```bash
python -m pytest -q tests/media/test_reassessment_pilot.py
```

Expected: PASS.

**Step 6 — Commit**

```bash
git add media/schemas/reassessment-pilot.schema.json media/service/reassessment.py media/tools/reassessment.py tests/media/test_reassessment_pilot.py
git commit -m "feat: build deterministic reassessment cohort"
```

---

## Task 4: Add snapshot validation to normal repository validation

**Files:**
- Modify: `media/tools/validate.py`
- Create: `media/service/reassessment_validation.py`
- Test: `tests/media/test_validator.py`
- Test: `tests/media/test_reassessment_pilot.py`

**Step 1 — Write failing tests**

When ledger exists, snapshot validation must reject:

- malformed schema;
- empty or duplicate frozen cohort IDs;
- frozen work ID that no longer resolves to a canonical work;
- frozen `viewing_status` outside the allowed membership statuses;
- missing/inconsistent stratum/order metadata;
- reviewed item missing outcome, `historical_exposure`, `reviewed_at`, or operation provenance;
- `pilot_status=completed` while pending/resumable in-progress main-pass items remain;
- closed session with an item still reserved to that session as `in_progress`;
- non-monotonic cumulative session counters across the append-only session sequence.

Also prove what must **not** be rejected:

- current canonical viewing status may differ from the frozen cohort’s historical `viewing_status` after a valid user correction;
- a later current total may exceed an earlier closed-session snapshot total;
- repository without a pilot ledger (PR A state) remains valid.

**Step 2 — Run**

```bash
python -m pytest -q tests/media/test_validator.py tests/media/test_reassessment_pilot.py
```

Expected: FAIL.

**Step 3 — Implement validation**

In `validate_repository()`:

- if `media/pilots/legacy-reassessment-primary.json` exists, validate against `reassessment-pilot.schema.json`;
- then run semantic snapshot checks using canonical `works` already loaded by validator;
- do not compare current mutable feedback/viewing values to frozen pre-pilot values.

**Step 4 — Run targeted tests**

```bash
python -m pytest -q tests/media/test_validator.py tests/media/test_reassessment_pilot.py
```

Expected: PASS.

**Step 5 — Commit**

```bash
git add media/tools/validate.py media/service/reassessment_validation.py tests/media/test_validator.py tests/media/test_reassessment_pilot.py
git commit -m "feat: validate reassessment pilot snapshots"
```

---

## Task 5: Build the unanchored read model and explicit history read path

**Files:**
- Modify: `media/service/reassessment.py`
- Modify: `media/cli.py`
- Test: `tests/media/test_reassessment_pilot.py`
- Test: `tests/media/test_tooling_e2e.py`

**Step 1 — Write failing tests**

Add read-model tests proving the default reassessment context contains only safe first-response fields:

- `work_id`, title, year;
- factual saved synopsis/overview when available;
- optional factual director/cast identity context;
- session/queue metadata required by the agent.

It must **not** expose current/old:

- numeric rating;
- reaction;
- feedback summary/signals;
- semantic fingerprint terms;
- inferred taste hypotheses.

Add a distinct explicit history lookup that returns old viewer evidence only when the caller asks for it after the first response (or the user explicitly requests it).

**Step 2 — Run**

```bash
python -m pytest -q tests/media/test_reassessment_pilot.py tests/media/test_tooling_e2e.py
```

Expected: FAIL.

**Step 3 — Implement read-only CLI surfaces**

Add commands such as:

```bash
python -m media.cli reassessment-context --limit 5 --format json
python -m media.cli reassessment-history <work_id> --format json
```

`reassessment-context` should return:

- current ledger digest;
- open session/resume information when present;
- next safe cards in lifecycle/frozen order;
- no historical opinion content in the card payload.

`reassessment-history` is the explicit second-phase surface and resolves by canonical work id only.

The CLI does not generate prose memory-jog adjectives; the agent turns factual synopsis/identity fields into 1–2 neutral sentences according to `media/AGENTS.md`.

**Step 4 — Run targeted tests**

```bash
python -m pytest -q tests/media/test_reassessment_pilot.py tests/media/test_tooling_e2e.py
```

Expected: PASS.

**Step 5 — Commit**

```bash
git add media/service/reassessment.py media/cli.py tests/media/test_reassessment_pilot.py tests/media/test_tooling_e2e.py
git commit -m "feat: expose unanchored reassessment context"
```

---

## Task 6: Implement reserve, complete, and close planners using existing feedback primitives

**Files:**
- Create: `media/service/reassessment_mutate.py`
- Modify: `media/service/transaction.py`
- Modify: `media/domain/commands.py`
- Test: `tests/media/test_reassessment_mutations.py`
- Test: `tests/media/test_transaction.py`

**Step 1 — Write failing planner tests**

### Reserve tests

- ledger digest mismatch fails closed;
- only `pending` (main pass) or explicitly selected `deferred` (deferred pass) items can become `in_progress`;
- reservation creates one open session record with `reserved_work_ids` and timestamps;
- each reserved item stores current `pre_review_feedback_digest` and current `pre_review_work_file_digest` (SHA-256 of raw canonical work file bytes);
- reviewed item cannot be reserved;
- duplicate/open conflicting session reservation fails.

### Complete tests

- requires matching `in_progress` item + session;
- requires current ledger digest;
- requires current feedback-state digest to equal reserved digest;
- `changed` reuses existing feedback edit semantics and history;
- same score with `source: inferred` becomes `source: explicit` and outcome is `changed`;
- `confirmed_unchanged` only succeeds when current canonical evidence is already explicit and creates no fake history;
- completion may mutate at most one canonical work and it must be the reserved work id;
- operation receipt/details preserve reserved work id, expected ledger digest, pre-review feedback digest, and pre-review work-file digest for downstream trusted checks;
- `deferred` changes ledger only;
- reviewed item cannot be completed again.

### Close tests

- requires exact ledger digest;
- all session-reserved items must be `reviewed` or `deferred`;
- computes audit from repository state, not request-provided metrics;
- appends one closed immutable session snapshot;
- advances `scheduled_reanalysis.last_completed` only when a due scheduled operation id is supplied and corresponds to an applied `set_inferred_preferences` receipt for `primary`;
- a manual/user-requested reanalysis does not reset scheduled cadence unless deliberately used as the due scheduled milestone under the close contract;
- close does not mutate works/preferences/generated files itself.

**Step 2 — Run**

```bash
python -m pytest -q tests/media/test_reassessment_mutations.py tests/media/test_transaction.py
```

Expected: FAIL.

**Step 3 — Implement planners**

In `media/service/reassessment_mutate.py`:

- read ledger through one helper;
- compare `expected_ledger_digest` against exact current ledger bytes;
- produce updated ledger through `MutationPlan.json_documents`;
- during reservation compute both relevant-feedback digest and raw work-file SHA-256;
- for `changed`, construct an implicit-`primary` `TargetEdit` and call existing `apply_feedback_edits()` rather than reimplementing history rules;
- set rebuild flags/profile targets exactly as `plan_edit_viewing_feedback()` would for a changed `primary` work;
- for ledger-only outcomes leave `changed_entities=()` while `plan.has_changes` remains true;
- include `expected_ledger_digest`, `session_id`, reserved work id, and pre-review digest fields in trusted operation `details` for downstream verification/observability.

For close, call `collect_intelligence_audit(repo.media_root.parent)` against the transaction’s temporary repository state.

**Step 4 — Integrate dispatcher**

Add the new command types to `MutableCommand` and `_plan()` in `media/service/transaction.py`.

**Step 5 — Run targeted tests**

```bash
python -m pytest -q tests/media/test_reassessment_mutations.py tests/media/test_transaction.py
```

Expected: PASS.

**Step 6 — Commit**

```bash
git add media/service/reassessment_mutate.py media/service/transaction.py media/domain/commands.py tests/media/test_reassessment_mutations.py tests/media/test_transaction.py
git commit -m "feat: implement atomic reassessment pilot mutations"
```

---

## Task 7: Prove audit independence and persistent reanalysis cadence

**Files:**
- Modify: `tests/media/test_intelligence_audit.py`
- Modify: `tests/media/test_reassessment_mutations.py`
- Optional modify: `media/tools/audit_intelligence.py` only if a clarifying constant/helper materially improves the contract; behavior should already be correct.

**Step 1 — Write tests**

- creating/changing only `media/pilots/legacy-reassessment-primary.json` does not change `canonical_input_digest`;
- changing canonical work feedback does change digest;
- close snapshot records current canonical digest and baseline references;
- scheduled due calculation is deterministic from `reviewed_total - last_completed.reviewed_count`;
- explicit user-requested reanalysis does not alter scheduled cadence state;
- final-main-pass reanalysis can be required even if fewer than 15 reviews occurred since the prior milestone.

**Step 2 — Run**

```bash
python -m pytest -q tests/media/test_intelligence_audit.py tests/media/test_reassessment_mutations.py
```

**Step 3 — Make the minimum change if needed**

Prefer a test-only contract if `audit_input_paths()` already excludes `media/pilots/`. Do not add the ledger to canonical audit inputs.

**Step 4 — Commit**

```bash
git add tests/media/test_intelligence_audit.py tests/media/test_reassessment_mutations.py media/tools/audit_intelligence.py
git commit -m "test: lock reassessment audit independence"
```

---

## Task 8: Add path policy entries and operation-specific changed-file guards

**Files:**
- Modify: `media/config/operation_path_policy.json`
- Modify: `media/service/path_policy.py` only if a small reusable operation-specific verifier belongs there; do **not** broaden matcher grammar
- Modify: `media/service/reassessment_validation.py`
- Test: `tests/media/test_path_policy.py`
- Modify: `tests/media/fixtures/operation_path_policy_cases.json`

**Policy entries:**

`reserve_reassessment_session`:

- `media/pilots/legacy-reassessment-primary.json`
- `.media/operations/*.json`

`complete_reassessment_item`:

- `media/pilots/legacy-reassessment-primary.json`
- `media/data/works/*.yaml`
- `media/generated/index.jsonl`
- `media/generated/profiles/*.yaml`
- `.media/operations/*.json`

`close_reassessment_session`:

- `media/pilots/legacy-reassessment-primary.json`
- `.media/operations/*.json`

All three are `auto_merge: true` **only after this PR A is manually reviewed and merged**.

**Step 1 — Write failing tests**

- all pre-existing operations reject the pilot ledger path;
- reserve/close reject work/generated/preferences/vocabulary/schema/workflow paths;
- complete rejects semantic/vocabulary/preferences/schema/workflow paths;
- complete’s operation-specific verifier rejects two changed `media/data/works/*.yaml` paths even though the wildcard individually matches both;
- complete rejects one work path whose stem is not the reserved work id;
- existing Stage A matcher corpus remains unchanged/green.

**Step 2 — Run**

```bash
python -m pytest -q tests/media/test_path_policy.py
```

**Step 3 — Implement minimal guards**

Keep the generic path grammar exact/one-wildcard. Add a pure pilot-specific changed-file check that takes operation details + changed file list and enforces “0 or 1 work, exact reserved id”. Reuse this same pure rule in local/CI tests and, where possible, workflow verification.

**Step 4 — Run**

```bash
python -m pytest -q tests/media/test_path_policy.py
```

**Step 5 — Commit**

```bash
git add media/config/operation_path_policy.json media/service/path_policy.py media/service/reassessment_validation.py tests/media/test_path_policy.py tests/media/fixtures/operation_path_policy_cases.json
git commit -m "security: scope reassessment pilot paths"
```

---

## Task 9: Add independent base→head ledger transition validation

**Files:**
- Create: `media/tools/validate_reassessment_transition.py`
- Modify: `media/service/reassessment_validation.py`
- Test: `tests/media/test_reassessment_transition.py`

**Step 1 — Write failing pure transition tests**

Reject:

- changes to pilot id/base revision/baseline refs/frozen cohort or frozen stratum/order/pre-pilot digests;
- `reviewed` → any other state;
- mutation of terminal outcome, historical exposure, completion timestamp or completion provenance;
- deletion/mutation/reorder of a previously closed session snapshot;
- illegal lifecycle transitions for the named operation;
- scheduled-reanalysis history moving backwards.

Allow only operation-specific transitions:

- reserve: eligible `pending|deferred` → `in_progress`, append/open one session;
- complete: one matching `in_progress` → `reviewed|deferred`, update only its open-session progress metadata;
- close: no item lifecycle changes; close one fully resolved session, append one snapshot, optionally advance scheduled reanalysis monotonically.

**Step 2 — Run**

```bash
python -m pytest -q tests/media/test_reassessment_transition.py
```

**Step 3 — Implement pure validator + CLI wrapper**

CLI shape:

```bash
python -m media.tools.validate_reassessment_transition \
  --base /tmp/base-ledger.json \
  --head media/pilots/legacy-reassessment-primary.json \
  --operation complete_reassessment_item \
  --operation-receipt .media/operations/<id>.json
```

Return nonzero with concise machine-readable/error output on violation.

**Step 4 — Run targeted tests**

```bash
python -m pytest -q tests/media/test_reassessment_transition.py
```

**Step 5 — Commit**

```bash
git add media/tools/validate_reassessment_transition.py media/service/reassessment_validation.py tests/media/test_reassessment_transition.py
git commit -m "security: validate monotonic reassessment transitions"
```

---

## Task 10: Wire trusted workflows for pilot staging, exact-head transition checks, and serialized auto-merge

**Files:**
- Modify: `.github/workflows/media-command.yml`
- Modify: `.github/workflows/media-check.yml`
- Modify: `.github/workflows/media-auto-merge.yml`
- Test: `tests/media/test_workflows.py`
- Test: `tests/media/test_auto_merge_dispatch_contract.py`

**Security principle:** PR A is manual developer review. After it lands, pilot operation PRs may only carry transient request/data outputs. Transition/check code must come from trusted `main` through the existing command replay model; privileged auto-merge must not execute arbitrary PR-head code with a write-capable token.

**Step 1 — Write failing workflow-contract tests**

Require:

- Media Command stages `media/pilots` when present;
- command workflow captures the exact `origin/main` SHA after replay and dispatches Media Check with both `expected_sha` and `base_sha`;
- Media Check fetches enough history/base state to materialize the base ledger and runs transition validation when the ledger changed;
- missing base ledger is allowed only for manual activation/developer PR, never for an auto-merge pilot operation;
- auto-merge recognizes the new operations only via trusted-main path policy;
- before merging any pilot op, privileged auto-merge re-reads current-main ledger and verifies its digest equals the receipt’s trusted `details.expected_ledger_digest`; stale pilot PR fails closed even if Git could technically merge it;
- before merging `complete_reassessment_item`, privileged auto-merge additionally re-reads the current-main reserved work file and verifies its SHA-256 equals receipt `details.pre_review_work_file_digest`; a concurrent ordinary edit/metadata change after planning therefore fails closed rather than relying on Git conflict behavior;
- complete operation PR has at most one changed work and the work matches receipt/reserved id;
- reserve/close PRs have no work path;
- unknown/malformed pilot receipt fields fail closed.

**Step 2 — Run**

```bash
python -m pytest -q tests/media/test_workflows.py tests/media/test_auto_merge_dispatch_contract.py
```

Expected: FAIL.

**Step 3 — Modify Media Command**

- include `media/pilots` in staged operation outputs;
- record/pass the replayed current-main SHA to the exact-head check;
- ensure the new operations are provider-independent;
- keep “one transient request before execution” and architecture-path rejection unchanged.

**Step 4 — Modify Media Check**

Add `base_sha` input. For exact-head operation checks where the pilot ledger changed:

1. materialize trusted/base ledger from `base_sha`;
2. identify the single applied operation receipt for the exact head;
3. run the transition validator against base → head;
4. still run the full existing pytest/validate/rebuild/doctor gate.

The check token remains read-only.

**Step 5 — Harden privileged auto-merge**

For the three pilot operation kinds, before merge:

- fetch trusted current-main ledger bytes via GitHub Contents API;
- compute the same ledger SHA-256 algorithm;
- compare with `details.expected_ledger_digest` in the bot-generated operation receipt;
- for `complete_reassessment_item`, fetch the reserved current-main work file content and compare raw-file SHA-256 with `details.pre_review_work_file_digest`;
- enforce pilot-specific changed-file cardinality/id checks;
- fail closed if current main moved in either relevant ledger state or reserved work state since planning.

This second work-file guard is intentionally stricter than the planner’s relevant-feedback digest: any concurrent canonical edit to that work forces the reassessment completion to be replayed against fresh state.

Do not add a generic shell pattern DSL or execute PR-head Python in the privileged workflow.

**Step 6 — Optional Pages optimization decision**

Do **not** block PR A on this. If tests show a safe simple trusted-policy distinction is easy, skip Pages dispatch for reserve/close ledger-only merges. Otherwise leave current publish behavior and document the extra runs as accepted pilot cost.

**Step 7 — Run targeted tests**

```bash
python -m pytest -q tests/media/test_workflows.py tests/media/test_auto_merge_dispatch_contract.py tests/media/test_path_policy.py
```

**Step 8 — Commit**

```bash
git add .github/workflows/media-command.yml .github/workflows/media-check.yml .github/workflows/media-auto-merge.yml tests/media/test_workflows.py tests/media/test_auto_merge_dispatch_contract.py
git commit -m "security: gate reassessment pilot auto merge"
```

---

## Task 11: Update the agent/runtime documentation and executable documentation contracts

**Files:**
- Modify: `media/AGENTS.md`
- Modify: `media/START_PROMPT.md`
- Modify: `docs/architecture/intelligence.md`
- Modify: `docs/architecture/write-pipeline.md`
- Modify: `docs/reference/media-commands.md`
- Modify: `docs/reference/invariants.md` if present/relevant
- Modify: `docs/reference/repository-layout.md` if present/relevant
- Create: `docs/runbooks/media-legacy-reassessment.md`
- Modify: `docs/status/current.md`
- Test: `tests/media/test_agent_ux_contract.py`
- Test: `tests/media/test_docs.py`
- Test: `tests/media/test_documentation_system.py`

**Content that must be explicit:**

- reassessment starts with a neutral factual memory jog and does not show old rating/reaction/feedback before the first response unless the user asks;
- semantic fingerprint work is out of scope;
- reserve must be durable before a canonical completion write;
- all pilot writes serialize on current ledger digest;
- `confirmed_unchanged` is a valid terminal result; identical inferred score still changes provenance to explicit;
- default session size 5; scheduled hypothesis reanalysis every 15 reviewed works and at end of main pass;
- generated profiles/affinities are expected to drift as direct evidence replaces inferred evidence;
- progress is compared to frozen Stage A baseline, not previous generated profile;
- deferred pass happens after main pending pass;
- pilot ledger is operational provenance, not taste truth;
- runtime user experience hides Git/PR plumbing.

`docs/status/current.md` in PR A should say **foundation implemented / pilot not activated until ledger activation PR lands**.

**Step 1 — Add/adjust docs tests first**

Lock critical phrases/links/operation names so docs cannot silently drift from runtime contracts.

**Step 2 — Run**

```bash
python -m pytest -q tests/media/test_agent_ux_contract.py tests/media/test_docs.py tests/media/test_documentation_system.py
```

**Step 3 — Update docs**

Keep architecture docs normative and the runbook operational. Do not copy the 800+ line design spec into user-facing docs.

**Step 4 — Run docs tests again**

```bash
python -m pytest -q tests/media/test_agent_ux_contract.py tests/media/test_docs.py tests/media/test_documentation_system.py
```

**Step 5 — Commit**

```bash
git add media/AGENTS.md media/START_PROMPT.md docs tests/media/test_agent_ux_contract.py tests/media/test_docs.py tests/media/test_documentation_system.py
git commit -m "docs: document legacy reassessment pilot"
```

---

## Task 12: PR A full verification and manual security review

**Step 1 — Run focused pilot suite**

```bash
python -m pytest -q \
  tests/media/test_reassessment_pilot.py \
  tests/media/test_reassessment_mutations.py \
  tests/media/test_reassessment_transition.py \
  tests/media/test_command_contracts.py \
  tests/media/test_transaction.py \
  tests/media/test_path_policy.py \
  tests/media/test_workflows.py \
  tests/media/test_auto_merge_dispatch_contract.py \
  tests/media/test_intelligence_audit.py
```

**Step 2 — Run full developer gate**

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Expected: all green while **no pilot ledger exists yet**.

**Step 3 — Verify security diff manually**

Check:

```bash
git diff main...HEAD -- \
  media/config/operation_path_policy.json \
  media/service/path_policy.py \
  media/service/reassessment_validation.py \
  .github/workflows/media-command.yml \
  .github/workflows/media-check.yml \
  .github/workflows/media-auto-merge.yml
```

Confirm:

- no new privileged trigger model;
- no PR-head executable code used with write-capable token;
- new auto-merge paths are the exact ledger + existing work/generated/receipt classes only;
- stale expected ledger state and stale reserved-work state both fail before privileged merge.

**Step 4 — Request code review**

Use `superpowers:requesting-code-review` before declaring PR A ready.

**Step 5 — Merge PR A manually**

Do not activate a ledger in this PR. Record the exact PR A merge SHA; PR B must branch from it.

---

# PR B — Pilot Activation

## Task 13: Generate the frozen Stage A ledger from the exact approved base revision

**Files:**
- Create: `media/pilots/legacy-reassessment-primary.json`
- Modify: `docs/status/current.md`
- Modify: `docs/runbooks/media-legacy-reassessment.md`
- Test: existing validator/audit tests only; no new runtime code expected.

**Why a separate PR:** first ledger creation cannot be protected by a base→head ledger transition because no base ledger exists. It is therefore a manual developer activation change after PR A’s validators are trusted on `main`.

**Step 1 — Materialize Stage A data at the frozen revision**

From the PR B worktree, create a temporary data worktree at the approved base:

```bash
git worktree add /tmp/chatgpt-lib-stage-a 35afaca898eae6937066f230906b41af0e1f6690
```

Run the **new PR A initializer code** from the current worktree against the old data tree:

```bash
PYTHONPATH="$PWD" python -m media.tools.reassessment init \
  --repo-root /tmp/chatgpt-lib-stage-a \
  --output /tmp/legacy-reassessment-primary.json \
  --base-revision 35afaca898eae6937066f230906b41af0e1f6690 \
  --baseline-path media/baselines/intelligence-stage-a.json
```

Copy the deterministic result:

```bash
mkdir -p media/pilots
cp /tmp/legacy-reassessment-primary.json media/pilots/legacy-reassessment-primary.json
```

Do **not** regenerate the cohort from current mutable `main` data.

**Step 2 — Inspect the cohort before commit**

```bash
python -m media.tools.reassessment summary media/pilots/legacy-reassessment-primary.json
```

Verify:

- every item came from `watched|partial|dropped|forgotten` at Stage A revision;
- no `unwatched` work exists in the cohort;
- expected approximate size is around the known Stage A viewed set (~55 works, subject to exact canonical calculation);
- strata/order ranks are complete and deterministic;
- all lifecycle states are initially `pending`;
- sessions empty;
- scheduled reanalysis state empty;
- baseline revision/digest exactly match the approved spec.

Do not hard-code “55” in schema/tests unless the generated Stage A data proves exactly 55; the frozen ledger itself becomes authoritative for cohort size.

**Step 3 — Prove the ledger does not perturb Stage A intelligence digest**

Run:

```bash
python -m media.tools.audit_intelligence . --format json
```

The expected canonical input digest must remain:

`sha256:98e9dc4521e69ee5273e302fc40cc1e5fc3d53b119e2c7637475ac45cce43fbf`

Baseline intelligence metrics should remain unchanged because `media/pilots/` is outside audit input inventory.

**Step 4 — Validate the activated snapshot**

```bash
python -m media.tools.validate .
python -m media.cli reassessment-context --limit 5 --format json
```

Inspect the first cards: they must contain neutral factual context and no old rating/reaction/feedback/semantic terms.

**Step 5 — Update activation docs**

In `docs/status/current.md` change pilot state from “foundation ready / not activated” to “pilot activated”. In the runbook record:

- actual frozen cohort size;
- stratum counts;
- Stage A baseline revision/digest;
- how to start session 1;
- reminder that first response is unanchored.

**Step 6 — Run full gate**

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

**Step 7 — Commit**

```bash
git add media/pilots/legacy-reassessment-primary.json docs/status/current.md docs/runbooks/media-legacy-reassessment.md
git commit -m "data: activate primary legacy reassessment pilot"
```

**Step 8 — Request review and merge manually**

Activation PR is intentionally not a normal operation PR. Review the generated frozen cohort/ordering, audit digest, and documentation before merging.

---

# Post-activation smoke test (no user evidence mutation yet)

## Task 14: Prove the runtime path is ready without consuming a reassessment item

After PR B merges:

1. Read the first batch:

```bash
python -m media.cli reassessment-context --limit 5 --format json
```

2. Construct a `reserve_reassessment_session` request for the returned ordered work IDs and current `ledger_digest`.
3. Use `--dry-run` locally first:

```bash
python -m media.cli apply-command /tmp/reserve-session.json --dry-run --format json
```

4. Confirm planned data paths are only the pilot ledger (plus the operation receipt during real execution).
5. **Do not submit/merge the real reserve request until the user is actually starting the first reassessment session.** Reservation changes durable lifecycle state and should correspond to a real session.

---

# First live pilot session acceptance checklist

When the user explicitly starts the pilot, the first 5-work session should satisfy all of the following:

1. reserve operation merges before the first completion write;
2. first card contains no old opinion data and uses neutral factual wording;
3. if historical feedback is revealed, `historical_exposure` truthfully records timing/finalization;
4. each completion write waits for the prior pilot ledger write to reach authoritative `main`;
5. same-score inferred ratings become explicit and count as `changed`;
6. already-explicit identical evidence can end as `confirmed_unchanged` without fake history;
7. `deferred` changes no canonical work;
8. close operation only runs after all five reserved items are resolved;
9. close snapshot shows Stage A audit progress and ledger-only state remains outside canonical digest;
10. no semantic fingerprint is written;
11. no scheduled hypothesis reanalysis occurs before 15 newly reviewed works unless the main pass ends earlier or the user explicitly requests a manual reanalysis.

---

# Verification before declaring the implementation complete

Use `superpowers:verification-before-completion` and rerun:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
python -m media.tools.audit_intelligence . --format json
```

Then verify repository/GitHub state:

- PR A and PR B both merged manually with green checks;
- `main` contains the exact approved ledger path;
- current ledger passes snapshot validation;
- policy from `main` contains exactly the three pilot operation entries intended;
- no existing operation gained access to `media/pilots/`;
- first live session has not been accidentally reserved during smoke testing;
- Stage A baseline file remains unchanged;
- semantic fingerprints/vocabulary remain untouched by this cycle.

Only after these checks is the pilot **ready for live reassessment**. The pilot itself is complete later, when the frozen cohort/deferred-pass stop conditions from the design spec are satisfied; that is operational usage, not part of the foundation implementation PRs.
