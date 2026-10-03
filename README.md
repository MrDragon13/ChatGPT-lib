# ChatGPT-lib

Личная библиотека структурированных данных и профилей, собранных в диалогах с ChatGPT.

## Разделы

### 🎬 Media

- [Personal Media Library v5](media/README.md) — фильмы, сериалы, анимация, multi-viewer сигналы, semantic fingerprints, taste profiles, external/internal recommendations, typed tooling и GitHub-native write flow.
- `web/` — русскоязычная GitHub Pages-витрина поверх той же медиатеки. Она получает deterministic read-only manifest из canonical/derived media layer, показывает v5 intelligence context и не является вторым источником истины.

Основной путь пополнения медиатеки остаётся разговором с LLM. Веб-интерфейс умеет отправлять поддерживаемые правки через защищённый typed-command broker; браузер не меняет YAML напрямую и не получает GitHub write credentials, provider tokens или LLM secrets.

Для нового агента точка входа — [`AGENTS.md`](AGENTS.md). Для обычного киноассистента — [`media/START_PROMPT.md`](media/START_PROMPT.md).

## Актуальная архитектура v5

- `docs/superpowers/specs/2026-10-03-media-intelligence-recommendation-v5-design.md`
- `docs/superpowers/specs/2026-10-03-media-intelligence-v5-web-agent-contract-amendment.md`
- `docs/superpowers/specs/2026-10-03-media-v5-agent-scenario-catalog.md`
- `docs/superpowers/specs/2026-10-03-media-intelligence-v5-development-continuity-contract.md`
- `media/V5_STATUS.md` — текущий handoff/status после завершения v5 pilot.

## Исторические архитектурные документы

- `docs/superpowers/specs/2026-10-01-personal-media-recommendation-v4-design.md`
- `docs/superpowers/plans/2026-10-01-personal-media-recommendation-v4.md`
- `docs/superpowers/specs/2026-10-01-media-tooling-orchestration-design.md`
- `docs/superpowers/plans/2026-10-01-media-tooling-orchestration.md`
- `docs/superpowers/specs/2026-10-01-media-web-experience-design.md`
- `docs/superpowers/plans/2026-10-01-media-web-experience.md`
