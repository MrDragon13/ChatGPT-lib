# Current status

Текущая capability line: **Media Intelligence v5.1**.

Этот файл описывает устойчивое текущее состояние проекта. Временный progress конкретной разработки хранится в active PR, а historical rationale — в `docs/superpowers/`.

## Реализовано

### Canonical и derived media

- Git/YAML остаётся canonical source of truth для media data, preferences, relations и configuration.
- Retrieval index, profiles, taste contexts, runtime database и web manifest являются derived и rebuildable.
- `primary`, `partner` и `couple` остаются независимыми subjective contexts; couple disagreement не скрывается автоматическим усреднением.

### Measurement foundation

Media Intelligence имеет read-only deterministic audit: `python -m media.tools.audit_intelligence . --format json`. Он отделяет works от collections, считает explicit coverage denominators, semantic/profile/similarity/interaction/recommendation-pool coverage и маркирует входное состояние через `canonical_input_digest`.

Audit считает runtime-relevant pool из canonical works в памяти и не использует generated profile/index bytes как источник истины. Historical snapshots хранятся под `media/baselines/`: deterministic payload отдельно от git/time provenance metadata. Snapshot является точкой сравнения, а не lockfile текущих данных.

### Typed operations

Normal media writes проходят через strict typed operations, deterministic transaction, validation/rebuild и operation-scoped GitHub workflow policy.

Поддерживаются viewing feedback, corrections, interest, inferred preferences, semantic fingerprints, recommendation interactions и explicit work similarity. Bulk `refresh_metadata` остаётся manual-review maintenance operation.

Guarded auto-merge теперь использует единый declarative `media/config/operation_path_policy.json`. Runtime проверяет локальный policy, а privileged workflow получает policy только из trusted `main`, changed-file inventory — через GitHub PR files API, и не исполняет PR-head Python для принятия решения о разрешениях. Policy/workflow/guard/executable-semantics changes поэтому остаются normal human-review developer PR.

Read-only context routes включают `recommend_context`, `taste_context` и `assess_candidate`.

### Candidate assessment

`assess_candidate` поддерживает qualitative ответ на вопрос «понравится ли мне X?» для canonical или external candidate. Он использует target taste context, concrete evidence works, semantic information и explicit similarity, но не сохраняет prediction и не создаёт fake precise match probability.

Assessment теперь возвращает top-level `assessment_coverage`: наличие candidate fingerprint, число directional candidate matches, request-local supporting-work fingerprint coverage и отдельный stable denominator по всем rated canonical works target. Для group target rated set учитывает member ratings и direct group rating как fallback, если member rating для work отсутствует. Top-level `limitations` остаётся fact-only (`no_candidate_semantic_fingerprint`, `no_candidate_personalized_basis`, `partial_semantic_coverage`) и не является deterministic verdict.

External candidate может быть оценён без добавления в canonical library; отсутствие его semantic fingerprint и personalized basis сообщается явно через limitations.

### Explicit work similarity

`set_work_similarity` хранит target-specific undirected user assertion между двумя works/references. `remove_work_similarity` удаляет ту же logical relation независимо от порядка endpoints.

Similarity может связывать canonical work и stable external identity. External endpoint не создаёт viewing/rating/interest или canonical work автоматически. Когда соответствующий work позже добавляется, deterministic reconciliation нормализует relation к canonical ID и устраняет duplicate/self-link состояния.

Explicit similarity используется как recommendation/explanation evidence и hint, но не является stable preference сама по себе.

### Taste и recommendations

Taste reasoning сохраняет provenance между explicit evidence, inferred hypotheses и semantic work knowledge. Inferred output не является independent evidence для последующего вывода. Generated profile хранит inferred hypotheses отдельно и не включает их в численные affinity `score`, `confidence` или `evidence_count`.

Internal recommendation request ограничивает candidate set локальной библиотекой. Его Stage A ranking сначала отделяет candidates с personalized semantic basis от fallback: `trait_overlap` всегда идёт раньше `none`. Personalized candidates сортируются по directional balance (`strengths - concerns`), затем по меньшему числу concerns, `interest.priority` и стабильному ID; fallback — только по priority и ID. Confidence и magnitude affinity пока не являются ranking weights, публичного numeric match score нет.

`recommend_context` сохраняет legacy strengths/concerns и добавляет structured evidence details, `ranking_basis`/`fallback_reason`, top-level pool-vs-returned `coverage` и top-level deterministic `limitations`. Эта policy является correctness/observability baseline, а не доказанной quality-optimal моделью.

Для group target `taste_context.couple.term_signals` отдельно показывает signed semantic direction каждого member по term и status `agreement`/`disagreement`/`insufficient`. Projection строится из индивидуальных member profiles, confidence не влияет на status, существующие rating-based couple agreements/disagreements сохраняются. Semantic disagreement не меняет couple aggregate; он только добавляет top-level limitation `couple_term_disagreement`.

General recommendation request допускает external discovery; library при этом служит памятью о вкусах, exclusions и evidence anchors.

### Legacy reassessment pilot

Pilot переоценки legacy `primary` reviews **активирован** отдельным manual PR B. Frozen Stage A revision: `35afaca898eae6937066f230906b41af0e1f6690`; frozen cohort содержит **55 works**: `23 central`, `10 high`, `10 low`, `9 medium_low`, `3 special`. На старте все 55 items имеют `pending`, sessions пусты.

Runtime foundation включает neutral/unanchored `reassessment-context`, отдельный opt-in `reassessment-history`, typed `reserve_reassessment_session` / `complete_reassessment_item` / `close_reassessment_session`, atomic feedback+ledger completion, current-ledger/work digests, monotonic transition validation и trusted workflow guards. Default session size — 5; scheduled inferred-hypothesis reanalysis — каждые 15 newly reviewed works и в конце main pending pass.

Legacy reassessment обновляет explicit user evidence; semantic fingerprint backfill в этот pilot не входит. `media/pilots/` хранит operational provenance и намеренно исключён из Stage A `canonical_input_digest`. Generated profiles/affinities могут ожидаемо drift по мере замены inferred/approx evidence на fresh explicit evidence; progress сравнивается с frozen Stage A baseline, а не с предыдущим generated profile.

### Web

Текущий exporter выдаёт **manifest v3**. Static GitHub Pages читает versioned derived manifest, а не canonical YAML.

Manifest v3 включает target-aware taste/recommendation data, semantic fingerprints и explicit similarity projection. Additive recommendation observability (`coverage`, `limitations`, candidate basis/reason) и couple term observability (`term_signals`) остаются в manifest v3, поскольку не меняют meaning существующих полей. Canonical↔canonical similarity проецируется на обе локальные work pages; canonical↔external отображается как lightweight external endpoint без выдуманного local route.

Поддерживаемые browser edits идут через protected broker и тот же typed-command boundary. GitHub/provider/model secrets не попадают в browser bundle.

## Известные ограничения

- Evidence для `partner` заметно менее насыщен, чем для `primary`; confidence reasoning должен отражать эту разницу.
- Current Stage A ranking исправляет directional correctness, но ещё не benchmarked как оптимальная модель качества; fingerprint length и alternative ordering policy остаются предметом будущего evaluation.
- Assessment coverage наблюдаема, но Stage A по-прежнему не вычисляет deterministic `likely/mixed/unlikely`, probability или opaque score; qualitative вывод остаётся agent responsibility с обязательным учётом active limitations.
- Couple term disagreement наблюдаем, но Stage A не меняет формулу couple aggregation и не вводит confidence threshold для direction/status.
- Derived semantic similarity не сохраняется как explicit user assertion и не показывается как пользовательское мнение без подтверждения.
- External discovery/live model reasoning находится на agent/server boundary; static Pages остаётся работоспособным без live model.
- Bulk provider metadata refresh требует manual review и не относится к normal auto-merge path.
- Controlled vocabulary расширяется только отдельным developer/architecture change, а не автоматически из обычного feedback.
- Legacy reassessment pilot активен, но первая durable reservation создаётся только при фактическом старте пользовательской сессии; smoke test не должен случайно потребить batch. Semantic fingerprint backfill остаётся отдельным будущим циклом.

## Verification model

Developer changes считаются проверенными только после релевантного полного gate: pytest, canonical validation, generated rebuild consistency и doctor; web-impacting changes дополнительно проходят web tests, typecheck/build и browser/static security checks.

Для публикации важна exact revision: Pages build/deploy должен соответствовать merge revision, а не более раннему зелёному commit.

## Где читать подробнее

- `docs/architecture/overview.md` — system boundaries;
- `docs/architecture/media-model.md` — canonical/derived domain model;
- `docs/architecture/intelligence.md` — taste/recommendations/assessment;
- `docs/architecture/write-pipeline.md` — typed mutation lifecycle;
- `docs/architecture/web-and-broker.md` — manifest, Pages и security boundary;
- `docs/reference/media-commands.md` — operation catalog;
- `docs/reference/invariants.md` — cross-system safety rules;
- `docs/runbooks/media-legacy-reassessment.md` — operational legacy reassessment flow.

Dated files under `docs/superpowers/specs/` и `docs/superpowers/plans/` сохраняют историю проектных решений, но не заменяют current code, schemas, AGENTS contracts или living docs.
