# Cross-system invariants

Короткий список правил, которые должны оставаться истинными независимо от конкретной feature/version. Подробности живут в schemas, code, `media/AGENTS.md` и тематических architecture docs.

## Data ownership

1. **Git/YAML canonical.** Canonical media facts/user-owned state живут в утверждённых repository paths и schemas.
2. **Generated data rebuildable.** `generated` artifacts не редактируются вручную как источник новых фактов или preference.
3. **No browser-only truth.** Web manifest/UI state не становится параллельным canonical store.

## Writes

4. **Normal mutations use a typed command.** LLM/CLI/web не применяют произвольный YAML patch вместо существующего operation contract.
5. **Unknown is better than guessed.** Ambiguous identity/provider result останавливает mutation или требует input; система не угадывает work.
6. **Operation scope stays narrow.** Auto-merge-eligible operation не получает скрытый доступ к architecture/schema/vocabulary/workflow paths.
7. **Read-only stays read-only.** `recommend_context`, `taste_context` и `assess_candidate` не мутируют canonical state.

## Targets

8. **Target никогда не меняется молча.** `primary`, `partner` и `couple` — разные destinations/contexts.
9. **Couple is a group context, not an averaged person.** Disagreement показывается явно; conflicting evidence не усредняется без объяснения.
10. **Absence is not substitution.** Нет partner/couple signal — значит signal отсутствует; нельзя незаметно копировать другой target.

## Evidence and intelligence

11. **Explicit evidence outranks inferred output.** Inferred hypothesis не является independent evidence для другой inferred hypothesis.
12. **One rating is not a full taste model.** Нельзя автоматически превращать все traits одного высоко/низко оценённого work в сильную stable preference.
13. **Semantic fingerprint describes the work.** Он не кодирует viewer reaction.
14. **Similarity is evidence/hint, not preference.** Одна связь «A похож на B» не создаёт affinity/stable preference сама по себе.
15. **Assessment is qualitative.** Candidate assessment не сохраняет prediction и не изображает fake precise probability/opaque score как знание пользователя.

## External identity

16. **External mention does not create a canonical work.** Recommendation, candidate assessment или similarity endpoint может ссылаться на внешний work без добавления его в library.
17. **Persistent external reference requires stable identity.** Для долговременной relation нужен устойчивый provider ID; title/year — display snapshot, не единственный ключ.
18. **Reconciliation is deterministic.** Когда external identity становится canonical work, relation normalization не должна создавать duplicate/self-link или user signals побочно.

## Vocabulary and schemas

19. **Unknown vocabulary terms are not invented.** Если подходящего controlled vocabulary term нет, normal data entry не создаёт новый term/synonym скрыто.
20. **Normal data entry cannot change schema.** Schema/vocabulary evolution — manual developer/architecture work с tests/migration policy.
21. **No invented fields.** Writer использует только fields, разрешённые текущим schema contract.

## Security

22. **Browser never receives write/provider/model secrets.** GitHub write token, provider credentials и model secrets остаются server/CI side.
23. **Broker reuses typed validation.** Browser write boundary не обходит command schemas, target safety или canonical validation.
24. **Static Pages remains safe without live model.** Core read surface не зависит от client-side model credentials.

## Verification

25. **Exact revision matters.** GREEN должен относиться к exact head/merge SHA, который проверяется или публикуется.
26. **Full validation before completion.** Focused tests недостаточны для финального success claim; выполняется project regression/validate/rebuild/doctor и релевантные web gates.
27. **Historical spec is rationale, not current authority.** Dated plan/spec не переопределяет реализованный code/schema/operating contract после merge.
