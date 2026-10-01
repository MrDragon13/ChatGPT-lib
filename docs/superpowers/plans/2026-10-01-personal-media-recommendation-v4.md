# Personal Media Recommendation v4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the existing movie taste data into the approved v4 multi-viewer canonical media model, with strict schemas, validation, reproducible derived indexes/profiles/SQLite, and no competing legacy source of truth.

**Architecture:** Git/YAML remains canonical. Each work/collection/list/tombstone is independently addressable, raw viewer/group signals live with the entity, and controlled vocabulary plus JSON Schema prevents drift. Python tooling validates cross-file invariants, migrates v1 data, and rebuilds derived JSONL/profile/SQLite artifacts; the future website/API consumes those derived artifacts but is not part of this implementation.

**Tech Stack:** Python 3.11+, PyYAML 6.x, jsonschema 4.x / JSON Schema 2020-12, Python `sqlite3`, pytest 8.x, Git/YAML/JSONL.

**Spec:** `docs/superpowers/specs/2026-10-01-personal-media-recommendation-v4-design.md`

## Global Constraints

- Git/YAML is the only canonical source of truth; generated data must be fully rebuildable.
- Do not store names, ages, birth dates, or other personal data for viewers; only stable IDs `primary`, `partner`, and group `couple` exist initially.
- Sparse signals are mandatory: do not create viewer/group records without real evidence.
- `unwatched` and `dropped` are not automatically negative reactions.
- Rating, reaction, feedback, viewing, rewatch, interest, and group suitability are independent fields.
- Normal data entry must never change schemas or silently invent vocabulary terms.
- Unknown factual metadata stays absent/null; migration must not guess medium, external IDs, seasons, cast, or other facts.
- TMDB uniqueness uses `(media_type, id)`, not numeric ID alone; IMDb `tt...` IDs are globally unique within active works.
- Season details are optional; season `0` is allowed for specials; movie entities cannot contain seasons.
- Immutable IDs are never repurposed; merge/delete is represented by tombstones/redirects.
- Ephemeral recommendation context is never persisted as an explicit preference unless the user states it is persistent.
- Legacy `movies/` files are removed only after new canonical data validate and all derived artifacts rebuild successfully.
- `generated/database.sqlite`, embeddings, and image cache are build artifacts and must not be committed.
- Web UI, production API/auth, background metadata refresh, vector DB, full person catalog, and full event sourcing are out of scope.

## Review Focus

- **TMDB collision:** `(movie, 123)` and `(tv, 123)` must coexist; a duplicate identical composite key must fail validation. Covered in Task 4.
- **Sparse multi-viewer data:** `partner: liked` without rating/viewing must validate, while an absent partner block must remain distinguishable from explicit `unknown`. Covered in Task 3.
- **Series boundaries:** a series with no seasons must validate, season `0` must validate, duplicate seasons and seasons on movies must fail. Covered in Tasks 3–4.
- **Reference integrity:** redirect cycles, missing list/collection/relation targets, self-relations, and invalid group targets must fail deterministically. Covered in Task 4.
- **Migration fidelity:** every legacy item must become exactly one active work or collection, preserving status/rating/source/confidence/comment semantics without converting `unwatched` into dislike. Covered in Task 5.

---

## File Structure Locked by This Plan

Canonical/runtime files created or replaced:

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
- Create: `tests/media/test_common.py`

**Interfaces:**
- Produces: `load_yaml(path: Path) -> Any`
- Produces: `dump_yaml(path: Path, data: Any) -> None`
- Produces: `iter_yaml_files(path: Path) -> list[Path]`
- Produces: `iter_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]`
- Produces: `write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None`

- [ ] **Step 1: Add the test/tool dependencies and pytest configuration**

Create `media/requirements.txt` with `PyYAML>=6.0,<7`, `jsonschema>=4.23,<5`, `pytest>=8,<9`; configure `pyproject.toml` so `tests/` is the pytest root and Python warnings are visible.

- [ ] **Step 2: Write failing deterministic I/O tests**

In `tests/media/test_common.py`, assert that YAML round-trips nested `None`/lists without custom tags, YAML file iteration is lexicographically stable, and JSONL reports the source line number for each parsed object.

- [ ] **Step 3: Run the tests and confirm failure**

Run: `python -m pytest tests/media/test_common.py -v`

Expected: FAIL because `media.tools.common` does not yet provide the required interfaces.

- [ ] **Step 4: Implement the five I/O helpers in `media/tools/common.py`**

Use `yaml.safe_load`/`safe_dump(sort_keys=False, allow_unicode=True)` and UTF-8; make `iter_yaml_files` non-recursive and stable; skip blank JSONL lines but preserve physical line numbers.

- [ ] **Step 5: Run the tests and confirm pass**

Run: `python -m pytest tests/media/test_common.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml media/__init__.py media/requirements.txt media/tools tests/media/test_common.py
git commit -m "build: add media tooling test harness"
```

### Task 2: Shared Schemas, Config, Vocabulary, Lists, Interactions, and Explicit Preferences

**Files:**
- Create: `media/tools/schema_utils.py`
- Create: `media/schemas/common.schema.json`
- Create: `media/schemas/viewers.schema.json`
- Create: `media/schemas/groups.schema.json`
- Create: `media/schemas/vocabulary.schema.json`
- Create: `media/schemas/explicit-preferences.schema.json`
- Create: `media/schemas/list.schema.json`
- Create: `media/schemas/interaction.schema.json`
- Create: `media/schemas/tombstone.schema.json`
- Create: `media/config/viewers.yaml`
- Create: `media/config/groups.yaml`
- Create: `media/vocabulary.yaml`
- Create: `media/preferences/explicit/primary.yaml`
- Create: `tests/media/test_aux_schemas.py`

**Interfaces:**
- Consumes: `load_yaml` from Task 1.
- Produces: `build_registry(schema_dir: Path) -> referencing.Registry`
- Produces: `validate_against_schema(instance: Any, schema_name: str, schema_dir: Path) -> list[str]`

- [ ] **Step 1: Write failing auxiliary-schema tests**

Assert all of the following: viewer config accepts exactly anonymous IDs with empty objects; `groups.couple.members == [primary, partner]`; unknown properties are rejected; vocabulary terms require canonical ID/kind/label/definition; list target and member IDs have stable string forms; interaction event type is one of `recommended|selected|skipped|dismissed|added_to_list|removed_from_list`; tombstone requires `status: merged` and a different `redirect_to`; explicit preference documents carry `target`, `preferences`, `constraints`, and `rules` with explicit provenance.

- [ ] **Step 2: Run tests and confirm failure**

Run: `python -m pytest tests/media/test_aux_schemas.py -v`

Expected: FAIL because schemas/registry are absent.

- [ ] **Step 3: Implement local JSON Schema registry and validator helper**

Use Draft 2020-12. `validate_against_schema` returns sorted human-readable error paths rather than raising on the first failure.

- [ ] **Step 4: Implement shared and auxiliary schemas with closed objects**

`common.schema.json` owns reusable rating/reaction/feedback/history/relation/target-state definitions. Set `additionalProperties: false` wherever the spec fixes the shape; maps keyed by viewer/group IDs remain map-like but their values are closed.

- [ ] **Step 5: Create canonical initial config and vocabulary**

`viewers.yaml` contains only `primary` and `partner`; `groups.yaml` contains only `couple`. Seed vocabulary with the approved namespaces needed by current taste data and future validation: core `genre.*`, `story.*`, `narrative.*`, `pacing.*`, `humor.*`, `atmosphere.*`, `characters.*`, `visuals.*`, `reaction.*`, `content.*`, `entertainment.engaging`, and `emotional_impact`. Include aliases only as lookup metadata; aliases are never canonical IDs.

- [ ] **Step 6: Create the minimal explicit primary preference file**

Persist only global statements actually established as persistent: genre is secondary to execution, and slow pacing is not inherently negative when justified by story/characters. Do not copy every conclusion from legacy `profile.md` into explicit preferences.

- [ ] **Step 7: Run tests and confirm pass**

Run: `python -m pytest tests/media/test_aux_schemas.py -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add media/config media/vocabulary.yaml media/preferences media/schemas media/tools/schema_utils.py tests/media/test_aux_schemas.py
git commit -m "feat: define media config vocabulary and shared schemas"
```

### Task 3: Work and Collection Schemas

**Files:**
- Create: `media/schemas/work.schema.json`
- Create: `media/schemas/collection.schema.json`
- Create: `tests/media/test_work_schema.py`

**Interfaces:**
- Consumes: `$defs`/registry from Task 2.
- Produces: canonical validation contract for work/collection YAML used by all later tasks.

- [ ] **Step 1: Write failing work-schema tests for sparse signals and identity**

Fixtures must prove: a movie with no `medium`/external IDs is valid; `medium` when present is only `live_action|animation|hybrid`; `partner` may contain only `reaction: liked`; rating may exist without reaction and vice versa; rating is `1..10` in `0.5` increments; TMDB identity is `{media_type,id}`.

- [ ] **Step 2: Write failing season/group/metadata tests**

Assert: a series with no `seasons` is valid; season `0` is valid; duplicate season numbers are rejected by repository validator later; a movie containing seasons is schema-invalid; group signal uses the same reaction/rating/feedback semantics; semantic traits carry `term/source/confidence`; metadata external/overrides/semantic are distinct; people are structured references rather than person files; poster/backdrop store provider references only.

- [ ] **Step 3: Run tests and confirm failure**

Run: `python -m pytest tests/media/test_work_schema.py -v`

Expected: FAIL because work/collection schemas are absent.

- [ ] **Step 4: Implement `work.schema.json`**

Required top-level fields: `schema_version: 4`, immutable `id`, `entity_type: work`, `identity`. Keep unknown factual identity/metadata fields optional rather than inventing values. Allow `viewer_signals`, `group_signals`, `target_states`, `seasons`, canonical relations, and provenance as specified. Identity titles are canonical display/lookup values; metadata overrides apply only to metadata fields, preventing a second competing title field.

- [ ] **Step 5: Implement `collection.schema.json`**

Use immutable ID/name/member IDs and the same sparse viewer/group signal definitions; allow empty `member_ids` during legacy migration; never copy a collection rating to members.

- [ ] **Step 6: Run tests and confirm pass**

Run: `python -m pytest tests/media/test_work_schema.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add media/schemas/work.schema.json media/schemas/collection.schema.json tests/media/test_work_schema.py
git commit -m "feat: define v4 work and collection schemas"
```

### Task 4: Repository Validator and Cross-Reference Integrity

**Files:**
- Create: `media/tools/validate.py`
- Create: `tests/media/test_validator.py`
- Create: `tests/media/fixtures/valid_repo/`

**Interfaces:**
- Consumes: all schema files and I/O helpers.
- Produces: `ValidationIssue(path: str, code: str, message: str)` dataclass.
- Produces: `validate_repository(repo_root: Path) -> list[ValidationIssue]`.
- CLI: `python -m media.tools.validate [repo-root]`, exit `0` when valid, `1` when issues exist.

- [ ] **Step 1: Write a minimal valid repository fixture and failing validator smoke test**

The fixture contains one movie, one seasonless series, primary/partner/couple config, minimal vocabulary, and no generated artifacts. Assert zero issues.

- [ ] **Step 2: Add failing tests for uniqueness and TMDB composite identity**

Assert identical IMDb IDs fail; identical TMDB `(media_type,id)` fails; `(movie,123)` and `(tv,123)` coexist successfully; active internal IDs are globally unique across canonical entity namespaces where references would otherwise be ambiguous.

- [ ] **Step 3: Add failing tests for references and redirects**

Assert missing work/list/collection targets, missing target IDs, redirect cycles, redirect-to-self, viewer `preferred_over` self-reference, and invalid group membership all fail with stable issue codes.

- [ ] **Step 4: Add failing tests for vocabulary and seasons**

Assert alias IDs cannot be used as canonical term references; unknown terms fail; duplicate season numbers fail; season `0` is allowed; collection/list member references resolve through tombstones but canonical files continue to store the active ID after write-layer normalization.

- [ ] **Step 5: Implement `validate_repository` and CLI**

Run schema validation first, then build in-memory indexes for IDs/external IDs/targets/vocabulary/redirects, then cross-reference checks. Sort issues by `(path, code, message)` for deterministic output.

- [ ] **Step 6: Run validator tests**

Run: `python -m pytest tests/media/test_validator.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add media/tools/validate.py tests/media/test_validator.py tests/media/fixtures/valid_repo
git commit -m "feat: add cross-file media validator"
```

### Task 5: Deterministic Legacy v1 Migration

**Files:**
- Create: `media/tools/migrate_v1.py`
- Create: `tests/media/test_migration.py`
- Read: `movies/data/movies.yaml`
- Read: `movies/profile.md`
- Create during execution: `media/data/works/*.yaml`
- Create during execution: `media/data/collections/*.yaml`

**Interfaces:**
- Consumes: legacy `{version, rating_scale, items}` document.
- Produces: `MigrationResult(works: list[dict], collections: list[dict])`.
- Produces: `migrate_v1_document(doc: Mapping[str, Any], migrated_at: str) -> MigrationResult`.
- Produces: `write_migration(result: MigrationResult, media_root: Path) -> None`.
- CLI supports `--source`, `--destination`, and `--check` (no writes).

- [ ] **Step 1: Write failing one-to-one migration tests**

For representative legacy movie/series/collection/unwatched records, assert exactly one destination entity per legacy item; preserve `id`, titles, year, status, rating, `rating_source`, confidence, and comment text; map current owner to `viewer_signals.primary`; do not synthesize reaction, medium, external IDs, seasons, or metadata traits.

- [ ] **Step 2: Add migration-fidelity assertions**

Assert `len(result.works) + len(result.collections) == len(source["items"])`; every source ID appears exactly once; every non-null legacy rating and every non-empty comment survives; `unwatched` remains viewing status only; collection ratings stay only on collection entities.

- [ ] **Step 3: Add explicit known partner-signal migration tests**

Apply only conversational facts already established in this design session, matched by canonical title/year rather than guessed IDs: Game Night (2018) partner `liked`/watched with high confidence; The Grand Budapest Hotel (2014) partner `liked`/watched with high confidence; Once Upon a Time in Hollywood (2019) partner `disliked`/watched because it was reported as very boring; Gone Girl (2014) partner `liked`/watched with medium confidence because the report was less certain. Do not create couple-specific ratings from these facts.

- [ ] **Step 4: Run migration tests and confirm failure**

Run: `python -m pytest tests/media/test_migration.py -v`

Expected: FAIL before implementation.

- [ ] **Step 5: Implement pure migration and writer**

Legacy `kind: movie|series` maps to `entity_type: work` / corresponding format; `kind: collection` maps to collection. Store old comment under `feedback.summary`; keep legacy inferred provenance. Empty metadata blocks are allowed only where the schema requires a container. Preserve legacy IDs rather than renaming them.

- [ ] **Step 6: Dry-run the real repository migration**

Run: `python -m media.tools.migrate_v1 --source movies/data/movies.yaml --destination media --check`

Expected: zero collisions, item-count parity, no write.

- [ ] **Step 7: Write the migrated canonical files while legacy remains present**

Run: `python -m media.tools.migrate_v1 --source movies/data/movies.yaml --destination media`

Then run: `python -m media.tools.validate .`

Expected: PASS. Do not delete `movies/` yet.

- [ ] **Step 8: Commit migration with both old and new data present**

```bash
git add media/data/works media/data/collections media/tools/migrate_v1.py tests/media/test_migration.py
git commit -m "data: migrate movie library to v4 canonical entities"
```

### Task 6: Compact Retrieval Index

**Files:**
- Create: `media/tools/build_index.py`
- Create: `tests/media/test_build_index.py`
- Create: `media/generated/index.jsonl`

**Interfaces:**
- Produces: `build_index(repo_root: Path) -> list[dict[str, Any]]`.
- CLI: `python -m media.tools.build_index [repo-root]` writes `media/generated/index.jsonl`.

- [ ] **Step 1: Write failing index tests**

Assert one deterministic row per active work, sorted by work ID. Each row includes IDs/titles/year/format/medium when known, TMDB composite/IMDb IDs, canonical semantic genres/traits, sparse primary/partner/couple reaction+rating summaries, target interest state, and derived collection memberships. Tombstoned IDs are excluded from active rows.

- [ ] **Step 2: Run tests and confirm failure**

Run: `python -m pytest tests/media/test_build_index.py -v`

Expected: FAIL before builder exists.

- [ ] **Step 3: Implement index builder without reading generated data**

All index fields come from canonical config/data/vocabulary/preferences only. Never parse or depend on an existing `generated/index.jsonl`.

- [ ] **Step 4: Run tests and build real index**

Run: `python -m pytest tests/media/test_build_index.py -v && python -m media.tools.build_index .`

Expected: PASS and deterministic `media/generated/index.jsonl`.

- [ ] **Step 5: Commit**

```bash
git add media/tools/build_index.py tests/media/test_build_index.py media/generated/index.jsonl
git commit -m "feat: build compact media retrieval index"
```

### Task 7: Rebuildable Derived Taste Profiles

**Files:**
- Create: `media/tools/build_profiles.py`
- Create: `tests/media/test_build_profiles.py`
- Create: `media/generated/profiles/primary.yaml`
- Create: `media/generated/profiles/partner.yaml`
- Create: `media/generated/profiles/couple.yaml`

**Interfaces:**
- Produces: `build_profiles(repo_root: Path) -> dict[str, dict[str, Any]]`.
- Produces: `aggregate_term_signals(signals: Iterable[SignalEvidence]) -> dict[str, Affinity]`.
- CLI: `python -m media.tools.build_profiles [repo-root]`.

- [ ] **Step 1: Write failing deterministic affinity tests**

Term affinity uses only term-specific feedback/preference evidence, never blindly propagates an overall bad rating onto every movie trait. Map sentiment `positive=+1`, `negative=-1`, `mixed=0`, `neutral=0`; weight by `strength` (1–3), provenance (`explicit=1.0`, `inferred=0.7`) and confidence (`exact=1.0`, `high=0.9`, `medium=0.7`, `low=0.5`, `none=0.25`). Normalize weighted signed sum by total absolute weight to `[-1,1]` and retain evidence IDs/counts.

- [ ] **Step 2: Add sparse partner and couple tests**

Partner profile must build successfully from only `liked/disliked` signals with no term affinity. Couple profile must include component references to primary/partner, then combine their term affinities by evidence weight and give direct `group_signals.couple`/explicit couple preferences precedence as additional evidence rather than arithmetic replacement.

- [ ] **Step 3: Add summary-signal tests**

Ratings/reactions/rewatch/viewing/relations/interactions contribute transparent summary/evidence sections (favorites, disliked works, rewatch signals, relation evidence, recommendation outcomes) but do not fabricate term affinities. Explicit persistent rules/constraints are copied into the target profile with provenance.

- [ ] **Step 4: Run tests and confirm failure**

Run: `python -m pytest tests/media/test_build_profiles.py -v`

Expected: FAIL before implementation.

- [ ] **Step 5: Implement profile builder and stable output**

Generated profiles include `schema_version`, `target`, `generated_from`, `affinities`, `explicit_preferences`, `rules`, `constraints`, `summary`, and `evidence`. They remain fully derived and can be deleted/recreated.

- [ ] **Step 6: Run tests and build real profiles**

Run: `python -m pytest tests/media/test_build_profiles.py -v && python -m media.tools.build_profiles .`

Expected: PASS and all three profile files produced even when partner/couple evidence is sparse.

- [ ] **Step 7: Commit**

```bash
git add media/tools/build_profiles.py tests/media/test_build_profiles.py media/generated/profiles
git commit -m "feat: build derived viewer and couple profiles"
```

### Task 8: Rebuildable SQLite Runtime Database

**Files:**
- Create: `media/tools/build_db.py`
- Create: `tests/media/test_build_db.py`
- Create/Modify: `media/.gitignore`

**Interfaces:**
- Produces: `build_database(repo_root: Path, output: Path) -> None`.
- CLI: `python -m media.tools.build_db [repo-root] [--output media/generated/database.sqlite]`.

- [ ] **Step 1: Write failing database rebuild tests**

Build from a canonical fixture into a temp SQLite file; assert tables for `works`, `people_refs`, `terms`, `viewer_signals`, `group_signals`, `seasons`, `collections`, `collection_members`, `lists`, `list_members`, `interactions`, `relations`, and `target_states`. Assert the database can be deleted and rebuilt with the same logical row counts.

- [ ] **Step 2: Add identity constraint tests**

Assert SQLite uniqueness mirrors canonical rules: non-null IMDb unique; `(tmdb_media_type, tmdb_id)` composite unique; same numeric TMDB ID with different media type succeeds.

- [ ] **Step 3: Run tests and confirm failure**

Run: `python -m pytest tests/media/test_build_db.py -v`

Expected: FAIL before implementation.

- [ ] **Step 4: Implement atomic SQLite builder**

Build to a temporary file, create all tables/indexes, load canonical YAML/JSONL only, commit SQLite transaction, then atomically replace the target path. Include effective display/search fields, runtime/production/synopsis/assets/external metrics where present, but never write back from SQLite to YAML.

- [ ] **Step 5: Ignore database and future binary caches**

`media/.gitignore` must include `generated/database.sqlite`, `generated/*.sqlite-*`, `generated/embeddings/`, and image/cache directories while keeping generated text index/profiles trackable.

- [ ] **Step 6: Run tests and build the real local DB**

Run: `python -m pytest tests/media/test_build_db.py -v && python -m media.tools.build_db .`

Expected: PASS; SQLite exists locally and `git status` does not list it.

- [ ] **Step 7: Commit**

```bash
git add media/tools/build_db.py media/.gitignore tests/media/test_build_db.py
git commit -m "feat: add rebuildable media SQLite runtime"
```

### Task 9: Operational Contract and Documentation

**Files:**
- Create: `media/AGENTS.md`
- Create: `media/README.md`
- Modify: `README.md`
- Create: `tests/media/test_acceptance.py`

**Interfaces:**
- Consumes: all canonical schemas/tools.
- Produces: documented commands and write contract for LLM/Web UI/CLI clients.

- [ ] **Step 1: Write failing documentation/acceptance assertions**

`test_acceptance.py` asserts documented core paths exist, generated SQLite is ignored, every schema is loadable, config contains only `primary/partner/couple`, and README commands reference real modules.

- [ ] **Step 2: Write `media/AGENTS.md` as the strict write protocol**

Include the approved rules: read schemas/vocabulary before writes; search/deduplicate first; resolve tombstones; unknown beats guessed; no schema change during data entry; no vocabulary synonym creation; no signal without evidence; preserve explicit/inferred provenance; do not persist ephemeral context; validate the full logical change-set before commit; generated data is never source of truth; one logical operation per commit.

- [ ] **Step 3: Write `media/README.md`**

Document entity locations, source-of-truth vs generated data, sparse multi-viewer semantics, how to add/update a work manually, and exact commands:

```bash
python -m media.tools.validate .
python -m media.tools.build_index .
python -m media.tools.build_profiles .
python -m media.tools.build_db .
```

Explain that metadata enrichment is permitted when a reliable provider is available but the current implementation does not include a background TMDB client/service.

- [ ] **Step 4: Update root README**

Replace the `movies/README.md` navigation with `media/README.md` and describe the section as films/series/animation with multi-viewer recommendations.

- [ ] **Step 5: Run documentation acceptance tests**

Run: `python -m pytest tests/media/test_acceptance.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add README.md media/AGENTS.md media/README.md tests/media/test_acceptance.py
git commit -m "docs: document v4 media write protocol"
```

### Task 10: Full Acceptance, Legacy Cutover, and Final Verification

**Files:**
- Delete after successful verification: `movies/data/movies.yaml`
- Delete after successful verification: `movies/profile.md`
- Delete after successful verification: `movies/schema.md`
- Delete after successful verification: `movies/README.md`
- Verify: all `media/**`, generated text artifacts, root README.

**Interfaces:**
- Consumes: every deliverable from Tasks 1–9.
- Produces: v4 as the sole active media source of truth.

- [ ] **Step 1: Run the complete test suite before deleting legacy data**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 2: Run repository validation and regenerate all derived artifacts from scratch**

```bash
rm -f media/generated/index.jsonl media/generated/profiles/*.yaml media/generated/database.sqlite
python -m media.tools.validate .
python -m media.tools.build_index .
python -m media.tools.build_profiles .
python -m media.tools.build_db .
python -m media.tools.validate .
```

Expected: every command exits 0; text artifacts are recreated; SQLite is recreated but ignored.

- [ ] **Step 3: Run legacy parity check one final time**

Run migration in `--check` mode against the still-present `movies/data/movies.yaml`; assert all legacy IDs/ratings/comments/statuses have matching v4 canonical entities and that no legacy collection rating leaked to a member.

- [ ] **Step 4: Delete legacy active source files**

Remove the four `movies/` files listed above. Git history and the superseded v3 design doc remain the historical record; do not create an archive that could be mistaken for a current source of truth.

- [ ] **Step 5: Re-run tests/validation without legacy files**

```bash
python -m pytest -v
python -m media.tools.validate .
python -m media.tools.build_index .
python -m media.tools.build_profiles .
python -m media.tools.build_db .
```

Expected: PASS/exit 0 without reading anything from `movies/`.

- [ ] **Step 6: Inspect Git status for source-of-truth mistakes**

Expected: no `database.sqlite`, cache, image, or embedding artifact is staged; only canonical YAML, schemas/tools/tests/docs, and generated text index/profiles are tracked.

- [ ] **Step 7: Commit the cutover**

```bash
git add -A
git commit -m "refactor: cut over media library to v4"
```

- [ ] **Step 8: Final acceptance check against the approved spec**

Confirm explicitly: migration preserves existing meaning; sparse `partner: liked` is supported; seasonless series are valid; `primary|partner|couple` targets work; vocabulary/schema drift is rejected; ephemeral request context has no canonical storage path; generated index/profiles/SQLite rebuild from YAML; TMDB movie/TV numeric collision is safe; deleting SQLite loses no information.
