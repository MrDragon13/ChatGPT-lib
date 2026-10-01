# Personal Media Library v4

Персональная медиатека для фильмов, сериалов, мини-сериалов и анимации. Канонические данные хранятся в Git/YAML; сайт, SQLite, поисковые индексы и LLM-контекст являются клиентами или производными представлениями.

## Структура

- `data/works/` — один YAML на произведение.
- `data/collections/` — франшизы/серии и их membership.
- `data/lists/` — пользовательские списки по target.
- `data/interactions/` — append-only история рекомендаций/выбора по месяцам.
- `data/tombstones/` — redirects для merged IDs.
- `config/` — анонимные viewer/group IDs (`primary`, `partner`, `couple`).
- `preferences/explicit/` — только устойчивые явно высказанные предпочтения/ограничения.
- `vocabulary.yaml` — controlled semantic vocabulary.
- `schemas/` — canonical JSON Schema 2020-12.
- `commands/schemas/` — строгие JSON contracts для LLM/CLI write-операций.
- `generated/index.jsonl` — компактный retrieval index, derived.
- `generated/profiles/` — derived taste profiles.
- `generated/database.sqlite` — локальная runtime-БД, derived и не коммитится.

## Multi-viewer

Raw signals хранятся внутри work/collection и создаются только при реальных данных. `partner: liked` валиден без числовой оценки. `couple` — group target для совместного просмотра, а не третий человек. Персональные данные зрителей не хранятся.

## Metadata

Factual metadata может автоматически обогащаться из внешних providers; TMDB — предпочтительный primary provider. Неизвестные факты не выдумываются. `metadata.overrides` сохраняет ручные правки и имеет приоритет над внешними данными. Semantic traits всегда имеют provenance.

Для массового обновления уже существующих фильмов используется typed maintenance-команда `refresh_metadata` со scope `all_movies`. Перед записью она полностью разрешает identity всех фильмов через существующий TMDB ID, IMDb lookup, явный `tmdb_overrides` либо строгий title+year fallback. Если хотя бы один фильм неоднозначен или конфликтует с canonical identity, bulk refresh останавливается без частичной записи.

Refresh обновляет только provider-owned factual snapshot: release date/external IDs, поддерживаемые canonical genres, runtime, язык/страны/status, synopsis, credits, artwork, TMDB metric и provider provenance. Пользовательские оценки, просмотры, реакции, feedback, semantic metadata, relations, internal IDs и manual overrides сохраняются. Неподдерживаемые TMDB genre IDs не создают новые vocabulary terms автоматически.

## Пользовательский UX

Для пользователя это прежде всего личный киноассистент. Штатные GitHub/YAML/Actions/command детали скрыты за сценой и не проговариваются при нормальной успешной операции. Техническая информация появляется только при проблеме, когда от пользователя действительно требуется действие, либо по прямому запросу.

Рекомендации не должны превращаться в анкету: если контекста достаточно, ассистент сразу предлагает варианты. При отзыве сохраняется всё уже понятное; дополнительный вопрос допустим только если он реально улучшит будущие рекомендации, и такой необязательный вопрос не блокирует сохранение понятной части отзыва. Обязательное уточнение нужно только при реальном риске перепутать произведение, зрителя или смысл.

Для нового чистого чата готовый пользовательский промпт лежит в [`START_PROMPT.md`](START_PROMPT.md). Обязательные правила поведения независимо от стартового промпта находятся в [`AGENTS.md`](AGENTS.md).

## ChatGPT / GitHub flow

Чтение идёт дешёвым путём: `generated/index.jsonl` + relevant profile → shortlist → только выбранные canonical YAML. `recommend_context` возвращает evidence (`strengths`, `concerns`, viewing state), а не сохраняемый opaque score.

Штатная запись для ChatGPT:

```text
natural language
→ strict typed JSON command
→ same-repo media/op-* branch
→ one transient .media/requests/<operation-id>.json
→ PR
→ media-command GitHub Action
→ deterministic Python service
→ canonical YAML + generated rebuild + receipt
→ dispatched media-check on exact resulting head SHA
→ guarded auto-merge for eligible normal data operations
```

Request-only `media/op-*` PR не получает отдельный автоматический зелёный `Media Check`: authoritative check запускается `Media Command` только после успешного применения команды и commit результата.

Обычные data-only операции `add_work`, `record_viewing_feedback` и `set_interest` после exact-head green gate могут завершаться guarded auto-merge. Архитектурные изменения и bulk maintenance `refresh_metadata` в этот allowlist не входят; `refresh_metadata(scope=all_movies)` после зелёного exact-head check остаётся открытым для ручного review/merge.

Если пользователь одновременно сообщает о просмотре/оценке нового произведения, используется одна команда `record_viewing_feedback` с `create_if_missing: true`. Service через TMDB создаёт work и применяет viewing/rating/reaction/feedback в одной транзакции; при provider outage, неоднозначной identity или validation failure не сохраняется ни work, ни feedback.

GitHub Actions не вызывает модель и не хранит OpenAI/model credentials. `TMDB_READ_TOKEN` нужен только provider-dependent операциям: `add_work`, `record_viewing_feedback` с `create_if_missing: true` при создании отсутствующего произведения и `refresh_metadata`. Обычные изменения уже существующего work не зависят от provider.

## Web / GitHub Pages

`web/` — статическая русскоязычная витрина медиатеки на React/Vite. Frontend не читает canonical YAML напрямую: перед сборкой deterministic exporter формирует versioned `manifest.json` из canonical/derived media layer. Этот manifest является только read-моделью и не коммитится как новый источник истины.

GitHub Pages pipeline сначала запускает media validation/rebuild/doctor, затем экспортирует manifest, выполняет frontend unit/type/browser/accessibility/security checks и только после этого собирает Pages artifact. В браузер не передаются GitHub write credentials, provider tokens или другие секреты.

V1 сайта работает только на чтение: выбор фильма, поиск, фильтры, карточка произведения и сохранённые впечатления. Будущие быстрые исправления оценки/статуса должны отправляться через защищённый write-broker в тот же typed-command pipeline, который используют LLM/CLI; прямого редактирования YAML из браузера не будет.

## CLI

```bash
python -m media.cli search "Arrival" --format json
python -m media.cli show arrival-2016 --format json
python -m media.cli recommend-context --request request.json --format json
python -m media.cli web-export --output /tmp/media-web-manifest.json --format json
python -m media.cli apply-command request.json --dry-run --format json
python -m media.cli apply-command request.json --format json
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

`apply-command` принимает только строгий typed command JSON, включая maintenance-команду `refresh_metadata`. Exit codes: `0` — success/no_change/already_applied, `2` — invalid/ambiguous/preflight-needs-input command, `3` — canonical/doctor/integrity failure, `4` — metadata provider unavailable.

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

Перед работой обязательно прочитать [`AGENTS.md`](AGENTS.md). Для обычной пользовательской записи модель формирует typed command и создаёт operation PR; она не редактирует canonical/generated YAML напрямую и не изменяет schema/vocabulary как побочный эффект data entry. Bulk `refresh_metadata(all_movies)` также идёт через typed-command pipeline, но всегда требует ручного merge после review.
