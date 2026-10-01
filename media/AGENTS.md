# Media v4 agent contract

This directory is a canonical personal media library. Git/YAML is source of truth; `generated/` is derived.

## Required read order before writes

1. Read this file.
2. Read the relevant schema under `media/schemas/`.
3. Read `media/vocabulary.yaml` before using semantic terms.
4. Search existing works, external IDs, alternate titles and tombstones before creating anything.

## Hard guardrails

- Never invent schema fields.
- Never create a vocabulary synonym before checking canonical terms and aliases.
- Unknown is better than guessed. Leave unknown factual metadata absent/null.
- Do not create viewer/group signals without evidence.
- Preserve `explicit` vs `inferred` provenance and confidence.
- `unwatched` and `dropped` are not negative reactions by themselves.
- Reaction, rating, viewing, feedback, rewatch and interest are independent signals.
- Do not persist ephemeral recommendation context such as "not tonight" as a stable preference.
- Normal data entry must not modify schemas. Schema/vocabulary migrations are separate architectural changes.
- Never edit `generated/` as source data.
- Immutable IDs are not renamed. Use tombstones/redirects for merges.
- Collection membership is canonical only in collection files; reverse membership is derived.
- Season records are optional and must not be fabricated for completeness.
- Manual metadata overrides always win over refreshed external metadata.
- Run full validation before commit.

## Canonical write protocol

For one logical user operation:

1. Resolve target (`primary`, `partner`, `couple`).
2. Deduplicate by TMDB `(media_type,id)`, IMDb ID, immutable internal ID, then title/year.
3. Resolve tombstones/redirects.
4. Enrich factual metadata only when a trustworthy provider is available; TMDB is the preferred provider, not a schema dependency.
5. Normalize semantic values to canonical vocabulary IDs.
6. Prepare the full change-set without touching generated artifacts.
7. Run `python -m media.tools.validate .`.
8. Rebuild index/profiles/SQLite as needed.
9. Commit one logical operation as one Git commit.

If validation fails, canonical data must not be left partially modified.

## Natural-language input

The user should be able to say, for example: "Посмотрели X, мне 8.5, жене понравилось". Translate that into existing v4 fields; do not ask the user to speak YAML. A relayed partner opinion is a real `partner` signal when the user is clearly conveying that opinion.
