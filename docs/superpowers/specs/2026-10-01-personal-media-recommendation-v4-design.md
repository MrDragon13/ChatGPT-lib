# Personal Media Recommendation Data Model v4 — design

Дата: 2026-10-01
Статус: proposed final architecture; implementation pending spec review

## 1. Цель

Создать долговечную персональную базу фильмов, сериалов, мини-сериалов и анимации, которую разные LLM смогут безопасно читать и обновлять без расползания схемы, дублей сущностей, дублирования понятий и потери пользовательского сигнала.

Система оптимизируется прежде всего под задачу: **понять вкус владельца, объяснимо рекомендовать непросмотренные произведения под текущий запрос и улучшать рекомендации по мере накопления отзывов**.

## 2. Ключевые принципы

1. Пользовательский сигнал важнее общих метаданных и внешних рейтингов.
2. `unwatched` не является отрицательной оценкой.
3. Оценка, причины оценки, пересмотры и интерес хранятся независимо.
4. Объективный признак произведения и субъективная реакция зрителя — разные сущности.
5. Все семантические признаки используют controlled vocabulary.
6. LLM не имеет права свободно расширять schema или vocabulary при обычном добавлении произведения.
7. Неизвестные данные остаются неизвестными; запрещено заполнять поля догадками ради полноты.
8. Одно произведение имеет одну каноническую запись.
9. Производные preferences должны иметь evidence и не заменяют исходные отзывы.
10. Физическое хранение оптимизируется под точечное чтение/обновление: один файл на произведение.
11. Общая оценка сериала самостоятельна; детализация сезонов необязательна.
12. Формат (`movie`, `series`, `miniseries`) и medium (`live_action`, `animation`, `hybrid`) независимы.
13. Франшиза/коллекция — не формат произведения, а отдельная сущность.
14. Пользовательские сравнения между произведениями — отдельный сильный сигнал.
15. Любая LLM сначала читает `AGENTS.md`, schemas и vocabulary, затем изменяет данные и запускает validation.
16. Одна связь хранится в одном каноническом месте; обратные ссылки и memberships строятся как derived data.

## 3. Физическая структура репозитория

```text
media/
├── AGENTS.md
├── README.md
├── vocabulary.yaml
├── preferences.yaml
│
├── schemas/
│   ├── work.schema.json
│   ├── collection.schema.json
│   ├── vocabulary.schema.json
│   └── preferences.schema.json
│
├── data/
│   ├── works/
│   │   ├── interstellar-2014.yaml
│   │   ├── game-night-2018.yaml
│   │   └── sherlock-2010.yaml
│   └── collections/
│       ├── oceans.yaml
│       └── now-you-see-me.yaml
│
├── generated/
│   └── index.jsonl
│
└── tools/
    ├── validate.py
    └── build_index.py
```

### Source of truth

- `media/data/works/*.yaml` — произведения + пользовательский сигнал.
- `media/data/collections/*.yaml` — франшизы/серии/группы произведений и пользовательские оценки коллекций.
- `media/vocabulary.yaml` — единственный канонический словарь семантических терминов.
- `media/preferences.yaml` — явные и производные закономерности вкуса.

### Производные данные

- `media/generated/index.jsonl` — компактный индекс для LLM/retrieval. Не source of truth; всегда пересобирается из канонических файлов.

## 4. Почему один файл на произведение

Один большой `works.yaml` отклонён для v4. При росте базы он ухудшает:

- точечное чтение LLM;
- размер контекста;
- Git diff;
- последовательные/параллельные изменения;
- риск случайной перезаписи соседних записей.

Один файл на произведение позволяет читать полный объект только для релевантных кандидатов.

## 5. Каноническая запись произведения

Пример:

```yaml
schema_version: 4
id: game-night-2018
entity_type: work

identity:
  format: movie
  medium: live_action
  title_original: Game Night
  title_ru: Игра в ночь
  alternate_titles: []
  year: 2018
  release_date: 2018-02-23
  external_ids:
    imdb: null
    tmdb: null

metadata:
  genres:
    - genre.comedy
    - genre.crime
    - genre.mystery
  runtime_min: 100
  original_language: en
  countries: [US]
  production_status: completed
  synopsis_short: >-
    Короткое spoiler-safe описание.
  directors:
    - John Francis Daley
    - Jonathan Goldstein
  writers: []
  main_cast: []
  traits:
    - term: pacing.fast
      source: metadata
      confidence: high
    - term: humor.absurd
      source: llm_inferred
      confidence: medium
  external_metrics:
    imdb:
      score: null
      votes: null
      observed_at: null
    tmdb:
      score: null
      votes: null
      observed_at: null
  provenance:
    source: null
    fetched_at: null

viewer:
  viewing:
    status: watched
    times_watched: 1
    times_watched_approximate: false
    first_watched_at: null
    last_watched_at: 2026-10-01
    progress: null
    contexts: []

  rating:
    score: 7.0
    source: explicit_approx
    confidence: high

  feedback:
    summary: >-
      Интересный и смешной фильм, но местами перебор с абсурдом,
      кринжем и испанским стыдом.
    signals:
      - term: entertainment.engaging
        sentiment: positive
        strength: 2
        source: explicit
        confidence: high
      - term: reaction.cringe
        sentiment: negative
        strength: 3
        source: explicit
        confidence: high
      - term: humor.absurd
        sentiment: negative
        strength: 2
        source: explicit
        confidence: high

  rewatch:
    intent: low

  interest:
    state: none
    priority: null

  recommendation:
    recommended_count: 1
    rejected_count: 0
    last_recommended_at: 2026-09-30
    permanent_rejection_reason: null

  relations:
    viewer: []

seasons: []

relations:
  canonical: []

provenance:
  created_at: 2026-10-01
  updated_at: 2026-10-01
```

## 6. Identity

### `identity.format`

Enum:

- `movie`
- `series`
- `miniseries`

### `identity.medium`

Enum:

- `live_action`
- `animation`
- `hybrid`

Примеры:

- мультфильм: `movie + animation`;
- анимационный сериал: `series + animation`;
- обычный сериал: `series + live_action`.

### Alternate titles

`alternate_titles` обязательны как поле-массив, но могут быть пустыми. Они используются при дедупликации и поиске.

### External IDs

IMDb/TMDB ID при наличии являются главными ключами дедупликации. Неизвестные ID остаются `null`.

## 7. Collections

Коллекция/франшиза — отдельная сущность и единственный source of truth для membership:

```yaml
schema_version: 4
id: oceans
entity_type: collection
name_ru: "Серия Ocean’s"
name_original: "Ocean's"
member_ids:
  - oceans-eleven-2001
  - oceans-twelve-2004
  - oceans-thirteen-2007

viewer:
  rating:
    score: 8.5
    source: inferred
    confidence: medium
  feedback:
    summary: "Вся серия хорошая."
    signals: []
```

Work-файл не дублирует `collection_ids`; memberships для retrieval выводятся из collection files в generated index.

Оценка коллекции не переносится автоматически на каждый member.

## 8. Metadata произведения

Рекомендуемые factual metadata:

- `genres`
- `runtime_min`
- `original_language`
- `countries`
- `production_status`
- `synopsis_short`
- `directors`
- `writers`
- `main_cast`
- `external_metrics`

### `production_status`

Enum:

- `ongoing`
- `completed`
- `cancelled`
- `unknown`

### External metrics

IMDb/TMDB score хранятся только как слабый внешний сигнал вместе с `votes` и `observed_at`.

Они никогда не переопределяют пользовательский профиль.

## 9. Semantic traits и provenance

`metadata.traits` не являются простым массивом строк. Каждый trait хранит происхождение:

```yaml
traits:
  - term: story.problem_solving
    source: metadata
    confidence: high

  - term: atmosphere.immersive
    source: llm_inferred
    confidence: medium
```

`source` enum:

- `metadata`
- `external_source`
- `llm_inferred`
- `user_explicit`

LLM-derived trait не должен со временем превращаться в «объективный факт» без provenance.

## 10. Viewing и progress

```yaml
viewing:
  status: partial
  times_watched: null
  times_watched_approximate: false
  first_watched_at: null
  last_watched_at: null
  progress:
    season: 2
    episode: 5
  contexts:
    - couple
```

`status` enum:

- `unwatched`
- `watched`
- `partial`
- `dropped`
- `forgotten`

`progress` необязателен и используется главным образом для сериалов.

`contexts` — controlled enum:

- `solo`
- `couple`
- `family`

Контекст не выдумывается, если пользователь его не сообщал.

## 11. Rating

```yaml
rating:
  score: 8.0
  source: inferred
  confidence: medium
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

Ручная правка пользователя имеет высший приоритет: `source: explicit`, `confidence: exact`.

## 12. Feedback signals

Вместо отдельных `positives/negatives` используется единый массив:

```yaml
feedback:
  summary: "..."
  signals:
    - term: story.intrigue
      sentiment: positive
      strength: 3
      source: explicit
      confidence: high
```

`sentiment`:

- `positive`
- `negative`
- `mixed`
- `neutral`

`strength`: `1..3`.

`source`:

- `explicit`
- `inferred`

Это позволяет отличать прямой пользовательский сигнал от интерпретации LLM.

## 13. Controlled vocabulary v4

Все term IDs namespaced.

Примеры:

- `genre.science_fiction`
- `genre.drama`
- `narrative.time_loop`
- `story.problem_solving`
- `story.intrigue`
- `story.twists`
- `pacing.fast`
- `pacing.slow`
- `humor.absurd`
- `humor.witty`
- `atmosphere.immersive`
- `visuals.strong`
- `characters.charisma`
- `reaction.cringe`
- `reaction.pacing_dragging`
- `reaction.excessive_darkness`

### Разделение trait/reaction

- `pacing.slow` — свойство произведения;
- `reaction.pacing_dragging` — субъективное ощущение затянутости.

- `humor.absurd` — стиль юмора;
- `reaction.cringe` — реакция пользователя.

Нельзя автоматически переносить неприязнь к viewer reaction на весь related movie trait.

## 14. Viewer relations между произведениями

Пользовательские сравнения — первичный персональный сигнал:

```yaml
viewer:
  relations:
    - target_id: edge-of-tomorrow-2014
      type: similar_to
      strength: 3
      dimensions:
        - story.problem_solving
        - narrative.time_loop
        - pacing.fast
      note: "По ощущениям напоминает «Грань будущего»."
      source: explicit
      confidence: exact
```

Минимальный enum типов:

- `similar_to`
- `reminds_of`
- `preferred_over`

`dimensions` используют canonical vocabulary IDs.

### Семантика `preferred_over`

Если relation хранится в work `A` и имеет `target_id: B`, то `A preferred_over B` означает: пользователь предпочитает исходное произведение A произведению B.

Если пользователь предпочитает B произведению A, relation должна храниться в B с `target_id: A`. Это исключает двусмысленное поле `direction`.

Viewer relation хранится только в исходной записи; обратные ссылки строятся в generated index.

## 15. Canonical relations

Фактические связи произведений хранятся отдельно от viewer relations:

```yaml
relations:
  canonical:
    - target_id: dune-part-two-2024
      type: sequel
```

Enum:

- `sequel`
- `prequel`
- `spinoff`
- `remake`
- `reboot`
- `adaptation`
- `same_franchise`

Каждая factual relation хранится один раз; reverse lookup является derived data.

## 16. Сериалы и сезоны

`seasons` — необязательная детализация. Общая оценка сериала самостоятельна.

Если есть только общая оценка:

```yaml
seasons: []
```

Если есть отдельное мнение:

```yaml
seasons:
  - number: 1
    title: null
    release_year: 2021
    episode_count: 9

    metadata:
      traits:
        - term: pacing.fast
          source: llm_inferred
          confidence: medium

    viewer:
      viewing:
        status: watched
      rating:
        score: 9.5
        source: explicit
        confidence: exact
      feedback:
        summary: "Первый сезон особенно сильный."
        signals: []
      rewatch:
        intent: high
```

Season metadata также необязательна. Она появляется только если различия между сезонами полезны для понимания вкуса.

Общая и сезонные оценки не пересчитывают друг друга.

## 17. Interest и recommendation state

`interest.state`:

- `none`
- `candidate`
- `shortlist`
- `not_interested`

`priority`: `1..5` или `null`.

Постоянное `not_interested` не следует путать с временным отказом от рекомендации «не сегодня».

Агрегированное состояние рекомендаций пока хранится в work record; подробный event log не вводится до появления реальной необходимости.

## 18. Preferences

`preferences.yaml` содержит два слоя:

```yaml
schema_version: 4
generated_at: 2026-10-01
derived_from_revision: <git-sha>

explicit_preferences: []
inferred_preferences: []
rules: []
constraints: []
```

### Explicit preferences

Только прямые пользовательские утверждения общего характера.

### Inferred preferences

Производные закономерности с evidence:

```yaml
- term: story.intrigue
  affinity: 0.9
  confidence: high
  evidence:
    positive:
      - knives-out-2019
      - sherlock-2010
    negative: []
```

### Rules

Контекстные зависимости, которые нельзя корректно выразить одним affinity:

```yaml
- id: slow-pacing-context
  statement: >-
    Медленный темп сам по себе не является проблемой; негатив возникает,
    когда медленность не окупается историей или персонажами.
  confidence: high
  evidence:
    positive:
      - shawshank-redemption-1994
      - the-green-mile-1999
    negative:
      - blade-runner-2049
```

### Constraints

Сильные режимы `avoid/prefer`, но создаются только при достаточном evidence или явном пользовательском указании.

## 19. Приоритет источников истины

От высшего к низшему:

1. Явное текущее утверждение пользователя.
2. Ручная правка пользователя в репозитории.
3. Сохранённый explicit feedback/rating конкретного произведения.
4. Inferred feedback конкретного произведения.
5. Explicit global preferences.
6. Inferred preferences/rules.
7. Factual metadata.
8. LLM-inferred semantic metadata.
9. External metrics/popularity.

Нижний уровень никогда не переопределяет верхний молча.

## 20. AGENTS.md: обязательный write protocol

Перед любым изменением данных агент обязан:

1. прочитать `media/AGENTS.md`;
2. прочитать соответствующую JSON Schema;
3. прочитать `media/vocabulary.yaml`;
4. найти существующую запись по external IDs, id и alternate titles;
5. не создавать неизвестные поля;
6. не создавать новый vocabulary term без поиска существующего аналога;
7. не менять schema из-за одного неудобного кейса;
8. не выдумывать unknown metadata;
9. сохранять provenance пользовательского и LLM-derived сигнала;
10. не создавать записи для всех рассмотренных кандидатов рекомендации — сохранять work только при реальном пользовательском взаимодействии/рекомендации/интересе;
11. запустить validation;
12. пересобрать generated index;
13. commit только при успешной validation.

Изменение schema, enum или semantics поля — отдельная архитектурная миграция.

## 21. Vocabulary growth protocol

Новый term допустим только если:

1. нет существующего канонического аналога;
2. различие полезно для будущих рекомендаций;
3. term не является синонимом;
4. есть однозначный namespace/kind/parent;
5. definition применима более чем к одному произведению.

Canonical term ID после использования не переименовывается без миграции.

## 22. Validation

`validate.py` проверяет как минимум:

- каждый work соответствует `work.schema.json`;
- каждая collection соответствует `collection.schema.json`;
- vocabulary и preferences соответствуют schemas;
- уникальность work IDs;
- уникальность ненулевых IMDb/TMDB IDs;
- отсутствие ссылок на несуществующие vocabulary terms;
- отсутствие relations на несуществующие targets;
- отсутствие collection member IDs без work;
- отсутствие дублирующего collection membership внутри work;
- уникальность season numbers;
- seasons разрешены только для series/miniseries;
- rating score/source/confidence согласованы;
- progress допустим только при подходящем viewing status;
- `dimensions` viewer relations существуют в vocabulary;
- preferences evidence ссылается на существующие works;
- generated index соответствует текущим source files.

## 23. Generated index

`build_index.py` строит `generated/index.jsonl`.

Каждая строка содержит компактный объект, достаточный для первичного retrieval:

```json
{"id":"interstellar-2014","title_ru":"Интерстеллар","format":"movie","medium":"live_action","year":2014,"status":"watched","rating":9.5,"genres":["genre.science_fiction","genre.drama"],"traits":["story.problem_solving","atmosphere.immersive"],"interest":"none"}
```

Индекс может включать derived collection memberships, обратные canonical/viewer relation ссылки и другие поля, которые полностью вычисляются из source data.

## 24. Recommendation pipeline

```text
current request
    ↓
preferences.yaml
    ↓
generated/index.jsonl
    ↓
filter watched / rejected / constraints
    ↓
select relevant candidates
    ↓
read full YAML for relevant works only
    ↓
rank/explain recommendations
```

Хранилище может расти до тысяч произведений без необходимости читать всю базу в контекст.

## 25. Что сознательно не хранится в v4

По умолчанию не сохраняются:

- стриминговая доступность;
- текущая цена аренды/покупки;
- полный cast/crew;
- длинный synopsis;
- бюджет/касса;
- десятки внешних рейтингов;
- награды;
- большой recommendation event log;
- автоматически придуманные десятки mood dimensions.

Это добавляется только при доказанной полезности.

## 26. Критерии готовности реализации v4

Реализация завершена, когда:

1. создана структура `media/` v4;
2. текущие данные мигрированы без потери пользовательских оценок/комментариев;
3. collections отделены от works;
4. текущие фильмы/сериалы получили отдельные source files;
5. создан минимальный namespaced vocabulary;
6. создан `preferences.yaml` с evidence;
7. schemas запрещают произвольные поля (`additionalProperties: false` там, где уместно);
8. создан `AGENTS.md` с протоколом записи;
9. `validate.py` проходит;
10. `build_index.py` строит корректный `index.jsonl`;
11. старые `movies/` v2/v3 данные удалены после успешной миграции;
12. README обновлён;
13. ни один inferred факт не выдан за explicit user statement;
14. сезонная детализация остаётся необязательной;
15. пользовательские relations и semantic provenance сохраняются отдельно от canonical metadata;
16. v3 design отмечен как superseded by v4.
