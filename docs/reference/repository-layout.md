# Repository layout

Карта основных путей ChatGPT-lib и их ответственности.

## Root

| Path | Responsibility |
| --- | --- |
| `README.md` | короткая project landing page |
| `AGENTS.md` | repository-level agent router |
| `PRODUCT.md` | media-web product brief |
| `DESIGN.md` | media-web visual/design-system contract |
| `docs/` | living docs + historical Superpowers artifacts |
| `media/` | canonical media domain, commands, services и generated read models |
| `web/` | static React/Vite GitHub Pages surface |
| `broker/` | protected browser write boundary |
| `tests/` | Python executable contracts/fixtures |
| `.github/workflows/` | CI, typed-operation automation, guarded merge, Pages publish |
| `.media/` | operation/request bookkeeping used by media automation |

## `docs/`

- `docs/README.md` — documentation map и authority model;
- `docs/architecture/` — current system architecture;
- `docs/guides/` — usage/development/operations;
- `docs/reference/` — compact contracts/definitions/layout;
- `docs/status/` — durable current project state;
- `docs/superpowers/specs/` — historical design rationale;
- `docs/superpowers/plans/` — historical implementation plans.

Historical paths сохраняются ради provenance и ссылок; они не заменяют living docs после реализации change.

## `media/` — canonical/configuration

- `media/data/works/` — canonical works;
- `media/data/collections/` — collections/franchises;
- `media/data/lists/` — target-scoped lists;
- `media/data/interactions/` — recommendation interaction events;
- `media/data/relations/similarity/` — explicit target-specific similarity;
- `media/data/tombstones/` — redirects/merged IDs;
- `media/preferences/explicit/` — explicit stable preferences;
- `media/preferences/inferred/` — evidence-backed inferred hypotheses;
- `media/config/` — viewer/group target configuration;
- `media/vocabulary.yaml` — controlled semantic vocabulary;
- `media/schemas/` — canonical/read-model JSON schemas;
- `media/commands/schemas/` — strict typed operation payload schemas.

## `media/` — code

- `media/domain/` — domain datatypes/contracts/errors;
- `media/commands/` — command parsing/schema registry;
- `media/service/` — deterministic application/read-model logic;
- `media/repository/` — canonical/index persistence access;
- `media/providers/` — external metadata provider integration;
- `media/tools/` — validation/build utilities;
- `media/cli.py` — CLI entry point.

## `media/generated/`

Derived, rebuildable output. Сюда относятся retrieval index, profiles и другие generated artifacts. Runtime SQLite тоже derived.

Правило ownership: generated state не редактируется вручную для изменения canonical meaning.

## `web/`

- `web/src/` — React/TypeScript application;
- `web/scripts/` — build/static artifact checks;
- `web/tests` или colocated tests — unit/browser contracts по текущей структуре;
- `web/package.json` — npm scripts/dependency contract.

Web читает exported manifest и не имеет права становиться вторым canonical store/recommendation engine.

## `broker/`

Server-side boundary для разрешённых browser writes. Broker не должен выдавать secrets browser bundle и не должен обходить typed media commands/validation.

## `.github/workflows/`

Ключевые классы workflows:

- normal typed media operation application/check/guarded merge;
- developer regression checks;
- web checks;
- maintenance;
- exact-revision Pages build/deploy.

Executable workflow YAML — authority для конкретных triggers/path policies.

## `.media/`

Service bookkeeping для typed operation pipeline: requests/receipts/operation metadata. Это не место для произвольных user-authored canonical YAML patches.

## Куда добавлять новый код/документ

- новый domain invariant → media domain/schema + `docs/architecture/media-model.md`/`docs/reference/invariants.md`;
- новая typed operation → commands/schema/service + `docs/reference/media-commands.md`;
- новая recommendation semantic → service/domain + `docs/architecture/intelligence.md`;
- write/CI change → workflow/service + `docs/architecture/write-pipeline.md`;
- web/broker boundary change → соответствующий code + `docs/architecture/web-and-broker.md`;
- rationale большого изменения → dated `docs/superpowers/specs/`, затем living docs после implementation.
