# Media operation transport

`.media/requests/*.json` — временные typed requests для обычных media mutations. Они не являются canonical media data и удаляются после применения операции.

`.media/operations/*.json` — технические receipts для idempotency/audit. После v6 reset старые receipts удалены; новые появляются только для новых операций.

Обычный auto-merge write использует один `Media Command` runner:

```text
request-only media/op-* PR
→ очередь media-data-pipeline
→ replay request на свежий main
→ deterministic transaction
→ operation-specific path policy
→ минимальная пересборка
→ targeted authoritative tests
→ exact-head/base guard
→ merge
→ Media Pages для merge SHA
```

Отдельных `Media Check` и `Media Auto Merge` больше нет.

`refresh_metadata` остаётся manual-review операцией: workflow может проверить и обновить её ветку, но не сливает её автоматически.

GitHub Actions не выполняет model inference. `TMDB_READ_TOKEN` доступен только provider-dependent шагу: например, созданию нового work или metadata refresh. Обычный feedback по существующему work выполняется без provider secret.

Fork PR отклоняется до secret-bearing шагов. Request PR до исполнения должен содержать ровно один `.media/requests/<operation-id>.json` и никакого заранее подготовленного canonical/generated diff.
