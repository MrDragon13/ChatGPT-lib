# Media Tooling & Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub-native typed tooling layer that lets ChatGPT, a local CLI, and future clients query and safely mutate the v4 media library through one deterministic Python service layer.

**Architecture:** Keep Git/YAML canonical and put typed command parsing, resolution, mutation, retrieval, enrichment, and transaction logic in Python modules under `media/`. ChatGPT produces validated structured requests; GitHub Actions executes the same service code used by the CLI, commits only allowlisted data/generated/audit paths, and never runs an LLM. Read paths use `generated/index.jsonl` plus generated profiles first, with selected canonical YAML loaded only when needed.

**Tech Stack:** Python standard library, PyYAML `>=6.0,<7`, jsonschema `>=4.23,<5`, pytest `>=8,<9`, SQLite via stdlib, GitHub Actions, TMDB HTTP API via stdlib `urllib` with an injected request function for tests.

**Spec:** `docs/superpowers/specs/2026-10-01-media-tooling-orchestration-design.md`

## Global Constraints

- Git/YAML remains the canonical source of truth; `media/generated/` and SQLite are derived.
- Existing v4 schemas/vocabulary remain authoritative; normal data operations must not mutate them.
- No OpenAI/model credential or model inference runs inside GitHub Actions.
- LLM output is accepted only through strict typed command schemas; there is no arbitrary patch or shell field.
- Mutable commands require an immutable `operation_id` and must be idempotent.
- Normal command writes use default-deny, operation-specific path allowlists.
- `media-command.yml` may use write permissions/secrets only for trusted same-repository branches; fork PRs never receive the TMDB secret.
- No auto-merge in the first implementation.
- Generated text artifacts must be byte-identical for the same canonical revision.
- TMDB/provider failure must not block mutations of already-resolved existing works that do not need provider data.
- Existing manual metadata overrides continue to win over provider metadata.

## Review Focus

1. **Ambiguous title/year input** — return `needs_input/ambiguous_identity` with candidates and leave canonical files byte-identical; pinned in Task 2 and Task 9.
2. **Retry of the same mutable command** — return `already_applied` and do not duplicate signal/history effects; pinned in Task 4 and Task 9.
3. **Concurrent/stale-base mutation** — never apply a saved textual diff to a newer base; replay the semantic command against current state or return `conflict`; pinned in Task 4.
4. **Command attempts to touch architecture paths** — reject before syncing any files; pinned in Task 4 and Task 8.
5. **TMDB unavailable** — existing-work feedback still succeeds, while an add-work operation that requires provider identity returns `provider_unavailable`; pinned in Task 5 and Task 9.

---

### Task 1: Typed command contracts and domain types

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
- Consumes: `media.tools.schema_utils.validate_against_schema(instance, schema_name, schema_dir)`.
- Produces: `WorkRef`, `TargetUpdate`, `RecordViewingFeedbackCommand`, `SetInterestCommand`, `AddWorkCommand`, `RecommendContextRequest`, `MediaCommand`, `parse_command(data, schema_dir=None)`, `load_command(path)`, and typed domain errors.

- [ ] **Step 1: Write failing command-schema tests**

```python
def test_record_feedback_requires_operation_id_and_known_fields():
    with pytest.raises(CommandValidationError):
        parse_command({"schema_version": 1, "operation": "record_viewing_feedback", "work_ref": {"title": "Arrival"}, "target_updates": []})


def test_rating_is_constrained_to_half_steps_and_existing_sources():
    bad = valid_record_feedback_dict()
    bad["target_updates"][0]["rating"] = {"score": 8.3, "source": "explicit", "confidence": "exact"}
    with pytest.raises(CommandValidationError):
        parse_command(bad)


def test_set_interest_priority_is_one_to_five():
    bad = valid_set_interest_dict(priority=6)
    with pytest.raises(CommandValidationError):
        parse_command(bad)
```

Also pin: unknown operation rejected; `WorkRef` must contain at least one identity key; mutable `operation_id` uses canonical UUID text form; feedback terms are strings but vocabulary membership is deferred to service validation.

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m pytest tests/media/test_command_contracts.py -q`

Expected: FAIL because command modules/schemas do not exist.

- [ ] **Step 3: Implement the domain dataclasses and parser**

Use these public shapes:

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

`parse_command(data: Mapping[str, Any], schema_dir: Path | None = None) -> MediaCommand | RecommendContextRequest` validates the operation-specific schema first, then constructs dataclasses. Do not add Pydantic or another dependency.

- [ ] **Step 4: Run command-contract tests GREEN**

Run: `python -m pytest tests/media/test_command_contracts.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add media/domain media/commands tests/media/test_command_contracts.py
git commit -m "feat: add typed media command contracts"
```

---

### Task 2: Canonical repository, targets, resolver, and synthetic fixture

**Files:**
- Create: `media/repository/__init__.py`
- Create: `media/repository/canonical.py`
- Create: `media/repository/yaml_repo.py`
- Create: `media/service/__init__.py`
- Create: `media/service/resolve.py`
- Create: `tests/fixtures/media_repo/media/config/viewers.yaml`
- Create: `tests/fixtures/media_repo/media/config/groups.yaml`
- Create: `tests/fixtures/media_repo/media/data/works/*.yaml` (5-8 synthetic works only)
- Create: `tests/media/fixture_repo.py`
- Test: `tests/media/test_repository_resolver.py`

**Interfaces:**
- Consumes: `WorkRef` from Task 1 and existing YAML helpers from `media.tools.common`.
- Produces: `WorkRecord`, `CanonicalRepository` protocol, `YamlRepository`, `resolve_work(repo, ref)`, `resolve_target_kind(media_root, target)`.

- [ ] **Step 1: Write failing repository/resolver tests**

Pin these cases:

```python
def test_resolve_exact_internal_id(repo):
    assert resolve_work(repo, WorkRef(id="arrival-2016")).id == "arrival-2016"


def test_tmdb_identity_is_composite(repo):
    # Same numeric TMDB id may exist under movie and tv in synthetic fixture.
    assert resolve_work(repo, WorkRef(tmdb_media_type="movie", tmdb_id=42)).id == "movie-42"
    assert resolve_work(repo, WorkRef(tmdb_media_type="tv", tmdb_id=42)).id == "tv-42"


def test_ambiguous_title_returns_candidates_without_guessing(repo):
    with pytest.raises(AmbiguousIdentityError) as exc:
        resolve_work(repo, WorkRef(title="Dune"))
    assert {c.year for c in exc.value.candidates} == {1984, 2021}
```

Also test title matching across `title_original`, `title_ru`, and `alternate_titles`; unknown work -> `NotFoundError`; unknown target -> `UnknownTargetError`.

- [ ] **Step 2: Run resolver tests RED**

Run: `python -m pytest tests/media/test_repository_resolver.py -q`

Expected: FAIL because repository/resolver modules do not exist.

- [ ] **Step 3: Implement repository and resolver**

Use:

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

class YamlRepository:
    def __init__(self, media_root: Path): ...
```

Resolver order for a supplied ref: exact internal ID when explicitly supplied; exact TMDB composite; exact IMDb; normalized title/alternate title with optional year. For add-work dedup in Task 5, re-check provider-derived TMDB then IMDb before creation. Title normalization is Unicode casefold + collapsed whitespace; do not transliterate or fuzzy-match in v1.

- [ ] **Step 4: Run resolver tests GREEN**

Run: `python -m pytest tests/media/test_repository_resolver.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add media/repository media/service/resolve.py tests/fixtures/media_repo tests/media/fixture_repo.py tests/media/test_repository_resolver.py
git commit -m "feat: add canonical media resolver"
```

---

### Task 3: Index query layer and recommendation context

**Files:**
- Create: `media/repository/index_repo.py`
- Create: `media/service/query.py`
- Create: `media/service/recommend.py`
- Test: `tests/media/test_query_service.py`
- Test: `tests/media/test_recommend_context.py`

**Interfaces:**
- Consumes: `RecommendContextRequest`, `YamlRepository`, `generated/index.jsonl`, `generated/profiles/<target>.yaml`.
- Produces: `IndexRepository`, `search_works(media_root, query, limit=20)`, `show_work(media_root, ref)`, `build_recommend_context(media_root, request)`.

- [ ] **Step 1: Write failing query/recommendation tests**

Pin:

```python
def test_search_uses_compact_index_before_full_yaml(fixture_repo):
    results = search_works(fixture_repo / "media", "arrival")
    assert results[0]["id"] == "arrival-2016"


def test_recommend_context_exposes_evidence_not_opaque_final_score(fixture_repo):
    ctx = build_recommend_context(fixture_repo / "media", request_for("primary", only_unwatched=True))
    candidate = ctx["candidates"][0]
    assert "strengths" in candidate["evidence"]
    assert "concerns" in candidate["evidence"]
    assert "match_score" not in candidate


def test_group_unwatched_excludes_only_when_every_member_watched(fixture_repo):
    ctx = build_recommend_context(fixture_repo / "media", request_for("couple", only_unwatched=True))
    assert "watched-by-both" not in ids(ctx)
    assert "watched-by-primary-only" in ids(ctx)
```

Also test `runtime_max`, `not_interested` exclusion by default, explicit inclusion override, deterministic `limit`, and stable ordering.

- [ ] **Step 2: Run query/recommend tests RED**

Run: `python -m pytest tests/media/test_query_service.py tests/media/test_recommend_context.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement compact retrieval and explainable ranking**

`IndexRepository` reads rows with existing `iter_jsonl`. `build_recommend_context(...) -> dict[str, Any]` applies hard filters first, loads the target profile, then derives evidence from candidate traits intersecting profile affinities:

- affinity `score > 0` -> `strengths`;
- affinity `score < 0` -> `concerns`;
- no overall score is persisted or exposed.

For deterministic shortlist ordering use `(matched_affinity_count DESC, interest_priority DESC, work_id ASC)`. This is retrieval-only and explicitly replaceable; it is not canonical preference data. For viewer targets, `only_unwatched` excludes `viewing=watched`. For group targets, it excludes a work only when every configured member is `watched`; include member viewing statuses as evidence for the LLM.

- [ ] **Step 4: Run query/recommend tests GREEN**

Run: `python -m pytest tests/media/test_query_service.py tests/media/test_recommend_context.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add media/repository/index_repo.py media/service/query.py media/service/recommend.py tests/media/test_query_service.py tests/media/test_recommend_context.py
git commit -m "feat: add media retrieval context"
```

---

### Task 4: ChangeSet, transactional existing-work mutations, idempotency, and path policy

**Files:**
- Create: `media/domain/changeset.py`
- Create: `media/service/mutate.py`
- Create: `media/service/transaction.py`
- Create: `media/service/path_policy.py`
- Create: `.media/operations/.gitkeep`
- Test: `tests/media/test_mutations.py`
- Test: `tests/media/test_transaction.py`

**Interfaces:**
- Consumes: mutable commands from Task 1, resolver/repository from Task 2, `validate_repository`, `write_index`, `write_profiles`.
- Produces: `MutationPlan`, `OperationResult`, `plan_record_viewing_feedback`, `plan_set_interest`, `preview_command`, `execute_command`, `allowed_paths_for_operation`, `verify_changed_paths`.

- [ ] **Step 1: Write failing mutation/transaction tests**

Pin all Review Focus behavior owned here:

```python
def test_record_feedback_updates_only_supplied_signal_parts(fixture_repo):
    result = execute_command(fixture_repo, feedback_command(score=8.5, reaction=None))
    work = load_work(fixture_repo, "arrival-2016")
    assert work["viewer_signals"]["primary"]["rating"]["score"] == 8.5
    assert "reaction" not in work["viewer_signals"]["primary"]
    assert result.status == "applied"


def test_retry_is_idempotent(fixture_repo):
    command = feedback_command(operation_id=FIXED_UUID)
    first = execute_command(fixture_repo, command)
    second = execute_command(fixture_repo, command)
    assert second.status == "already_applied"
    assert snapshot_media(fixture_repo) == snapshot_after(first)


def test_validation_failure_leaves_original_tree_unchanged(fixture_repo):
    before = snapshot_media(fixture_repo)
    with pytest.raises(TransactionValidationError):
        execute_command(fixture_repo, command_that_produces_invalid_term())
    assert snapshot_media(fixture_repo) == before


def test_path_policy_rejects_schema_write():
    with pytest.raises(PathPolicyError):
        verify_changed_paths("record_viewing_feedback", ["media/schemas/work.schema.json"])
```

Also test: viewer target writes `viewer_signals`; group target writes `group_signals` and rejects `viewing` because canonical group signals have no viewing field; interest priority is cleared for `unknown/not_interested`; stale `expected_base_sha` invokes semantic replay callback or returns `conflict`, never applies stored file bytes.

- [ ] **Step 2: Run transaction tests RED**

Run: `python -m pytest tests/media/test_mutations.py tests/media/test_transaction.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement ChangeSet and mutation semantics**

Use:

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
    status: Literal["planned", "applied", "already_applied"]
    operation_id: str
    operation: str
    changed_entities: tuple[str, ...]
    changed_files: tuple[str, ...]
```

Merge only explicitly supplied fields. When a supplied signal component changes an existing value, append one `history` entry containing `at`, `previous`, and `current` for the changed components; preserve unrelated signal keys. Update `provenance.updated_at`, preserving `created_at`.

For `set_interest`, write `target_states.<target>.interest`; priority is `1..5` only for `candidate/shortlist`, and is removed for `unknown/not_interested`.

- [ ] **Step 4: Implement transactional execution and receipts**

`execute_command(repo_root: Path, command: MutableCommand, *, now: datetime | None = None, expected_base_sha: str | None = None) -> OperationResult` must:

1. check `.media/operations/<operation_id>.json` before planning;
2. copy `media/` to an isolated temporary repository root;
3. resolve/replay the semantic command against that copy;
4. apply the plan there;
5. run canonical validation and rebuild derived text artifacts there;
6. diff original vs temporary trees;
7. verify changed paths against an operation-specific allowlist;
8. sync allowlisted files back with rollback-on-copy-error;
9. write the operation receipt only after successful sync.

Allowlisted final paths for current data operations are limited to the relevant `media/data/works/*.yaml`, `media/generated/index.jsonl`, `media/generated/profiles/*.yaml`, and `.media/operations/*.json`. Request files are orchestration inputs, not final canonical output.

- [ ] **Step 5: Run mutation/transaction tests GREEN**

Run: `python -m pytest tests/media/test_mutations.py tests/media/test_transaction.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add media/domain/changeset.py media/service/mutate.py media/service/transaction.py media/service/path_policy.py .media/operations tests/media/test_mutations.py tests/media/test_transaction.py
git commit -m "feat: add transactional media mutations"
```

---

### Task 5: TMDB provider and add-work flow

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
- Consumes: `AddWorkCommand`, repository/resolver, transaction engine.
- Produces: `ProviderCandidate`, `CanonicalMetadata`, `MetadataProvider`, `TMDBProvider`, `plan_add_work`, `make_work_id`.

- [ ] **Step 1: Write failing provider/add-work tests**

Pin:

```python
def test_tmdb_normalizes_movie_identity_and_metadata(fake_tmdb):
    item = fake_tmdb.fetch_work("movie", 329865)
    assert item.tmdb_id == 329865
    assert item.format == "movie"
    assert item.title_original == "Arrival"
    assert item.external_provenance["provider"] == "tmdb"


def test_add_work_rechecks_provider_ids_before_creating_duplicate(fixture_repo, fake_tmdb):
    command = add_work_command(title="Arrival")
    result = execute_command(fixture_repo, command, provider=fake_tmdb)
    assert result.status == "already_applied" or result.changed_entities == ("arrival-2016",)
    assert count_tmdb(fixture_repo, "movie", 329865) == 1


def test_provider_outage_blocks_only_provider_dependent_add(fixture_repo, failing_provider):
    with pytest.raises(ProviderUnavailableError):
        execute_command(fixture_repo, add_work_command(title="New Unknown Film"), provider=failing_provider)
```

Also test multiple plausible provider candidates -> `AmbiguousIdentityError`; empty search -> `NotFoundError`; manual `metadata.overrides` is never overwritten.

- [ ] **Step 2: Run provider/add-work tests RED**

Run: `python -m pytest tests/media/test_tmdb_provider.py tests/media/test_add_work.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement provider protocol and TMDB adapter**

Use:

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

`TMDBProvider(token: str, request_json: Callable[..., Mapping[str, Any]] | None = None)` uses bearer auth and stdlib HTTP. Search `/3/search/multi`, filter to `movie/tv`; details use `/{media_type}/{id}` with `language=ru-RU` and `append_to_response=external_ids,credits,release_dates,content_ratings`. Map TMDB `tv` with type `Miniseries` to canonical `miniseries`, otherwise `series`. Normalize only canonical fields supported by `work.schema.json`; never store raw provider payload.

- [ ] **Step 4: Implement add-work planning and deterministic IDs**

Flow: resolve existing ref -> provider search/fetch if still absent -> re-check TMDB composite then IMDb against canonical repo -> create one work document -> validate transaction.

`make_work_id(title_original: str, year: int | None, tmdb_media_type: str, tmdb_id: int, existing_ids: set[str]) -> str` uses NFKD ASCII slug + year; if the slug is empty or collides, fall back/suffix with `tmdb-<media_type>-<id>`. IDs are immutable after creation.

- [ ] **Step 5: Run provider/add-work tests GREEN**

Run: `python -m pytest tests/media/test_tmdb_provider.py tests/media/test_add_work.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add media/providers media/service/enrich.py media/service/mutate.py media/service/transaction.py tests/fixtures/tmdb tests/media/test_tmdb_provider.py tests/media/test_add_work.py
git commit -m "feat: add TMDB-backed work creation"
```

---

### Task 6: Deterministic rebuild checking and `media doctor`

**Files:**
- Create: `media/tools/rebuild.py`
- Create: `media/tools/doctor.py`
- Modify: `media/tools/build_profiles.py`
- Test: `tests/media/test_rebuild.py`
- Test: `tests/media/test_doctor.py`

**Interfaces:**
- Consumes: existing `validate_repository`, `write_index`, `build_database`, profile builder.
- Produces: `write_profiles(media_root, output_dir=None)`, `rebuild_generated(media_root)`, `check_generated(media_root)`, `DoctorCheck`, `DoctorReport`, `doctor(repo_root)`.

- [ ] **Step 1: Write failing rebuild/doctor tests**

Pin:

```python
def test_rebuild_is_byte_identical(fixture_repo):
    first = rebuild_snapshot(fixture_repo)
    second = rebuild_snapshot(fixture_repo)
    assert first == second


def test_check_generated_detects_stale_index(fixture_repo):
    corrupt_index(fixture_repo)
    assert "generated_index" in {x.code for x in check_generated(fixture_repo / "media")}


def test_doctor_rebuilds_sqlite_in_temp_without_committing_it(fixture_repo):
    report = doctor(fixture_repo)
    assert report.ok
    assert not (fixture_repo / "media/generated/database.sqlite").exists()
```

Also pin stale profile detection, validator errors surfaced, broken redirects surfaced through validator, and a tracked `media/generated/database.sqlite` is reported when a Git worktree is available.

- [ ] **Step 2: Run rebuild/doctor tests RED**

Run: `python -m pytest tests/media/test_rebuild.py tests/media/test_doctor.py -q`

Expected: FAIL.

- [ ] **Step 3: Add output-directory support to profiles and implement rebuild checks**

Change signature to:

```python
def write_profiles(media_root: Path, output_dir: Path | None = None) -> list[Path]: ...
```

`check_generated(media_root)` rebuilds index/profiles into a temporary directory and byte-compares against committed text artifacts. Do not compare SQLite bytes.

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

def doctor(repo_root: Path) -> DoctorReport: ...
```

Doctor runs canonical validation, generated drift checks, a temporary SQLite build, and the runtime-artifact Git-tracking check using fixed-argument `git ls-files` when `.git` is present. JSON/human formatting belongs to Task 7.

- [ ] **Step 5: Run rebuild/doctor tests GREEN**

Run: `python -m pytest tests/media/test_rebuild.py tests/media/test_doctor.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add media/tools/rebuild.py media/tools/doctor.py media/tools/build_profiles.py tests/media/test_rebuild.py tests/media/test_doctor.py
git commit -m "feat: add deterministic media doctor"
```

---

### Task 7: CLI and machine-readable results

**Files:**
- Create: `media/cli.py`
- Modify: `media/README.md`
- Test: `tests/media/test_cli.py`

**Interfaces:**
- Consumes: query/recommend service, command loader/transaction engine, rebuild/doctor.
- Produces: `python -m media.cli` with `search`, `show`, `recommend-context`, `apply-command`, `doctor`, `rebuild`.

- [ ] **Step 1: Write failing CLI tests**

Pin:

```python
def test_apply_command_dry_run_does_not_change_files(...): ...
def test_apply_command_json_result_contains_changed_entities(...): ...
def test_doctor_json_has_status_and_checks(...): ...
def test_recommend_context_json_is_valid_machine_output(...): ...
```

Also assert deterministic exit codes: `0` success, `2` invalid/ambiguous user command, `3` canonical/doctor failure, `4` provider unavailable.

- [ ] **Step 2: Run CLI tests RED**

Run: `python -m pytest tests/media/test_cli.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement CLI**

`main(argv: list[str] | None = None) -> int` supports:

```text
python -m media.cli search QUERY [--limit N] [--format human|json]
python -m media.cli show WORK_REF [--format human|json]
python -m media.cli recommend-context --request FILE [--format human|json]
python -m media.cli apply-command FILE [--dry-run] [--expected-base SHA] [--format human|json]
python -m media.cli doctor [--format human|json]
python -m media.cli rebuild [--check]
```

`apply-command` reads `TMDB_READ_TOKEN` only when an add-work command actually needs the provider. JSON output is a stable object with `status`, `operation_id` when applicable, `changed_entities`, `changed_files`, and error `reason`/`candidates` where applicable.

- [ ] **Step 4: Run CLI tests GREEN**

Run: `python -m pytest tests/media/test_cli.py -q`

Expected: PASS.

- [ ] **Step 5: Run all media unit/integration tests so far**

Run: `python -m pytest tests/media -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add media/cli.py media/README.md tests/media/test_cli.py
git commit -m "feat: add media service CLI"
```

---

### Task 8: GitHub Actions orchestration and trust boundaries

**Files:**
- Create: `.github/workflows/media-check.yml`
- Create: `.github/workflows/media-command.yml`
- Create: `.github/workflows/media-maintenance.yml`
- Create: `.media/README.md`
- Create: `.media/requests/.gitkeep`
- Test: `tests/media/test_workflows.py`

**Interfaces:**
- Consumes: `python -m media.cli` commands from Task 7.
- Produces: trusted PR command execution, deterministic PR checks, manual maintenance checks.

- [ ] **Step 1: Write failing workflow contract tests**

Read workflow files as text and assert:

- `media-check.yml` has `contents: read`, runs full pytest, `rebuild --check`, and `doctor`;
- `media-command.yml` rejects fork PRs with `github.event.pull_request.head.repo.full_name == github.repository` and requires `media/op-` head branch prefix;
- command workflow has no OpenAI secret/reference;
- TMDB token appears only in the command step that may need provider access;
- command workflow uses `contents: write`, `pull-requests: write`, and `actions: write` only because it must push the generated commit and explicitly dispatch a fresh head check;
- no workflow enables auto-merge.

- [ ] **Step 2: Run workflow tests RED**

Run: `python -m pytest tests/media/test_workflows.py -q`

Expected: FAIL because workflows do not exist.

- [ ] **Step 3: Implement `media-check.yml`**

Triggers: `pull_request` for relevant media/tooling/test paths plus `workflow_dispatch` with optional `expected_sha`. Use Python 3.12, install `media/requirements.txt`, run:

```text
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

When `expected_sha` is supplied, fail if checked-out `HEAD` differs. This workflow is read-only.

- [ ] **Step 4: Implement `media-command.yml` with loop protection**

Trigger on same-repo PR changes under `.media/requests/*.json`; guard same-repo + `media/op-` prefix before any secret-bearing step. Set a per-PR concurrency group.

Processing sequence:

1. checkout the PR head branch;
2. require exactly one pending request JSON or exit without mutation;
3. capture current head/base SHA;
4. run `apply-command` with `--expected-base` and JSON result;
5. delete the transient request file;
6. stage only allowlisted changed paths and the operation receipt;
7. fail if `git diff --cached --name-only` contains any disallowed path;
8. commit/push to the same head branch;
9. explicitly dispatch `media-check.yml` on that branch/ref with the new commit SHA using `actions: write`.

Do not rely on the push made with `GITHUB_TOKEN` to trigger another workflow; GitHub suppresses normal recursive workflow triggering for such pushes. The explicit `workflow_dispatch` is the supported re-check path.

- [ ] **Step 5: Implement read-only `media-maintenance.yml` v1**

Manual `workflow_dispatch` supports `doctor` and `rebuild-check` only. Metadata refresh writes remain deferred until the same PR-producing transaction path is reused; maintenance must not write directly to `main`.

- [ ] **Step 6: Run workflow tests GREEN**

Run: `python -m pytest tests/media/test_workflows.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .github/workflows .media/README.md .media/requests tests/media/test_workflows.py
git commit -m "ci: add media command and validation workflows"
```

---

### Task 9: End-to-end acceptance, agent contract, and full verification

**Files:**
- Modify: `media/AGENTS.md`
- Modify: `media/README.md`
- Modify: root `README.md` if it links media usage
- Create: `tests/media/test_tooling_e2e.py`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: documented ChatGPT/CLI/GitHub workflow and acceptance coverage for the approved spec.

- [ ] **Step 1: Write end-to-end acceptance tests**

Use the synthetic repo and pin the spec scenarios:

```python
def test_e2e_existing_work_feedback_is_one_atomic_operation(...):
    # primary watched + 8.5 explicit_approx; partner watched + liked
    ...


def test_e2e_add_work_then_validate_and_rebuild(...): ...
def test_e2e_recommend_context_does_not_require_loading_every_work(...): ...
def test_e2e_duplicate_operation_id_has_no_second_effect(...): ...
def test_e2e_invalid_semantic_term_leaves_tree_unchanged(...): ...
def test_e2e_stale_generated_artifact_fails_check(...): ...
def test_e2e_architecture_path_write_is_rejected(...): ...
def test_e2e_provider_outage_does_not_block_existing_feedback(...): ...
```

- [ ] **Step 2: Run end-to-end tests RED if any acceptance behavior is still missing**

Run: `python -m pytest tests/media/test_tooling_e2e.py -q`

Expected before final fixes: any uncovered behavior fails for a specific reason; do not weaken the assertion.

- [ ] **Step 3: Make the minimum integration fixes required by the acceptance tests**

Do not add deferred features. Keep all fixes within the approved interfaces and constraints.

- [ ] **Step 4: Update `AGENTS.md` and README documentation**

Document the normal agent path:

```text
read: index/profile -> selected canonical YAML
write: natural language -> typed command JSON -> media operation PR -> trusted Action -> service -> validation/rebuild -> review/merge
```

State explicitly that direct YAML editing is not the normal LLM mutation path once tooling is available, command requests are transient, schema/vocabulary changes remain architectural PRs, and no OpenAI key belongs in Actions.

- [ ] **Step 5: Run the complete local verification set**

Run:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Expected: all tests PASS, validator returns no issues, generated check reports no drift, doctor status is `ok`.

- [ ] **Step 6: Verify deterministic artifacts twice**

Rebuild text artifacts into two separate temporary directories and compare bytes for `index.jsonl` and every generated profile.

Expected: byte-identical outputs.

- [ ] **Step 7: Commit documentation/final acceptance**

```bash
git add media/AGENTS.md media/README.md README.md tests/media/test_tooling_e2e.py
git commit -m "docs: finalize media tooling workflow"
```

- [ ] **Step 8: Final branch review before PR**

Review the branch against the design spec, confirm no deferred scope slipped in, then run the verification set again immediately before opening the implementation PR.
