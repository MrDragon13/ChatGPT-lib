# ChatGPT-lib

Текущая media capability line: **Media Intelligence v6**.

Личная библиотека структурированных данных и профилей, собранных в диалогах с ChatGPT. Основной живой subsystem — персональная media intelligence system: фильмы, сериалы и анимация, multi-viewer сигналы, semantic fingerprints, taste context, рекомендации, candidate assessment и explicit similarity между произведениями.

## Что умеет проект сейчас

- хранит canonical media data в Git/YAML;
- ведёт независимые сигналы для `primary`, `partner` и `couple`;
- строит derived profiles, retrieval index, taste context и web manifest;
- поддерживает internal и external recommendations с provenance-aware explanations;
- отвечает на «понравится ли мне X?» через read-only `assess_candidate` без fake precise score;
- хранит explicit work similarity как target-specific evidence/hint, но не превращает её автоматически в preference;
- принимает normal media mutations только через strict typed operations и deterministic validation pipeline;
- использует `record_media_entry` как основной маршрут для нового просмотра, оценки, реакции или отзыва;
- публикует русскоязычную GitHub Pages-витрину поверх derived manifest;
- отправляет поддерживаемые browser edits через защищённый typed-command broker без выдачи браузеру GitHub/provider/model secrets.

## Архитектура в одном абзаце

`media/data/` и другие canonical YAML/config источники — source of truth. Python domain/service/repository слой применяет typed operations, валидирует данные и пересобирает derived artifacts. `web/` не читает canonical YAML напрямую: он получает versioned manifest и остаётся read-model surface. Записи из LLM/CLI/web используют один и тот же command contract; normal data operations идут через request-only operation PR, один `Media Command` runner и exact-head merge, а architecture/schema/vocabulary/workflow changes остаются manual developer work. Historical design specs объясняют решения, но текущее поведение описывается living docs и проверяется code/schemas/tests.

## Куда идти дальше

- [Карта всей документации](docs/README.md) — что является living docs, operating contract и historical rationale.
- [Как пользоваться медиатекой](docs/guides/media-usage.md) — пользовательские сценарии.
- [Как разрабатывать](docs/guides/development.md) — developer workflow, TDD и ownership документации.
- [Архитектура системы](docs/architecture/overview.md) — компоненты, data flow и security boundaries.
- [Personal Media Library v6](media/README.md) — локальная точка входа в `media/` и compatibility entry path для subsystem docs.
- [Старт нового киноассистента](media/START_PROMPT.md) — human-facing launcher.
- [`AGENTS.md`](AGENTS.md) — router для LLM/agent workflows.

## Web product/design references

`PRODUCT.md` и `DESIGN.md` относятся к media web surface: product brief и visual/design-system contract соответственно. Они не заменяют system architecture documentation.
