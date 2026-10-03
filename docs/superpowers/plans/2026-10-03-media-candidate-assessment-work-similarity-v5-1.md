# Media Candidate Assessment & Work Similarity v5.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship first-class explicit work similarity plus read-only candidate assessment so user-declared relationships can improve future recommendations/hints, explanations, and the website without becoming preferences by themselves.

**Architecture:** Store explicit target-specific similarity in a new canonical per-target relation layer under `media/data/relations/similarity/`, with normalized undirected endpoints that may be canonical works or stable external provider identities. Deterministic Python owns validation, upsert/remove, external→canonical reconciliation, read-model projection, and context assembly; the LLM/agent uses those provenance-aware contexts to produce natural-language `likely | mixed | unlikely` assessments rather than a Python scoring engine. Web manifest v3 projects canonical relations symmetrically onto work detail pages.

**Tech Stack:** Python 3, dataclasses, JSON Schema, YAML repository helpers, pytest, GitHub Actions, React + TypeScript + Vite + Vitest/Playwright, existing typed-command broker/CLI and manifest exporter.

**Spec:** `docs/superpowers/specs/2026-10-03-media-candidate-assessment-work-similarity-v5-1-design.md`

## Global Constraints

- Git/YAML remains source of truth; generated/read-model artifacts remain rebuildable.
- Explicit similarity is current user knowledge, target-specific for `primary`, `partner`, or `couple`, and is not a stable preference by itself.
- `A similar B` and `B similar A` are one canonical assertion; no mirrored canonical duplicates.
- Persistent external similarity endpoints require a stable provider identity; title/year are display snapshot only.
- Mentioning an external work in similarity or candidate assessment must not create a canonical library work.
- Existing vocabulary terms may be referenced; unknown terms are rejected rather than created implicitly.
- Repeated similarity upsert replaces `terms`/`note` and updates `updated_at`; remove deletes the current assertion.
- External→canonical reconciliation is deterministic, collision-safe, atomic with `add_work`, and never merges conflicting notes/terms.
- Similarity must be available in taste/recommendation contexts as provenance-aware evidence so it can improve future suggestions/hints, while never creating a preference on its own.
- Candidate assessment is read-only. Python assembles evidence; the agent produces the qualitative verdict/confidence and never persists that prediction as taste evidence.
- Existing exact-head Media Check and guarded auto-merge boundaries must not regress; architecture/schema/service/web changes remain manual-review development changes.
- Browser bundles contain no provider/GitHub/LLM secrets.
- PR #68 must maintain live Development status and append-only checkpoints at plan, RED/GREEN, deviation/blocker, pause, and final verification boundaries.

## Review Focus

1. A canonical work referenced externally (for example by TMDB ID) must normalize to the same endpoint as its `work_id`; tests in Task 2 cover self-links, reverse order, remove, and reconciliation.
2. Reconciliation collisions must choose the current assertion deterministically without silently merging conflicting reasons; tests in Task 2 cover later/equal timestamps and canonical tie-breaks.
3. Similarity must help recommendation/taste hints without being converted into affinity/preference evidence; tests in Task 3 assert context presence and unchanged profile affinities.
4. External similarity endpoints must remain displayable and usable during provider outage; tests in Tasks 1/3/4 build from persisted snapshots without network access.
5. Web projection must be symmetric for canonical↔canonical relations and safe for canonical↔external relations; Python + TypeScript/UI tests in Task 4 pin both cases.

---

### Task 1: Add strict v5.1 command and canonical relation contracts

**Files:**
- Modify: `media/domain/types.py`
- Modify: `media/domain/commands.py`
- Modify: `media/commands/schema.py`
- Modify: `media/commands/schemas/common.schema.json`
- Create: `media/commands/schemas/set_work_similarity.schema.json`
- Create: `media/commands/schemas/remove_work_similarity.schema.json`
- Create: `media/commands/schemas/assess_candidate.schema.json`
- Create: `media/schemas/work-similarity.schema.json`
- Modify: `media/tools/validate.py`
- Test: `tests/media/test_command_contracts.py`
- Test: `tests/media/test_aux_schemas.py`
- Create/Test: `tests/media/test_similarity_validation.py`

**Interfaces:**
- Produce `SetWorkSimilarityCommand(schema_version, operation_id, target, left, right, terms, note)`.
- Produce `RemoveWorkSimilarityCommand(schema_version, operation_id, target, left, right)`.
- Produce read-only `AssessCandidateRequest(schema_version, target, candidate, text)`.
- Reuse `WorkRef` in Python, but add a strict command-schema `$defs/persistentWorkRef` for similarity writes: either canonical `{id}` or external stable TMDB/IMDb identity; title-only is invalid for persistence.
- Canonical file shape: `schema_version: 1`, `target`, `relations[]`; each relation has `type: similar`, normalized `left/right`, `terms`, nullable `note`, `updated_at`, and `provenance.source: explicit`.
- Canonical storage path is `media/data/relations/similarity/<target>.yaml`.

- [ ] **Step 1: Write failing parser/schema tests** for set/remove/assess requests, title-only persistent ref rejection, stable external refs, unknown fields, and read-only request without `operation_id`.
- [ ] **Step 2: Run targeted command/schema tests and verify RED** because operations and relation schema do not exist.
- [ ] **Step 3: Add dataclasses, schemas, parser branches, and read-only union typing** without mutation behavior.
- [ ] **Step 4: Write failing canonical validation tests** for unknown target/work/term, external stable identity, duplicate/reversed pair, malformed order, and self-link.
- [ ] **Step 5: Extend `validate_repository()`** to load relation files, validate target/terms/endpoints, reject duplicate normalized pairs, and validate canonical endpoint refs against works.
- [ ] **Step 6: Run targeted + full pytest and verify GREEN.**
- [ ] **Step 7: Commit** `feat: add work similarity contracts`.

### Task 2: Implement symmetric similarity persistence, reconciliation, and write policy

**Files:**
- Create: `media/service/similarity.py`
- Modify: `media/service/transaction.py`
- Modify: `media/service/path_policy.py`
- Modify: `media/service/enrich.py` only if a small hook is cleaner than transaction composition
- Modify: `.github/workflows/media-command.yml`
- Modify: `.github/workflows/media-auto-merge.yml`
- Test: `tests/media/test_work_similarity.py`
- Test: `tests/media/test_path_policy.py`
- Test: `tests/media/test_workflows.py`
- Test: `tests/media/test_auto_merge_dispatch_contract.py`

**Interfaces:**
- `work_ref_identity(repo: YamlRepository, ref: WorkRef) -> tuple[str, dict]` resolves known external provider refs to canonical works, otherwise returns a stable external identity + snapshot.
- `normalize_similarity_pair(repo, left, right) -> tuple[endpoint, endpoint]` sorts by stable identity key and rejects self-links after resolution.
- `plan_set_work_similarity(repo, command, now=None) -> MutationPlan` upserts exactly one current relation in the target file, replacing `terms`/`note` and setting `updated_at`.
- `plan_remove_work_similarity(repo, command, now=None) -> MutationPlan` removes the current normalized relation and is idempotent when absent.
- `reconcile_similarity_for_new_work(repo, work_document, relation_documents, now=None) -> mapping[path, document]` rewrites matching external endpoints to the new `work_id`, removes self-links caused by identity merge, and applies §8.1 collision policy.
- `add_work` transaction composes relation reconciliation before validation/rebuild; its path policy permits only deterministic changes under `media/data/relations/similarity/*.yaml` in addition to existing add-work paths.
- New set/remove operations may auto-merge only relation canonical files, expected generated outputs (if any), and operation receipts after exact-head Media Check.

- [ ] **Step 1: Write failing mutation tests** for canonical↔canonical, canonical↔external, external↔external, reverse-order equality, repeated upsert replacement, remove, and unknown term/target failures.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement minimal relation loader/identity/normalization and set/remove planners.**
- [ ] **Step 4: Wire commands through transaction and operation-scoped path policy; run targeted tests GREEN.**
- [ ] **Step 5: Write failing reconciliation tests** for external→canonical rewrite, no duplicate, self-link removal, newer assertion wins, identical collision dedupe, equal-time canonical/lexical tie-break, and atomic rollback on validation failure.
- [ ] **Step 6: Compose reconciliation into `add_work` and make the tests GREEN.**
- [ ] **Step 7: Write workflow/path-policy contract tests** proving only the two new data operations gain guarded auto-merge eligibility and `add_work` gains relation-path allowance only for reconciliation.
- [ ] **Step 8: Update workflows/path policy and run targeted + full pytest GREEN.**
- [ ] **Step 9: Commit** `feat: persist explicit work similarity`.

### Task 3: Feed similarity into suggestions and add read-only candidate assessment context

**Files:**
- Modify: `media/service/taste_context.py`
- Modify: `media/service/recommend.py`
- Create: `media/service/assessment.py`
- Modify: `media/cli.py`
- Test: `tests/media/test_taste_context.py`
- Test: `tests/media/test_recommend.py`
- Create/Test: `tests/media/test_candidate_assessment.py`
- Modify/Test: `tests/media/test_cli.py`

**Interfaces:**
- `similarity_context(media_root, target) -> list[dict]` returns compact explicit relations with provenance, terms/note, endpoint snapshots, and canonical IDs where available.
- `build_taste_context()` adds `similarities` as a separate evidence collection; it does not write or alter `profile.affinities`/preferences.
- `build_recommend_context()` adds candidate-level `evidence.similarities` for local candidates connected to explicitly similar known works, so future hints/recommendations can use the user's own cross-work anchors.
- `build_candidate_assessment_context(media_root, request) -> dict` returns target, request text, normalized candidate view, compact taste context, candidate semantic fingerprint when canonical, and explicit similarities touching that candidate. It performs no write and no deterministic recommendation score.
- CLI adds `assess-candidate --request ... --format ...`; `apply-command` rejects `AssessCandidateRequest` as read-only.
- Agent-facing docs in Task 5 require the LLM response to map this context to `likely | mixed | unlikely` plus `low | medium | high` confidence, positive reasons, risks, and provenance-aware evidence, without percentages.

- [ ] **Step 1: Write failing taste/recommend tests** proving explicit similarity is present as separate evidence and can appear in candidate hints while profile affinity output remains unchanged.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Add relation read helpers and integrate taste/recommend contexts; run targeted tests GREEN.**
- [ ] **Step 4: Write failing assessment/CLI tests** for canonical candidate, stable external candidate, target validation, similarity evidence, absent fingerprint, and no filesystem mutation.
- [ ] **Step 5: Implement `assessment.py` and CLI routing; run targeted tests GREEN.**
- [ ] **Step 6: Run full pytest and `python -m media.cli rebuild --check`; verify GREEN.**
- [ ] **Step 7: Commit** `feat: use similarity in recommendation context`.

### Task 4: Export manifest v3 and render explicit similarity on both work pages

**Files:**
- Modify: `media/service/web_export.py`
- Modify: `media/schemas/web-manifest.schema.json`
- Modify: `tests/media/test_web_export.py`
- Modify: `web/src/data/types.ts`
- Modify: `web/src/features/detail/WorkDetailPage.tsx`
- Modify: `web/src/features/detail/intelligence.css` and/or `detail.css`
- Modify: `web/src/features/detail/detail-intelligence.test.tsx`
- Modify: other manifest compatibility tests under `web/src/test/` as discovered

**Interfaces:**
- `WEB_MANIFEST_SCHEMA_VERSION = 3`; frontend may continue accepting v2 during static deploy overlap.
- Each `WebWork` gets target-keyed `similarities`, projected symmetrically from one canonical relation.
- A similarity item contains the other endpoint display identity, canonical `id` when available, stable external identity when not, `terms`, nullable `note`, `updated_at`, and explicit provenance.
- canonical↔canonical appears on both pages; canonical↔external appears on the canonical page as a lightweight non-library card and does not fabricate a local route.
- Work detail shows `Похожие фильмы` → `По твоему мнению` for the active target. No derived-similarity section is rendered until a real derived source exists.

- [ ] **Step 1: Write failing Python manifest tests** for v3 schema, symmetric canonical projection, external lightweight endpoint, target filtering, and empty relation fallback.
- [ ] **Step 2: Run Python tests and verify RED.**
- [ ] **Step 3: Implement exporter/schema projection and run Python tests GREEN.**
- [ ] **Step 4: Write failing TypeScript/UI tests** for active-target similarity, reverse page visibility, external card without local link, note/term labels, and no block when empty.
- [ ] **Step 5: Update TS types/UI/styles and make unit tests GREEN.**
- [ ] **Step 6: Run web unit tests, typecheck, production build, and existing browser/review checks.**
- [ ] **Step 7: Commit** `feat: show explicit work similarity on web`.

### Task 5: Update agent contracts, scenario catalog, status, and continuity checkpoints

**Files:**
- Modify: `media/AGENTS.md`
- Modify: `media/START_PROMPT.md` only if a compact user-facing route needs mention
- Modify: `media/README.md`
- Modify: `media/V5_STATUS.md`
- Modify: `docs/superpowers/specs/2026-10-03-media-v5-agent-scenario-catalog.md`
- Modify: `docs/superpowers/specs/2026-10-03-media-candidate-assessment-work-similarity-v5-1-design.md` only for implementation-discovered clarifications consistent with approved intent
- Test: `tests/media/test_agent_ux_contract.py`
- Test: `tests/media/test_docs.py`

**Interfaces:**
- Intent router gains explicit `similarity` write/remove and read-only `assess candidate` routes.
- Recommendation guidance explicitly says user-declared similarity is a provenance-aware hint/anchor for future suggestions and explanations, never a preference by itself.
- Agent may ask at most one blocking clarification for ambiguous identity; otherwise it chooses the best route without infrastructure narration.
- External candidate assessment and external similarity endpoints do not create library works.
- PR #68 body remains a live status snapshot; append-only comments record Task-level RED/GREEN and resume instructions.

- [ ] **Step 1: Write failing docs/agent contract tests** for new intents, symmetry, external-work semantics, suggestion/hint use, and qualitative assessment wording.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Update current contracts/status/scenarios; keep `START_PROMPT.md` concise.**
- [ ] **Step 4: Run targeted + full pytest GREEN.**
- [ ] **Step 5: Commit** `docs: document media v5.1 similarity routes`.

### Task 6: Exact-head integration verification and PR handoff

**Files:**
- No new product scope; fixes only for failures found by verification.
- Update PR #68 body/comments with exact head, checks, deviations, and resume instructions.

**Interfaces:**
- Required repository verification: `python -m pytest -q`, `python -m media.tools.validate .`, `python -m media.cli rebuild --check`, `python -m media.cli doctor --format json`.
- Required web verification: existing Web Check suite including unit tests, TypeScript typecheck, production build, secret scan, responsive/motion/accessibility/browser checks, and review screenshots.
- Media Dev Check and Web Check must both pass on the same final head SHA before PR is marked ready.
- No sample user similarity is written merely to demonstrate the feature; real similarity data is added later only through the normal typed operation after the architecture is merged.

- [ ] **Step 1: Run/observe exact-head Media Dev Check and Web Check on the final implementation head.**
- [ ] **Step 2: If a check fails, use systematic debugging, add a regression test, fix minimally, and rerun on the new exact head.**
- [ ] **Step 3: Perform whole-branch review against the spec, plan, path policies, and secret boundaries.**
- [ ] **Step 4: Update `media/V5_STATUS.md` and PR #68 final Development status with verification evidence and safe resume instructions.**
- [ ] **Step 5: Mark PR ready for review only when exact-head checks are green.**
