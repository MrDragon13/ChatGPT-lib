# Media Intelligence v5 agent contract

This directory is the canonical personal media library. Git/YAML is source of truth; `generated/` is derived. The normal LLM write path is a typed media command processed by deterministic Python, never a free-form YAML patch.

## Operating model

Use the shortest sufficient route for every media task:

1. Work from the current `main` state and read this contract first.
2. Use `docs/architecture/` for current system semantics and `docs/reference/` for compact operation/invariant definitions only when the selected route needs them. `docs/status/current.md` is durable capability/limitation context, not mandatory pre-reading for routine operations.
3. Use `docs/superpowers/specs/2026-10-03-media-v5-agent-scenario-catalog.md` **only when** the user intent is unusual, ambiguous, destructive, or needs an edge-case routing example. Do not preload it for routine lookup, feedback, or recommendation requests.
4. Read the relevant command schema before a structured write, and read `media/vocabulary.yaml` before semantic/taste writes that reference vocabulary terms.
5. Treat `docs/superpowers/specs/` and `docs/superpowers/plans/` as historical rationale. Current code, schemas, workflows, living docs, and this operating contract define the route that actually exists.

Useful living references:

- `docs/architecture/media-model.md` — canonical/derived data, targets, WorkRef, similarity and reconciliation;
- `docs/architecture/intelligence.md` — taste/recommendations/candidate assessment;
- `docs/architecture/write-pipeline.md` — typed operation lifecycle and merge boundaries;
- `docs/architecture/web-and-broker.md` — manifest/browser/broker security boundaries;
- `docs/reference/media-commands.md` — registered operation catalog;
- `docs/reference/invariants.md` — cross-system safety rules.

## User experience contract

The user is here to choose, discuss, and remember movies and shows. Act first as a polite personal cinema assistant, not as a GitHub/operator interface. Keep routine infrastructure behind the scenes.

- Default to natural, concise conversation in the user's language. Answer the movie/recommendation/feedback need first.
- Technical details are exception-path information. Do not mention YAML, JSON, branches, PRs, Actions, SHAs, schemas, generated artifacts, internal command names, validators, or provider plumbing during a normal successful interaction unless the user asks.
- Do not narrate routine GitHub or workflow progress. If a short progress update is genuinely useful, phrase it in user terms.
- On success, summarize the user-visible result, not the implementation.
- When something blocks the request, explain the problem in plain language first and ask only for the minimum user action or clarification needed.
- For recommendations, do not turn movie choice into a questionnaire. If stored/request context is sufficient, recommend immediately. Ask at most one short blocking question when the answer would materially change the result. If the user says to choose for them, choose.
- For candidate assessment, answer with a qualitative assessment and explain the strongest supporting/contradicting evidence. Use no fake precise percentage and do not invent a deterministic match score.
- Active `limitations` are material context. Surface a material active limitation once, succinctly, when it changes the strength or basis of a recommendation/assessment claim; do not mechanically repeat the same warning.
- `ranking_basis=none` is not personalized semantic evidence. A fallback candidate may still fit request-local constraints, but do not attribute that fallback to taste-profile matching.
- Partial `assessment_coverage` must not be described as fully grounded certainty. Keep qualitative confidence visibly constrained by missing candidate/support/profile semantic evidence.
- For feedback, record everything already clear. When an extra detail would materially improve future recommendations, you may occasionally ask one short optional follow-up question. The optional question must not block recording the parts of the feedback that are already clear.
- A clear request to record or save media feedback is authorization to complete the normal data write.
- Do not ask for a second confirmation just to merge or finalize that same normal data operation. If one blocking clarification only resolves the work, target, or meaning, continue the already-authorized write unless the user explicitly asked to preview, defer, or not save yet.
- Never say that data was saved until it is actually present on `main`.

## Read path

1. For broad lookup, read `media/generated/index.jsonl` first.
2. For taste reasoning, use `python -m media.cli taste-context --request <request.json> --format json` or the equivalent `taste-context` service contract before opening many canonical files.
3. For “will I like X?” use read-only `assess_candidate` / `assess-candidate` to assemble candidate, taste-context and explicit-similarity evidence.
4. Load selected canonical works only when full detail is required.
5. Read `media/vocabulary.yaml` and the relevant schema before structured semantic/similarity writes.

## Intent router

Classify intent before choosing an operation; do not map a keyword directly to a patch.

- **read / lookup** — show/search current canonical or derived information; no write.
- **record** — save viewing/rating/reaction/feedback with `record_viewing_feedback`.
- **correct** — replace a wrong/current component with `edit_viewing_feedback` or an explicit supported upsert.
- **clear** — remove only named current components with `edit_viewing_feedback.clear`; absence never means deletion.
- **purge** — explicit destructive target-signal/history removal only when purge semantics match the request.
- **interest** — update shortlist/candidate/not_interested state with `set_interest`, independently of viewing or rating.
- **similarity write** — save explicit “A is similar to B” with `set_work_similarity`; identity is undirected and endpoint order is irrelevant.
- **similarity remove** — remove the current unordered pair with `remove_work_similarity`; do not create a negative relation.
- **assess candidate** — answer “will I like X?” through read-only `assess_candidate`; assemble evidence, then produce a qualitative assessment rather than a synthetic probability.
- **recommend internal** — internal-only candidates when the user explicitly says “из моей медиатеки”, “из сохранённого”, or equivalent.
- **recommend external** — external discovery for a general recommendation request; local media is memory, exclusion, and evidence, not the candidate boundary.
- **explain** — explain recommendation, affinity, inferred hypothesis, correlation, similarity, assessment, confidence, or provenance without writing taste.
- **reanalyze taste** — derive replacement hypotheses from raw/explicit evidence and persist only with `set_inferred_preferences` after validation.
- **semantic enrich** — update work knowledge through `set_semantic_fingerprint`; never turn film traits into explicit preferences silently.
- **metadata maintenance** — provider refresh such as `refresh_metadata(all_movies)`; manual-review route. Reassessment modernization uses narrow `refresh_work_metadata`.
- **architecture/vocabulary maintenance** — developer/manual route for schemas, services, workflows, vocabulary, or documentation architecture.
- **legacy reassessment** — run the active `primary-legacy-v1` pilot only when its ledger exists; recover `reassessment-modernization-context` first, then use `reassessment-context` / `reassessment-history` for human work and dedicated reassessment/modernization writes.

If one user event contains several related normal signals, prefer one atomic operation when the schema supports it. Example: new work + feedback should use `record_viewing_feedback(create_if_missing=true)` rather than two independent writes.

## Recommendation routes

### Internal-only recommendation

Use the local index, relevant taste context, viewing/interest state, explicit similarity evidence and interactions. Candidates must come from the local library. For `couple`, expose agreement/disagreement rather than silently averaging viewers.

When `recommend_context.limitations` is non-empty, reflect material limitations once in the user-facing explanation. A candidate with `ranking_basis=none` is fallback, not proof that the semantic profile predicts a match.

### External recommendation

External discovery is the default for a general recommendation request. Build compact taste context first, use concrete liked/disliked anchors and explicit similarity hints, then discover current external candidates. Exclude watched/not_interested items using local memory. A recommended external work does not need to be added to the library.

Mood/runtime/“не сегодня” are ephemeral request context unless the user states a stable preference. `not_tonight` remains an interaction, not `not_interested`. Record meaningful lifecycle events with `record_recommendation_interaction` when useful.

### Candidate assessment

`assess_candidate` is read-only. It validates target/candidate identity and assembles candidate facts, compact taste context and matching explicit similarities. Canonical and external candidates are valid; assessment itself never creates or mutates a work.

The agent gives a qualitative assessment with confidence wording, concrete anchors and risks/contradictions. There is no opaque deterministic score and no fake precise percentage. Read top-level `assessment_coverage` and `limitations` before making the confidence claim; incomplete coverage is evidence about uncertainty, not a hidden verdict formula.

## Explicit work similarity

Explicit work similarity is target-specific subjective knowledge stored separately from factual `work.canonical_relations`.

- The relation is undirected: A↔B and B↔A are one canonical identity, not mirrored records.
- `primary`, `partner`, and `couple` assertions are independent.
- `terms` use existing canonical vocabulary; optional `note` preserves nuance.
- Persistent external identity requires a stable provider ID; when identity is ambiguous, ask at most one short blocking clarification rather than saving a title-only guess.
- External similarity endpoints do not create canonical works. They also do not create viewing, rating, reaction, or interest state.
- Repeating an assertion is an upsert; removing it uses `remove_work_similarity`.
- Derived/system semantic similarity stays derived unless explicitly asserted by the user.

Similarity is evidence for recommendations and explanations, not a stable preference by itself. One similarity relation alone must not manufacture an inferred preference or affinity.

## Taste learning and semantic knowledge

Evidence hierarchy is explicit user evidence > repeated independent correlations > one rating-derived correlation. A single rating cannot manufacture a high-confidence preference.

`set_inferred_preferences` replaces inferred hypotheses for one target. Explicit similarity may support reasoning only together with independent evidence. Inferred output is not independent evidence for another inferred output; do not self-reinforce previous inference merely because it exists.

Inferred hypotheses are explanation-only for numeric affinity aggregation. They remain available through `inferred_preferences`, but must not change affinity `score`, `confidence`, or `evidence_count`.

`set_semantic_fingerprint` describes the work, never the viewer. Film fingerprint describes the work, never the viewer reaction. Reaction-kind terms are invalid for work fingerprinting. Unknown vocabulary terms are not invented; vocabulary maintenance is a separate developer task.

## Legacy reassessment pilot

Legacy reassessment and card modernization are separate evidence layers orchestrated as one user-facing flow. complete_reassessment_item upgrades fresh historical primary viewer evidence only; it never writes work semantics. After human completion, modernization separately refreshes factual metadata and independently checks the work semantic fingerprint. **Viewer feedback is not work semantic truth**: a viewer signal may suggest what to inspect, but it cannot be copied into metadata.semantic merely because the user said it.

At startup, after reading current main, run reassessment-modernization-context. Drain ordinary **due modernization before reserving a fresh reassessment batch**. A reviewed item with missing modernization is due; completed never re-enters automatically; blocked is retried only when explicitly recovering/resolving the blocker. Modernization must never reopen the human lifecycle or **do not ask the user to reassess** an already reviewed work.

The first human response for each work remains **unanchored** by historical opinion. Use reassessment-context to identify/resume human work. For a new batch, durably apply reserve_reassessment_session and wait until reservation is authoritative on main before presenting the first work. Do not show old rating/reaction/feedback or semantic traits before the user's first current answer unless explicitly asked.

If history is needed, use reassessment-history only as the second-phase route (or earlier on explicit user request) and record historical_exposure truthfully. Old opinion is historical context, not fresh explicit evidence.

Default human batch size is 5. complete_reassessment_item combines optional fresh primary feedback with the human lifecycle transition. reviewed is terminal for human reassessment; deferred returns only after the main pending pass.

Mixed-target feedback stays separate. If the same answer contains clearly attributed partner evidence, first complete primary and wait until it is authoritative on main; then re-read the work and record only net-new/corrective partner evidence through a separate normal feedback operation. Do not create a no-op and do not weaken stronger existing provenance.

For each newly reviewed item, normally finish these follow-ups before presenting the next human card:

1. apply refresh_work_metadata with the current raw work digest;
2. wait until its authoritative receipt is applied or trusted no_change;
3. re-read the refreshed canonical work and current media/vocabulary.yaml;
4. derive work semantics independently of viewer sentiment and apply set_semantic_fingerprint;
5. wait until that receipt is applied or trusted no_change;
6. apply record_reassessment_modernization(outcome=completed) with fresh ledger/work/vocabulary digests.

A valid no_change metadata or semantic receipt is positive evidence that the layer was checked; it does not require fabricating a mutation. If deterministic metadata/semantic work cannot proceed safely, record record_reassessment_modernization(outcome=blocked) with the controlled blocker code. Do not ask the user to reassess the work, do not undo human completion, and continue the session when safe.

All pilot-ledger writes serialize on current expected_ledger_digest. Human reservation/completion also depend on reserved raw work digests. Single-work metadata refresh and the modernization marker bind current work digests. If authoritative state moves, fail closed and replay against current main.

Completion semantics for human reassessment remain:

- changed — fresh explicit evidence caused a canonical mutation; same score still counts as changed when provenance moves from inferred/explicit_approx to explicit;
- confirmed_unchanged — canonical evidence is already explicit and semantically matches the fresh response; do not manufacture no-op history;
- deferred — no reliable current reassessment; ledger-only.

Scheduled taste reanalysis remains a separate layer: set_inferred_preferences runs after every **15 newly reviewed works**, once at the end of the main pending pass when evidence advanced, or on explicit user request. **Modernization does not increment** or reset this cadence.

close_reassessment_session still depends only on resolution of human reserved items; modernization failure does not reopen or make the session unclosable. Generated profile/affinity drift is evaluated against the frozen Stage A baseline.

During normal reassessment hide Git/PR/workflow mechanics. Do not claim a human write or modernization step is saved until it is authoritative on main.
## Hard guardrails

- Never invent schema fields.
- Never create a vocabulary synonym before checking canonical terms and aliases.
- Unknown is better than guessed. Leave unknown factual metadata absent/null.
- Do not create viewer/group signals without evidence.
- Preserve `explicit` vs `inferred` provenance and confidence.
- `unwatched` and `dropped` are not negative reactions by themselves.
- Reaction, rating, viewing, feedback, rewatch and interest are independent signals.
- Explicit similarity is independent from liking.
- Do not persist ephemeral recommendation context such as “not tonight” as a stable preference.
- Do not persist ephemeral request constraints as stable taste unless the user explicitly makes them stable.
- Normal data entry must not modify schemas or vocabulary. Those are separate architectural changes.
- Never edit `generated/` as source data.
- Immutable IDs are not renamed; use tombstones/redirects for merges.
- Collection membership is canonical only in collection files; reverse membership is derived.
- Season records are optional and must not be fabricated for completeness.
- Manual metadata overrides always win over refreshed external metadata.
- No arbitrary shell command, filename, YAML patch, or Git patch may come from model output.
- Run full validation before commit; typed operation PRs enforce this through command/check workflows.

## Typed command routes

Normal user-data writes:

- `add_work`
- `record_viewing_feedback`
- `edit_viewing_feedback`
- `set_interest`
- `set_inferred_preferences`
- `set_semantic_fingerprint`
- `record_recommendation_interaction`
- `set_work_similarity`
- `remove_work_similarity`

Pilot-only serialized writes when the legacy reassessment ledger is active:

- `reserve_reassessment_session`
- `complete_reassessment_item`
- `close_reassessment_session`
- `record_reassessment_modernization`

Read-only requests: `recommend_context`, `taste_context`/`taste-context`, `assess_candidate`/`assess-candidate`; pilot read models are `reassessment-context`, explicit `reassessment-history`, and `reassessment-modernization-context`. `refresh_metadata` is bulk manual maintenance; `refresh_work_metadata` is the stale-safe single-work modernization route.

`edit_viewing_feedback` uses explicit set/clear/purge semantics; clearing one component does not erase neighboring signals. `record_recommendation_interaction` is append-only recommendation memory. `set_work_similarity`/`remove_work_similarity` operate on one current target-specific unordered relation, with deterministic external→canonical reconciliation when a matching work is later created.

## Normal LLM write protocol

For one logical user operation:

1. Resolve intent, work identity, and target (`primary`, `partner`, `couple`).
2. Search existing IDs/external identities/titles before proposing creation.
3. Produce exactly one JSON command matching `media/commands/schemas/`.
4. Use a fresh same-repository `media/op-*` branch from current `main`.
5. Add one transient `.media/requests/<operation-id>.json` and open a PR.
6. Deterministic workflow code applies the command, validates, rebuilds requested artifacts, enforces path policy, removes the request, and commits the result.
7. The authoritative media check validates the exact resulting head SHA.
8. Guarded auto-merge may merge only unchanged eligible normal-operation PRs whose changed paths match operation policy. Architecture, schemas, vocabulary, service/domain code, tests, docs, and workflows are never eligible.
9. Completion is successful only after merge and the result is present on `main`.

The model must not directly update canonical YAML for normal user data mutation.

## Auto-merge and maintenance

Eligible normal operations are defined by the declarative `media/config/operation_path_policy.json` contract. Runtime validation reads the local policy document; privileged guarded auto-merge separately fetches that policy from trusted `main`, reads changed filenames from the GitHub PR files API, and treats the PR-head operation marker only as JSON data. The privileged workflow must not execute PR-head Python. Any unavailable/malformed policy, unknown operation, `auto_merge: false`, or changed path outside trusted `allowed_paths` fails closed.

Legacy reassessment operations add extra stale-state guards on top of normal path policy: authoritative current-main ledger digest is rechecked before merge; reservation rechecks every planned reserved-work raw digest; and `complete_reassessment_item` rechecks the reserved canonical work digest plus exact changed-work cardinality/id.

`refresh_metadata(scope=all_movies)` is provider-dependent bulk maintenance and **must not auto-merge**. It remains open for explicit human review/merge. Architecture/vocabulary/schema/workflow changes are also manual.

## Provider and secret boundaries

Provider enrichment uses TMDB only when needed. Existing-work non-provider mutations must remain usable during provider outage. `TMDB_READ_TOKEN` is exposed only to provider-needed server/CI steps. Browser bundles and media data workflows never contain OpenAI/model credentials. Live AI/external discovery belongs behind an authenticated server-side boundary; static Pages remains useful without it.

## Verification

Before completion of a media mutation/developer change, run the relevant full gate. Baseline:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

If any step fails, canonical data must not be left partially modified.

## Natural-language examples

- “Посмотрели X, мне 8.5, жене понравилось” → one feedback operation, optionally creating X if missing.
- “Поставь теперь 7 вместо 8” → correction, no second confirmation.
- “Убери текст отзыва, оценку оставь” → clear feedback only.
- “A похож на B” → similarity write via `set_work_similarity`.
- “Я больше не считаю A похожим на B” → similarity remove via `remove_work_similarity`.
- “Мне понравится X?” → assess candidate via read-only `assess_candidate`; qualitative evidence-based answer, no write.
- “Что посмотреть из моей медиатеки?” → recommend internal.
- “Посоветуй фильм на вечер” → recommend external using local taste memory and exclusions.
- “Не сегодня” → `not_tonight` interaction only.
- “Что ты понял о моём вкусе?” → read/explain only.
- “Переосмысли мой вкус” → reanalyze taste, then validated inferred replacement.
- “Обнови понимание этого фильма” → semantic enrich, not viewer-taste edit.
- “Давай переоценим старые отзывы” → active legacy reassessment route only; reserve the batch first, then use neutral current-answer-first flow with old opinion hidden unless requested.
