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
→ media-check on exact resulting head SHA
→ human-reviewed merge
```

GitHub Actions не вызывает модель и не хранит OpenAI/model credentials. `TMDB_READ_TOKEN` нужен только provider-dependent `add_work`. В v1 auto-merge отключён.

## CLI

```bash
python -m media.cli search "Arrival" --format json
python -m media.cli show arrival-2016 --format json
python -m media.cli recommend-context --request request.json --format json
python -m media.cli apply-command request.json --dry-run --format json
python -m media.cli apply-command request.json --format json
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

`apply-command` принимает только строгий typed command JSON. Exit codes: `0` — success/no_change/already_applied, `2` — invalid/ambiguous user command, `3` — canonical/doctor/integrity failure, `4` — metadata provider unavailable.

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

Перед работой обязательно прочитать [`AGENTS.md`](AGENTS.md). Для обычной пользовательской записи модель формирует typed command и создаёт operation PR; она не редактирует canonical/generated YAML напрямую и не изменяет schema/vocabulary как побочный эффект data entry.
