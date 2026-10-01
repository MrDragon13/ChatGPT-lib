# Media Bulk Metadata Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe, reusable `refresh_metadata(scope=all_movies)` operation and use it to enrich all existing movie works to the current TMDB-backed metadata representation without changing user-owned signals or schema/vocabulary.

**Architecture:** Extend the existing typed-command/service/transaction pipeline instead of adding a second write subsystem. `refresh_metadata` performs a complete provider/identity preflight for every movie, builds one atomic `MutationPlan`, then reuses the existing temp-repo validation/rebuild/rollback machinery. The command is provider-dependent but deliberately excluded from guarded auto-merge; the first real all-movies migration remains a manually reviewed maintenance PR.

**Tech Stack:** Python 3.12, dataclasses, JSON Schema 2020-12, PyYAML, pytest, standard-library HTTP TMDB adapter, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-01-media-bulk-metadata-refresh-design.md`

## Global Constraints

- Git/YAML remains canonical; generated artifacts are derived.
- Initial refresh scope is exactly `all_movies`; series/miniseries are out of scope.
- Existing canonical TMDB identity outranks explicit override; an override may resolve only works without a canonical TMDB ID.
- No identity guessing: zero/multiple candidates or conflicting external IDs fail closed before canonical mutation.
- Preserve immutable work IDs, canonical titles/year/format, all user/group signals, target states, semantic metadata, relations, lists, and `metadata.overrides`.
- Refresh only provider-owned factual metadata; unsupported TMDB genre IDs are omitted and reported, never added to vocabulary implicitly.
- The bulk mutation is all-or-nothing and idempotent by `operation_id`.
- `TMDB_READ_TOKEN` is exposed only to the provider-dependent apply step.
- `refresh_metadata` is never eligible for guarded auto-merge.
- Normal tests use mocked providers and never call live TMDB.

## Review Focus

- **Canonical IMDb resolves to a TMDB result whose IMDb/format/title/year conflicts with the work:** preflight must report a blocker and write nothing. Covered in Task 3.
- **An explicit `tmdb_overrides` entry conflicts with an existing canonical TMDB ID:** reject the command/preflight; never rebind the work. Covered in Task 3.
- **TMDB omits a field that was previously present externally:** conservative merge must avoid destructive erasure unless the field is explicitly treated as authoritative. Covered in Task 3.
- **A refresh changes zero work files:** still produce an idempotent receipt/result without rebuilding or inventing changes. Covered in Task 4.
- **Successful exact-head check fires guarded auto-merge:** `refresh_metadata` must remain rejected by the auto-merge allowlist even though its changed paths resemble ordinary operations. Covered in Task 5.

---

### Task 1: Typed refresh command contract

**Files:**
- Create: `media/commands/schemas/refresh_metadata.schema.json`
- Modify: `media/domain/commands.py`
- Modify: `media/commands/schema.py`
- Test: `tests/media/test_command_contracts.py`

**Interfaces:**
- Consumes: existing canonical UUID validation and command schema loader.
- Produces: `RefreshMetadataCommand(schema_version: int, operation_id: str, scope: Literal["all_movies"], tmdb_overrides: Mapping[str, ProviderWorkRef])` and parser support under operation `refresh_metadata`.

- [ ] **Step 1: Add failing contract tests** for: minimal valid `all_movies`; strict rejection of unknown properties/scope; canonical UUID requirement; override object requiring `media_type: movie` and positive integer `id`; parser returns `RefreshMetadataCommand`.
- [ ] **Step 2: Run** `python -m pytest tests/media/test_command_contracts.py -q` and verify the new tests fail because `refresh_metadata` is unknown.
- [ ] **Step 3: Implement** the dataclass/type alias extension, strict schema, `_SCHEMA_BY_OPERATION` entry, and parse branch. Keep `MediaCommand` inclusive of the new mutable command.
- [ ] **Step 4: Run** `python -m pytest tests/media/test_command_contracts.py -q` and verify PASS.
- [ ] **Step 5: Commit** as `feat: add metadata refresh command contract`.

### Task 2: TMDB lookup and normalization support for refresh

**Files:**
- Modify: `media/providers/base.py`
- Modify: `media/providers/tmdb.py`
- Test: `tests/media/test_add_work.py` or create focused `tests/media/test_tmdb_provider.py`

**Interfaces:**
- Consumes: `ProviderCandidate`, `CanonicalMetadata`, existing TMDB `search_work()` / `fetch_work()`.
- Produces: `MetadataProvider.find_by_imdb(imdb_id: str) -> list[ProviderCandidate]`; `CanonicalMetadata.unmapped_genre_ids: tuple[int, ...] = ()`; TMDB `/find/{imdb_id}` normalization restricted to movie candidates for movie refresh.

- [ ] **Step 1: Add failing provider tests** for IMDb lookup normalization, multiple/no results, and `fetch_work()` reporting unsupported genre IDs while emitting only mapped canonical genre terms.
- [ ] **Step 2: Run** the focused provider tests and confirm RED on missing `find_by_imdb` / unmapped genre reporting.
- [ ] **Step 3: Implement** protocol + TMDB adapter changes using standard-library HTTP and existing `ProviderUnavailableError` wrapping. Do not change existing add-work matching semantics.
- [ ] **Step 4: Run** focused provider tests plus `python -m pytest tests/media/test_add_work.py -q`; verify PASS.
- [ ] **Step 5: Commit** as `feat: support refresh metadata identity lookup`.

### Task 3: Atomic all-movies refresh planner and preflight

**Files:**
- Create: `media/service/refresh.py`
- Modify: `media/domain/errors.py`
- Modify: `media/domain/changeset.py`
- Test: create `tests/media/test_refresh_metadata.py`
- Test support: `tests/media/fixture_repo.py` only if needed for multi-work fixtures.

**Interfaces:**
- Consumes: `YamlRepository.iter_works()`, `RefreshMetadataCommand`, `MetadataProvider.find_by_imdb/search_work/fetch_work`, canonical work mappings.
- Produces: `plan_refresh_metadata(repo: YamlRepository, command: RefreshMetadataCommand, provider: MetadataProvider | None, *, now: datetime | None = None) -> MutationPlan`; an aggregate preflight error carrying structured blockers; `MutationPlan.details` / `OperationResult.details` (optional immutable mapping) for target/change counts and unmapped genre IDs.

- [ ] **Step 1: Add failing planner tests** covering direct canonical TMDB lookup; explicit override before title search; IMDb lookup; exact original-title/year fallback; only `identity.format == movie`; ambiguity/missing/conflicting identity aggregated with zero document plan; provider outage abort; preservation of titles/year/user signals/semantic metadata/manual overrides; non-TMDB metrics preserved; unsupported genres reported; conservative handling of absent provider fields; `updated_at` only on actually changed works.
- [ ] **Step 2: Add a multi-work failing test** proving one unresolved/ambiguous movie prevents every canonical document from being returned for application.
- [ ] **Step 3: Run** `python -m pytest tests/media/test_refresh_metadata.py -q` and verify RED.
- [ ] **Step 4: Implement** focused helpers in `media/service/refresh.py`: target enumeration, candidate resolution, provider/canonical identity compatibility checks, external snapshot merge, per-work document production, and aggregate result details. Keep provider-specific parsing out of this service.
- [ ] **Step 5: Run** `python -m pytest tests/media/test_refresh_metadata.py -q` and verify PASS.
- [ ] **Step 6: Commit** as `feat: plan atomic bulk metadata refresh`.

### Task 4: Transaction, CLI, idempotency, and path policy integration

**Files:**
- Modify: `media/service/transaction.py`
- Modify: `media/service/path_policy.py`
- Modify: `media/cli.py`
- Test: `tests/media/test_cli.py`
- Test: existing transaction/path-policy tests; create `tests/media/test_refresh_transaction.py` if separation is clearer.

**Interfaces:**
- Consumes: `plan_refresh_metadata()` and `RefreshMetadataCommand` from earlier tasks.
- Produces: normal `preview_command()` / `execute_command()` support, provider construction for refresh, receipt persistence/replay of technical `details`, and the same direct-work/generated/profile/receipt path allowlist under operation `refresh_metadata`.

- [ ] **Step 1: Add failing tests** for execute/preview dispatch, provider-required behavior, one atomic multi-work transaction, rollback on validation/sync error, `no_change`, receipt idempotency, details surviving receipt replay, and path-policy allow/reject behavior.
- [ ] **Step 2: Run** focused transaction/CLI/path-policy tests and verify RED.
- [ ] **Step 3: Implement** refresh dispatch in `_plan`, include the new command in mutable types, extend receipt serialization/loading with optional technical details, and mark refresh as provider-dependent in CLI. Keep existing result JSON backward-compatible by adding `details` only when non-empty.
- [ ] **Step 4: Run** focused tests and verify PASS.
- [ ] **Step 5: Commit** as `feat: execute bulk metadata refresh transaction`.

### Task 5: GitHub workflow/security contract and documentation

**Files:**
- Modify: `.github/workflows/media-command.yml`
- Verify/no behavioral expansion: `.github/workflows/media-auto-merge.yml`
- Modify: `media/AGENTS.md`
- Modify: `media/README.md`
- Test: workflow/security contract tests already under `tests/media/` (extend the existing workflow/UX contract file that owns these assertions).

**Interfaces:**
- Consumes: operation name `refresh_metadata` and existing command workflow.
- Produces: `needs_provider=true` for refresh; staged output support through existing directories; exact-head Media Check dispatch unchanged; explicit contract that auto-merge recognizes only `add_work|record_viewing_feedback|set_interest` and therefore rejects refresh.

- [ ] **Step 1: Add failing workflow-contract tests** asserting refresh receives TMDB secret only in the provider-bearing step, command workflow still default-denies architecture paths, and auto-merge has no `refresh_metadata` eligibility branch.
- [ ] **Step 2: Run** the focused workflow contract tests and verify RED only on the new provider-routing/documentation expectations.
- [ ] **Step 3: Update** `media-command.yml` operation inspection so `refresh_metadata` requires provider; update AGENTS/README with maintenance semantics and manual-merge requirement. Do not add refresh to auto-merge.
- [ ] **Step 4: Run** focused workflow/doc tests and verify PASS.
- [ ] **Step 5: Commit** as `ci: support guarded metadata refresh operations`.

### Task 6: Synthetic end-to-end gate and implementation PR

**Files:**
- Test: extend `tests/media/test_refresh_metadata.py` / `test_refresh_transaction.py` with one synthetic end-to-end command fixture.
- No production files unless the end-to-end test exposes a defect.

**Interfaces:**
- Consumes: complete command pipeline from Tasks 1–5.
- Produces: proof that a single typed refresh command enriches multiple synthetic movies, rebuilds derived artifacts, preserves user data, writes one receipt, and is safe on replay.

- [ ] **Step 1: Add/finish the synthetic end-to-end test** using a fake provider with one direct-ID movie, one IMDb-resolved movie, and one title/year movie; assert canonical metadata enrichment, user-data preservation, generated-current state, one receipt, and replay=`already_applied`.
- [ ] **Step 2: Run** `python -m pytest -q` and fix only regressions attributable to this feature until all tests pass.
- [ ] **Step 3: Run full repository gate:** `python -m media.tools.validate .`, `python -m media.cli rebuild --check`, `python -m media.cli doctor --format json`; require all green.
- [ ] **Step 4: Inspect whole-branch diff** for accidental schema/vocabulary/user-data changes and security regressions; request independent review if the runtime supports it.
- [ ] **Step 5: Open the implementation PR** against `main`, require exact-head `Media Check` success, and merge the architectural/implementation PR manually with expected-head protection.

### Task 7: Real all-movies enrichment migration

**Files:**
- Transport only initially: `.media/requests/<operation-id>.json` on a fresh `media/op-*` branch.
- Expected applied diff: many `media/data/works/*.yaml`, `media/generated/index.jsonl`, possibly generated profiles, and one `.media/operations/<operation-id>.json` receipt.

**Interfaces:**
- Consumes: merged v1.3 implementation on current `main`, repository `TMDB_READ_TOKEN`.
- Produces: one manually reviewed bulk maintenance PR with all existing movie works enriched where deterministically resolvable.

- [ ] **Step 1: Create** a fresh `media/op-*` branch from current `main` with exactly one strict `refresh_metadata(scope=all_movies)` request and open its PR.
- [ ] **Step 2: Let `Media Command` run preflight.** If it reports identity blockers, collect the complete blocker set; resolve only from deterministic evidence/candidates and rerun with explicit `tmdb_overrides`. Never guess.
- [ ] **Step 3: When applied, inspect the PR diff** for preservation of IDs/titles/year/user signals/semantic metadata/manual overrides and for expected provider enrichment. Spot-check at least representative old sparse works plus `masters-of-the-universe-2026` for no unintended churn.
- [ ] **Step 4: Require the dispatched exact-head `Media Check` to pass.** Confirm guarded auto-merge did not merge this maintenance PR.
- [ ] **Step 5: Merge the bulk maintenance PR manually** with an expected-head SHA guard.
- [ ] **Step 6: Verify current `main`** with canonical validation, generated-current check, and doctor, and confirm no transient request remains.
- [ ] **Step 7: Report user-facing completion concisely:** all resolvable movies are enriched; mention only unresolved exceptions if any remain.
