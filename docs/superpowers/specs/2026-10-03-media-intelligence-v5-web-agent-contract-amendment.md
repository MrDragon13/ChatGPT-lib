# Media Intelligence v5 — Web & Agent Operating Contract Amendment

Дата: 2026-10-03  
Статус: **design amendment approved in chat; awaiting final written review together with v5 spec**  
Дополняет: `2026-10-03-media-intelligence-recommendation-v5-design.md`

## 1. Цель

Новая intelligence-архитектура должна быть доступна одинаково корректно из трёх пользовательских поверхностей:

1. разговор с LLM;
2. сайт;
3. CLI/maintenance tooling.

Ни одна поверхность не должна изобретать собственную семантику вкуса или отдельный путь записи. `media/AGENTS.md` становится каноническим operating contract для LLM/агентов, а `media/START_PROMPT.md` — компактной пользовательской точкой входа, которая направляет агента к актуальному контракту и объясняет ожидаемое поведение без перегрузки техническими деталями.

Главный принцип:

> Сначала распознать пользовательский intent, затем выбрать один утверждённый read/write route. Не переводить естественный язык напрямую в произвольный patch данных.

## 2. Обязательная актуализация agent docs

Реализация v5 считается неполной, пока одновременно не обновлены:

- `media/AGENTS.md`;
- `media/START_PROMPT.md`;
- `media/README.md`;
- command schemas / command registry;
- website manifest contract и UI routes;
- тесты, фиксирующие ключевые routing invariants.

`AGENTS.md` должен описывать актуальную v5-архитектуру, а не оставаться контрактом v4.

`START_PROMPT.md` не должен дублировать весь technical manual. Он должен кратко закреплять:

- использование актуального `main` как источника истины;
- обязательное чтение `media/AGENTS.md`;
- естественный разговор вместо требований говорить JSON/YAML;
- способность записывать, исправлять и удалять пользовательские сигналы;
- способность переанализировать профиль по запросу;
- различие между «из моей медиатеки» и обычной внешней рекомендацией;
- отсутствие повторного подтверждения для уже ясно авторизованной обычной операции;
- запрет говорить «сохранено», пока результат не находится в `main`;
- минимальные уточнения только при реальной неоднозначности work / target / meaning.

## 3. Intent router как обязательная часть AGENTS.md

Агент не должен выбирать команду по одному ключевому слову. Он классифицирует запрос по пользовательскому намерению.

Основные классы intent:

1. **read / lookup** — показать сохранённые данные;
2. **record** — записать новый факт/сигнал;
3. **correct** — заменить ошибочный или устаревший текущий сигнал;
4. **clear** — удалить конкретный текущий сигнал без удаления work;
5. **purge** — явно удалить и активный сигнал, и его пользовательскую историю там, где такая операция поддержана;
6. **interest** — изменить интерес к произведению без утверждения о просмотре/качестве;
7. **recommend internal** — выбрать только из локальной медиатеки;
8. **recommend external** — найти новое произведение вне базы с использованием локальной памяти;
9. **explain** — объяснить рекомендацию, preference, correlation или источник вывода;
10. **reanalyze taste** — заново вывести inferred preferences из исходного evidence;
11. **semantic enrich** — обновить knowledge о самом произведении, не о вкусе пользователя;
12. **metadata maintenance** — factual refresh/provider maintenance;
13. **architecture/vocabulary maintenance** — отдельная developer/manual задача, никогда не скрытый побочный эффект пользовательского data entry.

Если запрос сочетает несколько логически связанных действий одного пользовательского события, агент предпочитает одну атомарную typed operation, если schema это поддерживает. Пример: «посмотрели новый фильм, мне 8, партнёру понравилось» — один feedback command с `create_if_missing`, а не цепочка отдельных операций.

## 4. Feedback lifecycle должен стать полноценным CRUD

Текущий `record_viewing_feedback` хорошо подходит для создания/обновления известного значения, но v5 должна добавить явную типизированную семантику corrections/clears. Нельзя выражать удаление через случайный `null`, отсутствующее поле или ручной YAML patch.

Предлагаемый контракт:

### 4.1 `record_viewing_feedback`

Используется для нового наблюдения и обычного upsert:

- впервые поставить rating;
- изменить rating, если пользователь формулирует это как новую актуальную оценку;
- записать просмотр;
- добавить/обновить reaction;
- записать новый feedback summary и semantic signals;
- одновременно создать отсутствующий work через `create_if_missing`.

### 4.2 `edit_viewing_feedback` (новая typed operation)

Используется, когда intent явно исправляющий или удаляющий.

Должна поддерживать schema-controlled действия по target:

- `set_rating`;
- `clear_rating`;
- `set_reaction`;
- `clear_reaction`;
- `set_feedback`;
- `clear_feedback`;
- `set_viewing`;
- `clear_viewing` там, где отсутствие viewing signal семантически допустимо.

Операция работает только с существующим work; она не должна неявно создавать произведение.

При обычной correction/clear active state обновляется/удаляется, а audit/history может сохранять факт изменения. Это позволяет отличить «я передумал» от «этого никогда не было».

### 4.3 Полный purge

Запрос уровня «удали мой отзыв полностью, включая историю» — отдельный сильный intent. Он не должен автоматически следовать из фразы «убери мой отзыв».

Если v5 реализует purge, это отдельная строго ограниченная typed operation, которая:

- требует явного указания, что удаляется history/evidence;
- удаляет только пользовательские сигналы указанного target/work;
- не удаляет сам work или сигналы другого viewer;
- вызывает rebuild profiles/context;
- не может быть сгенерирована моделью из неоднозначной формулировки.

## 5. Семантическое обогащение при отзыве

При новом отзыве LLM должна рассматривать два независимых объекта:

1. **что пользователь сказал о своём впечатлении**;
2. **что система знает о самом произведении**.

Если fingerprint произведения отсутствует или явно недостаточен, LLM может предложить work-level semantic enrichment в рамках утверждённого typed protocol.

Предпочтительный v5 путь — разрешить `record_viewing_feedback` v2 нести опциональный ограниченный `work_semantic_context`, содержащий только существующие vocabulary terms с provenance/confidence. Deterministic service валидирует и атомарно применяет его вместе с feedback, если это безопасно.

Это позволяет сценарию:

> «8/10»

не выдумывать explicit причины пользователя, но одновременно гарантировать, что для будущего rating-correlation у фильма есть качественный semantic fingerprint.

Если агент не уверен в semantic trait фильма или требуется свежая внешняя проверка, он не должен заполнять trait догадкой. Допустим отдельный read/enrichment route через LLM/web/provider.

## 6. Реальные пользовательские сценарии и правильные маршруты

Ниже не исчерпывающий список фраз, а нормативные примеры для intent router.

### 6.1 Обычный отзыв

**Пользователь:** «Посмотрели X. Мне 8.5, партнёру понравилось. Интрига классная, финал слабоват».

**Route:** `record_viewing_feedback` → existing/new work resolution → explicit semantic extraction → optional film fingerprint enrichment → deterministic apply → rebuild profiles/context.

Не спрашивать второй раз «сохранять?».

### 6.2 Только оценка

**Пользователь:** «X — 9/10».

**Route:** `record_viewing_feedback` с rating. Не придумывать explicit feedback. Rating участвует в weak correlation evidence через fingerprint.

### 6.3 Переоценка

**Пользователь:** «Я передумал, X теперь 7 вместо 9».

**Route:** correction (`edit_viewing_feedback` или явно correction-mode текущей операции). Новая оценка становится active, история изменения сохраняется. Profile rebuild обязателен.

### 6.4 Добавить мнение к старой оценке

**Пользователь:** «К моей восьмёрке за X добавь: очень понравились диалоги».

**Route:** обновить feedback, не менять rating; explicit semantic signal добавляется/пересобирается из актуального feedback state.

### 6.5 Исправить текст/смысл отзыва

**Пользователь:** «Я не говорил, что мне не понравился медленный темп. Убери это».

**Route:** correction только конкретного ошибочного semantic evidence; пересчитать profile. Не оставлять неверный active inferred/explicit signal.

### 6.6 Удалить оценку, оставить отзыв

**Пользователь:** «Убери мою оценку X, отзыв оставь».

**Route:** `clear_rating` только для нужного target. Feedback/reaction/viewing остаются.

### 6.7 Удалить отзыв, оставить оценку

**Пользователь:** «Удали мой текстовый отзыв и теги по X, оценку 8 оставь».

**Route:** `clear_feedback`; rating не изменяется.

### 6.8 Исправить статус просмотра

**Пользователь:** «Я ошибся, X я не смотрел».

**Route:** correction viewing state. Rating/reaction/feedback не должны автоматически уничтожаться без явного запроса; если возникает логическое противоречие, агент задаёт одно минимальное уточнение или применяет schema-defined consistency rule.

### 6.9 Отзыв партнёра, переданный пользователем

**Пользователь:** «Жене X понравился, где-то на 8».

**Route:** `partner` signal с корректным source/confidence (`explicit_approx` для approximate rating), если контекст ясно показывает, что пользователь передаёт мнение партнёра.

### 6.10 Совместное мнение

**Пользователь:** «Нам обоим очень зашло».

**Route:** не превращать автоматически в одинаковые числовые ratings. Сохранить только те group/viewer signals, которые действительно следуют из фразы по утверждённой semantics.

### 6.11 Добавить фильм без просмотра

**Пользователь:** «Добавь X в медиатеку, хочу потом посмотреть».

**Route:** `add_work` + `set_interest(candidate|shortlist)` по ясному intent; не создавать watched/rating/reaction.

### 6.12 «Не хочу это смотреть»

**Пользователь:** «X мне вообще неинтересен».

**Route:** `set_interest(not_interested)`. Не считать это negative review фильма и не обучать taste как dislike качества произведения.

### 6.13 Временное «не сегодня»

**Пользователь:** «Не хочу сегодня ничего мрачного».

**Route:** ephemeral recommendation constraint; не сохранять как persistent preference.

### 6.14 Рекомендация без уточнения источника

**Пользователь:** «Посоветуй нам фильм на вечер».

**Route:** external discovery по умолчанию: compact taste context + concrete anchors + current intent + external candidates + factual verification + watched/not-interested exclusion + explainable shortlist.

### 6.15 Только из локальной базы

**Пользователь:** «Что посмотреть из моей медиатеки?».

**Route:** internal recommendation only; никаких внешних кандидатов.

### 6.16 Похожее на конкретный фильм

**Пользователь:** «Хочу что-то вроде X».

**Route:** использовать X как semantic anchor, но учитывать current taste/history; не ограничивать поиск жанром X.

### 6.17 Совет по настроению

**Пользователь:** «Сегодня хочется лёгкого, умного и до двух часов».

**Route:** hard constraint для runtime, soft/current-intent constraints для tone/complexity; долгосрочный профиль — prior, а не фильтр.

### 6.18 Неожиданная рекомендация

**Пользователь:** «Удиви меня».

**Route:** exploration mode с повышенной дистанцией от привычных жанров, но с объяснимой глубинной связью с taste evidence.

### 6.19 Сравнить несколько вариантов

**Пользователь:** «Что нам лучше — A, B или C?».

**Route:** candidate comparison against couple context/current intent. Не требуется добавлять все три фильма в canonical library только ради сравнения.

### 6.20 Объяснить рекомендацию

**Пользователь:** «Почему ты думаешь, что мне это зайдёт?».

**Route:** read-only explanation с evidence pointers: concrete liked/disliked works, explicit/inferred preferences, current request. Не придумывать новые stored preferences как побочный эффект ответа.

### 6.21 Пересобрать понимание вкуса

**Пользователь:** «Переосмысли мой вкус по всей истории».

**Route:** `reanalyze_preferences(target)` → raw evidence + fingerprints + ratings + explicit preferences → candidate inferred preferences → validated canonical inferred layer → generated profile/context rebuild.

### 6.22 Исправить inferred preference

**Пользователь:** «Нет, мне не важен сильный визуал — это неправильный вывод».

**Route:** пользовательское утверждение имеет более высокий приоритет. Удалить/ослабить соответствующую inferred hypothesis и при необходимости записать explicit rule/preference, чтобы следующий reanalysis не восстанавливал ту же ошибку без нового сильного evidence.

### 6.23 Объяснить профиль

**Пользователь:** «Что ты сейчас понял о моём вкусе?».

**Route:** read compact taste context + evidence. Разделять explicit facts, inferred hypotheses и uncertainty.

### 6.24 Переанализировать один фильм

**Пользователь:** «Разбери X глубже, чтобы рекомендации были точнее».

**Route:** semantic enrichment work-level knowledge only. Не менять пользовательский rating/reaction/preferences.

### 6.25 Обновить factual metadata

**Пользователь:** «Обнови данные по фильмам».

**Route:** существующий provider maintenance (`refresh_metadata`) и его review policy; не смешивать factual refresh с taste reanalysis.

### 6.26 «Забудь, что я это смотрел»

Это неоднозначный intent между correction, clear и purge. Агент должен задать одно короткое уточнение только если последствия различаются materially: убрать только active viewing state или полностью удалить связанные пользовательские сигналы/history.

## 7. Recommendation modes, которые должны понимать агенты

AGENTS.md должен явно перечислять не одну команду «recommend», а набор пользовательских режимов:

- external default discovery;
- internal-library-only;
- couple / individual target;
- mood/current-context;
- strict runtime/content constraints;
- similar-to anchor;
- avoid-something;
- high-confidence safe picks;
- exploration / «удиви меня»;
- compare supplied candidates;
- continue franchise / related works;
- rewatch suggestion;
- short watch / long watch;
- series vs movie intent;
- recent/new releases when freshness is requested;
- «почему это?» explain mode;
- «что из предложенного мы уже видели?» history check.

Жанровые affinities всегда soft priors, если пользователь не сформулировал жанр как hard constraint.

## 8. Website integration — обязательная часть v5

Сайт не должен оставаться v4-витриной после изменения canonical intelligence model.

### 8.1 Manifest v2 / intelligence read model

Web exporter должен получить versioned manifest contract, способный безопасно отдавать:

- explicit preferences;
- inferred preferences;
- generated affinities;
- evidence summaries/pointers;
- film semantic fingerprints;
- representative liked/disliked works;
- couple agreement/disagreement hints;
- recommendation interactions/inbox, если они реализованы;
- сохранённые external recommendation candidates, если они предназначены для UI.

Frontend не вычисляет собственный taste profile и не создаёт скрытый score.

### 8.2 Новые read-only возможности сайта

Минимально полезные v5-функции:

- раздел «Мой вкус»;
- разделы `Я / Партнёр / Вместе`;
- explicit vs inferred preferences визуально различаются;
- confidence и uncertainty отображаются без ложной точности;
- «Почему система так думает?» раскрывает supporting works/evidence;
- semantic fingerprint на work detail;
- «Почему может подойти»;
- зоны совпадения/расхождения пары;
- список внешних рекомендаций/inbox, если candidate ещё не добавлен в медиатеку;
- история/эволюция понимания вкуса, если canonical audit data это позволяет.

### 8.3 Website write routes

Существующий authenticated broker остаётся единственным write boundary для обычных web-правок. UI actions должны маппиться на те же typed operations, что LLM:

- поставить/изменить оценку;
- удалить оценку;
- записать/исправить/удалить feedback;
- поменять viewing state;
- изменить interest;
- исправить ошибочный target signal.

Сайт не создаёт собственные REST semantics, которые невозможно выразить через media command model.

### 8.4 Intelligence Broker / Live AI

Для функций, требующих модели или внешнего discovery, нужен отдельный authenticated intelligence boundary (может быть расширением существующего broker deployment, но логически отдельный capability):

- «Что посмотреть сегодня?»;
- «Удиви меня»;
- external discovery;
- natural-language feedback parsing;
- deep profile reanalysis;
- semantic work enrichment;
- explain/compare, если нужен live reasoning.

LLM/provider credentials никогда не попадают в browser bundle.

Статический сайт должен оставаться полезным при недоступности live intelligence service.

## 9. Возможности сайта, которые открываются поверх v5

После появления evidence-rich intelligence layer становятся возможны без отдельной альтернативной модели данных:

- **Taste Explorer** — интерактивно смотреть устойчивые и неуверенные области вкуса;
- **Evidence Drill-down** — открыть preference и увидеть фильмы/отзывы, которые его поддерживают или опровергают;
- **Taste Contradictions** — показать противоречивые сигналы («медленный темп иногда раздражает, но несколько медленных фильмов оценены очень высоко»);
- **Couple Match** — не средняя оценка, а объяснение, почему фильм может сработать для обоих и где риск расхождения;
- **Discovery Slider** — UI-параметр от «надёжное попадание» к «неожиданное» как текущий recommendation intent, а не persistent preference;
- **Recommendation Inbox** — внешние кандидаты из LLM-чата/сайта с действиями `Хочу посмотреть / Неинтересно / Уже смотрел`;
- **Taste Evolution** — какие гипотезы усилились/ослабли после новых просмотров;
- **Review Interpretation Preview** — перед сохранением сложного свободного текста можно показать, что именно модель поняла, если пользователь явно просит preview или если ambiguity materially affects stored meaning;
- **Profile Reanalysis Control** — ручной запуск deep reanalysis с понятным пользовательским статусом;
- **Why this movie** — explainability на detail/recommendation card;
- **Similar for deeper reasons** — искать не только по жанру, а по смысловой структуре/атмосфере/персонажам.

Ни одна из этих функций не должна требовать хранить opaque recommendation score как source of truth.

## 10. START_PROMPT v5 — продуктовый контракт

Новый `START_PROMPT.md` должен оставаться коротким и человеческим. Его задача — не обучить модель всем JSON schema, а заставить её:

1. прочитать актуальный `AGENTS.md`;
2. использовать репозиторий как долговременную память;
3. знать, что пользователь может свободно просить записывать, исправлять и удалять данные;
4. понимать, что обычный совет ищет новое кино вне базы, если пользователь не ограничил поиск своей медиатекой;
5. учитывать concrete history + taste profile + current request;
6. уметь по запросу объяснить свои выводы и переосмыслить профиль;
7. не превращать жанры/preferences в жёсткие клетки;
8. не задавать повторные подтверждения и лишние анкеты;
9. не скрывать неопределённость;
10. никогда не заявлять об успешной записи до появления результата в актуальном `main`.

## 11. AGENTS.md v5 — структура

Рекомендуемая структура обновлённого контракта:

1. User experience contract.
2. Source-of-truth and intelligence-layer model.
3. Read paths.
4. Intent routing rules.
5. Feedback CRUD routes.
6. Semantic enrichment rules.
7. Rating-derived evidence rules.
8. Preference reanalysis and correction.
9. Internal/external recommendation modes.
10. Couple semantics.
11. Website/broker parity rules.
12. Hard guardrails.
13. Typed write protocol.
14. Maintenance routes.
15. Error/ambiguity policy.
16. Verification/completion semantics.
17. Natural-language examples.

## 12. Ambiguity policy

Агент задаёт уточнение только когда разные трактовки ведут к materially разным canonical изменениям или recommendation result.

Можно не уточнять:

- «X — 8» в контексте обсуждения фильма и target уже известен;
- «добавь, хочу посмотреть»;
- «посоветуй что-нибудь» при достаточном taste context.

Нужно уточнить:

- одно название соответствует нескольким works и identity нельзя разрешить надёжно;
- непонятно, чья именно оценка сообщается;
- «удали всё» может означать active signal vs full purge;
- пользовательское высказывание можно разумно трактовать как противоположные sentiments.

После одного blocking clarification агент продолжает исходную уже авторизованную операцию без второго подтверждения.

## 13. Completion semantics

Для write intent агент различает:

- interpreted;
- submitted;
- applied;
- checked;
- merged;
- published/read-visible.

Пользовательское «сохранено» допустимо только после merge в актуальный `main`; если конкретный UX зависит от Pages/read model, интерфейс отдельно может показывать pending publication до появления новой версии manifest.

Для read-only recommendation/explanation никакой фиктивной write operation не создаётся.

## 14. Acceptance criteria amendment

v5 implementation не считается законченной, пока:

1. `AGENTS.md` описывает v5 intent router и все реализованные typed operations;
2. `START_PROMPT.md` соответствует v5 UX и recommendation semantics;
3. rating/change/delete/clear сценарии имеют явные schema semantics и тесты;
4. external vs internal recommendation routes невозможно случайно перепутать;
5. website manifest поддерживает новый intelligence read model;
6. website write actions используют те же typed operations, что LLM;
7. live-AI web features не раскрывают credentials браузеру;
8. explicit / inferred / film knowledge остаются раздельными во всех surfaces;
9. profile reanalysis не может self-reinforce старые inferred conclusions;
10. documentation содержит end-to-end examples как минимум для: add, rate, re-rate, feedback correction, partial clear, full purge policy, profile reanalysis, internal recommendation, external recommendation, couple recommendation, semantic enrichment и metadata refresh.
