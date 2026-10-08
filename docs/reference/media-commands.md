# Media operations reference

Компактный каталог текущих typed operations. Полные payload fields и validation rules определяются JSON schemas в `media/commands/schemas/`; этот документ не дублирует schema contract.

## Каталог

| Operation | Категория | Режим | Основной effect | Normal auto-merge |
| --- | --- | --- | --- | --- |
| `record_media_entry` | feedback/library | write | Атомарно записать пользовательский отзыв; для отсутствующего work проверить stable provider identity, получить metadata на trusted side, сохранить semantics и создать work | да |
| `media_entry_context` | library context | read-only | Вернуть компактное target-scoped состояние work для LLM/Broker без лишних чтений | n/a |
| `edit_viewing_feedback` | feedback | write | Точечно изменить/clear/purge target-scoped viewing feedback | да |
| `set_interest` | library intent | write | Установить устойчивое interest state для target/work | да |
| `add_work` | library | write | Добавить canonical work после identity/provider validation | да |
| `refresh_metadata` | maintenance | write | Bulk/provider metadata refresh с preflight; manual review route | нет |
| `refresh_work_metadata` | modernization | write | Stale-safe provider metadata refresh ровно одного existing work | да |
| `set_inferred_preferences` | intelligence | write | Полностью заменить evidence-backed inferred hypotheses target | да |
| `set_semantic_fingerprint` | semantics | write | Заменить work-level semantic traits из controlled vocabulary | да |
| `record_recommendation_interaction` | recommendation | write | Добавить append-only recommendation interaction event | да |
| `set_work_similarity` | relation | write | Upsert одной target-specific undirected explicit similarity assertion | да |
| `remove_work_similarity` | relation | write | Удалить explicit similarity для target/unordered pair | да |
| `recommend_context` | recommendation | read-only | Построить candidate/context read model для recommendation reasoning | n/a |
| `taste_context` | intelligence | read-only | Построить компактный target taste/evidence context | n/a |
| `assess_candidate` | intelligence | read-only | Собрать контекст для qualitative ответа «понравится ли мне X?» без mutation | n/a |

Для `record_media_entry(create_if_missing=true)` клиент передаёт stable `provider_identity`, semantic traits и пользовательские сигналы. Полный provider payload, semantic input digest, vocabulary digest и algorithm version получает или вычисляет trusted runtime. Это исключает ложные конфликты из-за изменившегося runtime, локализации, credits или synopsis.

## Write vs read-only

Write operation имеет `operation_id` и применяется через deterministic transaction/path policy. Read-only operation canonical state не мутирует и не создаёт operation PR как побочный эффект.

## Auto-merge

Колонка выше описывает intended current class, но executable authority остаётся за workflow/path-policy code. Даже auto-merge-eligible operation не merge'ится, если затронула запрещённый path, не прошла exact-head checks или перестала соответствовать operation contract.

`refresh_metadata` намеренно остаётся manual maintenance operation. `refresh_work_metadata` — узкая операция обновления одного существующего произведения; успешная проверка может завершиться trusted status `no_change` без искусственной canonical mutation.

## External works

Некоторые operations принимают work reference, который может быть external stable identity. External reference не означает автоматическое добавление work, кроме явно разрешённого create flow (`add_work` или feedback create-if-missing).

Similarity может persist external endpoint без создания canonical work; candidate assessment external work остаётся read-only.

## Схемы

Source contracts:

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

Operation registry synchronization защищается executable docs contract: добавление новой registered operation требует обновить эту таблицу.
