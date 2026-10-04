# Media Intelligence Correctness & Observability — implementation-plan review amendment

Дата: 2026-10-04  
Статус: **normative amendment to the implementation plan**  
Изменяет: `docs/superpowers/plans/2026-10-04-media-intelligence-correctness-observability.md`  
Основание: external review `review-correctness-observability-plan.md` + verification against current v5.1 code/workflows

Этот amendment является частью implementation plan и читается вместе с основным plan, основной design spec и normative design amendment. При конфликте с более ранним implementation-plan text этот файл имеет приоритет. Scope Stage A не расширяется новой model/scoring логикой.

## 1. Review resolution

Подтверждены и принимаются в plan:

1. единая строгая семантика path-pattern matching для Python и privileged workflow;
2. механическая проверка полноты audit digest inventory против фактических repository reads;
3. полный web verification gate для PR1, потому что web manifest прямо потребляет recommendation/taste/profile outputs;
4. краткое однократное user-facing disclosure активных limitations;
5. явная документация trust assumption для `workflow_run`;
6. merge-commit requirement для PR0, чтобы baseline `source_revision` оставался достижимым из `main`.

Не принимается как delivery change предложение выделить Tasks 9–10 в третий implementation PR. Утверждённая Stage A spec фиксирует два последовательных PR: PR0 и PR1. Вместо нового PR trust-boundary работа остаётся отдельными commits/tasks внутри PR1 и получает отдельный review section/checklist в PR description.

---

## 2. Amendment to Task 2 — mechanical audit-read coverage

Task 2 сохраняет существующий `audit_input_paths(repo_root)` и `canonical_input_digest(repo_root)` contract, но добавляет обязательный read-tracing regression test.

### 2.1 Read tracing contract

Добавить тест:

`test_audit_repository_reads_are_digest_covered_or_explicitly_exempt(tmp_path, monkeypatch)`.

Тест запускает `collect_intelligence_audit()` на fixture repository и журналирует фактические file reads под repository root через обёртки для `Path.open`, `Path.read_text` и `Path.read_bytes` (либо эквивалентную низкоуровневую точку, если implementation использует другой helper).

После запуска каждый прочитанный repository file относится ровно к одной категории:

1. **digest-covered input** — путь присутствует в `audit_input_paths(repo_root)`;
2. **explicit non-data dependency** — разрешён только заранее объявленным narrow allowlist, первоначально `media/schemas/**`, которые читаются canonical validation, но versioned через git/source revision, а не data-content digest.

Любой новый фактический repository read вне этих двух категорий ломает тест. Нельзя добавлять broad exclusions вроде `media/**`.

Если validation/collector фактически читает canonical/config data, которых нет в текущем inventory, implementation Task 2 должен добавить их в `audit_input_paths()` в том же RED→GREEN change. Schema/tool source files остаются git-provenance dependencies, а не data digest inputs.

### 2.2 Reverse property remains required

Существующий negative test сохраняется: изменение файла, который действительно не является audit input и не читается collector/validation как data, не должно менять `canonical_input_digest` или audit metrics.

Это делает Review Focus `Audit digest drift` механически проверяемым, а не только дисциплиной разработчика.

---

## 3. Amendment to Tasks 9–10 — one strict path-matching language

Текущие v5.1 реализации доказанно расходятся:

- Python `PurePosixPath.match("media/data/works/*.yaml")` допускает suffix match вроде `evil/media/data/works/x.yaml`;
- bash `case` для того же шаблона допускает `media/data/works/sub/x.yaml`, потому что `*` пересекает `/`.

Stage A не переносит ни одну из этих семантик в новый policy contract.

### 3.1 Declarative pattern grammar

`media/config/operation_path_policy.json` использует намеренно узкий Stage A grammar:

- путь всегда repository-relative POSIX path без ведущего `/`;
- pattern без `*` означает exact whole-path equality;
- pattern может содержать **ровно один** `*`;
- `*` означает zero-or-more characters внутри одного path segment и **никогда не пересекает `/`**;
- `**`, второй `*`, character classes (`[]`), `?`, brace expansion и shell-specific glob syntax не поддерживаются и делают policy invalid/fail-closed;
- matching всегда anchored к началу и концу всего repository-relative path.

Примеры для `media/data/works/*.yaml`:

| path | expected |
| --- | --- |
| `media/data/works/x.yaml` | allow |
| `evil/media/data/works/x.yaml` | reject |
| `media/data/works/sub/x.yaml` | reject |
| `media/data/works/x.yaml.bak` | reject |

Python `path_policy.py` больше не использует `PurePosixPath.match` для declarative policy patterns. Он реализует exact/one-segment-wildcard semantics напрямую.

Privileged workflow также не использует shell glob semantics для policy matching. Он реализует тот же prefix/suffix/single-segment contract после parsing trusted JSON policy.

### 3.2 Shared parity corpus

Добавить fixture:

`tests/media/fixtures/operation_path_policy_cases.json`.

Каждый case содержит как минимум:

- `operation`;
- `pattern`;
- `path`;
- `expected`.

Обязательные negative classes:

- leading-prefix injection: `evil/media/...`;
- nested path under a single-segment wildcard;
- suffix extension `.bak`;
- policy file itself;
- `.github/workflows/**`;
- `media/service/**`;
- `media/tools/**`;
- guard/test/code paths not explicitly allowed.

Обязательные positive classes включают normal work, relation, interaction, profile, operation-marker paths согласно policy.

### 3.3 Two implementations, one executable contract

Добавить parity tests, которые прогоняют **один и тот же fixture corpus** через:

1. Python matcher из `media/service/path_policy.py`;
2. matcher function из `.github/workflows/media-auto-merge.yml`, выполняемую как shell snippet/subprocess в test environment.

Workflow matcher должен быть выделен в чётко именованный shell function/block, чтобы test мог извлечь/исполнить именно production logic, а не отдельную тестовую копию.

Обе реализации обязаны давать `expected` для каждого case.

### 3.4 Policy-coverage test

Добавить test, который загружает `operation_path_policy.json` и проверяет:

- каждая operation с `auto_merge: true` присутствует в corpus;
- каждый `allowed_paths` pattern каждой auto-merge operation имеет минимум один positive case;
- corpus содержит общие protected negative classes;
- unsupported pattern grammar отклоняется fail-closed в Python и workflow path.

Изменение auto-merge operation/pattern без обновления parity corpus должно ломать tests.

### 3.5 Task 10 trust inputs remain unchanged

Privileged auto-merge eligibility по-прежнему строится из двух trusted inputs:

1. policy JSON, fetched from `main` через GitHub contents API;
2. changed-file inventory, fetched через PR files API.

PR-head используется только как data source для operation marker/status/kind, не как executable policy/guard source.

Любой fetch/decode/schema/matcher error = ineligible/fail-closed.

---

## 4. Amendment to Task 11 — PR1 is web-impacting

Это решение теперь explicit: PR1 считается **web-impacting**, хотя Stage A не меняет manifest schema.

Причина: `media/service/web_export.py` напрямую экспортирует generated profiles и вызывает `build_recommend_context()`/`build_taste_context()`. Task 5 меняет profile content, Tasks 6 и 8 меняют recommendation/taste payloads. Поэтому только `web-export` недостаточен.

### 4.1 Full local/CI web gate

После final PR1 commit выполнить полный существующий Web Check equivalent:

```bash
python -m media.cli web-export --output web/public/data/manifest.json --format json
cd web
npm ci
npm run test:run
npm run typecheck
VITE_MEDIA_BROKER_URL=https://broker.test npm run build
EXPECTED_BROKER_URL=https://broker.test node ./scripts/assert-broker-build-env.mjs dist
npm run scan:dist
npx playwright install --with-deps chromium
VITE_MEDIA_BROKER_URL=https://broker.test npm run test:e2e -- responsive.spec.ts motion.spec.ts a11y.spec.ts edit-feedback.spec.ts
VITE_MEDIA_BROKER_URL=https://broker.test npm run test:e2e -- review.spec.ts
```

Expected: all commands PASS/exit 0.

### 4.2 Exact-head Web Check evidence

Поскольку current `Web Check` path filters не включают все Stage A service/profile paths, PR1 completion не полагается на автоматический trigger.

После freeze final PR1 head:

1. сохранить `EXPECTED_SHA=$(git rev-parse HEAD)`;
2. manually dispatch `.github/workflows/web-check.yml` for the PR branch;
3. verify resulting workflow run `head_sha == EXPECTED_SHA`;
4. require conclusion `success` before merge.

Если branch head изменился после dispatch, предыдущий Web Check не считается evidence для нового head.

Stage A **не расширяет** scope изменением Web Check trigger paths; это отдельная CI-routing decision. Здесь требуется explicit final verification только для PR1.

---

## 5. Amendment to Task 11 — limitation disclosure UX

Agent contract уточняется без thresholds/scoring:

- material active limitations сообщаются **один раз на user-facing answer**;
- формулировка краткая и естественная, без повторения одного limitation в каждом recommendation paragraph/candidate card;
- если несколько machine-readable limitation codes сводятся к одной понятной причине (например, низкое semantic coverage), agent может объединить их в одну короткую оговорку без потери смысла;
- полный список machine-readable limitations доступен по запросу/debug context;
- fallback candidate нельзя описывать как semantic-personalized match;
- отсутствие/частичность evidence не маскируется как уверенность.

Тесты `test_agent_ux_contract.py` должны закрепить “once per answer / concise / no repetitive limitation narration” wording.

---

## 6. Amendment to Task 11 docs — why privileged workflow definition is trusted

`docs/architecture/write-pipeline.md` должен явно описать текущую security assumption:

- `media-auto-merge.yml` запускается через `workflow_run`;
- для `workflow_run` GitHub использует default-branch event ref/SHA и workflow должен существовать на default branch;
- поэтому mutable PR не подменяет исполняемое определение privileged auto-merge workflow;
- workflow отдельно fetches trusted policy from `main` and changed-file inventory from GitHub PR metadata API;
- изменение trigger model (`pull_request_target`, checkout/eval PR-head code или другой mechanism) требует отдельного security review — нельзя переносить текущий trust argument автоматически.

`tests/media/test_auto_merge_dispatch_contract.py` сохраняет assertion на `workflow_run` trigger как security contract, а docs test фиксирует эту assumption prose-level.

---

## 7. Amendment to PR0 merge checkpoint — preserve baseline source revision

`media/baselines/intelligence-stage-a.meta.json.source_revision` указывает на clean committed state, из которого был сгенерирован baseline. Чтобы этот SHA оставался достижимым из истории `main`, PR0 нельзя squash/rebase-merge.

PR0 merge step изменяется на:

1. require exact final PR0 head green;
2. merge PR0 методом **merge commit** (`merge_method=merge`, например `gh pr merge <PR> --merge`);
3. после merge fetch/update `main`;
4. verify `git merge-base --is-ancestor "$SOURCE_REVISION" origin/main` succeeds;
5. verify baseline payload/meta still parse and `source_revision` equals measured clean implementation commit.

Если repository policy запрещает merge commits, PR0 не следует silently squash: нужно остановиться и пересмотреть provenance contract до merge.

Это требование относится именно к PR0 baseline provenance; оно не меняет обычную merge policy для других developer PR без embedded source-revision provenance.

---

## 8. PR1 review packaging remains one PR

PR1 остаётся единым correctness + observability delivery согласно approved spec.

Для облегчения security review:

- Tasks 4–8 commits описываются в PR body как **Intelligence correctness/observability**;
- Tasks 9–10 commits описываются отдельным разделом **Trust boundary / privileged auto-merge**;
- Task 11 verification report отдельно перечисляет media gate, web gate и trust-boundary tests;
- reviewer может approve/inspect эти группы независимо, но merge происходит одним exact-head PR1 после прохождения всех gates.

---

## 9. Updated completion evidence

К исходному Stage A completion evidence добавляются обязательные пункты:

- Python и privileged workflow используют одинаковую anchored single-segment wildcard semantics, подтверждённую общим parity corpus;
- каждый auto-merge operation/pattern покрыт corpus и не может быть добавлен без test update;
- фактические repository reads audit collector покрыты digest inventory либо narrow explicit schema exemption;
- final PR1 head прошёл полный Web Check equivalent и exact-head dispatched Web Check;
- user-facing active limitations раскрываются кратко и не более одного раза на ответ;
- living write-pipeline docs фиксируют `workflow_run` default-branch trust assumption;
- PR0 merged with merge commit and baseline `source_revision` подтверждён как ancestor of merged `main`.

Только после этих проверок основной implementation plan + этот amendment считаются полностью выполненными.