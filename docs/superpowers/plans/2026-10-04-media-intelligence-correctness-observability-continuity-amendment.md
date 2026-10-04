# Media Intelligence Correctness & Observability — development continuity amendment

Дата: 2026-10-04  
Статус: **normative amendment to the implementation plan**  
Изменяет: `docs/superpowers/plans/2026-10-04-media-intelligence-correctness-observability.md` и `2026-10-04-media-intelligence-correctness-observability-review-amendment.md`  
Область: development bureaucracy, living documentation, PR continuity/checkpoints

Этот amendment является обязательной частью execution contract для Stage A / PR0 и PR1. Он не меняет product scope, ranking, audit, assessment или trust-boundary semantics. Его цель — не допустить ситуации, когда реализация технически продвинулась, а PR и living documentation больше не позволяют безопасно понять текущее состояние или продолжить работу после паузы.

## 1. Development Continuity Contract

Каждый implementation PR (PR0 и PR1) ведётся как самодостаточный журнал текущей разработки.

Обязательны одновременно два слоя:

1. **living documentation в ветке** — описывает фактически реализованное состояние текущего branch head;
2. **PR continuity log** — фиксирует ход работы, проверки, отклонения и ближайшие локальные планы.

Historical specs/plans сохраняют rationale и не переписываются как будто они всегда описывали фактический implementation. Новые implementation-discovered решения оформляются явным amendment/deviation и затем отражаются в living docs.

## 2. Living docs обновляются по ходу разработки

Документацию нельзя откладывать целиком до финального Task 11.

Правило:

> если task/commit меняет observable behavior, public/read-model contract, security boundary, ownership/invariant или operational workflow, соответствующая living documentation обновляется в том же task либо непосредственно следующим documentation commit до перехода к следующему смысловому checkpoint.

Для Stage A это означает как минимум:

- PR0 audit/baseline behavior поддерживается в `docs/architecture/intelligence.md`, `docs/reference/repository-layout.md` и релевантном status/reference prose по мере появления реального contract;
- recommendation/assessment/couple semantics PR1 поддерживаются в `docs/architecture/intelligence.md` и `docs/reference/invariants.md` по мере реализации Tasks 5–8;
- path-policy/auto-merge trust boundary поддерживается в `docs/architecture/write-pipeline.md` одновременно с Tasks 9–10, а не только в конце;
- `media/AGENTS.md` обновляется вместе с появлением реально доступных observability/limitations semantics, чтобы agent contract не опережал и не отставал от branch code;
- `docs/status/current.md` в implementation branch должен быть точным относительно branch state, но не должен утверждать, что незамерженная capability уже находится на `main`. После merge он приводится к устойчивому main-state wording.

Task 11 остаётся обязательным, но его роль — **final reconciliation**: проверить consistency code/tests/AGENTS/living docs/status, а не впервые документировать уже давно реализованные изменения.

## 3. PR body как текущий status snapshot

С момента открытия PR его body содержит отдельный раздел `Development Status`, который обновляется in-place и отражает только актуальное состояние.

Минимальные поля:

- exact current head SHA;
- текущая task/subtask;
- состояние: `RED | GREEN focused | integration | blocked | verification | ready for review`;
- завершённые task boundaries;
- активные deviations/risks;
- последние релевантные checks и их SHA;
- ближайшие 1–3 локальные шага;
- ссылка/указатель на последний checkpoint comment.

PR body не используется как append-only history: старые детали переносятся/остаются в checkpoint comments, а body остаётся компактным current snapshot.

## 4. Append-only checkpoint comments

Помимо обновляемого PR body, PR получает append-only checkpoint comments. Старые checkpoints не редактируются задним числом, кроме исправления явной фактической ошибки отдельной follow-up записью.

Checkpoint обязателен в следующих границах:

1. **PR opened / execution start** — зафиксировать base, plan/spec refs, scope и первый локальный шаг;
2. **после каждого завершённого Task** — RED→GREEN evidence, commit/head SHA и следующий Task;
3. **после существенного partial milestone внутри длинного Task**, если работа уже полезно продолжима с этого места;
4. **при deviation от plan/spec** — до продолжения зависимых работ либо сразу после обнаружения, с причиной и решением;
5. **при blocker/неожиданном regression/security finding** — текущее evidence и безопасный следующий диагностический шаг;
6. **перед любой осознанной паузой/hand-off/end-of-session**, если работа не завершена;
7. **при возобновлении после паузы** — подтвердить, что branch/head/context перечитаны, и указать, какой checkpoint принят как точка старта;
8. **перед final verification freeze** — exact head, ожидаемые gates, отсутствие незапланированного scope;
9. **после final exact-head verification** — результаты media/web/security gates и readiness state;
10. **перед merge** — финальный resume/rollback context на случай, если merge или post-merge verification прервутся.

Не нужно писать checkpoint после каждого микрокоммита. Граница — task, значимый milestone, deviation, blocker, pause/resume или verification state change.

## 5. Формат checkpoint

Каждый checkpoint должен позволять другому исполнителю продолжить работу без восстановления контекста из всего чата.

Минимальный шаблон:

```text
Checkpoint: <Task / milestone>
Head: <exact SHA>
State: <RED | GREEN focused | integration | blocked | verification>

Completed:
- ...

Verification:
- <command/check> -> <result>
- exact-SHA CI evidence if available

Docs/contracts updated:
- <paths or "none required", with reason>

Deviations / risks:
- none | ...

Current local state:
- branch
- working tree clean/dirty
- uncommitted/generated files if any

Next local steps:
1. ...
2. ...
3. ...

Resume instructions:
- start from <branch>@<SHA>
- reread <plan/spec/checkpoint refs>
- rerun <smallest validation command needed before editing>
- continue at <exact task/step>
```

Для pause/hand-off checkpoint дополнительно обязательно указать:

- есть ли незакоммиченные изменения;
- какие файлы намеренно modified/generated;
- какой test сейчас RED и почему, если TDD cycle прерван;
- какие команды уже запускались и на каком SHA;
- что **не следует** повторно делать или считать завершённым без проверки.

## 6. Commit/checkpoint discipline

Для безопасного resume:

- по возможности пауза делается на чистом working tree после осмысленного commit;
- если TDD/diagnostic работа прерывается с dirty tree, checkpoint обязан перечислить dirty paths и смысл незакоммиченного состояния;
- checkpoint никогда не заявляет `GREEN` без указания фактически запущенной проверки;
- CI evidence всегда привязывается к exact SHA; новый commit инвалидирует старое exact-head evidence там, где gate зависит от head;
- generated diffs не описываются как случайный шум: checkpoint фиксирует, ожидаемы ли они и из какого deterministic change следуют;
- deviation, который меняет утверждённый architecture/security contract, не маскируется как implementation detail: работа на зависимых шагах останавливается до review/amendment.

## 7. PR0-specific bureaucracy

Для PR0 обязательны checkpoints как минимум:

- Task 1 eligibility extraction GREEN;
- Task 2 audit/digest GREEN;
- clean implementation commit перед baseline generation;
- baseline generation checkpoint с measured `SOURCE_REVISION`, digest и reproducibility result;
- final PR0 gate;
- pre-merge checkpoint с требованием merge commit;
- post-merge checkpoint, подтверждающий `source_revision` как ancestor of `main`.

Living docs должны быть уже актуальны **до** baseline snapshot, чтобы measured source revision соответствовал не только code, но и документации измеряемого contract.

## 8. PR1-specific bureaucracy

Для PR1 обязательны checkpoints как минимум:

- после каждого Tasks 4–8 correctness/observability boundary;
- отдельный checkpoint перед началом Tasks 9–10 с явным переходом в **Trust boundary / privileged auto-merge** review area;
- Task 9 path-policy parity GREEN;
- Task 10 privileged workflow trust-boundary GREEN;
- checkpoint после living docs/AGENTS reconciliation;
- pre-final-verification freeze;
- exact-head Media Dev Check evidence;
- exact-head manually dispatched Web Check evidence;
- whole-branch review result;
- ready-for-review / pre-merge checkpoint.

PR body должен сохранять две независимые review-секции:

- **Intelligence correctness / observability — Tasks 4–8**;
- **Trust boundary / privileged auto-merge — Tasks 9–10**.

## 9. Documentation review at every task boundary

После GREEN каждого Task исполнитель делает короткую documentation-impact проверку:

1. изменился ли observable behavior/contract/invariant/security assumption?;
2. если да — какие living docs/AGENTS/status должны измениться сейчас?;
3. если нет — checkpoint явно пишет `Docs/contracts updated: none required` и краткую причину.

Это предотвращает накопление undocumented drift до конца PR.

## 10. Completion evidence amendment

К Stage A completion evidence добавляются обязательные process requirements:

- PR0 и PR1 имеют актуальный `Development Status` в body;
- task/milestone/deviation/pause/resume/final-verification checkpoints присутствуют в PR history;
- последний checkpoint на каждом PR соответствует exact final head;
- living docs обновлялись вместе с contract-changing tasks, а Task 11 выполнил final reconciliation;
- любой pause/hand-off оставляет однозначные resume instructions;
- merged `main` documentation соответствует фактически доставленному состоянию, а historical specs/plans остаются rationale, а не конкурирующей current authority.

Без этих артефактов Stage A не считается процессно завершённым даже при зелёных product tests.
