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
- `schemas/` — JSON Schema 2020-12.
- `generated/index.jsonl` — компактный retrieval index, derived.
- `generated/profiles/` — derived taste profiles.
- `generated/database.sqlite` — локальная runtime-БД, derived и не коммитится.

## Multi-viewer

Raw signals хранятся внутри work/collection и создаются только при реальных данных. `partner: liked` валиден без числовой оценки. `couple` — group target для совместного просмотра, а не третий человек. Персональные данные зрителей не хранятся.

## Metadata

Factual metadata может автоматически обогащаться из внешних providers; TMDB — предпочтительный primary provider. Неизвестные факты не выдумываются. `metadata.overrides` сохраняет ручные правки и имеет приоритет над внешними данными. Semantic traits всегда имеют provenance.

## CLI

Основной программный интерфейс поверх общего service layer:

```bash
python -m media.cli search "Arrival" --format json
python -m media.cli show arrival-2016 --format json
python -m media.cli recommend-context --request request.json --format json
python -m media.cli apply-command request.json --dry-run --format json
python -m media.cli apply-command request.json --format json
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

`apply-command` принимает только строгий typed command JSON. Для `add_work`, которому действительно нужен внешний поиск, может использоваться `TMDB_READ_TOKEN`; операции с уже известными произведениями не зависят от TMDB.

Exit codes CLI: `0` — success/no_change/already_applied, `2` — invalid/ambiguous user command, `3` — canonical/doctor/integrity failure, `4` — metadata provider unavailable.

## Проверка и пересборка

```bash
python -m media.tools.validate .
python -m media.tools.build_index media
python -m media.tools.build_profiles media
python -m media.tools.build_db media
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Полный тестовый прогон:

```bash
python -m pytest -q
```

Generated SQLite можно удалить в любой момент: она полностью пересобирается из canonical YAML.

## Для LLM/агентов

Перед записью обязательно прочитать [`AGENTS.md`](AGENTS.md), соответствующую schema и `vocabulary.yaml`. Нормальный write-path использует typed command/service layer; обычное добавление произведения не должно менять schema или создавать новые термины без необходимости.
