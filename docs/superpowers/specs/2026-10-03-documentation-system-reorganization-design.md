# Documentation System Reorganization — design

Дата: 2026-10-03  
Статус: **approved conversational design, written spec awaiting review**  
База: `main@6898f208dddfbedd724e5b212c65319a02e0f61d`  
Область: repository documentation architecture, navigation, operational contracts, historical specs/plans, drift prevention

## 1. Цель

Превратить документацию ChatGPT-lib из набора исторически наслоившихся README, status, agent contracts, product/design notes и implementation specs в цельную систему, где человек или агент быстро понимает:

1. что проект делает сейчас;
2. как им пользоваться;
3. как он устроен;
4. как безопасно его менять и обслуживать;
5. какие документы являются текущим контрактом, а какие — историей решений.

Критерий успеха: для понимания текущей системы не требуется читать цепочку dated design specs и development handoff-файлов.

## 2. Текущая проблема

После v5/v5.1 полезная информация распределена по нескольким пересекающимся слоям:

- root `README.md` одновременно landing page и ручной список «актуальных» specs;
- `media/README.md` одновременно overview, architecture reference, command reference, runbook и agent guide;
- `media/AGENTS.md` нормативен, но частично дублирует объяснительную документацию;
- `media/V5_STATUS.md` сочетает current state, pilot history, development checkpoints и resume notes;
- `PRODUCT.md` и `DESIGN.md` в основном относятся к media web, но из root location это неочевидно;
- `docs/superpowers/specs/` и `plans/` содержат ценную историю, но рядом с current docs выглядят как возможный source of truth;
- command lists, manifest version, verification commands и архитектурные правила повторяются в нескольких местах и могут расходиться.

Проблема — не количество файлов само по себе, а отсутствие однозначных ролей, ownership и update policy.

## 3. Выбранный подход

Используем **living documentation layer + historical design archive**.

- Текущее устройство, usage и operations описываются в небольшом наборе living docs под `docs/`.
- `docs/superpowers/specs/` и `docs/superpowers/plans/` остаются по текущим путям и сохраняют historical rationale.
- Мы не делаем массовое переименование/архивирование старых specs: это создаст churn и сломанные ссылки без достаточной пользы.
- Root/media entry files становятся короткими routers/landing pages вместо монолитов.

## 4. Целевая структура

```text
README.md                     # короткая landing page проекта
AGENTS.md                     # repository-level agent router
PRODUCT.md                    # media-web product reference
DESIGN.md                     # media-web visual/design-system reference

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
    development.md            # developer workflow и evolution rules
    operations.md             # validate/rebuild/doctor/deploy/recovery

  reference/
    media-commands.md         # operation catalog
    repository-layout.md      # назначение директорий
    invariants.md             # MUST / MUST NOT
    terminology.md            # canonical/derived/target/evidence/etc.

  status/
    current.md                # короткий current state + known limitations

  superpowers/
    specs/                    # historical design decisions
    plans/                    # historical implementation plans
```

Роли файлов являются частью design contract; конкретная длина разделов — implementation detail.

## 5. Модель источников истины

Один линейный priority list недостаточен, поэтому authority разделяется по типу знания.

### 5.1 Реализованное поведение

Для того, **что система реально делает**, приоритет:

1. runtime code;
2. JSON schemas, vocabulary, workflow configuration;
3. tests как executable contracts;
4. living architecture/reference docs.

Если living doc расходится с реализованным контрактом, это documentation bug.

### 5.2 Agent operating policy

Для того, **как агент обязан действовать**, нормативны:

1. root `AGENTS.md` как router;
2. `media/AGENTS.md` как subsystem operating contract;
3. typed command schemas и path/workflow policies.

Living docs объясняют эти правила, но не должны копировать imperative guardrails слово в слово без необходимости.

### 5.3 Historical rationale

`docs/superpowers/specs/` и `plans/` отвечают на вопрос «почему мы пришли к этому решению». После реализации они не переопределяют code/schemas/AGENTS/living docs.

## 6. Навигационный UX

### Для человека

Root `README.md` читается за 2–3 минуты и ведёт по четырём маршрутам:

```text
README
  -> понять проект       -> docs/README.md
  -> пользоваться media -> docs/guides/media-usage.md
  -> разрабатывать      -> docs/guides/development.md
  -> понять архитектуру -> docs/architecture/overview.md
```

README не является changelog и не перечисляет вручную каждый dated spec.

### Для агента

```text
AGENTS.md
  -> media/AGENTS.md
  -> только нужный living reference
  -> schema/code по выбранному route
```

Обычная media operation не должна требовать предварительного чтения длинного historical status и нескольких design specs.

## 7. Роли существующих entry documents

### `README.md`

Короткий project landing page:

- purpose;
- основные current capabilities;
- compact architecture summary;
- entry links;
- ссылка на `docs/README.md`.

Ручные списки current/historical specs удаляются.

### `AGENTS.md`

Остаётся коротким router. Не дублирует subsystem manual.

### `media/README.md`

Становится media subsystem landing page:

- что хранится под `media/`;
- canonical/derived boundary;
- links на guides/reference/architecture;
- минимальный CLI quickstart.

Подробные recommendation semantics, operation catalog, pipeline internals и web architecture уходят в тематические living docs.

### `media/AGENTS.md`

Сохраняет нормативные вещи:

- intent routing;
- mutation/read boundaries;
- evidence hygiene;
- hard guardrails;
- verification/merge discipline.

Объяснительное дублирование сокращается только там, где ссылка на living doc не ослабляет imperative semantics. При сомнении правило остаётся в `AGENTS.md`.

### `media/V5_STATUS.md`

Остаётся как compatibility path, но становится маленьким router:

- current release line;
- ссылка на `docs/status/current.md`;
- указание, что подробная v5/v5.1 development history находится в specs/PR history;
- resume rule: проверить current `main` + active PR, затем current status.

Durable current status живёт в `docs/status/current.md`.

### `PRODUCT.md` и `DESIGN.md`

Не перемещаются в первой итерации. Их scope явно маркируется:

- `PRODUCT.md` — media-web product brief;
- `DESIGN.md` — media-web visual/design-system contract.

Они не считаются architecture overview всего repository.

### `docs/superpowers/*`

Пути сохраняются. `docs/README.md` объясняет, что это historical design/implementation record. Старые markers вроде `awaiting review` трактуются как историческое состояние документа, а не current project status.

## 8. Living architecture layer

### `architecture/overview.md`

Объясняет крупные компоненты, canonical source of truth, derived layers, media/web/broker/GitHub Actions связи и security/write boundaries.

### `architecture/media-model.md`

Фиксирует current domain model:

- works/collections/lists/interactions/relations;
- targets `primary`, `partner`, `couple`;
- explicit vs inferred evidence;
- semantic fingerprints;
- explicit work similarity;
- external WorkRef + reconciliation;
- canonical vs generated data.

### `architecture/intelligence.md`

Описывает:

- taste context;
- evidence hierarchy;
- internal/external recommendation routing;
- explicit similarity как hint/evidence, но не preference;
- candidate assessment;
- provenance/explainability;
- couple disagreement semantics;
- отсутствие fake precise probability/opaque match score.

### `architecture/write-pipeline.md`

End-to-end lifecycle:

```text
natural language
-> strict typed request
-> operation branch / PR
-> deterministic transaction
-> validation + scoped rebuild
-> exact-head gate
-> guarded merge
-> exact-merge Pages publish
```

Также описывает manual/developer route и maintenance exceptions.

### `architecture/web-and-broker.md`

Фиксирует static Pages/read-model boundary, manifest versioning, broker responsibility, credential restrictions и reuse typed writes.

## 9. Guides

### `guides/media-usage.md`

User-facing scenarios без GitHub implementation noise:

- просмотр + feedback;
- исправление rating/reaction/feedback;
- interest;
- recommendations;
- «понравится ли мне X?»;
- set/remove similarity;
- partner/couple context.

### `guides/development.md`

Developer workflow:

- current main first;
- branch/PR flow;
- typed operation vs manual developer route;
- TDD/validation expectations;
- schema/vocabulary evolution;
- обязательное обновление соответствующих living docs.

### `guides/operations.md`

Runbook:

- install/test/validate/rebuild/doctor;
- web checks;
- metadata maintenance;
- Pages verification;
- stale generated artifacts;
- interrupted work recovery;
- authoritative CI gates.

## 10. Reference layer

### `reference/media-commands.md`

Compact catalog operations: category, read/write status, side effects и auto-merge eligibility. Полные payload contracts не копируются — источник полей остаётся `media/commands/schemas/`.

### `reference/repository-layout.md`

Карта repository ownership: root/media/web/broker/docs/workflows/generated/canonical paths.

### `reference/invariants.md`

Короткий cross-system MUST/MUST NOT list, включая:

- Git/YAML canonical;
- generated data never hand-edited;
- normal mutations via typed commands;
- external mention/recommendation/similarity does not implicitly create a work;
- inferred output is not independent evidence;
- similarity is not preference;
- target never silently changes;
- browser never receives repository/provider/model secrets;
- unknown vocabulary terms are not invented.

### `reference/terminology.md`

Единые определения терминов, используемых в docs, code review и agent reasoning.

## 11. Current status policy

`docs/status/current.md` короткий и durable.

Разрешено:

- current release/capability line;
- implemented capabilities;
- known limitations;
- active architectural follow-ups;
- полезная стабильная verification baseline.

Не допускается превращение status в development ledger:

- temporary task checklist;
- длинная история RED/GREEN run numbers;
- stale feature-branch head SHA;
- narrative pilot diary.

Транзитный progress живёт в active PR body/comments. После merge в current status переносится только устойчивый результат.

## 12. Language policy

Чтобы документация была последовательной, но не ломала существующий agent workflow:

- human-facing living docs и root/media README — преимущественно на русском;
- code identifiers, operation names, schema fields и canonical terms сохраняются в исходном English spelling;
- `AGENTS.md` может оставаться на английском как machine/agent-oriented operating contract;
- `PRODUCT.md`/`DESIGN.md` сохраняют текущий язык в этой итерации;
- один документ не должен бессистемно переключаться между русским и английским в обычном prose, кроме технических идентификаторов и коротких established terms.

## 13. Documentation ownership / update matrix

Каждый тип изменения обязан обновлять только релевантные living docs, а не весь набор.

| Изменение | Обязательные docs-кандидаты |
| --- | --- |
| новый/изменённый typed operation | `reference/media-commands.md`; при semantic impact — соответствующий architecture guide |
| schema/domain invariant | `architecture/media-model.md` и/или `reference/invariants.md` |
| recommendation/taste/assessment semantics | `architecture/intelligence.md`; user-visible behavior — `guides/media-usage.md` |
| write/CI/auto-merge pipeline | `architecture/write-pipeline.md`, `guides/operations.md` |
| manifest/broker/security boundary | `architecture/web-and-broker.md`; при product impact — `PRODUCT.md` |
| repository path/layout change | `reference/repository-layout.md` |
| visual web design rule | `DESIGN.md` |
| current limitation/release capability | `status/current.md` |
| architectural rationale | новый dated `docs/superpowers/specs/...`; после реализации current behavior также отражается в living docs |

PR review должен рассматривать missing required docs update как обычный regression, а не optional polish.

## 14. Drift prevention

Добавляются executable documentation contracts. Минимум:

1. ключевые relative links из root/living docs разрешаются в существующие repository paths;
2. root/media README не объявляют historical dated specs «current architecture»;
3. documented media operation names синхронизированы с parser/registry;
4. documented current manifest version совпадает с exporter/schema constant;
5. operations guide содержит реально существующие CLI commands;
6. compatibility routers указывают на существующие living docs;
7. `status/current.md` не содержит запрещённые transient handoff markers.

Тесты проверяют contracts/structure, а не exact prose snapshots.

## 15. Migration strategy

Один documentation PR, инкрементально:

1. добавить docs index + living docs;
2. добавить docs contract tests;
3. обновить root README/AGENTS routes;
4. сократить и перенаправить `media/README.md`;
5. аккуратно сократить `media/AGENTS.md`, сохранив нормативные guardrails;
6. превратить `media/V5_STATUS.md` в compatibility router и создать `docs/status/current.md`;
7. обозначить scope `PRODUCT.md`/`DESIGN.md`;
8. link/reference audit;
9. полный project + web verification.

Historical specs/plans не перемещаются и не переписываются массово.

## 16. Совместимость и non-goals

Сохраняются существующие entry paths:

- `README.md`;
- `AGENTS.md`;
- `media/README.md`;
- `media/AGENTS.md`;
- `media/START_PROMPT.md`;
- `media/V5_STATUS.md`.

Реорганизация не должна менять runtime media behavior, schemas, canonical data, recommendation semantics или website behavior.

Не входят в scope:

- новый recommendation/taste algorithm;
- schema/domain changes;
- website UX redesign;
- перенос `PRODUCT.md`/`DESIGN.md`;
- массовое переименование historical specs/plans;
- MkDocs/Docusaurus/внешний docs-сайт;
- auto-generation всей документации из кода;
- переписывание Git/PR history.

Если audit обнаруживает реальную runtime проблему, она оформляется отдельно, если только не блокирует правдивость документации.

## 17. Acceptance criteria

Работа завершена, когда:

1. новый читатель через root README за один переход находит learning/usage/development/architecture route;
2. `docs/README.md` однозначно объясняет living docs, AGENTS contracts и historical specs/plans;
3. current v5.1 architecture можно понять без dated specs;
4. `media/README.md` и `media/V5_STATUS.md` перестают быть накопительными монолитами;
5. `media/AGENTS.md` остаётся достаточным normative contract после сокращения дублирующего explanation;
6. `PRODUCT.md`/`DESIGN.md` однозначно scoped как media-web;
7. similarity и candidate assessment отражены в current architecture/reference docs;
8. update matrix делает ownership будущих docs очевидным;
9. docs contract tests защищают от наиболее вероятного drift;
10. existing project verification остаётся GREEN;
11. historical specs/plans сохранены и ясно маркированы как historical rationale.

## 18. Review focus

При review особенно проверить:

- не потерялись ли imperative guardrails из `media/AGENTS.md`;
- не возник ли новый duplication между architecture/reference/guides;
- можно ли понять current v5.1 без historical specs;
- не делают ли docs tests prose слишком жёстким;
- не сломаны ли старые entry paths;
- отражена ли similarity как recommendation evidence/hint, но не preference;
- отделён ли PR progress ledger от durable current status;
- достаточно ли update matrix для будущего сопровождения документации.
