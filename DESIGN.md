---
product: media-web
status: implemented
platform: web
font: Onest Variable
canvas: "#080808"
text: "#F3F0E8"
muted: "#BDB7AB"
accent: "#E0B56C"
design_variance: 7
motion_intensity: 8
visual_density: 4
---

# Media Web Design System

## Overview

Media Web is a private-household cinematic film surface, built as an **evening screening board + personal film journal** rather than a generic catalog or dashboard. The frontend renders repository-derived data and sends lightweight feedback edits only through the protected typed-command broker. Personal ratings, reactions and comments visually outrank public provider metrics.

The library is **personal-first**: `Я / primary` is the default context and represents the owner's library. `Партнёр` and `Вместе` are additional household contexts over the same film library, not separate or equally primary libraries.

The north-star composition is `.impeccable/mocks/home-c.svg` (“Вечерний сеанс”). The interface uses real poster/backdrop imagery as its primary color source and a restrained neutral UI around it.

Taste configuration is fixed at **DESIGN_VARIANCE 7 / MOTION_INTENSITY 8 / VISUAL_DENSITY 4**.

## Colors

Core roles:

| Token | Value | Role |
| --- | --- | --- |
| `--color-canvas` | `#080808` | page/background canvas |
| `--color-surface` | `#111111` | primary raised/contained surface |
| `--color-surface-soft` | `#191919` | quiet secondary surface / artwork fallback |
| `--color-text` | `#F3F0E8` | primary text |
| `--color-text-muted` | `#BDB7AB` | secondary metadata, AA-safe on canvas |
| `--color-accent` | `#E0B56C` | tungsten action, active and focus role |

Rules:
- Use **one accent only**. Do not introduce blue/purple AI glows or unrelated status colors.
- Let TMDB imagery provide most page chroma; neutral UI must not tint itself to each poster.
- Text overlays on backdrops require a dark scrim; do not rely on image darkness.
- Provider/public metrics stay quieter than household signals.

## Typography

Brand/UI family: **Onest Variable**, self-hosted via `@fontsource-variable/onest`, with Cyrillic/Cyrillic-ext support and system sans fallback.

Roles:
- Hero/detail titles: large responsive Onest, roughly 610–700 weight, tight tracking, compact line-height.
- Section titles: 590–700 weight.
- Body/actions: 450–650, ordinary readable floor around 16px.
- Metadata: 14–16px using `--color-text-muted` or stronger.
- Long synopsis measure: keep near 45–75ch.

Do not use Inter, Roboto, Arial, Open Sans or Helvetica as the chosen brand face.

## Layout

### Global
- Near-black full-page canvas with a centered content frame.
- Navigation stays one desktop line and remains compact.
- Desktop compositions are asymmetric where useful; CSS Grid is preferred over fragile flex percentage math.
- Mobile is a real re-composition, not a scaled desktop.
- A route without an explicit `target` resolves to `primary / Я`; an explicit valid target is preserved across navigation.

### Today
- First viewport belongs to one hero recommendation.
- Hero identity and evidence lead; a small number of alternatives stay visibly subordinate.
- Remaining recommendation candidates become the `Посмотреть следующим` horizontal poster rail rather than disappearing.
- `Я / Партнёр / Вместе` is visible and route-aware; `Я` is the default context.

### Library
- Dense browsing surface: poster-led grid, search and target-aware filters.
- Desktop prioritizes efficient scanning; mobile keeps a two-column poster grid when space permits.
- Empty states remain composed and useful rather than rendering blank space.
- Switching target changes whose subjective signals are foregrounded; it does not create a different underlying film catalog.

### Detail
- Backdrop + poster + identity form the opening cinematic field.
- `Наши впечатления` precedes TMDB.
- The configured contexts `Я / Партнёр / Вместе` remain visible as distinct signal panels, including a composed empty state when a context has no feedback yet.
- The active context appears first and is visually marked, but other household contexts remain inspectable.
- Editing is attached to the target panel being edited; the save target must never change implicitly.
- A missing `Вместе` signal may explicitly use `Я` as a starting template, but the UI must state both the template source and that the result saves to `Вместе`.
- Provider score is rounded to one decimal for display and rendered at a subordinate scale.

## Elevation & Depth

Depth comes from imagery, scrims and restrained separation rather than card shadows everywhere.

- Poster plates may use a soft dark shadow where physical separation improves the cinematic feel.
- Dividers use low-opacity milk-white lines.
- Most grouped content relies on spacing and contrast instead of bordered cards.
- No global glassmorphism treatment.

## Shapes

- Primary surfaces use a consistent soft radius where the approved comp calls for a cinematic field.
- Poster artwork preserves film-poster proportions and is not forced into pill shapes.
- Interactive controls may use compact rounded shapes, but the page must not become “pill-everything”.
- Focus rings use the tungsten accent and remain clearly visible.

## Components

### `TargetSwitcher`
Visible household context control with `Я`, `Партнёр`, `Вместе`. `Я / primary` is the product default. The switcher replaces only the `target` query parameter and preserves route/filter state.

### Today Hero
One dominant recommendation with real backdrop, title, year/runtime/genres, evidence-based “почему сейчас” and a single primary `Подробнее` action.

### Recommendation Alternatives / Poster Rail
Subordinate candidates. Hover/focus may reveal depth under full motion, but reduced-motion must remove spatial movement.

### Library Filters
Search and factual filters, labelled explicitly. No placeholder-as-label behavior.

### Signal Panel
Target-scoped personal/group rating, reaction, viewing status and optional feedback summary. Missing data is shown as an explicit empty state rather than silently substituted from another target. Editing stays scoped to that panel. Copying another target into a new record is allowed only as an explicit user action and never changes the destination target.

### Feedback Editor
The editor always preloads the canonical signal for its destination target. When a template from another target is offered, the form starts empty until the user explicitly chooses the template. The UI visibly identifies where changes will be saved and, after template use, where the starting values came from.

### TMDB Context
Secondary provider metric. Present score with at most one decimal; preserve full source value in canonical data.

### State Messages
Russian loading, empty, error and missing states. They are part of the composed interface, not raw diagnostic output.

### Credits
The `О проекте`/credits surface carries required TMDB attribution. Attribution is not optional decoration.

## Motion

Motion uses `motion/react` and supports the cinematic feel without becoming a dependency for comprehension.

- Entrance/reveal: opacity + restrained transform.
- Recommendation focus changes: controlled crossfade/spatial transition; no autoplay or scroll hijacking.
- Frequent animation is transform/opacity only.
- `prefers-reduced-motion: reduce` removes spatial movement and keeps the entire interface usable.
- Accessibility scans audit the stable reduced-motion state; separate browser tests cover the full-motion path.

## Accessibility

Shipping floor:
- WCAG AA text contrast.
- Semantic landmarks/headings.
- Keyboard-complete profile, filters, cards and detail navigation.
- Visible `:focus-visible` state.
- Useful image alt text where artwork conveys identity; decorative duplicates are hidden appropriately.
- Hover and focus parity for meaningful interactions.
- Responsive checks at 390px, 768px and desktop widths.

## Do’s and Don’ts

### Do
- Prefer personal evidence over generic popularity.
- Treat `Я / primary` as the default owner context while preserving explicit partner/couple choices.
- Use real repository-derived titles, signals and TMDB asset refs.
- Keep Russian as the normal interface language.
- Vary section composition; let hero, rail, library grid and detail each have a different job.
- Keep target absence explicit instead of borrowing another target's data invisibly.
- Keep write actions behind the protected typed-command broker boundary.

### Don’t
- Do not embed mock movie arrays in production components.
- Do not add a second recommendation/scoring engine in React.
- Do not expose GitHub/TMDB/write credentials in the browser.
- Do not mutate canonical YAML from the site.
- Do not use blue-purple AI gradients, generic dashboard metric cards, or equal-card walls as the page’s primary composition.
- Do not fabricate or silently substitute a partner/couple rating to balance layout.
- Do not redirect an edit to another target just because the selected target is empty.
- Do not let TMDB score become visually more important than `Наши впечатления`.

## Review provenance

The executable Impeccable launcher and `spawn_agent` are unavailable in this harness. Direction, critique, audit/polish and documentation therefore follow Impeccable’s documented degraded path. See `.impeccable/surfaces/home.md`, approved comp artifacts under `.impeccable/mocks/`, and `.impeccable/critique/2026-10-01-media-web.md`.
