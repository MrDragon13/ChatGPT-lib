# Web и Broker

Этот документ описывает границу между статическим Media Web, Cloudflare Broker, GitHub и media-подсистемой.

## Web

`web/` — статический React/Vite-клиент на GitHub Pages.

Он:

- читает версионированный Web manifest;
- показывает библиотеку, историю, сигналы вкуса и рекомендации;
- отправляет разрешённые правки через Broker;
- не читает канонические YAML напрямую;
- не хранит секреты GitHub, провайдера или модели;
- не содержит собственного второго алгоритма рекомендаций.

Пустая библиотека остаётся поддерживаемым UI-состоянием. Home, Library и History должны показывать понятный empty state, а не фиктивные фильмы.

## Broker

Cloudflare Worker — stateless граница для записи из браузера.

Production `POST /v1/feedback` использует `record_media_entry`.

Broker:

1. проверяет сессию владельца;
2. получает точный SHA текущего `main`;
3. читает `media/generated/index.jsonl` на этом же SHA;
4. получает viewer digest нужного `work/target`;
5. строит `record_media_entry(create_if_missing=false)` с `expected_viewer_digests`;
6. создаёт ветку `media/op-*` и request-only PR от того же SHA;
7. возвращает состояние операции.

Браузер viewer digest не получает и не вычисляет.

## Почему Broker не хранит свою базу

Broker не использует D1, KV или Durable Objects как второй источник истины.

Состояние незавершённой операции восстанавливается из PR, workflow, merge и Pages. Так долговременное состояние остаётся в GitHub и не требует отдельной синхронизации.

## Что отправляет браузер

Browser отправляет только понятные пользователю поля, например:

- `work_id`;
- `target`;
- rating;
- reaction;
- текст отзыва.

Внутренние preconditions добавляет Broker.

Если для того же `work/target` уже есть активная операция, второй параллельный request не создаётся. Web сохраняет локальный черновик и разрешает следующую отправку после завершения первой операции и обновления manifest.

## Состояния операции

Основные состояния для пользователя:

- `submitted` / `checking` — запись ещё не стала канонической;
- `merged` — данные уже в `main`, но Pages может ещё обновляться;
- `published` — Pages для merge SHA опубликованы;
- `failed` — операция не стала канонической.

Текущий путь использует единый `Media Command`, operation receipt, merge и Pages. Старый раздельный workflow больше не используется.

## Web manifest

Current manifest version: v4.

Manifest строится только из канонических и производных media-данных.

В нём есть публичные сигналы пользователей/группы, данные для отображения вкуса и рекомендаций, semantics, explicit similarity и публичный reanalysis gate.

Внутренние viewer/evidence digests и служебные данные GitHub-операций не публикуются.

При пустой библиотеке manifest остаётся корректным: `works: []`, а наборы кандидатов рекомендаций пусты.

## Безопасность

- приватный ключ GitHub App и session secret находятся только в Worker;
- `TMDB_READ_TOKEN` используется только в доверенной server/Actions-среде;
- browser bundle получает только публичный URL Broker;
- Broker создаёт типизированный request PR и не правит YAML напрямую;
- `Media Command` проверяет разрешённые пути и точные base/head;
- недоверенные fork PR не получают выполнение с секретами.

## Публикация

`Broker Deploy` запускается вручную и принимает ожидаемый SHA `main`.

`Media Pages` строит Web для точного merge SHA.

Если `MEDIA_BROKER_URL` не задан, Web должен полноценно работать в режиме чтения.
