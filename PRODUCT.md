# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: React + Vite + TypeScript + Motion, deployed as a static GitHub Pages site. The site reads repository-derived media data; future write interactions must go through the existing typed command / validation protocol rather than direct YAML editing.

## Users

Primary users are the repository owner and partner. The site is intended for internal household use rather than a public audience.

## Product Purpose

Provide a cinematic, visual interface over the existing personal media recommendation system so the users can browse their library, understand recommendations, revisit watched titles, and choose what to watch next without reading repository files.

The primary way of adding rich new media data remains conversation with an LLM. The website complements that workflow rather than replacing it.

## Positioning

The product is a personal recommendation surface backed by the users' own canonical viewing signals, ratings, feedback, semantic preferences, and enriched media metadata. It is not a generic public movie catalog or a public-rating browser.

## Operating Context

- Git/YAML remains the canonical source of truth.
- Generated indexes/profiles are derived and rebuildable.
- LLM, CLI, and future website write actions share one validation/write protocol.
- Website v1 is a read-only visual surface over existing data.
- A later edit flow may support quick corrections such as rating or viewing-status changes, but those edits must be submitted as typed commands through a protected write broker and must never mutate YAML directly from the browser.
- The repository and GitHub Pages deployment remain the architectural home of the project.
- The site is for internal use, but confidentiality of movie ratings, reactions, and comments is not a product requirement; it is acceptable if the published Pages site is reachable by others.

## Capabilities and Constraints

- Current canonical media structure is strict and must be treated as read-only by frontend rendering code.
- Frontend components must consume real repository-derived data; no production mock arrays may be embedded in components.
- The browser must never receive repository write credentials, GitHub tokens, provider secrets, or unrelated private data.
- Existing media schema, vocabulary, IDs, validation rules, generated artifacts, and user signals must remain authoritative.
- v1 may publish media ratings, reactions, comments, and other media-library fields as ordinary static read data; no passphrase/encryption layer is required for them.
- v1 must work as a static build suitable for GitHub Pages.
- Future quick edits must reuse the typed-command pipeline and validation gates already used by LLM/CLI writes.
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

1. Personal signal outranks generic popularity.
2. The site visualizes canonical truth; it does not create a second source of truth.
3. Choosing a film should feel immediate and enjoyable, not like operating an admin panel.
4. Rich LLM conversation remains the primary input path; the site adds fast visual navigation and later lightweight corrections.
5. Every future write path must preserve validation, identity safety, and reviewability.

## Accessibility & Inclusion

The web surface should meet WCAG AA contrast and keyboard/focus expectations, respect reduced-motion preferences, and preserve full usability without motion effects.
