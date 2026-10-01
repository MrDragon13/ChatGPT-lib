# ChatGPT-lib

Личная библиотека структурированных данных и профилей, собранных в диалогах с ChatGPT.

## Разделы

### 🎬 Media

- [Personal Media Library v4](media/README.md) — фильмы, сериалы, анимация, multi-viewer сигналы, рекомендации, typed tooling и GitHub-native write flow.
- `web/` — кинематографичная русскоязычная GitHub Pages-витрина поверх той же медиатеки. Она получает deterministic read-only manifest из canonical/derived media layer и не является вторым источником истины.

Основной путь пополнения медиатеки остаётся разговором с LLM. Веб-интерфейс v1 предназначен для просмотра, выбора фильма, поиска и чтения сохранённых впечатлений; будущие быстрые правки должны отправляться через защищённый typed-command broker, а не менять YAML из браузера.

## Архитектурные документы

- `docs/superpowers/specs/2026-10-01-personal-media-recommendation-v4-design.md`
- `docs/superpowers/plans/2026-10-01-personal-media-recommendation-v4.md`
- `docs/superpowers/specs/2026-10-01-media-tooling-orchestration-design.md`
- `docs/superpowers/plans/2026-10-01-media-tooling-orchestration.md`
- `docs/superpowers/specs/2026-10-01-media-web-experience-design.md`
- `docs/superpowers/plans/2026-10-01-media-web-experience.md`
