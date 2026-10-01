# Media Write UX v1.2 Amendment

## Status

Approved by the user on 2026-10-01 and implemented as a narrow amendment to `2026-10-01-media-tooling-orchestration-design.md`.

This document supersedes only the original first-version statements that excluded automatic merge and required every normal media-operation PR to remain manually mergeable/reviewable. All other tooling/orchestration design constraints remain in force.

## Motivation

The first production feedback flow proved the typed command pipeline, but exposed one unnecessary user-facing step. After the user had already clearly asked to record feedback and, when needed, answered a single identity clarification, the assistant still asked for a second confirmation such as “сохраняй” before merge.

That second confirmation does not add useful semantic consent. The original feedback/save request already authorizes the normal data mutation. Requiring another confirmation makes the assistant feel like a GitHub operator interface instead of a cinema assistant.

## UX rule

A clear request to record or save a normal media change is authorization to carry that operation through to completion.

If one blocking clarification is required only to resolve the work, viewer/target, or meaning, the assistant continues the already-authorized write after the answer. It does not ask for another merge/finalization confirmation.

Explicit user requests to preview, defer, or not save yet always override this rule.

The assistant must not say that data was saved until the operation is actually merged and the resulting data is visible on `main`.

## Guarded auto-merge scope

Automatic merge is allowed only for successful typed normal-data operations produced by the existing command pipeline.

An operation is eligible only when all of the following are true:

- the authoritative `Media Check` run completed successfully;
- that check was the dispatched exact-head check for a `media/op-*` branch;
- the PR is still open, same-repository, and targets `main`;
- the PR head SHA is unchanged from the SHA that was checked;
- the operation result head was produced by `github-actions[bot]` through the trusted command workflow;
- the final diff contains only the existing normal-operation allowlisted data/generated/audit paths;
- there is exactly one `.media/operations/*.json` receipt and it reports `status: applied`;
- the operation kind is one of the explicitly auto-merge-enabled write commands (`add_work`, `record_viewing_feedback`, `set_interest`).

The merge API call must include the checked head SHA so a race that changes the PR after verification fails closed.

## Explicit exclusions

The guarded path must never auto-merge changes to code, schemas, vocabulary, agent instructions, tests, documentation, configuration, or GitHub workflows. Those remain ordinary manually reviewed architectural/development PRs.

The privileged auto-merge workflow must not checkout or execute code from the media-operation branch. It evaluates GitHub metadata and operation outputs only, and receives the minimal repository permissions required to perform the merge.

## Failure behavior

If any eligibility check, verification step, or merge fails, the PR remains unmerged and the assistant must not claim that the user's data was saved. User-facing reporting should describe only the minimal blocker unless technical detail is requested.

## Verification

The change is accepted only with a demonstrated RED→GREEN regression cycle covering the no-second-confirmation contract and the presence of the guarded auto-merge workflow, plus the repository's full `Media Check` gate:

```text
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```
