# Repository layout

Карта основных путей ChatGPT-lib после Media Intelligence v6 cutover.

## Root

| Path | Responsibility |
| --- | --- |
| `README.md` | короткая project landing page |
| `AGENTS.md` | repository-level agent router |
| `PRODUCT.md` | media-web product brief |
| `DESIGN.md` | media-web visual/design-system contract |
| `docs/` | living docs + historical Superpowers artifacts + human archive |
| `media/` | canonical media domain, commands, services и generated read models |
| `web/` | static React/Vite GitHub Pages client |
| `broker/` | protected browser write boundary |
| `tests/` | executable contracts/fixtures |
| `.github/workflows/` | CI, typed-operation automation и Pages publish |
| `.media/` | transient requests + operation receipts |

## `docs/`

- `docs/architecture/` — current architecture;
- `docs/guides/` — usage/development/operations;
- `docs/reference/` — compact contracts/layout;
- `docs/status/` — durable current state;
- `docs/runbooks/media-v6-reset.md` — cutover/reset record and recovery rules;
- `docs/archive/media-library-before-v6-reset-2026-10-07.md` — human-readable historical checklist;
- `docs/superpowers/specs/` и `docs/superpowers/plans/` — historical rationale/plans.

Archive и historical specs не являются runtime input.

## `media/` canonical/configuration

- `media/data/works/` — canonical works; после reset каталог валидно пуст;
- `media/data/collections/` — collections;
- `media/data/lists/` — target lists;
- `media/data/interactions/` — recommendation interactions;
- `media/data/relations/similarity/` — explicit target-specific similarity;
- `media/data/tombstones/` — redirects/merged IDs;
- `media/preferences/explicit/` — explicit stable preferences;
- `media/preferences/inferred/` — evidence-backed hypotheses; после reset пусты до нового reanalysis;
- `media/config/viewers.yaml` / `groups.yaml` — targets;
- `media/config/intelligence.yaml` — algorithm versions/reanalysis threshold;
- `media/config/operation_path_policy.json` — operation path/execution policy;
- `media/vocabulary.yaml` — controlled semantic vocabulary;
- `media/schemas/` — canonical/read-model schemas;
- `media/commands/schemas/` — typed request schemas.

`media/pilots/legacy-reassessment-primary.json` и Stage A runtime baselines больше не существуют.

## `media/` code

- `media/domain/` — datatypes/contracts/errors;
- `media/commands/` — command parsing/schema registry;
- `media/service/` — deterministic mutation/read logic;
- `media/repository/` — persistence/read adapters;
- `media/providers/` — external metadata providers;
- `media/tools/` — validate/build/doctor/archive/audit utilities;
- `media/cli.py` — CLI.

## `media/generated/`

Derived, rebuildable output:

- `index.jsonl`;
- `profiles/*.yaml`;
- другие generated read models.

Runtime SQLite derived и не versioned; `doctor` может строить его во временном каталоге.

Generated state не редактируется вручную для изменения canonical meaning.

## `web/`

- React/TypeScript static client;
- читает exported manifest;
- не является canonical store;
- browser edits отправляет только через Broker.

## `broker/`

Stateless server-side boundary для browser writes. Production feedback преобразуется в `record_media_entry` и использует exact-main viewer digest.

## `.github/workflows/`

- `media-command.yml` — normal typed writes и manual maintenance branch preparation;
- `media-dev-check.yml` — полный developer media gate;
- `web-check.yml` — Web tests/build/browser;
- `broker-check.yml` — Broker tests/typecheck;
- `media-pages.yml` — exact-SHA Pages build/deploy;
- maintenance/deploy workflows по текущему назначению.

Отдельные `Media Check` и `Media Auto Merge` удалены.

## `.media/`

- `.media/requests/` — transient request files;
- `.media/operations/` — operation receipts.

Это не canonical user-authored storage.

## Где менять контракт

- domain/schema invariant → domain/schema + `architecture/media-model.md` / `reference/invariants.md`;
- typed operation → command/schema/service + `reference/media-commands.md`;
- taste/recommendation behavior → service + `architecture/intelligence.md`;
- write/CI → workflow/service + `architecture/write-pipeline.md`;
- Web/Broker boundary → code + `architecture/web-and-broker.md`;
- repository layout → этот файл;
- большое новое решение → dated Superpowers spec/plan, затем living docs после реализации.
