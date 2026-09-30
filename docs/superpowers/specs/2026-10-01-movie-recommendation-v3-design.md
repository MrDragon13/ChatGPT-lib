# Personal Media Recommendation Data Model v3 — design

Дата: 2026-10-01
Статус: design refined; implementation pending final spec review

## 1. Цель

Создать долговечную структуру данных для персональных рекомендаций фильмов, сериалов, мини-сериалов и анимации, которую разные LLM смогут читать и обновлять без расползания схемы, дублирования понятий и потери пользовательского сигнала.

Система оптимизируется не под каталогизацию медиа как таковую, а под задачу: **понять вкус владельца, объяснимо подобрать непросмотренное произведение под текущий запрос и учиться на новых отзывах**.

## 2. Основные принципы

1. Пользовательский сигнал важнее общих метаданных произведения.
2. `unwatched` никогда не трактуется как отрицательная оценка.
3. Числовая оценка и причины оценки хранятся независимо.
4. Объективный признак произведения и субъективная реакция зрителя — разные сущности.
5. Медленный темп (`pacing.slow`) и ощущение затянутости (`pacing.dragging`) не смешиваются.
6. LLM не имеет права свободно расширять структуру или словарь.
7. Неизвестные значения остаются неизвестными; данные не выдумываются ради заполнения полей.
8. Одно произведение имеет одну каноническую запись; дубликаты предотвращаются до записи.
9. Производные выводы о вкусе имеют evidence и не подменяют исходные отзывы.
10. Структура хранения должна быть удобна LLM: минимум join-операций между несколькими большими списками.
11. Сезонная детализация сериалов необязательна. Общая оценка сериала является самостоятельной и не вычисляется автоматически из оценок сезонов.
12. Фильм/сериал — формат произведения; live action/animation/hybrid — отдельное свойство medium.

## 3. Файловая структура v3

```text
media/
├── AGENTS.md
├── README.md
├── vocabulary.yaml
├── preferences.yaml
├── schemas/
│   ├── works.schema.json
│   ├── vocabulary.schema.json
│   └── preferences.schema.json
├── tools/
│   └── validate.py
└── data/
    └── works.yaml
```

Корневой `README.md` репозитория ссылается на `media/README.md`.

### Роли файлов

- `media/data/works.yaml` — единственный источник истины по произведениям, просмотрам, личным оценкам и индивидуальным отзывам.
- `media/vocabulary.yaml` — канонический controlled vocabulary.
- `media/preferences.yaml` — агрегированные выводы о вкусе с confidence и evidence.
- `media/schemas/*.schema.json` — машинно-проверяемые JSON Schema.
- `media/AGENTS.md` — обязательный протокол чтения и записи для любой LLM/агента.
- `media/tools/validate.py` — локальная проверка структуры и ссылочной целостности vocabulary.
- `media/README.md` — человекочитаемая навигация.

Старые `movies/profile.md` и `movies/schema.md` после миграции удаляются как дублирующие источники истины. Git history сохраняет прошлые версии.

## 4. Верхний уровень `works.yaml`

```yaml
version: 3
rating_scale: 10
works: []
```

## 5. Каноническая запись произведения

```yaml
- id: game-night-2018

  identity:
    format: movie
    medium: live_action
    title_original: Game Night
    title_ru: Игра в ночь
    year: 2018
    release_date: 2018-02-23
    external_ids:
      imdb: null
      tmdb: null
    franchise_id: null

  metadata:
    genres:
      - comedy
      - crime
      - mystery
    runtime_min: 100
    original_language: en
    countries:
      - US
    synopsis_short: >-
      Короткое описание без существенных спойлеров.
    directors:
      - John Francis Daley
      - Jonathan Goldstein
    writers: []
    main_cast: []
    traits:
      - pacing.fast
      - tone.light
      - structure.ensemble
      - humor.absurd
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

  viewing:
    status: watched
    watched_at: null

  rating:
    score: 7.0
    source: explicit_approx
    confidence: high

  feedback:
    summary: >-
      В целом хороший, интересный и смешной фильм, но местами
      перебор с абсурдом, кринжем и испанским стыдом.
    positives:
      - trait: pacing.fast
        strength: 2
      - trait: entertainment.engaging
        strength: 2
    negatives:
      - trait: humor.cringe
        strength: 3
      - trait: humor.absurd
        strength: 2

  rewatch:
    count: 1
    count_is_approximate: false
    intent: low

  interest:
    state: none
    priority: null

  recommendation:
    recommended_count: 1
    rejected_count: 0
    last_recommended_at: 2026-09-30

  seasons: []

  provenance:
    created_at: 2026-10-01
    updated_at: 2026-10-01
```

## 6. Формат и medium

`identity.format` — enum:

- `movie`
- `series`
- `miniseries`
- `collection`

`identity.medium` — enum:

- `live_action`
- `animation`
- `hybrid`

Анимационный фильм — `format: movie`, `medium: animation`.
Анимационный сериал — `format: series`, `medium: animation`.

## 7. Метаданные произведения

Метаданные нужны для сопоставления характеристик непросмотренных произведений с пользовательским вкусом, но всегда имеют меньший приоритет, чем пользовательский сигнал.

### Рекомендуемые поля

Обязательная/основная идентификация:

- `year`
- `external_ids.imdb`
- `external_ids.tmdb`
- `format`
- `medium`

Полезные рекомендательные признаки:

- `genres`
- `runtime_min`
- `synopsis_short`
- `directors`
- `writers`
- `main_cast`
- `original_language`
- `countries`
- `traits`

`main_cast` хранит только ключевых исполнителей, а не полный cast.
`synopsis_short` должен быть коротким и по возможности без спойлеров.

### Внешние рейтинги

Публичные рейтинги являются слабым дополнительным сигналом, а не заменой персонального вкуса.

```yaml
external_metrics:
  imdb:
    score: 8.7
    votes: 2200000
    observed_at: 2026-10-01
```

Значения должны хранить дату наблюдения, потому что публичные рейтинги меняются.

### Provenance метаданных

```yaml
metadata:
  provenance:
    source: tmdb
    fetched_at: 2026-10-01
```

LLM не должна выдумывать factual metadata, если оно неизвестно. Неизвестные значения остаются `null`/пустыми согласно schema.

## 8. Идентичность и дедупликация

Внутренний `id` — человекочитаемый стабильный ключ `<canonical-title-slug>-<year>`.

Если внешние ID известны, они являются главным средством дедупликации.

Перед созданием новой записи агент проверяет по порядку:

1. TMDB ID;
2. IMDb ID;
3. внутренний `id`;
4. canonical title + year и альтернативные названия.

После создания внутренний `id` не меняется из-за перевода или альтернативного названия.

## 9. Статус просмотра

`viewing.status`:

- `unwatched`
- `watched`
- `partial`
- `dropped`
- `forgotten`

Статус просмотра не является оценкой.

`dropped` также не означает автоматически отрицательное отношение.

## 10. Личная оценка

```yaml
rating:
  score: 8.0
  source: inferred
  confidence: medium
```

`score`:

- `1.0..10.0`;
- шаг `0.5`;
- `null`, если оценки нет.

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

При ручной пользовательской правке числа `source` становится `explicit`, `confidence` — `exact`.

## 11. Feedback — главный обучающий сигнал

```yaml
feedback:
  summary: "..."
  positives:
    - trait: story.intrigue
      strength: 3
  negatives:
    - trait: pacing.dragging
      strength: 2
```

`strength`:

- `1` — заметный нюанс;
- `2` — существенный фактор;
- `3` — одна из главных причин впечатления.

Не заполнять аспекты «на всякий случай». Структурируются только реально выраженные или очень надёжно выведенные причины.

## 12. Movie traits и viewer reactions

Это разные категории.

```yaml
metadata:
  traits:
    - pacing.slow

feedback:
  negatives:
    - trait: pacing.dragging
      strength: 2
```

`pacing.slow` — описательный признак произведения.
`pacing.dragging` — субъективная реакция зрителя.

Из отрицательной реакции `pacing.dragging` нельзя автоматически выводить нелюбовь к `pacing.slow`.

## 13. Rewatch

```yaml
rewatch:
  count: 5
  count_is_approximate: true
  intent: high
```

`intent`:

- `none`
- `low`
- `medium`
- `high`
- `unknown`

Пересмотр — самостоятельный сильный сигнал и не вычисляется из рейтинга.

## 14. Interest / watchlist

Отдельный watchlist-файл не создаётся.

```yaml
interest:
  state: shortlist
  priority: 3
```

`state`:

- `none`
- `candidate`
- `shortlist`
- `not_interested`

`priority`: `1..5` или `null`.

`unwatched` — факт просмотра; `shortlist` — намерение посмотреть.

## 15. Recommendation state

Пока хранится агрегированно внутри произведения:

```yaml
recommendation:
  recommended_count: 3
  rejected_count: 1
  last_recommended_at: 2026-10-01
```

Подробный event log в v3 не вводится.

## 16. Сериалы и необязательные оценки сезонов

### Главный принцип

`seasons` — **необязательный слой детализации**.

Если пользователь оценил сериал только в целом, этого достаточно:

```yaml
identity:
  format: series

rating:
  score: 9.0
  source: explicit
  confidence: exact

feedback:
  summary: "Отличный сериал."

seasons: []
```

Нельзя создавать фиктивные оценки сезонов только ради заполнения структуры.

### Если есть отдельное мнение о сезонах

```yaml
seasons:
  - number: 1
    title: null
    release_year: 2021
    episode_count: 9

    viewing:
      status: watched

    rating:
      score: 9.5
      source: explicit
      confidence: exact

    feedback:
      summary: "Первый сезон особенно сильный."
      positives: []
      negatives: []

    rewatch:
      count: null
      count_is_approximate: false
      intent: unknown

  - number: 2
    title: null
    release_year: 2024
    episode_count: 9

    viewing:
      status: unwatched

    rating:
      score: null
      source: none
      confidence: none
```

### Независимость общей и сезонной оценки

Общая оценка сериала и оценки сезонов **не пересчитывают друг друга автоматически**.

Например:

- Season 1 — 9.5
- Season 2 — 7.5
- Series overall — 9.0

Это валидно: общая оценка отражает общее впечатление, а не среднее арифметическое.

Сезоны не являются отдельными top-level `works`, если нет отдельной архитектурной причины это изменить в будущей версии.

## 17. Controlled vocabulary

`vocabulary.yaml` — обязательный канонический словарь.

```yaml
version: 1
terms:
  story.intrigue:
    kind: aspect
    parent: story
    label_ru: Интрига
    definition: Насколько сюжет вызывает желание узнать, что произойдёт дальше.
    aliases:
      - сюжетная интрига

  pacing.slow:
    kind: movie_trait
    parent: pacing
    label_ru: Медленный темп
    definition: Низкая скорость развития действия как свойство произведения.
    aliases: []

  pacing.dragging:
    kind: viewer_reaction
    parent: pacing
    label_ru: Ощущение затянутости
    definition: Субъективное ощущение, что темп медленнее, чем оправдывает содержание.
    aliases:
      - душновато
      - затянуто
```

Допустимые `kind`:

- `genre`
- `movie_trait`
- `narrative_device`
- `theme`
- `aspect`
- `viewer_reaction`

### Vocabulary rules

1. В данных используются только canonical term IDs.
2. Alias никогда не используется как ID.
3. Перед созданием нового термина агент ищет существующий по ID, label, aliases, parent и смыслу.
4. Новый термин допустим только если существующий не выражает нужное различие.
5. Термин не создаётся ради одного специфического произведения, если его нельзя осмысленно применить повторно.
6. Предпочтение отдаётся существующему более общему термину перед бессмысленно узким новым.
7. Новому термину обязательны `kind`, `label_ru`, `definition`; `parent` может быть `null`.
8. Изменение/слияние canonical IDs считается миграцией, а не обычной записью данных.

## 18. Начальный словарь v3

Минимальный набор покрывает текущие отзывы и расширяется только по необходимости.

### Story / structure

- `story.intrigue`
- `story.twists`
- `story.logic`
- `story.payoff`
- `structure.ensemble`
- `structure.mystery`
- `problem_solving`

### Pacing / engagement

- `pacing.fast`
- `pacing.moderate`
- `pacing.slow`
- `pacing.dragging`
- `entertainment.engaging`

### Characters

- `characters.charisma`
- `characters.depth`
- `dialogue.strong`

### Tone / atmosphere

- `tone.light`
- `tone.serious`
- `tone.dark`
- `atmosphere.immersive`
- `darkness.excessive`

### Humor

- `humor.witty`
- `humor.dark`
- `humor.absurd`
- `humor.cringe`

### Craft / concept

- `visuals.strong`
- `action.strong`
- `emotional_impact`
- `worldbuilding`
- `concept.high`
- `time_loop`

## 19. `preferences.yaml`

Производные закономерности отделены от первичных отзывов.

```yaml
version: 1
preferences:
  - trait: story.intrigue
    affinity: 0.9
    confidence: high
    evidence:
      positive:
        - knives-out-2019
        - sherlock-bbc
      negative: []

rules:
  - id: slow-pacing-context
    statement: >-
      Медленный темп сам по себе не является проблемой. Негатив возникает,
      когда медленность не окупается историей или персонажами.
    confidence: high
    evidence:
      positive:
        - shawshank-redemption-1994
        - the-green-mile-1999
      negative:
        - blade-runner-2049
```

`preferences.yaml` не должен автоматически переписываться после каждого единичного фильма без достаточного evidence.

## 20. Приоритет источников истины

От высшего к низшему:

1. Явное текущее утверждение пользователя.
2. Ручная правка пользователем данных в репозитории.
3. Сохранённый пользовательский отзыв/оценка конкретного произведения.
4. Структурированный feedback, выведенный из отзыва.
5. Производные preferences.
6. Метаданные произведения.
7. Внешние рейтинги/общественная популярность.

Нижний уровень никогда не должен молча переопределять верхний.

## 21. Обязательный LLM write protocol

Перед изменением данных агент обязан:

1. Прочитать `media/AGENTS.md`.
2. Прочитать соответствующие JSON Schema.
3. Прочитать `media/vocabulary.yaml`.
4. Найти существующую запись произведения и проверить внешние ID.
5. Не создавать неизвестные поля.
6. Не создавать новый vocabulary term без поиска существующего аналога.
7. Не менять schema только потому, что новая запись неудобно в неё укладывается.
8. Не выдумывать неизвестные данные ради полноты.
9. Сохранять пользовательский сигнал и его provenance.
10. Проверить schema и vocabulary references перед commit.

### Изменение схемы

Изменение структуры, enum или смысла существующего поля — отдельная архитектурная миграция. Обычное добавление произведения не имеет права менять schema.

## 22. Создание нового vocabulary term

Новый термин допустим только когда:

1. существующего подходящего canonical term нет;
2. различие полезно для будущих рекомендаций;
3. это не синоним существующего термина;
4. можно однозначно определить `kind` и `parent`;
5. definition применима более чем к одному конкретному произведению.

## 23. Validation

`media/tools/validate.py` проверяет как минимум:

- соответствие `works.yaml` JSON Schema;
- соответствие `vocabulary.yaml` своей schema;
- соответствие `preferences.yaml` своей schema;
- уникальность внутренних `id`;
- уникальность ненулевых IMDb/TMDB ID;
- что каждый `metadata.genres`, `metadata.traits` и `feedback.*.trait` существует в vocabulary;
- что каждый preference trait существует в vocabulary;
- что evidence ссылается на существующие works;
- что season number уникален внутри сериала;
- что `seasons` используется только для `series`/`miniseries`;
- согласованность `rating.source/confidence/score` на базовом уровне.

## 24. Контекст для рекомендаций

Хранилище может со временем стать большим, но LLM не обязана каждый раз читать все произведения.

Позже поверх v3 можно строить временный recommendation context из:

- `preferences.yaml`;
- релевантных просмотренных произведений;
- shortlist/candidates;
- последних просмотров;
- недавно рекомендованных произведений;
- текущего пользовательского запроса.

Это производный runtime-контекст, а не дополнительный источник истины.

## 25. Критерии готовности реализации v3

Реализация считается завершённой, когда:

1. текущие данные без потери пользовательских оценок перенесены в `media/data/works.yaml`;
2. текущие сериал/коллекции корректно представлены новым `format`;
3. `seasons` отсутствует или пуст для сериалов без сезонной детализации;
4. создан минимальный canonical `vocabulary.yaml`;
5. создан `preferences.yaml` с evidence на основе текущего опроса;
6. созданы строгие JSON Schema с `additionalProperties: false` там, где это уместно;
7. создан `AGENTS.md` с write protocol;
8. создан `validate.py` и он проходит на всех v3-файлах;
9. старые v2-файлы удалены/заменены без двух конкурирующих источников истины;
10. README обновлён под `media/`;
11. ни один inferred факт не выдан за пользовательское утверждение;
12. общая оценка сериала не зависит автоматически от наличия/оценок сезонов.
