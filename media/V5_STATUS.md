# Media Intelligence v5.1 — compatibility status

Media Intelligence v5.1 is the current implemented capability line.

The durable current state now lives in [`../docs/status/current.md`](../docs/status/current.md). Read that file for implemented capabilities, known limitations and the verification model.

## Why this file remains

`media/V5_STATUS.md` is kept as a compatibility path for older agent/bootstrap instructions and links. It is no longer a development diary or the authoritative place for feature-task progress.

Historical v5/v5.1 design decisions, pilot notes and implementation plans remain available under `../docs/superpowers/specs/` and `../docs/superpowers/plans/`, plus merged PR history. Those documents are historical rationale, not current project status.

## Safe resume rule

When resuming interrupted development:

1. verify current `main`;
2. inspect the active PR and its latest checkpoint, if one exists;
3. read [`../docs/status/current.md`](../docs/status/current.md) for durable system state;
4. then load only the architecture/reference docs relevant to the unfinished task.

For ordinary media use, start with [`AGENTS.md`](AGENTS.md) and follow the shortest route matching the user intent. This compatibility file does not need to be read before every normal media operation.

## Current v5.1 anchors

- read-only `assess_candidate` for qualitative candidate assessment;
- explicit `set_work_similarity` / `remove_work_similarity` relations, including stable external endpoints and deterministic reconciliation;
- similarity as recommendation/explanation evidence, not preference by itself;
- manifest v3 explicit similarity projection on the static web surface;
- strict typed mutation pipeline with exact-revision validation and guarded operation-specific merge policy.
