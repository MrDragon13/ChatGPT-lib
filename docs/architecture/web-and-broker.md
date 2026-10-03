# Web и broker boundaries

Этот документ описывает текущую web surface: статическую GitHub Pages-витрину, versioned manifest и server-side write broker.

Current manifest version: v3

## Static Pages как read surface

`web/` — React/Vite application, публикуемое через GitHub Pages. Оно не читает canonical YAML напрямую и не содержит собственного recommendation/taste engine.

Data flow:

```text
canonical media + derived contexts
        -> media web exporter
        -> versioned JSON manifest
        -> static web build
        -> GitHub Pages
```

Manifest является derived read model. Его можно пересобрать; он не становится вторым source of truth.

## Manifest contract

Current exporter выдаёт schema version 3. Manifest включает, среди прочего:

- configured targets;
- controlled vocabulary projection;
- derived profiles/taste contexts;
- recommendation context;
- work identity/metadata/user signals;
- semantic fingerprint;
- target-keyed explicit similarity projection.

Frontend временно умеет читать несколько предыдущих manifest versions для безопасного staged static deploy overlap, но **current write/export contract** определяется exporter/schema code.

## Similarity projection

Canonical explicit similarity хранится как одна undirected relation. Web read model может развернуть её для удобного чтения:

- canonical↔canonical relation появляется на обеих локальных work pages;
- canonical↔external relation показывается только на локальной canonical page;
- external endpoint отображается как lightweight identity card без выдуманного local route;
- projection фильтруется по active target;
- UI не выдаёт derived semantic similarity за explicit пользовательское мнение.

## Web target semantics

`primary` — default context. Явно выбранные `partner`/`couple` сохраняются через navigation. UI меняет foregrounded subjective signals, но не создаёт отдельные каталоги произведений.

Write destination всегда видим. Web не должен молча сохранять `couple` edit в `primary` или подставлять чужой target как будто это canonical signal выбранного target.

## Broker boundary

Статический browser не может безопасно владеть GitHub write token, provider secret или model credential. Поэтому поддерживаемые lightweight edits отправляются через authenticated broker.

Broker отвечает за:

1. authentication/authorization request;
2. разрешённый набор browser write intents;
3. перевод запроса в existing strict typed operation;
4. передачу mutation в тот же repository/PR pipeline;
5. возврат operation/result status без раскрытия secrets.

Broker не должен создавать параллельную browser-only data model или bypass validation.

## Что browser никогда не получает

В static bundle запрещены:

- GitHub repository write credentials;
- `TMDB_READ_TOKEN` и другие provider secrets;
- OpenAI/model credentials;
- server-side signing/authentication secrets;
- произвольный доступ к repository write API.

Публичность Pages и confidentiality пользовательских movie ratings/comments — отдельный product decision; отсутствие секретов в bundle остаётся обязательным независимо от публичности content.

## Read vs write

Read:

```text
Pages -> exported manifest -> rendered UI
```

Write:

```text
browser -> broker -> typed command -> operation PR -> deterministic validation/merge pipeline
```

Browser никогда не мутирует canonical YAML напрямую.

## Product и visual contracts

Root `PRODUCT.md` — media-web product brief. Root `DESIGN.md` — current media-web visual/design-system contract. Они определяют product/design surface, но не заменяют system architecture или canonical media contracts.

## Deployment

Publishable artifact строится из exact repository revision после media export и web checks. Pages deployment должен соответствовать exact merge SHA, чтобы UI и manifest не расходились с `main`.

Web-related verification включает unit tests, TypeScript typecheck, production build, static credential scan и browser/accessibility/responsive checks, как закреплено текущими workflows.
