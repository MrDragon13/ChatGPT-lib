# Media intelligence

Этот документ описывает текущие правила taste reasoning, recommendations, candidate assessment и explicit similarity в Media Intelligence v6.

## Источники знания

Система различает три слоя:

1. **explicit user evidence** — rating, reaction, feedback, explicit preference, interest, similarity;
2. **inferred taste hypotheses** — объясняющие гипотезы, построенные из independent evidence;
3. **work semantics** — признаки самого произведения из controlled vocabulary.

Эти слои нельзя смешивать.

Explicit evidence имеет приоритет над inferred interpretation. Inferred output не является independent evidence для следующего inference. Film fingerprint описывает work, never the viewer reaction. Credits (directors/writers/main cast) остаются canonical metadata, но не входят в semantic input digest: изменение состава или порядка credits не должно само по себе инвалидировать fingerprint содержания. Synopsis остаётся canonical metadata и может использоваться LLM при построении fingerprint, но его редакционная формулировка не входит в semantic input digest и сама по себе не инвалидирует fingerprint. `genres` и `countries` в digest трактуются как неупорядоченные множества; устойчивые структурированные факты вроде runtime/genres продолжают влиять на freshness.

## Taste profile

Generated profile строится детерминированно для конкретного target.

Он содержит:

- explicit preferences/rules;
- affinities по semantic terms;
- inferred hypotheses как отдельную explanation layer;
- evidence counts/provenance;
- cached reanalysis status для viewer targets.

Inferred hypotheses не должны молча усиливать численные affinity scores как будто это новое пользовательское evidence.

## Checkpointed taste reanalysis

Глубокий LLM reanalysis не выполняется после каждого feedback.

Для `primary` и `partner` отдельно существует evidence checkpoint.

Default threshold: **5** новых содержательных explicit events после последнего полного reanalysis.

Material event:

- максимум +1 за один человеческий эпизод по одному work;
- retry и idempotent replay не считаются;
- `no_change` не считается;
- metadata-only change не считается;
- косметическая правка `feedback.summary` без изменения structured explicit signals не считается;
- последующая содержательная переоценка того же work может дать новое событие.

Источник истины — checkpoint/prefix digest, а не отдельный изменяемый integer.

Перед taste-dependent decision (`recommend`, сравнение, «что сегодня», `assess_candidate`, couple recommendation):

1. прочитать reanalysis status;
2. если threshold не достигнут — использовать current profile, но свежие explicit signals имеют приоритет;
3. если threshold достигнут — сначала построить fresh reanalysis;
4. сохранить его через `set_inferred_preferences` вместе с evidence checkpoint/digest и algorithm version;
5. использовать свежий результат в текущем разговоре сразу; canonical checkpoint становится authoritative только после merge.

`couple` не имеет собственного счётчика. Перед couple decision проверяются `primary` и `partner`; переанализируется только тот участник, которому это нужно.

## Taste context

`taste_context` — read-only компактный context для reasoning.

Он включает explicit/inferred profile data, representative works, recent feedback, couple disagreement и limitations.

При нуле work evidence viewer context сообщает `cold_start_no_work_evidence`. Это не отменяет сохранённые global explicit preferences.

## Recommendations

### Internal

Internal recommendation рассматривает только canonical local works.

Если library пуста, candidate list пуст и limitation содержит `empty_library`. Нельзя создавать фиктивный кандидат ради UI или теста.

Текущая deterministic ranking policy отделяет кандидатов с personalized semantic basis от fallback:

- `trait_overlap` идёт раньше `none`;
- personalized candidates учитывают directional balance strengths/concerns;
- затем учитываются concerns, interest priority и stable ID;
- fallback не притворяется personalized reasoning.

Confidence и magnitude affinity доступны для explanation, но не являются скрытым opaque match score.

### External discovery

General recommendation request допускает external discovery по умолчанию.

Локальная библиотека служит памятью о вкусах, evidence anchors и exclusions, но не ограничивает внешний candidate set.

Сам факт внешней рекомендации не создаёт canonical work.

## Recommendation evidence и limitations

`recommend_context` возвращает:

- candidates;
- structured strengths/concerns;
- `ranking_basis` / fallback reason;
- coverage;
- top-level `limitations`.

`ranking_basis=none` не является personalized semantic evidence.

Active limitations — material context. Agent должен учитывать их в выводе один раз и кратко, а не механически повторять предупреждение.

## Candidate assessment

`assess_candidate` — read-only context для вопроса «понравится ли мне X?».

Кандидат может быть canonical или external.

Assessment использует:

- target taste context;
- candidate semantic fingerprint, если он есть;
- concrete supporting/contradicting works;
- explicit similarity;
- coverage/limitations.

Ответ остаётся **qualitative**. Система не создаёт fake precise probability, deterministic `likely/mixed/unlikely` или opaque match score.

Top-level `assessment_coverage` показывает реальную полноту основания: наличие fingerprint, число directional matches и coverage supporting work evidence.

Partial `assessment_coverage` must not be described as fully grounded certainty.

External candidate может быть оценён без добавления в canonical library.

## Explicit similarity

`set_work_similarity` хранит target-specific undirected user assertion. `remove_work_similarity` удаляет ту же logical relation независимо от порядка endpoints.

Similarity может связывать canonical и stable external work.

Она является evidence/hint для recommendation и explanation, но **не является preference** сама по себе.

Derived semantic similarity не показывается как пользовательское мнение без explicit confirmation.

## Couple reasoning

Couple profile не должен скрывать disagreement.

`taste_context.couple.term_signals` показывает signed direction каждого member для semantic term и status:

- `agreement` — одинаковый non-zero sign у всех участников;
- `disagreement` — разные non-zero signs при наличии directed evidence;
- `insufficient` — directed evidence не хватает.

Confidence не превращает disagreement в agreement.

## Semantic coverage и uncertainty

Недостаточный fingerprint/evidence не должен компенсироваться выдуманными traits.

Uncertainty выражается через coverage и limitations. Unknown лучше guessed.

## Pre-v6 archive

Старый MD-архив не является taste evidence.

Его нельзя автоматически импортировать в profiles, recommendations или candidate assessment.

Если пользователь заново проходит старый фильм, fresh response создаёт новое explicit evidence обычным v6 flow.

## Quality regression

После reset старая активная пользовательская библиотека не используется как regression fixture.

Качественные правила защищаются compact synthetic/reference fixtures, включая:

- strong positive intrigue/problem-solving evidence;
- mixed evidence;
- couple disagreement;
- sparse semantic coverage;
- explicit similarity without preference;
- stale inferred interpretation против fresh explicit evidence.

Это защищает поведение, не превращая старую персональную базу в скрытый runtime input.


## Диагностика качества

`python -m media.tools.audit_intelligence . --format json` остаётся воспроизводимой диагностикой текущего canonical состояния.

`canonical_input_digest` позволяет проверить, что два запуска аудита относятся к одному набору входных данных. Старый Stage A baseline больше не является активным runtime-файлом после reset; исторические измерения остаются в Git history.

Регрессии поведения v6 защищаются небольшими синтетическими/reference fixtures, а не старой персональной библиотекой. Это отделяет проверку алгоритма от пользовательских данных.
