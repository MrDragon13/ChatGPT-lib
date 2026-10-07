# Personal Media Library v6

`media/` — canonical personal media subsystem для фильмов, сериалов, мини-сериалов и анимации. Git/YAML хранит долговременное состояние; index, profiles, taste/recommendation contexts, временный SQLite и web manifest являются derived read models.

После v6 reset активная библиотека намеренно начинается пустой. Глобальные explicit preferences и vocabulary сохранены. Старые пользовательские данные находятся только в человекочитаемом архиве `docs/archive/media-library-before-v6-reset-2026-10-07.md` и не участвуют автоматически в intelligence.

## Быстрый ориентир

Canonical data:

- `data/works/` — произведения и target-scoped viewer/group signals;
- `data/collections/`, `data/lists/`, `data/interactions/` — коллекции, списки и recommendation events;
- `data/relations/similarity/` — explicit target-specific undirected similarity;
- `preferences/explicit/` и `preferences/inferred/` — explicit preferences и evidence-backed inferred hypotheses;
- `config/` — `primary`, `partner`, `couple`;
- `vocabulary.yaml` и `schemas/` — controlled semantic/schema contracts.

Derived state находится в `generated/` и пересобирается из canonical data. Не редактируйте generated artifacts как источник пользовательских фактов.

## Текущая документация

- [Media domain model](../docs/architecture/media-model.md)
- [Media intelligence](../docs/architecture/intelligence.md)
- [Write pipeline](../docs/architecture/write-pipeline.md)
- [Web and broker](../docs/architecture/web-and-broker.md)
- [Как пользоваться медиатекой](../docs/guides/media-usage.md)
- [Operations runbook](../docs/guides/operations.md)
- [Media operations reference](../docs/reference/media-commands.md)
- [Cross-system invariants](../docs/reference/invariants.md)
- [Current status](../docs/status/current.md)

Исторические specs/plans под `../docs/superpowers/` объясняют причины решений, но не заменяют current code, schemas, `AGENTS.md` и living docs.

## Operating contract

Перед agent/LLM работой читайте [`AGENTS.md`](AGENTS.md). Новый основной write route — `record_media_entry`; существующий work использует быстрый путь без provider lookup и semantic recomputation.

[`START_PROMPT.md`](START_PROMPT.md) — human-facing launcher нового киноассистента.

`V5_STATUS.md` сохранён только как historical compatibility pointer.

## CLI quickstart

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

Full verification и explicit build commands находятся в [operations runbook](../docs/guides/operations.md).

## Core boundaries

- Normal media mutations используют strict typed commands; LLM/browser code не патчит canonical YAML напрямую.
- `media_entry_context`, `recommend_context`, `taste_context` и `assess_candidate` read-only.
- External recommendation/candidate/similarity reference не создаёт canonical work без явного create flow.
- Explicit similarity — evidence/hint, но не preference.
- Unknown identity/metadata/vocabulary не угадываются.
- Architecture, schemas, vocabulary и workflows меняются отдельным developer PR.
- Browser write/provider/model secrets не попадают в static Pages bundle.
- Pre-v6 MD archive не является canonical или recommendation input.

## Архив до v6

`media.tools.archive_library` остаётся инструментом воспроизводимой проверки исторического MD-снимка. Финальный архив был проверен побайтной регенерацией до reset.

После cutover архив используется только как человеческий чек-лист. Автоматический импорт старых ratings/reactions/feedback обратно в intelligence запрещён.
