# Media Intelligence Correctness & Observability — design

Дата: 2026-10-04  
Статус: **written spec awaiting final user review**  
База: `2026-10-03-media-intelligence-recommendation-v5-design.md`, `2026-10-03-media-candidate-assessment-work-similarity-v5-1-design.md`  
Область: measurement foundation, recommendation/assessment correctness and observability, couple disagreement visibility, path-policy trust boundary

## 1. Цель

Этот этап не пытается сделать recommendation model «умнее». Его цель — сделать существующую Media Intelligence систему:

- логически корректной в доказанных местах;
- измеряемой до изменения формул;
- наблюдаемой по основаниям рекомендаций, candidate assessment и отсутствующим данным;
- честной относительно fallback и uncertainty;
- безопасной на границе privileged GitHub automation;
- готовой к последующему evaluation-driven выбору scoring, weighting и enrichment решений.

Основной принцип этапа:

> Сначала correctness и measurement, затем формулы. Отсутствие данных не должно выглядеть как положительный сигнал, а explanation-layer гипотезы не должны усиливать сами себя численно.

## 2. Контекст и подтверждённые проблемы

Текущая реализация уже имеет deterministic Python core, generated profiles, recommendation context, candidate assessment context, semantic fingerprints, couple profiles и guarded auto-merge. При этом аудит текущего состояния выявил несколько проблем, которые можно исправить без выбора новой predictive/scoring модели:

1. Recommendation ranking учитывает количество matched traits без учёта знака affinity, поэтому отрицательное совпадение может улучшать позицию кандидата.
2. Inferred preference hypotheses участвуют в численной агрегации профиля и могут повторно усиливать evidence, из которого сами были выведены.
3. При низком semantic coverage recommendation и assessment flows не всегда явно сообщают, насколько вывод опирается на semantic evidence, а часть recommendation order может быть fallback, а не персонализированным выводом.
4. Couple profile агрегирует evidence, но потребитель не видит по каждому term направление сигналов отдельных участников.
5. Operation/path policy существует более чем в одном представлении; privileged workflow нельзя упрощать ценой исполнения изменяемого PR-head кода с write credentials.
6. До изменения formula/weights нет единого canonical audit и reproducible baseline, позволяющих сравнивать состояние до и после.

Этот design ограничен исправлением этих классов проблем. Он не утверждает, что текущие affinity magnitude, confidence rules, assessment verdict logic или couple aggregation являются оптимальными.

## 3. Архитектурная граница этапа

Работа делится на два последовательных PR.

### Stage A / PR0 — Measurement foundation

PR0 не меняет recommendation или assessment behavior. Он вводит canonical read-only audit и baseline snapshot.

Цель PR0 — получить воспроизводимый ответ на вопросы о составе canonical media state, качестве покрытия и каноническом recommendation candidate pool до любых behavior changes.

### Stage A / PR1 — Intelligence correctness & observability

PR1 исправляет доказанные logical defects и расширяет read-only context, но не вводит новую predictive formula или deterministic assessment verdict.

PR1 включает шесть компонентов:

1. sign-aware deterministic recommendation ranking policy;
2. explanation-only treatment inferred hypotheses;
3. recommendation coverage/limitations observability;
4. минимальную semantic coverage observability для `assess_candidate`;
5. per-term couple disagreement observability без изменения couple score;
6. trust-safe single-source path-policy integration.

### Соответствие roadmap revision 3

В этой spec используется локальная нумерация Stage A:

- **PR0** соответствует measurement foundation из roadmap P0;
- **PR1** объединяет correctness + observability work, который в roadmap распределён между ранними PR/P1-пунктами;
- assessment core, semantic provenance/versioning и evaluation harness остаются следующими отдельными этапами, а не скрытой частью Stage A.

Эта нумерация задаёт delivery sequence этой spec и не переименовывает roadmap целиком.

### Что сознательно не входит

В этот этап не входят:

- новый public `ranking_score`;
- подбор weights для affinity/confidence;
- pseudocount calibration;
- rating normalization/calibration;
- deterministic `assess_candidate` verdict/scoring core;
- новая couple aggregation formula;
- arbitrary coverage confidence thresholds;
- массовое semantic enrichment;
- semantic enrichment versioning (`vocab_version`, `enriched_at`, `enriched_by`);
- MMR/exploration;
- numeric rating prediction;
- optimization по MAE без отдельной predictor model и ground truth.

Эти решения должны приниматься после отдельного evaluation harness и explicit/confirmed decision benchmark либо в специально выделенном semantic-provenance этапе.

## 4. PR0: canonical audit

### 4.1 Источник истины

Audit читает canonical data и deterministic derived state только там, где измеряется именно derived behavior.

Canonical YAML остаётся source of truth для inventory, ratings, viewing, feedback, semantic metadata и preferences. Generated profiles не должны использоваться как shortcut для метрик, которые можно напрямую восстановить из canonical state.

Если измеряется recommendation candidate pool, audit должен использовать ту же deterministic eligibility logic, что и runtime, но с каноническими параметрами, определёнными ниже.

### 4.2 Стабильный versioned result contract

Audit result имеет явную версию формата и структурированные секции. Концептуально:

```yaml
schema_version: 1
canonical_input_digest: <content-digest>
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
- semantic coverage считается как минимум для всей work library и отдельно для canonical recommendation pool;
- feedback/similarity/partner coverage получают явный denominator.

### 4.3 Determinism, input digest и provenance

Сравниваемый audit payload должен быть детерминированным для одного и того же набора canonical inputs.

`canonical_input_digest` вычисляется из нормализованного набора canonical файлов, реально использованных audit. Конкретный hash algorithm и canonicalization format фиксируются implementation plan/tests; порядок файлов не должен влиять на digest.

Git commit SHA не является частью сравниваемого metric payload, потому что baseline commit не может содержать собственный окончательный SHA без самоссылки. Git revision, human-facing timestamp и прочая execution metadata могут храниться рядом с payload как несравниваемая provenance-обёртка.

Wall-clock `generated_at` не входит в deterministic payload. Если timestamp нужен для human-facing metadata, он хранится только в provenance metadata либо нормализуется/инъецируется в тестах.

### 4.4 Канонический recommendation pool

Чтобы coverage не зависел от произвольного runtime query, PR0 определяет канонический pool отдельно для каждого supported target:

- только локальные canonical works;
- `only_unwatched=true`;
- без `limit`;
- без runtime/duration filter;
- без query-specific filters;
- без external discovery candidates.

Если runtime eligibility имеет дополнительные обязательные invariant-фильтры, audit использует их же; implementation plan должен перечислить их явно.

Audit хранит coverage канонического pool. Runtime context отдельно может считать coverage конкретного запроса.

### 4.5 Ошибки аудита

Audit различает два состояния:

- **invalid canonical state / broken invariant** — fail closed;
- **valid, но не классифицированное состояние** — явный `unclassified_*` counter или аналогичный diagnostic field, если это допустимо schema.

Audit не должен молча пропускать записи ради красивой метрики.

### 4.6 Baseline snapshot

Snapshot является исторической точкой отсчёта, а не вторым source of truth и не lockfile пользовательских данных.

CI не должен ломать обычные media updates только потому, что текущие counts отличаются от исторического baseline. Вместо этого тестируется:

- reproducibility audit logic на fixtures;
- валидность baseline format/input digest/provenance;
- возможность сознательно пересоздать новый baseline при отдельном решении.

## 5. PR1: recommendation ranking correctness

### 5.1 Никакого нового public ranking score

PR1 не вводит public или pseudo-precise numeric `ranking_score`.

Существующие affinity `score` и `confidence` могут показываться как evidence metadata, но не становятся новой скрытой weighted formula для ordering.

Внутренний integer `strengths_count - concerns_count` используется только как первый элемент deterministic ordering key. Он не публикуется как probability, preference score или самостоятельная model output.

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

Personalized group всегда идёт раньше fallback group. Это не позволяет отсутствию данных выглядеть лучше, чем реальный evidence.

Внутри personalized group используется следующий transparent lexicographic key:

1. больше `strengths_count - concerns_count`;
2. при равном net count — меньше `concerns`;
3. выше существующий `interest.priority`;
4. стабильный `id` tie-break.

Внутри fallback group:

1. выше `interest.priority`;
2. стабильный `id` tie-break.

Следствия contract:

- добавление negative match никогда не улучшает позицию при прочих равных;
- добавление positive match никогда не ухудшает позицию при прочих равных;
- отсутствие fingerprint не является ranking advantage;
- один concern не является абсолютным veto против любого clean candidate;
- magnitude/confidence не скрыто кодируют новую weighted formula;
- ordering воспроизводим.

### 5.5 Временный policy, а не доказанная model

Этот ordering — осознанно минимальная Stage A policy, выбранная для исправления sign bug без confidence/weight tuning.

Следующий evaluation stage должен сравнить как минимум:

- текущий Stage A key: `net directional matches -> fewer concerns`;
- более осторожный вариант: `fewer concerns -> more strengths`;
- другие простые baselines, определённые evaluation design.

Stage A не утверждает, что выбранный lexicographic key оптимален по recommendation quality.

## 6. Recommendation observability contract

### 6.1 Backward-compatible fields

Существующие consumer-facing `strengths` и `concerns` сохраняются как `list[str]`, если current consumers зависят от этого shape.

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

### 6.2 Global coverage: pool vs returned results

`recommend_context` получает агрегированный coverage block с явным различием между eligible pool до `limit` и фактически возвращённым списком после `limit`.

Концептуально:

```yaml
coverage:
  pool_total: 42
  pool_with_fingerprint: 8
  pool_with_personalized_basis: 5
  pool_fallback: 37

  returned_total: 12
  returned_with_fingerprint: 5
  returned_with_personalized_basis: 3
  returned_fallback: 9
```

`pool_*` относится к eligible candidate set после request filters (`target`, `only_unwatched`, runtime и другие runtime filters), но до `limit`.

`returned_*` относится к фактически возвращённым candidates после ordering и `limit`.

Так смена ranking не маскируется как изменение denominator coverage.

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

## 7. Candidate assessment observability

### 7.1 Scope

Stage A не вводит deterministic verdict для `assess_candidate`, но assessment flow должен перестать быть слепым к semantic coverage.

Assessment переиспользует тот же read-only semantic evidence classification primitive, что recommendation, насколько это применимо к одному кандидату.

### 7.2 Минимальный coverage contract

Assessment context должен позволять consumer определить как минимум:

- есть ли semantic fingerprint у оцениваемого candidate;
- сколько candidate traits имеют известное target affinity и направленный сигнал;
- сколько relevant/supporting local works использовано assessment context;
- сколько из этих supporting works имеют semantic fingerprint;
- какие coverage limitations активны.

Концептуально:

```yaml
assessment_coverage:
  candidate_has_fingerprint: true
  candidate_directional_matches: 3
  supporting_works_total: 6
  supporting_works_with_fingerprint: 2
limitations:
  - partial_semantic_coverage
```

Точные имена полей уточняются implementation plan после проверки current `assess_candidate` consumer shape, но смысл denominator должен остаться однозначным.

### 7.3 Что Stage A не делает

Stage A не превращает coverage в `likely/unlikely` формулу и не задаёт confidence threshold для verdict.

Если agent формулирует qualitative assessment, активные limitations должны быть отражены по тому же принципу, что и recommendation: недостаток semantic evidence нельзя маскировать под уверенное основание.

Deterministic assessment core остаётся следующим этапом.

## 8. Inferred hypotheses: explanation-only

### 8.1 Новая граница

Inferred preference hypotheses остаются полезными как reasoning/explanation memory, но перестают участвовать в численной aggregation affinity.

Profile affinities строятся только из primary evidence, определённого текущей моделью данных. Hypothesis не должна:

- менять affinity `score`;
- повышать `confidence`;
- увеличивать numeric `evidence_count` affinity;
- становиться вторым экземпляром supporting evidence, из которого сама была выведена.

### 8.2 Почему не heuristic dedup

PR1 не пытается сопоставлять hypothesis с исходным evidence через brittle identity matching. Это оставило бы возможность double-count при изменении provenance shape.

Вместо этого граница архитектурная: hypotheses хранятся/показываются отдельным explanation layer и физически не входят в numeric aggregator.

### 8.3 Совместимость и ожидаемый generated diff

Если generated profile сегодня содержит hypotheses рядом с affinities, schema/serialization может сохранить их как отдельный раздел. Изменяется именно aggregation semantics, а не необходимость хранить объяснение.

После реализации и rebuild ожидается содержательный diff generated profiles, потому что hypothesis evidence больше не участвует в aggregation. Review пересчёт указывает, что эффект, вероятно, небольшой, но `couple` profile может изменить confidence как минимум для одного affinity. Точные значения не фиксируются этой spec и должны подтверждаться реальным rebuild/tests в PR.

PR description должен явно отметить такой generated diff как ожидаемое следствие semantic change, а не как случайный churn.

## 9. Couple observability

### 9.1 Цель

PR1 делает видимым различие между индивидуальными сигналами пары, но не меняет текущую couple aggregation или couple score.

### 9.2 Per-term projection

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

`direction` существует, если у участника по term есть non-zero directed evidence.

`status` определяется без confidence threshold:

- `agreement` — у обоих участников есть directed evidence одного знака;
- `disagreement` — у обоих участников есть directed evidence противоположного знака;
- `insufficient` — хотя бы у одного участника нет directed evidence по этому term.

`evidence_count` и `confidence` возвращаются как observability metadata, чтобы consumer мог видеть тонкое/слабое disagreement, но не меняют status в Stage A.

### 9.3 Инвариант

Добавление couple disagreement projection не должно менять существующий couple affinity/score. Это observability-only change.

## 10. Path policy и trust boundary

### 10.1 Требование

Operation-to-path policy должна иметь одно canonical machine-readable представление, но privileged workflow не должен для этого исполнять mutable PR-head Python с `contents: write` / `pull-requests: write` credentials.

### 10.2 Canonical format

Canonical operation/path policy хранится в declarative, non-executable machine-readable формате, например YAML или JSON.

Python runtime validation читает этот declarative contract. Workflow не импортирует и не исполняет policy implementation из PR head.

Конкретный формат выбирается implementation plan с учётом текущих consumers, но файл должен разбираться как data без исполнения PR-controlled code.

### 10.3 Trusted policy lookup

Privileged auto-merge workflow получает policy из trusted `main` либо другой заранее доверенной revision.

Недостаточно просто checkout PR и открыть «тот же путь»: рабочая копия PR является untrusted.

Способ чтения trusted policy должен быть явным в implementation plan/tests, например отдельный trusted checkout/ref/API read.

Proposed policy changes проверяются отдельным unprivileged CI contract. После normal review/merge новая policy становится trusted state для последующих PR.

### 10.4 Что не автомерджится

Guarded auto-merge должен fail closed для PR, которые меняют trust-defining или executable automation surface, включая как минимум:

- canonical operation/path policy file;
- privileged workflow definitions;
- executable media command/service/tooling code, способный изменить semantics применения operation;
- CI/guard code, от которого зависит auto-merge eligibility.

Точный path set фиксируется после inspection текущего repository layout в implementation plan и покрывается contract tests.

Такие PR проходят normal human review/merge. Только уже доверенное состояние может автоматически разрешить последующие data-only operation PR.

### 10.5 Security invariant

Ни один PR не получает возможность изменить policy/guard/executable semantics и в том же privileged execution запустить изменённую логику до merge.

## 11. Data flow

### 11.1 PR0

```text
canonical YAML
  -> canonical input inventory + digest
  -> audit collector
  -> normalized metrics
  -> deterministic metric payload
  -> provenance wrapper
  -> reviewed baseline snapshot
```

Audit read-only. Никаких writes в canonical data.

### 11.2 PR1 recommendation

```text
candidate traits + target affinities
  -> classify positive/negative/unmatched evidence
  -> determine ranking_basis/fallback_reason
  -> partition personalized vs fallback
  -> deterministic ordering
  -> pool/returned coverage + limitations
  -> agent explanation
```

Classification кандидата не зависит от положения других candidates. Cross-candidate logic начинается только на этапе partition/order.

### 11.3 PR1 assessment

```text
candidate + target context + supporting works
  -> semantic evidence/coverage classification
  -> assessment_coverage + limitations
  -> agent qualitative assessment
```

Stage A не добавляет deterministic verdict calculation.

## 12. Error handling

Система различает три класса состояний.

### 12.1 Invariant violation

Broken schema/canonical state — fail closed. Audit/rebuild/command сообщает ошибку.

### 12.2 Insufficient evidence

Данные валидны, но personalized basis отсутствует. Это нормальный result:

- recommendation: `ranking_basis=none` + explicit `fallback_reason`;
- assessment: coverage fields показывают отсутствие/недостаток semantic evidence;
- соответствующая limitation metadata доступна consumer.

### 12.3 Partial evidence

Часть candidate pool personalized, часть fallback либо assessment опирается только на часть semantic context. Это также нормальное состояние:

- personalized recommendation group ранжируется sign-aware;
- fallback group остаётся доступной;
- coverage показывает границу качества данных;
- qualitative assessment не маскирует partial coverage.

Отсутствие данных не превращается ни в exception, ни в implicit positive signal.

## 13. Testing strategy

### 13.1 PR0 audit fixtures

Нужны small fixture repositories с заранее известными counts.

Проверяются:

- works/collections отдельно;
- watched/rated denominators;
- source categories ratings;
- library semantic coverage;
- canonical candidate-pool semantic coverage;
- canonical pool параметры не зависят от runtime `limit`;
- feedback/similarity/partner numerator + denominator;
- deterministic payload для одного canonical input set;
- одинаковый content set даёт одинаковый `canonical_input_digest` независимо от iteration order;
- git revision/timestamp не меняют deterministic metric payload;
- malformed invariant fail closed;
- valid unclassified state отображается явно.

Отдельный regression test должен не позволить снова представить `103 works + 4 collections` как неясные `107 works`.

### 13.2 Ranking RED -> GREEN cases

Ключевые tests:

- `2 strengths / 0 concerns` выше `2 strengths / 1 concern`;
- `5 strengths / 1 concern` выше `1 strength / 0 concerns`, потому что net directional evidence больше;
- при равном `strengths - concerns` меньше concerns выше;
- добавление concern не может улучшить rank при прочих равных;
- добавление strength не может ухудшить rank при прочих равных;
- затем применяется `interest.priority`;
- затем стабильный `id`;
- personalized candidate выше fallback candidate;
- fallback candidates сортируются только `priority -> id`;
- repeated call возвращает одинаковый order.

Тесты фиксируют Stage A policy и correctness invariants, а не утверждают, что эта policy оптимальна. Evaluation stage обязан сравнить её с альтернативным `concerns-first` baseline.

### 13.3 Hypothesis isolation tests

Добавление inferred hypothesis при неизменном primary evidence не меняет:

- affinity score;
- affinity confidence;
- affinity evidence_count.

При этом hypothesis остаётся доступной explanation consumer.

Rebuild test должен позволять ожидаемый generated profile diff, вызванный удалением hypothesis evidence из aggregation, и не классифицировать его как случайный nondeterminism.

### 13.4 Recommendation observability tests

Проверяются:

- fingerprint + known affinity match => `trait_overlap`;
- fingerprint без known affinity => `none` + `no_matching_affinities`;
- no fingerprint => `none` + `no_semantic_fingerprint`;
- `pool_*` coverage относится к pre-limit eligible set;
- `returned_*` coverage относится к фактически возвращённым results;
- изменение `limit` не меняет `pool_*`;
- limitations выводятся детерминированно;
- `evidence_details` сохраняет term/direction/confidence/evidence_count;
- legacy strengths/concerns shape сохраняется на migration этапе.

### 13.5 Assessment observability tests

Проверяются:

- candidate fingerprint presence отражается явно;
- directional match count вычисляется тем же sign rule, что recommendation classification;
- supporting works total и supporting works with fingerprint имеют однозначный denominator;
- partial/missing coverage создаёт соответствующую limitation metadata;
- Stage A не добавляет deterministic numeric verdict/scoring side effect.

### 13.6 Couple tests

Проверяются:

- directed evidence у обоих одного знака => `agreement`;
- directed evidence у обоих разных знаков => `disagreement`;
- отсутствие directed evidence хотя бы у одного => `insufficient`;
- low confidence сам по себе не превращает directed signal в `insufficient`;
- disagreement projection не меняет existing couple score.

### 13.7 Security tests

Нужны regression/contract tests, доказывающие:

- privileged workflow не исполняет PR-head policy implementation до merge;
- trusted `main`/trusted revision является источником privileged policy;
- trusted policy разбирается как declarative data, без исполнения PR-controlled code;
- proposed policy change валидируется в unprivileged CI;
- новая operation без trusted policy coverage не получает auto-merge path;
- PR, меняющий policy file, не получает auto-merge path;
- PR, меняющий privileged workflow/guard surface, не получает auto-merge path;
- PR, меняющий executable operation semantics, не получает auto-merge path.

### 13.8 Agent contract tests

Не проверяется точная русская/английская фраза. Проверяется нормативная documentation contract:

- active limitation должна учитываться;
- fallback не маскируется под personalized semantic result;
- assessment с partial semantic coverage не маскируется под fully grounded certainty;
- uncertainty не маскируется под certainty.

## 14. Backward compatibility и rollout

### 14.1 Additive first

PR1 предпочитает additive context fields вместо изменения shape существующих consumer-facing полей.

Перед merge выполняется consumer checklist:

- CLI;
- agent instructions;
- web manifest/export;
- broker boundary, если recommendation/assessment context проходит через него;
- relevant documentation/tests.

Поскольку исходный audit/review не инспектировал `web/` и `broker/`, этот checklist является обязательной implementation-time проверкой, а не предположением о совместимости.

Если поле меняет meaning, а не только получает additive metadata, нужен явный version/migration decision.

### 14.2 Никакого semantic backfill как prerequisite

PR1 не требует сначала увеличить число fingerprints.

При текущем низком coverage корректный результат — явно показать большую fallback/partial-coverage долю. Targeted enrichment следует только после measurement/evaluation и не является условием correctness fix.

### 14.3 Baseline не блокирует обычные data changes

Historical baseline фиксирует состояние перед Stage A. Он не обязан равняться текущим counts после каждого легитимного media update.

### 14.4 Expected generated profile changes

После hypothesis isolation generated profiles должны быть rebuild-нуты обычным deterministic путём.

Изменения, вызванные исключением hypothesis evidence из numeric aggregation, считаются ожидаемым semantic diff и перечисляются в PR description. Exact values принимаются только из фактического rebuild и tests; spec не закрепляет приблизительный review-пересчёт как golden output.

## 15. Acceptance criteria

### Measurement

- один canonical audit воспроизводимо объясняет roadmap metrics;
- works/collections и их denominators не смешиваются;
- можно однозначно определить semantic coverage canonical candidate pool;
- runtime recommendation context различает `pool_*` и `returned_*`;
- baseline имеет format version, canonical input digest и внешнюю provenance metadata.

### Correctness

- negative affinity не может улучшить ranking при прочих равных;
- positive affinity не может ухудшить ranking при прочих равных;
- отсутствие fingerprint/basis не является ranking advantage;
- personalized candidates идут перед fallback;
- inferred hypothesis не меняет numeric affinity/confidence/evidence_count;
- ordering deterministic.

### Recommendation observability

Для любого recommendation result можно определить:

- personalized он или fallback;
- strengths и concerns;
- confidence/evidence count relevant matches;
- coverage eligible pool и returned result;
- активные limitations.

### Assessment observability

Для `assess_candidate` можно определить:

- есть ли candidate fingerprint;
- сколько directional personalized matches доступно;
- насколько semantic fingerprint покрывает supporting local works;
- какие coverage limitations активны.

Stage A не обязан выдавать deterministic assessment verdict.

### Couple

- per-term agreement/disagreement/insufficient доступен consumer;
- `insufficient` не зависит от непроверенного confidence threshold;
- existing couple aggregation не меняется.

### Agent UX

- следование contract не позволяет представить fallback или partial assessment coverage как уверенную персональную semantic рекомендацию/оценку.

### Security

- privileged auto-merge не исполняет mutable PR-head policy code;
- operation/path policy имеет один trusted declarative semantic source;
- policy/workflow/executable semantic changes исключены из auto-merge;
- drift и missing operation coverage ловятся CI.

## 16. Что остаётся после Stage A

Stage A сознательно оставляет открытыми:

- optimal affinity/confidence weights;
- pseudocount/source weights;
- rating calibration;
- deterministic `assess_candidate` verdict/scoring core;
- assessment confidence calibration;
- couple aggregation alternatives;
- confidence thresholds;
- semantic enrichment target;
- semantic enrichment provenance/versioning (`vocab_version`, `enriched_at`, `enriched_by`);
- temporary external candidate fingerprinting;
- exploration/MMR;
- predictive rating model.

Следующий architecture cycle должен начать с evaluation/ground-truth design, а не с выбора формулы. Для model selection следует разделять diagnostic benchmark на всей доступной истории и decision benchmark на небольшом explicit/confirmed stratified set, чтобы не оптимизировать новую модель против старых inferred labels.

Semantic provenance/versioning и deterministic assessment core должны быть явно включены в план следующих этапов, даже если они будут реализовываться до или параллельно evaluation harness.

## 17. Recommended implementation sequence

После финального review этой spec:

1. написать отдельный implementation plan через `writing-plans`;
2. реализовать PR0 полностью и зафиксировать baseline до behavior changes;
3. реализовать PR1 как единый correctness + observability change;
4. проверить current consumers, generated profile diff и trust boundary;
5. только после Stage A проектировать evaluation harness / ground-truth benchmark и следующие assessment/semantic-provenance этапы.

Implementation plan должен назвать точные файлы, tests, canonical pool eligibility rules, trusted-policy lookup mechanism и команды проверки. Эта design spec намеренно фиксирует behavioral contracts и trust boundaries, а не преждевременно привязывает каждое решение к конкретной функции.
