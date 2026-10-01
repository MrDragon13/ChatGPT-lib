# Media Tooling & Orchestration Design

## Status

Approved conversational design; written spec pending final user review.

This spec extends the personal media v4 architecture. It does not replace the canonical Git/YAML model. Its purpose is to define the runtime/tooling layer that lets ChatGPT, a CLI, and a future web/API client read and mutate the same media library safely without duplicating business rules.

## Goals

1. Keep Git/YAML as the canonical source of truth.
2. Give ChatGPT a small typed command surface instead of direct YAML editing.
3. Reuse the same domain/service logic from ChatGPT workflows, local CLI, and a future HTTP API.
4. Keep GitHub-native operation for the first version; no permanently hosted application server is required.
5. Keep LLM reasoning out of deterministic integrity-sensitive operations.
6. Use GitHub Actions as an execution/verification host, not as the home of business logic.
7. Make normal writes atomic, idempotent, validated, auditable, and reviewable through PRs.
8. Support fast recommendation retrieval without loading every work YAML into the model context.

## Non-goals for the first implementation

The first implementation will not include a web UI, hosted HTTP API, OpenAI API calls from GitHub Actions, embeddings/vector search, scheduled metadata refresh, automatic merge, multi-provider metadata consensus, a full person graph, or ML-based ranking.

## Architectural principles

### Canonical data remains unchanged

The existing v4 rules remain authoritative:

- canonical user/media data lives under `media/data/`, `media/config/`, `media/preferences/explicit/`, and the controlled vocabulary/schema files;
- `media/generated/` is derived;
- SQLite is rebuildable and not committed;
- viewer/group signals are independent;
- unknown information is not guessed;
- schemas and vocabulary are not modified as a side effect of normal media data entry.

### One business logic layer

The same service layer must be used by:

- the local CLI;
- GitHub Actions processing typed requests;
- future API/web clients.

Business rules such as identity resolution, deduplication, signal merging, vocabulary checks, and transaction validation must not be reimplemented in prompts or workflow YAML.

### LLM for semantics; code for integrity

The LLM is responsible for:

- interpreting natural-language requests;
- selecting an allowed semantic operation;
- extracting explicit versus inferred user signals;
- classifying free-form feedback into existing controlled vocabulary terms;
- recommendation reasoning and explanation;
- asking for clarification when identity is genuinely ambiguous.

Deterministic code is responsible for:

- ID resolution and deduplication;
- schema and vocabulary validation;
- signal merge semantics;
- TMDB requests and factual metadata normalization;
- serialization;
- atomic change application;
- derived rebuilds;
- Git/PR orchestration and idempotency checks.

The LLM never receives an unrestricted shell command or a generic arbitrary-write operation.

## Package structure

The target structure is:

```text
media/
├── cli.py
├── domain/
│   ├── commands.py
│   ├── changeset.py
│   ├── errors.py
│   └── types.py
├── service/
│   ├── query.py
│   ├── resolve.py
│   ├── mutate.py
│   ├── recommend.py
│   ├── enrich.py
│   └── transaction.py
├── repository/
│   ├── canonical.py
│   ├── yaml_repo.py
│   ├── index_repo.py
│   └── sqlite_repo.py
├── providers/
│   ├── base.py
│   └── tmdb.py
├── commands/
│   └── schemas/
│       ├── add_work.schema.json
│       ├── record_viewing_feedback.schema.json
│       ├── set_interest.schema.json
│       └── recommend_context.schema.json
└── tools/
    ├── validate.py
    ├── build_index.py
    ├── build_profiles.py
    ├── build_db.py
    └── doctor.py
```

Existing v4 builders/validator remain the foundation and should be reused rather than rewritten unless a concrete limitation is discovered.

## Domain commands and public tool surface

The long-term semantic operations are:

```text
read/search:
  search
  show
  profile
  recommend-context

write:
  add-work
  record-viewing-feedback
  set-interest
  add-relation
  update-list

maintenance:
  enrich
  validate
  rebuild
  doctor
```

The first implementation intentionally exposes only:

- `search`;
- `show`;
- `add-work`;
- `record-viewing-feedback`;
- `set-interest`;
- `recommend-context`;
- `doctor`.

`record_viewing_feedback` is a single atomic user operation capable of carrying viewing state, rating, reaction, and feedback for one or more targets. This avoids creating several independent commits for the common case: “we watched X, I rate it 8.5, partner liked it.”

Each operation has a strict JSON Schema. The model outputs typed command JSON, never free-form YAML patches.

Example:

```json
{
  "schema_version": 1,
  "operation_id": "01K...",
  "operation": "record_viewing_feedback",
  "work_ref": {"title": "Arrival"},
  "target_updates": [
    {
      "target": "primary",
      "viewing": {"status": "watched"},
      "rating": {"score": 8.5, "source": "explicit_approx"}
    },
    {
      "target": "partner",
      "viewing": {"status": "watched"},
      "reaction": {"value": "liked", "source": "explicit"}
    }
  ]
}
```

## ChangeSet and transactional writes

A validated command is converted to an internal `ChangeSet` before touching canonical files.

Conceptually:

```yaml
operation_id: 01K...
operation: record_viewing_feedback
summary: Record viewing feedback for Arrival
changes:
  - entity: arrival-2016
    action: update
derived:
  rebuild_index: true
  rebuild_profiles:
    - primary
    - partner
    - couple
```

The write lifecycle is:

```text
received
→ command-schema validated
→ identities resolved
→ full ChangeSet planned
→ applied in temporary workspace
→ canonical validation
→ derived rebuild
→ integration checks
→ committed to branch
→ ready_for_merge
```

If any validation/rebuild/check fails, the canonical branch must not be left partially modified.

CLI/service operations support a dry-run mode that reports the resolved entity and proposed semantic changes without committing them.

## Repository abstraction

Define one canonical repository interface for domain/service code, for example:

```python
class CanonicalRepository:
    def get_work(...): ...
    def search_works(...): ...
    def get_collection(...): ...
    def apply_changeset(...): ...
```

`YamlRepository` is the write-capable canonical implementation.

`IndexRepository` and `SQLiteRepository` are read optimizations only. They do not expose a canonical write method.

Local/runtime query policy:

- local CLI/site may prefer fresh SQLite for complex queries;
- GitHub/ChatGPT uses `generated/index.jsonl` as the portable first retrieval layer;
- both paths fall back to canonical YAML for full entity detail.

## Read and recommendation path

ChatGPT should not load every work YAML for each recommendation.

Recommended flow:

```text
user request
→ resolve target + ephemeral request constraints
→ generated/index.jsonl retrieval/filter
→ generated/profiles/<target>.yaml
→ shortlist
→ load only relevant full work YAMLs
→ LLM reasoning/explanation
```

Ephemeral request context such as “not dark tonight” is not persisted as a stable preference.

Two retrieval modes are supported conceptually:

- `fast`: index + profile + compact history/evidence;
- `deep`: shortlist first, then selected full work records for richer reasoning.

`recommend-context` returns structured evidence rather than a single opaque score. An internal ranking score may be used for sorting but is not canonical user data.

Recommendation interactions should distinguish temporary skips from durable preference:

- “not today” may create an interaction such as skipped/not_today;
- “I never want to watch this” may update durable interest to `not_interested`.

Persisting recommendation interactions beyond the operations explicitly included in the first implementation is deferred until a dedicated command contract is added; the semantic distinction above is still normative.

## Metadata enrichment

Factual enrichment uses a provider abstraction and does not require an LLM.

Initial provider:

```text
MetadataProvider
└── TMDBProvider
```

Provider responses are normalized into a canonical metadata DTO before they can affect YAML. External provider JSON is never copied directly into canonical storage.

Manual metadata overrides continue to win over provider refreshes.

A TMDB read token may be stored in GitHub Secrets for workflows that need factual enrichment. OpenAI/API model credentials are explicitly out of scope for GitHub Actions in this version.

Semantic enrichment, when used, may be proposed by an LLM only from existing vocabulary IDs. If the needed concept is missing, the result is “needs vocabulary extension”; normal data entry must not create a new vocabulary term automatically.

## GitHub-native runtime

The first runtime has no permanent server.

### Reads

ChatGPT reads `generated/index.jsonl`, generated profiles, and selected canonical YAML directly through GitHub access.

### Writes

ChatGPT creates a small typed command request on a dedicated same-repository branch, preferably named `media/op-<operation_id>`, and opens a PR. GitHub Actions is the remote execution host:

```text
ChatGPT
→ typed request
→ trusted same-repo branch / PR
→ media-command workflow
→ Python service layer
→ canonical YAML changes
→ validation + derived rebuild
→ commit updates to same PR branch
```

GitHub Actions contains orchestration steps only. The domain behavior remains in Python modules.

The transient request may live at `.media/requests/<operation_id>.json` while the workflow is processing it. A successfully applied command removes that request from the final PR diff. The request directory is transport, not source of truth.

## GitHub workflows

### `media-check.yml`

Runs for media-related PRs and acts as the normal merge gate:

1. install dependencies;
2. run full pytest suite;
3. run canonical validator;
4. rebuild index into temporary output and compare with committed generated index;
5. rebuild profiles into temporary output and compare with committed profiles;
6. build SQLite from canonical state;
7. run `media doctor`.

Generated text artifacts must be deterministic and byte-identical for the same repository revision.

### `media-command.yml`

Processes a typed media command from a trusted same-repository media operation branch:

1. verify the PR/head repository and reserved operation branch pattern;
2. validate command JSON Schema;
3. check `operation_id` idempotency;
4. resolve entities;
5. optionally use TMDB where required;
6. plan and apply ChangeSet in a temporary workspace;
7. validate canonical state;
8. rebuild generated text artifacts;
9. verify the resulting diff against the operation-specific write allowlist;
10. remove the transient request;
11. commit the resulting canonical/generated/audit changes to the same branch;
12. produce a machine-readable result.

The command workflow must not expose secrets or obtain write-back behavior for untrusted fork PRs. In the first implementation, command execution is supported only for same-repository branches created for media operations.

The workflow must avoid self-trigger loops after it pushes its result commit, for example by requiring the transient request to exist before the apply job runs.

### `media-maintenance.yml`

Manual workflow for deterministic maintenance such as doctor/rebuild and explicitly selected metadata refreshes. No model inference runs inside this workflow.

## Idempotency and concurrency

Every mutable command requires an immutable `operation_id`.

Retrying the same operation must return `already_applied` (with the original commit/result where possible) rather than duplicating interactions or mutations.

A lightweight technical operation receipt may be committed under `.media/operations/<operation_id>.json`; it is orchestration/audit metadata, not canonical media-domain data. Receipt content is intentionally minimal and must not duplicate private free-form feedback.

Commands are planned against a specific base SHA. If `main` changes before application, the system must not blindly apply an old textual diff. It reloads the latest entity state and replays the semantic command through normal resolution/merge/validation rules.

## Error model

Machine-readable failures include at least:

- `invalid_command`;
- `ambiguous_identity`;
- `not_found`;
- `provider_unavailable`;
- `conflict`;
- `validation_failed`;
- `generated_drift`;
- `already_applied`.

Example ambiguity response:

```json
{
  "status": "needs_input",
  "reason": "ambiguous_identity",
  "candidates": [
    {"id": "dune-1984", "title": "Dune", "year": 1984},
    {"id": "dune-2021", "title": "Dune", "year": 2021}
  ]
}
```

The LLM asks the user only when deterministic resolution cannot safely continue.

Provider outage must not block writes for already-resolved existing works that do not require provider data.

## Security and permissions

No command schema contains arbitrary shell/script fields.

GitHub workflow permissions should be minimal and scoped to what the job requires, expected to be primarily `contents: write` and `pull-requests: write` for the command workflow. Secrets are exposed only to jobs that need them and only after the same-repository trust check.

Normal command writes are default-deny. Every command type has an explicit output-path allowlist. For the first implementation, a command may change only the canonical entity files that its semantic operation owns, declared generated text artifacts, and its minimal `.media/operations/<operation_id>.json` receipt. The transient `.media/requests/<operation_id>.json` file must disappear from the final applied diff.

A normal command must never modify code, schemas, vocabulary, agent instructions, configuration of the command machinery, or GitHub workflows. This includes at least:

- `media/schemas/**`;
- `media/vocabulary.yaml`;
- `media/AGENTS.md`;
- `.github/workflows/**`;
- `media/domain/**`;
- `media/service/**`;
- `media/repository/**`;
- `media/providers/**`;
- `media/commands/schemas/**`.

Changes to these remain normal manually reviewed architectural PRs.

Auto-merge is not enabled in the first version. The first real operations are intentionally reviewable to build confidence in the pipeline.

## Doctor and observability

`media doctor` checks operational health beyond JSON Schema validity, including:

- generated index matches canonical state;
- generated profiles match canonical state;
- SQLite is rebuildable;
- no broken/orphan references;
- tombstone redirects resolve and do not cycle;
- aliases are not persisted where canonical vocabulary IDs are required;
- runtime artifacts such as `database.sqlite` are not committed;
- relevant metadata provenance/override invariants hold.

`doctor` and `apply-command` support both human-readable and JSON output.

Operational logs/results contain technical identifiers (`operation_id`, base SHA, resolved work IDs, changed files, result) but should avoid unnecessarily echoing full private user feedback into CI logs.

## Testing strategy

Four levels are required:

1. **Unit tests** for resolver, signal merge rules, command handling, ChangeSet generation, idempotency, and query logic.
2. **Contract tests** for command schemas, canonical schemas, vocabulary checks, provider normalization, and per-operation output-path allowlists.
3. **Integration tests** using a small synthetic fixture media repository and exercising command → apply → validate → rebuild → resulting files.
4. **Workflow smoke tests** for changes to GitHub workflow/orchestration code, including same-repo trust checks and self-trigger-loop prevention.

TMDB unit/integration tests use mocked or recorded fixtures. Normal pytest must not depend on live network access. A real-provider smoke test may be manual/separate.

Synthetic test fixtures must not copy private real-library feedback.

## First implementation scope

The first implementation proves the complete write/read loop, not every future feature.

Deliverables:

- domain command/ChangeSet types;
- canonical YAML repository implementation;
- index-based read repository and current SQLite read integration where useful;
- resolver/service layer;
- CLI entry point including `apply-command`;
- strict command schemas;
- `doctor`;
- TMDB provider abstraction + adapter;
- `media-check.yml`;
- `media-command.yml`;
- `media-maintenance.yml`;
- synthetic integration fixtures and tests.

Initial user-facing operations:

- search/show;
- add work;
- record viewing/rating/reaction/feedback atomically;
- set interest;
- build recommendation context.

## Acceptance criteria

The implementation is complete when all of the following hold:

1. “We watched Arrival; my rating is about 8.5; partner liked it” can become one valid typed command and one atomic canonical mutation.
2. The command resolves the existing work without duplication and correctly applies primary/partner signals.
3. Adding a new work resolves against existing IDs first, and when necessary can identify/enrich it through TMDB before canonical creation.
4. Recommendation context for a target is built from compact index/profile evidence without loading the entire canonical library.
5. Reusing an `operation_id` cannot duplicate signals or interaction effects.
6. Invalid mutations leave canonical repository state unchanged.
7. CI fails when canonical data changed but committed generated artifacts are stale.
8. A normal command attempting to mutate schema/vocabulary/tooling architecture, or any path outside its operation-specific allowlist, is rejected.
9. Rebuilding deterministic generated text artifacts twice from the same revision produces byte-identical output.
10. Full project tests, validator, generated drift checks, SQLite rebuild, and doctor are green before a normal media PR is considered ready to merge.
11. Secret-bearing command execution is rejected for fork/untrusted PR heads and accepted only for the explicitly supported same-repository media-operation flow.
12. A workflow result commit cannot recursively re-apply the same transient request.

## Deferred extensions

Once the GitHub-native version is proven, the same service layer may later be wrapped by an HTTP API and used by a web application. Embeddings, additional metadata providers, scheduled refresh, richer interaction analytics, autonomous model-assisted enrichment, and carefully constrained auto-merge can be added without changing the canonical model or duplicating the core mutation rules.
