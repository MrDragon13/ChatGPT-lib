# Разработка ChatGPT-lib

Этот guide описывает developer workflow для code/schema/architecture/docs changes. Для обычной пользовательской media mutation применяйте typed-operation route из `media/AGENTS.md`, а не этот manual process.

## 1. Начинайте с current main

Перед изменением:

1. проверьте актуальный `main`;
2. проверьте открытые PR/active work по затрагиваемой области;
3. прочитайте root `AGENTS.md`, затем subsystem contract `media/AGENTS.md` для media work;
4. загрузите только релевантные living docs/schema/code.

Historical specs полезны для rationale, но не заменяют current code/contracts.

## 2. Сначала выберите route

### Normal typed operation

Используйте, когда пользователь меняет обычные media data в рамках уже существующего contract: viewing feedback, interest, semantic/inferred state, interactions, explicit similarity и т. п.

Такая операция должна идти через strict command schema и существующий operation PR pipeline.

### Manual developer route

Используйте для:

- domain/service/repository code;
- schemas;
- controlled vocabulary;
- architecture semantics;
- workflow/path policy;
- broker/security behavior;
- documentation architecture;
- maintenance behavior;
- tests.

Не расширяйте normal auto-merge path ради developer change.

## 3. TDD

Для behavior/code changes:

1. напишите failing test;
2. подтвердите RED по правильной причине;
3. внесите минимальное изменение;
4. подтвердите GREEN;
5. выполните полный regression suite.

Для docs architecture используйте executable docs contracts там, где drift можно проверить структурно: registry/version/link/path synchronization. Не тестируйте exact prose без необходимости.

## 4. Schema и vocabulary evolution

Schema/vocabulary change — отдельный developer task. Обычная data-entry операция не должна:

- добавлять новое schema field;
- менять enum/required rules;
- создавать новый vocabulary term/synonym;
- ослаблять validation.

Сначала изменяется contract + tests + migration/compatibility policy, затем data flow.

## 5. Verification baseline

Минимальный media gate:

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
```

Для web-impacting change дополнительно выполняются web unit/type/build/browser/static scans согласно текущим workflows.

## 6. PR discipline

Для существенной работы используйте отдельную ветку/PR. В активном PR храните короткий progress ledger:

- что завершено;
- exact head SHA для подтверждённого checkpoint;
- какой gate прошёл;
- следующий незавершённый task;
- rulings по неожиданным развилкам.

Transient checkpoint не переносится в `docs/status/current.md` после merge. Durable status содержит только текущее реализованное состояние и ограничения.

## 7. Documentation ownership

При изменении поведения обновляется документ, который владеет соответствующим контрактом:

| Изменение | Living docs |
| --- | --- |
| typed operation | `docs/reference/media-commands.md`; semantic impact → relevant architecture doc |
| schema/domain invariant | `docs/architecture/media-model.md` и/или `docs/reference/invariants.md` |
| recommendation/taste/assessment | `docs/architecture/intelligence.md`; user behavior → `docs/guides/media-usage.md` |
| write/CI/auto-merge | `docs/architecture/write-pipeline.md`, `docs/guides/operations.md` |
| manifest/broker/security | `docs/architecture/web-and-broker.md`; product impact → `PRODUCT.md` |
| repository layout | `docs/reference/repository-layout.md` |
| visual web rule | `DESIGN.md` |
| durable capability/limitation | `docs/status/current.md` |
| architectural rationale | dated `docs/superpowers/specs/...` + living docs after implementation |

Missing required docs update — regression, а не optional polish.

## 8. Review checklist

Перед ready-for-review проверьте:

- change соответствует выбранному route;
- test наблюдался RED → GREEN;
- canonical/generated boundary не нарушен;
- target semantics не изменились молча;
- security/credential boundary не расширился;
- living docs соответствуют code/schema/workflow truth;
- historical specs не переписаны как будто они current state;
- active PR содержит checkpoint, достаточный для безопасного resume.
