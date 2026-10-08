# Web and Broker architecture

Этот документ описывает текущую границу между static Web, Cloudflare Broker, GitHub и media domain.

## Роли

### Web

`web/` — статический React/Vite клиент GitHub Pages.

Он:

- читает versioned derived manifest;
- показывает library/history/taste/recommendation data;
- может отправлять разрешённый feedback через Broker;
- не читает canonical YAML напрямую;
- не хранит GitHub/provider/model secrets;
- не является вторым recommendation engine или canonical store.

Пустая медиатека после v6 reset — нормальный UI state. Home/Library/History должны быть полезными и доступными без фиктивных works.

### Broker

Cloudflare Worker — stateless защищённая граница browser write.

Production `POST /v1/feedback` использует v6 `record_media_entry`.

Broker:

1. проверяет owner session;
2. получает exact SHA текущего `main`;
3. читает `media/generated/index.jsonl` на этом же SHA;
4. извлекает viewer digest нужного `work/target`;
5. строит `record_media_entry(create_if_missing=false)` с `expected_viewer_digests`;
6. создаёт `media/op-*` branch и request-only PR от того же SHA;
7. возвращает operation status.

Browser не получает и не вычисляет viewer digest.

## Почему Broker не хранит состояние

Broker не использует D1/KV/Durable Objects как source of truth.

Pending status восстанавливается из GitHub operation PR/workflow/merge/Pages state. Это сохраняет один долговременный источник данных и не создаёт отдельную синхронизацию.

## Browser feedback contract

Browser отправляет только human-facing поля, например:

- `work_id`;
- `target`;
- rating;
- reaction;
- feedback summary.

Internal preconditions добавляет Broker.

Если по тому же work/target уже есть активная operation, Broker/Web не создают второй параллельный request. Web сохраняет следующий local draft и разрешает submit после authoritative первой операции и refresh manifest.

## Status lifecycle

Основные user-facing состояния:

- `submitted` / `checking` — операция ещё не authoritative;
- `merged` — canonical data уже в `main`, Pages ещё может обновляться;
- `published` — Pages для merge SHA завершены;
- `failed` — operation не стала authoritative.

Status lifecycle опирается на единый v6 `Media Command`, operation receipt, merge и Pages state; старый split-workflow handoff не используется.

## Web manifest

Current manifest version: v4.

Manifest строится только из canonical/derived media data.

Он включает публичные viewer/group signals, taste/recommendation read models, semantics, explicit similarity и публичный reanalysis gate. Внутренние viewer/evidence digests и GitHub operation bookkeeping не публикуются.

Пустая библиотека экспортируется как валидный manifest с `works: []` и пустыми recommendation candidate sets.

## Security boundaries

- GitHub App private key и session secret живут только в Worker.
- `TMDB_READ_TOKEN` живёт только в trusted server/Actions context.
- Browser bundle содержит только public Broker URL.
- Broker создаёт только typed request PR и не патчит canonical YAML напрямую.
- Media Command применяет operation path policy и exact-head/base guard.
- Fork/untrusted PR не получает secret-bearing normal data execution.

## Deploy

Broker Deploy остаётся manual и SHA-gated.

Media Pages строит Web для exact merge SHA.

Если `MEDIA_BROKER_URL` отсутствует, Web должен сохранять read-only функциональность.
