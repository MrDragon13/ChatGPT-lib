# Personal Media Recommendation Data Model v4 — design

Дата: 2026-10-01  
Статус: **design approved in chat; written spec awaiting final user review**  
Заменяет: `2026-10-01-movie-recommendation-v3-design.md`

## 1. Цель

Создать долговечную персональную медиатеку для фильмов, сериалов, мини-сериалов и анимации, которая:

- сохраняет пользовательский сигнал точнее обычного списка оценок;
- поддерживает нескольких зрителей и совместный просмотр;
- безопасно обновляется разными LLM без расползания схемы и словаря;
- остаётся удобной для Git и ручного чтения;
- масштабируется до сотен и тысяч произведений;
- позже служит каноническим источником для сайта, API, SQLite, полнотекстового и векторного поиска.

Главная задача — **объяснимо рекомендовать произведения под конкретного зрителя или группу и улучшать рекомендации по мере накопления реальных отзывов**.

## 2. Основные принципы

1. Git/YAML — канонический source of truth.
2. SQLite, индексы, derived profiles, embeddings и image cache — пересобираемые представления.
3. Один work хранится в одном YAML-файле.
4. Неизвестные данные остаются неизвестными; LLM не заполняет поля догадками ради полноты.
5. Пользовательский сигнал важнее semantic metadata, внешних метаданных и публичных рейтингов.
6. `unwatched` не является отрицательным сигналом.
7. Reaction, rating, feedback, rewatch, interest и viewing — независимые сигналы.
8. Trait произведения и субъективная viewer reaction — разные понятия.
9. Все semantic terms используют controlled vocabulary.
10. Обычное добавление произведения не имеет права менять schema.
11. Новый vocabulary term не создаётся без поиска существующего canonical term.
12. Immutable IDs не переименовываются; merge/delete выполняются через redirects/tombstones.
13. Сезонная детализация сериалов необязательна.
14. Общая оценка сериала не вычисляется из сезонов и наоборот.
15. Один relation/membership хранится в одном каноническом месте; обратные связи derived.
16. LLM, сайт и CLI используют один validation/write protocol.
17. Ephemeral настроение/ограничения запроса по умолчанию не становятся persistent preferences.
18. Raw signals хранятся рядом с work; агрегированные taste profiles являются derived data.

## 3. Физическая структура

```text
media/
├── AGENTS.md
├── README.md
├── vocabulary.yaml
├── .gitignore
│
├── config/
│   ├── viewers.yaml
│   └── groups.yaml
│
├── preferences/
│   └── explicit/
│       ├── primary.yaml
│       ├── partner.yaml
│       └── couple.yaml          # только если появятся explicit group preferences
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
│   ├── collections/
│   ├── lists/
│   ├── interactions/
│   │   └── 2026-10.jsonl
│   └── tombstones/
│
├── generated/
│   ├── index.jsonl
│   ├── profiles/
│   │   ├── primary.yaml
│   │   ├── partner.yaml
│   │   └── couple.yaml
│   └── database.sqlite          # build artifact, не коммитится
│
└── tools/
    ├── validate.py
    ├── build_index.py
    ├── build_db.py
    └── build_profiles.py
```

### Канонические данные

Source of truth:

- `config/*`;
- `vocabulary.yaml`;
- `preferences/explicit/*`;
- `data/works/*`;
- `data/collections/*`;
- `data/lists/*`;
- `data/interactions/*`;
- `data/tombstones/*`.

### Generated data

`generated/index.jsonl` и `generated/profiles/*.yaml` можно коммитить для удобного чтения LLM через Git, но они всегда считаются derived и должны полностью пересобираться.

`generated/database.sqlite`, embeddings и image cache являются локальными/deployment build artifacts и в Git не коммитятся.

Ни один generated artifact не может быть единственным носителем информации.

## 4. Entity model

### 4.1 Work

`work` — фильм, сериал или мини-сериал.

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
    tmdb:
      media_type: movie
      id: 157336
    imdb: tt0816692
```

`identity.format`: `movie | series | miniseries`.

`identity.medium`: `live_action | animation | hybrid`.

Мультфильм — `movie + animation`; анимационный сериал — `series + animation`.

TMDB movie и TV используют разные пространства ID, поэтому canonical TMDB identity — пара `(media_type, id)`. Для `movie` используется TMDB media type `movie`; для `series/miniseries` — `tv`.

IMDb `tt...` ID глобально уникален в рамках поддерживаемых work entities.

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

Collection поддерживает ту же multi-viewer/group signal model, если есть отзыв о франшизе целиком. Оценка collection не переносится автоматически на members.

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

Collection — логическая/каноническая серия; list — пользовательская организация.

### 4.4 Interaction

Append-only событие истории рекомендаций/выбора.

### 4.5 Viewer / group

Viewer/group — стабильные анонимные IDs. Персональные данные не хранятся.

### 4.6 Tombstone

```yaml
schema_version: 4
id: live-die-repeat-2014
entity_type: tombstone
status: merged
redirect_to: edge-of-tomorrow-2014
```

Redirects не образуют циклов. Старый ID никогда молча не переиспользуется для другой сущности.

## 5. Multi-viewer configuration

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

Никаких имён, возраста, даты рождения и других персональных данных.

Новые viewer/group добавляются только при реальной необходимости. Будущие члены семьи не создаются заранее.

## 6. Viewer signals

Raw signal конкретного зрителя хранится внутри work. Viewer-блок не создаётся без реальных данных.

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

### Viewing

`status`: `unwatched | watched | partial | dropped | forgotten`.

`unwatched` и `dropped` не считаются автоматически отрицательной реакцией.

`progress` необязателен:

```yaml
progress:
  season: 2
  episode: 5
```

### Reaction

`liked | disliked | neutral | mixed | unknown`.

Отсутствие viewer-блока означает отсутствие данных. `unknown` используется только когда явно зафиксированная неизвестность сама полезна.

Reaction и rating независимы и не вычисляются друг из друга.

Если primary передаёт реальное мнение partner («жене понравилось»), это полноценный partner signal. Confidence зависит от уверенности формулировки, а не от того, кто передал мнение.

### Rating

`score`: `1.0..10.0`, шаг `0.5`, либо `null`.

`source`: `explicit | explicit_approx | inferred | none`.

`confidence`: `exact | high | medium | low | none`.

### Feedback

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

### Rewatch

`rewatch.intent`: `none | low | medium | high | unknown`.

Фактическое число просмотров хранится только в `viewing.times_watched`.

### Significant history

Полного event-sourcing мнений нет. `history` необязателен и используется только для значимых изменений реакции/оценки.

## 7. Group signals

Group не является отдельным человеком. Это необязательный сигнал именно о совместном просмотре.

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

Group block создаётся только при реальном group-specific сигнале.

`primary: 7.5`, `partner: liked`, `couple: 9.0` — валидная комбинация.

## 8. Сезоны

`seasons` полностью необязателен. Общей оценки сериала достаточно.

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

Сезон использует те же viewer/group signal semantics, что и work. Пустые season records не создаются ради полноты.

`number` уникален внутри сериала и может быть `0` для specials, если внешний источник использует такую модель.

Общая и сезонные оценки независимы.

## 9. Metadata и enrichment

```yaml
metadata:
  external: {}
  overrides: {}
  semantic: {}
```

### External factual metadata

TMDB — primary metadata provider v4, но schema provider-neutral.

Полезные данные:

- genres;
- runtime;
- original language;
- countries;
- production status;
- spoiler-safe synopsis;
- directors/writers/key cast;
- certifications;
- content warnings;
- external metrics;
- poster/backdrop references.

При добавлении нового work write-layer по возможности автоматически обогащает metadata. Если provider недоступен, сохраняется только достоверно известное.

Provider genres/content labels должны быть нормализованы в canonical vocabulary до записи в semantic/controlled поля; raw provider-specific значения не подменяют canonical terms.

### People references

Отдельные person YAML в v4 не создаются.

```yaml
directors:
  - name: Christopher Nolan
    external_ids:
      tmdb: 525
      imdb: nm0634240
```

### Assets

В Git хранятся только provider references:

```yaml
assets:
  poster:
    provider: tmdb
    path: /...
```

Бинарники и image cache находятся вне canonical Git data.

### External metrics

```yaml
external_metrics:
  imdb:
    score: 8.7
    votes: 2200000
    observed_at: 2026-10-01
```

Публичные рейтинги являются слабым внешним сигналом.

### Persistent manual overrides

Автоматический metadata refresh никогда не затирает manual overrides.

Effective value: `override -> external -> null`.

Override допускается только для разрешённых schema полей.

### Semantic traits

```yaml
semantic:
  traits:
    - term: story.problem_solving
      source: llm_inferred
      confidence: high
```

`source`: `external_source | llm_inferred | user_explicit`.

LLM-inferred trait всегда сохраняет provenance и не становится молча «фактом».

## 10. Controlled vocabulary

Все term IDs namespaced, например:

- `genre.science_fiction`
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

Принципиально:

- `pacing.slow` — свойство work;
- `reaction.pacing_dragging` — реакция viewer;
- `humor.absurd` — стиль юмора;
- `reaction.cringe` — реакция viewer.

Новый term создаётся только если подходящего canonical term нет, это не синоним, различие полезно рекомендациям и понятие применимо более чем к одному произведению.

Изменение/слияние canonical term IDs — отдельная vocabulary migration.

## 11. Relations

### Viewer/group relations

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

Типы: `similar_to | reminds_of | preferred_over`.

`dimensions` используют canonical vocabulary IDs.

Если `preferred_over` записан в work A с `target_id: B`, субъект предпочитает A произведению B. Если предпочтение обратное, relation хранится в B. `direction` не используется.

### Canonical relations

Фактические связи хранятся отдельно:

`sequel | prequel | spinoff | remake | reboot | adaptation`.

Canonical relation и subjective similarity не смешиваются.

## 12. Interest / target state

Interest принадлежит target, а не work глобально.

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

`state`: `unknown | candidate | shortlist | not_interested`.

`not_interested` — устойчивое состояние. «Не сегодня» остаётся ephemeral.

## 13. Explicit preferences и constraints

Постоянные предпочтения, высказанные вне контекста одного work, хранятся по target в `preferences/explicit/*`.

Одноразовые условия вроде «сегодня без фантастики» не сохраняются.

Explicit preference/constraint всегда отделён от derived preference.

## 14. Derived profiles

`generated/profiles/{target}.yaml` строится из:

- explicit preferences/constraints;
- viewer/group signals;
- ratings/reactions/feedback;
- viewing/rewatch evidence;
- relations;
- значимых interaction outcomes.

`couple` не является средним арифметическим `primary` и `partner`: он учитывает оба профиля, explicit group preferences, `group_signals.couple` и историю совместного выбора.

Каждый derived вывод хранит confidence/evidence и может быть полностью пересобран.

## 15. Interaction log

Append-only по месяцам:

```text
media/data/interactions/2026-10.jsonl
```

```json
{"id":"evt-20261001-001","at":"2026-10-01T20:15:00+02:00","work_id":"arrival-2016","target":"couple","type":"recommended"}
{"id":"evt-20261001-002","at":"2026-10-01T20:17:00+02:00","work_id":"arrival-2016","target":"couple","type":"skipped","reason":"not_today"}
```

Event types v4:

- `recommended`
- `selected`
- `skipped`
- `dismissed`
- `added_to_list`
- `removed_from_list`

Это не event-sourcing. Current rating/viewing/feedback хранится в work.

`recommended_count`, `last_recommended_at`, `skipped_count` и другие счётчики derived и не дублируются в canonical work.

Внутренние кандидаты LLM, не показанные пользователю, не логируются.

## 16. Recommendation runtime

```text
ephemeral request
+ target derived profile
+ index/SQLite retrieval
        ↓
30–50 candidates
        ↓
viewing / interest / constraints filters
        ↓
10–20 relevant candidates
        ↓
full YAML only for finalists
        ↓
recommendation
```

`generated/index.jsonl` — компактный retrieval index.

`generated/database.sqlite` — runtime DB для будущего сайта/сложных фильтров, полностью пересобираемая и не коммитимая.

Embeddings — optional future derived layer, не обязательная часть v4.

## 17. Будущий сайт

Будущий сайт — полноценный read/write client, но не source of truth.

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

Сайт читает главным образом SQLite/index/profiles/image cache, но записывает только через общий write-layer.

Сам web UI не входит в текущую реализацию v4.

## 18. Write protocol

Перед записью клиент/agent обязан:

1. определить target;
2. прочитать применимые schema и vocabulary;
3. найти существующий work по TMDB composite ID, IMDb ID, internal ID и title/year;
4. разрешить redirects/tombstones;
5. при создании выполнить metadata enrichment, если provider доступен;
6. не создавать неизвестные schema fields;
7. не создавать vocabulary synonym вместо canonical term;
8. не сохранять ephemeral context как persistent preference;
9. не создавать viewer/group signal без evidence;
10. сохранять explicit/inferred provenance;
11. подготовить весь logical change-set;
12. провалидировать proposed state;
13. выполнить atomic write;
14. создать один Git commit на одну логическую операцию;
15. пересобрать affected generated data.

При ошибке validation canonical state не должен оставаться частично изменённым.

## 19. Deduplication

Порядок проверки:

1. TMDB `(media_type, id)`;
2. IMDb ID;
3. internal immutable ID;
4. original/alternate title + year;
5. fuzzy candidate search.

TMDB numeric ID без `media_type` не считается глобальным dedup key.

При неоднозначности identity не угадывается.

## 20. Data precedence

От высшего к низшему:

1. новое явное утверждение пользователя;
2. persistent manual override;
3. существующий explicit viewer/group signal конкретного work;
4. explicit persistent preference/constraint;
5. inferred viewer/group signal;
6. derived profile;
7. semantic metadata;
8. factual external metadata;
9. public rating/popularity.

Нижний уровень не перезаписывает верхний молча. Specific explicit signal конкретного work может естественно отличаться от общего explicit preference без признания данных конфликтными.

## 21. Validation

`validate.py` проверяет как минимум:

- соответствие YAML/JSONL schema;
- закрытые объекты через `additionalProperties: false`, где уместно;
- уникальность active internal IDs;
- уникальность ненулевых IMDb IDs;
- уникальность TMDB composite keys `(media_type, id)`;
- redirects без циклов;
- существование work/collection/list/target references;
- корректность group members;
- существование canonical vocabulary terms;
- запрет aliases вместо term IDs;
- уникальность season numbers и допустимость season `0`;
- seasons только у `series/miniseries`;
- rating `1..10` с шагом `0.5`;
- согласованность score/source/confidence;
- отсутствие бессмысленных self-relations;
- корректность `preferred_over`;
- валидность canonical relations;
- interaction IDs/timestamps/types;
- существование list members;
- допустимость metadata overrides;
- отсутствие canonical зависимости от generated-only данных.

После validation build pipeline должен уметь с нуля пересобрать index, SQLite и derived profiles.

## 22. AGENTS.md contract

Минимальный operational contract:

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

1. canonical directory structure;
2. config `primary`, `partner`, `couple`;
3. JSON Schemas;
4. initial controlled vocabulary;
5. миграция текущей movie-базы без потери пользовательского сигнала;
6. один YAML на work;
7. collections;
8. multi-viewer/group-compatible signals;
9. explicit preference representation;
10. validator;
11. generated index;
12. SQLite builder;
13. минимально достаточный derived profile builder;
14. README/AGENTS;
15. удаление старых конкурирующих source-of-truth файлов только после успешной validation.

Не входят:

- web UI;
- production API/service;
- authentication;
- background metadata refresh;
- обязательные embeddings/vector DB;
- полноценный person catalog;
- полный event-sourcing.

Эти слои добавляются поверх v4 без изменения canonical model.

## 24. Migration rules

- текущий пользователь -> `primary`;
- partner signal переносится только там, где он реально был сообщён;
- отсутствие просмотра не становится негативом;
- ratings/comments сохраняются;
- inferred ratings сохраняют provenance;
- collection rating не размножается по members;
- seasons не создаются без сезонной информации;
- сомнительные factual metadata не выдумываются;
- external IDs добавляются только при надёжном match;
- старые source-of-truth файлы удаляются только после успешной validation новой структуры.

## 25. Acceptance criteria

v4 реализована, когда:

1. текущие пользовательские данные перенесены без потери смысла;
2. `primary`, `partner`, `couple` поддерживаются без персональных данных;
3. work/collection/list/interaction/tombstone schemas валидируются;
4. vocabulary refs проверяются автоматически;
5. schema drift при обычном data entry запрещён;
6. `validate.py` проходит на всей canonical базе;
7. index, SQLite и derived profiles пересобираются из canonical data;
8. old v2 files больше не конкурируют как source of truth;
9. можно добавить work естественным языком без создания новой структуры;
10. можно сохранить только `partner: liked`, а позже дополнить rating/feedback;
11. можно оценить сериал целиком без seasons и позже добавить season-specific signals;
12. можно рекомендовать для `primary`, `partner` или `couple`;
13. ephemeral request context не загрязняет persistent profile;
14. будущий сайт сможет читать generated runtime и писать через общий protocol без смены canonical model;
15. TMDB movie/TV ID collision не создаёт ложную дедупликацию;
16. удаление локальной SQLite не приводит к потере информации.
