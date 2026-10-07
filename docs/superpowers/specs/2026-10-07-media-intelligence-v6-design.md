# Media Intelligence v6 — design

Дата: 2026-10-07  
Статус: **approved design, implementation not started**  
Основание: current `main` @ `d51e95a73d04342cc31a96b9ad629a3b0c66957a`

## 1. Цель

Media Intelligence v6 оптимизируется под реальный основной сценарий использования:

> **один фильм → один человеческий отзыв → один LLM-разбор → одна typed operation → один минимальный rebuild → одна authoritative validation → один merge**

Главная цель — **максимальное быстродействие без потери достигнутого качества анализа и рекомендаций, на текущей инфраструктуре, за счёт алгоритмической, логической, кодовой, стратегической и структурной оптимизации**.

Скорость не достигается уменьшением объёма анализа или ослаблением гарантий. v6 должна устранять повторные I/O, повторные LLM-проходы, ненужную invalidation, лишние rebuild, лишние Git-транзакции и лишние CI cold starts.

LLM остаётся основным пользовательским интерфейсом. Сайт остаётся полноценным вторичным клиентом и визуальной оболочкой той же системы. GitHub `main` + canonical Git/YAML остаются source of truth.

## 2. Неподвижные качественные гарантии

v6 сохраняет сильные стороны v5.1:

- explicit user evidence выше inferred evidence;
- work semantics не выводятся из пользовательского sentiment;
- rating/reaction не считаются доказательством объективных traits;
- controlled vocabulary обязателен для semantic fingerprints;
- provenance сохраняется;
- inferred output не является независимым evidence для последующего inference;
- explicit similarity — evidence/hint, а не preference;
- couple disagreement не скрывается усреднением;
- candidate assessment остаётся qualitative и не использует fake precise probability;
- partial coverage/limitations продолжают ограничивать confidence;
- fresh explicit evidence имеет приоритет над stale inferred interpretation.

Любая оптимизация, нарушающая эти инварианты, не соответствует v6.

## 3. Reset старой медиатеки

Перед cutover выполняется полный reset активной медиатеки.

### 3.1 Человекочитаемый архив

До destructive reset создаётся один MD-архив всей текущей медиатеки: `docs/archive/media-library-before-v6-reset-2026-10-07.md`.

Архив содержит все существующие произведения. Для каждого произведения сохраняются только человечески полезные данные:

- название и год;
- viewing status;
- rating;
- reaction;
- текстовый feedback;
- явно высказанные причины/заметки;
- `partner` / `couple` данные, если они реально существуют.

Отдельно архивируются:

- explicit work similarities;
- названия существующих collections.

Архив не содержит:

- internal work IDs;
- provider IDs;
- operation IDs;
- digests;
- semantic fingerprints;
- inferred hypotheses;
- технический provenance;
- pilot lifecycle;
- CI/runtime metadata.

Архив является памяткой и чек-листом. Он **не является machine-readable restore source**, не входит в recommendation input и не участвует в taste analysis.

Completeness-check обязан доказать, что в архиве присутствуют все canonical works до reset и все работы с human signals.

### 3.2 Что очищается

После проверки архива active state очищается:

- canonical works;
- collections;
- work similarities;
- interactions;
- legacy reassessment pilot;
- inferred preferences `primary`, `partner`, `couple`;
- runtime artifacts, относящиеся только к legacy pilot.

### 3.3 Что сохраняется

Сохраняются:

- global explicit preferences/rules;
- vocabulary;
- schemas и код;
- recommendation/candidate-assessment logic;
- Broker;
- Web/Pages;
- historical Git history.

Stage A baselines перестают быть live/runtime input. Если отдельные старые сценарии нужны для regression coverage, они переносятся в специальные synthetic/reference fixtures.

## 4. Legacy reassessment больше не runtime

После cutover legacy reassessment не является active capability.

Из runtime и agent routing удаляются:

- `reserve_reassessment_session`;
- `complete_reassessment_item`;
- `close_reassessment_session`;
- `record_reassessment_modernization`;
- pilot-specific modernization orchestration;
- pilot-specific transaction/path-policy/workflow branches.

История остаётся в Git и historical specs.

Повторное прохождение старых фильмов идёт через MD-архив как нейтральный checklist: LLM показывает работу без старого rating/review anchoring, пользователь даёт свежий отзыв, после чего используется обычный v6 write-path.

## 5. Главная aggregate operation

v6 вводит новый рекомендованный normal write route, `record_media_entry`.

Операция соответствует одному естественному человеческому событию о конкретном произведении.

Концептуальный payload:

```text
schema_version
operation_id
idempotency_key

work_ref
create_if_missing

viewer_updates[]

creation_context?
  resolved_identity
  provider_identity
  minimum_metadata

semantic_snapshot?
  traits
  semantic_input_digest
  vocabulary_digest
  algorithm_version

preconditions
  expected_viewer_digest[target]?
```

Операция не является универсальным arbitrary bundle engine. В неё не входят глобальный taste reanalysis, unrelated similarity mutations, vocabulary changes или bulk maintenance.

### 5.1 Existing work fast path

Для существующего фильма обычный отзыв содержит только:

- work reference;
- viewer update;
- expected viewer digest.

Он не требует:

- provider call;
- metadata refresh;
- semantic recomputation;
- legacy modernization;
- global taste reanalysis.

### 5.2 New work path

Для нового фильма одна операция атомарно включает:

- resolved identity;
- provider identity;
- factual minimum;
- semantic snapshot, подготовленный LLM;
- viewer evidence.

Не допускается последовательность `add → reread → semantics → feedback` как normal path.

Если work появился конкурентно до применения операции, stable identity используется для reconciliation вместо создания дубля.

## 6. Canonical logical layers

Физически work может оставаться единым YAML, но логически состоит из независимых слоёв:

```text
Work
├── identity
├── metadata
├── semantics
└── viewer state
    ├── primary
    ├── partner
    └── direct couple/group evidence
```

Изменение одного слоя не инвалидирует остальные автоматически.

## 7. Granular concurrency

Normal feedback больше не должен зависеть от digest всего work-файла.

Основной optimistic precondition:

```text
work identity
+ target
+ expected_viewer_digest(target)
```

Следствия:

- metadata change не конфликтует с primary feedback;
- semantic refresh не конфликтует с viewer feedback;
- partner feedback не конфликтует с primary feedback;
- реальный конфликт возникает только при конкурентном изменении того же viewer evidence.

Typed intent при применении replay'ится относительно свежего `main`; не применяется старый готовый YAML patch.

## 8. Idempotency

`operation_id` остаётся audit identity конкретной попытки.

`idempotency_key` идентифицирует одно человеческое событие.

Retry одного события не должен:

- создавать duplicate history;
- увеличивать evidence count;
- создавать duplicate work;
- повторять rebuild;
- создавать второй логический отзыв.

`no_change` является полноценным успешным результатом и не создаёт искусственную history mutation.

## 9. Invalidation и dependency graph

Domain mutation сначала сообщает, **что изменилось**, а infrastructure определяет, **что нужно пересчитать**.

Вводится явный `changed_domains`, например:

```text
work_identity
metadata
semantics
viewer.primary
viewer.partner
explicit_preferences.primary
similarity.primary
```

Затем deterministic dependency planner строит `DirtyPlan`.

Принцип:

> Domain planners declare changes; infrastructure derives rebuilds.

Каждый affected derived output rebuild'ится максимум один раз за operation.

## 10. Digests и доказуемый reuse

Digest-логика становится отдельным доменным контрактом.

Минимально нужны:

- `compute_viewer_digest(work, target)`;
- `compute_metadata_digest(work)`;
- `compute_semantic_input_digest(...)`;
- `compute_profile_input_digest(repo, target)`;
- `compute_evidence_digest(repo, target)`.

Набор входов каждого digest должен быть документирован и покрыт тестами, включая проверки того, что **не входит** в digest.

Общий принцип:

> **calculate once, prove reuse**

Если входной digest и версия алгоритма совпадают, повторное вычисление запрещено как ненужное.

## 11. Metadata freshness

Metadata делится минимум на классы:

- identity facts;
- static facts;
- dynamic metrics.

Identity/static/dynamic данные имеют отдельные freshness policies.

Изменение provider popularity/vote metrics не инвалидирует semantic fingerprint.

Для existing-work feedback provider I/O равен нулю.

Для нового work блокируют создание только identity-critical facts и factual minimum, необходимый для качественной семантики. Optional metadata не блокирует человеческий отзыв.

## 12. Semantic fingerprint

Semantic key определяется как:

```text
hash(
  semantic_input_projection
  + vocabulary_digest
  + semantic_algorithm_version
)
```

User rating/reaction/feedback, history, pilot state и provider popularity metrics в semantic input не входят.

Если key совпадает, semantics переиспользуются без нового LLM-прохода.

### 12.1 LLM-side generation

Основная LLM, с которой разговаривает пользователь, подготавливает semantics нового/действительно dirty work один раз.

### 12.2 Repository-side acceptance

GitHub/Python не повторяют reasoning. Они детерминированно проверяют:

- schema;
- vocabulary terms;
- semantic key;
- algorithm/vocabulary versions;
- provenance;
- запрет reaction-kind terms в work fingerprint;
- identity consistency.

## 13. Stale не означает blocker

Stale metadata или semantics не блокируют human feedback существующего work.

Human evidence сохраняется независимо.

Maintenance обновляет только реально stale слой и только когда он нужен по policy.

## 14. Derived rebuild

`MutationPlan` v6 содержит canonical changes и `changed_domains`.

Отдельный dependency layer строит `DirtyPlan`.

Transaction:

1. validates command;
2. loads current canonical state;
3. validates granular preconditions;
4. applies all canonical mutations in memory;
5. computes changed domains;
6. derives dirty outputs;
7. rebuilds each dirty output once;
8. validates resulting repository;
9. writes receipt;
10. commits.

Никаких rebuild между внутренними canonical mutations.

На первом v6 этапе profile остаётся full deterministic build для конкретного affected target. Сложный delta-profile не вводится без измеримого bottleneck.

`media/generated/` остаётся versioned в Git, но rebuild становится строго dependency-driven.

## 15. LLM-first UX

GitHub остаётся durability boundary, но перестаёт быть latency boundary разговора.

Логические статусы:

```text
accepted_local
pending_persistence
authoritative
failed/conflicted
```

LLM может продолжать разговор после принятия и submission операции, не ожидая merge.

Слово «сохранено» допустимо только после authoritative состояния в `main`.

## 16. Session-local read-your-writes

Пока операция pending, текущая LLM-сессия может учитывать только явные пользовательские сигналы:

- viewing;
- rating;
- reaction;
- feedback;
- explicit signals.

Pending overlay:

- не является второй БД;
- живёт только в текущем разговоре;
- после merge заменяется canonical state;
- после failure/conflict перестаёт считаться durable;
- не содержит автоматически inferred global profile changes.

## 17. Compact read context

Добавляется компактный read-only route `media_entry_context`.

Он возвращает минимум для решения normal feedback:

- identity;
- current viewer state;
- viewer digest;
- metadata status;
- semantic status/key;
- relevant factual fields;
- current semantic fingerprint;
- interest state.

LLM не должна ради простого feedback последовательно читать index, work, profile, vocabulary, status docs и legacy context.

Vocabulary читается только когда создаются/меняются semantics.

## 18. Taste reanalysis lifecycle

Deep taste reanalysis не входит в critical path каждого отзыва.

Fresh explicit evidence используется сразу.

Inferred preferences остаются versioned/materialized interpretation, а не первичной истиной.

### 18.1 Evidence threshold

Конфигурируемый threshold, default = **5**.

Одна единица evidence:

- максимум +1 за одно materially changed human event по одному work;
- количество изменённых полей не увеличивает значение;
- retry/no-change/metadata-only mutation не считаются;
- существенная последующая переоценка того же work может дать ещё +1.

Canonical source of truth — checkpoint/evidence digest, а не независимый mutable integer.

### 18.2 Target semantics

Checkpoints независимы для:

- `primary`;
- `partner`.

`couple` не имеет отдельного автоматического counter. Перед couple taste-dependent decision проверяется актуальность обоих индивидуальных profiles.

### 18.3 Reanalysis gate

Gate обязателен перед taste-dependent запросами:

- recommendation;
- internal recommendation;
- candidate comparison;
- candidate assessment;
- couple recommendation;
- «подойдёт ли мне X?» и аналогичные запросы.

Lookup/factual queries reanalysis не запускают.

Если outstanding material evidence достигло threshold, LLM обязана сначала сделать fresh reanalysis, а затем строить taste-dependent ответ.

Новый inferred result может использоваться как session-local overlay до merge. Canonical checkpoint продвигается только после authoritative persistence.

Если после snapshot появился новый feedback, он остаётся outstanding; нельзя слепо сбрасывать counter в ноль.

## 19. Single-runner data pipeline

Обычный data write в v6 проходит один основной Actions runner:

```text
typed request PR
→ checkout/replay latest main
→ validate request/preconditions
→ apply transaction
→ derive/rebuild dirty outputs once
→ authoritative data validation
→ commit verified result
→ push
→ guarded auto-merge
```

Цель — один provisioning, один checkout, один Python setup и один dependency install.

Отдельный exact-head/full developer gate остаётся для изменений executable logic, где это оправдано.

## 20. Data CI vs Dev CI

### Data Operation CI

Для normal data writes:

- schema validation;
- domain/operation invariants;
- canonical validation;
- path policy;
- dirty-derived consistency;
- operation-specific targeted tests;
- receipt/idempotency checks.

### Dev CI

Для Python, schemas, workflows, vocabulary contracts, architecture/config, frontend logic и tests:

- full pytest;
- canonical validation;
- full rebuild checks;
- doctor;
- web checks;
- architecture/docs contract checks.

Bot-generated data result не должен запускать overlapping Dev CI.

## 21. GitHub PR и merge

PR-модель сохраняется ради audit, branch safety, path policy, observability и Broker compatibility.

Норма:

```text
1 human event
= 1 request PR
= 1 application cycle
= 1 merge
```

Количество технических commits внутри branch не является performance KPI.

Auto-merge остаётся fail-closed и разрешается только при:

- permitted operation class;
- valid path policy;
- successful authoritative data gate;
- verified operation/result identity;
- отсутствии unresolved conflict.

## 22. Provider behavior

Existing-work feedback не требует provider secret или provider call.

New-work operation использует provider только для identity-critical facts и factual minimum.

Optional metadata failure не должна превращать human feedback в multi-operation lifecycle.

## 23. Web/Broker

LLM и Web — два клиента одного Media Domain.

Ответственности:

```text
Media Domain:
- validation
- concurrency
- history semantics
- idempotency
- canonical mutation
- invalidation/rebuild

LLM:
- natural-language understanding
- semantic reasoning
- conversational UX
- session-local overlay

Broker:
- browser trust boundary
- authentication/authorization
- typed submission
- operation status

Web:
- visualization
- browser interaction
- optional pending UX
```

Broker остаётся stateless. v6 не добавляет D1/KV/Durable Objects или новую backend database.

Web feedback использует те же viewer digests, idempotency и domain semantics.

Web read model остаётся authoritative-only; собственный pending status может отображаться как UX, но не становится canonical state.

## 24. Code boundaries

`transaction.py` должен стать тонким coordinator.

Логические модули v6:

- command/schema registry;
- media-entry orchestration;
- feedback;
- identity;
- metadata;
- semantics;
- preferences;
- similarity;
- digests;
- invalidation/dependencies;
- derived rebuild;
- transaction.

Новая aggregate operation имеет отдельный planner, который вызывает независимые domain-функции, но ни одна domain-функция сама не запускает rebuild.

Главный интерфейс:

```text
command
→ domain planner
→ MutationPlan(changed_domains)
→ dependency planner
→ DirtyPlan
→ transaction/rebuild
```

Основной path должен быть понятен без чтения половины `media/`.

## 25. Backward compatibility

Cutover не обязан бесконечно поддерживать legacy reassessment API.

Полезный `record_viewing_feedback` может временно остаться narrow compatibility command поверх новых domain primitives, если это дёшево и не влияет на архитектуру.

Новый рекомендованный LLM route — aggregate v6 operation.

Все незавершённые legacy operation PR/session state должны быть завершены или закрыты до cutover.

## 26. Error model

Normal write имеет только значимые состояния:

- accepted;
- pending;
- authoritative;
- failed/conflicted.

Aggregate human event применяется атомарно либо не применяется вообще.

### Conflict

Viewer-level digest conflict приводит к перечитыванию compact context и переоценке исходного intent, а не к blind overwrite.

### Provider failure

Existing work unaffected. New work блокируется только если identity нельзя надёжно установить.

### Semantic validation failure

Operation отклоняется до canonical mutation; LLM исправляет payload и retry сохраняет idempotency человеческого события.

### Pending overlay

Failure/conflict не превращается в durable history.

## 27. Receipts

Receipt остаётся компактным audit artifact:

- operation_id;
- idempotency_key;
- operation;
- status;
- changed_entities;
- changed_domains;
- changed_files;
- applied_at;
- минимальные operation-specific details.

Receipt не дублирует canonical snapshot.

## 28. Performance correctness contract

Скорость становится частью correctness.

### Existing canonical work + feedback

Должно выполняться:

```text
provider calls              = 0
semantic recomputations     = 0 при unchanged semantic key
metadata refreshes          = 0
typed operations            = 1
operation PRs               = 1
data CI runner cold starts  = 1
canonical transactions      = 1
each affected rebuild       <= 1
merge                       = 1
```

### New work

```text
identity/provider phase     = 1
semantic LLM pass           = 1
typed operations            = 1
canonical transactions      = 1
each affected rebuild       <= 1
data CI cycle               = 1
merge                       = 1
```

Wall-clock time является diagnostic metric, а не хрупким CI assertion. Structural causes of latency должны тестироваться напрямую.

## 29. Test matrix

Минимальные permanent scenarios:

1. existing work — rating only;
2. existing work — rich feedback;
3. existing work — viewing correction;
4. existing work — semantic unchanged;
5. existing work — semantic correction;
6. new work — viewing only;
7. new work — rating + rich feedback;
8. partner feedback;
9. concurrent primary vs partner;
10. true same-target conflict;
11. idempotent retry;
12. no_change;
13. taste threshold < 5;
14. taste threshold == 5;
15. couple recommendation with one due member;
16. equivalent LLM/Broker viewer mutation.

Каждый scenario проверяет canonical result, dirty domains, rebuild set, allowed external I/O и CI class.

## 30. Recommendation quality fixtures

После reset active user library не используется как regression fixture.

Создаются synthetic/reference fixtures для:

- strong positive intrigue/problem-solving evidence;
- mixed evidence;
- couple disagreement;
- sparse semantic coverage;
- explicit similarity without preference;
- stale inferred + fresh contradicting explicit evidence.

Regression tests защищают качественные invariants, а не старый персональный dataset.

## 31. Documentation contract

Documentation является частью executable/operational contract.

До cutover должны быть синхронизированы:

- `media/AGENTS.md`;
- `media/START_PROMPT.md`;
- `docs/architecture/media-model.md`;
- `docs/architecture/write-pipeline.md`;
- `docs/architecture/intelligence.md`;
- `docs/architecture/web-and-broker.md`;
- `docs/reference/media-commands.md`;
- `docs/reference/invariants.md`;
- `docs/status/current.md`;
- current scenario catalog / его преемник;
- Broker README;
- релевантные Web docs;
- migration/reset runbook.

Правило:

> Code, schemas, tests, living docs, agent routing и Web/Broker contract должны описывать одну и ту же v6 semantics.

Historical v5/v5.1 specs не переписываются задним числом. Этот design явно supersede'ит active legacy reassessment lifecycle после cutover; living docs меняются только вместе с работающим v6 runtime.

## 32. Atomic cutover

v6 не вводится как длительный гибрид.

До cutover должны быть готовы:

- v6 command/domain implementation;
- new digests/invalidation;
- single-runner data pipeline;
- Broker/Web compatibility;
- taste checkpoint/reanalysis semantics;
- performance and quality tests;
- archive generator/completeness check;
- updated living docs.

Один cutover включает:

- human-readable archive;
- reset active data;
- removal of legacy runtime;
- clean generated state;
- v6 code/workflows/docs;
- compatible Broker/Web.

## 33. Rollback

Git history остаётся техническим backup.

До появления новых v6 evidence cutover можно откатить контролируемым revert.

После появления новых v6 отзывов blind revert запрещён, потому что уничтожит новое evidence. В этом случае восстановление делается только forward migration.

## 34. Post-cutover sanity

Сразу после reset должно быть доказано:

- canonical works = 0;
- collections = 0;
- similarities = 0;
- interactions = 0;
- legacy pilot absent;
- inferred profiles empty/current-empty;
- explicit global preferences preserved;
- generated state reproducible;
- Web корректно отображает пустую library;
- новый фильм можно добавить end-to-end;
- после первого добавления existing-work fast path работает;
- recommendation cold-start limitations отображаются корректно.

## 35. Non-goals v6

В v6 сознательно не входят:

- внешняя database;
- новый backend/service;
- Cloudflare KV/D1/Durable Objects;
- отдельный LLM worker;
- background semantic daemon;
- полный rewrite Web;
- отказ от Git/YAML;
- сложный delta-profile до измеримого bottleneck;
- arbitrary bundle transaction engine;
- автоматическое восстановление старых inferred preferences;
- автоматический импорт MD-архива обратно в intelligence;
- сохранение legacy reassessment subsystem как production path.

## 36. Release Definition of Done

v6 считается готовой только когда одновременно выполнены четыре группы условий.

### Speed

Normal existing-work feedback не способен без доказуемой необходимости вызвать provider I/O, metadata refresh, semantic recomputation, несколько transaction/rebuild cycles или несколько тяжёлых CI jobs.

### Quality

Все intelligence invariants v5.1, перечисленные в этой спецификации, проходят regression tests.

### Clean cutover

Старые human data сохранены в MD-архиве, legacy runtime удалён, active library очищена, explicit global preferences сохранены.

### Compatibility

LLM работает как основной быстрый интерфейс, Web/Broker остаются рабочим вторичным клиентом той же canonical системы.

## 37. Итоговый принцип

> **Каждый тяжёлый шаг выполняется максимум один раз и только тогда, когда изменение его входов доказывает необходимость. Качество анализа и рекомендаций сохраняется как invariant, а не как best effort.**
