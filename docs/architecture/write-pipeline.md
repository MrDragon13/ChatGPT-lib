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

Для legacy operations authoritative `Media Check` запускается для точного resulting head SHA. Это исключает ситуацию, когда зелёный check относится к предыдущему commit.

Для dormant v6 `record_media_entry` и checkpointed `set_inferred_preferences` действует отдельный быстрый путь. Один `Media Command` runner:

1. сериализуется через общую группу `media-data-pipeline` без отмены ожидающих запусков;
2. заново накладывает исходный typed request на свежий `main`;
3. применяет deterministic transaction;
4. запускает canonical validation, `rebuild --check` и точечные operation-specific tests;
5. коммитит и push'ит проверенный результат в operation branch;
6. повторно сверяет base SHA с текущим `main`;
7. сливает exact checked head через GitHub API;
8. запускает Pages для exact merge SHA.

Если `main` изменился вне сериализованного media pipeline, запрос повторно накладывается на новый base и заново проверяется. Число таких повторов ограничено; после лимита операция fail closed. Provider secret передаётся этому пути только для `create_if_missing=true`.

Текущая реализация same-runner merge опирается на фактическую конфигурацию репозитория без required status check, который ожидает завершения самого `Media Command`. Изменение branch protection/rulesets требует повторной проверки этого предположения, а не молчаливого bypass.

### 7. Guarded merge

Auto-merge разрешён только allowlisted normal data operations и только для operation-specific path set. `record_media_entry` и checkpointed `set_inferred_preferences` выполняют этот guarded merge внутри `Media Command`; legacy normal operations временно получают тот же trust boundary через успешный `Media Check -> Media Auto Merge`. **Guarded merge** не распространяется на architecture/schema/vocabulary/workflow changes.

Canonical policy — declarative `media/config/operation_path_policy.json`. Runtime transaction проверяет локальную копию policy, а privileged auto-merge **не доверяет PR checkout**: он получает policy из trusted `main` через GitHub Contents API и список changed filenames через GitHub PR files API. PR-head operation marker читается только как JSON data. Privileged workflow не должен импортировать или исполнять PR-head Python.

Path patterns используют один и тот же узкий grammar в Python и privileged workflow: repository-relative POSIX path; exact match либо ровно один `*`; wildcard не пересекает `/`; matching anchored ко всему path. `**`, второй `*`, `?`, character classes, brace expansion и ненормализованные paths invalid и приводят к fail closed.

Для legacy operations trust-модель privileged `Media Auto Merge` опирается на trigger `workflow_run`: исполняемое определение workflow существует на default branch, а PR-head Python с write-capable token там не запускается. Поля event ref/SHA из события считаются только входными метаданными: workflow заново сверяет exact checked head с текущим PR и trusted `main`, прежде чем разрешить merge.

Dormant v6 `record_media_entry` и checkpointed `set_inferred_preferences` используют другой, более узкий контракт same-runner merge: только same-repo `media/op-*` PR, до исполнения разрешён ровно один request-файл, затем рабочее дерево строится заново от свежего `main` и в него возвращается только сохранённый JSON request. Этот путь рассчитан на текущий персональный репозиторий, где `main` не защищён branch protection/ruleset и same-repo writers уже являются доверенными. Это **не** общий механизм для недоверенных contributor/fork PR. Изменение collaborator-модели, branch protection или event model требует отдельного security review.

Любая ошибка fetch/decode/JSON parsing, неизвестная operation, `auto_merge: false`, unsupported matcher grammar, пустой/invalid allowlist или path вне trusted policy приводит к fail closed.

### 8. Pages publish

После merge публикация GitHub **Pages** строится на exact merge SHA. Web manifest экспортируется заново из canonical/derived media layer.

## Auto-merge eligible normal operations

Точный список определяется `media/config/operation_path_policy.json`, а не prose-файлом и не дублированным shell `case`. Типовые normal routes включают viewing feedback, interest, inferred preferences, semantic fingerprint, recommendation interaction и explicit similarity writes.

Изменение самого policy, privileged workflows, guard tests или executable media service/tooling code не может быть разрешено тем же untrusted PR: такие PR идут только через обычный developer review/merge. Если operation меняет больше разрешённых paths, guarded merge должен остановиться, а не расширять права молча.

## Work creation + feedback

Когда пользователь сообщает о новом просмотренном work и feedback одновременно, existing route `record_viewing_feedback(create_if_missing=true)` выполняет provider-backed creation, feedback mutation и deterministic relation reconciliation атомарно. Не нужно создавать work отдельным предварительным шагом.

## Similarity write

`set_work_similarity`/`remove_work_similarity` ограничены relation storage и operation metadata. Если новый canonical work создаётся и совпадает с persisted external similarity endpoint, reconciliation relation paths допустимы только внутри соответствующего work-creation transaction.

## Legacy reassessment serialized operations

Legacy reassessment использует отдельную correctness-first цепочку поверх того же typed transaction boundary. Она не превращает старый текст в новый explicit evidence автоматически и не расширяет semantic/vocabulary права.

- `reserve_reassessment_session` резервирует exact next frozen-order batch и переводит его в `in_progress`.
- `complete_reassessment_item` атомарно объединяет optional `primary` feedback edit и lifecycle transition `in_progress -> reviewed|deferred`; существующие feedback mutation primitives сохраняют history/rebuild semantics.
- `close_reassessment_session` закрывает только полностью resolved session, сохраняет audit/progress snapshot и при необходимости продвигает persisted scheduled-reanalysis state.

Каждая ledger mutation несёт `expected_ledger_digest` от authoritative current `main`; следующая pilot write request создаётся только после того, как предыдущая стала видимой на `main`. Completion дополнительно проверяет raw pre-review work-file digest, поэтому concurrent canonical edit к reserved work заставляет replay вместо silent overwrite.

`media/pilots/legacy-reassessment-primary.json` — operational provenance, не taste truth. Frozen cohort/base/baseline refs immutable; reviewed items и closed session snapshots monotonic/immutable. Runtime planner guards дублируются independent base→head transition validator'ом, который `Media Check` запускает против trusted replay base.

Path scope остаётся узким: reserve/close могут менять только exact pilot ledger + receipt; complete может дополнительно изменить не более одного canonical work, только reserved `work_id`, и требуемые existing generated profile/index paths. Generic wildcard policy дополняется operation-specific cardinality/id guard.

Privileged auto-merge не выполняет PR-head Python для этих проверок. Перед merge он заново читает current-main ledger bytes и сравнивает SHA-256 с trusted receipt `details.expected_ledger_digest`; для `complete_reassessment_item` также заново читает reserved work bytes и сверяет `pre_review_work_file_digest`. Stale operation fail-closed даже если Git merge технически возможен.

Pilot foundation может быть auto-merge authority только после manual merge PR A. Первичное создание frozen ledger — отдельный manual activation PR, потому что у первого ledger snapshot нет trusted base ledger для transition comparison.

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

`recommend_context`, `taste_context` и `assess_candidate` не создают operation PR и не мутируют canonical data. Legacy reassessment добавляет `reassessment-context` как unanchored safe-card route и отдельный `reassessment-history` explicit historical lookup; эти read models сами canonical state не меняют.

## Security properties

GitHub Actions media pipeline не должен требовать live LLM credentials. Provider tokens выдаются только provider-dependent server/CI операциям. Browser никогда не получает repository write credentials или provider/model secrets.

Legacy privileged guarded merge использует только доверенные policy/state inputs из `main` и GitHub PR metadata; PR-head Python там не исполняется с write-capable credentials. V6 same-runner path вместо этого опирается на same-repo/request-only contract, повторную сборку рабочего дерева от свежего `main`, operation path policy и exact base/head guards, описанные выше.

## Проверка developer change

Базовый полный gate:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Web-impacting change дополнительно проходит web tests/typecheck/build/browser/security checks согласно workflow contract.
