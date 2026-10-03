# Media Intelligence v5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Media Intelligence v5 end-to-end: richer feedback lifecycle, semantic film knowledge, evidence-based taste learning, compact LLM context, external-recommendation routing, agent contracts, and website intelligence UI while keeping Git/YAML deterministic and reproducible.

**Architecture:** Keep canonical user/work data under `media/`, add typed commands for corrections, inferred preferences, semantic enrichment, and recommendation interactions, then rebuild all derived profiles/context deterministically. LLMs create semantic/inferred payloads and do external discovery, but Python validates, stores, aggregates, and exports them. The website consumes the same derived intelligence through manifest v2; live model credentials remain outside the browser.

**Tech Stack:** Python 3, dataclasses, JSON Schema, YAML repositories, pytest, GitHub Actions, React + TypeScript + Vite + Vitest/Playwright, existing broker/typed-command pipeline.

**Spec:** `docs/superpowers/specs/2026-10-03-media-intelligence-recommendation-v5-design.md` plus the web/agent, scenario-catalog, and development-continuity amendments dated 2026-10-03.

## Global Constraints

- Git/YAML remains source of truth; all generated artifacts must be rebuildable.
- LLMs never patch canonical/generated YAML directly for normal user operations.
- Explicit user evidence outranks repeated correlations, which outrank single-rating inference.
- Film semantic fingerprint describes the work, never viewer reaction.
- Rating-derived taste evidence is weak, cannot create high-confidence preference by itself, and cannot self-reinforce through prior inferred output.
- Genres/profile are soft priors unless the user states a hard constraint.
- Unknown is better than guessed; new vocabulary terms require separate vocabulary maintenance.
- Existing exact-head `workflow_dispatch` Media Check and guarded auto-merge path must not regress.
- Browser bundles must not contain GitHub/provider/LLM secrets.
- Each implementation PR maintains the Development Continuity Contract in its body/comments.

## Review Focus

1. A high rating on one film must not turn every film trait into a strong preference; tests pin weak weighting and multi-work confidence thresholds in Task 4.
2. Clearing one feedback component must preserve other current components and append history; tests pin this in Task 2.
3. Reanalysis payloads must not cite inferred preferences as independent evidence or unknown works/terms; tests pin this in Task 5.
4. `couple` context must expose agreement/disagreement without silently averaging conflicting viewers; tests pin this in Task 6.
5. Website manifest/UI must remain usable when inferred preferences/fingerprints are absent; tests pin graceful fallbacks in Tasks 9-10.

---

## Delivery structure

v5 ships as independently mergeable PR phases. Each phase leaves `main` green and becomes the base for the next.

- **Phase A / PR 1 — Core mutation & taste evidence:** Tasks 1-4.
- **Phase B / PR 2 — Inferred intelligence & compact context:** Tasks 5-7.
- **Phase C / PR 3 — Agent routes + interaction memory:** Task 8.
- **Phase D / PR 4 — Web intelligence parity:** Tasks 9-10.
- **Phase E / PR 5 — Pilot data, end-to-end verification, docs:** Tasks 11-12.

## Task 1: Extend typed command/domain primitives

**Files:**
- Modify: `media/domain/commands.py`
- Modify: `media/domain/types.py`
- Modify: `media/commands/schema.py`
- Create: `media/commands/schemas/edit_viewing_feedback.schema.json`
- Create: `media/commands/schemas/set_inferred_preferences.schema.json`
- Create: `media/commands/schemas/set_semantic_fingerprint.schema.json`
- Create: `media/commands/schemas/record_recommendation_interaction.schema.json`
- Create: `media/schemas/inferred-preferences.schema.json`
- Test: `tests/media/test_command_contracts.py`
- Test: `tests/media/test_aux_schemas.py`

**Interfaces:**
- Produces `EditViewingFeedbackCommand`, `SetInferredPreferencesCommand`, `SetSemanticFingerprintCommand`, `RecordRecommendationInteractionCommand` parsed by `parse_command()`.
- `EditViewingFeedbackCommand` uses explicit `set` and `clear` fields; absence never means deletion.
- `SetInferredPreferencesCommand` carries target plus complete replacement hypotheses with evidence pointers.
- `SetSemanticFingerprintCommand` carries work ref plus complete semantic traits using existing vocabulary IDs.
- `RecordRecommendationInteractionCommand` carries target, recommendation session id, work identity/title, event type, optional note/timestamp.

- [ ] **Step 1: Write failing parser/schema tests** for valid/invalid examples, including explicit clear semantics, unknown fields rejection, canonical UUID enforcement, and inferred evidence structure.
- [ ] **Step 2: Run targeted tests and verify RED** with unknown operations/schemas.
- [ ] **Step 3: Add dataclasses, JSON schemas, and parser branches** with no service behavior yet.
- [ ] **Step 4: Run targeted tests and full pytest; verify GREEN.**
- [ ] **Step 5: Commit** `feat: add v5 media intelligence command contracts`.

## Task 2: Implement feedback correction, clear, and purge-safe semantics

**Files:**
- Modify: `media/service/mutate.py`
- Modify: `media/service/transaction.py`
- Modify: `media/service/path_policy.py`
- Test: `tests/media/test_mutations.py` (or existing feedback mutation test file)
- Test: `tests/media/test_path_policy.py`

**Interfaces:**
- Produces `plan_edit_viewing_feedback(repo, command, now=None) -> MutationPlan`.
- `set` replaces only named current components; `clear` removes only named current components.
- Every actual change appends one history entry containing previous/current state; clearing uses an explicit history note/current-null representation rather than erasing history.
- Clearing the final current component may leave `history`; a dedicated explicit purge flag/operation may remove the target signal container only when requested by the command schema.

- [ ] **Step 1: Write failing tests** for re-rating, clear-rating-preserves-feedback, clear-feedback-preserves-rating, no-op clear, wrong target, and explicit purge behavior.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement minimal mutation planner and transaction dispatch/path policy.**
- [ ] **Step 4: Run targeted + full pytest; verify GREEN.**
- [ ] **Step 5: Commit** `feat: add safe feedback correction and clearing`.

## Task 3: Persist semantic fingerprints independently of viewer taste

**Files:**
- Modify: `media/service/mutate.py` or create `media/service/intelligence.py`
- Modify: `media/service/transaction.py`
- Modify: `media/service/path_policy.py`
- Modify: `media/tools/validate.py` only if cross-field validation is needed
- Test: `tests/media/test_semantic_fingerprint.py`

**Interfaces:**
- Produces `plan_set_semantic_fingerprint(repo, command, now=None) -> MutationPlan`.
- Writes only `metadata.semantic.traits` on the resolved work.
- Rejects vocabulary terms of `kind: reaction` for film fingerprint and rejects unknown terms.
- Preserves external metadata, viewer/group signals, and manual metadata overrides.

- [ ] **Step 1: Write failing tests** for valid trait replacement, reaction-term rejection, unknown-term rejection, and preservation of viewer data.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement vocabulary-aware fingerprint planner and transaction wiring.**
- [ ] **Step 4: Run targeted + full pytest; verify GREEN.**
- [ ] **Step 5: Commit** `feat: add semantic film fingerprints`.

## Task 4: Make ratings weak deterministic taste evidence

**Files:**
- Modify: `media/tools/build_profiles.py`
- Test: `tests/media/test_build_profiles.py`

**Interfaces:**
- Add rating-derived evidence items with `source_kind: rating_trait`, `entity_id`, `source_target`, `term`, rating score, trait confidence, signed value, and weight.
- Rating contribution uses only film semantic traits and never reaction-kind terms.
- Rating signal is centered around a neutral band and has lower maximum weight than explicit feedback.
- Confidence remains evidence-weight based; one rating-derived item cannot reach `high` confidence.

- [ ] **Step 1: Write failing profile tests** proving high/low rating weakly changes affinity, neutral ratings contribute near zero, explicit feedback dominates, and repeated independent works can strengthen confidence.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement the smallest deterministic rating-to-trait contribution helper.**
- [ ] **Step 4: Run targeted + full pytest + rebuild check; verify GREEN.**
- [ ] **Step 5: Commit** `feat: learn weak taste evidence from ratings`.

## Task 5: Add canonical inferred preferences and reanalysis write path

**Files:**
- Create: `media/service/preferences.py`
- Modify: `media/service/transaction.py`
- Modify: `media/service/path_policy.py`
- Modify: `media/tools/build_profiles.py`
- Modify: `media/repository/yaml_repo.py` if repository helpers are needed
- Create canonical seed files under `media/preferences/inferred/` only when produced by the pilot operation, not as empty placeholders unless schema/tests require them
- Test: `tests/media/test_inferred_preferences.py`
- Test: `tests/media/test_build_profiles.py`

**Interfaces:**
- Produces `plan_set_inferred_preferences(repo, command, now=None) -> MutationPlan`.
- Complete replacement semantics per target, validated against `inferred-preferences.schema.json`.
- Evidence pointers may reference canonical works and explicit/raw signal kinds; inferred-preference IDs cannot be used as independent supporting evidence.
- `build_profile()` merges inferred hypotheses as lower-weight preference evidence while exposing them separately in generated profile output.

- [ ] **Step 1: Write failing tests** for valid replacement, unknown target/work/term rejection, self-reference rejection, removal of stale hypotheses, and profile aggregation.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement canonical writer, validation, path policy, and profile aggregation.**
- [ ] **Step 4: Run targeted + full pytest + doctor/rebuild check; verify GREEN.**
- [ ] **Step 5: Commit** `feat: add evidence-backed inferred preferences`.

## Task 6: Build compact taste context for LLM recommendations

**Files:**
- Create: `media/service/taste_context.py`
- Create: `media/commands/schemas/taste_context.schema.json`
- Modify: `media/domain/commands.py`
- Modify: `media/commands/schema.py`
- Modify: `media/cli.py`
- Test: `tests/media/test_taste_context.py`
- Test: `tests/media/test_cli.py`

**Interfaces:**
- Produces read-only `TasteContextRequest(target, recent_limit, representative_limit)` and `build_taste_context(media_root, request) -> dict`.
- Output includes explicit preferences/rules/constraints, stable inferred preferences, strongest affinities with evidence, representative high/low-rated works, recent meaningful feedback, exclusions (`watched`, `not_interested`), and for groups agreement/disagreement summaries.
- No persistent write occurs.

- [ ] **Step 1: Write failing tests** for primary, partner, couple disagreement, missing inferred files, representative limits, and read-only CLI behavior.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement context service/schema/parser/CLI.**
- [ ] **Step 4: Run targeted + full pytest; verify GREEN.**
- [ ] **Step 5: Commit** `feat: add compact taste context`.

## Task 7: Record recommendation interactions without corrupting stable taste

**Files:**
- Create: `media/service/interactions.py`
- Modify: `media/service/transaction.py`
- Modify: `media/service/path_policy.py`
- Modify: `media/tools/build_profiles.py` only for non-preference counters unless explicitly justified
- Test: `tests/media/test_recommendation_interactions.py`

**Interfaces:**
- Writes append-only `media/data/interactions/YYYY-MM.jsonl` events.
- Supported event types include at least `recommended`, `selected`, `already_watched`, `not_tonight`, `not_interested`.
- `not_tonight` never becomes a stable preference or `not_interested` state automatically.
- Duplicate operation receipt keeps command idempotent.

- [ ] **Step 1: Write failing tests** for append-only event storage, idempotency, `not_tonight` non-persistence, and path policy.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement interaction planner/write path.**
- [ ] **Step 4: Run targeted + full pytest; verify GREEN.**
- [ ] **Step 5: Commit** `feat: record recommendation interactions`.

## Task 8: Upgrade AGENTS/START_PROMPT/README and workflow eligibility contracts

**Files:**
- Modify: `media/AGENTS.md`
- Modify: `media/START_PROMPT.md`
- Modify: `media/README.md`
- Modify: `.github/workflows/media-command.yml`
- Modify: `.github/workflows/media-auto-merge.yml` if allowed-path/operation logic is explicit there
- Modify: tests under `tests/media/test_agent_ux_contract.py`, `test_docs.py`, `test_auto_merge_dispatch_contract.py`, `test_workflows.py`

**Interfaces:**
- Agent intent router covers read/record/correct/clear/purge/interest/internal-recommend/external-recommend/explain/reanalyze/enrich/maintenance.
- Current Media Check path is documented as dispatch-only.
- New normal data commands remain eligible for guarded auto-merge only when changed paths are in their explicit policy; architecture/vocabulary/schema changes never auto-merge as media operations.
- `START_PROMPT.md` stays compact and delegates technical details to `AGENTS.md`.

- [ ] **Step 1: Write failing contract tests** for required v5 routes/text and workflow command acceptance.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Update docs/workflow contracts.**
- [ ] **Step 4: Run targeted + full pytest; verify GREEN.**
- [ ] **Step 5: Commit** `docs: upgrade media agents to v5 routes`.

## Task 9: Export web manifest v2 intelligence data

**Files:**
- Modify: `media/service/web_export.py`
- Modify/Create: `media/schemas/web-manifest.schema.json`
- Test: `tests/media/test_web_export.py`
- Modify: `web/src/data/types.ts`
- Test: relevant TypeScript manifest tests

**Interfaces:**
- `WEB_MANIFEST_SCHEMA_VERSION = 2`.
- Export per-work semantic fingerprint, target inferred preferences, explainable profile evidence, and compact target taste summaries without secrets.
- Missing optional intelligence layers serialize as empty arrays/maps, not export failure.

- [ ] **Step 1: Write failing Python + TS contract tests** for v2 shape and v1-data fallback behavior.
- [ ] **Step 2: Run tests and verify RED.**
- [ ] **Step 3: Implement exporter/schema/types.**
- [ ] **Step 4: Run pytest + web unit/typecheck/build; verify GREEN.**
- [ ] **Step 5: Commit** `feat: export media intelligence manifest v2`.

## Task 10: Add website Intelligence UI

**Files:**
- Modify: `web/src/app/*` routing/navigation as needed
- Create: `web/src/features/taste/*`
- Modify: `web/src/features/work-detail/*`
- Modify: `web/src/styles/*`
- Test: `web/src/test/*` and browser checks

**Interfaces:**
- New `Мой вкус` surface for current target showing explicit vs inferred hypotheses, confidence, and evidence works.
- Work detail shows film fingerprint separately from personal reactions.
- `Почему система так думает?` expands evidence rather than displaying an opaque score.
- Couple surface shows agreements/disagreements; unknown/insufficient data is neutral.
- No browser-side LLM credentials or direct AI calls.

- [ ] **Step 1: Write failing unit/browser tests** for taste navigation, inferred evidence rendering, fingerprint separation, couple disagreement, and empty-state fallback.
- [ ] **Step 2: Run tests and verify RED.**
- [ ] **Step 3: Implement minimal UI following existing cinematic design system.**
- [ ] **Step 4: Run unit/typecheck/build/browser/screenshot checks; verify GREEN.**
- [ ] **Step 5: Commit** `feat: add explainable taste intelligence UI`.

## Task 11: Run v5 pilot enrichment and profile reanalysis

**Files:**
- Canonical data changes only through new typed operations on `media/op-*` branches.
- Generated profiles/index rebuilt by service.

**Interfaces:**
- Select a representative pilot set spanning high/low ratings and multiple genres, enrich fingerprints using existing vocabulary, then generate evidence-backed inferred preferences for `primary`, `partner`, and `couple` only where evidence is sufficient.
- Do not fabricate partner signals or fill missing semantic traits merely for completeness.

- [ ] **Step 1: Produce pilot semantic-fingerprint commands** for a representative set and apply through normal pipeline.
- [ ] **Step 2: Verify exact-head Media Check + auto-merge + Pages for each logical operation/batch allowed by command semantics.**
- [ ] **Step 3: Build current taste contexts and have LLM produce inferred-preference replacement commands with evidence.**
- [ ] **Step 4: Apply and verify profile rebuilds; inspect for implausible overconfidence/self-reinforcement.**
- [ ] **Step 5: Record checkpoint with resulting profile summary and known limitations.**

## Task 12: End-to-end external recommendation pilot and final v5 verification

**Files:**
- Modify docs only if pilot exposes routing gaps.
- No persistent recommendation preference writes unless user interaction warrants them.

**Interfaces:**
- General recommendation request uses taste context + concrete liked/disliked anchors + external web/provider discovery; local library is exclusion/memory, not candidate boundary.
- Internal-library request remains internal-only.
- Recommendation output includes explainable rationale and at least one exploration candidate when appropriate.

- [ ] **Step 1: Run an internal-only recommendation smoke test** and confirm candidates come only from local index.
- [ ] **Step 2: Run an external-discovery pilot** using fresh web/provider facts; exclude watched/not-interested works.
- [ ] **Step 3: Verify agent route can explain why each candidate fits using evidence without claiming inferred facts as explicit user statements.**
- [ ] **Step 4: Run final full verification:** `python -m pytest -q`, media validate, rebuild check, doctor, web tests, typecheck, production build, browser checks, static scan, workflow-contract tests.
- [ ] **Step 5: Perform whole-branch/spec review, fix Critical/Important findings through RED→GREEN, and merge final PR after fresh checks.**
- [ ] **Step 6: Confirm post-merge Pages deployment and finalize continuity handoff with v5 pilot status / v6 candidates.**
