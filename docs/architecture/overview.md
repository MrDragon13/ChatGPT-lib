# Архитектура ChatGPT-lib

Этот документ описывает **текущее** устройство проекта. Historical design decisions находятся в `docs/superpowers/`, но для понимания работающей системы читать dated specs не требуется.

## Система в целом

ChatGPT-lib — Git-native personal media intelligence system. Канонические пользовательские данные и долгоживущие выводы хранятся в репозитории; Python-слой применяет строгие операции, строит derived read models и экспортирует данные для статического web-интерфейса.

```text
user / LLM / CLI / web edit
          |
          v
strict typed operation
          |
          v
media domain + service + repository
          |
          +--> canonical Git/YAML
          |
          +--> derived index / profiles / taste context / web manifest
                                              |
                                              v
                                      static GitHub Pages

web write -> authenticated broker -> same typed operation boundary
```

## Основные компоненты

### Canonical media layer

`media/` содержит source of truth для библиотеки. Canonical данные включают works, collections, lists, recommendation interactions, explicit similarity relations, explicit/inferred preferences, target configuration и controlled vocabulary.

Generated artifacts не являются вторым источником истины: их можно пересобрать из canonical state.

Подробнее: [media model](media-model.md).

### Domain / service / repository

Python-код под `media/domain/`, `media/service/` и `media/repository/` разделяет:

- типы и domain contracts;
- deterministic application typed commands;
- read-only context building;
- provider resolution/enrichment;
- canonical persistence;
- derived export/rebuild.

Обычный LLM или browser request не пишет YAML произвольно. Сначала выбирается typed operation, затем deterministic код применяет mutation или строит read-only response.

### Intelligence layer

Taste reasoning опирается на explicit user evidence, evidence-backed inferred hypotheses, semantic fingerprint произведений, representative works, recommendation interactions и explicit work similarity. Recommendation engine не сводит вкус к одному opaque score и сохраняет provenance объяснений.

Подробнее: [intelligence](intelligence.md).

### Write pipeline и GitHub Actions

Normal media mutations проходят через operation PR, deterministic transaction, validation/rebuild, exact-head verification и guarded merge. Architecture/schema/vocabulary/workflow changes используют manual developer route.

GitHub Actions исполняет deterministic проверки и публикацию; LLM не запускается внутри media pipeline.

Подробнее: [write pipeline](write-pipeline.md).

### Web

`web/` — статическая React/Vite GitHub Pages поверхность. Она читает versioned **web manifest**, экспортированный из media layer, а не canonical YAML напрямую.

Frontend отвечает за presentation и lightweight interaction UX, но не имеет собственного recommendation engine и не становится source of truth.

### Broker

Browser write не получает GitHub write credentials, TMDB/provider tokens или model secrets. Поддерживаемые изменения отправляются через authenticated **broker**, который переводит разрешённый request в тот же typed-command flow, что используется другими клиентами.

Подробнее: [web and broker](web-and-broker.md).

## Canonical и derived

**Canonical** — данные, которые должны пережить rebuild и являются долговременной памятью проекта.

**Derived** — представления, которые детерминированно строятся поверх canonical данных: retrieval index, taste profiles/context, SQLite runtime database, recommendation context и web manifest.

Практическое правило: generated/derived data не правится вручную как способ изменить смысл системы.

## Targets

Система различает `primary`, `partner` и `couple`:

- `primary` и `partner` — отдельные viewer contexts;
- `couple` — group target для совместного reasoning, а не «третий человек»;
- субъективные сигналы и explicit similarity не копируются между targets автоматически;
- disagreement в couple-контексте показывается явно, а не скрывается средним значением.

## Read и write boundaries

Read-only операции (`recommend_context`, `taste_context`, `assess_candidate`) не должны мутировать canonical state.

Normal writes используют strict typed commands. Изменения schemas, vocabulary, architecture, workflows и maintenance-policy не маскируются под обычную data-entry операцию.

## Security boundaries

- canonical write credentials не попадают в browser bundle;
- provider/model secrets не публикуются в Pages;
- web manifest содержит только данные, допустимые для статической read surface;
- broker ограничивает поддерживаемые write intents;
- GitHub Actions media pipeline остаётся deterministic и не зависит от live LLM.

## Куда читать дальше

- [Media model](media-model.md)
- [Intelligence](intelligence.md)
- [Write pipeline](write-pipeline.md)
- [Web and broker](web-and-broker.md)
- [Repository layout](../reference/repository-layout.md)
- [Cross-system invariants](../reference/invariants.md)
