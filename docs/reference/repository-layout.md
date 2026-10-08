# Структура репозитория

Карта основных путей ChatGPT-lib после перехода на Media Intelligence v6.

## Корень

| Путь | Назначение |
| --- | --- |
| `README.md` | короткая входная страница проекта |
| `AGENTS.md` | маршрутизация для агента |
| `PRODUCT.md` | описание продукта Media Web |
| `DESIGN.md` | дизайн-система Media Web |
| `docs/` | живая документация, архив и история решений |
| `media/` | данные и логика медиатеки |
| `web/` | статический React/Vite-клиент |
| `broker/` | защищённая запись из браузера |
| `tests/` | исполняемые контракты и fixtures |
| `.github/workflows/` | CI, операции и публикация |
| `.media/` | временные requests и operation receipts |

## `docs/`

- `docs/architecture/` — текущая архитектура;
- `docs/guides/` — использование, разработка и эксплуатация;
- `docs/reference/` — краткие контракты и справочники;
- `docs/status/` — текущее устойчивое состояние;
- `docs/archive/` — исторические записи и завершённые разовые процедуры;
- `docs/superpowers/` — датированные specs/plans и история проектных решений.

Архив и historical specs не используются как runtime input.

## Канонические данные `media/`

- `media/data/works/` — произведения;
- `media/data/collections/` — коллекции и франшизы;
- `media/data/lists/` — списки;
- `media/data/interactions/` — recommendation interactions;
- `media/data/relations/similarity/` — явно указанное сходство;
- `media/data/tombstones/` — перенаправления после merge identity;
- `media/preferences/explicit/` — явные устойчивые предпочтения;
- `media/preferences/inferred/` — выведенные гипотезы;
- `media/config/viewers.yaml`, `groups.yaml` — пользователи и группы;
- `media/config/intelligence.yaml` — версии алгоритмов и порог reanalysis;
- `media/config/operation_path_policy.json` — разрешённые пути и классы исполнения;
- `media/vocabulary.yaml` — контролируемый словарь;
- `media/schemas/` — схемы данных и read models;
- `media/commands/schemas/` — схемы типизированных операций.

Старые pre-v6 runtime/pilot-файлы и Stage A baselines в текущем дереве отсутствуют.

## Код `media/`

- `media/domain/` — типы, контракты и ошибки;
- `media/commands/` — разбор команд и registry схем;
- `media/service/` — запись и построение read-only контекста;
- `media/repository/` — чтение и сохранение;
- `media/providers/` — внешние поставщики метаданных;
- `media/tools/` — проверка, сборка, диагностика и архив;
- `media/cli.py` — CLI.

## `media/generated/`

Пересобираемые данные:

- `index.jsonl`;
- `profiles/*.yaml`;
- другие read models.

Runtime SQLite тоже является производной и не хранится в Git как источник истины.

## `web/`

Статический React/TypeScript-клиент. Он читает Web manifest и отправляет поддерживаемые правки только через Broker.

## `broker/`

Stateless server-side слой для браузерной записи. Он преобразует отзыв в `record_media_entry` и использует viewer digest на точном SHA `main`.

## `.github/workflows/`

- `media-command.yml` — обычные типизированные записи и подготовка manual maintenance PR;
- `media-dev-check.yml` — полный media-gate developer PR;
- `web-check.yml` — проверки Web;
- `broker-check.yml` — проверки Broker;
- `media-pages.yml` — сборка и публикация Pages для точного SHA;
- `broker-deploy.yml` — ручная публикация Broker.

Старый раздельный validation/merge путь удалён; обычные записи обслуживает `media-command.yml`.

## `.media/`

- `.media/requests/` — временные файлы запросов;
- `.media/operations/` — operation receipts.

Это служебные данные процесса, а не пользовательское хранилище.

## Где менять контракт

- схема или доменный инвариант → code/schema + `architecture/media-model.md` / `reference/invariants.md`;
- типизированная операция → command/schema/service + `reference/media-commands.md`;
- вкус и рекомендации → service + `architecture/intelligence.md`;
- CI и запись → workflow/service + `architecture/write-pipeline.md`;
- Web/Broker → code + `architecture/web-and-broker.md`;
- структура репозитория → этот файл;
- крупное новое решение → датированный spec/plan, затем живые документы после реализации.
