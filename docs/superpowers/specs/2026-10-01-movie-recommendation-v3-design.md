# Movie Recommendation Data Model v3 — design

Дата: 2026-10-01
Статус: design approved in chat; implementation pending spec review

## 1. Цель

Создать долговечную структуру данных для персональных рекомендаций фильмов, которую разные LLM смогут читать и обновлять без постепенного расползания схемы, дублирования понятий и потери пользовательского сигнала.

Система должна оптимизироваться не под каталогизацию кино как таковую, а под задачу: **понять вкус владельца, объяснимо подобрать непросмотренные фильмы под текущий запрос и учиться на новых отзывах**.

## 2. Основные принципы

1. Пользовательский сигнал важнее общих метаданных фильма.
2. `unwatched` никогда не трактуется как отрицательная оценка.
3. Числовая оценка и причина оценки хранятся независимо.
4. Объективный/описательный признак фильма и субъективная реакция зрителя — разные сущности.
5. Медленный темп (`pacing.slow`) и ощущение затянутости (`pacing.dragging`) не смешиваются.
6. Новые LLM не имеют права свободно расширять структуру или словарь.
7. Неизвестные значения остаются неизвестными; данные не выдумываются ради заполнения полей.
8. Один фильм имеет одну каноническую запись; дубликаты должны предотвращаться до записи.
9. Производные выводы о вкусе должны иметь evidence и не подменять исходные отзывы.
10. Структура хранения должна быть удобна LLM: минимум join-операций между несколькими большими списками.

## 3. Файловая структура v3

```text
movies/
├── AGENTS.md
├── README.md
├── schema.json
├── vocabulary.yaml
├── preferences.yaml
└── data/
    └── movies.yaml
```

Корневой `README.md` репозитория ссылается на `movies/README.md`.

### Роли файлов

- `movies/data/movies.yaml` — единственный источник истины по фильмам, просмотрам, оценкам и индивидуальным отзывам.
- `movies/vocabulary.yaml` — канонический controlled vocabulary для жанров, признаков, narrative devices, аспектов и реакций.
- `movies/preferences.yaml` — агрегированные выводы о вкусе с confidence и evidence.
- `movies/schema.json` — машинно-проверяемая JSON Schema для структуры `movies.yaml`.
- `movies/AGENTS.md` — обязательный протокол чтения и записи для любой LLM/агента.
- `movies/README.md` — человекочитаемая навигация и краткая инструкция.

Старый `profile.md` удаляется как самостоятельный источник выводов: его содержимое мигрирует в `preferences.yaml`. Старый prose `schema.md` заменяется машинной `schema.json` и пояснениями в README/AGENTS.

## 4. `movies.yaml`: один самодостаточный объект на произведение

Верхний уровень:

```yaml
version: 3
rating_scale: 10
movies: []
```

Пример записи:

```yaml
- id: game-night-2018

  identity:
    kind: movie
    title_original: Game Night
    title_ru: Игра в ночь
    year: 2018
    external_ids:
      imdb: null
      tmdb: null
    franchise_id: null

  metadata:
    genres:
      - comedy
      - crime
      - mystery
    runtime_min: null
    traits:
      - pacing.fast
      - tone.light
      - structure.ensemble
      - humor.absurd

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

  provenance:
    created_at: 2026-10-01
    updated_at: 2026-10-01
```

## 5. Идентичность и дедупликация

### `id`

Человекочитаемый стабильный ключ: `<canonical-title-slug>-<year>`.

Пример: `edge-of-tomorrow-2014`.

После создания `id` не меняется из-за перевода, альтернативного названия или ребрендинга.

### `external_ids`

```yaml
external_ids:
  imdb: tt1631867
  tmdb: 137113
```

Если внешние ID известны, они являются главным средством дедупликации.

Перед созданием новой записи агент обязан проверить:

1. совпадение TMDB ID;
2. совпадение IMDb ID;
3. существующий внутренний `id`;
4. совпадение canonical title + year / известных альтернативных названий.

Неизвестные внешние ID могут быть `null`; агент не должен выдумывать их.

## 6. Статус просмотра

`viewing.status` — enum:

- `unwatched`
- `watched`
- `partial`
- `dropped`
- `forgotten`

Статус просмотра не является оценкой.

`dropped` также не означает автоматически отрицательное отношение: причина может быть бытовой или неизвестной.

## 7. Личная оценка

```yaml
rating:
  score: 8.0
  source: inferred
  confidence: medium
```

### `score`

- число от `1.0` до `10.0`;
- шаг `0.5`;
- `null`, если пользователь не дал достаточного сигнала.

### `source`

- `explicit` — пользователь дал точное число;
- `explicit_approx` — пользователь дал приблизительное число/границу (`около 7`, `максимум 7`);
- `inferred` — число восстановлено по словесной формулировке;
- `none` — оценки нет.

### `confidence`

- `exact`
- `high`
- `medium`
- `low`
- `none`

Оценка не должна автоматически вычисляться из `feedback` при обычной записи. Если пользователь позже вручную меняет число, его правка имеет приоритет и `source` становится `explicit`.

## 8. Feedback: главный обучающий сигнал

`feedback` хранит не только общий комментарий, но и структурированные причины впечатления.

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

### `strength`

- `1` — заметный нюанс;
- `2` — существенный фактор;
- `3` — одна из главных причин впечатления.

Нельзя заполнять десятки аспектов «на всякий случай». В запись добавляются только аспекты, по которым есть реальный пользовательский сигнал или очень надёжная интерпретация его слов.

## 9. Movie traits и viewer reactions

Это разные категории.

Пример:

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

`pacing.dragging` — субъективная негативная реакция зрителя.

Нельзя делать вывод, что пользователь не любит `pacing.slow`, только потому что один медленный фильм получил негатив за `pacing.dragging`.

## 10. Rewatch

Пересмотр — отдельный сильный сигнал, не производный от рейтинга.

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

Высокий `rewatch.count` или `rewatch.intent` должен учитываться при построении preferences как дополнительное подтверждение вкуса.

## 11. Interest / watchlist

Отдельный файл watchlist не создаётся.

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

`priority` — `1..5` или `null`.

`unwatched` — факт просмотра; `shortlist` — намерение посмотреть. Эти состояния не смешиваются.

## 12. Recommendation state

Пока хранится агрегированно внутри фильма:

```yaml
recommendation:
  recommended_count: 3
  rejected_count: 1
  last_recommended_at: 2026-10-01
```

Это предотвращает повторное навязчивое рекомендование одних и тех же фильмов.

Подробный event log в v3 не вводится. Он добавляется только при реальной потребности анализировать последовательность рекомендаций.

## 13. Controlled vocabulary

`vocabulary.yaml` — обязательный канонический словарь.

Структура:

```yaml
version: 1
terms:
  story.intrigue:
    kind: aspect
    parent: story
    label_ru: Интрига
    definition: >-
      Насколько сюжет вызывает желание узнать, что произошло
      или что произойдёт дальше.
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
    definition: >-
      Субъективное ощущение зрителя, что темп медленнее,
      чем оправдывает содержание.
    aliases:
      - душновато
      - затянуто
```

### Допустимые `kind`

- `genre`
- `movie_trait`
- `narrative_device`
- `theme`
- `aspect`
- `viewer_reaction`

### Правила vocabulary

1. В данных используются только canonical term IDs.
2. Alias никогда не используется как ID в `movies.yaml` или `preferences.yaml`.
3. Перед созданием нового термина агент ищет существующий по ID, label, aliases, parent и семантике.
4. Новый термин допустим только если существующий термин не выражает нужное различие.
5. Термин не создаётся ради одного специфического фильма, если его нельзя осмысленно применить повторно.
6. Предпочтение отдаётся существующему более общему термину перед бессмысленно узким новым.
7. Каждому новому термину обязательны `kind`, `label_ru`, `definition`; `parent` может быть `null`.
8. Изменение/слияние существующих canonical IDs считается миграцией, а не обычным добавлением фильма.

## 14. Начальный словарь v3

Словарь должен стартовать небольшим и расширяться по необходимости. Минимальный набор покрывает текущие отзывы:

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
- `tone.dark`
- `atmosphere.immersive`
- `darkness.excessive`

### Humor

- `humor.witty`
- `humor.dark`
- `humor.absurd`
- `humor.cringe`

### Craft

- `visuals.strong`
- `action.strong`
- `emotional_impact`
- `worldbuilding`
- `concept.high_concept`

### Narrative devices

- `time_loop`
- `time_travel`
- `unreliable_reality`
- `heist_or_plan`
- `investigation`

### Genres

Базовые жанры (`sci_fi`, `drama`, `thriller`, `crime`, `mystery`, `comedy`, `action`, `adventure`, `historical`, `war`, `horror`, `romance`, `animation`) также являются canonical vocabulary terms `kind: genre`.

## 15. `preferences.yaml`

Это производный, но сохраняемый слой глобальных выводов о вкусе.

```yaml
version: 3
updated_at: 2026-10-01
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
  - id: slow-is-not-dragging
    statement: >-
      Медленный темп сам по себе не является проблемой; негативный сигнал
      возникает при ощущении неоправданной затянутости.
    confidence: high
    evidence:
      supports:
        - the-green-mile-1999
        - shawshank-redemption-1994
        - blade-runner-2049
```

### `affinity`

Число `-1.0 .. 1.0`:

- отрицательное — trait чаще связан с негативной реакцией;
- около нуля — устойчивого сигнала нет;
- положительное — trait чаще связан с положительной реакцией.

`affinity` — не пользовательская оценка фильма и не обязана автоматически пересчитываться после каждой записи.

### Evidence

Любое предпочтение должно ссылаться на конкретные фильмы. Вывод без evidence не допускается.

`high` confidence не устанавливается по одному косвенному наблюдению.

## 16. Приоритет источников истины

При конфликте действует порядок:

1. явное текущее утверждение пользователя;
2. ручная правка пользователя в репозитории;
3. сохранённый исходный `feedback.summary`;
4. структурированный feedback, выведенный из слов пользователя;
5. агрегированные preferences;
6. общие метаданные фильма, добавленные LLM.

LLM не должна отменять пользовательскую реакцию на основании жанра или публичной репутации фильма.

## 17. `schema.json`

JSON Schema должна валидировать структуру `movies.yaml` после YAML→JSON parsing.

Ключевые требования:

- `additionalProperties: false` на всех структурных объектах;
- enum для `kind`, `status`, `rating.source`, `confidence`, `rewatch.intent`, `interest.state`;
- rating `1..10`, `multipleOf: 0.5`, nullable;
- feedback `strength` только `1|2|3`;
- даты формата `YYYY-MM-DD` или `null`;
- внешние IDs nullable strings/integers по выбранному типу;
- обязательны `id`, `identity`, `viewing`, `rating`, `feedback`, `rewatch`, `interest`, `recommendation`, `provenance`;
- неизвестные поля запрещены.

JSON Schema не может сама проверить существование trait ID в `vocabulary.yaml`; это семантическое правило AGENTS/protocol и будущего validator script.

## 18. `AGENTS.md`: обязательный write protocol

Перед любым изменением кино-базы LLM обязана:

1. Прочитать `movies/AGENTS.md`.
2. Прочитать `movies/schema.json`.
3. Прочитать `movies/vocabulary.yaml`.
4. Найти существующую запись фильма до создания новой.
5. Проверить внешние IDs / title + year для дедупликации.
6. Не добавлять новых полей вне schema.
7. Не использовать новые термины без проверки vocabulary.
8. Не менять schema ради удобства одной новой записи.
9. Не выдумывать неизвестные данные.
10. При добавлении нового vocabulary term выполнить canonicalization checks.
11. Не выводить отрицательную оценку из `unwatched`, `forgotten`, `partial` или `dropped`.
12. Сохранять исходный смысл пользовательского комментария.
13. Пользовательскую ручную оценку не заменять LLM-инференсом.
14. После изменения проверить структурную согласованность всех затронутых записей.

### Изменение архитектуры

Изменения в `schema.json`, meaning существующих canonical vocabulary IDs, enum-значениях или основных правилах AGENTS считаются архитектурными и не должны происходить как побочный эффект обычного добавления фильма.

## 19. Recommendation protocol

При запросе рекомендации LLM должна:

1. Прочитать `preferences.yaml` как компактный глобальный профиль.
2. Учесть текущие ограничения пользователя (жанр, настроение, длительность, степень мрачности и т. п.).
3. Исключить `watched`, если пользователь не просит пересмотр.
4. Учитывать `interest.state=not_interested` как сильный фильтр.
5. Учитывать историю рекомендаций, чтобы не повторять один и тот же фильм без причины.
6. Для объяснения рекомендаций использовать evidence из высокооценённых фильмов и feedback, а не только жанровое сходство.
7. Не считать жанр самостоятельным доказательством предпочтения.
8. Различать глобальный вкус и текущий контекст: например, пользователь может любить мрачные триллеры, но сегодня просить лёгкий фильм.

## 20. Масштабирование

В v3 база физически остаётся одним `movies.yaml`, потому что это минимизирует join-операции для LLM.

Когда размер файла реально станет проблемой, допускается физическое шардирование без изменения логической модели, например по первой букве ID или году. До этого момента шардирование не вводится.

При больших объёмах можно генерировать временный `recommendation-context.yaml`, содержащий только:

- preferences;
- самые информативные оценённые фильмы;
- последние просмотры;
- shortlist;
- релевантных текущему запросу кандидатов;
- недавно рекомендованные позиции.

Этот context-файл является производным и не становится источником истины.

## 21. Миграция v2 → v3

1. Сохранить все существующие записи и числовые оценки.
2. Перенести плоские поля `kind/title/year/status/rating/...` в новую вложенную структуру.
3. Сохранить каждый текущий `comment` как `feedback.summary` без потери смысла.
4. Добавить структурированные positives/negatives только там, где они ясно следуют из уже известных отзывов.
5. Не придумывать метаданные только ради заполнения новой схемы.
6. Создать начальный vocabulary на основании реально используемых понятий.
7. Перенести аналитические выводы из `profile.md` в `preferences.yaml` как rules/preferences с evidence.
8. Удалить `profile.md` после успешной миграции.
9. Заменить prose `schema.md` на `schema.json`.
10. Обновить `movies/README.md` и корневой README.

## 22. Non-goals v3

В v3 сознательно не вводятся:

- SQLite/PostgreSQL;
- отдельный event log каждой рекомендации;
- отдельный watchlist-файл;
- отдельные user/movie таблицы;
- embedding storage;
- автоматические LLM-generated оценки всех аспектов;
- сотни заранее придуманных vocabulary terms;
- автоматическое изменение пользовательской оценки по модели.

## 23. Критерии готовности v3

Миграция считается завершённой, когда:

- все текущие фильмы представлены в `version: 3` формате;
- оценки и комментарии v2 не потеряны;
- `schema.json` описывает и ограничивает структуру;
- `vocabulary.yaml` содержит все term IDs, использованные в мигрированных данных и preferences;
- `preferences.yaml` содержит только evidence-backed выводы;
- `AGENTS.md` однозначно запрещает произвольные поля/синонимы/скрытые schema changes;
- старые `profile.md` и `schema.md` удалены;
- README описывает v3 как единственную актуальную модель;
- в репозитории нет двух конкурирующих источников истины по оценкам.
