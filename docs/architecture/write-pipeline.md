# Media write pipeline

Этот документ описывает текущий deterministic lifecycle media mutations и границу между normal typed operations, maintenance и manual developer changes.

## Почему запись не идёт напрямую в YAML

LLM, CLI и web не должны формировать произвольный patch canonical media files. Обычная mutation сначала превращается в strict **typed request**, который валидируется schema contract и применяется deterministic Python-кодом.

Это даёт:

- schema safety;
- target/identity validation;
- idempotence по `operation_id`;
- контролируемые side effects;
- operation-scoped path policy;
- воспроизводимый rebuild;
- auditable Git history.

## Normal typed operation lifecycle

```text
natural-language intent / CLI / broker
        -> typed request
        -> media/op-* branch
        -> operation PR
        -> transient .media/requests/<operation-id>.json
        -> deterministic transaction
        -> validation + operation-scoped rebuild
        -> authoritative exact-head check
        -> guarded merge
        -> exact-merge GitHub Pages publish
```

### 1. Intent resolution

Agent или caller определяет конкретную operation: например `record_viewing_feedback`, `set_interest` или `set_work_similarity`. Нельзя подменять неизвестную/неподдерживаемую mutation free-form YAML edit.

### 2. Typed request

Payload соответствует JSON schema под `media/commands/schemas/`. Mutable operations получают canonical UUID `operation_id`; read-only routes не маскируются под write.

### 3. Operation PR

Normal write создаётся на свежей same-repo `media/op-*` ветке от current `main` и несёт один transient request. PR является review/audit boundary и входом в GitHub Actions pipeline.

### 4. Deterministic transaction

`Media Command` применяет request через domain/service/repository layer. Transaction разрешает только side effects, предусмотренные operation contract: например work creation, feedback update или similarity relation normalization/reconciliation.

### 5. Validation и rebuild

После mutation выполняются canonical validation и требуемая пересборка derived artifacts. Generated state не редактируется как независимый source of truth.

### 6. Exact-head gate

Authoritative `Media Check` запускается для точного resulting head SHA. Это исключает ситуацию, когда зелёный check относится к предыдущему commit.

### 7. Guarded merge

Auto-merge разрешён только allowlisted normal data operations и только для operation-specific path set. **guarded merge** не распространяется на architecture/schema/vocabulary/workflow changes.

### 8. Pages publish

После merge публикация GitHub **Pages** строится на exact merge SHA. Web manifest экспортируется заново из canonical/derived media layer.

## Auto-merge eligible normal operations

Точный список определяется workflow/policy code, а не этим prose-файлом. Типовые normal routes включают viewing feedback, interest, inferred preferences, semantic fingerprint, recommendation interaction и explicit similarity writes.

Если operation меняет больше разрешённых paths, guarded merge должен остановиться, а не расширять права молча.

## Work creation + feedback

Когда пользователь сообщает о новом просмотренном work и feedback одновременно, existing route `record_viewing_feedback(create_if_missing=true)` выполняет provider-backed creation, feedback mutation и deterministic relation reconciliation атомарно. Не нужно создавать work отдельным предварительным шагом.

## Similarity write

`set_work_similarity`/`remove_work_similarity` ограничены relation storage и operation metadata. Если новый canonical work создаётся и совпадает с persisted external similarity endpoint, reconciliation relation paths допустимы только внутри соответствующего work-creation transaction.

## Maintenance route

`refresh_metadata` использует тот же deterministic transaction foundation, но относится к maintenance, а не к normal auto-merge data entry.

Для bulk scope `all_movies` выполняется identity preflight до mutation. Ambiguity/provider failure не должен оставлять partial repository state. `refresh_metadata` требует manual review и **не** входит в normal guarded auto-merge allowlist.

## Manual developer route

Следующие изменения идут через **manual developer** workflow, а не через normal typed-operation auto-merge:

- schemas;
- controlled vocabulary;
- domain/service/repository code;
- architecture semantics;
- GitHub workflows/path policy;
- tests;
- documentation architecture;
- broker/security policy;
- maintenance behavior itself.

Такие PR проходят development checks и обычный review/merge. Их нельзя выдавать за routine user data operation ради более широкого auto-merge доступа.

## Read-only routes

`recommend_context`, `taste_context` и `assess_candidate` не создают operation PR и не мутируют canonical data. Если read path начинает писать состояние, это архитектурное изменение, а не implementation detail.

## Security properties

GitHub Actions media pipeline не должен требовать live LLM credentials. Provider tokens выдаются только provider-dependent server/CI операциям. Browser никогда не получает repository write credentials или provider/model secrets.

## Проверка developer change

Базовый полный gate:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Web-impacting change дополнительно проходит web tests/typecheck/build/browser/security checks согласно workflow contract.
