# Personal Media Library v5

Персональная медиатека для фильмов, сериалов, мини-сериалов и анимации. Канонические данные хранятся в Git/YAML; сайт, SQLite, поисковые индексы, taste context и другие read-модели являются производными представлениями.

## Структура

- `data/works/` — один YAML на произведение.
- `data/collections/` — франшизы/серии и membership.
- `data/lists/` — пользовательские списки по target.
- `data/interactions/` — append-only история рекомендаций/выбора по месяцам.
- `data/tombstones/` — redirects для merged IDs.
- `config/` — анонимные viewer/group IDs (`primary`, `partner`, `couple`).
- `preferences/explicit/` — устойчивые явно высказанные предпочтения/ограничения.
- `preferences/inferred/` — evidence-backed гипотезы вкуса; это canonical выводы, но не independent evidence для самих себя.
- `vocabulary.yaml` — controlled semantic vocabulary.
- `schemas/` — canonical JSON Schema 2020-12.
- `commands/schemas/` — строгие JSON contracts для typed read/write operations.
- `generated/index.jsonl` — компактный retrieval index, derived.
- `generated/profiles/` — deterministic taste profiles, derived.
- `generated/database.sqlite` — локальная runtime-БД, derived и не коммитится.

## v5 intelligence model

v5 разделяет четыре слоя: factual metadata, film semantic fingerprint, user evidence и inferred taste. Film fingerprint описывает произведение, а не реакцию зрителя. Explicit user evidence сильнее повторяющихся correlations; повторяющиеся correlations сильнее одного rating-derived сигнала. Один высокий/низкий rating не должен автоматически превращать все traits фильма в сильную preference.

Для LLM-рекомендаций есть компактный read-only `taste-context`: explicit preferences, inferred hypotheses, strongest affinities с evidence, representative liked/disliked works, recent meaningful feedback, exclusions и для `couple` зоны agreement/disagreement без скрытого среднего.

## Multi-viewer

Raw signals создаются только при реальных данных. `partner: liked` валиден без числовой оценки. `couple` — group target для совместного reasoning, а не третий человек. В совместном контексте conflicting ratings/affinities показываются как disagreement, а не усредняются молча.

## Typed operations

Нормальные user/data write routes:

- `add_work`
- `record_viewing_feedback`
- `edit_viewing_feedback`
- `set_interest`
- `set_inferred_preferences`
- `set_semantic_fingerprint`
- `record_recommendation_interaction`

`edit_viewing_feedback` использует явные `set`/`clear`/`purge`: отсутствие поля никогда не означает удаление. Clear одного компонента не стирает соседние rating/reaction/feedback/viewing данные.

`set_inferred_preferences` полностью заменяет inferred hypotheses одного target и принимает только evidence-backed выводы с canonical vocabulary terms. `set_semantic_fingerprint` заменяет film-level semantic traits и отклоняет reaction-kind/unknown terms. `record_recommendation_interaction` пишет append-only события вроде `recommended`, `selected`, `already_watched`, `not_tonight`, `not_interested`; `not_tonight` не становится stable preference автоматически.

Read-only routes включают `recommend_context` и `taste-context`.

## Recommendation routing

Запрос «что посмотреть из моей медиатеки?» — internal-only: candidates берутся только из local index. Обычная просьба «посоветуй фильм» использует external discovery по умолчанию: локальная база служит памятью о вкусах, evidence и exclusions, но не ограничивает каталог кандидатов. Внешний рекомендованный фильм можно записать как interaction по stable work ref без преждевременного добавления его в библиотеку.

Mood/runtime/«не сегодня» относятся к текущему request context и не становятся permanent preferences без явного устойчивого заявления пользователя.

## Reanalysis и semantic enrichment

«Переосмысли мой вкус» строит новый taste context, выводит hypotheses из raw/explicit evidence и сохраняет replacement через `set_inferred_preferences`. Inferred hypothesis не может использовать другой inferred hypothesis как независимое подтверждение.

«Обнови понимание этого фильма» использует `set_semantic_fingerprint`: это knowledge о произведении, не о пользователе. Если нужного vocabulary term нет, его не добавляют скрыто; vocabulary maintenance — отдельная manual/developer задача.

## Metadata maintenance

Factual metadata может обогащаться через providers; TMDB — preferred primary provider. Неизвестные факты не выдумываются. `metadata.overrides` имеет приоритет над external snapshot.

Для массового обновления уже существующих фильмов используется typed maintenance-команда `refresh_metadata` со scope `all_movies`. Она выполняет полный identity preflight до записи, сохраняет user-owned signals/manual overrides и не делает partial mutation при ambiguity/provider failure. Это bulk maintenance и всегда остаётся manual-review operation: `refresh_metadata` не входит в normal-data auto-merge allowlist.

## Пользовательский UX

Для пользователя это личный киноассистент, а не интерфейс GitHub. Нормальные GitHub/YAML/Actions детали скрыты. Рекомендации не превращаются в анкету; feedback сохраняет всё уже ясное. Исправление/clear делают ровно запрошенную mutation, а explicit purge рассматривается отдельно как более разрушительное действие. Полный operating contract — [`AGENTS.md`](AGENTS.md), компактный старт для нового чата — [`START_PROMPT.md`](START_PROMPT.md).

## ChatGPT / GitHub flow

```text
natural language
→ strict typed JSON command
→ same-repo media/op-* branch
→ one transient .media/requests/<operation-id>.json
→ PR
→ Media Command
→ deterministic Python transaction + validation + operation-scoped rebuild
→ authoritative dispatch-only Media Check for exact resulting head SHA
→ guarded operation-specific auto-merge when eligible
→ Media Pages dispatch for exact merge SHA
```

`media-check.yml` — dispatch-only authoritative gate для media operation. Неавторитетный automatic `pull_request` Media Check намеренно отсутствует.

После exact-head GREEN guarded auto-merge разрешён только нормальным data operations:

`add_work`, `record_viewing_feedback`, `edit_viewing_feedback`, `set_interest`, `set_inferred_preferences`, `set_semantic_fingerprint`, `record_recommendation_interaction`.

Каждая операция дополнительно ограничена собственным path policy. Architecture, schemas, vocabulary, service/domain code, tests, docs, workflows и `refresh_metadata` не auto-merge через этот путь.

Если пользователь сообщает о новом просмотренном фильме и feedback одновременно, используется один `record_viewing_feedback(create_if_missing=true)`; provider creation + feedback применяются атомарно.

GitHub Actions media pipeline не вызывает LLM и не хранит OpenAI/model credentials. `TMDB_READ_TOKEN` доступен только provider-dependent операциям. Live AI/external discovery должен находиться за authenticated server-side Intelligence Broker boundary; статический Pages остаётся работоспособным без live model.

## Web / GitHub Pages

`web/` — статическая React/Vite витрина. Frontend читает versioned exported manifest, а не canonical YAML напрямую. Manifest — read model, не новый source of truth. Browser bundle не получает GitHub write credentials, provider tokens или LLM secrets.

v5 web parity должна показывать explicit/inferred taste, evidence, film fingerprints и couple disagreement отдельно от личных reactions. Website writes должны маппиться на те же typed operations, что LLM/CLI; browser-only data model запрещён.

## CLI

```bash
python -m media.cli search "Arrival" --format json
python -m media.cli show arrival-2016 --format json
python -m media.cli recommend-context --request request.json --format json
python -m media.cli taste-context --request taste.json --format json
python -m media.cli web-export --output /tmp/media-web-manifest.json --format json
python -m media.cli apply-command request.json --dry-run --format json
python -m media.cli apply-command request.json --format json
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

`apply-command` принимает только strict typed command JSON. Exit codes: `0` — success/no_change/already_applied, `2` — invalid/ambiguous/preflight-needs-input, `3` — canonical/doctor/integrity failure, `4` — provider unavailable.

## Проверка и пересборка

```bash
python -m media.tools.validate .
python -m media.tools.build_index media
python -m media.tools.build_profiles media
python -m media.tools.build_db media
python -m media.cli rebuild --check
python -m media.cli doctor --format json
python -m pytest -q
```

Generated SQLite можно удалить в любой момент: она полностью пересобирается из canonical YAML.

## Для LLM/агентов

Перед работой обязательно прочитать [`AGENTS.md`](AGENTS.md). Нормальная пользовательская запись всегда идёт через typed command/operation PR. Модель не правит canonical/generated YAML напрямую и не меняет schema/vocabulary как побочный эффект data entry. Bulk `refresh_metadata(all_movies)` идёт через тот же deterministic transaction layer, но требует manual review/merge.
