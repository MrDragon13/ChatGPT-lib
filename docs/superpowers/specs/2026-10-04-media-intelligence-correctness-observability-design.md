# Media Intelligence Correctness & Observability — design

Дата: 2026-10-04  
Статус: **written spec awaiting final user review**  
База: `2026-10-03-media-intelligence-recommendation-v5-design.md`, `2026-10-03-media-candidate-assessment-work-similarity-v5-1-design.md`  
Область: measurement foundation, recommendation correctness, uncertainty/coverage observability, couple disagreement visibility, path-policy trust boundary

## 1. Цель

Этот этап не пытается сделать recommendation model «умнее». Его цель — сделать существующую Media Intelligence систему:

- логически корректной в доказанных местах;
- измеряемой до изменения формул;
- наблюдаемой по основаниям рекомендаций и отсутствующим данным;
- честной относительно fallback и uncertainty;
- безопасной на границе privileged GitHub automation;
- готовой к последующему evaluation-driven выбору scoring, weighting и enrichment решений.

Основной принцип этапа:

> Сначала correctness и measurement, затем формулы. Отсутствие данных не должно выглядеть как положительный сигнал, а explanation-layer гипотезы не должны усиливать сами себя численно.

## 2. Контекст и подтверждённые проблемы

Текущая реализация уже имеет deterministic Python core, generated profiles, recommendation context, semantic fingerprints, couple profiles и guarded auto-merge. При этом аудит текущего состояния выявил несколько проблем, которые можно исправить без выбора новой predictive/scoring модели:

1. Recommendation ranking учитывает количество matched traits без учёта знака affinity, поэтому отрицательное совпадение может улучшать позицию кандидата.
2. Inferred preference hypotheses участвуют в численной агрегации профиля и могут повторно усиливать evidence, из которого сами были выведены.
3. При низком semantic coverage система не всегда явно сообщает, что часть порядка является fallback, а не персонализированным выводом.
4. Couple profile агрегирует evidence, но потребитель не видит по каждому term направление сигналов отдельных участников.
5. Operation/path policy существует более чем в одном представлении; privileged workflow нельзя упрощать ценой исполнения изменяемого PR-head кода с write credentials.
6. До изменения formula/weights нет единого canonical audit и reproducible baseline, позволяющих сравнивать состояние до и после.

Этот design ограничен исправлением этих классов проблем. Он не утверждает, что текущие affinity magnitude, confidence rules или couple aggregation являются оптимальными.

## 3. Архитектурная граница этапа

Работа делится на два последовательных PR.

### PR0 — Measurement foundation

PR0 не меняет recommendation behavior. Он вводит canonical read-only audit и baseline snapshot.

Цель PR0 — получить воспроизводимый ответ на вопросы о составе canonical media state, качестве покрытия и фактическом candidate pool до любых behavior changes.

### PR1 — Intelligence correctness & observability

PR1 исправляет доказанные logical defects и расширяет read-only context, но не вводит новую численную recommendation formula.

PR1 включает пять компонентов:

1. sign-aware deterministic ranking policy;
2. explanation-only treatment inferred hypotheses;
3. recommendation coverage/limitations observability;
4. per-term couple disagreement observability без изменения couple score;
5. trust-safe single-source path-policy integration.

### Что сознательно не входит

В этот этап не входят:

- новый public `ranking_score`;
- подбор weights для affinity/confidence;
- pseudocount calibration;
- rating normalization/calibration;
- новая couple aggregation formula;
- arbitrary coverage confidence thresholds;
- массовое semantic enrichment;
- MMR/exploration;
- numeric rating prediction;
- optimization по MAE без отдельной predictor model и ground truth.

Эти решения должны приниматься после отдельного evaluation harness и explicit/confirmed decision benchmark.

## 4. PR0: canonical audit

### 4.1 Источник истины

Audit читает canonical data и deterministic derived state только там, где измеряется именно derived behavior.

Canonical YAML остаётся source of truth для inventory, ratings, viewing, feedback, semantic metadata и preferences. Generated profiles не должны использоваться как shortcut для метрик, которые можно напрямую восстановить из canonical state.

Если измеряется фактический recommendation candidate pool, допускается использование той же deterministic selection logic, которую использует runtime.

### 4.2 Стабильный versioned result contract

Audit result имеет явную версию формата и структурированные секции. Концептуально:

```yaml
schema_version: 1
source_revision: <git-sha-or-explicit-source-id>
inventory: ...
ratings: ...
feedback: ...
semantic_coverage: ...
similarity: ...
partner: ...
recommendation_pool: ...
```

Каждая coverage metric должна хранить явные numerator и denominator, а не только ratio.

Примеры обязательных различий:

- works и collections считаются отдельно;
- `works_total` не смешивается с `entities_total`;
- ratings по works и collections не смешиваются неявно;
- explicit, explicit_approx и inferred rating/source категории считаются отдельно, если такие категории существуют в canonical data;
- semantic coverage считается как минимум для всей work library и отдельно для фактического candidate pool;
- feedback/similarity/partner coverage получают явный denominator.

### 4.3 Determinism и provenance

Сравниваемый audit payload должен быть детерминированным для одного и того же repository state.

Wall-clock `generated_at` не входит в детерминированное содержимое baseline. Если timestamp нужен для human-facing metadata, он хранится вне сравниваемого metric payload либо нормализуется/инъецируется в тестах.

Baseline обязан содержать provenance, достаточный для восстановления контекста: как минимум format/schema version и source revision.

### 4.4 Ошибки аудита

Audit различает два состояния:

- **invalid canonical state / broken invariant** — fail closed;
- **valid, но не классифицированное состояние** — явный `unclassified_*` counter или аналогичный diagnostic field, если это допустимо schema.

Audit не должен молча пропускать записи ради красивой метрики.

### 4.5 Baseline snapshot

Snapshot является исторической точкой отсчёта, а не вторым source of truth и не lockfile пользовательских данных.

CI не должен ломать обычные media updates только потому, что текущие counts отличаются от исторического baseline. Вместо этого тестируется:

- reproducibility audit logic на fixtures;
- валидность baseline format/provenance;
- возможность сознательно пересоздать новый baseline при отдельном решении.

## 5. PR1: ranking correctness

### 5.1 Никакого нового public ranking score

PR1 не вводит public или pseudo-precise numeric `ranking_score`.

Существующие affinity `score` и `confidence` могут показываться как evidence metadata, но не становятся новой скрытой weighted formula для ordering.

### 5.2 Evidence classification

Для каждого candidate сначала независимо вычисляются:

- наличие semantic fingerprint;
- positive trait matches (`strengths`);
- negative trait matches (`concerns`);
- отсутствие user affinity для candidate traits;
- наличие или отсутствие personalized semantic basis.

Trait считается:

- strength, если соответствующий profile affinity имеет `score > 0`;
- concern, если `score < 0`;
- neutral/unmatched, если affinity отсутствует или score не имеет направления.

`confidence` и `evidence_count` не фильтруют trait в PR1 и не влияют на ordering. Они возвращаются для observability и будущего evaluation.

### 5.3 Ranking basis

Каждый candidate получает:

```text
ranking_basis: trait_overlap | none
fallback_reason: null | no_semantic_fingerprint | no_matching_affinities
```

`trait_overlap` означает, что найден хотя бы один positive или negative personalized trait match.

`none` означает, что semantic personalized ordering для этого candidate отсутствует. Наличие fingerprint само по себе не является personalized basis, если для его traits нет известных affinities.

### 5.4 Ordering contract

Candidates сначала делятся на две группы:

1. personalized (`ranking_basis=trait_overlap`);
2. fallback (`ranking_basis=none`).

Personalized group всегда идёт раньше fallback group. Это не позволяет отсутствию данных выглядеть лучше, чем реальный negative evidence.

Внутри personalized group используется только следующий transparent lexicographic key:

1. меньше `concerns`;
2. больше `strengths`;
3. выше существующий `interest.priority`;
4. стабильный `id` tie-break.

Внутри fallback group:

1. выше `interest.priority`;
2. стабильный `id` tie-break.

Следствия contract:

- добавление negative match никогда не улучшает позицию при прочих равных;
- отсутствие fingerprint не является ranking advantage;
- magnitude/confidence не скрыто кодируют новую формулу;
- ordering воспроизводим.

## 6. Recommendation observability contract

### 6.1 Backward-compatible fields

Существующие consumer-facing `strengths` и `concerns` сохраняются как `list[str]`, если текущие consumers зависят от этого shape.

PR1 расширяет contract additive metadata, например:

```yaml
strengths:
  - story.intrigue
concerns:
  - pacing.slow

evidence_details:
  strengths:
    - term: story.intrigue
      direction: positive
      affinity_score: 0.42
      confidence: medium
      evidence_count: 3
  concerns:
    - term: pacing.slow
      direction: negative
      affinity_score: -0.31
      confidence: low
      evidence_count: 1
```

`affinity_score` здесь является существующим profile attribute, а не candidate ranking score.

Если inspection всех consumers докажет, что legacy string fields не нужны, их удаление остаётся отдельной migration задачей, а не частью этого PR.

### 6.2 Global coverage

`recommend_context` получает агрегированный coverage block, концептуально:

```yaml
coverage:
  candidates_total: 12
  candidates_with_fingerprint: 5
  candidates_with_personalized_basis: 3
  candidates_fallback: 9
```

Названия могут быть уточнены implementation plan, но смысл каждого denominator должен быть однозначным.

### 6.3 Limitations reason codes

Code формирует machine-readable limitations из фактических состояний, а не из субъективных confidence thresholds.

Минимальный набор категорий:

- `partial_semantic_coverage`;
- `fallback_candidates_present`;
- `no_personalized_candidates`;
- `couple_term_disagreement` — когда релевантно couple context.

PR1 не вводит правило вида `coverage < N% => low confidence`, пока threshold не подтверждён evaluation.

### 6.4 Agent UX contract

Deterministic Python определяет, что известно и какие ограничения активны. Агент определяет естественную формулировку.

Living documentation/`media/AGENTS.md` должна зафиксировать:

- active limitation нельзя игнорировать в пользовательском объяснении, если она влияет на recommendation claim;
- `ranking_basis=none` нельзя представлять как персонализированный semantic вывод;
- fallback candidate можно рекомендовать по другим основаниям текущего запроса, но это должно быть отделено от утверждения «профиль считает, что вам это понравится»;
- uncertainty нельзя превращать в выдуманную уверенность.

Python не должен генерировать обязательную готовую пользовательскую фразу.

## 7. Inferred hypotheses: explanation-only

### 7.1 Новая граница

Inferred preference hypotheses остаются полезными как reasoning/explanation memory, но перестают участвовать в численной aggregation affinity.

Profile affinities строятся только из primary evidence, определённого текущей моделью данных. Hypothesis не должна:

- менять affinity `score`;
- повышать `confidence`;
- увеличивать numeric `evidence_count` affinity;
- становиться вторым экземпляром supporting evidence, из которого сама была выведена.

### 7.2 Почему не heuristic dedup

PR1 не пытается сопоставлять hypothesis с исходным evidence через brittle identity matching. Это оставило бы возможность double-count при изменении provenance shape.

Вместо этого граница архитектурная: hypotheses хранятся/показываются отдельным explanation layer и физически не входят в numeric aggregator.

### 7.3 Совместимость

Если generated profile сегодня содержит hypotheses рядом с affinities, schema/serialization может сохранить их как отдельный раздел. Изменяется именно aggregation semantics, а не необходимость хранить объяснение.

## 8. Couple observability

### 8.1 Цель

PR1 делает видимым различие между индивидуальными сигналами пары, но не меняет текущую couple aggregation или couple score.

### 8.2 Per-term projection

Для релевантного term context возвращает структуру уровня:

```yaml
term: visuals.strong
members:
  primary:
    direction: positive
    confidence: high
    evidence_count: 4
  partner:
    direction: negative
    confidence: medium
    evidence_count: 2
status: disagreement
```

`status` имеет как минимум:

- `agreement` — оба участника имеют направленный сигнал одного знака;
- `disagreement` — направленные сигналы противоположны;
- `insufficient` — для одного или обоих участников нет достаточного направленного evidence.

### 8.3 Инвариант

Добавление couple disagreement projection не должно менять существующий couple affinity/score. Это observability-only change.

## 9. Path policy и trust boundary

### 9.1 Требование

Operation-to-path policy должна иметь одно canonical machine-readable представление, но privileged workflow не должен для этого исполнять mutable PR-head Python с `contents: write` / `pull-requests: write` credentials.

### 9.2 Recommended boundary

Design использует следующие роли:

- canonical declarative operation/path policy хранится в trusted repository state;
- Python runtime validation читает эту policy;
- privileged auto-merge workflow использует policy только из trusted `main`/trusted revision;
- proposed changes policy проверяются отдельным unprivileged CI contract;
- workflow integration проверяет format/coverage policy, но не исполняет untrusted implementation с privileged token.

Если новая operation требует расширения policy, такое расширение должно сначала пройти normal review/CI и стать trusted state; только затем privileged automation может применять новую operation автоматически.

### 9.3 Security invariant

Ни один PR не получает возможность изменить исполняемую policy logic и в том же privileged execution запустить её до merge.

## 10. Data flow

### 10.1 PR0

```text
canonical YAML
  -> audit collector
  -> normalized metrics
  -> deterministic JSON/text representation
  -> reviewed baseline snapshot
```

Audit read-only. Никаких writes в canonical data.

### 10.2 PR1 recommendation

```text
candidate traits + target affinities
  -> classify positive/negative/unmatched evidence
  -> determine ranking_basis/fallback_reason
  -> partition personalized vs fallback
  -> deterministic ordering
  -> coverage + limitations
  -> agent explanation
```

Classification кандидата не зависит от положения других candidates. Cross-candidate logic начинается только на этапе partition/order.

## 11. Error handling

Система различает три класса состояний.

### 11.1 Invariant violation

Broken schema/canonical state — fail closed. Audit/rebuild/command сообщает ошибку.

### 11.2 Insufficient evidence

Данные валидны, но personalized basis отсутствует. Это нормальный result:

- `ranking_basis=none`;
- explicit `fallback_reason`;
- соответствующая limitation/coverage metadata.

### 11.3 Partial evidence

Часть candidate pool personalized, часть fallback. Это также нормальное состояние:

- personalized group ранжируется sign-aware;
- fallback group остаётся доступной;
- coverage показывает границу качества данных.

Отсутствие данных не превращается ни в exception, ни в implicit positive signal.

## 12. Testing strategy

### 12.1 PR0 audit fixtures

Нужны small fixture repositories с заранее известными counts.

Проверяются:

- works/collections отдельно;
- watched/rated denominators;
- source categories ratings;
- library semantic coverage;
- candidate-pool semantic coverage;
- feedback/similarity/partner numerator + denominator;
- deterministic payload для одного canonical state;
- malformed invariant fail closed;
- valid unclassified state отображается явно.

Отдельный regression test должен не позволить снова представить `103 works + 4 collections` как неясные `107 works`.

### 12.2 Ranking RED -> GREEN cases

Ключевые tests:

- candidate A: `2 strengths, 0 concerns` выше candidate B: `2 strengths, 1 concern`;
- при одинаковом числе concerns больше strengths выше;
- затем применяется `interest.priority`;
- затем стабильный `id`;
- personalized candidate выше fallback candidate;
- fallback candidates сортируются только `priority -> id`;
- repeated call возвращает одинаковый order;
- добавление concern не может улучшить rank при прочих равных.

Тесты фиксируют invariants, а не будущую scoring formula.

### 12.3 Hypothesis isolation tests

Добавление inferred hypothesis при неизменном primary evidence не меняет:

- affinity score;
- affinity confidence;
- affinity evidence_count.

При этом hypothesis остаётся доступной explanation consumer.

### 12.4 Observability tests

Проверяются:

- fingerprint + known affinity match => `trait_overlap`;
- fingerprint без known affinity => `none` + `no_matching_affinities`;
- no fingerprint => `none` + `no_semantic_fingerprint`;
- coverage соответствует candidate states;
- limitations выводятся детерминированно;
- `evidence_details` сохраняет term/direction/confidence/evidence_count;
- legacy strengths/concerns shape сохраняется на migration этапе.

### 12.5 Couple tests

Проверяются:

- same direction => agreement;
- opposite directions => disagreement;
- missing member signal => insufficient;
- disagreement projection не меняет existing couple score.

### 12.6 Security tests

Нужны regression/contract tests, доказывающие:

- privileged workflow не исполняет PR-head policy implementation до merge;
- trusted revision является источником privileged policy;
- proposed policy change валидируется в unprivileged CI;
- новая operation без trusted policy coverage не получает auto-merge path.

### 12.7 Agent contract tests

Не проверяется точная русская/английская фраза. Проверяется нормативная documentation contract:

- active limitation должна учитываться;
- fallback не маскируется под personalized semantic result;
- uncertainty не маскируется под certainty.

## 13. Backward compatibility и rollout

### 13.1 Additive first

PR1 предпочитает additive context fields вместо изменения shape существующих consumer-facing полей.

Перед merge проверяются current consumers:

- CLI;
- agent instructions;
- web manifest/export;
- broker boundary, если recommendation context проходит через него;
- relevant documentation/tests.

Если поле меняет meaning, а не только получает additive metadata, нужен явный version/migration decision.

### 13.2 Никакого semantic backfill как prerequisite

PR1 не требует сначала увеличить число fingerprints.

При текущем низком coverage корректный результат — явно показать большую fallback долю. Targeted enrichment следует только после measurement/evaluation и не является условием correctness fix.

### 13.3 Baseline не блокирует обычные data changes

Historical baseline фиксирует состояние перед stage A. Он не обязан равняться текущим counts после каждого легитимного media update.

## 14. Acceptance criteria

### Measurement

- один canonical audit воспроизводимо объясняет roadmap metrics;
- works/collections и их denominators не смешиваются;
- можно однозначно определить semantic coverage фактического candidate pool;
- baseline имеет format version и source provenance.

### Correctness

- negative affinity не может улучшить ranking при прочих равных;
- отсутствие fingerprint/basis не является ranking advantage;
- personalized candidates идут перед fallback;
- inferred hypothesis не меняет numeric affinity/confidence/evidence_count;
- ordering deterministic.

### Observability

Для любого recommendation result можно определить:

- personalized он или fallback;
- strengths и concerns;
- confidence/evidence count relevant matches;
- coverage candidate pool;
- активные limitations.

### Couple

- per-term disagreement доступен consumer;
- existing couple aggregation не меняется.

### Agent UX

- следование contract не позволяет представить fallback как уверенную персональную semantic рекомендацию.

### Security

- privileged auto-merge не исполняет mutable PR-head policy code;
- operation/path policy имеет один trusted semantic source;
- drift и missing operation coverage ловятся CI.

## 15. Что остаётся после stage A

Stage A сознательно оставляет открытыми:

- optimal affinity/confidence weights;
- pseudocount/source weights;
- rating calibration;
- couple aggregation alternatives;
- confidence thresholds;
- semantic enrichment target;
- temporary external candidate fingerprinting;
- exploration/MMR;
- predictive rating model.

Следующий architecture cycle должен начать с evaluation/ground-truth design, а не с выбора формулы. Для model selection следует разделять diagnostic benchmark на всей доступной истории и decision benchmark на небольшом explicit/confirmed stratified set, чтобы не оптимизировать новую модель против старых inferred labels.

## 16. Recommended implementation sequence

После финального review этой spec:

1. написать отдельный implementation plan через `writing-plans`;
2. реализовать PR0 полностью и зафиксировать baseline до behavior changes;
3. реализовать PR1 как единый correctness + observability change;
4. проверить consumers и trust boundary;
5. только после stage A проектировать evaluation harness / ground-truth benchmark.

Implementation plan должен назвать точные файлы, tests и команды проверки. Эта design spec намеренно фиксирует behavioral contracts и trust boundaries, а не преждевременно привязывает каждое решение к конкретной функции.