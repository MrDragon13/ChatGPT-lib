# Служебный transport media-операций

Каталог `.media/` хранит служебные файлы пути записи. Это не пользовательская медиатека и не второй источник истины.

## Requests

`.media/requests/*.json` — временные типизированные запросы обычных media-операций.

До выполнения request-only PR должен содержать ровно один файл:

```text
.media/requests/<operation-id>.json
```

Заранее подготовленных изменений канонических YAML или `generated/` в таком PR быть не должно.

## Operation receipts

`.media/operations/*.json` — технические receipts для idempotency и аудита.

После v6 reset старые receipts были удалены. Новые появляются только после новых операций.

## Обычный путь записи

Все auto-merge операции используют единый `Media Command` runner:

```text
request-only media/op-* PR
→ очередь media-data-pipeline
→ replay запроса на свежем main
→ deterministic transaction
→ operation-specific path policy
→ минимальная пересборка
→ целевые проверки операции
→ exact head/base guard
→ merge
→ Media Pages для merge SHA
```

Старый раздельный validation/merge path удалён.

`refresh_metadata` остаётся manual-review операцией: workflow может подготовить и проверить изменения в ветке, но не сливает их автоматически.

## Секреты и внешние данные

GitHub Actions не запускает model inference.

`TMDB_READ_TOKEN` доступен только тем шагам, которым действительно нужен провайдер: например, созданию нового произведения или обновлению metadata. Обычный отзыв о существующем произведении выполняется без provider secret.

Fork PR отсекаются до шагов, которые используют секреты.
