# Media Bulk Metadata Refresh Design

## Status

Approved in conversation on 2026-10-01; written design for review before implementation.

This design extends the existing Media v4 tooling with deterministic refresh of factual provider metadata for works that already exist in the canonical library. It does not change the canonical work schema and does not replace the existing `add_work` or feedback flows.

## User outcome

The library currently contains many valid schema-v4 work files whose canonical identity and user signals are present but whose factual metadata is sparse. A newly created work such as `masters-of-the-universe-2026` demonstrates the richer provider-backed representation already supported by the schema: provider IDs, release date, runtime, genres, countries/language, synopsis, credits, artwork, external metrics, and metadata provenance.

The goal is to bring the existing movie library to the same factual-metadata level where TMDB can supply the data, without changing the user's ratings, viewing history, reactions, feedback, semantic traits, relations, lists, or manual metadata overrides.

The initial migration targets all canonical works with `identity.format: movie`. Series/miniseries are deliberately out of scope for this pass.

## Alternatives considered

### 1. One-off manual YAML migration

Fetch TMDB data and directly rewrite every work file once.

This is rejected because it duplicates provider normalization outside the service layer, is difficult to retry safely, and leaves no reusable refresh path for future metadata updates.

### 2. Separate write-capable maintenance workflow

Add a new privileged GitHub Actions subsystem that discovers works, fetches TMDB, writes files, creates a branch, and opens a PR.

This would work, but it would duplicate orchestration and trust logic already present in the typed command pipeline.

### 3. Reuse the typed command/service pipeline with a deterministic maintenance command

Add a `refresh_metadata` command implemented in the existing domain/service layer and transported through the same `media/op-*` request/PR mechanism.

This is the selected approach. It keeps one business-logic layer, one transaction model, one path-policy mechanism, one provider adapter, and one verification gate. Unlike ordinary feedback operations, bulk refresh is explicitly excluded from guarded auto-merge and remains a manually reviewed maintenance PR.

## Command contract

Add mutable command `refresh_metadata`.

Initial v1.3 scope:

```json
{
  "schema_version": 1,
  "operation_id": "<uuid>",
  "operation": "refresh_metadata",
  "scope": "all_movies",
  "tmdb_overrides": {
    "optional-work-id": {
      "media_type": "movie",
      "id": 123
    }
  }
}
```

`scope` is intentionally limited to `all_movies` for this implementation. `tmdb_overrides` is optional and exists only to resolve deterministic identity blockers discovered during preflight; it must never be populated by guessing.

The command is provider-dependent and requires `TMDB_READ_TOKEN` only in the provider-bearing execution step.

## Identity resolution and preflight

Refresh must resolve every target work before any canonical mutation begins.

Resolution order for each movie:

1. Existing canonical TMDB composite ID (`media_type`, `id`) — fetch directly.
2. Existing canonical IMDb ID — resolve through TMDB external-ID lookup, then fetch the unique movie result.
3. Otherwise search TMDB using canonical `title_original` plus canonical year and accept only one exact normalized title/year match.
4. If `tmdb_overrides` contains the work ID, use that explicit TMDB composite ID after validating that the fetched provider record is compatible with the canonical work.

If zero or multiple plausible candidates remain, or if existing external IDs conflict with provider identity, preflight fails closed. The command returns the affected work IDs/candidates and performs no canonical write.

Provider/network failure for any target also aborts the bulk operation before mutation.

## Provider normalization

The existing `TMDBProvider` remains the only provider-specific adapter. It is extended where needed for IMDb external-ID lookup and reusable refresh behavior.

For an existing work, provider refresh may update or add:

- `identity.release_date`;
- `identity.external_ids.tmdb`;
- `identity.external_ids.imdb` when provider data supplies a non-conflicting value;
- `metadata.external.genres` using only existing canonical vocabulary IDs;
- `runtime_min`;
- `original_language`;
- `countries`;
- `production_status`;
- `synopsis_short`;
- `directors`;
- `writers`;
- `main_cast`;
- `assets.poster` and `assets.backdrop`;
- the TMDB entry in `external_metrics`;
- `metadata.external.provenance`.

Unsupported TMDB genre IDs are omitted rather than creating vocabulary as a side effect. Their omission should be visible in the machine-readable maintenance result/log summary so vocabulary can be extended separately if desired.

Certifications and content warnings remain absent unless a deterministic normalized mapping is explicitly implemented and tested; they are not guessed for completeness.

## Fields that must be preserved

Refresh must not overwrite the canonical/user-owned meaning of the work.

The following remain unchanged unless required only to add a non-conflicting external ID/release date as described above:

- immutable internal `id`;
- `identity.format`;
- `identity.medium`;
- `identity.title_original`;
- `identity.title_ru`;
- `identity.alternate_titles`;
- canonical `identity.year`;
- `metadata.overrides`;
- `metadata.semantic`;
- `viewer_signals`;
- `group_signals`;
- `target_states`;
- `seasons`;
- `canonical_relations`;
- provenance `created_at`.

`provenance.updated_at` changes only for work files whose canonical content actually changes.

Manual overrides continue to win over refreshed external metadata at read/use time; refresh never deletes them.

## Merge semantics for external metadata

Provider refresh replaces the current TMDB-owned factual snapshot rather than filling only previously null fields. This allows stale runtime, credits, artwork, synopsis, production status, and TMDB metrics to update.

If `external_metrics` contains entries for providers other than TMDB, those entries are preserved while the TMDB metric is replaced.

Absent provider fields do not erase manual overrides. For provider-owned external fields, normalized absence may remove stale provider data only when the provider response is authoritative for that field and the behavior is covered by tests; otherwise existing external value is preserved. This rule is deliberately conservative to avoid destructive refreshes caused by incomplete provider responses.

## Atomic bulk transaction

The refresh is all-or-nothing at the canonical-write level.

Lifecycle:

```text
validate typed command
→ enumerate all movie works
→ resolve/fetch/normalize every target (preflight)
→ build one complete mutation plan
→ apply all changes in temporary repository
→ validate canonical repository
→ rebuild generated index/profiles
→ run integrity checks
→ atomically sync planned files + operation receipt
→ commit result to operation PR branch
→ dispatch exact-head Media Check
```

Any identity ambiguity, provider outage, normalization error, validation error, rebuild error, or sync failure leaves canonical branch data unapplied.

The operation receipt contains technical IDs/counts only and must not duplicate private free-form feedback.

## Path policy and merge policy

`refresh_metadata` may modify only:

- direct `media/data/works/*.yaml` files;
- `media/generated/index.jsonl`;
- direct `media/generated/profiles/*.yaml` if the builders determine profiles changed;
- exactly one `.media/operations/*.json` receipt.

It may not modify schema, vocabulary, agent instructions, code, tests, configuration, collections/lists/interactions, or workflows as part of the data operation.

The existing guarded `media-auto-merge.yml` must continue to reject `refresh_metadata`. Bulk refresh is maintenance with a large diff and requires explicit human review/merge after the exact-head check passes.

## CLI and GitHub transport

Extend the existing command parser/service dispatch so `python -m media.cli apply-command request.json` can execute `refresh_metadata` with the same stable JSON/error model as other mutable commands.

`media-command.yml` recognizes `refresh_metadata` as provider-dependent, exposes `TMDB_READ_TOKEN` only to that provider-needed apply step, and otherwise reuses the existing same-repository trust guard, request deletion, path policy, validation, rebuild, commit, and exact-head check dispatch.

No model/API key is used in Actions. The LLM only creates the typed request and, when preflight reports genuine ambiguity, may ask the user for the minimum clarification necessary.

## Result reporting

Machine-readable success output should include at least:

- operation ID;
- number of targeted movie works;
- number changed;
- number already current/no-change;
- changed work IDs;
- omitted/unmapped provider genre IDs if any.

Preflight failure should aggregate identity blockers where practical rather than failing after the first ambiguous work, so a single correction pass can resolve the batch. Provider transport failure may terminate immediately.

Normal user-facing conversation remains concise: technical detail is shown only when a blocker requires action or the user asks for it.

## Testing strategy

Implementation follows TDD and adds coverage for:

1. strict `refresh_metadata` command schema/parsing;
2. TMDB direct composite-ID refresh;
3. IMDb-to-TMDB external-ID lookup;
4. title/year fallback resolution;
5. ambiguous/missing identity preflight with zero canonical mutation;
6. conflicting external IDs fail closed;
7. preservation of titles/year/user signals/semantic metadata/manual overrides;
8. replacement of provider-owned factual snapshot while preserving non-TMDB external metrics;
9. unsupported genres omitted and reported without vocabulary mutation;
10. multi-work all-or-nothing transaction and rollback;
11. idempotent replay by operation receipt;
12. generated artifact rebuild/currentness;
13. path-policy acceptance for refresh outputs and rejection of architecture paths;
14. workflow contract: TMDB secret only on provider-needed step;
15. workflow contract: `refresh_metadata` remains ineligible for auto-merge;
16. end-to-end synthetic bulk refresh using mocked TMDB fixtures.

Normal pytest must not call live TMDB.

## Initial migration procedure

After the implementation PR is merged:

1. create one `refresh_metadata(scope=all_movies)` operation against current `main`;
2. run preflight through the normal command workflow;
3. if identity blockers are reported, resolve them without guessing and rerun with explicit `tmdb_overrides` where needed;
4. once the bulk operation applies, inspect the resulting maintenance PR for unexpected identity/user-signal changes;
5. require exact-head `Media Check` success;
6. merge the maintenance PR manually;
7. verify `main` with validator, generated-current check, and doctor.

## Acceptance criteria

The feature is complete when:

1. every existing canonical movie can be deterministically resolved to TMDB or appears in an explicit blocker report without any partial canonical mutation;
2. a successful all-movies run enriches existing work files with normalized provider metadata comparable to newly created works where TMDB supplies the fields;
3. user ratings, viewing states, reactions, free-form feedback, semantic traits, manual overrides, IDs, and relations are byte-for-byte/semantically preserved except for expected serialization ordering where unavoidable;
4. external identity conflicts and ambiguous matches fail closed;
5. no schema or vocabulary change can occur as a side effect of refresh;
6. refresh is idempotent with respect to one operation ID and safe to retry after provider/preflight failure;
7. full project tests, canonical validation, generated drift check, SQLite rebuild, and doctor pass on the implementation;
8. the real library migration completes as one reviewed bulk maintenance PR with an exact-head green gate;
9. guarded auto-merge remains limited to the existing ordinary data commands and never merges this bulk maintenance command automatically.
