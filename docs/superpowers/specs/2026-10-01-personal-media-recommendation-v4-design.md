# Personal Media Recommendation Data Model v4 — design

Дата: 2026-10-01  
Статус: **design approved in chat; written spec awaiting final user review**  
Заменяет: `2026-10-01-movie-recommendation-v3-design.md`

## 1. Цель

Создать долговечную персональную медиатеку для фильмов, сериалов, мини-сериалов и анимации, которая:

- сохраняет пользовательский сигнал точнее, чем обычный список оценок;
- поддерживает нескольких зрителей и совместный просмотр;
- безопасно обновляется разными LLM без расползания схемы и словаря;
- остаётся удобной для Git и ручного чтения;
- масштабируется до сотен и тысяч произведений;
- позже может служить каноническим источником для сайта, API, SQLite, полнотекстового и векторного поиска.

Главная задача системы — **объяснимо рекомендовать произведения под конкретного зрителя или группу и улучшать рекомендации по мере накопления реальных отзывов**.

## 2. Основные архитектурные принципы

1. Git/YAML — канонический источник истины.
2. SQLite, индексы, derived profiles и embeddings — только пересобираемые представления.
3. Один work хранится в одном YAML-файле.
4. Неизвестные данные остаются неизвестными; LLM не заполняет поля догадками ради полноты.
5. Пользовательский сигнал имеет больший приоритет, чем semantic metadata, внешние метаданные и публичные рейтинги.
6. `unwatched` не является отрицательным сигналом.
7. Reaction, числовая оценка, отзыв, пересмотры, интерес и контекст просмотра — независимые сигналы.
8. Объективный/описательный trait произведения и субъективная viewer reaction — разные понятия.
9. Все семантические понятия используют controlled vocabulary.
10. Обычное добавление произведения не имеет права менять schema.
11. Новые vocabulary terms не создаются, пока не проверено отсутствие подходящего canonical term.
12. Immutable ID не переименовываются; merge/delete выполняются через redirects/tombstones.
13. Сезонная детализация сериалов необязательна.
14. Общая оценка сериала не вычисляется из оценок сезонов и наоборот.
15. Один relation/membership хранится в одном каноническом месте; обратные связи — derived.
16. Запись от LLM, сайта или CLI проходит через один и тот же validation/write protocol.
17. Одноразовое настроение и ограничения текущего запроса по умолчанию не становятся постоянными preferences.
18. Raw signals хранятся рядом с work; агрегированные профили вкуса являются derived data.

## 3. Физическая структура репозитория

```text
media/
├── AGENTS.md
├── README.md
├── vocabulary.yaml
│
├── config/
│   ├── viewers.yaml
│   └── groups.yaml
│
├── preferences/
│   └── explicit/
│       ├── primary.yaml
│       ├── partner.yaml
│       └── couple.yaml          # создаётся только при явных group preferences
│
├── schemas/
│   ├── work.schema.json
│   ├── collection.schema.json
│   ├── list.schema.json
│   ├── interaction.schema.json
│   ├── tombstone.schema.json
│   ├── viewers.schema.json
│   ├── groups.schema.json
│   ├── vocabulary.schema.json
│   └── explicit-preferences.schema.json
│
├── data/
│   ├── works/
│   │   ├── interstellar-2014.yaml
│   │   └── sherlock-2010.yaml
│   ├── collections/
│   │   └── oceans.yaml
│   ├── lists/
│   ├── interactions/
│   │   └── 2026-10.jsonl
│   └── tombstones/
│
├── generated/
│   ├── index.jsonl
│   ├── database.sqlite
│   └── profiles/
│       ├── primary.yaml
│       ├── partner.yaml
│       └── couple.yaml
│
└── tools/
    ├── validate.py
    ├── build_index.py
    ├── build_db.py
    └── build_profiles.py
```

### Source of truth

Каноническими являются:

- `media/config/*`;
- `media/vocabulary.yaml`;
- `media/preferences/explicit/*`;
- `media/data/works/*`;
- `media/data/collections/*`;
- `media/data/lists/*`;
- `media/data/interactions/*`;
- `media/data/tombstones/*`.

`media/generated/*` никогда не редактируется как источник данных и может быть полностью удалён и пересобран.

## 4. Entity model

### 4.1 Work

`work` — отдельное произведение: фильм, сериал или мини-сериал.

```yaml
schema_version: 4
id: interstellar-2014
entity_type: work

identity:
  format: movie
  medium: live_action
  title_original: Interstellar
  title_ru: Интерстеллар
  alternate_titles: []
  year: 2014
  release_date: 2014-11-07
  external_ids:
    tmdb: 157336
    imdb: tt0816692
```

`identity.format`:

- `movie`
- `series`
- `miniseries`

`identity.medium`:

- `live_action`
- `animation`
- `hybrid`

Мультфильм — `movie + animation`; анимационный сериал — `series + animation`.

### 4.2 Collection

Франшиза/серия произведений — отдельная сущность, а не `format`.

```yaml
schema_version: 4
id: oceans
entity_type: collection
name_ru: "Ocean’s"
name_original: "Ocean's"
member_ids:
  - oceans-eleven-2001
  - oceans-twelve-2004
  - oceans-thirteen-2007
```

Membership хранится только в collection. Work не дублирует `collection_ids`.

Collection поддерживает тот же `viewer_signals` / `group_signals`, что и work, если есть реальный отзыв о франшизе целиком.

### 4.3 List

Произвольная пользовательская подборка:

```yaml
schema_version: 4
id: weekend-couple
entity_type: list
target: couple
title: "На выходные"
description: null
member_ids: []
```

`collection` описывает логическую/каноническую серию произведений; `list` — пользовательскую организацию.

### 4.4 Interaction

Append-only событие истории рекомендаций/выбора.

### 4.5 Viewer / group

Viewer и group — стабильные анонимные IDs. Персональные данные не хранятся.

### 4.6 Tombstone

Удалённый/объединённый immutable ID остаётся разрешимым:

```yaml
schema_version: 4
id: live-die-repeat-2014
entity_type: tombstone
status: merged
redirect_to: edge-of-tomorrow-2014
```

Redirect chains не должны образовывать циклы.

## 5. Multi-viewer model

Начальная конфигурация:

```yaml
# config/viewers.yaml
schema_version: 4
viewers:
  primary: {}
  partner: {}
```

```yaml
# config/groups.yaml
schema_version: 4
groups:
  couple:
    members:
      - primary
      - partner
```

Никаких имён, дат рождения, возраста и других персональных данных.

Новые viewer/group создаются только при реальной необходимости; схема должна позволять добавить будущих членов семьи без миграции формата.

## 6. Viewer signals

Raw signal конкретного зрителя хранится внутри work. Viewer-блок **не создаётся без реальных данных**.

```yaml
viewer_signals:
  primary:
    viewing:
      status: watched
      times_watched: 2
      times_watched_approximate: false
      first_watched_at: null
      last_watched_at: 2026-10-01
      progress: null

    reaction:
      value: liked
      source: explicit
      confidence: high

    rating:
      score: 8.5
      source: explicit
      confidence: exact

    feedback:
      summary: "..."
      signals: []

    rewatch:
      intent: high

    relations: []
    history: []

  partner:
    reaction:
      value: liked
      source: explicit
      confidence: high
```

### 6.1 Viewing status

Enum:

- `unwatched`
- `watched`
- `partial`
- `dropped`
- `forgotten`

`dropped` не считается автоматически отрицательной реакцией.

`progress` необязателен и в основном используется для сериалов:

```yaml
progress:
  season: 2
  episode: 5
```

### 6.2 Reaction

Минимальный персональный сигнал:

- `liked`
- `disliked`
- `neutral`
- `mixed`
- `unknown`

Отсутствие viewer-блока означает отсутствие данных. `unknown` используется только если неизвестность сама была явно зафиксирована и полезна.

Reaction и rating независимы. Rating не генерирует reaction автоматически и наоборот.

Если пользователь передаёт мнение partner (например, «жене понравилось»), это считается полноценным сигналом partner. Confidence зависит от уверенности формулировки, а не от того, кто произнёс фразу в чат.

### 6.3 Rating

```yaml
rating:
  score: 8.5
  source: explicit_approx
  confidence: high
```

`score`: `1.0..10.0`, шаг `0.5`, либо `null`.

`source`:

- `explicit`
- `explicit_approx`
- `inferred`
- `none`

`confidence`:

- `exact`
- `high`
- `medium`
- `low`
- `none`

### 6.4 Feedback signals

```yaml
feedback:
  summary: "Интересный, но местами слишком кринжовый."
  signals:
    - term: reaction.cringe
      sentiment: negative
      strength: 3
      source: explicit
      confidence: high
```

`sentiment`: `positive | negative | mixed | neutral`.

`strength`: `1..3`.

`source`: `explicit | inferred`.

LLM должна отличать свою интерпретацию от прямого пользовательского сигнала.

### 6.5 Rewatch

```yaml
rewatch:
  intent: high
```

Количество фактических просмотров хранится в `viewing.times_watched`, поэтому двусмысленного `rewatch.count` нет.

### 6.6 Significant history

Полного event-sourcing мнений нет. Необязательный `history` используется только для значимых изменений, например сильного пересмотра оценки после повторного просмотра.

## 7. Group signals

Group не является отдельным «человеком». Это контекст совместного просмотра и собственный необязательный сигнал.

```yaml
group_signals:
  couple:
    reaction:
      value: liked
      source: explicit
      confidence: high

    rating:
      score: 9.0
      source: explicit
      confidence: exact

    feedback:
      summary: "Как совместный просмотр особенно хорошо."
      signals: []

    suitability:
      strength: 3

    relations: []
    history: []
```

Group-блок создаётся только при наличии реального group-specific сигнала.

Ситуация `primary: 7.5`, `partner: liked`, `couple: 9.0` валидна.

## 8. Сезоны сериалов

`seasons` — необязательная детализация. Если сериал оценён только целиком, этого достаточно.

```yaml
seasons:
  - number: 1
    title: null
    release_year: 2021
    episode_count: 9
    metadata:
      semantic:
        traits: []
    viewer_signals:
      primary:
        rating:
          score: 9.5
          source: explicit
          confidence: exact
    group_signals: {}
```

Сезон использует те же viewer/group signal semantics, что и work. Никакие пустые season records не создаются «для полноты».

Общая оценка сериала и сезонные оценки независимы.

## 9. Metadata и enrichment

Metadata разделяются на внешний слой, ручные overrides и semantic слой.

```yaml
metadata:
  external: {}
  overrides: {}
  semantic: {}
```

### 9.1 External factual metadata

TMDB — основной metadata provider v4, но schema остаётся provider-neutral.

Полезные поля:

- genres;
- runtime;
- original language;
- countries;
- production status;
- spoiler-safe short synopsis;
- directors;
- writers;
- key cast;
- certifications;
- content warnings;
- external metrics;
- poster/backdrop references.

При добавлении нового произведения write-layer по возможности автоматически получает factual metadata из внешнего источника. Если источник недоступен, сохраняются только достоверно известные данные.

### 9.2 People references

Отдельные person YAML в v4 не создаются.

```yaml
directors:
  - name: Christopher Nolan
    external_ids:
      tmdb: 525
      imdb: nm0634240
```

Это позволяет строить derived каталог людей без тысяч канонических person-файлов.

### 9.3 Assets

Бинарные постеры/backdrops в Git не хранятся.

```yaml
assets:
  poster:
    provider: tmdb
    path: /...
```

Будущий сайт может кэшировать assets вне canonical Git data.

### 9.4 External metrics

Публичные рейтинги — слабый дополнительный сигнал:

```yaml
external_metrics:
  imdb:
    score: 8.7
    votes: 2200000
    observed_at: 2026-10-01
```

Они не переопределяют персональный вкус.

### 9.5 Persistent manual overrides

Ручные правки никогда не затираются автоматическим refresh.

Effective value:

```text
override -> external -> null
```

Override допускается только для полей, разрешённых schema.

### 9.6 Semantic traits

```yaml
semantic:
  traits:
    - term: story.problem_solving
      source: llm_inferred
      confidence: high
```

Trait обязательно хранит provenance.

`source`:

- `external_source`
- `llm_inferred`
- `user_explicit`

LLM-inferred trait не превращается со временем в «объективный факт».

## 10. Controlled vocabulary

Все semantic term IDs namespaced.

Примеры:

- `genre.science_fiction`
- `genre.drama`
- `narrative.time_loop`
- `story.problem_solving`
- `story.intrigue`
- `pacing.fast`
- `pacing.slow`
- `humor.absurd`
- `atmosphere.immersive`
- `characters.charisma`
- `reaction.cringe`
- `reaction.pacing_dragging`
- `reaction.excessive_darkness`
- `content.violence`

Ключевое разделение:

- `pacing.slow` — trait произведения;
- `reaction.pacing_dragging` — реакция зрителя;
- `humor.absurd` — стиль юмора;
- `reaction.cringe` — пользовательская реакция.

Новый term создаётся только если:

1. подходящего canonical term нет;
2. это не синоним;
3. различие полезно будущим рекомендациям;
4. term применим более чем к одному произведению;
5. определены namespace/kind/definition/aliases.

Изменение/слияние canonical term IDs — отдельная миграция vocabulary.

## 11. Relations

### 11.1 Viewer/group relations

Пользовательское сходство — сильный персональный сигнал.

```yaml
relations:
  - target_id: edge-of-tomorrow-2014
    type: similar_to
    strength: 3
    dimensions:
      - story.problem_solving
      - narrative.time_loop
    note: "По ощущениям напоминает «Грань будущего»."
    source: explicit
    confidence: exact
```

Типы v4:

- `similar_to`
- `reminds_of`
- `preferred_over`

Relation хранится в viewer/group signal соответствующего субъекта.

`preferred_over`: если relation записан в work A и указывает `target_id: B`, субъект предпочитает A произведению B. Обратная ситуация записывается в B. Поле `direction` не используется.

### 11.2 Canonical relations

Фактические связи произведений хранятся отдельно от viewer relations:

- `sequel`
- `prequel`
- `spinoff`
- `remake`
- `reboot`
- `adaptation`

Canonical relation и subjective similarity никогда не смешиваются.

## 12. Interest и target state

Interest принадлежит target (`primary`, `partner`, `couple`), а не work глобально.

```yaml
target_states:
  primary:
    interest:
      state: shortlist
      priority: 4
  couple:
    interest:
      state: candidate
      priority: 3
```

`interest.state`:

- `unknown`
- `candidate`
- `shortlist`
- `not_interested`

`not_interested` — устойчивое состояние. «Не сегодня» остаётся ephemeral и не превращается в постоянный dislike/interest state.

## 13. Explicit preferences и constraints

Постоянные пользовательские предпочтения, высказанные вне контекста одного произведения, хранятся отдельно по target.

Примеры:

- «обычно люблю фильмы с загадкой»;
- «не советуй мне тяжёлый cringe-humor»;
- «для совместного просмотра предпочитаем не слишком мрачное».

Одноразовые условия вроде «сегодня не хочется фантастики» не сохраняются.

Explicit preference всегда отличается от derived preference.

## 14. Derived profiles

`generated/profiles/{target}.yaml` строится из:

- explicit preferences;
- viewer/group signals;
- ratings;
- reactions;
- structured feedback;
- rewatch/viewing evidence;
- relations;
- значимых interaction outcomes.

`couple` не является простым средним `primary` и `partner`. Он учитывает:

1. primary profile;
2. partner profile;
3. explicit group preferences;
4. group_signals.couple;
5. релевантную историю совместного выбора.

Каждый derived вывод должен иметь confidence/evidence и может быть полностью пересобран.

## 15. Interaction log

История рекомендаций и выбора хранится append-only по месяцам:

```text
media/data/interactions/2026-10.jsonl
```

Пример:

```json
{"id":"evt-20261001-001","at":"2026-10-01T20:15:00+02:00","work_id":"arrival-2016","target":"couple","type":"recommended"}
{"id":"evt-20261001-002","at":"2026-10-01T20:17:00+02:00","work_id":"arrival-2016","target":"couple","type":"skipped","reason":"not_today"}
```

Минимальные event types:

- `recommended`
- `selected`
- `skipped`
- `dismissed`
- `added_to_list`
- `removed_from_list`

Это **не event-sourcing**. Текущее состояние rating/viewing/feedback хранится в work.

Счётчики `recommended_count`, `last_recommended_at`, `skipped_count` и аналогичные значения являются derived и не дублируются как source of truth.

Внутренние кандидаты, которые LLM рассматривала, но не показала пользователю, в log не попадают.

## 16. Recommendation runtime

LLM не должна загружать всю библиотеку для каждого запроса.

Pipeline:

```text
ephemeral request
+ target derived profile
+ index/SQLite retrieval
        ↓
30–50 кандидатов
        ↓
фильтры просмотра / interest / constraints
        ↓
10–20 релевантных кандидатов
        ↓
полные YAML только финалистов
        ↓
рекомендация
```

### `generated/index.jsonl`

Компактный retrieval index с идентичностью, основными genres/traits, краткими target signals и derived memberships.

### `generated/database.sqlite`

Предназначена для будущего сайта, фильтрации и сложного поиска. Она полностью пересобирается из canonical data и никогда не редактируется напрямую.

### Embeddings

Не являются обязательной частью реализации v4. Их можно добавить позже как derived слой semantic search без изменения canonical model.

## 17. Будущий сайт

Сайт рассматривается как будущий полноценный read/write client, а не как источник истины.

```text
Web UI / LLM / CLI
        ↓
единый write-layer
        ↓
validation + dedup + enrichment + vocabulary rules
        ↓
canonical YAML
        ↓
Git commit
        ↓
rebuild generated runtime
```

Сайт читает в основном SQLite/index/generated profiles/image cache, но изменения записывает только через общий write-layer.

Сам веб-интерфейс **не входит в реализацию этой миграции v4**.

## 18. Write protocol

Перед любой записью агент/клиент обязан:

1. определить target;
2. прочитать применимые schema и vocabulary;
3. найти существующий work по TMDB ID, IMDb ID, immutable ID и title/year;
4. разрешить redirects/tombstones;
5. при создании work выполнить metadata enrichment, если источник доступен;
6. не создавать неизвестные поля;
7. не создавать vocabulary synonym вместо существующего term;
8. не сохранять ephemeral context как постоянный preference;
9. не создавать viewer/group block без реального evidence;
10. не понижать explicit signal до inferred;
11. подготовить весь logical change-set;
12. провалидировать proposed canonical state;
13. выполнить atomic write;
14. создать один Git commit на одну логическую операцию;
15. пересобрать affected generated data.

Если validation падает, canonical state не должен оставаться частично изменённым.

## 19. Deduplication

Перед созданием work проверяются:

1. TMDB ID;
2. IMDb ID;
3. internal immutable ID;
4. original/alternate title + year;
5. fuzzy candidate search.

При высокой неоднозначности identity не угадывается. Нужно либо оставить запись неполной без ложного external ID, либо запросить разрешение неоднозначности в подходящем interactive workflow.

## 20. Data precedence

От высшего к низшему:

1. новое явное утверждение пользователя;
2. persistent manual override;
3. существующий explicit viewer/group signal;
4. inferred viewer/group signal;
5. explicit persistent preference/constraint;
6. derived profile;
7. semantic metadata;
8. factual external metadata;
9. public rating/popularity.

Нижний уровень не перезаписывает верхний молча.

## 21. Validation

`validate.py` проверяет как минимум:

- соответствие всех YAML/JSONL schema;
- `additionalProperties: false` там, где структура должна быть закрытой;
- уникальность active internal IDs;
- уникальность ненулевых external IDs;
- корректность redirects и отсутствие redirect cycles;
- существование work/collection/list/target references;
- корректность group members;
- существование всех vocabulary terms;
- запрет aliases вместо canonical IDs;
- уникальность season numbers;
- seasons только у `series`/`miniseries`;
- rating `1..10` с шагом `0.5`;
- согласованность rating value/source/confidence;
- отсутствие self-relations там, где они бессмысленны;
- корректность `preferred_over`;
- валидность canonical relations;
- валидность interaction IDs/timestamps/types;
- существование list members;
- допустимость metadata overrides;
- отсутствие canonical ссылок на generated data как source of truth.

После успешной проверки build pipeline должен уметь полностью пересобрать index, SQLite и derived profiles.

## 22. AGENTS.md contract

`media/AGENTS.md` — короткий обязательный operational contract для любой LLM/agent.

Минимальные правила:

- Read schemas and vocabulary before writing.
- Never invent schema fields.
- Never create canonical vocabulary synonyms without checking existing terms.
- Search before creating a work.
- Unknown is better than guessed.
- Do not persist ephemeral recommendation context.
- Do not create viewer/group signals without evidence.
- Preserve explicit vs inferred provenance.
- Never edit generated files as source data.
- Normal data entry must not modify schemas.
- Run full validation before commit.

## 23. Scope реализации v4

В текущую реализацию входят:

1. каноническая directory structure;
2. config для `primary`, `partner`, `couple`;
3. schemas;
4. initial controlled vocabulary;
5. миграция текущей v2 movie-базы без потери пользовательского сигнала;
6. один YAML на work;
7. collections;
8. multi-viewer/group-compatible signals;
9. explicit preference representation;
10. validator;
11. generated index;
12. SQLite builder;
13. derived profile builder в минимально достаточном виде;
14. README и AGENTS contract;
15. удаление/архивирование старых конкурирующих v2 source-of-truth файлов после проверки миграции.

Не входят в текущую реализацию:

- web UI;
- production API/service;
- authentication;
- автоматический background metadata refresh;
- обязательные embeddings/vector DB;
- полноценный персональный каталог people;
- полный event-sourcing.

Эти слои должны добавляться поверх v4 без изменения canonical model.

## 24. Migration rules

При миграции текущих данных:

- текущий пользователь становится `primary`;
- мнение partner переносится только там, где оно реально было сообщено;
- отсутствие просмотра никогда не становится негативным сигналом;
- существующие ratings/comments сохраняются;
- inferred ratings сохраняют provenance;
- collections не размножают оценки на отдельные members;
- season records не создаются без сезонной информации;
- сомнительные factual metadata не выдумываются;
- существующие title/year используются для первичной идентичности, external IDs добавляются только при надёжном match;
- старые файлы удаляются только после успешной validation новой структуры.

## 25. Acceptance criteria

v4 считается реализованной, когда:

1. все текущие пользовательские данные перенесены без потери смысла;
2. `primary`, `partner`, `couple` поддерживаются схемой без персональных данных;
3. work/collection/list/interaction/tombstone schemas валидируются;
4. vocabulary references проверяются автоматически;
5. schema drift при обычном добавлении work запрещён;
6. `validate.py` проходит на всей canonical базе;
7. index и SQLite полностью пересобираются из canonical data;
8. derived profiles пересобираются из raw signals/explicit preferences;
9. old v2 files больше не являются конкурирующим source of truth;
10. можно добавить новый work естественным языком, не придумывая новую структуру;
11. можно сохранить только `partner: liked`, а позже дополнить rating/feedback без миграции;
12. можно оценить сериал целиком без seasons и позже добавить season-specific signals;
13. можно запросить рекомендации для `primary`, `partner` или `couple`;
14. временные условия запроса не загрязняют постоянный профиль;
15. будущий сайт сможет читать generated runtime и писать через общий write protocol без смены canonical data model.
