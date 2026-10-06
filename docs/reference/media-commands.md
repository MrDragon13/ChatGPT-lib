# Media operations reference

Компактный каталог текущих typed operations. Полные payload fields и validation rules определяются JSON schemas в `media/commands/schemas/`; этот документ не дублирует schema contract.

## Каталог

| Operation | Категория | Режим | Основной effect | Normal auto-merge |
| --- | --- | --- | --- | --- |
| `record_viewing_feedback` | feedback | write | Записать viewing/rating/reaction/feedback; может атомарно создать отсутствующий work при `create_if_missing` | да |
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
| `reserve_reassessment_session` | reassessment pilot | write | Зарезервировать до 5 frozen-cohort works в одной primary legacy reassessment session | да |
| `complete_reassessment_item` | reassessment pilot | write | Завершить один reserved item как changed/confirmed unchanged/deferred с ledger serialization | да |
| `close_reassessment_session` | reassessment pilot | write | Закрыть полностью разрешённую reassessment session и сохранить progress snapshot | да |
| `record_reassessment_modernization` | reassessment modernization | write | Зафиксировать completed/blocked modernization outcome для уже reviewed work | да |
| `recommend_context` | recommendation | read-only | Построить candidate/context read model для recommendation reasoning | n/a |
| `taste_context` | intelligence | read-only | Построить компактный target taste/evidence context | n/a |
| `assess_candidate` | intelligence | read-only | Собрать контекст для qualitative ответа «понравится ли мне X?» без mutation | n/a |

## Write vs read-only

Write operation имеет `operation_id` и применяется через deterministic transaction/path policy. Read-only operation canonical state не мутирует и не создаёт operation PR как побочный эффект.

## Auto-merge

Колонка выше описывает intended current class, но executable authority остаётся за workflow/path-policy code. Даже auto-merge-eligible operation не merge'ится, если затронула запрещённый path, не прошла exact-head checks или перестала соответствовать operation contract.

`refresh_metadata` намеренно остаётся manual maintenance operation. `refresh_work_metadata` и `record_reassessment_modernization` — узкие reassessment-modernization operations; successful metadata/semantic checks могут иметь trusted status `no_change` без искусственной canonical mutation.

## External works

Некоторые operations принимают work reference, который может быть external stable identity. External reference не означает автоматическое добавление work, кроме явно разрешённого create flow (`add_work` или feedback create-if-missing).

Similarity может persist external endpoint без создания canonical work; candidate assessment external work остаётся read-only.

## Схемы

Source contracts:

- `media/commands/schemas/record_viewing_feedback.schema.json`
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
- `media/commands/schemas/reserve_reassessment_session.schema.json`
- `media/commands/schemas/complete_reassessment_item.schema.json`
- `media/commands/schemas/close_reassessment_session.schema.json`
- `media/commands/schemas/record_reassessment_modernization.schema.json`
- `media/commands/schemas/recommend_context.schema.json`
- `media/commands/schemas/taste_context.schema.json`
- `media/commands/schemas/assess_candidate.schema.json`

Operation registry synchronization защищается executable docs contract: добавление новой registered operation требует обновить эту таблицу.
