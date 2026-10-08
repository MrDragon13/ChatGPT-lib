# Media invariants

Короткий список обязательных правил, которые должны одинаково соблюдаться domain code, CLI, GitHub Actions, Broker, Web и agent.

1. **Canonical wins.** Git/YAML в `main` — единственная долговременная истина media state.
2. **Generated is rebuildable.** Index, profiles, manifest и временный SQLite не становятся canonical user data.
3. **Typed command boundary.** Обычная mutation проходит через зарегистрированную typed operation; free-form YAML patch не является normal user route.
4. **Target is explicit.** `primary`, `partner` и `couple` не смешиваются молча.
5. **Unknown beats guessed.** Неизвестная identity/metadata/vocabulary остаётся неизвестной до надёжной проверки.
6. **Explicit beats inferred.** Свежий explicit user evidence важнее inferred interpretation.
7. **Inference does not self-prove.** Inferred output не становится independent evidence для следующего inferred output.
8. **Work semantics are not sentiment.** Rating/reaction/feedback зрителя не являются factual work traits.
9. **Vocabulary is controlled.** Неизвестный semantic term не добавляется скрыто обычной data operation.
10. **Similarity is not preference.** Explicit similarity — evidence/hint, но не стабильная taste preference сама по себе.
11. **External is not canonical.** External recommendation/candidate/similarity endpoint не создаёт canonical work без явного create flow.
12. **Read-only stays read-only.** `media_entry_context`, `recommend_context`, `taste_context`, `assess_candidate` не мутируют canonical state.
13. **One human event, one normal write.** Связанные сигналы одного work по возможности записываются одной `record_media_entry`.
14. **Existing feedback has zero provider I/O.** Обычный existing-work `record_media_entry` не требует provider, metadata refresh или semantic recomputation.
15. **New work is atomic and provider-owned.** Stable provider identity, trusted provider metadata, semantic traits и viewer evidence нового work применяются одной transaction; технические semantic digests вычисляет runtime.
16. **Viewer digest is target-scoped.** Изменение metadata, semantics или другого target не должно менять digest текущего viewer.
17. **No-change is real success.** `no_change` не создаёт fake history/evidence и не запускает ненужную пересборку.
18. **Idempotency is human-event scoped.** Тот же `idempotency_key` + тот же intent не дублирует запись; другой intent с тем же key fail closed.
19. **Material evidence is bounded.** Один содержательный пользовательский эпизод даёт максимум одно новое taste event.
20. **Summary text alone is not taste evidence.** Косметическая правка `feedback.summary` без structured explicit signal не продвигает reanalysis checkpoint.
21. **Taste checkpoint is digest-based.** Outstanding evidence вычисляется относительно prefix/checkpoint, а не самостоятельного mutable counter.
22. **Threshold gate precedes taste-dependent answer.** При достигнутом threshold fresh reanalysis выполняется до recommendation/comparison/assessment.
23. **Couple has no third automatic counter.** Couple decision проверяет member statuses `primary`/`partner`.
24. **Pending is not saved.** Session-local overlay можно использовать сразу, но authoritative claim допустим только после `main`.
25. **Same-work pending does not fan out.** Второе уточнение того же work не создаёт параллельный request PR до завершения первого.
26. **Request PR is request-only.** До исполнения normal operation PR содержит ровно один `.media/requests/<id>.json`.
27. **Path policy is narrow.** Normal data operation не получает права менять schemas, vocabulary, workflows или architecture.
28. **Auto-merge uses one v6 runner.** Все `auto_merge=true` operations используют `v6_single_runner`; старый раздельный validation/merge path не является текущим путём.
29. **Main is rechecked before merge.** GitHub Actions queue не заменяет exact base/head guard.
30. **Manual maintenance stays manual.** Bulk `refresh_metadata` не auto-merge.
31. **Each dirty output rebuilds at most once per transaction.** Derived work следует dependency plan, а не числу внутренних mutations.
32. **Provider failure does not block existing human evidence.** Stale optional metadata не мешает existing-work feedback.
33. **Archive is historical only.** Pre-v6 MD archive не является canonical, taste input или machine restore source.
34. **Empty library is valid.** Validate/rebuild/doctor/Web/read contexts обязаны работать при `works=0`.
35. **Global explicit preferences survive reset.** Reset не удаляет explicit rules/preferences или vocabulary.
36. **Old inferred state does not survive reset.** Inferred preferences старой библиотеки не восстанавливаются автоматически.
37. **Browser has no secrets.** GitHub/provider/model credentials не попадают в static bundle.
38. **Broker uses the same domain semantics.** Browser feedback преобразуется в `record_media_entry`, а не в отдельную бизнес-логику.
39. **Public manifest hides internal concurrency data.** Viewer digests и internal operation bookkeeping не публикуются в Web manifest.
40. **Qualitative assessment stays qualitative.** Никаких fake precise probability или opaque match score.
41. **Limitations are material.** Active limitations учитываются в reasoning и не скрываются ложной уверенностью.
42. **Full validation before developer completion.** Focused tests недостаточны для финального success claim developer PR.
43. **Historical specs are rationale, not authority.** Dated v5/v5.1 specs не переопределяют current code, schemas, `AGENTS.md` или living docs.
44. **Post-cutover rollback protects new evidence.** До появления новых v6 user writes cutover можно revert; после появления нового evidence blind revert запрещён — нужна forward migration.
