# Media v5 — Agent Scenario Catalog

Дата: 2026-10-03  
Статус: **current v5/v5.1 agent scenario catalog**  
Связан с:
- `2026-10-03-media-intelligence-recommendation-v5-design.md`
- `2026-10-03-media-intelligence-v5-web-agent-contract-amendment.md`
- `2026-10-03-media-candidate-assessment-work-similarity-v5-1-design.md`

## 1. Назначение

Каталог задаёт ожидаемую семантику реальных пользовательских запросов. Он не заменяет command schemas и не требует дословного matching фраз. Агент должен распознавать intent и выбирать утверждённый route.

Общее правило: одна человеческая мысль → минимальное число атомарных typed operations. Уточнение задаётся только если без него materially меняется canonical результат или рекомендация.

## 2. Read / lookup

| Пользовательский intent | Route | Persistence | Уточнение |
|---|---|---|---|
| «Что у меня записано про X?» | lookup/show work + target signals | none | только при ambiguous identity |
| «Какую оценку я ставил X?» | lookup target rating | none | нет, если target известен |
| «Что партнёр думал про X?» | lookup partner signal | none | только если target неоднозначен |
| «Когда мы это смотрели?» | lookup viewing/history | none | нет |
| «Что я недавно высоко оценил?» | query history/index | none | нет |
| «Какие выводы ты сделал о моём вкусе?» | compact taste context + evidence | none | нет |
| «Почему в профиле написано X?» | inferred/affinity evidence drill-down | none | нет |
| «Что изменилось в профиле после последнего фильма?» | compare taste/profile evidence snapshots if available | none | нет |

## 3. Record / upsert feedback

| Intent | Route | Persistence rule |
|---|---|---|
| «Посмотрел X» | record viewing | не создавать rating/reaction |
| «X — 8/10» | record rating | rating-only; no invented explicit reasons |
| «X понравился» | record reaction | не придумывать rating |
| «8/10, интрига супер» | record rating + explicit feedback | semantic signal explicit/high if unambiguous |
| «Жене понравилось» | partner reaction | relayed opinion is valid evidence |
| «Жена сказала где-то 8» | partner approximate rating | explicit_approx semantics |
| «Нам обоим понравилось» | group/couple or viewer signals per schema semantics | не клонировать одинаковый numeric rating |
| «Посмотрели новый X, мне 8, ей 7» | create-if-missing feedback | one atomic operation if possible |
| «Досмотрел сериал X» | viewing update | preserve existing rating/feedback |
| «Бросил X на середине» | dropped/partial viewing | dropped is not automatic dislike |
| «Почти ничего не помню про X» | forgotten viewing state | не превращать в negative reaction |

## 4. Corrections

| Intent | Route | Rule |
|---|---|---|
| «X теперь 7 вместо 9» | edit rating | active rating=7; preserve audit/history |
| «Я ошибся, оценка была партнёра» | move/correct target signal | atomic target correction preferred |
| «Я говорил про другой X» | relocate/correct work reference | do not duplicate signal on both works |
| «Не писал, что темп раздражал» | remove wrong feedback evidence | rebuild taste context/profile |
| «Отзыв оставь, оценку поменяй» | edit rating only | other signals unchanged |
| «Оценку оставь, текст исправь» | edit feedback only | rating unchanged |
| «Я всё-таки это смотрел» | correct viewing | preserve independent feedback fields |
| «Я это не смотрел» | correct/clear viewing | do not silently delete rating unless consistency policy requires clarification |
| «Это был не horror, а thriller» | factual/semantic correction route | distinguish metadata vs taste signal |

## 5. Clear / delete / purge

| Intent | Route | Rule |
|---|---|---|
| «Убери мою оценку X» | clear_rating | keep feedback/reaction/viewing |
| «Удали мой отзыв про X» | clear_feedback | keep rating unless requested otherwise |
| «Убери реакцию liked» | clear_reaction | other fields unchanged |
| «Удали всё моё мнение про X, но факт просмотра оставь» | clear rating/reaction/feedback | keep viewing |
| «Удали все мои данные по X» | clear all active target signals | clarify whether history should remain only if materially relevant |
| «Удали полностью, включая историю» | purge target/work evidence | explicit destructive intent required |
| «Верни удалённую оценку» | restore from explicit new value or history-assisted correction | do not infer restored value unless known |
| «Отмени последнее изменение» | compensating typed operation | do not use blind git revert if it could revert unrelated changes |

## 6. Work/library lifecycle

| Intent | Route | Rule |
|---|---|---|
| «Добавь X» | add_work | no viewing/rating without evidence |
| «Добавь X, хочу посмотреть» | add_work + interest candidate/shortlist | one logical operation if schema supports |
| «Удали случайно добавленный фильм» | delete/remove-work maintenance with preconditions | must check signals/relations before destructive removal |
| «Это два дубля одного фильма» | merge/tombstone maintenance | immutable IDs; redirect old ID |
| «Исправь название/год» | metadata correction/override | never rename immutable work ID merely for title correction |
| «Добавь всю франшизу» | collection/add works route | no fabricated per-work viewer signals |
| «Оцениваю франшизу целиком» | collection signal route | do not copy score to members |

## 7. Interest / intent-to-watch

| Intent | Route | Rule |
|---|---|---|
| «Хочу посмотреть X» | set_interest(candidate/shortlist) | not watched |
| «Очень хочу X» | priority/shortlist | no rating/reaction |
| «X мне неинтересен» | not_interested | not a negative review |
| «Не предлагай X больше» | usually not_interested | clarify only if user means temporary exclusion |
| «Не сегодня X» | ephemeral request context | do not persist as not_interested |
| «Отложим на потом» | optional interest state/priority adjustment | avoid converting to dislike |

## 8. Recommendation — external default

| Intent | Route | Rule |
|---|---|---|
| «Посоветуй фильм» | external discovery | local library is memory/exclusion, not candidate boundary |
| «Что нам посмотреть сегодня?» | external + couple context | current intent can outweigh genre prior |
| «Хочу что-то лёгкое» | current mood context | ephemeral unless user explicitly states stable preference |
| «До 100 минут» | hard runtime constraint | verify factual runtime externally when needed |
| «Без ужасов» | hard genre/content constraint for request | do not persist unless stated as stable preference |
| «Что-то вроде X» | semantic-anchor discovery | reason beyond genre |
| «Похожее на A и B одновременно» | multi-anchor external discovery | explain shared dimensions |
| «Что-нибудь новое за последние месяцы» | fresh web/provider discovery | freshness verification required |
| «Выбери сам» | choose without questionnaire | one best pick + concise rationale |
| «Дай 5 вариантов» | diversified shortlist | do not force one winner if user asked list |
| «Удиви меня» | exploration mode | deliberately broader but evidence-connected |
| «Самое надёжное попадание» | exploit/high-confidence mode | minimize exploration |
| «Хочу попробовать новый жанр» | exploration with requested novelty | old genre profile is soft prior only |

## 9. Recommendation — internal/local

| Intent | Route | Rule |
|---|---|---|
| «Что посмотреть из моей медиатеки?» | internal recommend_context | candidates only from local index |
| «Что у меня лежит непросмотренное?» | internal query/filter | no external discovery |
| «Выбери из shortlist» | internal candidate comparison | respect interest priority |
| «Что пересмотреть?» | internal rewatch mode | viewing=watched allowed; use rewatch signals/history |

## 10. Candidate comparison / explanation

| Intent | Route | Rule |
|---|---|---|
| «A или B?» | compare candidates | use current intent + taste evidence |
| «Что лучше для нас двоих — A/B/C?» | couple comparison | expose disagreement risks |
| «Почему ты советуешь X?» | explain recommendation | concrete anchors + profile + current request |
| «Почему не советуешь Y?» | explain concerns/exclusions | distinguish hard constraint from soft concern |
| «Насколько это рискованный вариант?» | explain confidence/exploration | no fake precise percentage |
| «Что в X похоже на мои любимые фильмы?» | semantic comparison | load relevant full work context only as needed |

## 10.1 v5.1 — explicit similarity and candidate assessment

| Intent | Route | Persistence / rule |
|---|---|---|
| «A похож на B» | `set_work_similarity` | save one target-specific undirected current assertion; endpoint order does not matter |
| «B похож на A» after the previous assertion | `set_work_similarity` upsert | same canonical relation, never a mirrored duplicate |
| «Я больше не считаю A похожим на B» | `remove_work_similarity` | remove the same unordered pair; do not persist a negative similarity record |
| «Для нас A похож на B» | `set_work_similarity(target=couple)` | couple assertion is independent from primary/partner |
| «A похож на внешний B, но B пока не добавляй» | `set_work_similarity` with stable external WorkRef | external endpoint does not create a canonical work; no viewing/interest side effect |
| ambiguous external title | identity clarification | ask at most one short blocking question; never persist title-only identity guess |
| «Мне понравится X?» | `assess_candidate` | read-only context; agent returns qualitative verdict/confidence, concrete evidence and risks |
| «Насколько вероятно, что X зайдёт?» | `assess_candidate` | qualitative verdict/confidence; no fake precise percentage or opaque score |
| similarity used in recommendation | recommendation/explanation evidence | similarity is a hint/evidence, not a preference; it may anchor or contextualize, but not manufacture affinity alone |
| external X assessed for fit | `assess_candidate` external WorkRef | read-only; external candidate does not create a canonical work |

Derived/system semantic similarity stays read-only/derived unless the user explicitly asserts it. Explicit similarity may support future recommendation explanation, candidate comparison, or correlation reasoning, but one relation alone never becomes a stable taste hypothesis.

## 11. Recommendation interaction learning

| Intent/event | Route | Persistence |
|---|---|---|
| пользователь выбрал один из предложенных | append recommendation-choice interaction | yes, if interaction layer implemented |
| «Уже смотрел» после рекомендации | correct viewing/history; mark candidate resolved | yes |
| «Неинтересно вообще» | not_interested + interaction | yes |
| «Не сегодня» | interaction/ephemeral rejection | do not make stable negative preference |
| «Хороший совет» до просмотра | recommendation feedback only | do not treat as movie rating |
| «Ты всё время советуешь одно и то же» | recommendation-system feedback | adjust diversity policy/context, not movie taste directly |

## 12. Taste/profile lifecycle

| Intent | Route | Rule |
|---|---|---|
| «Переосмысли мой вкус» | reanalyze_preferences | rebuild inferred layer from raw evidence |
| «Пересчитай профиль» | deterministic rebuild if meaning is technical; deep reanalysis if user asks reinterpretation | distinguish rebuild vs reanalysis |
| «Почему ты решил, что я люблю X?» | explain inferred preference | show supporting/contradicting evidence |
| «Это неверно, X мне не важно» | correct inferred preference + optional explicit rule | user statement outranks model inference |
| «Да, я правда люблю X» | record explicit preference | do not keep it only inferred |
| «Удали этот вывод из профиля» | clear inferred hypothesis | preserve underlying raw feedback unless asked to remove it |
| «Не учитывай фильм X при анализе вкуса» | evidence exclusion policy if supported | must be explicit; do not delete film itself |
| «Сбрось inferred-профиль и построи заново» | clear/rebuild inferred layer from raw evidence | deterministic anti-self-reinforcement |

## 13. Film semantic knowledge

| Intent | Route | Rule |
|---|---|---|
| «Разбери X глубже» | semantic fingerprint enrichment | work knowledge only |
| «О чём X в плане темпа/тона/персонажей?» | read fingerprint + verified context | no user preference mutation |
| «Этот фильм на самом деле не медленный» | semantic correction/review | distinguish objective-ish trait from user reaction |
| rating added but fingerprint sparse | optional opportunistic semantic enrichment | weak rating correlation only after knowledge exists |
| model notices useful missing concept | vocabulary proposal | never auto-add term during feedback operation |

## 14. Couple semantics

| Intent | Route | Rule |
|---|---|---|
| «Посоветуй нам обоим» | couple context | do not average scores blindly |
| «Мне нравится, ей нет» | preserve disagreement | do not collapse into neutral group preference |
| «Найди компромисс» | couple balanced recommendation | identify strengths/risks per member |
| «Сегодня выбираю я» | current target weighting | ephemeral unless user states stable group rule |
| «Что больше понравится ей?» | partner target | do not leak primary preference into partner as fact |

## 15. Series / seasons / progress

| Intent | Route | Rule |
|---|---|---|
| «Мы на 5 серии второго сезона» | progress update if schema supports | no fabricated season review |
| «Первый сезон понравился, второй нет» | season-level signal only if canonical model supports it | otherwise explain unsupported granularity rather than corrupt work-level signal |
| «Сериал в целом 8» | work-level rating | independent from season scores |
| «Продолжать ли сериал?» | recommendation/advice using progress + taste | read-only unless user changes interest/viewing |

## 16. Maintenance / integrity

| Intent | Route | Rule |
|---|---|---|
| «Обнови метаданные» | refresh_metadata | provider facts only |
| «Пересобери generated» | deterministic rebuild | no new LLM inference |
| «Проверь целостность базы» | validate/doctor | read/maintenance |
| «Обнови semantic fingerprints всех фильмов» | bulk semantic maintenance | separate reviewed operation; do not hide inside normal feedback |
| «Добавь новый тег в vocabulary» | architecture/vocabulary review | never normal auto-merge data entry |

## 17. Preview / authorization

| Intent | Route | Rule |
|---|---|---|
| «Покажи, что ты собираешься сохранить» | preview/dry-run | stop before write until explicit save request |
| «Пока не сохраняй» | analysis only | no operation PR |
| обычный ясный feedback | authorized normal write | no second confirmation |
| после blocking identity clarification | continue original authorized write | no extra «сохранять?» |

## 18. Failure / ambiguity routes

| Ситуация | Поведение агента |
|---|---|
| несколько фильмов с одинаковым названием | одно короткое identity clarification |
| непонятно, чей rating | одно target clarification |
| ambiguous external similarity endpoint | одно короткое identity clarification; no title-only persisted guess |
| provider unavailable при создании нового work | объяснить пользовательский blocker; не сохранять partial feedback/work |
| existing-work feedback при provider outage | должен продолжать работать без provider |
| saved external similarity during provider outage | read from stored identity/display snapshot; provider not required for basic display |
| concurrent operation conflict | не создавать второй противоречащий write; восстановить/принять активную operation state по утверждённой broker semantics |
| validation failure | не заявлять success; canonical state остаётся целым |
| Pages задерживается после merge | data считается сохранённой в main; UI publication может отдельно быть pending |
| live AI на сайте недоступен | static intelligence/library UI остаётся рабочим |

## 19. Документирование новых возможностей

Каждая новая typed operation или новая пользовательская capability должна одновременно обновлять:

1. command schema / domain semantics;
2. tests;
3. `media/AGENTS.md` route;
4. при необходимости `media/START_PROMPT.md`, если меняется пользовательская mental model;
5. `media/README.md`;
6. web manifest/types/UI, если capability доступна на сайте;
7. этот scenario catalog или его преемник.

Нельзя считать feature завершённой, если код умеет её выполнять, но агент не знает, когда и как ею пользоваться.

## 20. Особая актуализация после dispatch-only Media Check

Текущий v4 `AGENTS.md` содержит устаревшую формулировку про automatic pull-request `media-check.yml`, который якобы «intentionally skipped» на request-only ветках. После перехода Media Check в dispatch-only режим v5 docs обязаны описывать фактический route:

```text
Media Command applies operation
→ commits exact new head
→ explicitly dispatches Media Check for expected_sha
→ exact-head check succeeds
→ guarded auto-merge may proceed
```

В agent docs не должно оставаться инструкций, предполагающих существование дополнительного pull_request Media Check.
