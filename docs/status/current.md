# Текущее состояние

Текущая версия — **Media Intelligence v6**.

Этот файл хранит только устойчивое состояние проекта. Временный прогресс конкретной ветки, PR или CI-run сюда не попадает.

## Данные

- Git/YAML в `main` остаётся главным источником истины.
- Reset 7 октября 2026 года начал новую v6-библиотеку с пустого состояния.
- После reset библиотека уже снова наполняется обычными v6-записями; пустота остаётся поддерживаемым техническим состоянием, а не описанием текущего содержимого.
- Старые collections, similarity, interactions и inferred preferences были очищены при reset и возвращаются только через новые v6-записи.
- Глобальные явные предпочтения пользователя и контролируемый словарь сохранены.
- Архив `docs/archive/media-library-before-v6-reset-2026-10-07.md` остаётся только человекочитаемой историей и автоматически в рекомендации не попадает.
- В текущем runtime нет старых v5 compatibility/pilot paths.

## Основная запись

Главная операция для нового пользовательского события — `record_media_entry`.

### Уже известное произведение

Обычный отзыв:

- не обращается к metadata provider;
- не обновляет metadata;
- не пересчитывает semantic fingerprint без причины;
- выполняется одной типизированной операцией;
- пересобирает только нужные производные данные.

### Новое произведение

`record_media_entry(create_if_missing=true)` делает всё одной атомарной операцией:

1. проверяет устойчивую provider identity;
2. доверенный runtime получает актуальные фактические metadata;
3. LLM один раз подготавливает semantic traits из контролируемого словаря;
4. произведение, semantics и пользовательские сигналы записываются вместе.

Старая последовательность `add → reread → semantics → feedback` больше не является обычным путём.

## Путь записи в GitHub

Обычные auto-merge операции проходят через единый `Media Command` runner:

```text
request-only PR
→ очередь media-data-pipeline
→ replay запроса на свежем main
→ transaction
→ минимальная пересборка
→ проверка операции
→ exact head/base check
→ merge через GitHub API
→ Media Pages для merge SHA
```

`media/config/operation_path_policy.json` задаёт разрешённые пути и класс исполнения.

Все обычные auto-merge операции используют `v6_single_runner`. Массовый `refresh_metadata` остаётся `manual_review`.

## Разговор во время записи

GitHub определяет момент долговременного сохранения, но не должен задерживать разговор.

После отправки корректной операции текущая LLM-сессия может сразу учитывать свежий явный сигнал. Говорить «сохранено» можно только после того, как результат появился в `main`.

Если по тому же произведению уже идёт запись, следующее уточнение остаётся локально в текущей сессии. После завершения первой операции агент заново читает `media_entry_context` и viewer digest.

Web использует тот же принцип: не отправляет второй submit по тому же `work/target`, но сохраняет локальный черновик.

## Broker и Web

Cloudflare Broker остаётся stateless мостом для записи из браузера.

Production `POST /v1/feedback` преобразует браузерный отзыв в `record_media_entry`, читает viewer digest на точном SHA `main` и создаёт request-only PR от того же SHA.

Production Broker для текущей v6-версии опубликован. Последующие изменения Broker по-прежнему требуют ручного `Broker Deploy` с ожидаемым SHA.

Web manifest — **v4**. Он публикует нужный reanalysis gate, но не внутренние viewer/evidence digests и служебные данные операций.

Пустая библиотека отображается честным empty state без выдуманных кандидатов.

## Производные данные

В Git хранятся пересобираемые:

- `media/generated/index.jsonl`;
- `media/generated/profiles/*.yaml`;
- данные для Web manifest в Pages build.

Пересборка идёт через `changed_domains → DirtyPlan`. Каждый нужный результат строится максимум один раз за transaction.

SQLite не является каноническим хранилищем и не коммитится как источник истины.

## Повторный анализ вкуса

Глубокий reanalysis не запускается после каждого отзыва.

Для `primary` и `partner` отдельно хранится evidence checkpoint. Порог по умолчанию — **5** новых содержательных событий.

- Повторы, `no_change`, metadata-only изменения и косметическая правка summary не считаются новым событием.
- Свежий явный сигнал важнее старой inferred interpretation.
- Если перед ответом, зависящим от вкуса, порог достигнут, сначала выполняется новый анализ.
- Результат сохраняется через `set_inferred_preferences` вместе с checkpoint/digest и версией алгоритма.
- У `couple` нет отдельного счётчика.

## Основные правила intelligence

- явные слова пользователя важнее выведенных гипотез;
- выведенный результат не становится самостоятельным evidence для следующего вывода;
- semantic fingerprint описывает произведение, а не эмоцию зрителя;
- rating/reaction не являются фактическими traits фильма;
- semantic fingerprint использует контролируемый vocabulary;
- similarity помогает рассуждению, но не является preference;
- разногласия пары не скрываются усреднением;
- `assess_candidate` даёт качественный вывод, а не псевдоточную вероятность;
- недостаток данных отражается через coverage и `limitations`.

`assess_candidate`, `recommend_context`, `taste_context` и `media_entry_context` остаются read-only.

Явное сходство записывается через `set_work_similarity` и удаляется через `remove_work_similarity`.

## Cold start и пустая библиотека

Поддержка пустой библиотеки остаётся обязательной:

- при `works=0` `recommend_context` сообщает `empty_library`;
- при отсутствии work evidence `taste_context` сообщает `cold_start_no_work_evidence`;
- глобальные явные предпочтения всё равно доступны;
- обычная рекомендация может использовать внешний поиск.

Это технический edge case и состояние сразу после reset, а не утверждение, что библиотека сейчас пуста.

## Архив до v6

Архив старой библиотеки — только памятка.

Если пользователь заново обсуждает старый фильм, агент не показывает прежнюю оценку, реакцию или отзыв до нового ответа, если пользователь сам этого не попросил.

Качественные правила проверяются синтетическими/reference fixtures, а не старой персональной библиотекой.

## Известные ограничения

- Персональный evidence после reset всё ещё заметно меньше старой библиотеки.
- Данные партнёра могут накапливаться медленнее, чем данные `primary`.
- Внутренние рекомендации ограничены локальной библиотекой.
- Внешний поиск и live model reasoning остаются на agent/server boundary.
- Массовый `refresh_metadata` требует ручного review.
- Контролируемый словарь меняется отдельным developer PR.
- Публичный Web manifest v4 не раскрывает внутренние digests и bookkeeping.

## Как проверяется developer-изменение

Полная проверка включает:

- pytest;
- validation канонических данных;
- `rebuild --check`;
- doctor;
- для Broker — tests + typecheck;
- для Web — export manifest, tests, typecheck, build, browser/a11y checks.

Для публикации важна **exact revision**: Pages должны быть собраны для того же merge SHA, который находится в `main`.

## Где читать дальше

- `docs/architecture/overview.md`
- `docs/architecture/media-model.md`
- `docs/architecture/intelligence.md`
- `docs/architecture/write-pipeline.md`
- `docs/architecture/web-and-broker.md`
- `docs/reference/media-commands.md`
- `docs/reference/invariants.md`
- `docs/archive/media-v6-reset-cutover-2026-10-07.md` — историческая запись cutover/reset.

Датированные файлы в `docs/superpowers/` — история решений, а не описание текущего runtime.
