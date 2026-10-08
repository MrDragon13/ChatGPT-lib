# Personal Media Library v6

`media/` — основная подсистема личной медиатеки для фильмов, сериалов, мини-сериалов и анимации.

Долговременные данные хранятся в Git/YAML. Индексы, профили, контексты вкуса и рекомендаций, временная SQLite-база и Web manifest — производные данные, которые можно пересобрать.

После перехода на v6 библиотека была обнулена и начала наполняться заново обычными v6-записями. Старые пользовательские данные сохранены только в человекочитаемом архиве `docs/archive/media-library-before-v6-reset-2026-10-07.md` и автоматически в рекомендации не попадают.

## Где что лежит

- `data/works/` — произведения и сигналы зрителей/группы;
- `data/collections/`, `data/lists/`, `data/interactions/` — коллекции, списки и события рекомендаций;
- `data/relations/similarity/` — явно указанное сходство;
- `preferences/explicit/` — явно заявленные устойчивые предпочтения;
- `preferences/inferred/` — выведенные гипотезы о вкусе;
- `config/` — настройки `primary`, `partner`, `couple` и алгоритмов;
- `vocabulary.yaml`, `schemas/` — словарь и схемы;
- `generated/` — производные файлы, которые нельзя править как источник пользовательских фактов.

## Актуальная документация

- [Модель данных](../docs/architecture/media-model.md)
- [Логика вкуса и рекомендаций](../docs/architecture/intelligence.md)
- [Путь записи](../docs/architecture/write-pipeline.md)
- [Web и Broker](../docs/architecture/web-and-broker.md)
- [Как пользоваться медиатекой](../docs/guides/media-usage.md)
- [Эксплуатация](../docs/guides/operations.md)
- [Справочник операций](../docs/reference/media-commands.md)
- [Инварианты](../docs/reference/invariants.md)
- [Текущее состояние](../docs/status/current.md)

Исторические specs/plans в `../docs/superpowers/` нужны только для разбора старых решений.

## Правила для агента

Перед работой с медиатекой читайте [`AGENTS.md`](AGENTS.md). Основной путь записи просмотра, оценки, реакции и отзыва — `record_media_entry`.

[`START_PROMPT.md`](START_PROMPT.md) — короткий стартовый текст для нового чата с киноассистентом.

## Быстрые команды CLI

```bash
python -m media.cli search "Arrival" --format json
python -m media.cli show arrival-2016 --format json
python -m media.cli media-entry-context --request entry-context.json --format json
python -m media.cli taste-context --request taste.json --format json
python -m media.cli recommend-context --request request.json --format json
python -m media.cli assess-candidate --request assessment.json --format json
python -m media.cli apply-command request.json --dry-run --format json
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Полная проверка описана в [руководстве по эксплуатации](../docs/guides/operations.md).

## Важные границы

- Обычные изменения данных идут через типизированные команды, а не через прямую правку YAML.
- `media_entry_context`, `recommend_context`, `taste_context` и `assess_candidate` только читают данные.
- Внешняя рекомендация или ссылка на похожий фильм сама по себе не добавляет произведение в библиотеку.
- Явно указанное сходство — основание для рекомендаций, но не предпочтение само по себе.
- Неизвестные идентичность, метаданные и термины словаря не угадываются.
- Схемы, словарь, workflows и архитектура меняются отдельным developer PR.
- Секреты GitHub, провайдера и модели не попадают в статический Web.
- Архив до v6 не является источником текущих данных.
