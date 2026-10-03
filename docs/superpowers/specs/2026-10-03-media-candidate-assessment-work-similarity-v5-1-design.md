# Media Candidate Assessment & Work Similarity v5.1 — design

Дата: 2026-10-03  
Статус: **written spec awaiting user review**  
База: `2026-10-03-media-intelligence-recommendation-v5-design.md`  
Область: candidate assessment, explicit user work similarity, external work references, web/read-model projection

## 1. Цель

Расширить Media Intelligence v5 двумя связанными возможностями:

1. отвечать на вопрос «понравится ли мне этот фильм?» как на отдельный read-only сценарий с объяснимым выводом;
2. сохранять явное пользовательское знание вида «A похож на B», включая причины похожести, даже если один из фильмов ещё не добавлен в медиатеку.

Решение должно сохранять существующие принципы v5:

- Git/YAML остаётся canonical source of truth;
- normal writes идут через strict typed commands и deterministic Python;
- generated/read-model данные полностью пересобираемы;
- explicit и inferred evidence не смешиваются;
- LLM не создаёт vocabulary terms на лету;
- внешнее произведение не становится canonical work только потому, что оно было упомянуто, рекомендовано или использовано как similarity endpoint;
- объяснимость важнее непрозрачного similarity/recommendation score.

## 2. Границы релиза

v5.1 вводит:

- read-only capability `assess_candidate`;
- canonical explicit user similarity между произведениями;
- target-specific similarity для `primary`, `partner`, `couple`;
- `WorkRef`, который может указывать либо на canonical work, либо на external identity;
- typed write operations для upsert/remove similarity;
- deterministic reconciliation external reference → canonical work;
- derived web/read-model projection similarity в обе стороны;
- agent scenarios для сохранения, удаления, чтения и объяснения similarity, а также candidate assessment.

v5.1 не вводит:

- универсальный численный similarity score между всеми works;
- автоматическое сохранение LLM-derived similarity;
- автоматическое добавление внешнего фильма в медиатеку;
- автоматическое создание vocabulary terms;
- обучение stable preference только из одной similarity-связи;
- сложную версионную историю similarity assertions;
- новые relation types кроме `similar`;
- opaque probability вида «82% понравится».

## 3. Почему similarity не расширяет `work.canonical_relations`

Существующие `canonical_relations` описывают прежде всего связи самих произведений: sequel, prequel, spinoff, remake, reboot, adaptation. Они объективнее, directional и не зависят от viewer target.

Пользовательская similarity имеет другую семантику:

- субъективна;
- target-specific;
- симметрична;
- может содержать viewer-authored explanation;
- может ссылаться на external work, которого ещё нет в canonical library;
- должна отличаться от автоматически выведенной semantic similarity.

Поэтому explicit similarity хранится в отдельном canonical relation layer и не смешивается с `work.canonical_relations`.

## 4. Canonical explicit similarity

### 4.1 Семантика

Одна canonical запись означает:

> target явно считает work A и work B похожими по указанным причинам.

Порядок A/B не имеет значения. Физически хранится одна запись на `(target, unordered pair)`.

Концептуальный пример:

```yaml
type: similar
target: primary
works:
  - work_id: deja-vu-2006
  - external:
      provider: tmdb
      id: "45612"
      title: Source Code
      year: 2011
terms:
  - narrative.time_loop
note: >-
  Оба строятся вокруг повторного переживания события и расследования причины катастрофы.
updated_at: 2026-10-03T18:00:00Z
provenance:
  source: explicit
```

`updated_at` является частью current-assertion semantics и обновляется при каждом explicit upsert. Он используется только для определения актуального assertion при reconciliation collision, а не как дополнительный taste signal.

Точный file layout и schema naming являются implementation detail, но canonical invariants из этого документа обязательны.

### 4.2 Симметрия

Similarity — undirected relation.

`A similar B` и `B similar A` обязаны разрешаться в одну и ту же canonical identity. Нельзя хранить две зеркальные записи только ради удобства чтения.

Симметричная проекция допустима и желательна в generated/read-model слое, где одна canonical связь может появляться в карточке A и карточке B.

### 4.3 Target

Similarity хранится независимо для:

- `primary`;
- `partner`;
- `couple`.

Одинаковая пара works для разных targets является разными assertions. Нельзя автоматически переносить мнение одного target на другой.

### 4.4 Причины похожести

Причины состоят из:

- `terms`: существующие canonical vocabulary terms;
- optional `note`: краткое человеческое пояснение, сохраняющее нюанс пользователя.

LLM не создаёт новый vocabulary term только ради записи similarity. Если подходящего canonical term нет, смысл сохраняется в `note`; расширение vocabulary является отдельной developer/manual задачей.

### 4.5 Explicit vs derived similarity

Только явно подтверждённая пользователем similarity становится canonical.

LLM/system-derived similarity:

- может вычисляться из semantic fingerprints;
- может использоваться в read/explain/recommendation reasoning;
- может отображаться как отдельная derived категория;
- не становится canonical assertion без явного подтверждения пользователя.

Это предотвращает self-reinforcement, когда модель использует собственную предыдущую догадку как новое независимое evidence.

## 5. `WorkRef`: canonical и external endpoints

### 5.1 Зачем нужен external endpoint

Similarity должна сохраняться, даже если один из фильмов ещё отсутствует в медиатеке.

Упоминание внешнего фильма внутри relation не должно:

- создавать полноценный canonical work;
- выставлять viewing/interest state;
- добавлять фильм в обычный library catalog;
- превращать recommendation candidate в сохранённый work.

Поэтому relation endpoint использует общий тип `WorkRef`.

### 5.2 Концептуальная модель

```text
WorkRef
├── canonical
│   └── work_id
└── external
    ├── provider
    ├── provider_id
    ├── title
    └── year
```

Поддерживаются:

- canonical ↔ canonical;
- canonical ↔ external;
- external ↔ external.

Основной пользовательский сценарий — canonical ↔ external, но доменная модель не должна искусственно запрещать external ↔ external.

### 5.3 Identity external work

Persistent external endpoint обязан иметь устойчивый `(provider, provider_id)`. `title` и `year` являются display snapshot, а не identity key.

Если пользователь назвал неоднозначный фильм и система не может надёжно разрешить provider identity, она не должна сохранять догадку. Допустим один короткий blocking clarification, например: «Source Code 2011 года?». Если после уточнения provider identity всё ещё нельзя установить надёжно, similarity остаётся несохранённой, а не записывается по одному title.

После сохранения relation доступность внешнего provider не требуется для чтения уже сохранённой связи: snapshot должен быть достаточен для базового отображения.

## 6. Normalization и canonical identity relation

Перед записью оба endpoints приводятся к стабильным identity keys:

- canonical: `work:<work_id>`;
- external: `external:<provider>:<provider_id>`.

Пара сортируется детерминированно по identity key. Relation identity логически строится из:

```text
(target, relation_type=similar, min(endpoint_a, endpoint_b), max(endpoint_a, endpoint_b))
```

Следствия:

- A/B и B/A дают одну запись;
- repeated assertion делает upsert, а не append duplicate;
- self-relation запрещена;
- reversed duplicate запрещён;
- storage representation не задаёт direction.

## 7. Typed write contract

Добавляются normal typed operations:

```text
set_work_similarity
remove_work_similarity
```

После реализации они должны идти через существующий protected media command pipeline. LLM не редактирует canonical relation files напрямую.

### 7.1 `set_work_similarity`

Концептуально принимает:

```text
target
left: WorkRef
right: WorkRef
terms: [canonical vocabulary terms]
note?: string | null
```

Поведение:

1. resolve/validate endpoints;
2. detect self-relation;
3. normalize unordered pair;
4. validate vocabulary terms;
5. create or replace current relation for this `(target, pair)`;
6. replace `terms` and `note` as the current assertion rather than silently accumulating historical reasons;
7. set canonical `updated_at` from the accepted operation timestamp;
8. rebuild dependent read models;
9. validate transaction atomically.

### 7.2 `remove_work_similarity`

Удаляет current relation для `(target, unordered pair)` независимо от того, представлены endpoints сейчас canonical или external refs.

Фраза пользователя вроде «я больше не считаю A похожим на B» соответствует remove semantics, а не отрицательной similarity record.

### 7.3 Upsert semantics

Повторное утверждение обновляет одну запись. v5.1 не хранит append-only history изменений opinion. Если такая история понадобится позже, это отдельное расширение.

## 8. Reconciliation external → canonical

Когда external work позже действительно добавляется в canonical library, relation должна автоматически начать ссылаться на canonical work.

Пример:

```text
external:tmdb:45612
        ↓
work:source-code-2011
```

Reconciliation является deterministic domain step при создании work или изменении его stable external identity. Она выполняется в той же atomic media transaction до rebuild, поэтому successful `add_work` не оставляет stale external refs на уже известный canonical work.

Предпочтительный результат — физическая нормализация canonical relation endpoint на `work_id`, а не вечный provider lookup при каждом чтении.

Reconciliation учитывает:

- совпадение stable provider identity;
- self-link после замены endpoint;
- duplicate relations, которые могут схлопнуться после canonicalization;
- сохранение `target`, `terms`, `note`, `updated_at`, provenance.

После reconciliation не должно существовать двух эквивалентных relation records для одного target и одной unordered canonical pair.

### 8.1 Collision policy

Если external→canonical normalization приводит две relation records к одной `(target, pair)`, применяется deterministic current-assertion policy:

1. если `terms` и `note` совпадают, записи схлопываются; сохраняется более поздний `updated_at`;
2. если assertions различаются, запись с более поздним `updated_at` считается текущим явным мнением и заменяет более старую;
3. при одинаковом `updated_at` предпочтение получает запись, которая уже использовала canonical endpoint до reconciliation; если обе были одинакового endpoint-kind, применяется стабильный lexical tie-break по relation identity;
4. `terms` и `note` никогда не объединяются автоматически из конфликтующих assertions.

Эта политика согласуется с upsert semantics v5.1: canonical слой хранит текущее мнение, а не историю всех прошлых формулировок.

Если reconciliation превращает пару в self-link, такая stale relation удаляется как логически бессмысленная после identity merge; это должно быть явно отражено в deterministic operation result и покрыто тестом.

## 9. Similarity как evidence для taste reasoning

Explicit similarity является полезным evidence, но не preference сама по себе.

Фраза:

> «A похож на B»

не означает автоматически:

> «мне нравится trait X».

Допустимое использование:

- recommendation explanation;
- candidate comparison;
- поиск cross-work correlations;
- усиление или ослабление inferred hypothesis только совместно с независимыми rating/feedback/reaction/semantic signals.

Примеры:

- если target высоко оценил A и B и явно считает их похожими, общие traits могут получить дополнительную поддержку;
- если target считает A и B похожими, но оценки резко расходятся, relation является полезным контрпримером и может помочь понять различающий фактор;
- одна similarity-связь без других сигналов не создаёт stable taste hypothesis.

Generated/inferred output не должен становиться независимым evidence для самого себя.

## 10. Candidate assessment

### 10.1 Назначение

Добавляется отдельная read-only capability `assess_candidate` для запросов:

- «Мне понравится X?»;
- «Как думаешь, X мне зайдёт?»;
- «Насколько X похож на то, что мне обычно нравится?»;
- «Почему ты думаешь, что X мне понравится?».

Capability работает и для canonical work, и для external candidate, которого нет в library.

### 10.2 Inputs

Концептуально:

```text
target
candidate: WorkRef or externally resolved candidate identity
request_text?: string
```

`request_text` может содержать ephemeral контекст вроде «сегодня хочется что-то динамичное». Такой контекст не становится stable taste автоматически.

### 10.3 Evidence assembly

Assessment собирает только релевантный compact context:

- explicit preferences;
- inferred preferences с provenance/confidence;
- representative positive/negative works;
- recent relevant feedback;
- candidate factual/semantic fingerprint;
- explicit similarity relations;
- relevant cross-work correlations;
- текущие ephemeral constraints.

Для внешнего candidate provider/LLM semantic analysis может использоваться transiently без создания canonical work.

### 10.4 Output contract

Assessment не возвращает псевдоточный процент.

Предпочтительная структура:

```text
verdict: likely | mixed | unlikely
confidence: low | medium | high
positive_reasons
risks
relevant_evidence_works
provenance/explanation
```

Human-facing формулировка может быть естественной, например:

> Скорее понравится. Уверенность: medium.
>
> Почему: тебе обычно заходят истории с активным расследованием; ты высоко оценил Déjà Vu; ты сам считаешь Déjà Vu и Source Code похожими.
>
> Риски: ...

Важно различать:

- что пользователь сказал явно;
- что является inferred hypothesis;
- что является свойством candidate;
- что является текущим ephemeral request context.

### 10.5 Read-only invariant

Сам assessment ничего не сохраняет:

- не создаёт work;
- не создаёт similarity;
- не создаёт preference;
- не записывает prediction как evidence.

Новое canonical evidence появляется только после реального пользовательского действия: feedback, rating, viewing, explicit preference/similarity или поддерживаемого recommendation interaction.

## 11. Read models и web manifest

Web/read-model слой получает derived projection explicit similarity.

Для canonical work relation должна быть доступна с обеих сторон, хотя в canonical storage запись одна.

Пример поведения:

```text
Déjà Vu page
  → Source Code

Source Code page
  → Déjà Vu
```

Если endpoint external, read model может включать lightweight display snapshot:

- title;
- year;
- provider identity;
- poster/other provider display metadata, если оно уже доступно и безопасно кэшируется.

External relation endpoint не должен автоматически появляться как обычный library work.

Поскольку меняется публичный web-manifest contract, версия manifest должна быть повышена при реализации.

## 12. UI

На work detail page появляется блок «Похожие фильмы».

Минимальный обязательный v5.1 UI:

### По твоему мнению

Показывает canonical explicit similarity для выбранного target.

Для external endpoint отображается lightweight card, которая явно не маскируется под полноценную library entry.

### По характеристикам

Derived similarity должна быть визуально и семантически отделена от explicit user opinion.

Этот подраздел показывается только если implementation уже имеет надёжный derived similarity source. v5.1 не должен создавать новый opaque ranking algorithm только ради заполнения UI.

Для `partner` и `couple` фильтрация идёт по выбранному target. Мнения разных targets не смешиваются.

## 13. Error handling и guardrails

Обязательные ошибки/валидации:

- self-relation запрещена при обычной записи;
- unknown canonical `work_id` запрещён;
- external reference без stable provider identity запрещена для persistent similarity;
- malformed/unsupported external identity запрещена;
- reversed duplicate нормализуется в существующую relation;
- unknown vocabulary term не записывается;
- provider outage не делает уже сохранённую relation нечитаемой;
- ambiguous unresolved title не сохраняется как guessed external identity;
- canonicalization external → work не создаёт duplicate silently;
- reconciliation collision следует правилам §8.1;
- relation write transaction не оставляет partially modified canonical/generated state при validation failure.

## 14. Agent/user scenarios

Сценарий-каталог должен покрыть как минимум:

```text
«Дежавю похож на Исходный код»
«Дежавю похож на Исходный код из-за временной петли и расследования»
«Мы считаем A и B похожими»
«Ей A напоминает B»
«Я больше не считаю A похожим на B»
«Что у меня похоже на Дежавю?»
«Почему я считаю A и B похожими?»
«Почему ты считаешь A и B похожими?»
«Понравится ли мне X?»
«Почему ты думаешь, что X мне понравится?»
```

В сценариях `X`, `A` или `B` могут отсутствовать в canonical library.

Если пользователь спрашивает, почему **он** считает works похожими, agent должен опираться на explicit relation note/terms. Если пользователь спрашивает, почему **система** считает works похожими, agent должен отделять derived semantic comparison от explicit user assertion.

## 15. Testing contract

Реализация должна иметь coverage минимум на следующих уровнях.

### 15.1 Schema/domain

- canonical/external `WorkRef` validation;
- pair normalization;
- self-link rejection;
- target validation;
- vocabulary-term validation;
- deterministic relation identity;
- rejection/deduplication reversed duplicates.

### 15.2 Typed commands

- create explicit similarity;
- update existing similarity;
- remove similarity;
- A/B и B/A дают один canonical result;
- unknown work/external identity fails atomically;
- terms/note replacement semantics;
- accepted operation updates `updated_at` deterministically.

### 15.3 Reconciliation

- external → canonical by stable provider ID;
- relation remains visible after reconciliation;
- no duplicate after canonicalization;
- self-link after reconciliation is removed deterministically;
- identical collisions deduplicate;
- conflicting collisions select the latest assertion without merging terms/notes;
- equal-timestamp tie-break is deterministic.

### 15.4 Taste/read context

- explicit similarity appears as separately attributed evidence;
- similarity alone does not create stable inferred preference;
- target boundaries are preserved;
- derived similarity is not represented as explicit user evidence.

### 15.5 Candidate assessment

- canonical candidate works;
- external candidate works without adding library entry;
- call is read-only;
- output separates explicit/inferred/candidate/ephemeral evidence;
- no numeric probability is required or invented;
- explicit similarity can support explanation without becoming preference.

### 15.6 Web

- manifest version update;
- explicit relation projected both directions;
- external lightweight endpoint rendered without becoming library work;
- target filtering;
- canonicalized endpoint starts linking to full work after reconciliation;
- existing work pages without similarity remain backward-safe.

## 16. Compatibility и migration

Existing work files и `canonical_relations` сохраняют текущую семантику.

Новый relation layer изначально пуст, поэтому existing canonical data не требует content migration.

Generated/read-model schema changes потребуют rebuild и web-manifest version bump, но не ручного преобразования существующих works.

Existing recommendation behavior остаётся совместимым: similarity добавляет новый evidence source, но не заменяет taste context, semantic fingerprint или concrete anchors.

После реализации `set_work_similarity` и `remove_work_similarity` становятся normal auto-merge-eligible media operations при условии отдельного path-policy allowlist только для relation canonical paths и ожидаемых generated outputs, плюс прохождения exact-head Media Check. Сам rollout architecture/schema/service/web/tests/workflow изменений остаётся developer/manual route.

Поскольку `add_work` может запускать reconciliation, его path policy после v5.1 должен разрешать только детерминированные relation-file изменения, вызванные external→canonical identity normalization в той же transaction. Это расширение покрывается отдельными path-policy и regression tests.

## 17. Implementation boundaries

При реализации ожидаются изменения в следующих областях:

- relation schema/storage/domain model;
- `WorkRef` validation/normalization;
- typed command schemas и deterministic service apply;
- reconciliation logic;
- validation/rebuild/doctor coverage;
- taste/recommendation context assembly;
- read-only `assess_candidate` contract;
- web manifest schema/export/types;
- work detail UI;
- agent contract/scenario catalog/status docs;
- tests и workflow/path-policy allowlists для новых normal operation kinds.

Точный список файлов определяется implementation plan после review этого spec.

## 18. Acceptance criteria

v5.1 считается архитектурно реализованным, когда одновременно выполняются условия:

1. пользователь может явно сохранить `A similar B` для `primary`, `partner` или `couple`;
2. relation хранится один раз и читается симметрично;
3. optional structured terms и note сохраняют причины similarity;
4. external endpoint поддерживается без добавления фильма в library;
5. последующее добавление external work корректно reconciles relation на canonical work;
6. reconciliation collision разрешается детерминированно по current-assertion policy без смешивания conflicting reasons;
7. explicit и derived similarity остаются различимыми;
8. similarity может участвовать в explanation/reasoning, но сама не создаёт stable preference;
9. `assess_candidate` работает для canonical и external candidates и ничего не мутирует;
10. assessment объясняет verdict через provenance-aware evidence без fake percentage;
11. web показывает explicit similarity с обеих сторон и корректно обрабатывает external endpoint;
12. новые similarity writes и reconciliation проходят через существующие typed transaction/path-policy safety boundaries;
13. validation/rebuild/doctor и relevant web checks проходят на изменённой архитектуре;
14. существующие v5 invariants — source-of-truth, typed write path, target separation, provenance и no-self-reinforcement — остаются сохранены.

## 19. Итоговое архитектурное решение

v5.1 добавляет два новых понятия, но не смешивает их:

- **explicit work similarity** — canonical, subjective, target-specific, symmetric relation с optional structured reasons и human note;
- **candidate assessment** — read-only reasoning поверх существующего taste context, candidate knowledge и explicit relations.

External work identity является lightweight reference, а не скрытым способом добавить work в медиатеку. Derived model opinions не становятся canonical user facts без подтверждения. Это позволяет сохранить полезное долговременное знание о связях между фильмами и улучшить объяснимость рекомендаций без размывания границ source-of-truth и evidence provenance.