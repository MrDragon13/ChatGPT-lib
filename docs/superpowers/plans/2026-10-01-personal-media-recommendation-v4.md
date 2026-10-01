# Personal Media Recommendation v4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the existing movie taste data into the approved v4 multi-viewer canonical media model, with strict schemas, validation, reproducible derived indexes/profiles/SQLite, and no competing legacy source of truth.

**Architecture:** Git/YAML remains canonical. Each work/collection/list/tombstone is independently addressable, raw viewer/group signals live with the entity, and controlled vocabulary plus JSON Schema prevents drift. Python tooling validates cross-file invariants, migrates v1 data, and rebuilds derived JSONL/profile/SQLite artifacts; the future website/API consumes those derived artifacts but is not part of this implementation.

**Tech Stack:** Python 3.11+, PyYAML 6.x, jsonschema 4.x / JSON Schema 2020-12, Python `sqlite3`, pytest 8.x, Git/YAML/JSONL.

**Spec:** `docs/superpowers/specs/2026-10-01-personal-media-recommendation-v4-design.md`

## Global Constraints

- Git/YAML is the only canonical source of truth; generated data must be fully rebuildable.
- Do not store names, ages, birth dates, or other personal data for viewers; initial stable IDs are `primary`, `partner`, and group `couple` only.
- Sparse signals are mandatory: do not create viewer/group records without real evidence.
- `unwatched` and `dropped` are not automatically negative reactions.
- Rating, reaction, feedback, viewing, rewatch, interest, and group suitability are independent fields.
- Normal data entry must never change schemas or silently invent vocabulary terms.
- Unknown factual metadata stays absent/null; migration must not guess medium, external IDs, seasons, cast, or other facts.
- TMDB uniqueness uses `(media_type, id)`, not numeric ID alone; IMDb `tt...` IDs are globally unique within active works.
- Season details are optional; season `0` is allowed for specials; movie entities cannot contain seasons.
- Immutable IDs are never repurposed; merge/delete uses tombstones/redirects.
- Ephemeral recommendation context is never persisted unless the user explicitly makes it persistent.
- Legacy `movies/` files are removed only after new canonical data validate and all derived artifacts rebuild successfully.
- `generated/database.sqlite`, embeddings, and image cache are build artifacts and must not be committed.
- Web UI, production API/auth, background metadata refresh, vector DB, full person catalog, and full event sourcing are out of scope.

## Review Focus

- **TMDB collision:** `(movie, 123)` and `(tv, 123)` coexist; duplicate identical composite keys fail. Covered in Task 4.
- **Sparse multi-viewer data:** `partner: liked` without rating/viewing validates; absent partner and explicit `unknown` remain distinct. Covered in Task 3.
- **Series boundaries:** seasonless series and season `0` validate; duplicate seasons and seasons on movies fail. Covered in Tasks 3–4.
- **Reference integrity:** redirect cycles, missing targets, self-relations, stale redirected IDs, and invalid group targets fail deterministically. Covered in Task 4.
- **Migration fidelity:** every legacy item maps exactly once, preserves rating/status/comment meaning, preserves important legacy inferred taste signals with provenance, and never converts `unwatched` into dislike. Covered in Task 5.

---

## File Structure Locked by This Plan

```text
pyproject.toml
media/
├── __init__.py
├── AGENTS.md
├── README.md
├── .gitignore
├── requirements.txt
├── vocabulary.yaml
├── config/
│   ├── viewers.yaml
│   └── groups.yaml
├── preferences/
│   └── explicit/
│       └── primary.yaml
├── schemas/
│   ├── common.schema.json
│   ├── work.schema.json
│   ├── collection.schema.json
│   ├── list.schema.json
│   ├── interaction.schema.json
│   ├── tombstone.schema.json
│   ├── viewers.schema.json
│   ├── groups.schema.json
│   ├── vocabulary.schema.json
│   └── explicit-preferences.schema.json
├── data/
│   ├── works/*.yaml
│   ├── collections/*.yaml
│   ├── lists/
│   ├── interactions/
│   └── tombstones/
├── generated/
│   ├── index.jsonl
│   └── profiles/
│       ├── primary.yaml
│       ├── partner.yaml
│       └── couple.yaml
└── tools/
    ├── __init__.py
    ├── common.py
    ├── schema_utils.py
    ├── validate.py
    ├── migrate_v1.py
    ├── build_index.py
    ├── build_profiles.py
    └── build_db.py

tests/media/
├── fixtures/
├── test_common.py
├── test_aux_schemas.py
├── test_work_schema.py
├── test_validator.py
├── test_migration.py
├── test_build_index.py
├── test_build_profiles.py
├── test_build_db.py
└── test_acceptance.py
```

`generated/database.sqlite` is produced locally by `build_db.py` and ignored by Git.

### Task 1: Python Tooling and Deterministic Data I/O

**Files:**
- Create: `pyproject.toml`
- Create: `media/__init__.py`
- Create: `media/tools/__init__.py`
- Create: `media/requirements.txt`
- Create: `media/tools/common.py`
- Test: `tests/media/test_common.py`

**Interfaces:**
- Produces: `load_yaml(path: Path) -> Any`
- Produces: `dump_yaml(path: Path, data: Any) -> None`
- Produces: `iter_yaml_files(path: Path) -> list[Path]`
- Produces: `iter_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]`
- Produces: `write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None`

- [ ] **Step 1: Add dependencies/test config** — `media/requirements.txt`: `PyYAML>=6.0,<7`, `jsonschema>=4.23,<5`, `pytest>=8,<9`; configure pytest in `pyproject.toml`.
- [ ] **Step 2: Write failing deterministic I/O tests** — YAML round-trip preserves nested `None`/lists and Unicode; YAML iteration is lexicographically stable; JSONL returns physical line numbers and skips blank lines.
- [ ] **Step 3: Run failure check** — `python -m pytest tests/media/test_common.py -v`; expected FAIL because helpers do not exist.
- [ ] **Step 4: Implement the five helpers** — use UTF-8, `yaml.safe_load`, `yaml.safe_dump(sort_keys=False, allow_unicode=True)`.
- [ ] **Step 5: Run pass check** — same pytest command; expected PASS.
- [ ] **Step 6: Commit** — `git commit -m "build: add media tooling test harness"`.

### Task 2: Shared Schemas, Config, Vocabulary, Lists, Interactions, Explicit Preferences

**Files:**
- Create: `media/tools/schema_utils.py`
- Create: `media/schemas/common.schema.json`
- Create: `media/schemas/{viewers,groups,vocabulary,explicit-preferences,list,interaction,tombstone}.schema.json`
- Create: `media/config/viewers.yaml`
- Create: `media/config/groups.yaml`
- Create: `media/vocabulary.yaml`
- Create: `media/preferences/explicit/primary.yaml`
- Test: `tests/media/test_aux_schemas.py`

**Interfaces:**
- Produces: `build_registry(schema_dir: Path) -> referencing.Registry`
- Produces: `validate_against_schema(instance: Any, schema_name: str, schema_dir: Path) -> list[str]`

- [ ] **Step 1: Write failing auxiliary-schema tests** — anonymous viewer config, `couple=[primary,partner]`, closed objects, canonical vocabulary term shape, list shape, interaction event enum, tombstone shape, explicit preference/rule/constraint provenance.
- [ ] **Step 2: Run failure check** — `python -m pytest tests/media/test_aux_schemas.py -v`.
- [ ] **Step 3: Implement Draft 2020-12 registry/helper** — return sorted human-readable error paths rather than fail-fast exceptions.
- [ ] **Step 4: Implement common/auxiliary schemas** — common `$defs` owns rating/reaction/feedback/history/relation/target-state structures; use `additionalProperties: false` for fixed objects.
- [ ] **Step 5: Create initial config/vocabulary** — only `primary`, `partner`, `couple`; seed approved namespaced terms including core `genre.*`, `story.*`, `narrative.*`, `pacing.*`, `humor.*`, `atmosphere.*`, `characters.*`, `visuals.*`, `reaction.*`, `content.*`, `entertainment.engaging`, `emotional_impact`; aliases are lookup metadata only.
- [ ] **Step 6: Create minimal explicit primary preferences** — persist only genuinely global user statements established in conversation: genre is secondary to execution; slow pacing is not inherently negative when justified by story/characters. Do not copy all legacy derived conclusions here.
- [ ] **Step 7: Run pass check** — auxiliary schema tests PASS.
- [ ] **Step 8: Commit** — `git commit -m "feat: define media config vocabulary and shared schemas"`.

### Task 3: Work and Collection Schemas

**Files:**
- Create: `media/schemas/work.schema.json`
- Create: `media/schemas/collection.schema.json`
- Test: `tests/media/test_work_schema.py`

**Interfaces:**
- Consumes: Task 2 common definitions.
- Produces: canonical work/collection contract used by migration, validator, and builders.

- [ ] **Step 1: Write failing sparse-signal/identity tests** — movie without `medium`/external IDs is valid; `medium` if present is enum; partner-only `liked` is valid; rating/reaction independent; rating `1..10` step `0.5`; TMDB identity is `{media_type,id}`.
- [ ] **Step 2: Write failing season/group/metadata tests** — seasonless series valid; season `0` valid; movie with seasons invalid; group signal reuses signal semantics; semantic traits have `term/source/confidence`; `metadata.external`, `metadata.overrides`, `metadata.semantic` are distinct; people are structured external refs; assets are provider refs only.
- [ ] **Step 3: Write manual-override schema tests** — overrides may contain only explicitly allowed metadata fields and cannot introduce arbitrary provider-shaped keys.
- [ ] **Step 4: Run failure check** — `python -m pytest tests/media/test_work_schema.py -v`.
- [ ] **Step 5: Implement `work.schema.json`** — require `schema_version: 4`, `id`, `entity_type: work`, `identity`; keep unknown factual fields optional instead of guessing. Identity titles are canonical display/lookup values; metadata overrides apply only to metadata fields, avoiding a second title source.
- [ ] **Step 6: Implement `collection.schema.json`** — immutable ID/name/member IDs plus same sparse viewer/group signals; allow empty members during migration; never propagate collection rating to members.
- [ ] **Step 7: Run pass check** — work schema tests PASS.
- [ ] **Step 8: Commit** — `git commit -m "feat: define v4 work and collection schemas"`.

### Task 4: Repository Validator and Cross-Reference Integrity

**Files:**
- Create: `media/tools/validate.py`
- Create: `tests/media/test_validator.py`
- Create: `tests/media/fixtures/valid_repo/`

**Interfaces:**
- Produces: `ValidationIssue(path: str, code: str, message: str)`.
- Produces: `validate_repository(repo_root: Path) -> list[ValidationIssue]`.
- CLI: `python -m media.tools.validate [repo-root]`, exit `0` valid / `1` invalid.

- [ ] **Step 1: Write minimal valid fixture/smoke test** — one movie, one seasonless series, sparse partner reaction, config/vocabulary, zero generated dependencies; expect no issues.
- [ ] **Step 2: Write identity uniqueness tests** — duplicate IMDb fails; duplicate identical TMDB composite fails; `(movie,123)` + `(tv,123)` succeeds; active internal IDs are unambiguous.
- [ ] **Step 3: Write reference/tombstone tests** — missing targets, redirect cycles/self-redirect, relation self-reference, invalid group members fail. References that point to a tombstoned ID are rejected as stale and must be normalized to the active redirect target by the writer.
- [ ] **Step 4: Write vocabulary/season tests** — aliases cannot be used as canonical IDs; unknown terms fail; duplicate season numbers fail; season `0` succeeds.
- [ ] **Step 5: Write interaction-log integrity tests** — files must be `YYYY-MM.jsonl`; IDs/timestamps/types validate; event timestamp month must match the containing monthly file; referenced work/target/list IDs must exist when required by the event type.
- [ ] **Step 6: Implement validator** — schema first, then in-memory indexes for IDs/external IDs/targets/vocabulary/redirects, then cross-reference/business checks; sort issues by `(path, code, message)`.
- [ ] **Step 7: Run pass check** — `python -m pytest tests/media/test_validator.py -v`.
- [ ] **Step 8: Commit** — `git commit -m "feat: add cross-file media validator"`.

### Task 5: Deterministic Legacy v1 Migration

**Files:**
- Create: `media/tools/migrate_v1.py`
- Test: `tests/media/test_migration.py`
- Read: `movies/data/movies.yaml`
- Read: `movies/profile.md`
- Write during execution: `media/data/works/*.yaml`, `media/data/collections/*.yaml`

**Interfaces:**
- Produces: `MigrationResult(works: list[dict], collections: list[dict])`.
- Produces: `migrate_v1_document(doc: Mapping[str, Any], migrated_at: str) -> MigrationResult`.
- Produces: `apply_legacy_signal_mappings(result: MigrationResult) -> MigrationResult`.
- Produces: `write_migration(result: MigrationResult, media_root: Path) -> None`.
- CLI: `--source`, `--destination`, `--check`.

- [ ] **Step 1: Write failing one-to-one migration tests** — representative movie/series/collection/unwatched records map exactly once; preserve ID/title/year/status/rating/source/confidence/comment; map owner to `viewer_signals.primary`; do not synthesize reaction, medium, external IDs, seasons, cast.
- [ ] **Step 2: Add parity assertions** — destination count equals source item count; every source ID occurs once; every non-null rating and non-empty comment survives; `unwatched` stays viewing-only; collection ratings stay on collection.
- [ ] **Step 3: Preserve legacy derived taste as inferred, evidence-backed feedback signals** — create a small explicit migration mapping only where legacy `profile.md`/comments already establish the interpretation. At minimum: Game Night → positive `entertainment.engaging`, negative `reaction.cringe`, negative `humor.absurd`; Blade Runner 2049 → positive `visuals.strong`, negative `reaction.pacing_dragging`; Knives Out + Sherlock → positive `story.intrigue`; Ocean’s/Now You See Me/Guy Ritchie Sherlock collection → positive `characters.charisma` and `story.problem_solving`. Mark every migrated structured signal `source: inferred`; retain original summary text. Resolve entries by title/year when old IDs are uncertain. Do not manufacture broader signals not supported by legacy evidence.
- [ ] **Step 4: Add known partner facts from this design session** — Game Night partner liked/watched high confidence; Grand Budapest Hotel partner liked/watched high confidence; Once Upon a Time in Hollywood partner disliked/watched high confidence; Gone Girl partner liked/watched medium confidence. Do not create couple ratings from these.
- [ ] **Step 5: Run failure check** — `python -m pytest tests/media/test_migration.py -v`.
- [ ] **Step 6: Implement migration** — old `movie|series` → work format; old `collection` → collection; comment → feedback summary; preserve inferred rating provenance; preserve existing IDs; optional metadata containers only when schema requires them.
- [ ] **Step 7: Dry-run real migration** — `python -m media.tools.migrate_v1 --source movies/data/movies.yaml --destination media --check`; expect zero collisions and exact parity.
- [ ] **Step 8: Write migrated files while legacy remains** — run migration without `--check`, then `python -m media.tools.validate .`; expect PASS.
- [ ] **Step 9: Commit** — `git commit -m "data: migrate movie library to v4 canonical entities"`.

### Task 6: Compact Retrieval Index

**Files:**
- Create: `media/tools/build_index.py`
- Test: `tests/media/test_build_index.py`
- Create: `media/generated/index.jsonl`

**Interfaces:**
- Produces: `build_index(repo_root: Path) -> list[dict[str, Any]]`.
- CLI writes `media/generated/index.jsonl`.

- [ ] **Step 1: Write failing index tests** — one deterministic active-work row sorted by ID; include identity, semantic genres/traits, sparse primary/partner/couple rating/reaction summaries, target interest, derived collection memberships; tombstones excluded.
- [ ] **Step 2: Add override-precedence tests** — for every indexed metadata field that allows overrides, effective value is `override -> external -> null`; canonical identity fields are read from `identity` and are never shadowed by metadata.
- [ ] **Step 3: Run failure check** — `python -m pytest tests/media/test_build_index.py -v`.
- [ ] **Step 4: Implement builder from canonical data only** — never read an existing generated index/profile/SQLite as input.
- [ ] **Step 5: Run/build** — tests PASS; `python -m media.tools.build_index .` creates stable JSONL.
- [ ] **Step 6: Commit** — `git commit -m "feat: build compact media retrieval index"`.

### Task 7: Rebuildable Derived Taste Profiles

**Files:**
- Create: `media/tools/build_profiles.py`
- Test: `tests/media/test_build_profiles.py`
- Create: `media/generated/profiles/{primary,partner,couple}.yaml`

**Interfaces:**
- Produces: `build_profiles(repo_root: Path) -> dict[str, dict[str, Any]]`.
- Produces: `aggregate_term_signals(signals: Iterable[SignalEvidence]) -> dict[str, Affinity]`.

- [ ] **Step 1: Write deterministic term-affinity tests** — only term-specific feedback/preferences create term affinity. Sentiment: `positive=+1`, `negative=-1`, `mixed=0`, `neutral=0`; weight = `strength` × provenance (`explicit=1.0`, `inferred=0.7`) × confidence (`exact=1.0`, `high=0.9`, `medium=0.7`, `low=0.5`, `none=0.25`); normalize signed sum by total absolute weight to `[-1,1]`; retain evidence IDs/counts.
- [ ] **Step 2: Prove no trait leakage from overall rating** — a low-rated work tagged `pacing.slow` must not create negative `pacing.slow` affinity unless feedback explicitly links sentiment to that term. This pins the slow-vs-dragging design rule.
- [ ] **Step 3: Write sparse partner/couple tests** — partner profile builds from liked/disliked alone; couple profile references primary/partner components, combines their term affinities by evidence weight, then adds direct `group_signals.couple`/explicit couple evidence rather than replacing with a simple average.
- [ ] **Step 4: Write summary/evidence tests** — ratings/reactions/rewatch/viewing/relations/interactions produce transparent summary/evidence sections but not invented term affinities; explicit rules/constraints are copied with provenance.
- [ ] **Step 5: Run failure check** — `python -m pytest tests/media/test_build_profiles.py -v`.
- [ ] **Step 6: Implement builder/stable output** — profiles contain `schema_version`, `target`, `generated_from`, `affinities`, `explicit_preferences`, `rules`, `constraints`, `summary`, `evidence`.
- [ ] **Step 7: Run/build** — tests PASS; build all three target profiles even when partner/couple evidence is sparse.
- [ ] **Step 8: Commit** — `git commit -m "feat: build derived viewer and couple profiles"`.

### Task 8: Rebuildable SQLite Runtime Database

**Files:**
- Create: `media/tools/build_db.py`
- Test: `tests/media/test_build_db.py`
- Create/Modify: `media/.gitignore`

**Interfaces:**
- Produces: `build_database(repo_root: Path, output: Path) -> None`.
- CLI default output: `media/generated/database.sqlite`.

- [ ] **Step 1: Write failing rebuild tests** — create temp DB; assert tables `works`, `people_refs`, `terms`, `viewer_signals`, `group_signals`, `seasons`, `collections`, `collection_members`, `lists`, `list_members`, `interactions`, `relations`, `target_states`; delete/rebuild yields same logical row counts.
- [ ] **Step 2: Add identity constraints** — non-null IMDb unique; TMDB composite unique; same numeric TMDB ID with different media type succeeds.
- [ ] **Step 3: Add effective-metadata tests** — SQLite stores the same effective override-first metadata values as index builder, and keeps provider provenance/external metric observation dates where present.
- [ ] **Step 4: Run failure check** — `python -m pytest tests/media/test_build_db.py -v`.
- [ ] **Step 5: Implement atomic DB builder** — build temporary file, create tables/indexes, read canonical YAML/JSONL only, commit transaction, atomically replace output; never write back to YAML.
- [ ] **Step 6: Ignore binary/runtime caches** — `.gitignore`: `generated/database.sqlite`, SQLite sidecars, embeddings, image/cache directories; generated text index/profiles remain trackable.
- [ ] **Step 7: Run/build** — tests PASS; build local DB; `git status` must not show SQLite.
- [ ] **Step 8: Commit** — `git commit -m "feat: add rebuildable media SQLite runtime"`.

### Task 9: Operational Contract and Documentation

**Files:**
- Create: `media/AGENTS.md`
- Create: `media/README.md`
- Modify: `README.md`
- Test: `tests/media/test_acceptance.py`

**Interfaces:**
- Produces: operational write protocol for LLM/Web UI/CLI clients.

- [ ] **Step 1: Write failing acceptance/doc assertions** — all core paths exist; SQLite ignored; every schema loads; initial config contains only `primary`, `partner`, `couple`; README commands refer to real modules.
- [ ] **Step 2: Write `media/AGENTS.md`** — read schemas/vocabulary before write; dedup first; resolve tombstones; unknown > guessed; no schema change during data entry; no synonym creation; no signal without evidence; preserve explicit/inferred provenance; do not persist ephemeral context; validate complete logical change-set; generated data never source of truth; one logical operation per commit.
- [ ] **Step 3: Write `media/README.md`** — source-of-truth vs generated layout, sparse multi-viewer semantics, work update flow, and exact commands for validate/index/profiles/DB. State that reliable metadata enrichment is allowed but no background TMDB client/service is implemented in v4.
- [ ] **Step 4: Update root README** — replace `movies/` navigation with `media/` and describe films/series/animation + multi-viewer recommendations.
- [ ] **Step 5: Run pass check** — `python -m pytest tests/media/test_acceptance.py -v`.
- [ ] **Step 6: Commit** — `git commit -m "docs: document v4 media write protocol"`.

### Task 10: Full Acceptance, Legacy Cutover, Final Verification

**Files:**
- Delete only after successful verification: `movies/data/movies.yaml`, `movies/profile.md`, `movies/schema.md`, `movies/README.md`
- Verify: all `media/**`, generated text artifacts, root README.

**Interfaces:**
- Produces: v4 as the sole active media source of truth.

- [ ] **Step 1: Run full suite before deletion** — `python -m pytest -v`; expected PASS.
- [ ] **Step 2: Delete/rebuild generated layer from scratch** — remove generated index/profiles/SQLite; run validate → build_index → build_profiles → build_db → validate; every command exits 0.
- [ ] **Step 3: Run final legacy parity check** — migration `--check` against still-present legacy source must prove all IDs/ratings/comments/statuses match v4 and no collection rating leaked to members.
- [ ] **Step 4: Delete the four legacy active source files** — do not create an archive that could be mistaken for a current source of truth; Git history and superseded design docs are the archive.
- [ ] **Step 5: Re-run suite/validation/builders without `movies/`** — must pass and must not read legacy paths.
- [ ] **Step 6: Inspect Git status** — no SQLite/cache/image/embedding artifacts staged; only canonical YAML, schemas/tools/tests/docs, generated text index/profiles tracked.
- [ ] **Step 7: Commit cutover** — `git commit -m "refactor: cut over media library to v4"`.
- [ ] **Step 8: Final spec checklist** — explicitly verify migration meaning preserved; sparse partner reaction supported; seasonless series supported; primary/partner/couple targets work; schema/vocabulary drift rejected; ephemeral request context has no canonical persistence path; all generated runtime rebuilds; TMDB movie/TV collision safe; deleting SQLite loses no information.

## Self-Review Result

- **Spec coverage:** all v4 scope items map to Tasks 1–10; web UI/API/embeddings remain deliberately outside implementation.
- **Type consistency:** later builders consume the same canonical work/collection/config/vocabulary structures established by Tasks 2–3; validator is the shared gate.
- **Migration meaning:** legacy raw comments/ratings are preserved verbatim while only evidence-backed legacy interpretations become `inferred` structured signals; explicit global preferences remain separate.
- **Derived-data safety:** index/profiles/SQLite read canonical inputs only; manual override precedence is pinned by tests in both index and DB builders.
- **Operational safety:** stale redirected references are rejected, monthly interaction files are validated, and legacy deletion occurs only after parity + rebuild checks pass.
