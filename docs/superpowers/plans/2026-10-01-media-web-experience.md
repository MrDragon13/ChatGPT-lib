# Media Web Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a cinematic Russian-language React site on GitHub Pages that visualizes the existing personal media library from repository-derived data without creating a second source of truth.

**Architecture:** Keep Git/YAML canonical and add a deterministic Python read exporter that emits a versioned static web manifest. Build a React + Vite + TypeScript + Motion client under `web/` that consumes only that manifest, uses hash routing, and never receives write credentials; future edits remain a separate protected typed-command broker. Establish the visual world through the approved comp-first Impeccable/Taste flow before writing UI components, then finish with Pages deployment, accessibility, critique, audit, polish, and DESIGN.md documentation.

**Tech Stack:** Python 3.12, existing PyYAML/jsonschema/pytest media tooling, React, Vite, TypeScript, Motion (`motion/react`), React Router hash routing, Tailwind CSS v4 via the Vite plugin plus CSS custom properties for design tokens, Phosphor icons, Vitest + Testing Library, Playwright + axe for browser/a11y checks, GitHub Actions + GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-10-01-media-web-experience-design.md`

## Global Constraints

- Git/YAML remains canonical; the web manifest is a derived build artifact and must never be treated as source data.
- Frontend v1 is read-only. No browser-side YAML edits, GitHub write token, Actions secret, TMDB credential, or future broker credential may enter the JS bundle or Pages artifact.
- Ratings, reactions, feedback, viewing state, and anonymous viewer/group IDs may be published in the static read manifest; no additional encryption/passphrase layer is required.
- All ordinary visible UI copy is Russian; only provider/legal text that must remain verbatim may stay in its required language.
- Production components consume repository-derived data only; no production mock movie arrays.
- Personal signal is visually primary; public metrics are secondary.
- No new opaque recommendation score. Reuse `build_recommend_context(...)` for deterministic evidence ordering where recommendations are needed.
- V1 routes are hash-based and must work under the GitHub project-site subpath.
- Taste dials are fixed at `DESIGN_VARIANCE = 7`, `MOTION_INTENSITY = 8`, `VISUAL_DENSITY = 4`.
- Visual direction is the approved “вечерний программный гид + личный киножурнал”: charcoal/graphite base, milk-white type, one tungsten accent, poster/backdrop imagery as the main color source, no blue-purple AI gradients.
- Motion must respect `prefers-reduced-motion`; frequent animation is transform/opacity only.
- Accessibility shipping floor: WCAG AA contrast, keyboard navigation, visible focus, semantic landmarks/headings, useful image alt/decorative treatment, hover/focus parity.
- TMDB image/data usage requires the approved logo plus the required notice in an `О проекте`/credits surface.
- Use the installed Impeccable and Taste/high-end-visual-design skills in the order specified below; `DESIGN.md` documents the built world at the end, not before it exists.

## Review Focus

1. **Incomplete metadata:** a work with no poster, backdrop, runtime, synopsis, rating, or viewer signal must still render a stable card/detail layout with honest omission/placeholder behavior. Covered in Tasks 1, 3, and 4.
2. **Sparse partner/couple data:** switching to `Партнёр` or `Вместе` must not fabricate recommendations or empty personal sections; sections hide or show an explicit empty state. Covered in Tasks 1, 3, and 4.
3. **GitHub Pages subpath/deep links:** direct refresh on `#/work/<id>` and `#/library?...` must not 404 or lose filters. Covered in Tasks 3 and 6.
4. **Real-image readability:** light or busy TMDB backdrops must not make hero/detail copy unreadable; scrim/contrast behavior is tested against representative real assets. Covered in Tasks 4, 5, and 7.
5. **Secret leakage:** final static artifact must contain read data but no write/provider credentials or accidental environment values. Covered in Tasks 1 and 6.

---

### Task 1: Versioned web manifest exporter

**Files:**
- Create: `media/service/web_export.py`
- Create: `media/schemas/web-manifest.schema.json`
- Modify: `media/cli.py`
- Test: `tests/media/test_web_export.py`
- Test: `tests/media/test_cli.py`

**Interfaces:**
- Consumes: `YamlRepository.iter_works()`, `YamlRepository.configured_targets()`, `IndexRepository.rows()`, generated profiles, and `build_recommend_context(media_root, RecommendContextRequest)`.
- Produces: `build_web_manifest(media_root: Path) -> dict[str, Any]` and `write_web_manifest(media_root: Path, output_path: Path) -> Path`.
- CLI: `python -m media.cli web-export --output <path> --format json`.
- Manifest v1 top-level keys: `schema_version`, `targets`, `profiles`, `recommendations`, `works`.
- `targets`: `{ "viewers": ["primary", "partner"], "groups": {"couple": ["primary", "partner"]} }` derived from config, never hard-coded.
- `recommendations[target]`: existing `recommend_context` output produced with `only_unwatched=True`, `runtime_max=None`, `include_not_interested=False`, `limit=24`, `text=None`.
- Each work includes only UI read fields already present in canonical/derived data: `id`, `identity`, factual external metadata/assets/metrics, `viewer_signals`, `group_signals`, derived index `interest`/`traits`, and canonical provenance dates needed for truthful chronology.

- [ ] **Step 1: Write failing exporter contract tests**

Add tests that assert: manifest schema version is `1`; targets come from fixture config; Arrival keeps its work ID/title/viewing signal; missing optional metadata serializes as null/empty without exception; recommendations contain no invented numeric score; exporting does not change any canonical/generated file bytes; manifest contains no keys matching token/secret/credential/password patterns.

- [ ] **Step 2: Run exporter tests to verify RED**

Run: `python -m pytest tests/media/test_web_export.py -q`

Expected: FAIL because `media.service.web_export` and the schema do not exist.

- [ ] **Step 3: Add `web-manifest.schema.json` and minimal exporter**

Use `validate_against_schema(...)` after construction. Keep serialization deterministic (`sort_keys=True`, UTF-8, compact separators, trailing newline). Do not mutate `media/generated/`.

- [ ] **Step 4: Add `web-export` CLI and CLI tests**

The command writes exactly the requested output path, creates parent directories, emits `{status:"ok", output:"...", works:<count>, bytes:<size>}` in JSON mode, and exits nonzero on schema/export failure.

- [ ] **Step 5: Run RED→GREEN verification**

Run:
```bash
python -m pytest tests/media/test_web_export.py tests/media/test_cli.py -q
python -m media.cli web-export --output /tmp/media-web-manifest.json --format json
```

Expected: tests pass; real export reports 102 current works (or the exact current canonical count if main changes before execution).

- [ ] **Step 6: Measure the real minified manifest before frontend contract lock**

If `/tmp/media-web-manifest.json` is `<= 2 MiB`, keep the single-file contract for v1. If it is `> 2 MiB`, stop this task and change the contract to `manifest.json` + `works/<id>.json` before Task 3; do not let frontend code support both formats.

- [ ] **Step 7: Commit**

```bash
git add media/service/web_export.py media/schemas/web-manifest.schema.json media/cli.py tests/media/test_web_export.py tests/media/test_cli.py
git commit -m "feat: export media web manifest"
```

---

### Task 2: Impeccable direction, comp-first visual contract, typeset, and colorize

**Files:**
- Read/verify: `PRODUCT.md`
- Read/verify: `.impeccable/config.json`
- Create/update: Impeccable surface brief for the primary home route
- Create: `.impeccable/mocks/**` and prompt/provenance sidecars produced by the Impeccable comp flow
- Do **not** create UI component source in this task.

**Interfaces:**
- Consumes: the real manifest produced in Task 1 plus the approved spec.
- Produces: one locked home-page direction/approved comp, a direction contract with six required blocks, selected Cyrillic-capable typography, and palette/material decisions used by Task 3+.

- [ ] **Step 1: Load Impeccable project context once**

Run the installed Impeccable context command from the project root. Honor `PRODUCT.md` and `.impeccable/config.json` (`buildPath: comp`). If the launcher cannot run in the available harness, follow Impeccable’s documented degraded path rather than inventing context.

- [ ] **Step 2: Run the required new-world direction round**

Use `mode=operate` because the visitor’s success is choosing/browsing a film, while preserving the approved cinematic/editorial thesis. The decision materials must use real titles/assets from Task 1, not fabricated film arrays. Avoid the category-default Netflix clone and generic dashboard as ruts.

- [ ] **Step 3: Lock one direction and record the direction contract**

The contract must explicitly preserve Taste `7/8/4`, asymmetric first viewport, charcoal/graphite + tungsten palette strategy, image-led chroma, Russian copy, and the no-blue-purple-gradient rule.

- [ ] **Step 4: Complete the comp-first round**

Produce the approved desktop-first home comp plus the required alternatives/provenance under Impeccable’s comp workflow. Use actual poster/backdrop references or clearly labeled generated plates only where Impeccable requires authored visual material; never synthesize replacement posters for real films.

- [ ] **Step 5: Run `/impeccable typeset`**

Select one production-available variable sans/grotesk with complete Cyrillic coverage. Record the exact font source/package and fallback stack in the surface contract. Do not use Inter, Roboto, Arial, Open Sans, or Helvetica as chosen brand typography.

- [ ] **Step 6: Run `/impeccable colorize`**

Lock one tungsten accent and the dark neutral token family. Real imagery remains the dominant color source; colorize must not introduce purple/blue AI glows.

- [ ] **Step 7: Verify comp/direction artifacts and commit them**

No UI source is allowed in this commit.

```bash
git add PRODUCT.md .impeccable docs/superpowers/specs/2026-10-01-media-web-experience-design.md
git commit -m "design: lock media web visual direction"
```

---

### Task 3: React/Vite data client, routing, and non-visual application shell

**Files:**
- Create: `web/package.json`, `web/package-lock.json`
- Create: `web/index.html`, `web/vite.config.ts`, `web/tsconfig*.json`
- Create: `web/src/main.tsx`
- Create: `web/src/app/router.tsx`
- Create: `web/src/app/AppShell.tsx`
- Create: `web/src/data/types.ts`
- Create: `web/src/data/client.ts`
- Create: `web/src/data/assets.ts`
- Create: `web/src/styles/global.css`
- Create: `web/src/test/setup.ts`
- Create: `web/src/data/client.test.ts`
- Create: `web/src/app/router.test.tsx`
- Modify: root `.gitignore` or `web/.gitignore` so generated `web/public/data/manifest.json` and build output are not hand-maintained source.

**Interfaces:**
- Consumes: manifest v1 from Task 1 and visual/type/color contract from Task 2.
- Produces: `loadManifest(): Promise<WebManifest>`, `tmdbImageUrl(path, size): string | null`, hash routes `#/today`, `#/library`, `#/work/:id`, and a shared `target` query parameter.

- [ ] **Step 1: Scaffold dependencies and verify them from `package.json` before import**

Use React, React DOM, React Router, Motion, Tailwind v4 + Vite plugin, Phosphor icons, Vitest, Testing Library, Playwright, and axe integration. Commit exact resolved versions in `package-lock.json`.

- [ ] **Step 2: Write failing data-client tests**

Tests cover valid manifest loading, schema-version mismatch -> Russian error state object, missing manifest -> Russian error, and asset helper behavior for null poster/backdrop refs.

- [ ] **Step 3: Run RED**

Run: `cd web && npm test -- --run src/data/client.test.ts`

Expected: FAIL because client/types do not exist.

- [ ] **Step 4: Implement TypeScript manifest types and data client**

Do not add movie arrays to component source. Keep provider URL construction centralized in `assets.ts`.

- [ ] **Step 5: Write and implement hash-router tests**

Assert `#/today`, `#/library?target=couple`, and `#/work/arrival-2016` resolve without history-server support and preserve the target parameter.

- [ ] **Step 6: Add the minimal semantic shell**

Only route outlets, landmarks, loading/error boundary, and typography/color token plumbing. No final visual sections yet.

- [ ] **Step 7: Run checks and commit**

```bash
cd web
npm test -- --run
npm run typecheck
npm run build
cd ..
git add web
git commit -m "feat: scaffold media web client"
```

---

### Task 4: Build the real home, library, and work-detail surfaces

**Files:**
- Create: `web/src/features/home/HomePage.tsx`
- Create: `web/src/features/home/selectors.ts`
- Create: `web/src/features/home/*.test.tsx`
- Create: `web/src/features/library/LibraryPage.tsx`
- Create: `web/src/features/library/filters.ts`
- Create: `web/src/features/library/*.test.tsx`
- Create: `web/src/features/work-detail/WorkDetailPage.tsx`
- Create: `web/src/features/work-detail/*.test.tsx`
- Create focused shared components under `web/src/components/` for poster/backdrop media, target switcher, rating/reaction display, poster rail, empty/error states, credits/about.
- Create/update: `web/src/styles/tokens.css`, `web/src/styles/components.css` (or equivalent focused style modules chosen by the executor; do not collapse the whole site into one giant stylesheet).

**Interfaces:**
- Consumes: `WebManifest`, `loadManifest`, route target, selected visual comp.
- Produces: selectors that return view models without inventing facts; components remain pure consumers of those view models.

- [ ] **Step 1: Write failing selector tests for the home screen**

Pin these rules: hero comes from precomputed recommendation candidates; unwatched/not-interested semantics are inherited rather than recalculated; `Для двоих` appears only when `couple` has usable candidates; “recent” uses actual `last_watched_at` or provenance dates and disappears when no truthful chronology exists; sparse partner data never copies primary reaction/rating.

- [ ] **Step 2: Run home RED and implement minimal selectors**

Run: `cd web && npm test -- --run src/features/home`

- [ ] **Step 3: Build HomePage to the approved comp using `high-end-visual-design`**

First viewport: one dominant real backdrop, one primary title, year/runtime/genres, concise evidence-based “почему сейчас”, `Подробнее`, and 2–3 visually subordinate alternatives. Below: varied poster rail/editorial layouts; no repeating equal-card grid and no generic dashboard metrics.

- [ ] **Step 4: Write failing library filter tests and implement**

Search matches Russian/original/alternate titles; viewing filters are target-aware; genre/year filters compose; URL search params round-trip.

- [ ] **Step 5: Build LibraryPage**

Poster-first grid, Russian filters, keyboard usable controls, honest zero-results state. No data table.

- [ ] **Step 6: Write failing detail tests and implement WorkDetailPage**

Assert identity + personal signal precede external rating; missing poster/backdrop/runtime/synopsis do not crash; primary/partner/couple panels render independently; future edit affordance has a component boundary but no write control in v1.

- [ ] **Step 7: Add `О проекте` / TMDB attribution**

Use approved TMDB logo asset and the required notice verbatim, with surrounding explanatory UI in Russian.

- [ ] **Step 8: Verify desktop functional build and commit**

```bash
cd web
npm test -- --run
npm run typecheck
npm run build
cd ..
git add web
git commit -m "feat: build cinematic media surfaces"
```

---

### Task 5: Motion choreography and responsive behavior

**Files:**
- Create: `web/src/motion/transitions.ts`
- Create/update: motion leaf components in home/library/detail features
- Create: `web/e2e/responsive.spec.ts`
- Create: `web/e2e/motion.spec.ts`

**Interfaces:**
- Consumes: stable surfaces from Task 4 and Impeccable direction contract.
- Produces: shared Motion variants/springs; no continuous values in React state.

- [ ] **Step 1: Run `/impeccable animate` against the built surfaces**

Implement the approved motion grammar: hero crossfade + spatial slide, restrained rail inertia/snap, subtle card scale/translation, detail continuity where compatible with hash routing, bounded section reveal.

- [ ] **Step 2: Add reduced-motion tests**

Playwright test emulates `prefers-reduced-motion: reduce` and asserts content is immediately available with spatial/entrance animation disabled.

- [ ] **Step 3: Add responsive tests**

At 1440px: hero/title/action fit first viewport and navigation is one line. At 390px: no horizontal page overflow; rails remain independently scrollable; library is two columns unless the tested narrower breakpoint requires one; tap targets remain usable.

- [ ] **Step 4: Implement mobile composition**

Do not shrink the desktop composition mechanically. Hero becomes a vertical poster/backdrop experience; remove desktop overlap/rotation that harms touch behavior.

- [ ] **Step 5: Verify and commit**

```bash
cd web
npm run test:e2e -- responsive.spec.ts motion.spec.ts
npm test -- --run
npm run typecheck
npm run build
cd ..
git add web
git commit -m "feat: add cinematic motion and responsive layouts"
```

---

### Task 6: GitHub Pages pipeline and full automated gates

**Files:**
- Create: `.github/workflows/media-pages.yml`
- Create: `web/e2e/a11y.spec.ts`
- Create: `tests/media/test_pages_contract.py`
- Modify: `README.md` and/or `media/README.md` with the read-site command/deployment contract.

**Interfaces:**
- Consumes: `python -m media.cli web-export`, npm scripts from `web/package.json`.
- Produces: a Pages artifact from `web/dist` on `main`; PRs run build/test without deploying.

- [ ] **Step 1: Write failing workflow contract tests**

Assert the workflow: validates media first; runs `rebuild --check` and doctor; exports the manifest before npm build; installs dependencies with `npm ci`; runs frontend tests/typecheck/build; uses Pages upload/deploy actions only for deployment; never references `TMDB_READ_TOKEN` or media write secrets.

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/media/test_pages_contract.py -q`

Expected: FAIL because workflow is absent.

- [ ] **Step 3: Implement Pages workflow**

Use minimal required Pages permissions and project-site Vite base. Generate `web/public/data/manifest.json` in the runner before build; do not commit it as source.

- [ ] **Step 4: Add browser accessibility test**

Run axe against Today, Library, one detail route, and representative empty/error state. Treat serious/critical violations as failures. Add explicit keyboard tests for nav, target switch, rail/card focus, search/filter, and detail navigation.

- [ ] **Step 5: Add static-artifact secret scan**

After `npm run build`, search `web/dist` for known secret variable names and test sentinel values; fail if found. Read data itself is allowed.

- [ ] **Step 6: Run complete local/CI-equivalent gate**

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
python -m media.cli web-export --output web/public/data/manifest.json --format json
cd web
npm ci
npm test -- --run
npm run typecheck
npm run build
npm run test:e2e
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/media-pages.yml tests/media/test_pages_contract.py README.md media/README.md web
git commit -m "ci: publish media site to GitHub Pages"
```

---

### Task 7: Impeccable critique, audit, polish, finish review, and DESIGN.md

**Files:**
- Update UI files only in response to concrete critique/audit findings.
- Create/update: `.impeccable/review/desktop.png`, `.impeccable/review/mobile.png`, comp diff artifacts as required by Impeccable.
- Create: `DESIGN.md`
- Create: `.impeccable/design.json`
- Update: primary surface brief with final direction state if required.

**Interfaces:**
- Consumes: complete built site and approved comp.
- Produces: finish-review verdict plus documented design system.

- [ ] **Step 1: Capture valid desktop/mobile review evidence**

Generate manifest from current branch first. Capture 1440px desktop and 390px mobile after entrance motion settles; verify each screenshot opens and shows the intended full page/state.

- [ ] **Step 2: Run `/impeccable critique`**

Judge visual hierarchy, first-viewport decision speed, poster/backdrop alignment, density, real-image text readability, and whether the page has slipped into repetitive card-grid/dashboard patterns. Apply one batched correction pass.

- [ ] **Step 3: Run `/impeccable audit`**

Fix accessibility, contrast, responsive overflow, DOM/semantic issues, motion/reduced-motion problems, and obvious performance defects in one batch. Do not weaken the chosen visual direction to “solve” the audit unless clarity/accessibility requires it.

- [ ] **Step 4: Run `/impeccable polish`**

Pixel-align grids, spacing, nested radii, typography rhythm, poster crops, and remove duplicate borders/noise. No new features in polish.

- [ ] **Step 5: Run Impeccable finish review**

Use the approved comp, direction contract, craft-floor reference, desktop/mobile captures, and comp-diff evidence. Follow the returned disposition exactly (`ship`, `fix`, `rebuild`, or `recapture`) within the bounded review budget.

- [ ] **Step 6: Run `/impeccable document` after the built world is final**

Create token-bearing `DESIGN.md` and `.impeccable/design.json` from the actual shipped interface. Verify the Taste dials, font, palette, spacing/radius/motion grammar, component rules, and Russian-copy conventions are documented.

- [ ] **Step 7: Run final verification after documentation**

```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
python -m media.cli web-export --output web/public/data/manifest.json --format json
cd web
npm test -- --run
npm run typecheck
npm run build
npm run test:e2e
```

Then confirm generated web manifest/build output are not accidentally staged as canonical source unless the plan explicitly changed that policy.

- [ ] **Step 8: Whole-branch review and PR**

Review `main...HEAD` for: canonical media untouched, no production mocks, no credentials, no unexpected schema/vocabulary changes, Russian visible copy, TMDB attribution, Pages-only deployment scope, and consistency with the approved comp/spec.

- [ ] **Step 9: Commit finish artifacts**

```bash
git add DESIGN.md .impeccable web docs .github tests README.md media/README.md
git commit -m "design: finish cinematic media web experience"
```

Open a normal architectural/frontend PR to `main`; this PR is never eligible for the media data auto-merge path.
