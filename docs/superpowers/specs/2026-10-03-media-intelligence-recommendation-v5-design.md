# Media Intelligence & Recommendation v5 — design

Дата: 2026-10-03  
Статус: **written spec awaiting final user review**  
База: `2026-10-01-personal-media-recommendation-v4-design.md`  
Область: semantic film knowledge, taste learning, profile reanalysis, external recommendation discovery

## 1. Цель

Расширить медиатеку из персонального каталога с объяснимым профилем вкуса в личного киноассистента с долговременной памятью, который:

- понимает обычные отзывы пользователя и извлекает из них semantic evidence;
- учится не только на явно названных тегах, но и на оценках, конкретных любимых/нелюбимых произведениях и повторяющихся корреляциях;
- хранит отдельно знания о произведении и знания о вкусе пользователя;
- не превращает жанры и существующий профиль в жёсткие фильтры;
- умеет рекомендовать новые произведения, которых ещё нет в локальной медиатеке;
- использует LLM для смыслового reasoning, а deterministic Python — для source-of-truth, валидации, агрегации evidence и воспроизводимости;
- сохраняет объяснимость: рекомендация должна быть обоснована историей пользователя и текущим запросом, а не непрозрачным score.

Основной принцип:

> LLM принимает решение на основании всей истории, текущего запроса и внешнего знания; профиль — explainable memory/prior, а не фильтр жанров и не самостоятельный recommendation engine.

## 2. Что остаётся неизменным

Существующий безопасный write-path сохраняется:

```text
natural language
→ strict typed JSON command
→ media/op-* branch
→ transient .media/requests/<operation-id>.json
→ PR
→ Media Command
→ deterministic Python service
→ exact-head dispatched Media Check
→ guarded auto-merge
→ main
```

LLM не редактирует canonical/generated YAML напрямую. Generated artifacts остаются полностью пересобираемыми. Никакой новый recommendation/intelligence слой не должен обходить path policy, schemas, validation, rebuild или doctor.

## 3. Разделение ответственности

### 3.1 LLM

LLM отвечает за:

- понимание естественного языка пользователя;
- выделение explicit semantic feedback из отзыва;
- формирование слабых гипотез на основе rating + film knowledge;
- поиск смысловых корреляций по нескольким произведениям;
- глубокий переанализ вкуса по команде пользователя;
- интерпретацию текущего контекста: «что хочется сегодня»;
- формирование стратегии внешнего поиска;
- сравнение внешних кандидатов с историей и профилем;
- объяснение рекомендаций человеческим языком.

LLM не отвечает за:

- окончательное хранение generated profile;
- прямое изменение canonical YAML вне typed commands;
- автоматическое создание vocabulary terms;
- превращение одной оценки в уверенный вывод о причине вкуса;
- проверку точных/свежих фактов, когда доступен внешний источник.

### 3.2 Deterministic Python

Python отвечает за:

- schemas и typed commands;
- transactions и rollback;
- validation/path policy;
- deterministic aggregation evidence;
- rebuild index/profiles/context;
- защиту от self-reinforcing inference;
- формальные thresholds/confidence rules;
- сохранение provenance;
- read-only context assembly для LLM.

### 3.3 External providers / web

TMDB и web-источники отвечают за проверяемые внешние факты и discovery-кандидатов: identity, runtime, release date, cast/crew, synopsis, availability of current releases и другие factual metadata.

Знания LLM могут использоваться для генерации направлений и смыслового сравнения, но свежие/точные факты по возможности проверяются извне.

## 4. Слои знания

Система должна различать четыре типа данных.

### 4.1 Film knowledge

Это знание о произведении, не о пользователе.

У work уже существует `metadata.semantic.traits`. v5 расширяет идею до semantic fingerprint: компактного описания значимых свойств произведения с provenance и confidence.

Пример концептуально:

```yaml
metadata:
  semantic:
    traits:
      - term: story.intrigue
        source: llm_inferred
        confidence: high
      - term: characters.charisma
        source: llm_inferred
        confidence: medium
      - term: pacing.slow
        source: external_source
        confidence: medium
```

Fingerprint должен описывать произведение, а не утверждать, нравится ли этот trait пользователю. Viewer-specific reaction terms вроде `reaction.pacing_dragging` относятся к user feedback и не должны использоваться как film-level property.

Дополнительно допускается derived/external consensus-контекст: common praise / common criticism. Он используется как candidate explanation для attribution, но сам по себе не является user evidence.

### 4.2 Explicit user evidence

То, что пользователь сказал явно.

Пример:

> «Картинка отличная, но фильм затянут»

даёт сильные feedback signals с `source: explicit`, а не гипотезы.

Explicit evidence имеет наивысший приоритет среди сигналов вкуса.

### 4.3 Inferred user evidence

Это гипотезы, полученные из повторяющихся корреляций между:

- ratings;
- reactions;
- explicit feedback;
- film fingerprints;
- relations between works;
- recommendation/choice interactions.

Inferred evidence всегда хранит provenance, confidence и supporting evidence. Оно не должно маскироваться под explicit statement.

### 4.4 Generated taste profile

`generated/profiles/<target>.yaml` остаётся derived summary. Он строится только из canonical source-of-truth и может быть полностью пересоздан.

Generated profile не является местом, куда LLM пишет выводы напрямую.

## 5. Semantic fingerprint фильма

### 5.1 Назначение

Fingerprint нужен, чтобы система могла учиться даже по короткому отзыву или одной оценке и чтобы LLM могла находить смысловые связи между произведениями разных жанров.

### 5.2 Источники

Fingerprint может содержать признаки из:

- controlled vocabulary;
- provider metadata;
- LLM semantic analysis;
- проверенного external consensus.

Каждый trait обязан иметь `source` и `confidence`.

### 5.3 Ограничения

- fingerprint не должен зависеть от конкретного viewer;
- rating пользователя не должен изменять fingerprint фильма;
- пользовательское мнение не превращается в «объективное свойство» фильма;
- LLM не создаёт новые vocabulary terms автоматически;
- незнакомый полезный концепт может быть предложен для отдельного vocabulary review.

## 6. Обработка нового отзыва

При обычном сообщении:

> «8/10. Очень зашла интрига и персонажи, но финал слабее»

LLM должна сформировать одну typed feedback operation, которая сохраняет:

- viewing state;
- rating;
- reaction, если он следует из сообщения;
- feedback summary;
- explicit semantic signals по существующему vocabulary.

После deterministic apply Python пересобирает index и profiles.

Если пользователь сообщает только:

> «8/10»

система не придумывает explicit причины. Rating становится слабым evidence для последующего correlation analysis относительно fingerprint фильма.

## 7. Rating как слабый обучающий сигнал

Текущая v4 модель хранит rating, но affinity в основном строится из feedback signals. v5 должна учитывать rating как слабый общий сигнал.

Правила:

1. Rating никогда не означает, что пользователю нравятся все traits фильма.
2. Чем ближе score к нейтральной зоне, тем меньше его вес.
3. Очень высокая/низкая оценка даёт слабое положительное/отрицательное evidence только в сочетании с film fingerprint.
4. Explicit feedback всегда сильнее rating-derived evidence.
5. Один rating не должен создавать `high confidence` preference.
6. Сигнал должен усиливаться только при повторении на нескольких независимых works.

Точные математические веса являются implementation detail и должны быть покрыты тестами; design фиксирует только относительный приоритет:

```text
explicit feedback
> repeated multi-work correlation
> single-work rating + fingerprint
> rating + external common praise/criticism
```

## 8. Canonical inferred preferences

Нужен отдельный canonical слой для устойчивых LLM-гипотез, не смешанный с explicit preferences.

Предлагаемая структура:

```text
media/preferences/
├── explicit/
│   ├── primary.yaml
│   ├── partner.yaml
│   └── couple.yaml
└── inferred/
    ├── primary.yaml
    ├── partner.yaml
    └── couple.yaml
```

Каждая inferred hypothesis концептуально содержит:

```yaml
id: intrigue-plus-competent-characters
statement: >-
  Высокие оценки часто получают произведения с интригой,
  активным раскрытием информации и компетентными персонажами.
confidence: medium
source: llm_inferred
terms:
  - story.intrigue
  - story.problem_solving
evidence:
  - entity_id: example-a
    kind: rating_correlation
  - entity_id: example-b
    kind: explicit_feedback
updated_at: 2026-10-03
```

Схема должна запрещать opaque model-only assertions без evidence.

## 9. Защита от self-reinforcement

Критически важно не позволить модели усиливать собственные старые догадки как независимые факты.

Правила:

- inferred preference не считается новым independent evidence для другой inferred preference;
- confidence пересчитывается из raw/explicit evidence и film knowledge;
- повторный reanalysis не повышает confidence только потому, что предыдущая версия уже содержала тот же вывод;
- если supporting evidence исчезло/изменилось, hypothesis может ослабнуть или исчезнуть;
- derived profile должен уметь показывать, на каких canonical evidence основан affinity.

## 10. Deep profile reanalysis

Пользователь может явно запросить:

> «Переосмысли мой вкус»

или эквивалент.

Это запускает отдельную typed operation, условно `reanalyze_preferences`, которая:

1. получает компактный snapshot всей релевантной истории;
2. анализирует high/low ratings, explicit feedback, representative works, film fingerprints и current explicit preferences;
3. находит повторяющиеся cross-work correlations;
4. формирует candidate inferred preferences;
5. сохраняет их в `preferences/inferred/<target>.yaml` через deterministic schema/path validation;
6. пересобирает generated profile.

Операция не имеет права менять work metadata, vocabulary или schemas как побочный эффект.

Deep reanalysis может также запускаться автоматически после определённого количества новых meaningful signals, но автоматический режим является отдельным policy decision; базовый v5 обязан поддерживать явный запуск пользователем.

## 11. Compact LLM taste context

LLM не должна читать сотни полных work YAML при каждой рекомендации.

Нужен derived context artifact / read command, который включает:

- target (`primary`, `partner`, `couple`);
- explicit preferences/rules/constraints;
- stable inferred preferences;
- generated affinities;
- representative highly-rated works;
- representative disliked/low-rated works;
- recent meaningful feedback;
- watched/not-interested IDs для exclusion;
- strongest cross-work correlations;
- confidence/evidence pointers;
- для couple — зоны совпадения и расхождения вкусов.

Полные canonical work документы загружаются только для финальных/нужных кандидатов.

## 12. Два режима рекомендаций

### 12.1 Internal recommendation

Явный запрос вида:

> «Что посмотреть из моей медиатеки?»

использует существующий/internal context path и выбирает только из локального index.

### 12.2 External discovery — default для общего запроса

Запрос вида:

> «Посоветуй нам фильм на вечер»

по умолчанию не ограничивается локальной медиатекой.

Целевой flow:

```text
user request
→ resolve target + current intent
→ load compact taste/history context
→ infer search strategy
→ generate/find external candidates
→ verify candidate facts via provider/web
→ exclude watched / not_interested / hard constraints
→ compare candidates with concrete liked/disliked works + profile + current intent
→ diversify / exploration
→ return explainable shortlist
```

Локальная медиатека здесь выступает долговременной памятью, а не каталогом разрешённых рекомендаций.

## 13. Жанры и профиль — мягкие priors

Положительная affinity к sci-fi не означает запрет horror/drama/comedy.

Жёсткие filters возникают только из явных ограничений текущего запроса или canonical constraints, например:

- «без ужасов»;
- «до 100 минут»;
- «только то, что мы оба не смотрели».

Остальные preference signals дают boosts/concerns, а не eligibility gate.

Это позволяет модели обнаруживать более глубокие закономерности: пользователь может любить не sci-fi как жанр, а интригу, компетентных персонажей и активное раскрытие информации — и поэтому подходящий horror может быть отличной рекомендацией.

## 14. Использование конкретных произведений как anchors

Recommendation reasoning не должно опираться только на агрегированный профиль.

Compact context обязан давать LLM representative anchors:

- несколько очень понравившихся works;
- несколько disliked/low-rated works;
- works, по которым есть богатый explicit feedback;
- recent works;
- при необходимости partner/couple anchors.

LLM может использовать собственное понимание этих произведений, чтобы находить смысловые связи, которых пока нет в controlled vocabulary.

Такие связи разрешены для reasoning и candidate explanation, но не становятся canonical vocabulary автоматически.

## 15. Exploration и защита от пузыря

External recommendation shortlist должен поддерживать diversity/exploration.

Рекомендуемый UX для 3–4 вариантов:

- 1–2 уверенных совпадения;
- 1 более широкий вариант;
- 1 осознанно неожиданный вариант, если есть убедительная связь с более глубокими предпочтениями.

Не требуется фиксированный процент exploration; важно не превращать исторические preferences в замкнутый жанровый пузырь.

LLM должна уметь объяснить unexpected pick, например:

> «Ты редко смотришь хорроры, но здесь сильны интрига и problem-solving — именно они повторяются среди твоих высоких оценок».

## 16. Couple target

`couple` не должен быть простым средним двух профилей.

Context для совместных рекомендаций должен показывать:

- common strengths;
- common concerns;
- preferences, которые важны только primary;
- preferences, которые важны только partner;
- конфликты;
- уже совместно просмотренное;
- direct group feedback, если он существует.

LLM выбирает либо компромисс с хорошей вероятностью для обоих, либо явно сообщает, что вариант больше ориентирован на одного из зрителей.

## 17. Recommendation interactions

Существующая v4 модель уже предусматривает `data/interactions/` как append-only history. v5 должна начать использовать её для recommendation feedback.

Полезные события:

- recommendation_shown;
- recommendation_selected;
- recommendation_rejected;
- recommendation_deferred.

Ограничение:

> «не сегодня» / deferred не превращается в persistent `not_interested`.

Interaction history может быть слабым evidence, но не должна весить больше явного post-watch feedback.

## 18. Новый внешний фильм и feedback loop

External candidate не обязан добавляться в локальную медиатеку в момент рекомендации.

После просмотра пользователь говорит обычным языком:

> «Посмотрели X. Мне 8.5, партнёру 7. Очень понравились диалоги и интрига».

Если work отсутствует, существующая `record_viewing_feedback(create_if_missing=true)` модель создаёт его через provider и применяет feedback атомарно.

После merge:

- work становится частью истории;
- semantic feedback участвует в profile rebuild;
- rating участвует как слабое evidence;
- fingerprint позволяет использовать этот фильм в последующем correlation analysis.

## 19. Vocabulary evolution

LLM может обнаружить устойчивую повторяющуюся закономерность, которой нет в vocabulary, например:

> «нравятся истории про профессионально компетентных героев».

Она может сформулировать candidate concept для отдельного review, но normal feedback/reanalysis/recommendation operation не имеет права автоматически изменять `vocabulary.yaml`.

Vocabulary change остаётся отдельным архитектурным PR с проверкой aliases/overlap/schema impact.

## 20. Требуемые новые read/write capabilities

Design предполагает появление следующих logical capabilities; точные command names фиксируются implementation plan:

- read: compact taste/history context;
- read: internal recommendation context;
- read: external candidate comparison context;
- write: enrich/update semantic fingerprint с provenance;
- write: deep preference reanalysis;
- write: recommendation interaction event.

Существующие `record_viewing_feedback`, `set_interest`, `add_work`, `refresh_metadata` сохраняются.

## 21. Проверяемость и тестирование

Минимальные категории тестов для реализации:

### Schemas

- inferred preferences требуют evidence/provenance/confidence;
- semantic fingerprint не содержит viewer preference;
- recommendation interactions валидируются и append-only;
- normal data operation не может менять vocabulary/schema.

### Profile aggregation

- explicit signal сильнее rating-derived;
- один rating не создаёт high-confidence affinity;
- repeated independent evidence повышает confidence;
- inferred preference не усиливает сама себя;
- removal/change raw evidence корректно меняет profile.

### Feedback extraction contract

- explicit user phrases сохраняются как explicit signals;
- rating-only feedback не фабрикует explicit причины;
- unknown semantic concept не добавляется в vocabulary автоматически.

### Recommendation context

- watched/not_interested корректно исключаются;
- genre affinity не становится hard filter;
- current hard constraints применяются как hard filters;
- anchors и evidence доступны LLM;
- couple context сохраняет disagreement, а не усредняет его молча.

### External discovery

- candidates вне локального index разрешены;
- exact facts проверяются provider/web path;
- локально просмотренное исключается;
- результат содержит human-readable rationale;
- exploration candidate не обязан совпадать с dominant genre.

## 22. Этапы реализации

Реализацию следует разбить на независимые вертикальные этапы:

### Phase A — Semantic Film Knowledge

- расширить/формализовать semantic fingerprint;
- provenance/confidence;
- derived common-praise/common-criticism context при необходимости;
- backfill strategy для существующих works.

### Phase B — Taste Learning

- rating-derived weak evidence;
- canonical inferred preferences;
- deterministic profile aggregation;
- anti-self-reinforcement rules.

### Phase C — Deep Profile Reanalysis

- compact whole-history context;
- typed reanalysis operation;
- LLM-generated hypotheses → schema validation → canonical inferred prefs;
- explicit user command for rebuild/rethink.

### Phase D — External Recommendation Discovery

- default external recommendation mode;
- web/TMDB verification;
- candidate comparison against history/profile/current intent;
- exploration/diversity;
- explainable output.

### Phase E — Recommendation Learning Loop

- append-only interaction events;
- selection/rejection/defer signals;
- careful weighting in future context;
- no persistence of ephemeral mood as stable preference.

## 23. Non-goals для первой реализации v5

- обучать собственную ML-модель recommender;
- строить единый opaque numeric match score;
- автоматически менять vocabulary;
- скачивать/хранить весь интернет-контент;
- автоматически добавлять каждый рекомендованный фильм в canonical library;
- считать public ratings главным сигналом качества для пользователя;
- автоматически превращать один high rating в набор уверенных preference claims.

## 24. Критерии успеха

v5 считается достигшей цели, когда:

1. Обычный отзыв обновляет explicit semantic evidence и generated profile без прямого редактирования generated data моделью.
2. Голая оценка участвует в обучении как слабый, а не выдуманный explicit signal.
3. Система умеет объяснимо хранить устойчивые inferred preferences с evidence.
4. Пользователь может явно попросить переосмыслить профиль по всей истории.
5. Общий запрос «посоветуй фильм» может вернуть произведение, которого нет в локальной медиатеке.
6. Recommendation reasoning использует конкретные liked/disliked anchors, а не только агрегированный profile.
7. Любимый жанр не блокирует рекомендации из других жанров.
8. Couple recommendation учитывает реальные расхождения предпочтений.
9. Inference не усиливает само себя без нового raw evidence.
10. Все canonical изменения проходят тот же deterministic typed-command/validation pipeline, что и текущая медиатека.

## 25. Итоговая модель

```text
                     ┌─────────────────────┐
                     │   external world    │
                     │ TMDB / web / facts  │
                     └─────────┬───────────┘
                               │
                               ▼
┌─────────────┐      ┌─────────────────────┐
│ film works  │─────▶│ semantic fingerprints│
└──────┬──────┘      └─────────┬───────────┘
       │                        │
       │                ┌───────▼─────────┐
       │                │ ratings/feedback│
       │                │ explicit evidence│
       │                └───────┬─────────┘
       │                        │
       │                ┌───────▼─────────┐
       │                │ correlations +  │
       │                │ inferred prefs  │
       │                └───────┬─────────┘
       │                        │
       └────────────────────────▼
                     ┌─────────────────────┐
                     │ generated profiles  │
                     │ + compact context   │
                     └─────────┬───────────┘
                               │
                current request│
                         ┌─────▼─────┐
                         │    LLM    │
                         │ reasoning │
                         └─────┬─────┘
                               │
                               ▼
                     external/internal
                      recommendations
                               │
                               ▼
                           viewing
                               │
                               ▼
                           feedback
                               └──────────→ learning loop
```

Python хранит и проверяет память. LLM интерпретирует, связывает и рекомендует. Внешние источники расширяют пространство кандидатов. Ни один слой не должен подменять остальные.
