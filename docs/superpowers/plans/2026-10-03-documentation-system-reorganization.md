# Documentation System Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize ChatGPT-lib documentation into a small authoritative living-docs layer with clear human/agent entry points, historical-spec boundaries, durable status, and executable drift-prevention tests without changing runtime media behavior.

**Architecture:** Keep existing historical `docs/superpowers/specs/` and `plans/` paths intact, add focused living docs under `docs/architecture`, `docs/guides`, `docs/reference`, and `docs/status`, then turn root/media entry documents into concise routers. Documentation contracts will validate structure, local links, operation-catalog synchronization, manifest-version synchronization, CLI/runbook reality, and status durability.

**Tech Stack:** Markdown, Python 3, pytest, existing media command registry/schema layer, existing web manifest exporter, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-03-documentation-system-reorganization-design.md`

## Global Constraints

- Do not change runtime media behavior, schemas, canonical data, recommendation semantics, or website behavior.
- Keep `docs/superpowers/specs/` and `docs/superpowers/plans/` at their existing paths as historical rationale.
- Preserve compatibility entry paths: `README.md`, `AGENTS.md`, `media/README.md`, `media/AGENTS.md`, `media/START_PROMPT.md`, `media/V5_STATUS.md`.
- Human-facing living docs and root/media README prose are primarily Russian; technical identifiers remain in their canonical English spelling.
- Root and media `AGENTS.md` remain normative operating contracts; living docs explain but do not weaken imperative guardrails.
- `PRODUCT.md` and `DESIGN.md` remain at repository root and are explicitly scoped to media-web.
- `docs/status/current.md` is durable current state, not a PR/task ledger.
- Similarity is documented as recommendation/explanation evidence, never as a preference by itself; candidate assessment remains qualitative/read-only.
- All implementation work stays in PR #70 with durable checkpoints in PR comments/body.

## Review Focus

- **Guardrail loss:** shortening `media/AGENTS.md` must not remove intent routing, evidence hygiene, no-direct-YAML rules, target safety, or verification/merge discipline; pin these phrases/behaviors in `tests/media/test_agent_ux_contract.py`.
- **False authority:** dated Superpowers specs must not be presented as current architecture from root/media landing pages; pin the boundary in `tests/media/test_documentation_system.py`.
- **Reference drift:** `reference/media-commands.md` must stay synchronized with `media.commands.schema._SCHEMA_BY_OPERATION`, including read-only operations; pin exact set equality.
- **Version drift:** `architecture/web-and-broker.md` must document the same current manifest version as `WEB_MANIFEST_SCHEMA_VERSION`; pin it directly.
- **Status decay / broken navigation:** living-doc relative links must resolve and `docs/status/current.md` must reject transient branch/task/run markers; pin both structurally rather than with prose snapshots.

---

## File Structure

**Create:**
- `docs/README.md` — documentation map, authority model, update matrix entry point.
- `docs/architecture/overview.md` — system-level component and boundary overview.
- `docs/architecture/media-model.md` — canonical/derived media domain model.
- `docs/architecture/intelligence.md` — taste/recommendation/assessment semantics.
- `docs/architecture/write-pipeline.md` — deterministic mutation and CI lifecycle.
- `docs/architecture/web-and-broker.md` — manifest/Pages/broker/security boundaries.
- `docs/guides/media-usage.md` — human-facing media workflows.
- `docs/guides/development.md` — developer workflow and documentation ownership.
- `docs/guides/operations.md` — validation/rebuild/doctor/deploy/recovery runbook.
- `docs/reference/media-commands.md` — compact operation catalog.
- `docs/reference/repository-layout.md` — path ownership map.
- `docs/reference/invariants.md` — cross-system MUST/MUST NOT rules.
- `docs/reference/terminology.md` — stable vocabulary for docs/reviews/agents.
- `docs/status/current.md` — durable current capability/limitations summary.
- `tests/media/test_documentation_system.py` — structural/drift documentation contracts.

**Modify:**
- `README.md` — short project landing page and human navigation.
- `AGENTS.md` — compact repository-level router to normative/media/living docs.
- `media/README.md` — subsystem landing page and minimal quickstart.
- `media/AGENTS.md` — retain normative rules, replace safe explanatory duplication with living-doc links.
- `media/START_PROMPT.md` — remove mandatory historical-status bootstrap while preserving human-first behavior.
- `media/V5_STATUS.md` — compatibility router to durable current status.
- `PRODUCT.md` — mark scope as media-web product brief.
- `DESIGN.md` — mark scope as media-web design-system contract.
- `tests/media/test_docs.py` — move old monolithic README/status assertions to living-doc ownership.
- `tests/media/test_agent_ux_contract.py` — preserve agent/user UX guardrails while updating bootstrap expectations.

---

### Task 1: Documentation navigation foundation

**Files:**
- Create: `tests/media/test_documentation_system.py`
- Create: `docs/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: repository paths and Markdown files only.
- Produces: a stable human documentation entry point and reusable test helpers `_text(path)` plus `_local_markdown_targets(path)` for later tasks.

- [ ] **Step 1: Write failing navigation tests**

Add tests named:

```python
def test_root_readme_routes_to_documentation_usage_development_and_architecture(): ...
def test_docs_index_separates_living_agent_and_historical_layers(): ...
def test_root_readme_does_not_publish_dated_specs_as_current_architecture(): ...
```

Assertions must require links to `docs/README.md`, `docs/guides/media-usage.md`, `docs/guides/development.md`, and `docs/architecture/overview.md`; require `docs/README.md` to identify `AGENTS.md`/`media/AGENTS.md` as operating contracts and `docs/superpowers/` as historical rationale; reject a root section that labels dated specs as current architecture.

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `python -m pytest tests/media/test_documentation_system.py -q`

Expected: FAIL because `docs/README.md` and new navigation links do not yet exist.

- [ ] **Step 3: Implement the navigation layer**

Write `docs/README.md` in Russian with four reader routes, the three authority categories (implemented behavior, agent policy, historical rationale), the language policy, and the update-matrix concept. Rewrite root `README.md` as a 2–3 minute landing page with purpose, current v5.1 capabilities, compact architecture summary, and the four required links; remove manual lists of dated current/historical specs.

- [ ] **Step 4: Re-run focused tests and confirm GREEN**

Run: `python -m pytest tests/media/test_documentation_system.py -q`

Expected: PASS for Task 1 tests.

- [ ] **Step 5: Commit and checkpoint**

Commit message: `docs: add living documentation entry points`

Update PR #70 with Task 1 GREEN and the exact head SHA.

---

### Task 2: Current architecture living docs

**Files:**
- Create: `docs/architecture/overview.md`
- Create: `docs/architecture/media-model.md`
- Create: `docs/architecture/intelligence.md`
- Create: `docs/architecture/write-pipeline.md`
- Create: `docs/architecture/web-and-broker.md`
- Modify: `tests/media/test_documentation_system.py`

**Interfaces:**
- Consumes: `media/commands/schema.py`, `media/service/web_export.py`, current v5.1 implementation/specs as factual reference.
- Produces: authoritative current architecture documentation independent of dated design specs.

- [ ] **Step 1: Add failing architecture contracts**

Add tests named:

```python
def test_architecture_layer_covers_current_v51_without_historical_specs(): ...
def test_intelligence_doc_keeps_similarity_as_evidence_not_preference(): ...
def test_candidate_assessment_doc_is_read_only_and_qualitative(): ...
def test_web_architecture_manifest_version_matches_exporter(): ...
def test_write_pipeline_separates_normal_typed_and_manual_developer_routes(): ...
```

The manifest test must import `WEB_MANIFEST_SCHEMA_VERSION` from `media.service.web_export` and compare it with a machine-readable prose marker `Current manifest version: vN` in `web-and-broker.md`.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/media/test_documentation_system.py -q`

Expected: FAIL because architecture files do not exist.

- [ ] **Step 3: Write `overview.md` and `media-model.md`**

`overview.md` covers canonical Git/YAML, generated read models, media service/domain/repository layers, web static manifest, broker boundary, and GitHub Actions. `media-model.md` covers works/collections/lists/interactions/similarity, `primary|partner|couple`, explicit/inferred evidence, semantic fingerprints, canonical/external WorkRef, reconciliation, and canonical-vs-derived rules.

- [ ] **Step 4: Write `intelligence.md`**

Document evidence hierarchy, taste context, internal-vs-external discovery, provenance, couple disagreement, similarity as hint/evidence only, `assess_candidate`, and the ban on fake precise probability/opaque match scores.

- [ ] **Step 5: Write `write-pipeline.md` and `web-and-broker.md`**

Document the exact normal lifecycle `typed request -> operation PR -> deterministic transaction -> validation/rebuild -> exact-head gate -> guarded merge -> exact-merge Pages publish`; separately document manual developer/maintenance routes. In `web-and-broker.md`, include `Current manifest version: v3`, static/read-only Pages behavior, broker responsibilities, and browser credential restrictions.

- [ ] **Step 6: Confirm GREEN**

Run: `python -m pytest tests/media/test_documentation_system.py -q`

Expected: PASS for Tasks 1–2 contracts.

- [ ] **Step 7: Commit and checkpoint**

Commit message: `docs: add current architecture living docs`

Update PR #70 with Task 2 GREEN and note that no runtime files changed.

---

### Task 3: Guides, reference catalog, and durable current status

**Files:**
- Create: `docs/guides/media-usage.md`
- Create: `docs/guides/development.md`
- Create: `docs/guides/operations.md`
- Create: `docs/reference/media-commands.md`
- Create: `docs/reference/repository-layout.md`
- Create: `docs/reference/invariants.md`
- Create: `docs/reference/terminology.md`
- Create: `docs/status/current.md`
- Modify: `tests/media/test_documentation_system.py`

**Interfaces:**
- Consumes: `media.commands.schema._SCHEMA_BY_OPERATION`, current CLI/module paths, architecture docs from Task 2.
- Produces: human workflows, developer/runbook guidance, synchronized operation catalog, stable terminology/invariants, durable current state.

- [ ] **Step 1: Add failing reference/runbook/status contracts**

Add tests named:

```python
def test_media_command_reference_matches_registered_operations(): ...
def test_operations_guide_uses_existing_verification_commands(): ...
def test_reference_invariants_include_cross_system_safety_rules(): ...
def test_current_status_is_durable_not_a_pr_ledger(): ...
def test_media_usage_covers_similarity_and_candidate_assessment(): ...
```

For operation synchronization, parse operation names from rows formatted `| `operation_name` |` and compare the set exactly with `set(_SCHEMA_BY_OPERATION)`. Reject transient status markers such as `Current head:`, `Media Dev Check #`, `Web Check #`, `Task 1`, `Task 2`, and feature-branch resume instructions.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/media/test_documentation_system.py -q`

Expected: FAIL because guides/reference/status files do not exist.

- [ ] **Step 3: Write user/developer/operations guides**

`media-usage.md` covers record/edit/interest/recommendations/candidate assessment/similarity/partner-couple behavior without GitHub implementation noise. `development.md` covers current-main-first, typed-vs-manual route selection, TDD/validation, schema/vocabulary changes, PR checkpointing, and the documentation update matrix. `operations.md` contains real commands for pytest, validation, rebuild check, doctor, web export, web tests/typecheck/build, and Pages/recovery verification.

- [ ] **Step 4: Write reference docs**

`media-commands.md` contains one row per `_SCHEMA_BY_OPERATION` entry with category, read/write status, side-effect summary, and auto-merge eligibility; it links to schemas instead of copying payload fields. `repository-layout.md`, `invariants.md`, and `terminology.md` stay concise and responsibility-focused.

- [ ] **Step 5: Write durable `docs/status/current.md`**

Summarize current v5.1 capabilities including candidate assessment and explicit similarity, known limitations, current manifest generation, and durable follow-ups. Do not include PR numbers, temporary task progress, stale branch SHA, or RED/GREEN run history.

- [ ] **Step 6: Confirm GREEN**

Run: `python -m pytest tests/media/test_documentation_system.py -q`

Expected: PASS for Tasks 1–3 contracts.

- [ ] **Step 7: Commit and checkpoint**

Commit message: `docs: add guides reference and durable status`

Update PR #70 with Task 3 GREEN.

---

### Task 4: Compatibility routers and normative agent contracts

**Files:**
- Modify: `AGENTS.md`
- Modify: `media/README.md`
- Modify: `media/AGENTS.md`
- Modify: `media/START_PROMPT.md`
- Modify: `media/V5_STATUS.md`
- Modify: `PRODUCT.md`
- Modify: `DESIGN.md`
- Modify: `tests/media/test_docs.py`
- Modify: `tests/media/test_agent_ux_contract.py`
- Modify: `tests/media/test_documentation_system.py`

**Interfaces:**
- Consumes: living docs from Tasks 1–3.
- Produces: preserved legacy entry paths that route to the new authority model without losing normative agent/user behavior.

- [ ] **Step 1: Rewrite tests first for the new ownership model**

Update old docs tests so detailed v5/v5.1 semantics are asserted in `docs/architecture`, `docs/reference`, and `docs/status/current.md` rather than requiring `media/README.md` or the compatibility status file to remain monoliths. Update agent UX tests to require root `AGENTS.md` -> `media/AGENTS.md` -> relevant living docs, while preserving existing human-first starter behavior and all safety/merge/intent guardrails.

Add focused tests:

```python
def test_media_readme_is_compact_subsystem_router(): ...
def test_v5_status_is_small_compatibility_router(): ...
def test_product_and_design_are_explicitly_scoped_to_media_web(): ...
def test_agent_bootstrap_does_not_require_historical_specs_or_long_status(): ...
```

- [ ] **Step 2: Confirm RED against current entry documents**

Run: `python -m pytest tests/media/test_docs.py tests/media/test_agent_ux_contract.py tests/media/test_documentation_system.py -q`

Expected: FAIL on old bootstrap/monolith expectations until entry documents are migrated.

- [ ] **Step 3: Rewrite root/media routers**

Keep root `AGENTS.md` compact and remove mandatory `media/V5_STATUS.md` reading for ordinary work. Rewrite `media/README.md` as a subsystem landing page with canonical/derived summary, living-doc links, and minimal CLI quickstart. Convert `media/V5_STATUS.md` to a short compatibility file linking `docs/status/current.md` and explaining where historical development detail lives.

- [ ] **Step 4: Carefully slim `media/AGENTS.md` without weakening imperative rules**

Retain intent router, normal read/write route rules, user-experience contract, evidence hierarchy, target safety, similarity/candidate-assessment safety, no-direct-YAML/generated-edit rules, path/workflow discipline, and full verification requirements. Replace only explanatory duplication with links to the relevant living docs.

- [ ] **Step 5: Update `media/START_PROMPT.md`, `PRODUCT.md`, and `DESIGN.md` scopes**

Keep START_PROMPT human-first and concise, but route technical bootstrap to `media/AGENTS.md` plus relevant living docs/current status instead of treating `media/V5_STATUS.md` as a required second manual. Add explicit media-web scope wording near the top of `PRODUCT.md` and `DESIGN.md` without moving them.

- [ ] **Step 6: Confirm GREEN for compatibility and guardrails**

Run: `python -m pytest tests/media/test_docs.py tests/media/test_agent_ux_contract.py tests/media/test_documentation_system.py -q`

Expected: PASS with all normative guardrails retained.

- [ ] **Step 7: Commit and checkpoint**

Commit message: `docs: migrate entry points to living documentation`

Update PR #70 with Task 4 GREEN and explicitly note that legacy paths remain valid.

---

### Task 5: Link audit, drift hardening, and final verification

**Files:**
- Modify: `tests/media/test_documentation_system.py`
- Modify as needed: any new/updated Markdown file with a broken or ambiguous local link.
- Update: PR #70 body/comments only for progress/final handoff.

**Interfaces:**
- Consumes: all living/entry documentation produced by Tasks 1–4.
- Produces: whole-system documentation integrity gate and verified final branch.

- [ ] **Step 1: Add generic local-link contract**

Implement `_local_markdown_targets(path: Path) -> list[Path]` in the test module and add:

```python
def test_key_living_documentation_local_links_resolve(): ...
```

Scan root README/AGENTS, media README/AGENTS/START_PROMPT/V5_STATUS, `docs/README.md`, and every Markdown file under `docs/architecture`, `docs/guides`, `docs/reference`, `docs/status`. Ignore `http(s)://`, `mailto:`, pure anchors, and code-fenced examples; every remaining relative target must exist.

- [ ] **Step 2: Run the docs suite and confirm any real RED findings**

Run: `python -m pytest tests/media/test_docs.py tests/media/test_agent_ux_contract.py tests/media/test_documentation_system.py -q`

Expected: either PASS immediately or FAIL only on genuine broken links/ownership drift; fix each finding at its source rather than weakening the test.

- [ ] **Step 3: Run the full Python/media verification**

Run, in order:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
python -m media.cli web-export --output /tmp/media-web-manifest.json --format json
```

Expected: all commands succeed; rebuild reports no drift; doctor reports `status=ok`.

- [ ] **Step 4: Run the web verification**

Run:

```bash
npm --prefix web run test:run
npm --prefix web run typecheck
npm --prefix web run build
npm --prefix web run scan:dist
```

Expected: all commands succeed; documentation-only change introduces no web/runtime regression.

- [ ] **Step 5: Whole-branch review against spec**

Review for duplicated ownership, lost AGENTS guardrails, stale current-v5 claims, historical specs presented as current, command/manifest drift, transient status data, broken compatibility paths, and accidental runtime/schema/data changes. Any Critical/Important finding gets its own RED -> GREEN fix before completion.

- [ ] **Step 6: Final exact-head CI and handoff**

Push the final branch head and require the repository’s authoritative Media Dev/Web checks (and any documentation-relevant checks) to complete successfully on that exact SHA. Update PR #70 body with completed tasks, verification evidence, known limitations, and a resume/reviewer focus. Mark ready for review only after exact-head GREEN.

- [ ] **Step 7: Commit final audit fixes, if any**

Commit message when needed: `docs: harden documentation integrity contracts`

No merge is performed without the owner’s explicit integration decision.
