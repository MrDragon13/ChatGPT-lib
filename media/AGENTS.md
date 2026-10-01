# Media v4 agent contract

This directory is a canonical personal media library. Git/YAML is source of truth; `generated/` is derived. The normal LLM write path is a typed media command processed by the deterministic service layer, not a free-form YAML edit.

## Read path

1. Read this file.
2. For broad lookup/recommendation, read `media/generated/index.jsonl` and the relevant `media/generated/profiles/<target>.yaml` first.
3. Load only the selected canonical work/collection YAMLs when full detail is required.
4. Read the relevant schema under `media/schemas/` and `media/vocabulary.yaml` before producing semantic write data.

## Hard guardrails

- Never invent schema fields.
- Never create a vocabulary synonym before checking canonical terms and aliases.
- Unknown is better than guessed. Leave unknown factual metadata absent/null.
- Do not create viewer/group signals without evidence.
- Preserve `explicit` vs `inferred` provenance and confidence.
- `unwatched` and `dropped` are not negative reactions by themselves.
- Reaction, rating, viewing, feedback, rewatch and interest are independent signals.
- Do not persist ephemeral recommendation context such as "not tonight" as a stable preference.
- Normal data entry must not modify schemas or vocabulary. Those are separate architectural changes.
- Never edit `generated/` as source data.
- Immutable IDs are not renamed. Use tombstones/redirects for merges.
- Collection membership is canonical only in collection files; reverse membership is derived.
- Season records are optional and must not be fabricated for completeness.
- Manual metadata overrides always win over refreshed external metadata.
- No arbitrary shell command, filename, YAML patch, or Git patch may come from model output.
- Run full validation before commit; typed operation PRs enforce this through `media-command.yml` and `media-check.yml`.

## Normal LLM write protocol

For one logical user operation:

1. Interpret the natural-language request and resolve the intended target (`primary`, `partner`, `couple`).
2. Search existing work IDs/external IDs/titles before proposing creation.
3. Produce exactly one JSON command matching a schema under `media/commands/schemas/`.
4. Use a fresh same-repository branch named `media/op-*` based on current `main`.
5. Add exactly one transient `.media/requests/<operation-id>.json` file and open a PR to `main`.
6. Let `media-command.yml` replay the branch on current `main`, execute `python -m media.cli apply-command`, validate, rebuild, enforce path policy, delete the request, and commit the result.
7. Require the read-only `media-check.yml` to pass on the exact resulting head SHA before merge.
8. Never auto-merge in v1; normal data PRs remain reviewable.

The model must not directly update canonical work YAML for a normal user data mutation. Manual maintenance by a human/developer may still edit canonical YAML, but must run the complete validation/rebuild/doctor gate.

## Typed command semantics

Initial commands are `add_work`, `record_viewing_feedback`, `set_interest`, and read-only `recommend_context`. `record_viewing_feedback` may carry viewing/rating/reaction/feedback for multiple targets atomically. `recommend_context` never writes interactions or persistent preferences in v1.

Factual enrichment uses TMDB only when required by `add_work`; existing-work mutations must not depend on provider availability. LLM semantic feedback may use only existing vocabulary IDs.

## Verification

Before a normal media PR is ready to merge:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

If any step fails, canonical data must not be left partially modified.

## Natural-language input

The user should be able to say, for example: "Посмотрели X, мне 8.5, жене понравилось". Translate that into one typed operation; do not ask the user to speak YAML. A relayed partner opinion is a real `partner` signal when the user is clearly conveying that opinion.
