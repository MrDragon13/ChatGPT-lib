# Media Intelligence Correctness & Observability — review amendment

Дата: 2026-10-04  
Статус: **normative amendment awaiting final user review**  
Изменяет: `2026-10-04-media-intelligence-correctness-observability-design.md`  
Основание: финальный review после второго self-review

Этот amendment не расширяет Stage A новыми моделями, thresholds или scoring logic. Он уточняет observability, audit provenance и trust-boundary contracts, а также фиксирует дополнительную гипотезу для будущего evaluation harness.

## 1. Fingerprint-length bias в ranking evaluation

Stage A ranking остаётся неизменным:

1. personalized candidates перед fallback;
2. внутри personalized — больше `strengths_count - concerns_count`;
3. при равном net count — меньше concerns;
4. затем `interest.priority`;
5. затем стабильный `id`.

При этом design явно признаёт потенциальный bias: абсолютное значение `strengths_count - concerns_count` зависит от количества traits в semantic fingerprint. Более богато описанный candidate имеет больше возможностей получить и strengths, и concerns, а при текущем низком coverage это может систематически влиять на ranking.

Stage A не нормализует ranking по длине fingerprint и не вводит новый коэффициент без benchmark.

Следующий evaluation harness обязан для каждого evaluated candidate записывать как минимум:

- `fingerprint_trait_count`;
- `strengths_count`;
- `concerns_count`;
- net directional count;
- rank/selection outcome.

Evaluation должен отдельно проверять зависимость ranking outcome от `fingerprint_trait_count` и сравнивать Stage A key с альтернативными baselines. Если enrichment увеличивает число traits, этот анализ обязателен до вывода, что quality improvement вызван самим ranking policy.

## 2. Assessment coverage: stable profile-level denominator

`assessment_coverage` сохраняет request-local показатели supporting context, но они не должны восприниматься как полная semantic coverage профиля.

Помимо:

- `supporting_works_total`;
- `supporting_works_with_fingerprint`;

assessment context должен предоставлять стабильный profile-level coverage indicator, концептуально:

```yaml
assessment_coverage:
  candidate_has_fingerprint: true
  candidate_directional_matches: 3
  supporting_works_total: 6
  supporting_works_with_fingerprint: 2
  profile_rated_works_total: 52
  profile_rated_works_with_fingerprint: 5
```

Точные имена полей определяются implementation plan после inspection текущего data model, но denominator должен быть независим от `recent_limit`, `representative_limit` и текущей выборки supporting works.

Implementation plan обязан точно определить `supporting work`: какие коллекции/works допускаются, какие filters применяются, как обрабатываются repeated viewings/ratings и является ли supporting set subset текущего `taste_context` или отдельной deterministic projection.

Profile-level metric не заменяет request-local supporting coverage: обе величины нужны, потому что отвечают на разные вопросы.

## 3. Placement of `limitations`

`limitations` является top-level peer metadata для конкретного context/result, а не вложенной частью `coverage` block.

Это намеренный contract для recommendation и assessment:

```yaml
coverage: ...
limitations:
  - partial_semantic_coverage
```

и

```yaml
assessment_coverage: ...
limitations:
  - partial_semantic_coverage
```

Причина: coverage содержит измерения, а limitations — machine-readable interpretation фактических состояний, которая может зависеть не только от одного coverage block (например, couple disagreement или fallback state).

Implementation plan/tests должны сохранить эту границу и не заставлять consumers искать limitations внутри нескольких разных coverage structures.

## 4. Trusted source for changed-file inventory

Guarded auto-merge policy зависит не только от trusted operation/path policy, но и от достоверного списка файлов, изменённых PR.

Privileged workflow не должен определять changed-file inventory через исполнение PR-controlled code или через untrusted working tree как источник истины.

Changed-file inventory должен поступать из trusted GitHub metadata/API boundary с credentials и ref semantics, не контролируемыми содержимым PR. Implementation plan обязан назвать конкретный механизм получения этого списка и покрыть его contract/security tests.

Auto-merge eligibility вычисляется как минимум из двух trusted inputs:

1. trusted declarative path/operation policy из `main` или иной заранее доверенной revision;
2. changed-file inventory из trusted GitHub PR metadata/API.

Если любой из этих inputs невозможно получить или однозначно проверить, auto-merge fail closed.

## 5. Audit input inventory and digest scope

`canonical_input_digest` должен покрывать не абстрактное понятие "canonical YAML", а точный deterministic inventory всех repository inputs, которые реально влияют на audit metrics.

Implementation plan обязан перечислить этот inventory до реализации digest. В него включаются не только works/collections, но и конфигурационные/canonical inputs, если audit их читает или они меняют eligibility/denominators — например viewers, groups, controlled vocabulary и иные relevant config files.

Правило:

> если изменение файла может изменить deterministic audit payload при неизменных остальных inputs, этот файл или его нормализованное содержимое должно участвовать в `canonical_input_digest`.

Tests должны доказывать обратное свойство: изменение файла, который объявлен не влияющим на audit, не должно менять digest или metrics неожиданным образом.

## 6. Дополнения к testing strategy

Stage A / следующий evaluation plan должны включить следующие дополнительные проверки:

- ranking/evaluation dataset записывает `fingerprint_trait_count` и позволяет проверить корреляцию длины fingerprint с rank/selection;
- assessment tests различают request-local supporting coverage и stable profile-level rated-work semantic coverage;
- `limitations` остаётся top-level sibling соответствующего coverage block;
- privileged auto-merge использует changed-file inventory из trusted GitHub metadata/API, а не из PR working tree;
- невозможность получить trusted changed-file inventory приводит к fail-closed;
- audit digest inventory включает все реально читаемые canonical/config inputs, включая viewer/group/vocabulary inputs там, где они влияют на metrics.

## 7. Влияние на scope

Эти уточнения не добавляют в Stage A:

- fingerprint-length normalization;
- новый ranking coefficient;
- confidence thresholds;
- deterministic assessment verdict;
- semantic enrichment backfill.

Они добавляют только измерения и contract precision, необходимые, чтобы следующий evaluation stage мог честно проверить bias, а privileged automation и audit provenance не зависели от неявных источников.

`writing-plans` должен рассматривать основной design и этот amendment как единый утверждённый письменный spec.