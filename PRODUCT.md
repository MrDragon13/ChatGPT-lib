# Product

<!-- impeccable:product-schema 1 -->

Scope: media-web product brief; not repository/system architecture.

## Platform

web

## Stack

delegated: React + Vite + TypeScript + Motion, deployed as a static GitHub Pages site. The site reads repository-derived media data; protected lightweight feedback edits go through the existing typed command / validation protocol rather than direct YAML editing.

## Users

The repository owner is the primary user and owner of the library. Partner and household/group data are supporting contexts over the same library rather than separate primary libraries. The site is intended for internal household use rather than a public audience.

## Product Purpose

Provide a cinematic, visual interface over the existing personal media recommendation system so the owner can browse the library, understand recommendations, revisit watched titles, and choose what to watch next without reading repository files, while still being able to inspect partner and shared household context when useful.

The primary way of adding rich new media data remains conversation with an LLM. The website complements that workflow rather than replacing it.

## Positioning

The product is a personal recommendation surface backed by the owner's canonical viewing signals, ratings, feedback, semantic preferences, and enriched media metadata, with partner and shared-group signals as additional context. It is not a generic public movie catalog or a public-rating browser.

## Operating Context

- Git/YAML remains the canonical source of truth.
- Generated indexes/profiles are derived and rebuildable.
- LLM, CLI, and website write actions share one validation/write protocol.
- `primary / Я` is the default website context; explicit `partner` and `couple` choices are preserved across navigation.
- Lightweight website corrections such as rating, reaction and review changes are submitted as typed commands through the protected write broker and never mutate YAML directly from the browser.
- The repository and GitHub Pages deployment remain the architectural home of the project.
- The site is for internal use, but confidentiality of movie ratings, reactions, and comments is not a product requirement; it is acceptable if the published Pages site is reachable by others.

## Capabilities and Constraints

- Current canonical media structure is strict and must be treated as authoritative by frontend rendering and editing code.
- Frontend components must consume real repository-derived data; no production mock arrays may be embedded in components.
- The browser must never receive repository write credentials, GitHub tokens, provider secrets, or unrelated private data.
- Existing media schema, vocabulary, IDs, validation rules, generated artifacts, and user signals must remain authoritative.
- Media ratings, reactions, comments, and other media-library fields may be published as ordinary static read data; no passphrase/encryption layer is required for them.
- The site must work as a static build suitable for GitHub Pages.
- Quick edits must reuse the typed-command pipeline and validation gates already used by LLM/CLI writes.
- A selected target is an explicit data destination: the UI must never silently save a `couple` edit into `primary`, or vice versa.
- Data from another target may be offered only as an explicit starting template; the source and save destination must remain visible to the user.
- All visible website interface copy is in Russian, except provider/legal wording that must remain verbatim for attribution compliance.

## Brand Commitments

- The interface should feel cinematic and premium rather than like a data dashboard.
- The user explicitly referenced Netflix/MUBI as a quality and composition signal, not as a requirement to copy either product.
- Avoid generic blue-purple AI gradients and generic flat dashboard/table layouts.

## Evidence on Hand

- Canonical media data under `media/data/works/`.
- Derived recommendation/read context under `media/generated/`.
- Viewer and group configuration under `media/config/`.
- Controlled vocabulary in `media/vocabulary.yaml`.
- Existing typed-command, validation, enrichment, receipt, and GitHub Actions workflows.
- TMDB poster/backdrop references already stored in enriched work metadata.

No testimonials, public-user metrics, commercial claims, pricing, or public audience evidence exists and none should be invented.

## Product Principles

1. The owner's personal signal and context are the default; partner/shared context is supplemental and explicit.
2. Personal signal outranks generic popularity.
3. The site visualizes canonical truth; it does not create a second source of truth.
4. Choosing a film should feel immediate and enjoyable, not like operating an admin panel.
5. Rich LLM conversation remains the primary input path; the site adds fast visual navigation and lightweight corrections.
6. Every write path must preserve target clarity, validation, identity safety, and reviewability.

## Accessibility & Inclusion

The web surface should meet WCAG AA contrast and keyboard/focus expectations, respect reduced-motion preferences, and preserve full usability without motion effects.
