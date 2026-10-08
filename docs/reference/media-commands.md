# Операции медиатеки

Краткий список текущих типизированных операций. Полные поля запросов и правила проверки определяются JSON Schema в `media/commands/schemas/`; здесь описано только назначение.

## Каталог

| Операция | Тип | Режим | Что делает | Автослияние |
| --- | --- | --- | --- | --- |
| `record_media_entry` | медиатека/отзыв | запись | Атомарно записывает просмотр, оценку, реакцию или отзыв; при необходимости создаёт новое произведение по устойчивой `provider_identity` | да |
| `media_entry_context` | медиатека | только чтение | Возвращает компактное состояние произведения для выбранного `target` | — |
| `edit_viewing_feedback` | отзыв | запись | Точечно меняет, очищает или удаляет сохранённый отзыв выбранного `target` | да |
| `set_interest` | медиатека | запись | Сохраняет устойчивое состояние интереса | да |
| `add_work` | медиатека | запись | Добавляет произведение после проверки идентичности | да |
| `refresh_metadata` | обслуживание | запись | Массово обновляет метаданные после предварительной проверки; требует ручной проверки | нет |
| `refresh_work_metadata` | обслуживание | запись | Безопасно обновляет метаданные одного существующего произведения | да |
| `set_inferred_preferences` | анализ вкуса | запись | Полностью заменяет выведенные гипотезы о вкусе выбранного `target` | да |
| `set_semantic_fingerprint` | семантика | запись | Заменяет семантические признаки произведения из контролируемого словаря | да |
| `record_recommendation_interaction` | рекомендации | запись | Добавляет событие взаимодействия с рекомендацией; старые события не переписываются | да |
| `set_work_similarity` | связь | запись | Создаёт или обновляет симметричное явное сходство для `target` | да |
| `remove_work_similarity` | связь | запись | Удаляет такое сходство | да |
| `recommend_context` | рекомендации | только чтение | Строит кандидатов и контекст для рекомендации | — |
| `taste_context` | анализ вкуса | только чтение | Строит компактный контекст вкуса и оснований | — |
| `assess_candidate` | анализ вкуса | только чтение | Собирает данные для качественного ответа «понравится ли мне X?» | — |

Для `record_media_entry(create_if_missing=true)` клиент передаёт устойчивую `provider_identity`, семантические признаки и пользовательские сигналы. Полные метаданные, `semantic input digest`, `vocabulary digest` и `algorithm version` получает или вычисляет доверенный код.

## Запись и чтение

Операция записи имеет `operation_id` и выполняется через детерминированную transaction с path policy.

Операции только для чтения канонические данные не меняют и operation PR не создают.

## Автоматическое слияние

Таблица показывает нормальный режим работы, но окончательное решение принимает процесс GitHub Actions и `path policy`.

Даже операция, которой разрешено автоматическое слияние, не будет слита, если она:

- затронула запрещённый путь;
- не прошла проверку точных head/base;
- нарушила свой контракт.

`refresh_metadata` намеренно остаётся ручной операцией обслуживания. `refresh_work_metadata` работает только с одним существующим произведением и может завершиться успешным `no_change`.

## Внешние произведения

Некоторые операции принимают `WorkRef` на внешнее произведение.

Внешняя ссылка сама по себе не добавляет произведение в библиотеку, кроме явно разрешённого путь создания: `add_work` или `record_media_entry(create_if_missing=true)`.

Связь сходства может хранить внешнюю ссылку без создания локального произведения. `assess_candidate` внешнего фильма остаётся операцией только для чтения.

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

Тест документации проверяет, что этот каталог совпадает с реестром (`registry`) зарегистрированных операций.
