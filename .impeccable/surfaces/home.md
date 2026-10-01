# Media Web — home surface brief

## Scope

Primary GitHub Pages route `#/today`. Operate/experience hybrid: the user is here to choose a film quickly, but the choice should feel cinematic rather than administrative.

## Audience and job

Two household viewers (`primary`, `partner`, joint group `couple`). Default context is `couple` when available. The page must make one next-watch option immediately legible, offer a small number of alternatives, and provide a quiet path to the full library.

## Constraints

- Canonical Git/YAML and generated media data remain read-only to the frontend.
- Real repository-derived titles/signals only; no production mock movie arrays.
- All ordinary UI copy is Russian.
- Taste: DESIGN_VARIANCE=7, MOTION_INTENSITY=8, VISUAL_DENSITY=4.
- No blue-purple AI gradients, generic dashboard grids, heavy card chrome, or invented movie artwork.
- Approved comp: `.impeccable/mocks/home-c.svg` with approval metadata in `.impeccable/mocks/home-c.json`.
- The official Impeccable launcher is present only as a plugin resource in this harness and is not mounted as an executable. This surface therefore follows the documented degraded path; no claim is made that `concept-seed`, `build-phase`, or `comp-spec` binaries ran.

## Direction contract

**THESIS** — The first viewport behaves like a private evening screening board: one film owns the room, two alternatives stay within reach, and the full library is one step away. It refuses the category-default wall of equal poster cards and the opposite extreme of a decorative movie poster with no task clarity.

**OWN-WORLD** — Near-black `#080808` canvas, graphite/espresso-neutral surfaces, milk-white `#F3F0E8` typography and a single tungsten `#E0B56C` action/focus accent. Real poster/backdrop imagery supplies almost all additional chroma. Typography is one variable family, Onest Variable (`@fontsource-variable/onest@5.3.1`, Cyrillic + Cyrillic-ext, wght 100–900). Corners are soft but not pill-everything; separators are rare and low-chroma.

**STORY** — The visitor lands on `Сегодня` and immediately sees one candidate with identity, runtime and an explainable reason grounded in stored facts. Two secondary candidates let them change focus without scanning a catalog. Scrolling reveals `Посмотреть следующим`, `Для двоих` when supported, recent personal history when truthful, then the library entry. Detail pages privilege personal viewing/rating/reaction/feedback over TMDB score.

**FIRST VIEWPORT** — At 1440×900 a compact floating navigation sits in the top band. A single rounded hero field spans almost the whole width from roughly y=110 to y=610; title and metadata occupy the left two-thirds, the real backdrop fills the field, and a narrow poster plate sits on the right. Below, two low-profile alternative cards occupy the left/middle and a quiet `Открыть всю медиатеку` card anchors the right. The primary action is `Подробнее`. No second element competes with the hero title scale.

**FORM** — Chosen form: `Вечерний сеанс`, approved comp `.impeccable/mocks/home-c.svg`. Official seed key is unavailable because the launcher is not executable in this harness; internal degraded reference `media-home-evening-screening-v1` is used only to correlate review artifacts. Signature interaction: keyboard focus/hover on a secondary candidate crossfades hero imagery and metadata like changing a projector frame; no autoplay or scroll hijacking. The user explicitly delegated the best-direction choice and later approved the written visual design, so this selection is treated as delegated approval.

**FINISH** — unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Typography roles

- Hero title: 700–780 weight, large but responsive only where the approved composition requires; no display serif.
- Section title: 620–700.
- Body/action: 450–650, ordinary floor 16px.
- Metadata: 14–16px, secondary color no darker than the AA-safe muted floor on canvas.
- Long synopsis measure: 45–75ch.

## Color strategy

Restrained dark system with one committed tungsten action/focus role. Poster/backdrop images own color; neutral UI does not tint itself toward their palette. Text and controls meet WCAG AA; the earliest comp value `#77736D` is explicitly rejected for body metadata on `#080808` because it falls below 4.5:1.

## Responsive translation

At ~390px the hero becomes a vertical movie-poster-like composition with backdrop at the top and content in the lower scrim; the separate poster plate may disappear when redundant. Alternatives remain horizontal touch-scroll or stack when needed. Library is two poster columns when width allows, one when it does not. Desktop overlaps/offsets do not survive by shrinking mechanically.
