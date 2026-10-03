# Media Intelligence v5 — Development Continuity Contract

Дата: 2026-10-03  
Статус: **design amendment approved in chat; awaiting final written review together with v5 spec**  
Дополняет:
- `2026-10-03-media-intelligence-recommendation-v5-design.md`
- `2026-10-03-media-intelligence-v5-web-agent-contract-amendment.md`
- `2026-10-03-media-intelligence-v5-agent-scenario-catalog.md`

## 1. Цель

Разработка v5 будет многоэтапной и может прерываться между чатами, сессиями, агентами или рабочими окружениями. Текущий контекст разработки не должен существовать только в памяти конкретной LLM-сессии.

Каждый implementation PR обязан сам содержать достаточное состояние для безопасного продолжения работы новым агентом или после длительного перерыва.

Главный принцип:

> Открытый implementation PR — это одновременно change set и живой handoff-документ. По нему должно быть понятно, где мы находимся, что уже доказано, что ещё не сделано и какой следующий безопасный шаг.

## 2. Два уровня фиксации состояния

Используется гибридная модель.

### 2.1 PR body — текущий canonical snapshot разработки

В описании implementation PR поддерживается один актуальный блок `Development status`.

Он должен обновляться, а не накапливать устаревшие варианты состояния.

Минимальный шаблон:

```markdown
## Development status

Last updated: <ISO timestamp>
Current head: `<sha>`
Phase: <phase name / number>
State: planned | red | implementing | green | blocked | verifying | ready-for-review

### Completed
- ...

### Verification evidence
- `<command>` → <result>
- workflow/run → <result>

### In progress
- ...

### Blockers / open questions
- none

### Decisions / deviations
- ...

### Next steps
1. ...
2. ...

### Resume from here
- Read: <spec/plan paths>
- Inspect: <important files / current failing test>
- Next safe action: ...
```

Если значение отсутствует, пишется `none`, а не удаляется сам раздел. Это позволяет следующему агенту отличать «проверено, проблем нет» от «никто не зафиксировал состояние».

### 2.2 PR comments — append-only checkpoints

Помимо mutable snapshot, в PR добавляются короткие checkpoint-комментарии после значимых этапов.

Checkpoint фиксирует исторический факт и не редактируется задним числом без необходимости.

Пример:

```markdown
### Checkpoint — Phase B GREEN
Head: `<sha>`

Completed:
- inferred-preferences schema
- deterministic profile aggregation

Verified:
- `python -m pytest ...` → 42 passed
- `python -m media.cli rebuild --check` → ok

Next:
- start compact LLM taste context

Notes:
- no schema deviations
```

Checkpoints нужны не после каждого мелкого commit, а после завершения фазы, достижения RED/GREEN boundary, значимого архитектурного решения, обнаруженного blocker либо перед намеренной остановкой длительной работы.

## 3. Когда статус обязан обновляться

`Development status` в PR body обновляется как минимум:

1. сразу после создания implementation PR;
2. после утверждения implementation plan / перед первым product-code изменением;
3. после получения ожидаемого RED evidence;
4. после существенного implementation milestone;
5. после получения GREEN evidence;
6. при обнаружении blocker или неожиданной архитектурной сложности;
7. при изменении ранее утверждённого плана;
8. перед переходом к следующей фазе;
9. перед намеренной остановкой работы, если задача не завершена;
10. перед переводом PR в ready-for-review;
11. после существенного review feedback и после его закрытия.

Если работа прервалась аварийно и обновить статус заранее было невозможно, первая операция после возобновления — восстановить фактическое состояние branch/CI и привести PR snapshot в соответствие с реальностью до новых product-code изменений.

## 4. Правила возобновления работы

Новый агент или новая сессия перед изменением кода обязаны прочитать в таком порядке:

1. актуальный v5 design/spec;
2. implementation plan текущего PR;
3. текущий `Development status` в PR body;
4. последний checkpoint comment;
5. текущий PR diff / head SHA;
6. актуальный CI/status checks.

После этого агент сверяет заявленный `Current head` с реальным head PR.

Если SHA или CI не совпадают с snapshot, snapshot считается stale. Сначала выполняется reconciliation, затем он обновляется, и только потом продолжается реализация.

Нельзя продолжать работу только из памяти предыдущего чата, если PR содержит более свежий статус.

## 5. Что считается достаточным handoff

После чтения PR без доступа к предыдущему чату должно быть возможно ответить на вопросы:

- Какова цель этого PR и какая часть v5 реализуется?
- Какой spec и implementation plan являются актуальными?
- Какая фаза выполняется сейчас?
- Какие изменения уже находятся в branch?
- Какие тесты/проверки реально запускались и с каким результатом?
- Есть ли известные failing tests, blockers или технический долг?
- Какие решения были приняты относительно первоначального плана?
- Что ещё точно не реализовано?
- Какой следующий безопасный шаг?
- Что необходимо проверить перед merge?

Если на один из этих вопросов невозможно ответить по PR, continuity snapshot считается неполным.

## 6. Evidence discipline

Status не должен содержать недоказанные утверждения вроде `tests pass`, если соответствующая проверка не запускалась на указанном head.

Для verification evidence фиксируются:

- команда или workflow;
- краткий результат;
- при необходимости run ID / ссылка;
- head SHA, к которому относится результат.

После нового code commit старое доказательство не считается доказательством нового head, если изменение могло повлиять на соответствующую проверку.

`planned`, `implemented`, `verified` и `deployed` — разные состояния и не должны подменять друг друга.

## 7. План и scope

Implementation plan хранится versioned в репозитории, а PR body содержит ссылку на него и компактный phase checklist.

Если scope меняется:

1. изменение фиксируется в `Decisions / deviations`;
2. при архитектурно значимом изменении сначала обновляется design/plan;
3. создаётся checkpoint comment с причиной;
4. только затем продолжается реализация нового scope.

Не допускается незаметно превращать implementation PR в другой проект.

## 8. Работа с несколькими implementation PR

v5 может быть разбита на несколько PR. Каждый PR поддерживает собственный continuity snapshot.

Главный implementation plan должен показывать межфазные зависимости и состояние уже merged фаз.

При создании следующего PR его initial status должен ссылаться на:

- предыдущий merged PR;
- merge SHA;
- завершённую фазу;
- новую фазу и её prerequisites.

Так continuation не зависит от порядка чатов или от того, какой агент начал следующую фазу.

## 9. Что не хранить в PR status

Запрещено помещать в body/comments:

- secrets, tokens, credentials;
- приватные provider responses с чувствительными данными;
- большие сырые логи вместо краткого результата и ссылки/run ID;
- скрытый chain-of-thought модели;
- временные предположения, выдаваемые за принятые решения.

Фиксируются решения, наблюдаемые факты, результаты проверок, blockers и следующие действия — не внутренние рассуждения модели.

## 10. Закрытие implementation PR

Перед merge `Development status` должен быть приведён к финальному виду:

```text
State: ready-for-review / verified
Completed: все пункты scope
Verification evidence: свежие финальные проверки
Blockers: none
Next steps: post-merge verification / следующий PR
Resume from here: post-merge checklist
```

После merge рекомендуется финальный checkpoint comment с merge SHA, post-merge verification и ссылкой на следующий PR/phase, если v5 ещё не завершена.

## 11. Обязательность для v5

Этот continuity protocol является частью definition of done для всей реализации Media Intelligence v5.

Implementation plan обязан явно включить задачи:

- создать и поддерживать PR status template;
- обновлять snapshot на phase boundaries;
- оставлять checkpoint comments;
- выполнять reconciliation после возобновления;
- финализировать handoff перед merge/следующей фазой.

Это организационный контракт разработки; он не меняет canonical media data model и не добавляет пользовательские данные в PR metadata.
