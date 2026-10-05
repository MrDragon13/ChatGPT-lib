# Media intelligence

Этот документ описывает текущую recommendation/taste reasoning model. Она строит объяснимые выводы из пользовательских сигналов и semantic knowledge, но не сводит вкус к одному opaque score.

## Базовый принцип

Media intelligence разделяет четыре слоя:

1. factual metadata о произведении;
2. semantic fingerprint произведения;
3. user evidence — ratings, reactions, feedback, explicit preferences, interest и interactions;
4. inferred taste hypotheses с provenance и evidence pointers.

Смешивание этих слоёв создаёт self-reinforcing выводы, поэтому provenance сохраняется явно.

## Evidence hierarchy

Практический приоритет:

1. explicit stable user statements;
2. повторяющиеся correlations, подтверждённые независимыми сигналами;
3. один rating-derived correlation как слабое/ограниченное evidence.

Inferred output **не является independent evidence** для другого inferred output. Гипотеза может быть пересчитана из raw/explicit evidence, но не должна усиливаться только потому, что предыдущая версия уже существовала.

Generated profile хранит hypotheses отдельно в `inferred_preferences`. Они доступны explanation/reasoning layer, но **не участвуют в численном расчёте `affinities`** и не увеличивают их `score`, `confidence` или `evidence_count`. Численные affinities строятся только из первичного evidence, которое профиль агрегирует напрямую.

## Taste context

`taste_context` — компактный read model для reasoning. Он может включать:

- explicit preferences/constraints;
- inferred hypotheses;
- representative liked/disliked works;
- recent meaningful feedback;
- exclusions;
- strongest evidence-backed affinities;
- explicit work similarity;
- для `couple` — agreement/disagreement без скрытого усреднения.

Taste context — память/контекст, а не готовая формула ranking.

## Internal и external recommendation routing

### Internal

Если пользователь явно просит «что посмотреть из моей медиатеки?», candidate boundary — локальная библиотека/index.

Stage A использует временную детерминированную ranking policy, которая исправляет directional correctness, но **не считается доказанной моделью качества**. Для каждого кандидата semantic traits сопоставляются со signed target affinities: `score > 0` даёт strength, `score < 0` — concern, zero/missing affinity не считается направленным совпадением. Confidence и magnitude affinity доступны для explanation, но не используются как скрытые ranking weights.

Кандидаты с `ranking_basis: trait_overlap` всегда идут раньше fallback-кандидатов с `ranking_basis: none`. В personalized-группе порядок определяется последовательно: больше `strengths - concerns`, затем меньше concerns, затем выше `interest.priority`, затем стабильный `id`. В fallback-группе используются только `interest.priority` и `id`. Внешний numeric match/ranking score не публикуется.

`recommend_context` сохраняет legacy `evidence.strengths`/`evidence.concerns`, добавляет structured `evidence_details`, а также явные `ranking_basis` и `fallback_reason`. Top-level `coverage` отдельно описывает весь отфильтрованный candidate pool до `limit` и фактически возвращённый набор после `limit`. Top-level `limitations` содержит только детерминированные fact codes, например partial semantic coverage, наличие fallback results или полное отсутствие personalized candidates; эти ограничения не вложены в `coverage`.

### External

Обычная просьба «посоветуй фильм» использует external discovery по умолчанию. Локальная media library служит памятью о вкусах, evidence, exclusions и semantic anchors, но не ограничивает каталог кандидатов.

Временные ограничения вроде mood, runtime или «не сегодня» относятся к текущему request context и не превращаются в permanent preference без explicit stable statement.

## Explicit similarity

User-declared work similarity — полезная cross-work связь для рекомендаций, сравнений и explanations.

Ключевой инвариант: **similarity не является preference сама по себе**. Assertion «A похож на B» не означает автоматически «мне нравится trait X» и не должна одна создавать affinity/stable taste hypothesis.

Similarity может усиливать reasoning, когда рядом есть independent evidence: например, пользователь любит A, считает A похожим на B и отдельно положительно оценил B. При противоположных ratings та же similarity полезна как counterexample.

LLM-derived semantic similarity остаётся derived knowledge и не выдаётся за explicit пользовательское утверждение.

## Candidate assessment

Для вопроса «понравится ли мне X?» используется `assess_candidate`.

`assess_candidate` — **read-only** capability. Он может работать как с canonical work, так и с external candidate и не обязан добавлять внешний фильм в library.

Контекст оценки включает:

- target taste evidence;
- candidate metadata/semantic fingerprint, если доступен;
- concrete liked/disliked anchors;
- explicit similarity relations;
- optional current request text/constraints.

Сам assessment не записывает prediction в canonical taste state.

Stage A делает uncertainty assessment наблюдаемой через top-level `assessment_coverage` и `limitations`, но не вычисляет verdict. `candidate_has_fingerprint` и `candidate_directional_matches` описывают, существует ли semantic basis для самого кандидата. Request-local supporting coverage считается по deduplicated canonical works, реально попавшим в `taste_context.recent_feedback` и `taste_context.representative.high/low`.

Отдельно считается stable profile coverage по **всем canonical rated works**, релевантным target, чтобы изменение `recent_limit`/`representative_limit` не меняло базовый знаменатель уверенности. Для viewer target учитывается его numeric rating; для group target достаточно numeric rating любого member, а direct group rating используется как fallback, если member ratings для work отсутствуют. `partial_semantic_coverage` означает только неполное fingerprint coverage одного из этих ненулевых знаменателей.

Fact-only limitation codes различают отсутствие candidate fingerprint (`no_candidate_semantic_fingerprint`) и отсутствие directional personalized basis (`no_candidate_personalized_basis`). Второй код ставится whenever directional matches равны нулю, независимо от того, вызвано это отсутствующим fingerprint или отсутствием известных signed affinities. Это не probability и не скрытый assessment score.

## Формат вывода assessment

Финальный user-facing вывод остаётся **qualitative**:

- `likely / mixed / unlikely` или эквивалентная естественная формулировка;
- confidence `low / medium / high`;
- positive reasons;
- risks/counterevidence;
- concrete evidence works;
- distinction explicit vs inferred provenance.

Запрещена fake precise probability вроде «82%». Также нет обязательного **opaque match score**, который скрывает, почему модель пришла к выводу.

Если candidate identity/fingerprint или пользовательского evidence мало, правильный результат — lower confidence, а не выдуманная точность. Agent обязан учитывать active `limitations` и не описывать partial coverage как полностью grounded certainty.

## Couple reasoning

`couple` — отдельный group target. Совместный recommendation reasoning учитывает сигналы обоих участников и explicit group data, но не превращает разные вкусы в молчаливое среднее.

Полезные состояния:

- agreement — оба сигнала поддерживают candidate;
- disagreement — один сигнал поддерживает, другой создаёт риск;
- sparse evidence — для одного участника данных недостаточно.

Stage A дополнительно проецирует `couple.term_signals` из **индивидуальных member profiles**, не из уже агрегированного couple score. Для каждого semantic term показываются direction (`positive`/`negative`/`null`), confidence и evidence count каждого member. `agreement` означает одинаковый non-zero sign у всех members, `disagreement` — разные non-zero signs при наличии directed evidence у всех, `insufficient` — отсутствие directed evidence хотя бы у одного member. Confidence не меняет status.

Эта projection read-only и не изменяет couple aggregation или generated profile. Старые rating-based `couple.agreements`/`couple.disagreements` сохраняются отдельно. Если существует хотя бы один semantic-term disagreement, top-level `limitations` получает fact code `couple_term_disagreement`, чтобы agent не скрывал конфликт усреднённым объяснением.

Explanation должно показывать конфликт, если он влияет на выбор.

## Reanalysis

Запрос переанализа вкуса строит новый context из текущего raw/explicit evidence и заменяет inferred hypotheses через typed operation. Reanalysis не должен считать старые inferred hypotheses независимыми подтверждениями.

Similarity может быть дополнительным мостом между evidence works, но не заменяет ratings/reactions/feedback как independent user signal.

## Legacy reassessment and explicit evidence backfill

Legacy reassessment — отдельный pilot для улучшения качества historical `primary` user evidence перед Stage B. Он не является semantic enrichment cycle: semantic fingerprint work, vocabulary evolution и semantic provenance/backfill остаются отдельными задачами.

Ключевой evidence rule — **unanchored first**. `reassessment-context` показывает только safe factual memory jog; old rating/reaction/feedback и semantic traits не должны якорить первый текущий ответ. Historical state читается отдельным `reassessment-history` route после независимого ответа либо раньше только по явному запросу пользователя; timing/finalization exposure записывается как provenance.

Fresh current response может создать explicit viewing/rating/reaction/feedback. Старый v1 review остаётся historical context и сам по себе не преобразуется в explicit evidence. Если пользователь подтверждает тот же numeric rating, но существующий source был `inferred` или `explicit_approx`, canonical provenance всё равно меняется на `explicit`, поэтому outcome — `changed`, а не `confirmed_unchanged`.

`confirmed_unchanged` означает, что уже существующее canonical evidence было explicit и fresh response не требует mutation. Для такого случая не создаётся искусственная feedback-history запись: confirmation provenance хранится в pilot ledger.

Pilot ledger — operational provenance, не taste truth и не Stage B benchmark сам по себе. Reviewed evidence позже может участвовать в benchmark selection, но Stage B отдельно определит sampling/leakage rules.

Default session size — 5. Deferred works не смешиваются с main pending pass и возвращаются только после его завершения. Scheduled `set_inferred_preferences` replacement выполняется после каждых 15 newly reviewed works с предыдущего scheduled milestone и один раз в конце main pending pass, если reviewed evidence продвинулось. Manual user-requested reanalysis не сбрасывает этот counter.

Поскольку pilot намеренно меняет evidence base, generated profiles/affinities могут drift. Это ожидаемый результат замены inferred/approx evidence свежим direct explicit evidence, а не автоматическая regression. Progress и quality comparison интерпретируются относительно frozen Stage A baseline/revision, а не относительно непосредственно предыдущего generated profile.

`media/pilots/` исключён из Stage A `canonical_input_digest`: ledger-only lifecycle mutation не должна выглядеть как изменение intelligence input. Canonical work mutation, напротив, меняет audit state обычным способом.

## Explainability rules

Хорошее объяснение рекомендации или assessment:

- называет конкретные works/traits;
- различает explicit user knowledge и inferred conclusions;
- показывает risks, а не только supports;
- учитывает текущий request context отдельно от stable taste;
- не изображает derived inference как факт, сообщённый пользователем.

## Measurement foundation

`python -m media.tools.audit_intelligence . --format json` — canonical read-only аудит текущего intelligence state. Он измеряет inventory, semantic coverage, viewing/rating/feedback coverage, derived profile affinity coverage, similarity/interactions и canonical internal recommendation pool.

Audit сначала валидирует canonical state и затем считает метрики из canonical/config inputs. Generated profiles не считаются источником истины: profile metrics строятся через `build_profile()` в памяти. Recommendation pool строится из canonical works через `build_index_rows()` и ту же eligibility policy, что runtime, поэтому stale `media/generated/index.jsonl` не меняет аудит.

`canonical_input_digest` — детерминированный SHA-256 content digest входов, способных изменить audit result. В него входят viewer/group config, vocabulary, canonical works/collections/lists/tombstones, similarity/interactions и explicit/inferred preferences. Schema/code revision хранится через git provenance, а не смешивается с data-content digest. Pilot ledger под `media/pilots/` намеренно не входит в этот inventory.

Baseline под `media/baselines/` — **historical baseline**, то есть фиксированная точка сравнения, а не lockfile текущих пользовательских данных. Детерминированный payload не содержит wall-clock timestamp или git SHA; `source_revision` и `generated_at` лежат в отдельном `.meta.json` provenance-файле.
