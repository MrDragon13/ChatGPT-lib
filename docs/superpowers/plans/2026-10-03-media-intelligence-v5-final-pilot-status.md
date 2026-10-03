# Media Intelligence v5 Final Pilot Status

## Current state

- Base `main`: `9d9cfa1eeac2033db3b81b3cc5a41ef39aa5d7f0`.
- Task 11 is complete and published through Pages #42.
- `primary`, `partner`, and `couple` all have conservative evidence-backed inferred-preference replacements.
- Semantic pilot coverage: five representative works.
- Production regressions found during the pilot were fixed through RED→GREEN in PRs #56 and #58.

## Task 12 live checklist

- [x] Internal-only recommendation smoke test; candidates are pinned by executable contract to the local index.
- [x] External-discovery pilot using fresh web/provider facts; local library is memory/exclusion, not the candidate boundary.
- [x] Explainability review: rationale distinguishes explicit user evidence, inferred hypotheses, and current-request reasoning.
- [x] Exploration candidate included without turning genre/profile into a hard filter.
- [ ] Full media verification on final head.
- [ ] Full web verification including browser/screenshot/static scan on final head.
- [ ] Whole-spec review and RED→GREEN fixes for any Critical/Important findings.
- [ ] Merge final PR and confirm post-merge Pages.

## Internal-only smoke

A regression contract now asserts that every `recommend_context` candidate ID is a member of `generated/index.jsonl`. The service implementation itself iterates only `IndexRepository(media/generated/index.jsonl)` and has no external provider call. Media Dev Check #42 passed the new contract together with pytest, canonical validation, rebuild-check, export, and doctor.

## External-discovery pilot

Pilot intent: `couple`; recommend something new outside the local library, under two hours, with intrigue/engagement, while allowing one deliberately unexpected genre choice.

Local-memory check: none of the four candidates below exists in the current generated index, so they are genuinely external candidates rather than disguised internal recommendations.

1. **Black Bag (2025)** — primary candidate. Verified runtime ~94–95 min. External sources describe a dialogue-driven espionage thriller built around suspicion, deduction, dry wit, and intrigue. This aligns with the *inferred* primary intrigue/problem-solving pattern and low-confidence shared couple preference for engaging viewing; it is not presented as an explicit user request for spy films.
2. **Drop (2025)** — direct thrill-ride alternative. Verified runtime 95 min. Reviews characterize it as a tight, efficient mystery thriller focused on sustained suspense. Fit comes mainly from the shared engagement signal. Concern: reviews also note plotting/reveal weaknesses, so the rationale should surface that instead of hiding it.
3. **The Thursday Murder Club (2025)** — lighter/safe option. Verified runtime 118 min; comedy/mystery/crime ensemble. It connects to the primary intrigue anchor and the history around `knives-out-2019`, but external reviews describe the mystery as comparatively cozy/slight, so it should not be oversold as the strongest puzzle.
4. **Companion (2025)** — exploration candidate. Verified runtime 97 min; mystery/thriller + sci-fi + horror + comedy. Sources consistently describe rapid twists/revelations and fast pacing. It intentionally crosses into horror rather than treating past genre history as a ban; the model should warn about the horror/violence dimension rather than silently assuming it is acceptable.

Fresh-fact sources used for the pilot:
- Black Bag: RogerEbert review and Rotten Tomatoes movie info (2025).
- Drop: RogerEbert review and Rotten Tomatoes movie info (2025).
- The Thursday Murder Club: Rotten Tomatoes movie info and RogerEbert review (2025).
- Companion: New York Times review and Rotten Tomatoes movie info (2025).

No `record_recommendation_interaction` command is written for this pilot because there was no real user-facing recommendation selection/rejection event.

## Explainability ruling

Recommended phrasing must say things such as `по накопленным данным есть гипотеза...` or `в прошлых отзывах повторяется...` for inferred taste. It must reserve `ты явно говорил...` only for raw explicit feedback/preferences. Current-request constraints (for example `до двух часов`) are separate from long-term taste and may override soft priors.

## Guardrails

- Do not persist recommendation preference unless an actual user interaction warrants it.
- `not_tonight` is not `not_interested`.
- Sparse partner evidence stays conservative.
- Couple disagreements remain visible; never average them into a hidden preference.
- Inferred preferences are hypotheses with evidence, never rewritten as explicit user statements.
- External discovery may use LLM knowledge for candidate generation, but fresh/precise facts must be verified with current external sources.

## Resume from here

Wait for both Media Dev Check and Web Check on the latest PR head. If both are green, run whole-spec/whole-PR review. Fix any Critical/Important finding through RED→GREEN. Then refresh the PR body with exact final SHA/check evidence, mark ready, merge exact head, verify full post-merge Pages, and close Task 12 continuity with v5 pilot status plus v6 candidates.