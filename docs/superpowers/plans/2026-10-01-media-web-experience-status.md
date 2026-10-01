# Media Web Experience — Execution Status

Companion tracker for `docs/superpowers/plans/2026-10-01-media-web-experience.md`.

Last reconciled against branch `feature/media-web-experience`, PR #13, head `8526f1d859c84f8ef5bbb9bf8d9eae59d1ad87e5`.

## Current state

- **Task 1 — Versioned web manifest exporter: COMPLETE.** Manifest v1 is deterministic, schema-validated, read-only, reuses `recommend_context`, exposes canonical Russian vocabulary labels, and contains no write/provider credentials. Real export: **103 works / 362,998 bytes**, so v1 remains a single `manifest.json`.
- **Task 2 — Impeccable direction / comp / type / color: COMPLETE via documented degraded path.** Three comps exist; `home-c` is approved. Onest Variable, near-black/graphite neutrals, milk-white type, single tungsten accent, Taste **7 / 8 / 4** are locked in `.impeccable/surfaces/home.md`. The Impeccable launcher is not executable in this harness, so no claim is made that slash-command binaries ran.
- **Task 3 — React/Vite data client, routing, shell: COMPLETE.** React/Vite/TypeScript client, committed lockfile, hash routing, manifest loader, target resolution, centralized TMDB image URLs, Onest/tokens, semantic loading/error shell are implemented. Reproducible CI uses Node 22.22.2 + `npm ci`.
- **Task 4 — Home / Library / Detail surfaces: IN PROGRESS (reopened by review findings).** Home, Library and Detail surfaces/selectors/tests exist and their previous contract tests were green. Current RED review additions require: (1) preserve recommendation candidates after hero alternatives as a `next-watch` rail; (2) add a visible `Я / Партнёр / Вместе` target switcher that preserves current route filters.
- **Task 5 — Motion and responsive behavior: IMPLEMENTED, REVERIFY AFTER TASK 4 FIXES.** Shared Motion transitions, reduced-motion behavior and responsive Playwright checks exist. A previous review fix removed spatial hover under reduced motion.
- **Task 6 — Pages pipeline and automated gates: IMPLEMENTED, FULL GATE NOT YET GREEN.** `media-pages.yml`, Web Check, secret scan, Playwright responsive/motion/a11y checks and review captures exist. Before the newest RED tests, unit/typecheck/build/secret scan were green; browser checks had one AA contrast finding for library count text (`#7b776f` on `#080808`, 4.49:1). Recheck after Task 4 fixes and correct centrally if still present.
- **Task 7 — Critique / audit / polish / document: IN PROGRESS.** Review findings are being converted into failing tests before fixes. Final `DESIGN.md` / `.impeccable/design.json`, final review captures, whole-branch review and ready-for-review transition are still outstanding.

## Current RED evidence

Current head Web Check intentionally fails at the unit stage while Media Check remains green:

1. `src/features/home/home.test.ts`: `model.next` is not yet produced; the new test requires recommendation candidates after the hero + alternatives to remain available for the `Посмотреть следующим` rail.
2. `src/components/TargetSwitcher.test.tsx`: `TargetSwitcher.tsx` does not yet exist. Contract requires navigation label `Профиль просмотра`, links `Я`, `Партнёр`, `Вместе`, active `aria-current="page"`, and replacement of only the `target` query parameter while preserving filters.

## Next actions

1. Implement the two current RED findings minimally and integrate them into the visible surfaces.
2. Run full Web Check: unit tests → typecheck → build → secret scan → Playwright responsive/motion/a11y → review screenshots.
3. If the previous 4.49:1 library contrast finding remains, raise the shared muted-text floor rather than suppressing axe.
4. Complete Task 7 critique/audit/polish against fresh desktop/mobile captures.
5. Generate `DESIGN.md` and `.impeccable/design.json` from the actual final interface.
6. Run whole-branch review and final exact-head gates, then mark PR #13 ready for review.

## Integration rule

PR #13 is an architectural/frontend PR and is **not** eligible for media data auto-merge. Do not merge it until final review/gates are green and the user explicitly approves integration.
