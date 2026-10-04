# Repository agent router

The current `main` branch is the repository source of truth. This file is a compact router; do not duplicate subsystem contracts here.

## Media bootstrap

For any task involving the personal media library, recommendations, taste/profile reasoning, the media website, or the media write broker:

1. Read `media/AGENTS.md` first. It is the normative media operating contract.
2. Use `docs/README.md` as the map to current living architecture, guides, reference, and status.
3. Read `docs/status/current.md` when the task depends on current capabilities/known limits or when resuming work; it is not required for every routine media operation.
4. Treat `media/START_PROMPT.md` as a human-facing launcher for a new cinema-assistant chat, not as the operational contract.
5. Load schemas, vocabulary, scenario examples, or historical `docs/superpowers/` specs/plans only when the selected route actually needs them. Historical documents explain rationale; they do not override current code, schemas, workflows, living docs, or operating contracts.

Normal media mutations must use the typed operation routes defined by `media/AGENTS.md`. Do not directly edit canonical media YAML or `generated/` as a shortcut.

## Scope routing

- Media data, ratings, feedback, interest, recommendations, taste reanalysis, semantic enrichment, similarity, and candidate assessment → `media/AGENTS.md` plus the relevant `docs/architecture/` or `docs/reference/` page when explanation is needed.
- Media web/broker work → `media/AGENTS.md`, then `docs/architecture/web-and-broker.md`, `PRODUCT.md` / `DESIGN.md`, and relevant code.
- Architecture, schemas, vocabulary, workflows, maintenance, or docs architecture → follow the explicit developer/manual route in `media/AGENTS.md` and `docs/guides/development.md`.
- Operational verification/recovery → `docs/guides/operations.md`.

When resuming interrupted work, verify current `main` and the active PR/status checkpoint first; then consult `docs/status/current.md` for durable project state.
