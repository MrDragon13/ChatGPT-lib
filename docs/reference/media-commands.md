# Операции media

Краткий список текущих типизированных операций. Полные поля запросов и правила проверки определяются JSON Schema в `media/commands/schemas/`; здесь описано только назначение.

## Каталог

| Операция | Тип | Режим | Что делает | Auto-merge |
| --- | --- | --- | --- | --- |
| `record_media_entry` | library/feedback | запись | Атомарно записывает просмотр, оценку, реакцию или отзыв; при необходимости создаёт новое произведение по устойчивой provider identity | да |
| `media_entry_context` | library | read-only | Возвращает компактное состояние произведения для выбранного `target` | — |
| `edit_viewing_feedback` | feedback | запись | Точечно меняет, очищает или удаляет сохранённый отзыв выбранного `target` | да |
| `set_interest` | library | запись | Сохраняет устойчивое состояние интереса | да |
| `add_work` | library | запись | Добавляет произведение после проверки identity | да |
| `refresh_metadata` | maintenance | запись | Массово обновляет metadata после preflight; требует ручного review | нет |
| `refresh_work_metadata` | maintenance | запись | Безопасно обновляет metadata одного существующего произведения | да |
| `set_inferred_preferences` | intelligence | запись | Полностью заменяет выведенные гипотезы о вкусе выбранного `target` | да |
| `set_semantic_fingerprint` | semantics | запись | Заменяет семантические признаки произведения из контролируемого словаря | да |
| `record_recommendation_interaction` | recommendation | запись | Добавляет append-only событие взаимодействия с рекомендацией | да |
| `set_work_similarity` | relation | запись | Создаёт или обновляет симметричное явное сходство для `target` | да |
| `remove_work_similarity` | relation | запись | Удаляет такое сходство | да |
| `recommend_context` | recommendation | read-only | Строит кандидатов и контекст для рекомендации | — |
| `taste_context` | intelligence | read-only | Строит компактный контекст вкуса и evidence | — |
| `assess_candidate` | intelligence | read-only | Собирает данные для качественного ответа «понравится ли мне X?» | — |

Для `record_media_entry(create_if_missing=true)` клиент передаёт устойчивую `provider_identity`, семантические traits и пользовательские сигналы. Полные metadata, `semantic input digest`, `vocabulary digest` и `algorithm version` получает или вычисляет доверенный код.

## Запись и чтение

Write-операция имеет `operation_id` и выполняется через детерминированную transaction с path policy.

Read-only операции канонические данные не меняют и operation PR не создают.

## Auto-merge

Таблица показывает нормальный режим работы, но окончательное решение принимает код workflow/path policy.

Даже операция, которой разрешён auto-merge, не будет слита, если она:

- затронула запрещённый путь;
- не прошла проверку exact head/base;
- нарушила свой контракт.

`refresh_metadata` намеренно остаётся ручной maintenance-операцией. `refresh_work_metadata` работает только с одним существующим произведением и может завершиться успешным `no_change`.

## Внешние произведения

Некоторые операции принимают `WorkRef` на внешнее произведение.

Внешняя ссылка сама по себе не добавляет произведение в библиотеку, кроме явно разрешённого create flow: `add_work` или `record_media_entry(create_if_missing=true)`.

Similarity может хранить внешний endpoint без создания локального произведения. `assess_candidate` внешнего фильма остаётся read-only.

## Схемы

- `media/commands/schemas/record_media_entry.schema.json`
- `media/commands/schemas/media_entry_context.schema.json`
- `media/commands/schemas/edit_viewing_feedback.schema.json`
- `media/commands/schemas/set_interest.schema.json`
- `media/commands/schemas/add_work.schema.json`
- `media/commands/schemas/refresh_metadata.schema.json`
- `media/commands/schemas/refresh_work_metadata.schema.json`
- `media/commands/schemas/set_inferred_preferences.schema.json`
- `media/commands/schemas/set_semantic_fingerprint.schema.json`
- `media/commands/schemas/record_recommendation_interaction.schema.json`
- `media/commands/schemas/set_work_similarity.schema.json`
- `media/commands/schemas/remove_work_similarity.schema.json`
- `media/commands/schemas/recommend_context.schema.json`
- `media/commands/schemas/taste_context.schema.json`
- `media/commands/schemas/assess_candidate.schema.json`

Тест документации проверяет, что этот каталог совпадает с registry зарегистрированных операций.
