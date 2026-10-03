# Media Web

`web/` — статическая React/Vite поверхность персональной медиатеки, публикуемая через GitHub Pages. Она читает versioned derived manifest и не является вторым source of truth.

## Где лежат актуальные контракты

- [Web and broker architecture](../docs/architecture/web-and-broker.md) — manifest, broker и security boundaries.
- [System architecture](../docs/architecture/overview.md) — место web в общей системе.
- [Operations runbook](../docs/guides/operations.md) — verification/build/deploy.
- [`PRODUCT.md`](../PRODUCT.md) — media-web product brief.
- [`DESIGN.md`](../DESIGN.md) — visual/design-system contract.

Canonical media state живёт под `media/`; frontend не читает и не мутирует canonical YAML напрямую. Поддерживаемые edits идут через protected broker и существующий typed-command pipeline.

## Локальная проверка

```bash
npm ci
npm run test:run
npm run typecheck
npm run build
npm run scan:dist
```

Browser/accessibility/responsive checks запускаются текущим `Web Check` workflow. Browser bundle не должен содержать GitHub write credentials, provider tokens или model secrets.
