# Terminology

Стабильные определения, используемые в living docs, code review и agent reasoning.

## Canonical

Долговременные данные/контракты, которые являются source of truth и не восстанавливаются из другого derived представления. Для media это в первую очередь утверждённые YAML/config/preferences/relations и schemas/vocabulary contracts.

## Derived

Детерминированно строящееся представление canonical state: index, profile, taste context, SQLite runtime DB, web manifest и другие read models. Derived artifact можно пересобрать и нельзя использовать как обходной путь для mutation canonical meaning.

## Work

Canonical произведение в media library с устойчивым локальным ID, identity, metadata, signals/provenance и optional semantic fingerprint.

## WorkRef

Ссылка на произведение, которая может быть canonical (`work_id`) или external stable provider identity. Используется там, где operation должна говорить о work, не обязательно уже добавленном в library.

## Target

Контекст субъективных данных/reasoning. Основные: `primary`, `partner`, `couple`. Target определяет, чьи signals/preference/similarity рассматриваются или куда записывается mutation.

## Viewer signal

Raw/explicit user-owned signal о просмотре/реакции: viewing, rating, reaction, feedback и связанные поля.

## Explicit preference

Устойчивое предпочтение/ограничение, которое пользователь заявил напрямую и которое подходит для long-term memory.

## Inferred hypothesis

Evidence-backed вывод о taste, построенный из независимых raw/explicit signals. Не является independent evidence для самого себя или другого вывода.

## Semantic fingerprint

Controlled-vocabulary описание самого произведения: narrative/story/tonal/experience traits и provenance/confidence. Не является оценкой пользователя.

## Evidence

Конкретное основание для reasoning: explicit preference, viewer feedback, repeated independent correlation, representative work, interaction или explicit similarity. Provenance должен позволять отличить user-stated signal от inferred conclusion.

## Taste context

Compact read model для recommendation/assessment reasoning: explicit/inferred taste, representative works, recent feedback, exclusions, affinities, similarity evidence и group disagreement.

## Recommendation context

Read model, соединяющий target taste/context с candidate set/constraints для explainable recommendation reasoning.

## Candidate assessment

Read-only оценка конкретного candidate через `assess_candidate`: qualitative verdict/confidence, supports, risks и evidence. Assessment не сохраняет prediction как taste fact.

## Explicit similarity

Target-specific undirected пользовательское утверждение «work A похож на work B». Хранится отдельно от factual sequel/prequel/remake relations. Может быть recommendation evidence/hint, но не preference сама по себе.

## Derived similarity

Сходство, вычисленное из semantic fingerprints/model reasoning. Не становится canonical explicit similarity без подтверждения пользователя.

## Reconciliation

Deterministic normalization persisted external identity к canonical work, когда тот позже появляется в library. Reconciliation обновляет references/deduplicates relation state, но не создаёт viewer signals.

## Typed operation

Strict JSON request, соответствующий schema и deterministic handler/read builder. Write operations применяют mutations через controlled pipeline; read-only operations возвращают context без canonical write.

## Normal data operation

Обычная user/data mutation, которая может быть eligible для guarded auto-merge при строгом path policy и exact-head GREEN.

## Maintenance operation

Операция обслуживания данных/provider metadata с более широким scope и manual review policy, например `refresh_metadata`.

## Manual developer route

Процесс изменения code/schema/vocabulary/architecture/workflows/tests/docs, который не притворяется normal data operation и не наследует её auto-merge privileges.

## Broker

Authenticated server-side boundary для разрешённых browser writes. Broker скрывает credentials и переиспользует typed operation/validation pipeline.

## Web manifest

Versioned derived JSON read model для static web surface. Manifest не является canonical store.

## Living docs

Актуальная документация текущего поведения/usage/operations/reference. Должна обновляться вместе с изменением реализованного contract.

## Historical rationale

Dated specs/plans под `docs/superpowers/`, сохраняющие контекст проектных решений. После реализации не заменяют living docs/code/schema/AGENTS как current authority.

## Durable status

Короткое описание текущих capabilities/known limitations, которое переживает завершение конкретного PR. Не содержит task ledger, transient branch SHA или run history.
