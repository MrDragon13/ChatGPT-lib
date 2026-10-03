# Documentation System Reorganization — design

Дата: 2026-10-03  
Статус: **approved conversational design, written spec awaiting review**  
База: `main@6898f208dddfbedd724e5b212c65319a02e0f61d`  
Область: repository documentation architecture, navigation, operational contracts, historical specs/plans, documentation drift prevention

## 1. Цель

Превратить документацию ChatGPT-lib из набора исторически наслоившихся README, status, agent contracts, product/design notes и implementation specs в цельную систему, где читатель быстро понимает:

1. что проект делает сейчас;
2. как им пользоваться;
3. как он устроен;
4. как безопасно его менять и обслуживать;
5. какие документы являются текущим контрактом, а какие — историей решений.

Документация должна быть удобна одновременно для владельца проекта, нового разработчика и LLM/agent workflow. Основной критерий успеха — для понимания текущего состояния не требуется читать цепочку старых design specs и handoff-файлов.

## 2. Проблема текущей структуры

После v5/v5.1 в репозитории есть несколько полезных, но пересекающихся слоёв документации:

- root `README.md` одновременно является landing page и вручную перечисляет несколько «актуальных» specs;
- `media/README.md` одновременно выполняет роли overview, architecture reference, command reference, operational runbook и agent guide;
- `media/AGENTS.md` содержит нормативные правила, но из-за объёма частично дублирует объяснительную документацию;
- `media/V5_STATUS.md` сочетает текущее состояние, историю пилота, development checkpoints и resume instructions;
- `PRODUCT.md` и `DESIGN.md` описывают главным образом web surface, но из расположения в корне это неочевидно;
- `docs/superpowers/specs/` и `docs/superpowers/plans/` содержат ценную историю проектирования, однако не имеют ясной границы между historical decision record и current documentation;
- списки операций, manifest versions, validation commands и архитектурные правила повторяются в нескольких местах и могут расходиться после следующих релизов.

Проблема не в количестве Markdown-файлов само по себе, а в отсутствии явных ролей и ownership каждого документа.

## 3. Выбранный подход

Используем **living documentation layer + historical design archive**.

Не переносим и не переписываем массово существующие `docs/superpowers/specs/` и `docs/superpowers/plans/`. Они остаются immutable-ish историческими артефактами: объясняют, почему решения были приняты, но не определяют текущее поведение системы.

Текущее устройство и эксплуатация описываются в небольшой иерархии living docs под `docs/`.

Это предпочтительнее двух альтернатив:

- только подчистить README — слишком быстро снова создаст дубли и drift;
- физически архивировать/переименовать все старые specs — создаст большой churn, сломанные ссылки и мало практической пользы.

## 4. Целевая структура

```text
README.md                     # короткая landing page проекта
AGENTS.md                     # компактный repository-level agent router
PRODUCT.md                    # web-product reference; scope явно обозначен
DESIGN.md                     # web visual/design-system reference; scope явно обозначен

docs/
  README.md                   # карта всей документации

  architecture/
    overview.md               # система целиком и границы компонентов
    media-model.md            # canonical/derived model, targets, evidence, similarity
    intelligence.md           # taste, recommendations, candidate assessment
    write-pipeline.md         # typed commands -> PR -> validation -> merge/deploy
    web-and-broker.md         # Pages, manifest, broker, security boundary

  guides/
    media-usage.md            # пользовательские сценарии
    development.md            # как менять code/schema/architecture
    operations.md             # validate/rebuild/doctor/deploy/recovery

  reference/
    media-commands.md         # read/write/maintenance operation catalog
    repository-layout.md      # назначение основных директорий
    invariants.md             # короткий MUST / MUST NOT contract
    terminology.md            # canonical/derived/target/evidence/etc.

  status/
    current.md                # короткое текущее состояние и known limitations

  superpowers/
    specs/                    # historical design decisions
    plans/                    # historical implementation plans
```

Точный объём каждого living-doc файла определяется при реализации, но ответственность файлов из этой структуры фиксирована этим design.

## 5. Модель источников истины

Линейная «один файл главнее всех» модель здесь недостаточна, поэтому authority разделяется по типу знания.

### 5.1 Implemented behavior

Для фактически реализованного поведения приоритет имеют:

1. runtime code;
2. JSON schemas / controlled vocabulary / workflow configuration;
3. tests как executable contracts;
4. living architecture/reference docs.

Если living doc расходится с реализованным контрактом, это documentation bug.

### 5.2 Agent operating policy

Для того, **как агент обязан работать с репозиторием**, нормативны:

1. root `AGENTS.md` как router;
2. subsystem `media/AGENTS.md` как operating contract;
3. typed command schemas и path/workflow policies.

Living docs объясняют эти правила, но не должны дублировать все imperative instructions слово в слово.

### 5.3 Historical rationale

`docs/superpowers/specs/` и `plans/` отвечают на вопрос «почему и как мы пришли к текущему решению». Они не переопределяют код, schemas, AGENTS или living docs после завершения соответствующего изменения.

Каждый docs index должен явно показывать эту границу.

## 6. Навигационный UX

### 6.1 Для человека

Root `README.md` должен читаться за 2–3 минуты и вести по четырём основным маршрутам:

```text
README
  -> понять проект         -> docs/README.md
  -> пользоваться media   -> docs/guides/media-usage.md
  -> разрабатывать        -> docs/guides/development.md
  -> понять архитектуру   -> docs/architecture/overview.md
```

Landing page не перечисляет вручную каждый актуальный spec и не становится changelog.

### 6.2 Для агента

```text
AGENTS.md
  -> media/AGENTS.md
  -> только релевантный living reference
  -> schema/code по выбранному route
```

Agent bootstrap не должен требовать чтения длинного исторического status или нескольких design specs перед обычной media operation.

## 7. Роли существующих документов

### 7.1 Root `README.md`

Становится кратким проектным landing page:

- purpose;
- основные capabilities текущей системы;
- 8–10 строк architecture summary;
- основные entry points;
- link на `docs/README.md`.

Из него удаляются ручные списки «актуальных» и «исторических» design specs.

### 7.2 Root `AGENTS.md`

Остаётся коротким router и не разрастается в subsystem manual. Он указывает на `media/AGENTS.md`, relevant living docs и правило чтения historical specs только при необходимости.

### 7.3 `media/README.md`

Сильно сокращается. Его роль — локальный subsystem landing page:

- что находится под `media/`;
- основные canonical/derived boundaries;
- ссылки на guides/reference/architecture;
- минимальный CLI quickstart.

Подробный command catalog, recommendation semantics, pipeline internals и web architecture уходят в тематические living docs.

### 7.4 `media/AGENTS.md`

Сохраняет нормативный operating contract:

- intent routing;
- mutation/read boundaries;
- evidence hygiene;
- hard guardrails;
- required validation/merge discipline.

Объяснительные длинные sections, которые можно безопасно заменить ссылками на living docs без потери imperative semantics, сокращаются. При сомнении правило остаётся в `AGENTS.md`: correctness важнее краткости.

### 7.5 `media/V5_STATUS.md`

Перестаёт быть накопительным development diary.

Для обратной совместимости файл сохраняется, но становится маленьким compatibility/router document:

- текущая release line;
- ссылка на `docs/status/current.md`;
- указание, что historical v5 pilot details находятся в specs/PR history;
- safe resume instruction: сначала current `main` + active PR, затем current status.

Новый authoritative human-readable current status — `docs/status/current.md`.

### 7.6 `PRODUCT.md` и `DESIGN.md`

Не перемещаются в первой итерации, чтобы не создавать лишний churn и не ломать tooling/reference paths.

В них и в docs index явно фиксируется scope:

- `PRODUCT.md` — current media-web product brief;
- `DESIGN.md` — current media-web visual/design-system contract.

Они не считаются описанием architecture всего repository.

### 7.7 `docs/superpowers/*`

Остаются по текущим путям.

Добавляется индекс/объяснение их роли через `docs/README.md`; массовое редактирование исторических design docs не выполняется. Старые status markers вроде `awaiting review` сохраняются как historical state и не должны интерпретироваться как current project status.

## 8. Living architecture docs

### `architecture/overview.md`

Должен отвечать на вопросы:

- какие крупные компоненты есть;
- где canonical source of truth;
- что derived;
- как media, web, broker и GitHub Actions связаны;
- где проходят security/write boundaries.

Это основной документ для понимания системы без чтения implementation history.

### `architecture/media-model.md`

Содержит current domain model:

- works/collections/lists/interactions/relations;
- targets `primary`, `partner`, `couple`;
- explicit vs inferred evidence;
- semantic fingerprints;
- explicit similarity + external WorkRef + reconciliation;
- canonical vs generated data.

### `architecture/intelligence.md`

Описывает reasoning model без fake scoring:

- taste context;
- evidence hierarchy;
- internal/external recommendation routing;
- explicit similarity as hint/evidence, not preference;
- candidate assessment;
- provenance/explainability;
- couple disagreement semantics.

### `architecture/write-pipeline.md`

Описывает end-to-end deterministic mutation lifecycle:

natural language -> strict typed request -> operation branch/PR -> deterministic transaction -> validation/rebuild -> exact-head check -> guarded merge -> exact-merge Pages publish.

Отдельно показывает manual/developer route и maintenance exceptions.

### `architecture/web-and-broker.md`

Описывает:

- static Pages/read-model boundary;
- manifest versioning;
- broker responsibility;
- browser credential restrictions;
- typed write reuse;
- product/design links.

## 9. Guides

### `guides/media-usage.md`

User-oriented, без GitHub implementation noise. Сценарии:

- добавить просмотр/feedback;
- исправить оценку/feedback;
- отметить интерес;
- спросить рекомендацию;
- спросить «понравится ли мне X?»;
- записать/remove similarity;
- partner/couple context.

### `guides/development.md`

Developer-oriented:

- старт с current main;
- ветки/PR;
- когда typed operation path, а когда manual developer change;
- TDD/validation expectations;
- schema/vocabulary evolution;
- docs update requirement.

### `guides/operations.md`

Runbook:

- install/validate/test/rebuild/doctor;
- web checks;
- provider maintenance;
- Pages verification;
- recovery from stale generated artifacts / interrupted work;
- authoritative CI gates.

## 10. Reference layer

### `reference/media-commands.md`

Единый compact catalog operations с категорией, mutation/read-only status, canonical side effects и auto-merge eligibility.

Он не копирует полные JSON schemas — вместо этого ссылается на `media/commands/schemas/`.

### `reference/repository-layout.md`

Карта корневых директорий и ключевых media/web/broker paths. Должна помогать быстро найти ownership кода/данных/docs.

### `reference/invariants.md`

Короткий checklist из наиболее важных cross-system правил, например:

- Git/YAML canonical;
- generated data never hand-edited;
- normal mutations via typed commands;
- external recommendation/similarity mention does not implicitly create work;
- inferred output is not independent evidence;
- similarity is not preference;
- target never silently changes;
- browser never receives write/provider/model secrets;
- unknown semantic terms are not invented.

### `reference/terminology.md`

Стабильные определения терминов, чтобы README/specs/code reviews использовали одинаковый язык.

## 11. Current status policy

`docs/status/current.md` должен быть коротким и обновляемым.

Разрешено:

- текущая release/capability line;
- implemented capabilities;
- known limitations;
- active architectural follow-ups;
- последняя подтверждённая verification baseline в человекочитаемой форме, если полезно.

Запрещено превращать его в вечный development ledger:

- временные task checklists;
- длинная история RED/GREEN run numbers;
- stale feature-branch head SHA;
- подробные narrative pilot logs.

Транзитный development progress живёт в active PR body/comments. После merge в current status переносится только устойчивый результат и known limitations.

## 12. Drift prevention

Реорганизация должна добавить executable documentation contracts.

Минимальный набор автоматических проверок:

1. ключевые relative Markdown links из root/living docs разрешаются в существующие repository paths;
2. root README/media README не объявляют historical dated specs «current architecture»;
3. documented media operation names синхронизированы с command parser/registry либо генерируются/проверяются из одного source;
4. documented current web manifest version совпадает с exporter/schema constant;
5. key verification commands в operations guide соответствуют реально существующим CLI commands;
6. compatibility routers (`media/V5_STATUS.md`, root `AGENTS.md`) указывают на существующие living docs;
7. current status не содержит явно запрещённых transient markers (`Task N in progress`, feature-branch head SHA и аналогичные handoff leftovers).

Тесты должны проверять контракт, а не exact prose, чтобы документацию можно было улучшать без brittle string snapshots.

## 13. Migration strategy

Реорганизация выполняется инкрементально в одном documentation PR.

Рекомендуемый порядок:

1. добавить docs index и living skeleton/content;
2. добавить contract tests;
3. обновить root README/AGENTS routes;
4. сократить и перенаправить `media/README.md`;
5. аккуратно сократить `media/AGENTS.md`, сохраняя normative guardrails;
6. заменить `media/V5_STATUS.md` compatibility router-ом и перенести устойчивое current состояние в `docs/status/current.md`;
7. обозначить scope `PRODUCT.md`/`DESIGN.md`;
8. выполнить link/reference audit;
9. полный project + web verification.

Старые specs/plans не перемещаются и не переписываются массово.

## 14. Совместимость

Изменение не должно менять runtime media behavior, schemas, canonical data, recommendation semantics или website behavior.

Сохраняются существующие известные entry paths:

- root `README.md`;
- root `AGENTS.md`;
- `media/README.md`;
- `media/AGENTS.md`;
- `media/START_PROMPT.md`;
- `media/V5_STATUS.md`.

Таким образом bookmarks/agent bootstrap не ломаются; старые paths становятся routers в новую систему там, где это необходимо.

Любая обнаруженная при docs-аудите реальная runtime проблема выходит за scope и оформляется отдельно, если только она не блокирует правдивость документации.

## 15. Non-goals

В эту работу не входят:

- изменение media schemas/domain behavior;
- новый recommendation/taste algorithm;
- изменение website UX;
- перенос `PRODUCT.md`/`DESIGN.md`;
- массовое переименование historical specs/plans;
- создание внешнего docs-сайта или MkDocs/Docusaurus;
- auto-generation всей документации из кода;
- переписывание commit/PR history.

## 16. Acceptance criteria

Работа считается завершённой, когда:

1. новый читатель через root README за один переход находит нужный learning/usage/development/architecture route;
2. `docs/README.md` объясняет роли living docs, AGENTS contracts и historical specs/plans;
3. current architecture v5.1 описана без необходимости читать dated specs;
4. `media/README.md` и `media/V5_STATUS.md` больше не являются накопительными монолитами;
5. `media/AGENTS.md` остаётся достаточным normative contract, но ссылается на living explanation вместо безопасно удаляемого дублирования;
6. PRODUCT/DESIGN scope однозначно обозначен как media-web;
7. explicit similarity и candidate assessment отражены в current architecture/reference docs;
8. docs contract tests предотвращают наиболее вероятный drift;
9. полный existing project verification остаётся GREEN;
10. historical specs/plans сохранены и ясно маркированы как historical rationale, а не current truth.

## 17. Review focus

При review особенно проверить:

- не потерялись ли imperative guardrails при сокращении `media/AGENTS.md`;
- не возник ли новый duplication между architecture/reference/guides;
- можно ли понять current v5.1 без historical specs;
- не делают ли docs tests prose слишком жёстким;
- не сломаны ли старые entry paths;
- отражена ли similarity как recommendation evidence/hint, но не preference;
- остаётся ли PR/status ledger отдельным от durable current documentation.
