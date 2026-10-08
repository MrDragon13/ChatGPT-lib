# Media write pipeline

Этот документ описывает текущий v6 lifecycle записи media data. Обычная пользовательская запись не патчит canonical YAML напрямую: сначала создаётся typed request, затем доверенный GitHub Actions runner применяет его к свежему `main`.

## Главный принцип

Для normal data write действует:

> один человеческий эпизод → один typed request → один operation PR → одна transaction → одна минимальная пересборка → один authoritative gate → один merge.

GitHub остаётся границей долговременного сохранения, но не должен быть границей задержки разговора.

## Request-only PR

Обычная запись создаёт request-only same-repo ветку `media/op-*` от текущего `main`.

До исполнения PR содержит **ровно один** файл:

```text
.media/requests/<operation-id>.json
```

Canonical YAML и `media/generated/**` не готовятся заранее клиентом. Их создаёт доверенный runner после повторного применения typed intent к свежему `main`.

Это позволяет replay операции вместо слияния устаревшего готового YAML diff.

## Очередь операций

Normal media writes сериализуются средствами GitHub Actions:

```yaml
concurrency:
  group: media-data-pipeline
  cancel-in-progress: false
  queue: max
```

Собственная БД блокировок или отдельный queue service не используются.

Очередь предотвращает обычное наложение media writes, но не заменяет exact-base guard: `main` всё ещё может измениться developer/manual PR.

## `Media Command`

Для операции с `execution_class=v6_single_runner` один runner выполняет весь normal path:

1. сохраняет request как недоверенные данные;
2. получает свежий `origin/main`;
3. проверяет, что исходный PR не содержал ничего кроме request;
4. заново строит operation branch от свежего `main` и возвращает только request;
5. валидирует command schema и preconditions;
6. применяет deterministic transaction;
7. определяет `changed_domains` и из них `DirtyPlan`;
8. пересобирает каждый нужный derived output максимум один раз;
9. проверяет operation path policy;
10. выполняет canonical validation, `rebuild --check` и operation-specific tests;
11. коммитит проверенный результат в operation branch;
12. повторно читает текущий `main`;
13. если base изменился, replay выполняется заново с ограниченным числом попыток;
14. если base тот же, GitHub API сливает exact checked head;
15. `Media Pages` запускается для exact merge SHA.

Прямой `git push HEAD:main` не используется. Repository auto-merge setting не является частью контракта.

## Проверка операции

Normal data write не запускает полный developer regression suite.

Его authoritative gate содержит только то, что доказывает корректность конкретной data operation:

- JSON schema / command validation;
- operation-specific preconditions;
- canonical validation;
- operation-specific path policy;
- dependency-driven rebuild;
- `rebuild --check`;
- целевые тесты данного типа операции;
- receipt/idempotency checks.

Полный `pytest`, doctor, Web/Broker gates и архитектурные проверки остаются обязательными для developer changes.

## Классы исполнения

Источник истины — `media/config/operation_path_policy.json`.

- Операции с `auto_merge=true` используют `execution_class=v6_single_runner`.
- Bulk `refresh_metadata` использует `execution_class=manual_review`: workflow может применить и полностью проверить изменение в PR-ветке, но не сливает его автоматически.
- Architecture/schema/vocabulary/workflow changes не являются typed data operations и идут обычным developer PR.

Старые раздельные validation/merge workflows удалены; current normal path полностью обслуживает единый `Media Command` runner.

## Provider secret

Provider secret передаётся только тогда, когда операция действительно требует внешнюю проверку.

Existing-work feedback не требует provider I/O.

Новый `record_media_entry(create_if_missing=true)` получает provider context для stable identity и свежих factual metadata; provider-owned metadata не передаются клиентом как blocking preconditions.

## `record_media_entry`

Это основной v6 маршрут для события «пользователь сообщает что-то об одном произведении».

### Existing work

Payload обычно содержит только:

- `work_ref`;
- `target_updates`;
- `preconditions.expected_viewer_digests`.

Existing-work path не обновляет metadata и не пересчитывает semantics.

### New work

Payload дополнительно содержит:

- `creation_context.provider_identity`;
- `semantic_snapshot.traits`;
- те же viewer updates.

Актуальные provider metadata, semantic input digest, vocabulary digest и algorithm version вычисляются доверенным runtime.

Создание work, semantic fingerprint и feedback выполняются одной transaction.

Если `create_if_missing=true`, но work уже существует по stable identity, existing canonical metadata/semantics не перезаписываются creation payload. Viewer digest проверяется против реально существующего target state.

## Idempotency

`operation_id` идентифицирует конкретную техническую попытку.

`idempotency_key` идентифицирует одно пользовательское событие.

Повтор с тем же `idempotency_key` и тем же нормализованным request возвращает уже применённый результат. Тот же key с другим intent fail closed.

`no_change` — полноценный успешный результат: он не создаёт искусственную history event и не запускает ненужную пересборку.

## Pending write и повторное уточнение

После отправки операции LLM может продолжать разговор и учитывать явный пользовательский сигнал локально.

Если пользователь изменяет тот же work, пока первая операция pending, второй Git request по тому же work не отправляется. Уточнение остаётся в session-local overlay до authoritative первой операции; затем читается свежий `media_entry_context` и отправляется следующая операция с новым viewer digest.

Web соблюдает тот же принцип: блокирует второй submit, но сохраняет локальный draft.

## Path policy и security boundary

`media/config/operation_path_policy.json` задаёт разрешённые пути конкретной операции.

Обычный request может менять только operation-specific canonical/generated/receipt paths. Он не получает право менять schemas, vocabulary, workflows, agent contracts или architecture.

`Media Command` допускается только для same-repository `media/op-*` PR. Fork/untrusted contributor path не получает secret-bearing выполнение.

Текущая same-runner модель рассчитана на фактическую конфигурацию персонального репозитория. Изменение collaborator model, branch protection/rulesets или trust boundary требует отдельного security review.

## Read-only routes

`media_entry_context`, `recommend_context`, `taste_context` и `assess_candidate` не создают operation PR и не мутируют canonical state.

## Pages

После merge `Media Pages` получает exact merge SHA. Web manifest строится заново из canonical/derived media state.

Публикация более раннего зелёного SHA не считается публикацией текущего состояния.

## Developer changes

Изменения Python, schemas, workflow, vocabulary, architecture/config или frontend/backend logic проходят обычный reviewed PR и полный релевантный gate.

Для таких изменений normal media auto-merge boundary не используется.
