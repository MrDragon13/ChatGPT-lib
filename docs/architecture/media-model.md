# Media domain model

Этот документ описывает текущую модель данных media subsystem: что является canonical, что derived, как разделяются viewers/targets и как связаны feedback, taste evidence, semantic knowledge и work similarity.

## Canonical data

Основные canonical paths:

- `media/data/works/` — одно произведение на YAML-файл;
- `media/data/collections/` — франшизы/серии и membership;
- `media/data/lists/` — пользовательские списки по target;
- `media/data/interactions/` — append-only recommendation interaction events;
- `media/data/relations/similarity/` — explicit target-specific similarity assertions;
- `media/data/tombstones/` — redirects для merged IDs;
- `media/preferences/explicit/` — устойчивые явно заявленные предпочтения/ограничения;
- `media/preferences/inferred/` — evidence-backed taste hypotheses;
- `media/config/` — viewer/group configuration;
- `media/vocabulary.yaml` — controlled semantic vocabulary.

Generated files под `media/generated/` не являются canonical и не должны редактироваться вручную как источник новых фактов.

## Work

Canonical work хранит identity, metadata, user/group signals, provenance и semantic knowledge. Work ID стабилен: identity merge/reconciliation не означает произвольную замену ID без explicit migration policy.

Произведение может существовать без viewing feedback. Viewing, rating, reaction, free-text feedback, rewatch/interest и recommendation interaction — разные сигналы; отсутствие одного не означает значение другого.

## Targets

Система использует три основных target-контекста:

- `primary` — основной пользователь;
- `partner` — отдельный viewer context;
- `couple` — group target для совместного reasoning.

`couple` не является скрытым средним двух пользователей. Если evidence конфликтует, read model должен уметь показать disagreement. Subjective state не переносится между `primary`, `partner` и `couple` автоматически.

## Explicit и inferred evidence

**Explicit evidence** — то, что пользователь сказал/оценил напрямую: rating, reaction, feedback, explicit preference, interest или similarity assertion.

**Inferred evidence** — evidence-backed hypothesis, построенная из независимых пользовательских сигналов. Inferred output не считается independent evidence для другого inferred output: вывод не может сам себя подтверждать через цепочку повторных выводов.

Один rating сам по себе не должен автоматически превращать все свойства фильма в сильную taste preference.

## Semantic fingerprint

Semantic fingerprint описывает произведение, а не зрителя. Traits используют controlled vocabulary и provenance/confidence. Неизвестный semantic term не придумывается автоматически во время обычной записи данных; vocabulary evolution — отдельная developer/architecture задача.

## WorkRef

Некоторые операции должны ссылаться на произведение, которое ещё не является canonical work. Для этого используется `WorkRef`-подобная модель:

- canonical reference — локальный `work_id`;
- external reference — stable provider identity (`tmdb`, `imdb` и т. п.) плюс display snapshot вроде title/year.

External mention не означает автоматическое добавление work в медиатеку и не создаёт viewing/rating/reaction/interest state.

## Explicit work similarity

Similarity хранится отдельно от factual `work.canonical_relations`, потому что она:

- субъективна;
- target-specific;
- undirected;
- может связывать canonical и external endpoints.

Одна logical relation определяется как `(target, unordered pair)`. Поэтому A↔B и B↔A — одна assertion. Повторная запись делает upsert текущего мнения; remove удаляет эту же связь независимо от порядка endpoints.

Причины similarity могут содержать существующие vocabulary terms и optional note. LLM-derived semantic similarity остаётся derived knowledge и не становится canonical assertion без явного подтверждения пользователя.

## Reconciliation external → canonical

Когда внешний endpoint позже появляется как реальный canonical work с той же stable provider identity, выполняется deterministic **reconciliation**:

1. external endpoint сопоставляется canonical `work_id`;
2. relation переписывается на canonical reference;
3. self-link после identity collapse удаляется;
4. совпавшие relations дедуплицируются по утверждённой deterministic policy;
5. пользовательские viewing/taste сигналы не создаются побочно.

Reconciliation является data-normalization step, а не recommendation inference.

## Derived data

Из canonical state строятся:

- retrieval index;
- deterministic profiles/affinities;
- taste context;
- recommendation context;
- runtime SQLite database;
- versioned web manifest;
- bidirectional web projection explicit similarity.

Derived projection может быть удобнее canonical representation. Например, одна undirected canonical similarity relation может появляться на обеих локальных work pages. Это не дублирует canonical assertion.

## Инварианты

- canonical data нельзя заменять generated state;
- unknown лучше guessed identity;
- target нельзя менять молча;
- inferred output не является independent evidence;
- semantic fingerprint описывает work, не viewer reaction;
- similarity является evidence/hint, но не preference сама по себе;
- external endpoint не создаёт canonical work автоматически;
- provider outage не должен разрушать уже сохранённую stable external identity.
