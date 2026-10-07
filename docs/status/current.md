# Current status

Текущая capability line: **Media Intelligence v6**.

Этот файл описывает устойчивое текущее состояние проекта после атомарного перехода на v6. Временный прогресс разработки хранится в активных PR, а исторические причины решений — в `docs/superpowers/` и Git history.

## Текущее состояние данных

- Git/YAML в `main` остаётся canonical source of truth.
- Активная медиатека после v6 reset начинается с пустого набора works.
- Collections, explicit work similarity, interactions и inferred preferences после reset пусты.
- Глобальные explicit preferences пользователя сохранены.
- Controlled vocabulary, schemas, code, Broker и Web сохранены.
- `docs/archive/media-library-before-v6-reset-2026-10-07.md` хранит человекочитаемый снимок старой медиатеки, но **не участвует автоматически** в рекомендациях, анализе вкусов или восстановлении canonical data.
- Legacy reassessment pilot/runtime удалён.

Пустая библиотека — ожидаемое валидное состояние. Index, profiles, web manifest, doctor, validate и read-contexts должны работать детерминированно и без специальных ручных обходов.

## Запись данных

Основной LLM/browser маршрут для нового человеческого события — `record_media_entry`.

### Существующее произведение

Обычный отзыв о существующем work:

- не обращается к metadata provider;
- не запускает metadata refresh;
- не пересчитывает semantic fingerprint при неизменном semantic input;
- выполняет одну typed operation;
- пересобирает каждый затронутый derived output максимум один раз.

### Новое произведение

Новый work создаётся одной атомарной `record_media_entry(create_if_missing=true)`:

1. подтверждается устойчивая identity;
2. provider даёт минимальные необходимые factual data;
3. LLM один раз подготавливает semantic snapshot;
4. work + semantics + viewer evidence применяются одной transaction.

Старая последовательность `add → reread → semantics → feedback` не является normal path.

## GitHub write pipeline

Обычные auto-merge операции проходят один основной `Media Command` runner:

```text
request-only PR
→ очередь media-data-pipeline
→ replay typed intent на свежий main
→ transaction
→ dependency-driven rebuild
→ operation-specific authoritative gate
→ exact-head/base check
→ merge через GitHub API
→ Media Pages для merge SHA
```

Очередь использует одну concurrency-group, не отменяет ожидающие записи и не заменяет final base/head guard.

`media/config/operation_path_policy.json` задаёт разрешённые пути и execution class.

- Все normal auto-merge операции используют `v6_single_runner`.
- Bulk `refresh_metadata` остаётся `manual_review`.
- Старые `Media Check` и `Media Auto Merge` удалены.

Для developer changes по Python, schemas, workflows, vocabulary, architecture/config, Web/Broker logic остаются полные PR-проверки.

## LLM-first UX и pending state

GitHub — граница долговременного сохранения, но не граница задержки разговора.

После отправки корректной операции текущая LLM-сессия может сразу учитывать свежие явные пользовательские сигналы. Слово «сохранено» допустимо только после появления результата в `main`.

Если по тому же work уже есть pending write, следующее уточнение можно держать локально в текущем разговоре, но новый Git-write отправляется только после authoritative первой операции и повторного чтения свежего viewer digest.

Web использует тот же принцип: второй submit по тому же work/target блокируется, а локальный черновик пользователя сохраняется.

## Broker и Web

Cloudflare Broker остаётся stateless write bridge.

Production `POST /v1/feedback` теперь преобразует browser feedback в `record_media_entry`:

- читает viewer digest из `media/generated/index.jsonl` на exact SHA текущего `main`;
- создаёт request-only operation PR от того же SHA;
- не передаёт browser-клиенту внутреннюю логику digest/precondition;
- не хранит GitHub/provider/model secrets в static Web bundle.

Web manifest остаётся **v3**. Внутренние viewer digests не публикуются в browser manifest.

Пустая Web-медиатека показывает честный empty state вместо выдуманного кандидата.

## Derived state

Versioned derived state остаётся в Git:

- `media/generated/index.jsonl`;
- `media/generated/profiles/*.yaml`;
- static web manifest в Pages build.

Пересборка строится из `changed_domains → DirtyPlan`. Каждый нужный output перестраивается максимум один раз за transaction.

SQLite не является canonical storage и не хранится в Git. Существующий `build_db.py` / `SQLiteRepository` можно использовать как временный локальный/диагностический read model; `doctor` строит SQLite только во временном каталоге.

## Taste reanalysis

Deep taste reanalysis не входит в critical path каждого отзыва.

Для `primary` и `partner` отдельно хранится evidence checkpoint. Default threshold — **5** новых содержательных explicit events.

- Retry, `no_change`, metadata-only и косметическая правка summary не считаются новым событием.
- Свежие explicit signals всегда имеют приоритет над stale inferred interpretation.
- Перед taste-dependent decision при достигнутом threshold LLM сначала выполняет fresh reanalysis.
- Результат сохраняется отдельной `set_inferred_preferences` вместе с evidence checkpoint/digest и algorithm version.
- `couple` не имеет отдельного счётчика; проверяются его участники.

Generated viewer profiles кэшируют reanalysis status, поэтому recommendation read-path не сканирует всю canonical библиотеку.

## Intelligence invariants

- Explicit user evidence важнее inferred evidence.
- Inferred output не становится самостоятельным evidence для следующего inference.
- Film semantic fingerprint описывает work, а не viewer sentiment.
- Rating/reaction не являются factual work traits.
- Controlled vocabulary обязателен для semantic fingerprint.
- Explicit similarity — evidence/hint, а не preference.
- Couple disagreement остаётся видимым.
- Candidate assessment остаётся qualitative: никакой fake precise probability или opaque match score.
- Неполное semantic/evidence coverage отражается через limitations.

`assess_candidate`, `recommend_context`, `taste_context` и `media_entry_context` остаются read-only.

## Recommendation cold start

После reset локальный recommendation pool пуст. Это не ошибка.

- `recommend_context` сообщает `empty_library`.
- `taste_context` при отсутствии work evidence сообщает `cold_start_no_work_evidence`.
- Сохранённые global explicit preferences остаются доступными.
- General recommendation request может использовать external discovery; локальная медиатека по мере нового заполнения снова становится памятью, evidence и exclusion layer.

## Архив старой библиотеки

Pre-v6 archive — только человеческая памятка и чек-лист.

При повторном прохождении старого фильма agent не должен до нового ответа автоматически показывать старый rating/reaction/feedback. После fresh ответа work добавляется обычным v6 flow.

Техническая история остаётся в Git. Quality regression защищается synthetic/reference fixtures, а не старой активной персональной библиотекой.

## Известные ограничения

- В первые дни после reset personalized work evidence мало; confidence reasoning обязан отражать cold start.
- Evidence партнёра может накапливаться медленнее, чем `primary`.
- Internal recommendations ограничены текущей локальной библиотекой; при пустом pool они честно пусты.
- External discovery/live model reasoning остаётся на agent/server boundary.
- Bulk provider metadata refresh требует manual review.
- Controlled vocabulary меняется только отдельным developer/architecture PR.
- Public Web manifest пока остаётся v3; внутренние v6 bookkeeping fields не обязаны быть browser-visible.

## Verification model

Developer changes считаются проверенными только после релевантного полного gate:

- pytest;
- canonical validation;
- generated rebuild consistency;
- doctor;
- для Broker: tests + typecheck;
- для Web: manifest export, tests, typecheck, build и browser/a11y checks.

Для публикации важна exact revision: Pages соответствует merge SHA, а не более раннему зелёному commit.

## Где читать подробнее

- `docs/architecture/overview.md` — границы системы;
- `docs/architecture/media-model.md` — canonical/derived модель;
- `docs/architecture/intelligence.md` — taste, recommendations, assessment;
- `docs/architecture/write-pipeline.md` — typed write lifecycle;
- `docs/architecture/web-and-broker.md` — Web/Broker security и write flow;
- `docs/reference/media-commands.md` — каталог операций;
- `docs/reference/invariants.md` — обязательные правила;
- `docs/runbooks/media-v6-reset.md` — одноразовый cutover/reset runbook.

Dated files под `docs/superpowers/specs/` и `docs/superpowers/plans/` сохраняются как история решений и не заменяют current code, schemas или living docs.
