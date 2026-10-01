# Media Tooling & Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub-native typed tooling layer that lets ChatGPT, a local CLI, and future clients query and safely mutate the v4 media library through one deterministic Python service layer.

**Architecture:** Keep Git/YAML canonical. Put command parsing, identity resolution, retrieval, mutation, enrichment, transactions, and health checks in Python modules under `media/`; keep GitHub Actions as an execution/verification host only. ChatGPT reads compact derived artifacts first and writes by creating a strict semantic command request, never by freely editing YAML.

**Tech Stack:** Python standard library, PyYAML `>=6.0,<7`, jsonschema `>=4.23,<5`, pytest `>=8,<9`, SQLite via stdlib, GitHub Actions, TMDB HTTP API via stdlib `urllib` with injected HTTP functions in tests.

**Spec:** `docs/superpowers/specs/2026-10-01-media-tooling-orchestration-design.md`

## Global Constraints

- Git/YAML remains source of truth; `media/generated/` and SQLite are derived.
- Existing v4 schemas and `media/vocabulary.yaml` remain authoritative; normal media operations cannot modify them.
- No OpenAI/model credentials or model inference run inside GitHub Actions.
- LLM output enters the write path only through strict command JSON Schemas; no arbitrary patch, filename, or shell field exists.
- Mutable commands require an immutable UUID `operation_id` and are idempotent.
- Normal command writes use default-deny, operation-specific path allowlists.
- Secret-bearing/write workflows run only for trusted same-repository `media/op-*` branches; fork PRs never receive TMDB credentials.
- No auto-merge in v1.
- Generated text artifacts must be byte-identical for the same canonical state.
- Provider outages do not block mutations of already-resolved works that need no provider data.
- Manual metadata overrides always win over provider metadata.
- `recommend-context` is read-only in v1; recommendation interaction persistence is deferred until a dedicated typed interaction command exists.

## Review Focus

1. **Ambiguous identity** — title/year ambiguity returns `needs_input/ambiguous_identity` and makes zero canonical changes. Covered in Tasks 2 and 9.
2. **Duplicate execution** — the same `operation_id` returns `already_applied` and adds no second history/signal effect. Covered in Tasks 4 and 9.
3. **Stale operation branch** — update from current `main` before interpreting/applying the semantic request; never replay an old file diff. Covered in Task 8.
4. **Architecture-path write attempt** — reject before syncing/committing any files; request deletion is the only transient-path exception. Covered in Tasks 4 and 8.
5. **TMDB failure** — existing-work feedback succeeds without TMDB, while provider-dependent add-work returns `provider_unavailable`. Covered in Tasks 5 and 9.

---

### Task 1: Typed command contracts and domain errors

**Files:**
- Create: `media/domain/__init__.py`
- Create: `media/domain/types.py`
- Create: `media/domain/commands.py`
- Create: `media/domain/errors.py`
- Create: `media/commands/__init__.py`
- Create: `media/commands/schema.py`
- Create: `media/commands/schemas/common.schema.json`
- Create: `media/commands/schemas/record_viewing_feedback.schema.json`
- Create: `media/commands/schemas/set_interest.schema.json`
- Create: `media/commands/schemas/add_work.schema.json`
- Create: `media/commands/schemas/recommend_context.schema.json`
- Test: `tests/media/test_command_contracts.py`

**Interfaces:**
- Consumes: `media.tools.schema_utils.validate_against_schema`.
- Produces: `WorkRef`, `TargetUpdate`, `RecordViewingFeedbackCommand`, `SetInterestCommand`, `AddWorkCommand`, `RecommendContextRequest`, `parse_command`, `load_command`, and typed command/domain errors.

- [ ] **Step 1: Write failing schema/parser tests**

```python
def test_mutable_command_requires_uuid_operation_id(): ...
def test_work_ref_requires_at_least_one_identity_key(): ...
def test_rating_rejects_non_half_step_score(): ...
def test_set_interest_rejects_priority_six(): ...
def test_unknown_operation_is_rejected(): ...
```

Pin canonical values from v4: rating score `1..10` in `0.5` increments; rating sources `explicit|explicit_approx|inferred|none`; confidence `exact|high|medium|low|none`; viewing/reaction/interest enums exactly match canonical schema; feedback strength `1..3`; interest priority `1..5`.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_command_contracts.py -q`

Expected: FAIL because modules/schemas do not exist.

- [ ] **Step 3: Implement exact public dataclasses**

```python
@dataclass(frozen=True)
class WorkRef:
    id: str | None = None
    title: str | None = None
    year: int | None = None
    tmdb_media_type: Literal["movie", "tv"] | None = None
    tmdb_id: int | None = None
    imdb_id: str | None = None

@dataclass(frozen=True)
class TargetUpdate:
    target: str
    viewing: Mapping[str, Any] | None = None
    rating: Mapping[str, Any] | None = None
    reaction: Mapping[str, Any] | None = None
    feedback: Mapping[str, Any] | None = None

@dataclass(frozen=True)
class RecordViewingFeedbackCommand:
    schema_version: int
    operation_id: str
    work_ref: WorkRef
    target_updates: tuple[TargetUpdate, ...]

@dataclass(frozen=True)
class SetInterestCommand:
    schema_version: int
    operation_id: str
    work_ref: WorkRef
    target: str
    state: Literal["unknown", "candidate", "shortlist", "not_interested"]
    priority: int | None

@dataclass(frozen=True)
class AddWorkCommand:
    schema_version: int
    operation_id: str
    work_ref: WorkRef

@dataclass(frozen=True)
class RecommendContextRequest:
    schema_version: int
    target: str
    text: str | None
    only_unwatched: bool
    runtime_max: int | None
    include_not_interested: bool
    limit: int
```

`parse_command(data: Mapping[str, Any], schema_dir: Path | None = None) -> MediaCommand | RecommendContextRequest` validates the operation-specific JSON Schema before constructing objects. Do not add Pydantic.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest tests/media/test_command_contracts.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add media/domain media/commands tests/media/test_command_contracts.py
git commit -m "feat: add typed media command contracts"
```

---

### Task 2: Canonical YAML repository, target resolution, and work resolver

**Files:**
- Create: `media/repository/__init__.py`
- Create: `media/repository/canonical.py`
- Create: `media/repository/yaml_repo.py`
- Create: `media/service/__init__.py`
- Create: `media/service/resolve.py`
- Create: `tests/fixtures/media_repo/media/config/viewers.yaml`
- Create: `tests/fixtures/media_repo/media/config/groups.yaml`
- Create: `tests/fixtures/media_repo/media/data/works/*.yaml` (5-8 synthetic works)
- Create: `tests/media/fixture_repo.py`
- Test: `tests/media/test_repository_resolver.py`

**Interfaces:**
- Consumes: Task 1 `WorkRef`, existing YAML helpers.
- Produces: `WorkRecord`, `CanonicalRepository` protocol, `YamlRepository`, `resolve_work`, `resolve_target_kind`.

- [ ] **Step 1: Write failing resolver tests**

```python
def test_resolve_exact_internal_id(...): ...
def test_tmdb_identity_uses_media_type_plus_numeric_id(...): ...
def test_title_ru_and_alternate_titles_resolve(...): ...
def test_dune_without_year_returns_ambiguous_candidates(...): ...
def test_unknown_target_is_rejected(...): ...
```

Synthetic fixture must include two `Dune` years and a movie/tv pair sharing the same numeric TMDB ID to pin composite identity.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_repository_resolver.py -q`

- [ ] **Step 3: Implement repository/resolver**

```python
@dataclass(frozen=True)
class WorkRecord:
    path: Path
    data: Mapping[str, Any]
    @property
    def id(self) -> str: ...

class CanonicalRepository(Protocol):
    def get_work(self, work_id: str) -> WorkRecord | None: ...
    def iter_works(self) -> Iterator[WorkRecord]: ...
    def configured_targets(self) -> tuple[set[str], dict[str, list[str]]]: ...
```

Resolver order for explicit references: internal ID; TMDB composite; IMDb; exact normalized title/alternate title plus optional year. Normalize with Unicode `casefold()` + whitespace collapse only; no fuzzy matching/transliteration in v1.

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest tests/media/test_repository_resolver.py -q`

- [ ] **Step 5: Commit**

```bash
git add media/repository media/service/resolve.py tests/fixtures/media_repo tests/media/fixture_repo.py tests/media/test_repository_resolver.py
git commit -m "feat: add canonical media resolver"
```

---

### Task 3: Read repositories, search, and recommendation context

**Files:**
- Create: `media/repository/index_repo.py`
- Create: `media/repository/sqlite_repo.py`
- Create: `media/service/query.py`
- Create: `media/service/recommend.py`
- Test: `tests/media/test_query_service.py`
- Test: `tests/media/test_recommend_context.py`
- Test: `tests/media/test_sqlite_repo.py`

**Interfaces:**
- Consumes: Task 1 request types, Task 2 repository, `generated/index.jsonl`, generated profiles, existing `build_database`.
- Produces: read-only `IndexRepository`, read-only `SQLiteRepository`, `search_works`, `show_work`, `build_recommend_context`.

- [ ] **Step 1: Write failing read/recommend tests**

```python
def test_index_search_finds_title_without_scanning_full_yaml(...): ...
def test_sqlite_repository_returns_same_work_ids_as_index_for_simple_search(...): ...
def test_recommend_context_has_strengths_and_concerns_but_no_match_score(...): ...
def test_primary_only_unwatched_excludes_watched(...): ...
def test_couple_only_unwatched_excludes_only_if_every_member_watched(...): ...
def test_not_interested_is_excluded_by_default(...): ...
def test_runtime_max_is_hard_filter(...): ...
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_query_service.py tests/media/test_recommend_context.py tests/media/test_sqlite_repo.py -q`

- [ ] **Step 3: Implement read-only repositories**

`IndexRepository` reads existing JSONL. `SQLiteRepository` exposes only read methods (`search`, `get_work_summary`) and never a canonical write method. CLI defaults to index/YAML; local callers may explicitly choose SQLite when they know the derived DB is fresh.

- [ ] **Step 4: Implement recommendation context**

`build_recommend_context(media_root: Path, request: RecommendContextRequest) -> dict[str, Any]`:

1. apply hard filters;
2. load target profile;
3. map candidate traits against profile affinities (`score>0` strengths, `<0` concerns);
4. include viewer/member viewing evidence;
5. order deterministically by `(matched_affinity_count DESC, interest_priority DESC, work_id ASC)`;
6. return at most `limit` candidates.

Do not persist or expose an opaque overall score. Do not write recommendation interactions in v1.

- [ ] **Step 5: Run GREEN and commit**

Run: `python -m pytest tests/media/test_query_service.py tests/media/test_recommend_context.py tests/media/test_sqlite_repo.py -q`

```bash
git add media/repository/index_repo.py media/repository/sqlite_repo.py media/service/query.py media/service/recommend.py tests/media/test_query_service.py tests/media/test_recommend_context.py tests/media/test_sqlite_repo.py
git commit -m "feat: add media retrieval context"
```

---

### Task 4: ChangeSet, existing-work mutations, idempotency, and atomic transaction

**Files:**
- Create: `media/domain/changeset.py`
- Create: `media/service/mutate.py`
- Create: `media/service/path_policy.py`
- Create: `media/service/transaction.py`
- Create: `.media/operations/.gitkeep`
- Test: `tests/media/test_mutations.py`
- Test: `tests/media/test_transaction.py`

**Interfaces:**
- Consumes: Tasks 1-2, `validate_repository`, `write_index`, `write_profiles`.
- Produces: `MutationPlan`, `OperationResult`, `plan_record_viewing_feedback`, `plan_set_interest`, `preview_command`, `execute_command`, path-policy helpers.

- [ ] **Step 1: Write failing mutation/transaction tests**

```python
def test_record_feedback_merges_only_supplied_components(...): ...
def test_changed_existing_signal_appends_one_history_entry(...): ...
def test_group_target_rejects_viewing_patch(...): ...
def test_set_interest_clears_priority_for_not_interested(...): ...
def test_same_operation_id_returns_already_applied_without_second_effect(...): ...
def test_invalid_vocabulary_term_leaves_original_tree_byte_identical(...): ...
def test_path_policy_rejects_schema_and_service_paths(...): ...
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_mutations.py tests/media/test_transaction.py -q`

- [ ] **Step 3: Implement mutation semantics**

```python
@dataclass(frozen=True)
class MutationPlan:
    operation_id: str
    operation: str
    changed_entities: tuple[str, ...]
    documents: Mapping[str, Mapping[str, Any]]
    rebuild_index: bool
    rebuild_profile_targets: tuple[str, ...]

@dataclass(frozen=True)
class OperationResult:
    status: Literal["planned", "applied", "no_change", "already_applied"]
    operation_id: str
    operation: str
    changed_entities: tuple[str, ...]
    changed_files: tuple[str, ...]
```

Viewer target -> `viewer_signals`; group target -> `group_signals`. Merge only supplied signal components and preserve unrelated keys. If an existing supplied component changes, append one `history` entry with `at`, `previous`, `current`. Preserve `created_at`, update `updated_at`.

`set_interest`: priority `1..5` is retained only for `candidate|shortlist`; clear it for `unknown|not_interested`.

- [ ] **Step 4: Implement transaction/receipt flow**

`execute_command(repo_root: Path, command: MutableCommand, *, now: datetime | None = None, provider: MetadataProvider | None = None) -> OperationResult`:

1. check `.media/operations/<operation_id>.json`;
2. copy `media/` to a temporary repo root;
3. resolve and plan against that temporary canonical state;
4. apply plan there;
5. validate canonical state and rebuild index/profiles there;
6. diff original vs temporary tree;
7. enforce operation-specific allowlist;
8. sync allowed files back with rollback on copy failure;
9. write receipt only after successful sync.

Current mutation allowlist: relevant `media/data/works/*.yaml`, `media/generated/index.jsonl`, `media/generated/profiles/*.yaml`, `.media/operations/*.json`. Architecture/config/schema/vocabulary/tooling paths are denied by default.

- [ ] **Step 5: Run GREEN and commit**

Run: `python -m pytest tests/media/test_mutations.py tests/media/test_transaction.py -q`

```bash
git add media/domain/changeset.py media/service/mutate.py media/service/path_policy.py media/service/transaction.py .media/operations tests/media/test_mutations.py tests/media/test_transaction.py
git commit -m "feat: add transactional media mutations"
```

---

### Task 5: TMDB provider and add-work

**Files:**
- Create: `media/providers/__init__.py`
- Create: `media/providers/base.py`
- Create: `media/providers/tmdb.py`
- Create: `media/service/enrich.py`
- Modify: `media/service/mutate.py`
- Modify: `media/service/transaction.py`
- Create: `tests/fixtures/tmdb/search_arrival.json`
- Create: `tests/fixtures/tmdb/movie_arrival.json`
- Test: `tests/media/test_tmdb_provider.py`
- Test: `tests/media/test_add_work.py`

**Interfaces:**
- Consumes: `AddWorkCommand`, Task 2 resolver, Task 4 transaction.
- Produces: `ProviderCandidate`, `CanonicalMetadata`, `MetadataProvider`, `TMDBProvider`, `plan_add_work`, `make_work_id`.

- [ ] **Step 1: Write failing provider/add tests**

```python
def test_tmdb_normalizes_arrival_identity_and_provenance(...): ...
def test_search_filters_out_person_results(...): ...
def test_multiple_plausible_results_are_ambiguous(...): ...
def test_existing_tmdb_identity_returns_no_change_not_duplicate(...): ...
def test_provider_failure_blocks_only_new_provider_dependent_add(...): ...
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_tmdb_provider.py tests/media/test_add_work.py -q`

- [ ] **Step 3: Implement provider protocol and TMDB adapter**

```python
@dataclass(frozen=True)
class ProviderCandidate:
    media_type: Literal["movie", "tv"]
    provider_id: int
    title: str
    original_title: str
    year: int | None

@dataclass(frozen=True)
class CanonicalMetadata:
    identity: Mapping[str, Any]
    external: Mapping[str, Any]

class MetadataProvider(Protocol):
    def search_work(self, title: str, year: int | None = None) -> list[ProviderCandidate]: ...
    def fetch_work(self, media_type: Literal["movie", "tv"], provider_id: int) -> CanonicalMetadata: ...
```

`TMDBProvider(token, request_json=None)` uses bearer auth. Search `/3/search/multi`; details use `/{media_type}/{id}?language=ru-RU&append_to_response=external_ids,credits,release_dates,content_ratings`. Filter `person`; map TMDB `tv` type `Miniseries` to canonical `miniseries`, else `series`. `title_ru` falls back to provider localized title/name, then original title if localization is empty. Store only fields supported by canonical schema; never raw provider JSON.

- [ ] **Step 4: Implement add-work planning**

Flow: try canonical resolution -> provider search/fetch if absent -> re-check provider-derived TMDB composite then IMDb -> return `no_change` when the work already exists -> otherwise create one work file and run full transaction validation.

Auto-select a provider candidate only when exact normalized title plus requested year (when supplied) leaves exactly one movie/tv candidate; otherwise return ambiguity.

`make_work_id(...)` uses NFKD ASCII slug + year; if empty/colliding, use/suffix `tmdb-<media_type>-<id>`.

- [ ] **Step 5: Run GREEN and commit**

Run: `python -m pytest tests/media/test_tmdb_provider.py tests/media/test_add_work.py -q`

```bash
git add media/providers media/service/enrich.py media/service/mutate.py media/service/transaction.py tests/fixtures/tmdb tests/media/test_tmdb_provider.py tests/media/test_add_work.py
git commit -m "feat: add TMDB-backed work creation"
```

---

### Task 6: Deterministic rebuild checks and `media doctor`

**Files:**
- Create: `media/tools/rebuild.py`
- Create: `media/tools/doctor.py`
- Modify: `media/tools/build_profiles.py`
- Test: `tests/media/test_rebuild.py`
- Test: `tests/media/test_doctor.py`

**Interfaces:**
- Consumes: existing validator, index/profile/database builders.
- Produces: `write_profiles(media_root, output_dir=None)`, `rebuild_generated`, `check_generated`, `DoctorCheck`, `DoctorReport`, `doctor`.

- [ ] **Step 1: Write failing health tests**

```python
def test_two_text_rebuilds_are_byte_identical(...): ...
def test_stale_index_is_detected(...): ...
def test_stale_profile_is_detected(...): ...
def test_doctor_builds_sqlite_only_in_temp(...): ...
def test_doctor_reports_tracked_database_sqlite_when_git_available(...): ...
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_rebuild.py tests/media/test_doctor.py -q`

- [ ] **Step 3: Add output-dir support and rebuild checking**

Change:

```python
def write_profiles(media_root: Path, output_dir: Path | None = None) -> list[Path]: ...
```

`check_generated(media_root)` rebuilds index/profiles to temp and byte-compares text artifacts. Never compare SQLite bytes.

- [ ] **Step 4: Implement doctor**

```python
@dataclass(frozen=True)
class DoctorCheck:
    code: str
    ok: bool
    message: str

@dataclass(frozen=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]
    @property
    def ok(self) -> bool: ...
```

Doctor runs canonical validation, generated drift checks, temporary SQLite build, and fixed-argument `git ls-files` check when `.git` exists to ensure runtime DB is not tracked.

- [ ] **Step 5: Run GREEN and commit**

Run: `python -m pytest tests/media/test_rebuild.py tests/media/test_doctor.py -q`

```bash
git add media/tools/rebuild.py media/tools/doctor.py media/tools/build_profiles.py tests/media/test_rebuild.py tests/media/test_doctor.py
git commit -m "feat: add deterministic media doctor"
```

---

### Task 7: CLI and stable machine-readable output

**Files:**
- Create: `media/cli.py`
- Modify: `media/README.md`
- Test: `tests/media/test_cli.py`

**Interfaces:**
- Consumes: Tasks 1-6.
- Produces: `python -m media.cli` commands.

- [ ] **Step 1: Write failing CLI tests**

```python
def test_apply_command_dry_run_changes_nothing(...): ...
def test_apply_command_json_reports_status_entities_and_files(...): ...
def test_add_existing_work_reports_no_change(...): ...
def test_doctor_json_has_status_and_checks(...): ...
def test_recommend_context_json_is_stable(...): ...
```

Exit codes: `0` success/no_change/already_applied, `2` invalid or ambiguous user command, `3` canonical/doctor failure, `4` provider unavailable.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_cli.py -q`

- [ ] **Step 3: Implement CLI**

```text
python -m media.cli search QUERY [--limit N] [--format human|json]
python -m media.cli show WORK_REF [--format human|json]
python -m media.cli recommend-context --request FILE [--format human|json]
python -m media.cli apply-command FILE [--dry-run] [--format human|json]
python -m media.cli doctor [--format human|json]
python -m media.cli rebuild [--check]
```

Read `TMDB_READ_TOKEN` only when an add-work operation actually needs provider access.

- [ ] **Step 4: Run GREEN plus current media suite**

Run: `python -m pytest tests/media -q`

- [ ] **Step 5: Commit**

```bash
git add media/cli.py media/README.md tests/media/test_cli.py
git commit -m "feat: add media service CLI"
```

---

### Task 8: GitHub Actions orchestration and trust boundary

**Files:**
- Create: `.github/workflows/media-check.yml`
- Create: `.github/workflows/media-command.yml`
- Create: `.github/workflows/media-maintenance.yml`
- Create: `.media/README.md`
- Create: `.media/requests/.gitkeep`
- Test: `tests/media/test_workflows.py`

**Interfaces:**
- Consumes: Task 7 CLI.
- Produces: data-operation PR execution, read-only PR gate, manual maintenance checks.

- [ ] **Step 1: Write failing workflow contract tests**

Assert:

- `media-check.yml` is read-only and runs full pytest + validator + rebuild check + doctor;
- `media-command.yml` guards `github.event.pull_request.head.repo.full_name == github.repository` and `media/op-` prefix before secret access;
- no OpenAI secret/reference exists;
- `TMDB_READ_TOKEN` is scoped only to apply-command step;
- no auto-merge exists;
- command workflow explicitly handles request-file deletion and checks staged paths.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_workflows.py -q`

- [ ] **Step 3: Implement `media-check.yml`**

Triggers: relevant `pull_request` paths plus `workflow_dispatch` with optional `expected_sha`. Use Python 3.12, install `media/requirements.txt`, then run:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

If `expected_sha` is supplied, fail when checked-out HEAD differs.

- [ ] **Step 4: Implement `media-command.yml` stale-base replay and loop protection**

Trusted same-repo PR + `media/op-*` only. Per-PR concurrency group. Sequence:

1. checkout head branch;
2. require exactly one pending `.media/requests/*.json`;
3. fetch current `main` and merge it into the operation branch **before** command execution; on merge conflict stop with `conflict` and make no media mutation;
4. execute the semantic request against this current merged canonical state;
5. remove that exact request file;
6. stage only operation allowlist outputs plus the deletion of that exact request path;
7. reject staged architecture/tooling/schema/vocabulary/config paths;
8. run full local verification before commit;
9. commit/push to same branch;
10. explicitly `workflow_dispatch` `media-check.yml` at the new branch head SHA using `actions: write`.

Do not depend on a `GITHUB_TOKEN` push to recursively trigger workflows.

- [ ] **Step 5: Implement read-only `media-maintenance.yml` v1**

Manual `workflow_dispatch`: `doctor` or `rebuild-check`. No direct writes to `main`; metadata-refresh writes remain deferred until they reuse the normal PR transaction path.

- [ ] **Step 6: Run workflow tests GREEN and commit**

Run: `python -m pytest tests/media/test_workflows.py -q`

```bash
git add .github/workflows .media/README.md .media/requests tests/media/test_workflows.py
git commit -m "ci: add media command and validation workflows"
```

---

### Task 9: End-to-end acceptance, agent contract, and final branch verification

**Files:**
- Modify: `media/AGENTS.md`
- Modify: `media/README.md`
- Modify: `README.md` if media usage is linked there
- Create: `tests/media/test_tooling_e2e.py`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: complete documented workflow and acceptance coverage.

- [ ] **Step 1: Write acceptance tests**

```python
def test_e2e_primary_and_partner_feedback_is_one_atomic_command(...): ...
def test_e2e_add_new_tmdb_work_validates_and_rebuilds(...): ...
def test_e2e_recommend_context_uses_compact_retrieval(...): ...
def test_e2e_duplicate_operation_has_no_second_effect(...): ...
def test_e2e_ambiguous_identity_changes_nothing(...): ...
def test_e2e_invalid_term_changes_nothing(...): ...
def test_e2e_stale_generated_artifact_fails_check(...): ...
def test_e2e_architecture_path_is_rejected(...): ...
def test_e2e_provider_outage_does_not_block_existing_feedback(...): ...
```

- [ ] **Step 2: Run acceptance tests RED for any remaining gap**

Run: `python -m pytest tests/media/test_tooling_e2e.py -q`

Do not weaken assertions; make only the minimum integration fixes required.

- [ ] **Step 3: Update agent/user docs**

Document:

```text
read: generated index/profile -> selected canonical YAML
write: natural language -> typed JSON request -> media operation PR -> trusted Action -> service -> validation/rebuild -> review/merge
```

State that direct YAML edits are no longer the normal LLM mutation path, request files are transient, schemas/vocabulary remain architectural changes, and OpenAI keys do not belong in Actions.

- [ ] **Step 4: Run complete local verification**

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Expected: all tests PASS, zero canonical issues, zero generated drift, doctor `ok`.

- [ ] **Step 5: Verify deterministic text artifacts twice**

Build index/profiles into two independent temp directories and byte-compare every text artifact.

Expected: identical bytes.

- [ ] **Step 6: Commit final docs/acceptance**

```bash
git add media/AGENTS.md media/README.md README.md tests/media/test_tooling_e2e.py
git commit -m "docs: finalize media tooling workflow"
```

- [ ] **Step 7: Whole-branch review against spec**

Check every spec section against implemented tasks; confirm deferred features did not slip in and no normal operation can modify architecture paths.

- [ ] **Step 8: Open implementation PR without auto-merge**

PR body must report exact test counts, validator/rebuild/doctor results, security/trust constraints, and any remaining limitations.

- [ ] **Step 9: Confirm GitHub `media-check` succeeds on the final PR head**

Do not call the implementation complete from local tests alone. Verify the workflow run is attached to the final head SHA and green before offering merge.
