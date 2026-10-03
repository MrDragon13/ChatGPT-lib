# Current status

Текущая capability line: **Media Intelligence v5.1**.

Этот файл описывает устойчивое текущее состояние проекта. Временный progress конкретной разработки хранится в active PR, а historical rationale — в `docs/superpowers/`.

## Реализовано

### Canonical и derived media

- Git/YAML остаётся canonical source of truth для media data, preferences, relations и configuration.
- Retrieval index, profiles, taste contexts, runtime database и web manifest являются derived и rebuildable.
- `primary`, `partner` и `couple` остаются независимыми subjective contexts; couple disagreement не скрывается автоматическим усреднением.

### Typed operations

Normal media writes проходят через strict typed operations, deterministic transaction, validation/rebuild и operation-scoped GitHub workflow policy.

Поддерживаются viewing feedback, corrections, interest, inferred preferences, semantic fingerprints, recommendation interactions и explicit work similarity. Bulk `refresh_metadata` остаётся manual-review maintenance operation.

Read-only context routes включают `recommend_context`, `taste_context` и `assess_candidate`.

### Candidate assessment

`assess_candidate` поддерживает qualitative ответ на вопрос «понравится ли мне X?» для canonical или external candidate. Он использует target taste context, concrete evidence works, semantic information и explicit similarity, но не сохраняет prediction и не создаёт fake precise match probability.

External candidate может быть оценён без добавления в canonical library.

### Explicit work similarity

`set_work_similarity` хранит target-specific undirected user assertion между двумя works/references. `remove_work_similarity` удаляет ту же logical relation независимо от порядка endpoints.

Similarity может связывать canonical work и stable external identity. External endpoint не создаёт viewing/rating/interest или canonical work автоматически. Когда соответствующий work позже добавляется, deterministic reconciliation нормализует relation к canonical ID и устраняет duplicate/self-link состояния.

Explicit similarity используется как recommendation/explanation evidence и hint, но не является stable preference сама по себе.

### Taste и recommendations

Taste reasoning сохраняет provenance между explicit evidence, inferred hypotheses и semantic work knowledge. Inferred output не является independent evidence для последующего вывода.

Internal recommendation request ограничивает candidate set локальной библиотекой. General recommendation request допускает external discovery; library при этом служит памятью о вкусах, exclusions и evidence anchors.

### Web

Текущий exporter выдаёт **manifest v3**. Static GitHub Pages читает versioned derived manifest, а не canonical YAML.

Manifest v3 включает target-aware taste/recommendation data, semantic fingerprints и explicit similarity projection. Canonical↔canonical similarity проецируется на обе локальные work pages; canonical↔external отображается как lightweight external endpoint без выдуманного local route.

Поддерживаемые browser edits идут через protected broker и тот же typed-command boundary. GitHub/provider/model secrets не попадают в browser bundle.

## Известные ограничения

- Evidence для `partner` заметно менее насыщен, чем для `primary`; confidence reasoning должен отражать эту разницу.
- Derived semantic similarity не сохраняется как explicit user assertion и не показывается как пользовательское мнение без подтверждения.
- External discovery/live model reasoning находится на agent/server boundary; static Pages остаётся работоспособным без live model.
- Candidate assessment сознательно не имеет opaque deterministic match score или псевдо-точной вероятности.
- Bulk provider metadata refresh требует manual review и не относится к normal auto-merge path.
- Controlled vocabulary расширяется только отдельным developer/architecture change, а не автоматически из обычного feedback.

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
- `docs/reference/invariants.md` — cross-system safety rules.

Dated files under `docs/superpowers/specs/` and `docs/superpowers/plans/` сохраняют историю проектных решений, но не заменяют current code, schemas, AGENTS contracts или living docs.
