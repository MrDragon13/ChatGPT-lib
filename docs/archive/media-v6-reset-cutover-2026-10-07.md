# Archived: Media Intelligence v6 cutover/reset record

> Historical artifact only. The v6 reset completed on 2026-10-07. Current operating rules live in `media/AGENTS.md`, `docs/status/current.md`, and the living architecture/reference docs.

Этот документ фиксирует одноразовый переход со старой активной медиатеки на v6 и правила восстановления после него.

## Что было защищено до удаления

Перед reset был детерминированно создан и побайтно проверен:

`docs/archive/media-library-before-v6-reset-2026-10-07.md`

Архив содержит 103 произведения в человекочитаемом виде, а также доступные пользовательские сигналы, явно заданное сходство и названия подборок. Он не является машиночитаемым backup и не участвует автоматически в анализе вкуса.

Контрольная точка перед destructive reset: `4e96881459d44aa87b07edbf4566f90d28e40bad`.

## Проверенный план удаления

Перед применением reset dry-run показал:

- works: 103;
- collections: 4;
- similarity files: 1;
- interactions: 0;
- inferred preference files: 3;
- legacy pilot files: 1;
- Stage A baseline files: 2;
- старые operation receipts: 33;
- всего удаляемых файлов: 147.

Открытых `media/op-*` PR и pending `.media/requests/*.json` не было.

Legacy pilot формально оставался active, но его operational session-state не переносился в v6 по утверждённой архитектуре. Canonical пользовательские данные произведений были защищены MD-архивом.

## Что сохраняется

Reset не удаляет:

- `media/preferences/explicit/**`;
- `media/vocabulary.yaml`;
- viewer/group config;
- схемы и код v6;
- Web/Broker;
- Git history.

## Что удаляется из активного runtime

- старые works и collections;
- explicit work similarity;
- interactions;
- inferred preferences;
- legacy reassessment pilot/runtime;
- Stage A active baselines;
- старые operation receipts.

После reset generated index и profiles пересобираются из пустой canonical библиотеки.

## Проверка пустого состояния

Обязательные инварианты:

- works = 0;
- collections = 0;
- similarity = 0;
- interactions = 0;
- inferred preferences = 0;
- старый pilot отсутствует;
- `media/generated/index.jsonl` валидно пуст;
- profiles для `primary`, `partner`, `couple` имеют `entity_count=0`;
- global explicit preferences сохранены;
- validate, rebuild, doctor, Web export и read-contexts работают детерминированно.

## После cutover

Новый пользовательский эпизод записывается через `record_media_entry`. Старый архив можно читать как чек-лист, но нельзя автоматически импортировать в активный вкус или показывать старую оценку до нового ответа пользователя.

## Откат

До появления новых пользовательских записей v6 допускается контролируемый revert cutover-коммита/PR.

После появления нового v6 evidence **слепой revert запрещён**: он потеряет новые данные. В этом случае используется только forward migration, которая сохраняет уже записанное новое evidence.

## Проверки перед merge PR cutover

Обязательны:

- полный Python gate;
- canonical validation;
- `rebuild --check`;
- doctor;
- Broker tests/typecheck;
- Web tests/typecheck/build;
- Playwright/a11y;
- post-cutover сценарии: пустая библиотека, новый work, второй feedback fast path, threshold=5, Web merged → published.
