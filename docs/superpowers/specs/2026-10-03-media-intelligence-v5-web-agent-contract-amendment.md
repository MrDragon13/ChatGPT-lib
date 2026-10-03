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
- тесты, фиксирующие ключевые routing invariants;
- development-continuity protocol из `2026-10-03-media-intelligence-v5-development-continuity-contract.md` для всех implementation PR.

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
- добавить/заменить reaction;
- сохранить summary + semantic signals;
- атомарно записать несколько target updates для одного просмотра.

Если пользователь говорит «поставь теперь 8 вместо 7», операция считается correction текущего значения, а history фиксирует замену по существующим правилам data model.

### 4.2 `edit_viewing_feedback` (новая typed operation)

Нужна для явных исправлений и удаления отдельных сигналов.

Концептуально команда должна уметь по target/work:

- `set` — установить/заменить конкретные поля;
- `clear` — убрать текущий `rating`, `reaction`, `feedback`, `viewing`, `rewatch` или выбранные semantic feedback signals;
- сохранить audit/history, если это correction, а не privacy purge.

Удаление не должно требовать ручной правки YAML.

### 4.3 Purge semantics

Фраза «удали мой отзыв» неоднозначна и должна трактоваться по минимальному intent:

- «убери текст отзыва, оценку оставь» → clear feedback only;
- «убери оценку» → clear rating only;
- «удали всё моё мнение об этом фильме» → clear rating/reaction/feedback/relations, но viewing может остаться, если пользователь не сказал удалить факт просмотра;
- «удали вообще всю мою историю по этому фильму, включая то, что я его смотрел» → explicit purge operation/policy.

Полный privacy-style purge должен быть отдельной операцией с более строгим подтверждением/guardrails, потому что он разрушает evidence/history, в отличие от обычной correction.

## 5. Recommendation intent routes

### 5.1 «Что посмотреть из моей медиатеки?»

Маршрут: internal recommendation. Только local index, viewing/interest/profile/history.

### 5.2 «Посоветуй фильм» / «что нам посмотреть?»

Маршрут по умолчанию: external discovery. Local media — память/exclusion/evidence, а не граница каталога.

### 5.3 «Похожее на X»

LLM использует X как concrete semantic anchor + taste context. Если X не в базе, допускается внешний factual/semantic lookup без обязательного добавления work.

### 5.4 Mood / constraints

«Сегодня лёгкое», «до 100 минут», «без ужасов», «хочу прям мрачное» относятся к текущему request context и не становятся permanent preferences без явного устойчивого заявления.

### 5.5 «Удиви меня»

Включает exploration mode: агент может сознательно выбрать вариант вне самых очевидных priors, но обязан объяснить связь с более глубокими сигналами вкуса.

### 5.6 Couple

«Нам с женой» / «для двоих» → `couple`, но reasoning не сводится к среднему. Нужно учитывать зоны совпадения и расхождения и, где полезно, пояснять asymmetric fit.

## 6. Recommendation interaction routes

Когда пользователь реагирует на совет, агент должен различать:

- «давай этот» → recommendation selection interaction;
- «это уже смотрели» → corrected viewing/history route, если контекст однозначен;
- «не сегодня» → ephemeral rejection, не persistent `not_interested`;
- «вообще не хочу такое» → возможно persistent interest/preferences signal, но только если формулировка действительно устойчива;
- «почему ты это предложил?» → explain route, без записи вкуса;
- «больше такое не советуй» → explicit stable constraint/preference route, а не просто interaction.

## 7. Profile routes

### 7.1 «Что ты понял о моём вкусе?»

Read/explain. Показывает explicit + inferred с evidence/confidence, ничего не меняет.

### 7.2 «Переосмысли мой вкус»

`reanalyze_preferences` по утверждённому v5 flow. Новая LLM-гипотеза сохраняется только через schema-validated canonical inferred preferences.

### 7.3 «Ты неправильно понял, я не люблю X»

Если это явное устойчивое утверждение пользователя, оно становится explicit preference/correction. Нельзя просто удалить inferred hypothesis и оставить contradiction unresolved.

### 7.4 «Удали этот вывод обо мне»

Нужно различить:

- пользователь оспаривает вывод → correction/explicit counter-evidence;
- пользователь просит скрыть/удалить inferred hypothesis → clear inferred preference;
- пользователь требует удалить исходные отзывы/ratings → это отдельные feedback clear/purge операции.

## 8. Semantic film knowledge routes

### 8.1 Отзыв о новом фильме

Если work создаётся через `record_viewing_feedback(create_if_missing=true)`, factual metadata приходит от provider. LLM explicit feedback записывается сразу.

Semantic fingerprint enrichment может быть выполнен в той же user journey только если typed contract делает provenance separation однозначным; иначе это отдельная безопасная enrichment operation.

### 8.2 «Обнови понимание этого фильма»

Маршрут semantic enrich: обновляет film-level knowledge/fingerprint, не user preferences напрямую.

### 8.3 Новое понятие, которого нет в vocabulary

Агент не добавляет term скрыто. Он либо использует существующий canonical/alias, либо оставляет концепт вне structured term и поднимает vocabulary proposal как отдельную developer задачу.

## 9. Website parity

Website обязан использовать те же intent semantics.

### 9.1 Read/Explain UI — обязательная часть v5

Manifest/read model должен уметь доставлять сайту:

- explicit preferences;
- inferred preferences + confidence;
- evidence pointers;
- film semantic fingerprints;
- cross-work correlations;
- couple overlap/disagreement hints;
- recommendation explanations;
- external recommendation candidates/interactions, если они сохранены canonical/derived способом.

Сайт может показывать:

- «Мой вкус»;
- «Почему система так думает?»;
- evidence films;
- «что изменилось после последних просмотров»;
- contradiction/uncertain areas;
- semantic traits фильма;
- «почему это может подойти»;
- couple fit;
- recommendation inbox/history.

### 9.2 Website write actions

Существующий write-broker путь расширяется только typed operations. UI affordances должны маппиться на те же операции, что LLM/CLI:

- поставить/изменить rating;
- изменить viewing/reaction/feedback;
- clear отдельного сигнала;
- interest;
- recommendation interaction.

Никакого отдельного browser-only data model.

### 9.3 Live AI — отдельная boundary

Статический Pages не содержит model/provider secrets.

Для будущих действий:

- «Посоветуй прямо сейчас»;
- «Переосмысли мой вкус»;
- свободный AI-разбор отзыва;
- external discovery;

нужен authenticated Intelligence Broker / server-side boundary. Browser отправляет typed/high-level request, сервер вызывает LLM/providers и возвращает structured result.

Недоступность Live AI не должна ломать обычную read-only медиатеку и уже опубликованные intelligence artifacts.

## 10. Real-life scenario catalog

Отдельный нормативный каталог сценариев хранится в `2026-10-03-media-intelligence-v5-agent-scenario-catalog.md` и является обязательным источником при обновлении `AGENTS.md`, command schemas, CLI и website routes.

Каталог должен охватывать как минимум:

- read/show/search;
- first rating;
- re-rating;
- add/replace feedback;
- correction неправильного target/work;
- clear rating/reaction/feedback/viewing;
- privacy purge;
- undo/revert последней операции;
- add work without feedback;
- remove/merge duplicate work;
- watched/partial/dropped/forgotten/rewatch;
- set/unset interest;
- internal/external/couple/exploration recommendations;
- recommendation accepted/rejected/not-tonight/already-watched;
- explicit stable preference/constraint;
- explain profile/correlation/recommendation;
- reanalyze profile;
- correct inferred preference;
- semantic fingerprint enrichment;
- metadata refresh;
- unknown vocabulary concept;
- ambiguous film identity;
- provider outage;
- partial failure/transaction rollback;
- website equivalent actions;
- preview/no-save request;
- bulk maintenance requiring manual review.

## 11. GitHub workflow documentation must reflect reality

При миграции `AGENTS.md`/`README.md` на v5 нужно удалить устаревшее описание автоматического `pull_request` Media Check. После PR #40 authoritative `media-check.yml` является dispatch-only и запускается `Media Command` на exact resulting head SHA.

Agent docs должны описывать фактический текущий route, иначе новая модель будет получать противоречивые инструкции.

## 12. Development continuity

Все implementation PR, создаваемые для реализации v5, обязаны следовать `2026-10-03-media-intelligence-v5-development-continuity-contract.md`.

PR body является актуальным handoff snapshot с текущей фазой, head SHA, completed work, свежим verification evidence, blockers, deviations и следующими шагами. Значимые phase boundaries и остановки дополнительно фиксируются append-only checkpoint comments.

Новая сессия/агент обязаны восстановить контекст из spec + implementation plan + PR status + latest checkpoint + фактического PR head/CI до продолжения product-code изменений.

## 13. Definition of done для v5 agent/web integration

Фаза считается завершённой только когда:

1. typed operations покрывают необходимые intents;
2. `AGENTS.md` документирует routes и guardrails;
3. `START_PROMPT.md` кратко активирует этот operating contract;
4. `README.md` описывает актуальную архитектуру;
5. site manifest/types/UI не отстают от canonical model;
6. website writes используют тот же typed-command boundary;
7. tests покрывают routing/data invariants;
8. legacy workflow docs не противоречат dispatch-only Media Check;
9. implementation PR поддерживает актуальный continuity snapshot и checkpoints.
