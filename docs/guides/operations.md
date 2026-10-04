# Operations runbook

Короткий runbook для проверки, пересборки, web verification и recovery. Команды предполагают запуск из корня репозитория, если не указано иное.

## Установка Python dependencies

```bash
python -m pip install -r media/requirements.txt
```

## Полный media verification

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Интерпретация:

- pytest — executable contracts;
- `validate` — canonical schemas/invariants;
- `rebuild --check` — committed generated artifacts соответствуют canonical state;
- `doctor` — repository/runtime integrity diagnostics.

Не объявляйте change GREEN, если прошёл только focused test, а полный suite красный.

## Явная пересборка derived artifacts

Если нужно пересобрать, а не только проверить:

```bash
python -m media.tools.build_index media
python -m media.tools.build_profiles media
python -m media.tools.build_db media
```

`generated/database.sqlite` является rebuildable runtime artifact и не должен восприниматься как canonical source of truth.

После rebuild снова выполните validation + `rebuild --check` + doctor.

## Web manifest

Проверка exporter вручную:

```bash
python -m media.cli web-export --output /tmp/media-web-manifest.json --format json
```

Current manifest contract описан в `docs/architecture/web-and-broker.md`; schema/exporter code остаётся фактическим источником version truth.

## Web verification

```bash
cd web
npm ci
npm run test:run
npm run typecheck
npm run build
```

Если change затрагивает browser behavior/visuals, также выполняйте Playwright/browser checks и static artifact scan согласно `.github/workflows/web-check.yml` / Pages workflow.

`npm run build` уже включает TypeScript check по текущему `package.json`, но отдельный `npm run typecheck` полезен как явный gate и закреплён CI.

## Canonical validation отдельно

Для быстрого preflight:

```bash
python -m media.tools.validate .
```

Validation failure чинится в canonical/schema/domain layer. Не правьте generated output вручную, чтобы «скрыть» canonical error.

## Metadata maintenance

Bulk metadata refresh выполняется через typed maintenance operation `refresh_metadata` со scope `all_movies`.

Maintenance должен:

- выполнить identity preflight до mutation;
- сохранить user-owned signals и manual overrides;
- не оставлять partial mutation при ambiguity/provider failure;
- пройти manual review/merge.

`refresh_metadata` не является normal auto-merge operation.

## GitHub Actions gates

Основные роли workflows:

- Media Command — применить typed operation детерминированно;
- Media Check — authoritative exact-head gate для normal operation result;
- Media Dev Check — developer/manual PR regression gate;
- Web Check — frontend tests/type/build/browser/security checks;
- Media Pages — exact-revision build + GitHub Pages deploy.

Название workflow важно меньше contract: success должен относиться к exact revision, которую вы собираетесь merge/publish.

## Проверка Pages после merge

После web/media change:

1. убедитесь, что `main` указывает на ожидаемый merge SHA;
2. найдите Media Pages run для этого же SHA;
3. подтвердите build success;
4. подтвердите deploy success;
5. при UI-impact проверьте опубликованную surface/browser checks.

До success на merge SHA публикацию нельзя считать завершённой.

## Stale generated artifacts

Симптом: canonical validation проходит, но `rebuild --check` показывает drift.

Порядок:

1. убедитесь, что canonical change intentional;
2. выполните deterministic rebuild соответствующих artifacts;
3. не добавляйте ручные правки в generated output;
4. повторите полный media verification.

Если rebuild меняет неожиданные unrelated artifacts, сначала расследуйте root cause.

## Interrupted work / recovery

При возобновлении работы:

1. проверьте current `main`;
2. найдите active PR/ветку;
3. прочитайте последний PR checkpoint;
4. сравните exact head SHA и CI state;
5. продолжайте с первого незавершённого task, не воспроизводя уже подтверждённые шаги.

Durable project state находится в `docs/status/current.md`; transient development progress — в active PR.

## Provider failure

Provider unavailable/ambiguous identity — не повод угадывать. Mutation должна остановиться до partial write или вернуть корректный needs-input/unavailable result согласно operation contract.

## Когда нужен отдельный incident/debug pass

Не «подгоняйте» тест/validation под неожиданный failure. Сначала определите root cause, особенно если:

- failure появляется только в CI;
- generated state расходится с canonical;
- exact-head workflow проверяет не тот SHA;
- browser build содержит credential-like content;
- provider identity разрешается неоднозначно.
