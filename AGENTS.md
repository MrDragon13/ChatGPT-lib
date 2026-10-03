# Repository agent router

The current `main` branch is the repository source of truth. This file is a compact router; do not duplicate subsystem contracts here.

## Media bootstrap

For any task involving the personal media library, recommendations, taste/profile reasoning, the media website, or the media write broker:

1. Read `media/AGENTS.md` first. It is the normative media operating contract.
2. Read `media/V5_STATUS.md` second. It records the current implemented state, known limits, and safe resume point.
3. Treat `media/START_PROMPT.md` as a human-facing launcher for a new cinema-assistant chat, not as the operational contract.
4. Load schemas, vocabulary, design specs, or the scenario catalog only when the selected route actually needs them.

Normal media mutations must use the typed operation routes defined by `media/AGENTS.md`. Do not directly edit canonical media YAML or `generated/` as a shortcut.

## Scope routing

- Media data, ratings, feedback, interest, recommendations, taste reanalysis, semantic enrichment, and recommendation interactions → `media/AGENTS.md`.
- Media web/broker work → `media/AGENTS.md`, then `media/README.md` and the relevant `web/` or broker code/docs.
- Architecture, schemas, vocabulary, workflows, or maintenance → follow the explicit developer/manual route in `media/AGENTS.md`; historical specs are reference, not a replacement for current code and contracts.

When resuming interrupted work, verify current `main` and the active PR/status checkpoint before changing anything.
