# Personal Media Recommendation Data Model v3 — superseded

Дата: 2026-10-01  
Статус: **superseded by v4**

Эта спецификация заменена более полной multi-viewer архитектурой v4:

`docs/superpowers/specs/2026-10-01-personal-media-recommendation-v4-design.md`

Причины перехода на v4:

- один файл на произведение вместо одного большого списка;
- multi-viewer (`primary`, `partner`) и group target (`couple`);
- individual/group signals и необязательные season-level signals;
- immutable IDs + tombstones/redirects;
- external metadata + persistent manual overrides + semantic provenance;
- interaction log и пользовательские lists;
- generated index/SQLite/derived profiles;
- единый write protocol для LLM и будущего сайта.

Полная история v3 остаётся доступна в Git history; этот файл намеренно не является действующей спецификацией.
