# Документация ChatGPT-lib

Текущая media capability — **Media Intelligence v6**. Living docs ниже описывают post-reset систему; v5/v5.1 материалы под `superpowers/` являются историей решений, а старые runtime compatibility surfaces удалены.

Этот каталог — карта **living documentation**: актуального описания того, как проект устроен и используется сейчас. Dated design specs и implementation plans сохраняются как история решений, но не являются текущим операционным контрактом после реализации соответствующих изменений.

## Быстрые маршруты

- [Понять систему](architecture/overview.md) — компоненты, источники истины и границы между media, web, broker и GitHub Actions.
- [Пользоваться медиатекой](guides/media-usage.md) — пользовательские сценарии без GitHub/implementation noise.
- [Разрабатывать](guides/development.md) — ветки, TDD, typed operations, manual developer route и правила обновления docs.
- [Обслуживать](guides/operations.md) — validate, rebuild, doctor, web checks, deploy и recovery.
- [Смотреть reference](reference/media-commands.md) — операции, инварианты, терминология и layout репозитория.
- [Проверить текущее состояние](status/current.md) — реализованные возможности и известные ограничения без PR/task ledger.

## Что является авторитетным

### Реализованное поведение

Для ответа на вопрос «что система реально делает?» первичны runtime code, JSON schemas, controlled vocabulary, workflow configuration и executable tests. Living architecture/reference docs объясняют эти контракты; расхождение living doc с кодом — документационный баг.

### Operating contracts для агентов

[`../AGENTS.md`](../AGENTS.md) — repository-level router, а [`../media/AGENTS.md`](../media/AGENTS.md) — нормативный media operating contract. Они определяют, **как агент обязан действовать**: какой route выбрать, где допустима запись, какие guardrails и verification gates обязательны. Living docs дают контекст, но не ослабляют imperative rules из `AGENTS.md`.

### Historical rationale

Repository path `docs/superpowers/` содержит historical design/implementation record. [`superpowers/specs/`](superpowers/specs/) и [`superpowers/plans/`](superpowers/plans/) — **historical rationale**: design decisions и implementation plans, объясняющие, почему проект пришёл к текущей архитектуре. Их старые status markers относятся к моменту написания документа и не описывают текущее состояние проекта.

## Структура living docs

- `architecture/` — как система устроена сейчас;
- `guides/` — как ей пользоваться, разрабатывать и обслуживать;
- `reference/` — компактные текущие контракты и определения;
- `status/` — durable current state;
- `archive/` — historical human records и завершённые one-time runbooks;
- `superpowers/` — исторические specs/plans.

## Язык

Human-facing living docs и README преимущественно русскоязычные. Имена операций, schema fields, CLI commands, code identifiers и другие canonical technical terms сохраняются в исходном English spelling. `AGENTS.md` может оставаться на английском как machine/agent-oriented operating contract.

## Как поддерживать документацию

Обновляется только слой, который владеет изменившимся контрактом:

| Изменение | Что обновлять |
| --- | --- |
| typed operation | `reference/media-commands.md`; при semantic impact — соответствующий architecture guide |
| schema/domain invariant | `architecture/media-model.md` и/или `reference/invariants.md` |
| taste/recommendation/assessment semantics | `architecture/intelligence.md`; user-visible behavior — `guides/media-usage.md` |
| write/CI/auto-merge pipeline | `architecture/write-pipeline.md`, `guides/operations.md` |
| manifest/broker/security boundary | `architecture/web-and-broker.md`; при product impact — `../PRODUCT.md` |
| repository layout | `reference/repository-layout.md` |
| visual web design rule | `../DESIGN.md` |
| current capability/limitation | `status/current.md` |
| новое архитектурное решение | dated spec under `superpowers/specs/`, а после реализации — соответствующие living docs |

Missing required docs update рассматривается как обычный regression, а не optional polish.
