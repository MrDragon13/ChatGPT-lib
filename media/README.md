# Personal Media Library v5

`media/` — canonical personal media subsystem для фильмов, сериалов, мини-сериалов и анимации. Git/YAML хранит долговременное состояние; indexes, profiles, taste/recommendation contexts, SQLite и web manifest являются derived read models.

## Быстрый ориентир

Canonical data:

- `data/works/` — произведения и target-scoped viewer/group signals;
- `data/collections/`, `data/lists/`, `data/interactions/` — коллекции, списки и recommendation events;
- `data/relations/similarity/` — explicit target-specific undirected similarity;
- `preferences/explicit/` и `preferences/inferred/` — stable explicit preferences и evidence-backed hypotheses;
- `config/` — `primary`, `partner`, `couple`;
- `vocabulary.yaml` и `schemas/` — controlled semantic/schema contracts.

Derived state находится в `generated/` и пересобирается из canonical data. Не редактируйте generated artifacts как источник пользовательских фактов.

## Current living docs

- [Media domain model](../docs/architecture/media-model.md) — canonical/derived, targets, evidence, semantic fingerprint, WorkRef, similarity/reconciliation.
- [Media intelligence](../docs/architecture/intelligence.md) — taste context, recommendations, `assess_candidate`, provenance и couple disagreement.
- [Write pipeline](../docs/architecture/write-pipeline.md) — typed request → operation PR → deterministic transaction → exact-head gate → guarded merge.
- [Web and broker](../docs/architecture/web-and-broker.md) — manifest v3, Pages и security boundaries.
- [Как пользоваться медиатекой](../docs/guides/media-usage.md) — human-facing scenarios.
- [Operations runbook](../docs/guides/operations.md) — validate/rebuild/doctor/deploy/recovery.
- [Media operations reference](../docs/reference/media-commands.md) — compact read/write/maintenance catalog.
- [Cross-system invariants](../docs/reference/invariants.md) — MUST/MUST NOT правила.
- [Current status](../docs/status/current.md) — durable capabilities и known limitations.

Исторические design specs/plans под `../docs/superpowers/` объясняют rationale, но не заменяют current code, schemas, `AGENTS.md` и living docs.

## Operating contract

Перед agent/LLM работой читайте [`AGENTS.md`](AGENTS.md). Он определяет intent routing, evidence hygiene, typed write protocol, target safety, auto-merge boundaries и hard guardrails.

[`START_PROMPT.md`](START_PROMPT.md) — human-facing launcher нового киноассистента, а не developer manual.

`V5_STATUS.md` сохранён как compatibility path и перенаправляет на durable [`docs/status/current.md`](../docs/status/current.md).

## CLI quickstart

```bash
python -m media.cli search "Arrival" --format json
python -m media.cli show arrival-2016 --format json
python -m media.cli taste-context --request taste.json --format json
python -m media.cli recommend-context --request request.json --format json
python -m media.cli assess-candidate --request assessment.json --format json
python -m media.cli apply-command request.json --dry-run --format json
python -m media.cli rebuild --check
python -m media.cli doctor --format json
python -m media.tools.archive_library --output docs/archive/media-library-before-v6-reset-2026-10-07.md
python -m media.tools.archive_library --output docs/archive/media-library-before-v6-reset-2026-10-07.md --verify
```

Full verification and explicit build commands live in the [operations runbook](../docs/guides/operations.md).

## Core boundaries

- Normal media mutations use strict typed commands; LLM/browser code does not patch canonical YAML directly.
- Read-only `recommend_context`, `taste_context` and `assess_candidate` do not mutate canonical state.
- External recommendation/candidate/similarity references do not implicitly create canonical works.
- Explicit similarity is useful recommendation/explanation evidence, but is not a preference by itself.
- Unknown identity/metadata/vocabulary is not guessed.
- Architecture, schemas, vocabulary, workflows and bulk maintenance use the manual developer/review route.
- Browser write/provider/model secrets remain outside the static Pages bundle.


## Pre-v6 human archive tool

`media.tools.archive_library` создаёт детерминированный человекочитаемый MD-снимок активной библиотеки и умеет побайтно проверить зафиксированный файл повторной регенерацией из canonical YAML. В архив попадают названия/годы и только человечески полезные пользовательские сигналы; технические ID, provider/provenance, digests, semantic fingerprints и inferred preferences исключены.

Файл `docs/archive/media-library-before-v6-reset-2026-10-07.md`, созданный в PR 3, является **review snapshot**. Перед деструктивным reset в PR 4 он обязательно генерируется заново из точного предсбросового `main` и проходит `--verify`; только после этого разрешён reset.
