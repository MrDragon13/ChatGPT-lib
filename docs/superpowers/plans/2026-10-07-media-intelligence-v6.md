# Media Intelligence v6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перевести медиаподсистему на v6 так, чтобы обычный отзыв сохранялся одной типизированной операцией и одним основным циклом GitHub Actions, без лишнего provider/semantic/metadata/rebuild I/O, при сохранении всех качественных гарантий v5.1.

**Architecture:** Git/YAML в `main` остаётся единственным долговременным источником состояния. Доменная логика сообщает, какие области изменились; отдельный планировщик зависимостей определяет минимальный набор производных данных для пересборки. Новый `record_media_entry` объединяет создание нового произведения и пользовательские сигналы, а глубокий анализ вкусов сохраняется отдельно через `set_inferred_preferences` с контрольной точкой evidence.

**Tech Stack:** Python 3.12, YAML/JSON, JSON Schema 2020-12, pytest, GitHub Actions/GitHub API, Cloudflare Worker + TypeScript/Vitest, React/Vite + Vitest/Playwright.

**Spec:** `docs/superpowers/specs/2026-10-07-media-intelligence-v6-design.md`

## Global Constraints

- `main` + canonical Git/YAML остаются единственным долговременным источником состояния; `media/generated/**` — только производные данные.
- Обычный отзыв о существующем произведении: 0 provider calls, 0 metadata refresh, 0 semantic recomputation при неизменном semantic key, 1 typed operation, 1 request PR, 1 основной data-CI cold start, 1 canonical transaction, не более 1 rebuild каждого нужного результата, 1 merge.
- Новое произведение: 1 этап определения identity/provider facts, 1 LLM semantic pass, 1 typed operation, 1 canonical transaction, не более 1 rebuild каждого нужного результата, 1 data-CI cycle, 1 merge.
- `record_media_entry` — основной LLM write route; он не превращается в универсальный bundle engine.
- `set_inferred_preferences` остаётся отдельной операцией. Порог автоматического повторного анализа вкусов настраиваемый, значение по умолчанию — `5` материальных пользовательских событий.
- Для `primary` и `partner` контрольные точки анализа вкусов независимы; у `couple` нет отдельного автоматического счётчика.
- Если по тому же произведению уже есть pending write, разговор может учитывать новое уточнение локально, но второй Git write отправляется только после подтверждения первой операции и чтения свежего `viewer_digest`.
- До исполнения request PR содержит только `.media/requests/<operation-id>.json`; canonical/generated diff строит доверенный runner на свежем `main`.
- Обычная операция с данными должна сливаться через GitHub API; прямой push результата в `main` запрещён. Перед merge повторно проверяется base SHA; при изменившемся `main` запрос заново накладывается и валидируется.
- SQLite не становится canonical или versioned generated storage. Существующие `build_db.py`/`SQLiteRepository` допустимы только как невёрсионируемый производный инструмент диагностики/тестов и не входят в v6 critical path.
- Reset выполняется только после детерминированной генерации MD-архива и точной проверки `committed archive == regenerated archive` из того же состояния, которое будет сброшено.
- Старые глобальные explicit preferences и vocabulary сохраняются; works/collections/similarities/interactions/inferred preferences/legacy pilot очищаются.
- Historical v5/v5.1 specs не переписываются. Все README и living docs, затронутые v6, обновляются синхронно с фактическим поведением.
- Документация по возможности пишется простым русским языком; английский сохраняется для точных имён API, команд, полей, классов, файлов и технологий.
- Каждый крупный implementation PR после значимого этапа и перед паузой получает checkpoint-комментарий: сделано, текущий commit/head, прошедшие проверки, незаконченные места/риски, следующий шаг, оставшийся план.
- TDD обязателен: сначала падающий тест, затем минимальная реализация, затем целевая проверка, затем commit.

## Review Focus

1. **Повтор того же человеческого события:** одинаковый `idempotency_key` не должен добавлять history/evidence второй раз; тот же ключ с другим payload должен fail closed. Тесты — Task 3.
2. **Уточнение того же work пока первая запись pending:** клиент не создаёт второй Git write от optimistic digest; LLM накапливает уточнение локально, Web блокирует повторную отправку. Тесты — Task 8 и агентский контракт Task 12.
3. **`main` изменился между apply и merge:** проверенный head нельзя сливать поверх непроверенной базы; request должен быть replay/revalidated. Тесты — Task 7.
4. **Taste snapshot устарел до merge:** новый explicit evidence после snapshot не должен считаться покрытым старой контрольной точкой. Тесты — Task 4.
5. **Архив формально имеет правильное количество строк, но неверное содержимое:** reset должен блокироваться, пока побайтовая детерминированная регенерация не совпадает с committed MD. Тесты — Task 9/Task 11.

## Delivery Structure

- **PR 1 — v6 domain core:** Tasks 1–6. Новые контракты и read/write primitives появляются, но `AGENTS.md` ещё не переключает пользователя на v6 и старый runtime остаётся рабочим.
- **PR 2 — pipeline + Broker/Web compatibility:** Tasks 7–8. Новый быстрый pipeline и клиентская совместимость готовы, но финальный reset/agent cutover ещё не выполнен.
- **PR 3 — archive tooling:** Task 9. Генератор архива и точная проверка готовы; можно создать review snapshot, но финальный архив всё равно регенерируется в PR 4 из точного pre-reset состояния.
- **PR 4 — atomic cutover:** Tasks 10–12. Переносятся нужные regression fixtures, удаляется legacy runtime, создаётся финальный архив, выполняется reset, обновляются все living docs и включается v6 как единственный нормальный путь.

---

## PR 1 — v6 domain core

### Task 1: Контрольные хэши, семантический ключ и материальные evidence-события

**Files:**
- Create: `media/domain/digests.py`
- Create: `media/domain/freshness.py`
- Modify: `media/schemas/common.schema.json`
- Modify: `media/schemas/work.schema.json`
- Test: `tests/media/test_v6_digests.py`
- Test: `tests/media/test_work_schema.py`

**Interfaces:**
- Produces: `compute_viewer_digest(document: Mapping[str, Any], target: str) -> str`
- Produces: `compute_vocabulary_digest(media_root: Path) -> str`
- Produces: `semantic_input_projection(document: Mapping[str, Any]) -> Mapping[str, Any]`
- Produces: `compute_semantic_input_digest(document: Mapping[str, Any], vocabulary_digest: str, algorithm_version: str) -> str`
- Produces: `material_evidence_projection(signal: Mapping[str, Any] | None) -> Mapping[str, Any]`
- Produces: `is_material_evidence_change(before: Mapping[str, Any] | None, after: Mapping[str, Any] | None) -> bool`
- Produces: `evaluate_metadata_freshness(document: Mapping[str, Any]) -> Mapping[str, str]`
- Schema change: history entries may carry optional `event_id` and `material_evidence`; work semantic metadata may carry `input_digest`, `vocabulary_digest`, `algorithm_version`.

- [ ] **Step 1: Write failing digest-isolation tests**

Add tests asserting:

```python
assert compute_viewer_digest(work_before, "primary") == compute_viewer_digest(metadata_only_change, "primary")
assert compute_semantic_input_digest(work, vocab_digest, "media-semantic-v1") == compute_semantic_input_digest(dynamic_metric_only_change, vocab_digest, "media-semantic-v1")
assert compute_semantic_input_digest(work, vocab_digest, "media-semantic-v1") != compute_semantic_input_digest(static_fact_change, vocab_digest, "media-semantic-v1")
```

Also assert summary-only typo correction is not material when structured rating/reaction/viewing/feedback signals are unchanged. In v6, substantive textual taste evidence must be normalized by the LLM into `feedback.signals`; `feedback.summary` by itself is display/history text and does not advance the automatic taste-reanalysis checkpoint.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python -m pytest tests/media/test_v6_digests.py tests/media/test_work_schema.py -q`

Expected: FAIL because v6 digest functions/schema fields do not exist.

- [ ] **Step 3: Implement canonical digest helpers and semantic projection**

Use deterministic JSON serialization (`sort_keys=True`, compact separators, UTF-8) and prefix SHA-256 values with `sha256:`. `semantic_input_projection` must exclude viewer/group signals, history and dynamic provider metrics; include only identity/static factual fields that are allowed to affect the work fingerprint.

- [ ] **Step 4: Implement pure metadata freshness classification**

`evaluate_metadata_freshness()` must return separate statuses for identity/static/dynamic classes without performing provider I/O. Initial v6 policy is conservative: missing data may be reported as missing; no automatic provider refresh is triggered from this function.

- [ ] **Step 5: Extend schemas without breaking current v5 writes**

Add optional v6 history/semantic bookkeeping fields. Do not make old v5 records invalid in PR 1.

- [ ] **Step 6: Run focused and schema regression tests**

Run: `python -m pytest tests/media/test_v6_digests.py tests/media/test_work_schema.py tests/media/test_validator.py -q`

Expected: PASS.

- [ ] **Step 7: Commit and checkpoint**

```bash
git add media/domain/digests.py media/domain/freshness.py media/schemas/common.schema.json media/schemas/work.schema.json tests/media/test_v6_digests.py tests/media/test_work_schema.py
git commit -m "feat: add v6 digest and freshness primitives"
```

Update the PR checkpoint comment with tests and next step.

### Task 2: `changed_domains → DirtyPlan` и единичная пересборка

**Files:**
- Modify: `media/domain/changeset.py`
- Create: `media/service/derived.py`
- Modify: `media/service/transaction.py`
- Modify: `media/service/mutate.py`
- Modify: `media/service/enrich.py`
- Modify: `media/service/intelligence.py`
- Modify: `media/service/preferences.py`
- Modify: `media/service/interactions.py`
- Modify: `media/service/refresh.py`
- Modify: `media/service/similarity.py`
- Modify: `media/service/reassessment_mutate.py`
- Test: `tests/media/test_v6_dirty_plan.py`
- Test: `tests/media/test_transaction.py`
- Test: existing operation-specific tests touched by constructor changes.

**Interfaces:**
- `MutationPlan` produces `changed_domains: tuple[str, ...]` instead of business code choosing generated outputs.
- Produces: `DirtyPlan(rebuild_index: bool, rebuild_profile_targets: tuple[str, ...])`
- Produces: `derive_dirty_plan(repo: YamlRepository, plan: MutationPlan) -> DirtyPlan`
- `transaction.execute_command()` consumes `DirtyPlan` and rebuilds every affected output at most once.

- [ ] **Step 1: Write failing dependency tests**

Cover at minimum:
- `viewer:primary` → index + `primary` + groups containing primary, not partner.
- metadata-only → index, no profiles.
- dynamic metric-only metadata change → index only, semantics unchanged.
- semantics change → index + only profiles whose rating evidence uses that work.
- inferred preference target → only that target profile.
- similarity-only → no index/profile rebuild unless an explicit existing consumer requires it.
- duplicate changed domains still rebuild each output once.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `python -m pytest tests/media/test_v6_dirty_plan.py tests/media/test_transaction.py -q`

Expected: FAIL because `DirtyPlan` and `changed_domains` are absent.

- [ ] **Step 3: Add `changed_domains` and dependency planner**

Use stable string domains such as `work.identity`, `work.metadata`, `work.semantics`, `viewer:<target>`, `interest:<target>`, `preferences.inferred:<target>`, `interaction:<target>`, `similarity:<target>`.

- [ ] **Step 4: Migrate planners to declare domains, not rebuild flags**

Move output-dependency knowledge into `media/service/derived.py`. Domain planners may calculate what changed, but must not call `build_profile()` or `write_index()`.

- [ ] **Step 5: Make transaction rebuild once after all canonical mutations**

`execute_command()` must derive one `DirtyPlan` after planning and perform one rebuild pass. Keep temp-tree validation and rollback behavior intact.

- [ ] **Step 6: Run operation regression suite**

Run: `python -m pytest tests/media/test_transaction.py tests/media/test_mutations.py tests/media/test_semantic_fingerprint.py tests/media/test_inferred_preferences.py tests/media/test_refresh_work_metadata.py tests/media/test_work_similarity.py -q`

Expected: PASS.

- [ ] **Step 7: Commit and checkpoint**

```bash
git add media/domain/changeset.py media/service tests/media/test_v6_dirty_plan.py tests/media/test_transaction.py
git commit -m "refactor: derive v6 rebuilds from changed domains"
```

Update the PR checkpoint comment.

### Task 3: `record_media_entry` — единая атомарная запись

**Files:**
- Create: `media/commands/schemas/record_media_entry.schema.json`
- Modify: `media/commands/schemas/common.schema.json`
- Modify: `media/domain/commands.py`
- Modify: `media/domain/types.py`
- Modify: `media/commands/schema.py`
- Create: `media/service/media_entry.py`
- Modify: `media/service/mutate.py`
- Modify: `media/service/transaction.py`
- Modify: `media/service/enrich.py`
- Modify: `media/service/intelligence.py`
- Modify: `media/config/operation_path_policy.json`
- Modify: `media/cli.py`
- Test: `tests/media/test_record_media_entry.py`
- Test: `tests/media/test_command_contracts.py`
- Test: `tests/media/test_path_policy.py`
- Test: `tests/media/test_transaction.py`

**Interfaces:**
- Produces `RecordMediaEntryCommand` with fields:
  - `schema_version: int`
  - `operation_id: str`
  - `idempotency_key: str`
  - `work_ref: WorkRef`
  - `create_if_missing: bool`
  - `target_updates: tuple[TargetUpdate, ...]`
  - `creation_context: CreationContext | None`
  - `semantic_snapshot: SemanticSnapshot | None`
  - `preconditions: MediaEntryPreconditions` with `expected_viewer_digests: Mapping[str, str]`
- The JSON schema keeps these digests nested under `preconditions.expected_viewer_digests`; the typed command preserves the same nested meaning instead of inventing a second flat wire format.
- Produces `plan_record_media_entry(repo, command, provider, now=None) -> MutationPlan`.
- `idempotency_key` is a canonical lowercase UUID identifying the human event; `operation_id` identifies one execution attempt.

- [ ] **Step 1: Write failing schema/parser tests**

Assert:
- existing-work command parses with no creation/semantic payload;
- `create_if_missing=true` requires both `creation_context` and `semantic_snapshot`;
- при `create_if_missing=false` каждый target update имеет matching expected viewer digest; для действительно нового work отсутствие viewer state защищается самим условием отсутствия work;
- both UUIDs are canonical lowercase UUID text;
- unknown fields fail closed.

- [ ] **Step 2: Write failing existing-work fast-path test**

Use a provider fake that raises if called. Apply rating+reaction+feedback to an existing work and assert:
- provider calls == 0;
- semantic block byte-equivalent;
- metadata byte-equivalent;
- one history entry for the target;
- history entry carries `event_id=idempotency_key`;
- `material_evidence` is true only for material structured evidence changes;
- generated outputs match `DirtyPlan` and each rebuild helper is invoked at most once.

- [ ] **Step 3: Write failing stale-digest and idempotency tests**

Assert:
- stale `expected_viewer_digest` fails before any provider call or mutation;
- retry with same `idempotency_key` and same normalized command returns `already_applied` without history/rebuild duplication;
- same `idempotency_key` with different normalized command raises `CommandValidationError`.

- [ ] **Step 4: Write failing new-work atomicity tests**

With a fake TMDB provider, assert:
- one provider fetch using stable provider identity;
- provider identity/minimum static facts are checked against `creation_context`;
- current vocabulary digest and semantic input digest must match `semantic_snapshot`;
- invalid vocabulary/reaction trait or provider mismatch leaves repository byte-identical;
- valid new work + semantic traits + viewer feedback commit as one plan/transaction.

- [ ] **Step 5: Implement command dataclasses and schema parsing**

`CreationContext` is a strict object with `resolved_identity`, `provider_identity`, and `minimum_metadata`. `resolved_identity` carries the canonical identity fields needed to create the work (`format`, titles, year/release date when known, stable external IDs); `provider_identity` is the stable provider pair (`media_type`, `id`); `minimum_metadata` contains only the factual fields actually supplied to semantic analysis. `SemanticSnapshot` contains `traits`, `semantic_input_digest`, `vocabulary_digest`, and `algorithm_version`. The repository must recompute the factual projection from provider data and reject any mismatch rather than trusting duplicated client facts.

- [ ] **Step 6: Implement `plan_record_media_entry`**

Resolve existing work first. Existing work must never require provider setup. For a missing work, fetch by the stable provider ID, verify identity/factual projection, build canonical work, validate semantic snapshot, apply viewer updates, and return one `MutationPlan`.

- [ ] **Step 7: Implement receipt-level idempotency**

Persist `idempotency_key` and a deterministic normalized request digest in the operation receipt. Before planning side effects, search existing operation receipts for the key: same key + same request digest returns `already_applied`; same key + different request digest fails closed. Keep this as a simple local receipt scan in v6; add a separate index only if measurements later prove the scan material.

- [ ] **Step 8: Wire provider detection and path policy**

`media.cli apply-command` and `media-command.yml` provider detection must treat `record_media_entry` as provider-dependent only when creation is actually required by the command path.

- [ ] **Step 9: Run focused tests**

Run: `python -m pytest tests/media/test_record_media_entry.py tests/media/test_command_contracts.py tests/media/test_path_policy.py tests/media/test_transaction.py -q`

Expected: PASS.

- [ ] **Step 10: Commit and checkpoint**

```bash
git add media/commands media/domain media/service media/config/operation_path_policy.json media/cli.py tests/media
git commit -m "feat: add atomic record_media_entry command"
```

Update the PR checkpoint comment.

### Task 4: Контрольные точки повторного анализа вкусов

**Files:**
- Create: `media/config/intelligence.yaml` (`taste_reanalysis_threshold: 5`, `semantic_algorithm_version: media-semantic-v1`, `taste_algorithm_version: media-taste-v1`)
- Create: `media/service/reanalysis_status.py`
- Modify: `media/domain/commands.py`
- Modify: `media/commands/schemas/set_inferred_preferences.schema.json`
- Modify: `media/schemas/inferred-preferences.schema.json`
- Modify: `media/commands/schema.py`
- Modify: `media/service/preferences.py`
- Modify: `media/service/taste_context.py`
- Modify: `media/service/recommend.py`
- Modify: `media/service/assessment.py`
- Test: `tests/media/test_v6_reanalysis_status.py`
- Test: `tests/media/test_inferred_preferences.py`
- Test: `tests/media/test_taste_context.py`
- Test: `tests/media/test_recommend_context.py`
- Test: `tests/media/test_candidate_assessment.py`

**Interfaces:**
- Config: `taste_reanalysis_threshold: 5`.
- Produces `EvidenceCheckpoint(material_event_count: int, material_event_prefix_digest: str)`.
- Produces `ReanalysisStatus(target, threshold, outstanding_count, due, checkpoint_valid, current_evidence_digest)`, where `due` is true when `outstanding_count >= threshold` or the checkpoint is invalid because current material state cannot be reconciled with its recorded event prefix. A mere digest change with fewer than 5 valid new material events does **not** make the profile due.
- Produces `get_reanalysis_status(repo_root: Path, target: str) -> ReanalysisStatus`.
- `SetInferredPreferencesCommand.analysis` contains `evidence_checkpoint`, `evidence_digest`, `algorithm_version`; v6 writes use `media-taste-v1`.

- [ ] **Step 1: Write failing threshold/checkpoint tests**

Assert:
- 4 material events since checkpoint → `due is False`;
- 5 → `due is True`;
- summary-only typo/no-change/retry does not increment;
- later material update to the same work can increment once;
- successful reanalysis on current evidence resets outstanding count;
- an event added after analysis snapshot remains outstanding after the profile operation;
- invalid checkpoint prefix or destructive evidence change fails safe with `checkpoint_valid=False` and requires fresh analysis.

- [ ] **Step 2: Write couple status tests**

For `couple`, return member statuses for `primary` and `partner`; do not create a third counter.

- [ ] **Step 3: Extend inferred preference schemas**

Keep PR 1 backward-compatible with existing v5 inferred files while accepting the v6 `analysis` block. Validation of a v6 reanalysis write must prove that the submitted `evidence_digest` and checkpoint describe current explicit evidence.

- [ ] **Step 4: Implement evidence event stream from canonical histories**

Use v6 history `event_id` + `material_evidence` to produce a stable ordered stream per viewer target. Store count + prefix digest in the checkpoint. `outstanding_count` is the number of valid material events after that prefix; `due` is normally `outstanding_count >= threshold`. Compute `evidence_digest` from the same material evidence projection (rating/reaction/viewing/structured feedback signals, not summary-only text), so a changed digest by itself does not force reanalysis while fewer than 5 valid new events are outstanding. If the material state changes without a corresponding append-only material event (for example destructive purge), mark the checkpoint invalid and require fresh analysis immediately.

- [ ] **Step 5: Surface status in taste-dependent read contexts**

`taste_context`, recommendation context and candidate assessment must expose reanalysis status/limitations so the agent can enforce “reanalyze first when due”. Do not block pure lookup.

- [ ] **Step 6: Run focused tests**

Run: `python -m pytest tests/media/test_v6_reanalysis_status.py tests/media/test_inferred_preferences.py tests/media/test_taste_context.py tests/media/test_recommend_context.py tests/media/test_candidate_assessment.py -q`

Expected: PASS.

- [ ] **Step 7: Commit and checkpoint**

```bash
git add media/config/intelligence.yaml media/service/reanalysis_status.py media/domain/commands.py media/commands media/schemas/inferred-preferences.schema.json media/service/preferences.py media/service/taste_context.py media/service/recommend.py media/service/assessment.py tests/media
git commit -m "feat: add evidence checkpointed taste reanalysis"
```

Update the PR checkpoint comment.

### Task 5: Компактный `media_entry_context` и viewer digests для клиентов

**Files:**
- Create: `media/commands/schemas/media_entry_context.schema.json`
- Modify: `media/domain/commands.py`
- Modify: `media/commands/schema.py`
- Create: `media/service/media_entry_context.py`
- Modify: `media/cli.py`
- Modify: `media/tools/build_index.py`
- Modify: `media/service/web_export.py` only if the existing manifest serializer needs to explicitly omit internal digest fields.
- Test: `tests/media/test_media_entry_context.py`
- Test: `tests/media/test_build_index.py`
- Test: `tests/media/test_web_export.py`
- Test: `tests/media/test_cli.py`

**Interfaces:**
- Produces read request `MediaEntryContextRequest(schema_version: int, work_ref: WorkRef, target: str)`.
- Produces `build_media_entry_context(media_root: Path, request: MediaEntryContextRequest) -> dict[str, Any]`.
- CLI: `python -m media.cli media-entry-context --request <request.json> --format json`.
- Generated index exposes viewer digests for trusted read/Broker use; the public Web manifest does not need to expose them unless a later measured need appears.

- [ ] **Step 1: Write failing compact-context tests**

Assert the JSON contains only identity, selected target state/digest, metadata freshness, semantic status/key, minimum factual fields and interest. Assert it omits full history, complete profiles and unrelated targets.

- [ ] **Step 2: Write missing-work context test**

A resolvable absence returns `exists=false` plus the supplied stable identity fields; it must not fabricate provider facts.

- [ ] **Step 3: Add deterministic viewer digests to the internal generated index**

Expose a digest even for an absent configured target signal so first writes can carry an expected digest. Keep full feedback history out of generated projections. `web_export` must not accidentally leak internal-only digest fields unless explicitly required.

- [ ] **Step 4: Implement CLI/read service**

Serialize JSON compactly for `--format json`. Do not impose a tokenizer-specific token limit; tests should assert allowed keys and, if useful, a byte-size ceiling for representative fixtures.

- [ ] **Step 5: Run Python and Web type tests**

Run: `python -m pytest tests/media/test_media_entry_context.py tests/media/test_build_index.py tests/media/test_web_export.py tests/media/test_cli.py -q`

Expected: PASS.

- [ ] **Step 6: Commit and checkpoint**

```bash
git add media/commands media/domain/commands.py media/service/media_entry_context.py media/cli.py media/tools/build_index.py media/service/web_export.py tests/media
git commit -m "feat: add compact media entry context"
```

Update the PR checkpoint comment.

### Task 6: PR 1 performance contract, local parity and dormant-core verification

**Files:**
- Create: `tests/media/test_v6_performance_contract.py`
- Modify: `tests/media/test_tooling_e2e.py`
- Modify: `tests/media/test_v51_command_contracts.py` as needed for coexistence only.
- Modify: `docs/status/current.md` only to mention dormant v6 implementation work if the existing documentation contract requires status; do not switch capability to v6 yet.

**Interfaces:**
- No new runtime interface; this task proves structural latency invariants and that all v6 writes run through `apply-command`/`--dry-run` locally.

- [ ] **Step 1: Add failing performance-contract spies**

For existing-work `record_media_entry`, spy/monkeypatch provider and rebuild helpers and assert provider=0, metadata refresh=0, semantic recompute=0, one transaction, each dirty output ≤1.

For `no_change`, assert no generated rebuild and no history/evidence append.

- [ ] **Step 2: Add local CLI parity tests**

Exercise both `record_media_entry` and v6 `set_inferred_preferences` through:

```bash
python -m media.cli apply-command request.json --dry-run --format json
python -m media.cli apply-command request.json --format json
```

- [ ] **Step 3: Run PR 1 full media gate**

Run:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Expected: all PASS/OK; `doctor` may build SQLite only in temp and must still report it as untracked.

- [ ] **Step 4: Commit and create PR 1 checkpoint**

```bash
git add tests/media docs/status/current.md
git commit -m "test: lock v6 domain performance contracts"
```

PR checkpoint must state that v6 core exists but agent/Broker cutover has not happened.

---

## PR 2 — pipeline + Broker/Web compatibility

### Task 7: Один основной data runner с exact-base merge guard

**Files:**
- Modify: `.github/workflows/media-command.yml`
- Modify: `.github/workflows/media-check.yml`
- Modify: `.github/workflows/media-auto-merge.yml`
- Modify: `.github/workflows/media-dev-check.yml`
- Modify: `.github/workflows/media-pages.yml`
- Modify: `media/config/operation_path_policy.json`
- Test: `tests/media/test_workflows.py`
- Test: `tests/media/test_auto_merge_dispatch_contract.py`
- Test: `tests/media/test_pages_contract.py`
- Test: `tests/media/test_review_regressions.py`

**Interfaces:**
- v6 normal data operations: request-only PR → replay on latest `main` → apply → targeted authoritative gate → commit/push exact head → recheck `main` base → GitHub API merge exact head → dispatch Pages for merge SHA.
- Legacy reassessment may temporarily keep the old check/auto-merge route until PR 4; v6 normal operations must not pay that extra cold-start cost.

- [ ] **Step 1: Write failing workflow contract tests**

Assert for v6 operation kinds:
- PR pre-execution diff contains exactly one request file;
- no `media-check.yml` dispatch;
- no separate `media-auto-merge.yml` dependency;
- merge uses GitHub API with exact head SHA;
- direct `git push HEAD:main` is absent;
- provider secret is exposed only when new-work creation actually needs provider verification.

- [ ] **Step 2: Add changed-main replay test at workflow-contract level**

Test the workflow/script text or extracted helper so that a changed `origin/main` forces request replay + revalidation before merge, not blind merge of previously checked output.

- [ ] **Step 3: Refactor `Media Command` v6 branch**

Keep the request bytes in trusted temp storage, rebuild the operation branch from the latest `main`, restore only the request, apply/validate, and push the checked result. If `main` moves before merge, repeat the replay/validation cycle; cap retries and fail closed rather than looping indefinitely.

- [ ] **Step 4: Move guarded v6 merge into the same workflow**

Use GitHub API PR merge with expected head SHA. Do not require repository auto-merge settings and do not bypass PR semantics by pushing directly to `main`.

- [ ] **Step 5: Keep Pages post-merge and outside save latency**

Dispatch `media-pages.yml` for the exact merge SHA. `published` is a website state; `authoritative/saved` is reached at merge and must not wait for Pages.

- [ ] **Step 6: Audit every workflow trigger**

Verify data-result commits do not trigger unrelated full Dev/Web checks. Preserve full gates for code/schema/workflow/vocabulary changes. Do not add broad `paths-ignore` where current event type already makes them unnecessary.

- [ ] **Step 7: Run workflow tests**

Run: `python -m pytest tests/media/test_workflows.py tests/media/test_auto_merge_dispatch_contract.py tests/media/test_pages_contract.py tests/media/test_review_regressions.py -q`

Expected: PASS.

- [ ] **Step 8: Commit and checkpoint**

```bash
git add .github/workflows media/config/operation_path_policy.json tests/media
git commit -m "ci: add single-runner v6 data pipeline"
```

Update PR checkpoint with which legacy routes remain temporarily and why.

### Task 8: Broker/Web compatibility and pending same-work rule

**Files:**
- Modify: `broker/src/operations.ts`
- Modify: `broker/src/feedback.ts`
- Modify: `broker/src/github.ts` only if exact request/PR metadata needs adjustment.
- Modify: `broker/test/feedback.test.ts`
- Modify: `broker/test/submit.test.ts`
- Modify: `broker/test/status.test.ts`
- Modify: `broker/test/conflict.test.ts`
- Modify: `web/src/broker/types.ts` only if operation status typing changes.
- Modify: `web/src/broker/client.ts` only if status handling changes.
- Modify: `web/src/features/detail/FeedbackEditor.tsx`
- Modify: relevant `web/src/features/detail/*feedback*.test.tsx`

**Interfaces:**
- Browser feedback remains `/v1/feedback`. PR 2 teaches Broker to support the v6 mapping while preserving the current v5-compatible live contract; the live route is switched to `record_media_entry` only in PR 4 together with the product cutover.
- Broker reads the viewer digest from the generated index at the exact `main` SHA used to create the operation branch and places it in `preconditions.expected_viewer_digests[target]`; the browser request shape can remain backward-compatible.
- Browser may have only one active write per `(work_id, target)`; second submit remains blocked while pending.

- [ ] **Step 1: Write failing Broker command tests**

Assert Broker reads `media/generated/index.jsonl` at the same `main` SHA used for the operation branch, obtains the target viewer digest, and generates `record_media_entry` with distinct `operation_id`/`idempotency_key`, `create_if_missing=false`, the expected digest and one target update.

- [ ] **Step 2: Write failing active-operation tests**

A second `/v1/feedback` for the same `(work,target)` while an operation PR is open returns the existing active operation/409 path and does not create a second request PR.

- [ ] **Step 3: Adapt status mapping to same-runner merge**

The Broker must not wait for `Media Check`/`Media Auto Merge` for a v6 operation. Once PR is merged, return `merged`; Pages success later returns `published`.

- [ ] **Step 4: Preserve backward-compatible Web input and enforce pending behavior**

Do not require the browser to know internal digests. Disable/reject a second submit while pending; keep the form readable and preserve the user-entered draft if they continue editing locally.

- [ ] **Step 5: Run Broker tests**

Run: `cd broker && npm test`

Expected: PASS.

- [ ] **Step 6: Run focused Web tests**

Run: `cd web && npm run test:run -- src/broker/client.test.ts src/features/detail/feedback-editor.test.tsx src/features/detail/feedback-editor-retry.test.tsx`

Expected: PASS.

- [ ] **Step 7: Commit and checkpoint**

```bash
git add broker web
git commit -m "feat: adapt broker and web to v6 feedback contract"
```

Checkpoint must state that the production Broker has **not** been switched to the v6 live route yet. If PR 2 changes deployable code, do not dispatch `broker-deploy.yml` for the v6 route until PR 4. User-visible cutover remains deferred to PR 4.

---

## PR 3 — deterministic archive tooling

### Task 9: Генератор и точная проверка pre-v6 MD-архива

**Files:**
- Create: `media/tools/archive_library.py`
- Create: `tests/media/test_archive_library.py`
- Create: `docs/archive/.gitkeep` only if Git requires the directory before the snapshot exists.
- Modify: `media/README.md` only to document the tool, without declaring reset complete.

**Interfaces:**
- Produces: `render_library_archive(media_root: Path) -> str`
- Produces: `write_library_archive(repo_root: Path, output: Path) -> Path`
- Produces: `verify_library_archive(repo_root: Path, output: Path) -> list[str]` where empty list means exact match.
- CLI:
  - `python -m media.tools.archive_library --output docs/archive/media-library-before-v6-reset-2026-10-07.md`
  - `python -m media.tools.archive_library --output ... --verify`

- [ ] **Step 1: Write failing archive-content tests**

Fixture must include:
- work with no user data → title/year only;
- exact and approximate ratings rendered in human-readable form;
- primary/partner/couple data where present;
- explicit feedback/notes/signals only where present;
- explicit similarity rendered by human titles, not internal IDs;
- collection names in a separate archive section;
- no provider IDs, operation IDs, digests, semantic fingerprints or inferred hypotheses.

- [ ] **Step 2: Write failing determinism/verification tests**

Generate twice and assert byte equality. Corrupt one archived work while keeping the same entry count and assert `--verify` fails.

- [ ] **Step 3: Implement renderer and CLI**

Do not include a current timestamp or any non-deterministic value in rendered content. Sort entries deterministically by human title/year with a stable fallback.

- [ ] **Step 4: Generate a review snapshot**

Run the generator against current `main`-equivalent data and inspect the MD manually for readability. This snapshot is review material, not yet the authoritative final pre-reset archive.

- [ ] **Step 5: Run archive tests**

Run: `python -m pytest tests/media/test_archive_library.py -q`

Expected: PASS.

- [ ] **Step 6: Commit and checkpoint**

```bash
git add media/tools/archive_library.py tests/media/test_archive_library.py docs/archive media/README.md
git commit -m "feat: add deterministic media library archive tool"
```

Checkpoint explicitly says the final archive will be regenerated and reverified in PR 4 immediately before reset.

---

## PR 4 — atomic cutover

### Task 10: Перенести нужные quality fixtures и подготовить reset migration

**Files:**
- Create: `tests/media/fixtures/v6_quality/` (small synthetic/reference fixtures only)
- Create: `media/tools/migrate_v6_reset.py`
- Create: `tests/media/test_v6_reset.py`
- Modify: `tests/media/test_intelligence_audit*.py` / recommendation tests that currently depend on Stage A baseline, only where required.
- Remove from active runtime at cutover: `media/baselines/intelligence-stage-a.json`, `media/baselines/intelligence-stage-a.meta.json` after required behavior is captured in fixtures.

**Interfaces:**
- Produces a reset planner/tool that refuses to mutate unless the archive verifies exactly.
- Reset preserves `media/preferences/explicit/**`, vocabulary, config, schemas/code and generated directory structure.

- [ ] **Step 1: Identify baseline behaviors that are still quality invariants**

Convert only meaningful behavioral assertions into compact synthetic fixtures: strong positive intrigue/problem-solving, mixed evidence, couple disagreement, sparse semantics, explicit similarity without preference, stale inferred vs fresh explicit.

- [ ] **Step 2: Write failing reset safety tests**

Assert reset refuses when archive verify reports any mismatch. Assert a successful reset removes active works/collections/similarity/interactions/inferred/pilot/baselines but preserves explicit preferences and vocabulary.

- [ ] **Step 3: Implement `migrate_v6_reset.py` as one-time migration tooling**

Support a dry-run/plan mode and an apply mode. The tool must call archive verification before destructive file removal and rebuild generated state after removal.

- [ ] **Step 4: Run fixture/reset tests**

Run: `python -m pytest tests/media/test_v6_reset.py tests/media/test_build_profiles.py tests/media/test_recommend_context.py tests/media/test_candidate_assessment.py -q`

Expected: PASS.

- [ ] **Step 5: Commit and checkpoint**

```bash
git add tests/media/fixtures/v6_quality media/tools/migrate_v6_reset.py tests/media/test_v6_reset.py tests/media
git commit -m "feat: prepare guarded v6 reset migration"
```

Checkpoint lists exactly what will be deleted only in the final cutover step.

### Task 11: Финальный архив, reset, удаление legacy runtime и переключение v6

**Files:**
- Generate/update: `docs/archive/media-library-before-v6-reset-2026-10-07.md`
- Remove: `media/data/works/*.yaml`
- Remove: `media/data/collections/*.yaml`
- Remove: `media/data/relations/similarity/*.yaml`
- Remove: active `media/data/interactions/*.jsonl` if present
- Remove: `media/preferences/inferred/*.yaml`
- Remove: `media/pilots/legacy-reassessment-primary.json`
- Remove: old `.media/operations/*.json` from active state; Git history remains the technical record and new v6 receipts start from the clean cutover state.
- Remove: `media/service/reassessment.py`
- Remove: `media/service/reassessment_mutate.py`
- Remove: `media/service/reassessment_validation.py`
- Remove: `media/tools/reassessment.py`
- Remove: `media/tools/validate_reassessment_transition.py`
- Remove: reassessment command schemas and active reassessment tests.
- Modify: `media/domain/commands.py`
- Modify: `media/commands/schema.py`
- Modify: `media/config/operation_path_policy.json`
- Modify: `.github/workflows/media-command.yml`
- Remove: `.github/workflows/media-check.yml` after its useful assertions are covered by the single-runner data gate.
- Remove: `.github/workflows/media-auto-merge.yml` after legacy reassessment is removed.
- Modify/deploy: switch Broker feedback mapping to the already-tested v6 route and deploy the compatible Broker as part of the cutover sequence.
- Rebuild: `media/generated/index.jsonl`, `media/generated/profiles/*.yaml`

**Interfaces:**
- After this task there is no active reassessment route.
- `record_media_entry` is the normal LLM record route.
- v6 `set_inferred_preferences` with checkpoint analysis is the only normal persistence route for fresh inferred profiles.

- [ ] **Step 1: Preflight open operation state**

Before destructive work, confirm there are no open media operation PRs, no pending request files and no unresolved legacy reassessment session that must be preserved. Close/cancel stale operation branches explicitly rather than importing them into v6.

- [ ] **Step 2: Regenerate final archive from the exact pre-reset tree**

Run:

```bash
python -m media.tools.archive_library --output docs/archive/media-library-before-v6-reset-2026-10-07.md
python -m media.tools.archive_library --output docs/archive/media-library-before-v6-reset-2026-10-07.md --verify
```

Expected: verification succeeds with byte-identical regeneration.

- [ ] **Step 3: Apply guarded reset migration**

Run migration first in dry-run, inspect listed removals/preservations, then apply. Abort on any archive verification error.

- [ ] **Step 4: Remove legacy code/contracts/tests**

Delete pilot commands, schemas, services, workflow branches and tests that no longer represent production behavior. Historical design documents remain untouched.

- [ ] **Step 5: Rebuild clean generated state and validate empty-library invariants**

Assert works=0, collections=0, similarities=0, interactions=0, inferred profiles absent/empty, explicit global preferences preserved, generated outputs reproducible.

- [ ] **Step 6: Commit the atomic data/code cutover**

```bash
git add -A
git commit -m "feat: cut over media intelligence to v6"
```

Do not merge the PR yet; living docs and full verification remain in Task 12.

- [ ] **Step 7: Update PR checkpoint immediately after destructive commit**

Record archive verification result, reset summary, deleted legacy paths, preserved explicit preference/vocabulary paths, commit SHA and the fact that PR is not merge-ready until Task 12 passes.

### Task 12: Обновить всю живую документацию и выполнить финальную проверку

**Files:**
- Modify: `README.md`
- Modify: `.media/README.md`
- Modify: `media/README.md`
- Modify: `docs/README.md`
- Modify: `broker/README.md`
- Modify: `web/README.md`
- Modify: `media/AGENTS.md`
- Modify: `media/START_PROMPT.md`
- Modify: `docs/architecture/media-model.md`
- Modify: `docs/architecture/write-pipeline.md`
- Modify: `docs/architecture/intelligence.md`
- Modify: `docs/architecture/web-and-broker.md`
- Modify: `docs/reference/media-commands.md`
- Modify: `docs/reference/invariants.md`
- Modify: `docs/status/current.md`
- Create: `docs/superpowers/specs/2026-10-07-media-v6-agent-scenario-catalog.md` as current successor if the existing catalog cannot be cleanly updated without rewriting history.
- Create: `docs/runbooks/media-v6-reset.md` or use the repository's established runbook location if one already exists at implementation time.
- Modify: `tests/media/test_docs.py`
- Modify: `tests/media/test_documentation_system.py`
- Modify: `tests/media/test_agent_ux_contract.py`

**Interfaces:**
- Living docs must all describe the same v6 routes and statuses.
- `AGENTS.md` must encode pending ≠ saved, same-work pending follow-up behavior, reanalysis threshold=5, compact context route and removal of legacy reassessment.

- [ ] **Step 1: Write/update documentation contract tests first**

Tests must fail while any living doc still advertises legacy reassessment as active, old normal `record_viewing_feedback(create_if_missing=true)` as preferred route, old multi-workflow save pipeline, or obsolete v5 capability status.

- [ ] **Step 2: Rewrite living docs in simple Russian**

Preserve exact command/file/API names in code formatting. Explain technical terms the first time they are needed. Historical v5/v5.1 specs remain unchanged.

- [ ] **Step 3: Update agent scenario catalog and runbook**

Include scenarios for: existing work feedback, new work atomic add, same-work pending correction, partner feedback, taste threshold 4→5, couple member reanalysis, provider ambiguity, idempotent retry, archive-driven neutral-first old-work recovery, Web feedback.

- [ ] **Step 4: Run Python full gate**

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Expected: all green; `database.sqlite` remains untracked and temp-only.

- [ ] **Step 5: Run Broker full gate**

```bash
cd broker
npm ci
npm test
npm run typecheck --if-present
```

Expected: PASS.

- [ ] **Step 6: Run Web full gate**

```bash
cd web
npm ci
npm run test:run
npm run typecheck
npm run build
```

Run the repository's existing Playwright/a11y checks required by `web-check.yml` before merge.

- [ ] **Step 7: Run post-cutover scenario checks**

At minimum prove:
- empty library renders correctly;
- one new film can be added end-to-end using v6 request/transaction path;
- a second feedback on that now-existing film takes the 0-provider/0-semantic fast path;
- taste context reports cold-start limitations honestly;
- threshold logic triggers exactly at 5 material events;
- Web operation reaches merged/authoritative before Pages publication.

- [ ] **Step 8: Commit documentation/final checks**

```bash
git add README.md .media/README.md media/README.md docs/README.md broker/README.md web/README.md media/AGENTS.md media/START_PROMPT.md docs tests/media
git commit -m "docs: switch living media contracts to v6"
```

- [ ] **Step 9: Final PR checkpoint and review handoff**

Update the PR with:
- exact final head SHA;
- archive verification result;
- reset counts;
- Python/Broker/Web commands and results;
- known limitations, if any;
- statement that product cutover occurs only when this PR merges;
- rollback rule: before new v6 evidence a controlled revert is possible; after new v6 evidence only forward migration is allowed.

Do not merge while any required test/doc contract is red.

---

## Self-Review Notes

- **Spec coverage:** Tasks 1–6 cover domain/digests/invalidation/aggregate command/reanalysis/read context/local parity. Tasks 7–8 cover single-runner CI, exact-base merge, Broker/Web. Task 9 covers deterministic archive. Tasks 10–12 cover regression fixtures, reset, legacy removal, documentation, final cutover and full validation.
- **Atomic cutover:** PRs 1–3 may add dormant/backward-compatible infrastructure, but only PR 4 removes old data/runtime and switches agent/Broker documentation to v6.
- **SQLite:** existing temporary SQLite tooling is retained only for diagnostics/tests; no task introduces a tracked `database.sqlite`.
- **No hidden parallelism:** no global multi-writer queue is added. Stale/base guards remain as defensive correctness checks.
- **Documentation:** all known README/living docs from the design are included in Task 12; each earlier PR updates only docs needed to truthfully describe already-merged dormant/tooling behavior.