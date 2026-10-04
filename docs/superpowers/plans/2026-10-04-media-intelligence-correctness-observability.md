# Media Intelligence Correctness & Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Stage A in two sequential PRs: first establish a reproducible Media Intelligence measurement baseline, then fix recommendation correctness, expose uncertainty/coverage, isolate inferred hypotheses from numeric affinities, surface couple disagreement, and make auto-merge path policy trust-safe.

**Architecture:** PR0 is behavior-neutral: extract shared local-candidate eligibility, add a read-only canonical audit with deterministic content digest, and commit one historical baseline. After PR0 merges, PR1 adds one shared semantic-evidence classifier used by recommendation and assessment, keeps all new observability additive, removes inferred hypotheses from numeric profile aggregation, adds per-term couple signals, and replaces duplicated executable path allowlists with one trusted declarative JSON policy consumed by Python and the privileged workflow.

**Tech Stack:** Python 3.12, stdlib `hashlib/json/pathlib`, PyYAML, pytest, GitHub Actions + `gh`/`jq`, existing YAML/index repositories and media CLI/tooling.

**Spec:** `docs/superpowers/specs/2026-10-04-media-intelligence-correctness-observability-design.md` plus normative amendment `docs/superpowers/specs/2026-10-04-media-intelligence-correctness-observability-amendment.md`.

## Global Constraints

- Merge the current docs-only branch containing the spec, amendment, and this plan before starting PR0; implementation branches start from `main` so product PRs do not accidentally carry unreviewed design commits.
- Delivery is exactly two sequential implementation PRs: **PR0 Measurement foundation**, then **PR1 Intelligence correctness & observability** after PR0 merges.
- PR0 must not change recommendation or assessment ordering/semantics; only shared eligibility extraction, audit, baseline, and measurement-facing CI/docs are allowed.
- No public or pseudo-precise numeric `ranking_score`; the Stage A ordering key is internal policy only.
- Personalized candidates always precede fallback candidates. Personalized ordering is `strengths_count - concerns_count` descending, then concerns ascending, existing interest priority descending, then stable ID ascending. Fallback ordering is priority descending then ID ascending.
- Confidence and affinity magnitude are observability metadata only in Stage A; they do not filter matches or enter ranking.
- Missing semantic evidence is normal data state, not an exception and not a positive signal.
- Inferred hypotheses remain explanation memory and must not change affinity score, confidence, or evidence count.
- Couple term visibility is additive and must not change current couple aggregation/score or remove existing rating-based couple disagreement output.
- `limitations` is top-level sibling metadata, not nested under `coverage` or `assessment_coverage`.
- Stage A does not add a deterministic `assess_candidate` verdict, confidence formula, coverage threshold, semantic backfill, enrichment versioning, MMR, or rating predictor.
- Privileged auto-merge never executes mutable PR-head policy/guard Python. Trusted policy comes from `main` (or another explicitly trusted revision), and changed-file inventory comes from GitHub PR metadata/API; failure to fetch or parse either input fails closed.
- Existing exact-head Media Check, merge-SHA Pages dispatch, Git/YAML canonical ownership, rebuildability, and browser secret boundaries must not regress.
- `fingerprint_trait_count` is recorded/exposed to future evaluation tooling, but Stage A does not normalize the ranking key by fingerprint length.

## Review Focus

1. **Fingerprint richness bias:** a richer fingerprint must not silently trigger an unapproved normalization/coefficient. Task 4 tests that classification records `fingerprint_trait_count` while ranking still uses raw directional counts.
2. **Two assessment denominators:** request-local supporting coverage must remain distinct from stable profile-rated-work coverage. Task 7 creates more rated works than sampled support and asserts both denominators.
3. **Trust boundary failure:** missing/invalid trusted policy or PR-files metadata must make auto-merge ineligible, never permissive. Tasks 9-10 pin trusted `main` policy lookup, PR-files API lookup, and fail-closed behavior.
4. **Fallback advantage:** a candidate with no personalized semantic basis must never outrank any personalized candidate merely because it has no concerns. Task 6 pins personalized-before-fallback ordering.
5. **Audit digest drift:** every input that can change deterministic audit metrics must change `canonical_input_digest`; ordering and unrelated non-input files must not. Task 2 pins both directions.

---

## Delivery structure

- **Documentation prerequisite:** merge `docs/media-intelligence-correctness-observability-design` to `main` after plan review.
- **Stage A / PR0:** Tasks 1-3 on a fresh branch such as `feat/media-intelligence-measurement-foundation` from updated `main`.
- **Merge checkpoint:** PR0 must be green and merged before PR1 starts; the committed baseline is the historical “before” point.
- **Stage A / PR1:** Tasks 4-11 on a fresh branch such as `feat/media-intelligence-correctness-observability` from `main` after PR0 merge.
- **No Stage B work:** evaluation harness/model selection, deterministic assessment verdict, enrichment provenance/versioning, and targeted enrichment are follow-up design cycles.

## File structure locked by this plan

New focused units:

```text
media/
├── baselines/
│   ├── intelligence-stage-a.json
│   └── intelligence-stage-a.meta.json
├── config/
│   └── operation_path_policy.json
├── service/
│   ├── recommendation_pool.py
│   └── semantic_evidence.py
└── tools/
    └── audit_intelligence.py

tests/media/
├── test_recommendation_pool.py
├── test_intelligence_audit.py
└── test_semantic_evidence.py
```

Existing files remain owners of their current responsibilities: `recommend.py` assembles recommendation context, `assessment.py` assembles assessment context, `taste_context.py` assembles taste/couple context, `build_profiles.py` aggregates numeric profile evidence, and `path_policy.py` validates operation paths by reading the declarative policy.

---

# PR0 — Measurement foundation

### Task 1: Extract shared local candidate eligibility without changing behavior

**Files:**
- Create: `media/service/recommendation_pool.py`
- Modify: `media/service/recommend.py` (`build_recommend_context` filtering loop only)
- Create/Test: `tests/media/test_recommendation_pool.py`
- Regression: `tests/media/test_recommend_context.py`

**Interfaces:**
- Produces:
  `eligible_local_candidates(media_root: Path, *, target: str, only_unwatched: bool, include_not_interested: bool, runtime_max: int | None) -> list[dict[str, Any]]`.
- The helper reads `generated/index.jsonl`, validates target through current configured viewers/groups, applies the exact current runtime, interest, and viewer/group watched semantics, preserves index order, and does **not** rank or apply `limit`.
- PR0 canonical pool calls this with `only_unwatched=True`, `include_not_interested=False`, `runtime_max=None`.

- [ ] **Step 1: Write failing parity tests**

```python
def test_eligible_local_candidates_matches_current_primary_filters(tmp_path): ...
def test_eligible_local_candidates_group_excludes_only_when_all_members_watched(tmp_path): ...
def test_eligible_local_candidates_preserves_runtime_and_interest_filters(tmp_path): ...
```

Assert exact IDs against the existing fixture and assert repeated calls preserve order.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_recommendation_pool.py -q`

Expected: FAIL because `media.service.recommendation_pool` does not exist.

- [ ] **Step 3: Implement the helper and replace only the filtering loop in `build_recommend_context()`**

Keep all current ranking/evidence code unchanged in PR0. `build_recommend_context()` must still apply its existing `limit` after existing ordering.

- [ ] **Step 4: Run GREEN + behavior regression**

Run: `python -m pytest tests/media/test_recommendation_pool.py tests/media/test_recommend_context.py -q`

Expected: PASS with no changed existing recommendation expectations.

- [ ] **Step 5: Commit**

```bash
git add media/service/recommendation_pool.py media/service/recommend.py tests/media/test_recommendation_pool.py tests/media/test_recommend_context.py
git commit -m "refactor: share media recommendation eligibility"
```

### Task 2: Add deterministic intelligence audit, input inventory, and content digest

**Files:**
- Create: `media/tools/audit_intelligence.py`
- Create/Test: `tests/media/test_intelligence_audit.py`
- Reuse: `tests/media/fixture_repo.py`
- Reuse: `media/tools/validate.py`, `media/tools/build_profiles.py`, Task 1 pool helper

**Interfaces:**
- Produces:
  - `audit_input_paths(repo_root: Path) -> tuple[Path, ...]`
  - `canonical_input_digest(repo_root: Path) -> str`
  - `collect_intelligence_audit(repo_root: Path) -> dict[str, Any]`
- Digest algorithm is SHA-256 over sorted relative POSIX paths plus file bytes normalized from CRLF to LF; output string is `sha256:<hex>`.
- Input inventory includes every repository input read by the collector or affecting its denominators/eligibility:
  - `media/config/viewers.yaml`
  - `media/config/groups.yaml`
  - `media/vocabulary.yaml`
  - `media/data/works/*.yaml`
  - `media/data/collections/*.yaml`
  - `media/data/relations/similarity/*.yaml`
  - `media/data/interactions/*.jsonl` when present
  - `media/preferences/explicit/*.yaml`
  - `media/preferences/inferred/*.yaml`
- JSON schemas/tool source code are not part of this **data-content** digest; schema/code revision is captured by external git provenance. If implementation makes the collector read any additional config/canonical path, add that path to this inventory in the same commit.
- `collect_intelligence_audit()` calls `validate_repository(repo_root)` first and fails closed if validation returns issues.
- Generated profiles are not metric source-of-truth: derive profile statistics by calling `build_profile(media_root, target)` in memory. Generated index is allowed only for canonical-pool eligibility because that is the runtime derived boundary; its canonical source inputs, not the generated file bytes, are hashed.
- Payload schema version is `1` and includes at minimum:
  - `canonical_input_digest`
  - inventory: works, collections, entities separately
  - vocabulary term count
  - global work fingerprint numerator/denominator
  - per-target viewing/rating counts, rating-source breakdown, feedback coverage
  - per-target derived affinity count/confidence distribution
  - similarity relation count
  - interaction event count/type breakdown
  - per-target canonical recommendation-pool total and fingerprint coverage.
- All coverage uses explicit numerator/denominator fields. Preserve observed rating-source strings under `by_source`; unexpected-but-valid categories go to an explicit `unclassified_*` field rather than disappearing.

- [ ] **Step 1: Write failing metric/digest tests**

```python
def test_audit_separates_works_collections_and_entities(tmp_path): ...
def test_audit_reports_explicit_coverage_numerators_and_denominators(tmp_path): ...
def test_audit_canonical_pool_is_unwatched_unlimited_and_runtime_unfiltered(tmp_path): ...
def test_digest_changes_when_viewers_groups_vocabulary_or_canonical_data_changes(tmp_path): ...
def test_digest_is_stable_under_path_iteration_order_and_unrelated_file_changes(tmp_path): ...
def test_invalid_canonical_state_fails_closed(tmp_path): ...
```

The first test must make `works_total + collections_total == entities_total` explicit so “103 + 4” can never be mislabeled as “107 works”.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_intelligence_audit.py -q`

- [ ] **Step 3: Implement input inventory/digest first** and make only digest tests GREEN.

- [ ] **Step 4: Implement metric collection** using canonical YAML/read helpers, `build_profile()` in memory, and Task 1 eligibility.

- [ ] **Step 5: Run GREEN**

Run: `python -m pytest tests/media/test_intelligence_audit.py tests/media/test_recommendation_pool.py -q`

- [ ] **Step 6: Commit**

```bash
git add media/tools/audit_intelligence.py tests/media/test_intelligence_audit.py
git commit -m "feat: add deterministic media intelligence audit"
```

### Task 3: Add audit CLI, historical baseline, PR0 docs, and merge gate

**Files:**
- Modify: `media/tools/audit_intelligence.py` (`main()` only)
- Create: `media/baselines/intelligence-stage-a.json`
- Create: `media/baselines/intelligence-stage-a.meta.json`
- Modify: `.github/workflows/media-dev-check.yml`
- Modify: `docs/architecture/intelligence.md`
- Modify: `docs/reference/repository-layout.md`
- Modify: `docs/status/current.md`
- Test: `tests/media/test_intelligence_audit.py`
- Test: `tests/media/test_docs.py` if living-doc links/contracts require updates

**Interfaces:**
- CLI: `python -m media.tools.audit_intelligence . --format json` prints only deterministic payload with sorted JSON keys.
- Add `--write-baseline <payload-path> --source-revision <sha> --generated-at <iso8601>`; it writes deterministic payload to the requested file and a sibling `.meta.json` provenance object.
- `intelligence-stage-a.json` contains no wall-clock timestamp or git SHA.
- `intelligence-stage-a.meta.json` contains baseline filename, payload schema version, `canonical_input_digest`, `source_revision`, and `generated_at`.
- The baseline is historical; CI validates format/reproducibility logic but never requires future current counts to equal this snapshot.
- Add `media/baselines/**` to Media Dev Check path triggers so baseline-only maintenance still runs checks.

- [ ] **Step 1: Write failing CLI/baseline tests** asserting byte-identical JSON for identical state and separation of provenance metadata.
- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_intelligence_audit.py -q`

- [ ] **Step 3: Implement CLI/writer and run GREEN.**

- [ ] **Step 4: Generate the real baseline twice and compare**

```bash
python -m media.tools.audit_intelligence . --format json > /tmp/intelligence-audit-1.json
python -m media.tools.audit_intelligence . --format json > /tmp/intelligence-audit-2.json
cmp /tmp/intelligence-audit-1.json /tmp/intelligence-audit-2.json
python -m media.tools.audit_intelligence . --write-baseline media/baselines/intelligence-stage-a.json --source-revision "$(git rev-parse HEAD)" --generated-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Expected: `cmp` succeeds; baseline payload digest matches meta digest.

- [ ] **Step 5: Update living docs** to describe canonical audit/baseline as measurement, not current lockfile.

- [ ] **Step 6: Run full PR0 gate**

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli web-export --output /tmp/media-web-manifest.json --format json
python -m media.cli doctor --format json
```

Expected: all PASS/exit 0; `git diff -- media/generated` is empty.

- [ ] **Step 7: Commit**

```bash
git add media/baselines media/tools/audit_intelligence.py .github/workflows/media-dev-check.yml docs/architecture/intelligence.md docs/reference/repository-layout.md docs/status/current.md tests/media
git commit -m "docs: establish media intelligence baseline"
```

- [ ] **Step 8: Open PR0, obtain review/CI, merge exact green head, and only then create PR1 from updated `main`.**

---

# PR1 — Intelligence correctness & observability

### Task 4: Add one shared semantic-evidence classifier

**Files:**
- Create: `media/service/semantic_evidence.py`
- Create/Test: `tests/media/test_semantic_evidence.py`

**Interfaces:**
- Produces:
  `classify_candidate_traits(traits: Iterable[str], affinities: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]`.
- Returned keys are exact:
  - `fingerprint_trait_count`
  - `strengths: list[str]`
  - `concerns: list[str]`
  - `evidence_details: {strengths: list[dict], concerns: list[dict]}`
  - `strengths_count`
  - `concerns_count`
  - `net_directional_count`
  - `directional_match_count`
  - `ranking_basis: "trait_overlap" | "none"`
  - `fallback_reason: None | "no_semantic_fingerprint" | "no_matching_affinities"`
- A strength is affinity `score > 0`; a concern is `< 0`; zero/missing is unmatched. Do not threshold by confidence.
- Each detail row has `term`, `direction`, `affinity_score`, `confidence`, `evidence_count`.
- `fingerprint_trait_count` is retained for future evaluation/bias analysis but does not normalize any Stage A ranking key.

- [ ] **Step 1: Write failing classifier tests** for positive, negative, zero, no fingerprint, fingerprint-with-no-known-affinity, confidence passthrough, and rich-fingerprint count.
- [ ] **Step 2: Run RED:** `python -m pytest tests/media/test_semantic_evidence.py -q`.
- [ ] **Step 3: Implement pure classifier; no filesystem access.**
- [ ] **Step 4: Run GREEN and commit** `feat: classify media semantic evidence`.

### Task 5: Make inferred hypotheses explanation-only and rebuild profiles

**Files:**
- Modify: `media/tools/build_profiles.py`
- Modify/Test: `tests/media/test_build_profiles.py`
- Expected generated updates: `media/generated/profiles/*.yaml` only where deterministic rebuild changes them

**Interfaces:**
- Remove `_add_inferred(..., bucket, ...)` numeric contribution path.
- Keep `_inferred(media_root, target)` and continue serializing `inferred_preferences` separately in generated profile output.
- Numeric affinities are built only from primary/raw evidence already supported by `build_profile`: feedback, rating-trait evidence, direct group evidence, explicit stable preferences.
- Inferred hypothesis must not change affinity `score`, `confidence`, or `evidence_count`.

- [ ] **Step 1: Write failing isolation test**

```python
def test_inferred_hypothesis_does_not_change_numeric_affinity(tmp_path):
    # build before/after adding a hypothesis over an already evidenced term
    # assert score/confidence/evidence_count identical
    # assert inferred_preferences contains the hypothesis
```

Also add a couple-target case so a member/group profile cannot regress through a separate branch.

- [ ] **Step 2: Run RED:** `python -m pytest tests/media/test_build_profiles.py -q`.
- [ ] **Step 3: Remove numeric inferred aggregation, keep explanation serialization.**
- [ ] **Step 4: Run GREEN, rebuild, inspect expected generated diff**

```bash
python -m media.cli rebuild
python -m media.cli rebuild --check
```

Expected: rebuild check passes; any profile diff is explainable solely by removal of `source_kind: inferred_preference` numeric evidence. Do not hand-edit exact values.

- [ ] **Step 5: Commit** `fix: isolate inferred taste hypotheses` including deterministic generated profile changes.

### Task 6: Implement sign-aware recommendation ranking and observability

**Files:**
- Modify: `media/service/recommend.py`
- Modify/Test: `tests/media/test_recommend_context.py`
- Reuse: `media/service/recommendation_pool.py`, `media/service/semantic_evidence.py`

**Interfaces:**
- Classify every pre-limit eligible candidate before ordering.
- Candidate preserves legacy `evidence.strengths: list[str]` and `evidence.concerns: list[str]`.
- Add `evidence.evidence_details`, root `ranking_basis`, and root `fallback_reason`.
- Internal ordering tuple:
  - personalized: `(0, -net_directional_count, concerns_count, -priority, id)`
  - fallback: `(1, 0, 0, -priority, id)`
- Do not expose `net_directional_count` as a public recommendation score.
- Add top-level `coverage` with exact keys:
  `pool_total`, `pool_with_fingerprint`, `pool_with_personalized_basis`, `pool_fallback`, `returned_total`, `returned_with_fingerprint`, `returned_with_personalized_basis`, `returned_fallback`.
- `pool_*` is after request filters but before ordering/limit; `returned_*` is after ordering/limit.
- Add top-level `limitations` in fixed deterministic order:
  - `partial_semantic_coverage` when `pool_total > 0` and `pool_with_fingerprint < pool_total`
  - `fallback_candidates_present` when `returned_fallback > 0`
  - `no_personalized_candidates` when `pool_total > 0` and `pool_with_personalized_basis == 0`.

- [ ] **Step 1: Write RED ranking tests** proving:
  - `2 strengths / 0 concerns` beats `2 / 1`;
  - `5 / 1` beats `1 / 0` by net count;
  - equal net prefers fewer concerns;
  - adding concern cannot improve rank;
  - adding strength cannot worsen rank;
  - personalized always beats fallback;
  - fallback is priority then ID;
  - repeated call is stable.
- [ ] **Step 2: Write RED observability tests** for evidence details, basis/reason, pool-vs-returned denominators, `limit` not changing `pool_*`, and top-level limitations.
- [ ] **Step 3: Run RED:** `python -m pytest tests/media/test_recommend_context.py -q`.
- [ ] **Step 4: Implement minimal ordering/context changes using Task 4 classifier.**
- [ ] **Step 5: Run GREEN and commit** `fix: make media recommendation ranking sign-aware`.

### Task 7: Add candidate assessment coverage with stable and request-local denominators

**Files:**
- Modify: `media/service/assessment.py`
- Modify: `media/service/taste_context.py` only to expose/reuse a small rated-work helper if needed
- Modify/Test: `tests/media/test_candidate_assessment.py`
- Modify/Test: `tests/media/test_taste_context.py` if helper semantics are promoted
- Reuse: `media/service/semantic_evidence.py`

**Interfaces:**
- Define supporting works exactly as the deduplicated union of canonical work IDs present in `taste_context.recent_feedback` and `taste_context.representative.high/low`; collections and unknown IDs are excluded. Repeated appearances count once.
- Stable profile-rated set is all canonical **works** with a numeric rating relevant to the target, using the same target semantics as current taste context:
  - viewer target: that viewer has numeric rating;
  - group target: any member numeric rating qualifies; if no member rating exists, a direct numeric group rating qualifies.
- Add top-level `assessment_coverage` with exact keys:
  `candidate_has_fingerprint`, `candidate_directional_matches`, `supporting_works_total`, `supporting_works_with_fingerprint`, `profile_rated_works_total`, `profile_rated_works_with_fingerprint`.
- Add top-level `limitations`, not nested. Use fact-only codes:
  - `no_candidate_semantic_fingerprint` when candidate fingerprint is absent/empty;
  - `no_candidate_personalized_basis` when fingerprint exists but directional matches are zero;
  - `partial_semantic_coverage` when either supporting fingerprint coverage or profile-rated fingerprint coverage is incomplete and the corresponding denominator is non-zero.
- External candidate continues to have no fingerprint and no deterministic verdict.

- [ ] **Step 1: Write RED tests** where sampled supporting works are fewer than all rated works; assert both denominators and that changing recent/representative limits can change supporting counts but not profile-rated counts.
- [ ] **Step 2: Add RED tests** for canonical candidate matches, external candidate missing fingerprint, group rated-work semantics, top-level limitations, and filesystem read-only behavior.
- [ ] **Step 3: Run RED:** `python -m pytest tests/media/test_candidate_assessment.py tests/media/test_taste_context.py -q`.
- [ ] **Step 4: Implement small helpers + assessment fields; do not add verdict/scoring.**
- [ ] **Step 5: Run GREEN and commit** `feat: expose candidate assessment coverage`.

### Task 8: Add per-term couple observability without changing aggregation

**Files:**
- Modify: `media/service/taste_context.py`
- Modify/Test: `tests/media/test_taste_context.py`
- Reuse: generated/member profiles and Task 4 sign rule

**Interfaces:**
- For group target, add `couple.term_signals` as a list sorted by term; preserve existing `couple.agreements`/`couple.disagreements` rating-based output unchanged.
- Each term row contains member keys (`primary`, `partner`, or configured group members), each with `direction` (`positive|negative` or absent/null), `confidence`, `evidence_count`, plus `status`.
- `agreement`: all configured members have non-zero directed evidence and all signs equal.
- `disagreement`: all configured members have directed evidence and signs differ.
- `insufficient`: at least one configured member has no directed evidence.
- Confidence never changes status in Stage A.
- For couple context, add `couple_term_disagreement` to top-level `limitations` if any term status is `disagreement`; keep limitations deterministic and deduplicated.
- Existing couple aggregate profile/affinity values must remain byte-for-byte governed by profile rebuild, not this projection.

- [ ] **Step 1: Write RED tests** for agreement, disagreement, insufficient, low-confidence-but-directed, and preservation of existing rating disagreement block.
- [ ] **Step 2: Snapshot/calculate couple profile before context call and assert it is unchanged afterward.**
- [ ] **Step 3: Run RED:** `python -m pytest tests/media/test_taste_context.py -q`.
- [ ] **Step 4: Implement projection only; run GREEN.**
- [ ] **Step 5: Commit** `feat: expose couple term disagreement`.

### Task 9: Replace Python path allowlist constants with one declarative policy

**Files:**
- Create: `media/config/operation_path_policy.json`
- Modify: `media/service/path_policy.py`
- Modify/Test: `tests/media/test_path_policy.py`

**Interfaces:**
- Policy JSON shape:
  `{ "schema_version": 1, "operations": { "<operation>": { "auto_merge": bool, "allowed_paths": [str, ...] } } }`.
- Runtime `allowed_paths_for_operation()` loads this local declarative file; no operation allowlist remains duplicated in Python constants.
- Preserve current runtime scopes except intentionally tighten `set_inferred_preferences` to the actual guarded-auto-merge subset: `media/preferences/inferred/*.yaml`, `media/generated/profiles/*.yaml`, `.media/operations/*.json` — no generated index.
- `refresh_metadata` remains in runtime policy but has `auto_merge: false`.
- Auto-merge true operations/path sets must match the current workflow semantics for `add_work`, `record_viewing_feedback`, `edit_viewing_feedback`, `set_interest`, `set_semantic_fingerprint`, `set_inferred_preferences`, `record_recommendation_interaction`, `set_work_similarity`, and `remove_work_similarity`.
- Missing operation, malformed schema/version, empty allowlist, or unreadable policy fails closed with `PathPolicyError`.

- [ ] **Step 1: Write RED policy-loader tests** for all current operations, `refresh_metadata=false`, tightened inferred path, malformed/missing policy, and explicit rejection of policy/workflow/service/tooling paths.
- [ ] **Step 2: Run RED:** `python -m pytest tests/media/test_path_policy.py -q`.
- [ ] **Step 3: Create JSON policy and refactor Python loader/matcher.**
- [ ] **Step 4: Run GREEN + transaction regressions:** `python -m pytest tests/media/test_path_policy.py tests/media/test_transaction.py -q`.
- [ ] **Step 5: Commit** `refactor: centralize media operation path policy`.

### Task 10: Make privileged auto-merge consume trusted policy and trusted changed-file metadata

**Files:**
- Modify: `.github/workflows/media-auto-merge.yml`
- Modify: `.github/workflows/media-dev-check.yml`
- Modify/Test: `tests/media/test_auto_merge_dispatch_contract.py`
- Modify/Test: `tests/media/test_agent_ux_contract.py` where it currently asserts workflow text
- Modify/Test: `tests/media/test_workflows.py` if existing workflow contracts cover path triggers

**Interfaces:**
- Keep current PR discovery, same-repo/base-main checks, bot-head validation, exact-head Media Check wait, exact-SHA merge, and Pages dispatch.
- Keep changed-file source as GitHub PR metadata API exactly at the trust boundary: `gh api --paginate "repos/$REPO/pulls/$PR_NUMBER/files?per_page=100" --jq '.[].filename'`.
- Fetch policy from trusted main, never PR checkout, via GitHub contents API for `media/config/operation_path_policy.json?ref=main`; decode base64 and parse with `jq`.
- Read the single operation marker from PR head as data; select `operations[$OP_KIND]` from trusted policy.
- Require `auto_merge == true`; every changed path must match one trusted `allowed_paths` pattern; any fetch/decode/schema/operation failure exits non-zero/fails closed.
- Remove duplicated generic/per-operation shell `case` allowlists after trusted JSON enforcement is in place.
- Policy/workflow/guard/executable-code PRs are automatically ineligible because no auto-merge operation allowlist contains those paths; tests must name these protected examples explicitly.
- Add `media/config/operation_path_policy.json` (or narrowly `media/config/**`) to Media Dev Check path triggers so trust-policy changes cannot skip developer CI.

- [ ] **Step 1: Write RED workflow-text/security contracts** asserting trusted `?ref=main` policy fetch, existing PR-files API, `auto_merge` check, fail-closed parsing, and absence of old duplicated operation `case` blocks.
- [ ] **Step 2: Add RED tests** that policy file, workflow file, `media/service/*.py`, `media/tools/*.py`, and guard-test/code paths cannot satisfy any normal operation path set.
- [ ] **Step 3: Run RED:** `python -m pytest tests/media/test_auto_merge_dispatch_contract.py tests/media/test_path_policy.py tests/media/test_agent_ux_contract.py -q`.
- [ ] **Step 4: Refactor workflow and dev-check trigger; run GREEN.**
- [ ] **Step 5: Commit** `security: trust media auto-merge policy from main`.

### Task 11: Update agent/living-doc contracts, verify consumers, and close PR1

**Files:**
- Modify: `media/AGENTS.md`
- Modify: `docs/architecture/intelligence.md`
- Modify: `docs/architecture/write-pipeline.md`
- Modify: `docs/reference/invariants.md`
- Modify: `docs/reference/repository-layout.md`
- Modify: `docs/status/current.md`
- Modify/Test: `tests/media/test_agent_ux_contract.py`
- Modify/Test: `tests/media/test_docs.py`
- Regression: `tests/media/test_web_export.py`

**Interfaces / documentation contract:**
- Agent must surface material active `limitations`; fallback cannot be described as personalized semantic evidence, and partial assessment coverage cannot be described as fully grounded certainty.
- Preserve qualitative assessment/no fake percentage language; Python still does not compute `likely/mixed/unlikely`.
- Document Stage A ranking as deterministic temporary policy, not proven model quality.
- Document inferred hypotheses as explanation-only for numeric aggregation.
- Document `coverage`/`assessment_coverage` and top-level `limitations` placement.
- Document declarative path policy and trusted-main/PR-files API boundary.
- Document baseline paths as historical measurement artifacts.
- Consumer inspection command is mandatory before edits:
  `rg -n "recommend_context|assess_candidate|strengths|concerns|ranking_basis|limitations|assessment_coverage|taste_context" media broker web tests`.
- Expected current architecture: web consumes exported manifest and broker handles typed writes, so no direct `recommend_context`/`assess_candidate` payload consumer should require a breaking migration. If the inspection finds a direct runtime consumer contrary to that expectation, stop implementation and revise this plan/spec before changing its contract.

- [ ] **Step 1: Write RED agent/docs tests** for limitation disclosure, fallback language, partial assessment uncertainty, hypothesis isolation, and trusted policy boundary.
- [ ] **Step 2: Run consumer inspection command and record result in PR notes.**
- [ ] **Step 3: Update living docs/agent contract; do not edit legacy historical status files unless a current doc test specifically requires it.**
- [ ] **Step 4: Run focused GREEN:**

```bash
python -m pytest tests/media/test_agent_ux_contract.py tests/media/test_docs.py tests/media/test_web_export.py -q
```

- [ ] **Step 5: Run final PR1 gate:**

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli web-export --output /tmp/media-web-manifest.json --format json
python -m media.cli doctor --format json
```

Expected: all exit 0; generated artifacts are current; no unexpected canonical data changes.

- [ ] **Step 6: Review generated profile diff** and state explicitly in PR description that any changed profile affinity/confidence is the expected consequence of removing inferred hypothesis evidence, not nondeterministic churn.

- [ ] **Step 7: Whole-branch review against both approved spec files and the Review Focus list. Fix every Critical/Important finding through RED→GREEN before claiming completion.**

- [ ] **Step 8: Commit final docs/contract changes**

```bash
git add media/AGENTS.md docs tests/media/test_agent_ux_contract.py tests/media/test_docs.py
git commit -m "docs: document media intelligence observability"
```

- [ ] **Step 9: Open PR1, require exact-head Media Dev Check, normal human review for all developer/workflow/policy changes, and merge only the verified head.**

---

## Stage A completion evidence

Do not claim Stage A complete until the merged PR1 proves all of the following:

- PR0 baseline exists with deterministic payload and separate provenance metadata.
- Audit can reproduce inventory/coverage metrics without reading generated profiles as truth.
- Negative affinity cannot improve recommendation rank; positive affinity cannot worsen it.
- Personalized candidates precede fallback; fallback is explicitly labeled.
- Recommendation context has separate pre-limit pool and post-limit returned coverage.
- Assessment exposes candidate, request-local supporting, and stable profile-rated semantic coverage without a deterministic verdict.
- Inferred hypotheses remain visible but do not alter numeric affinity score/confidence/evidence count.
- Couple term agreement/disagreement/insufficient is visible without changing couple aggregation.
- `limitations` stays top-level peer metadata in recommendation and assessment contexts.
- One declarative operation path policy drives runtime validation and trusted auto-merge eligibility.
- Privileged workflow reads policy from trusted `main`, changed files from GitHub PR metadata/API, and fails closed when either input is unavailable/invalid.
- Media Dev Check covers policy/baseline paths and the full project gate is green on the exact implementation head.
- Future evaluation has access to `fingerprint_trait_count`, but Stage A contains no fingerprint-length normalization or unbenchmarked weighting formula.
