# Media Intelligence v5 Final Pilot Status

## Current state

- Base `main`: `9d9cfa1eeac2033db3b81b3cc5a41ef39aa5d7f0`.
- Task 11 is complete and published through Pages #42.
- `primary`, `partner`, and `couple` all have conservative evidence-backed inferred-preference replacements.
- Semantic pilot coverage: five representative works.
- Production regressions found during the pilot were fixed through RED→GREEN in PRs #56 and #58.

## Task 12 live checklist

- [ ] Internal-only recommendation smoke test; candidates must come only from local index.
- [ ] External-discovery pilot using fresh web/provider facts; local library is memory/exclusion, not the candidate boundary.
- [ ] Explainability review: rationale must distinguish explicit user evidence, inferred hypotheses, and current-request reasoning.
- [ ] Exploration candidate included when appropriate without turning genre/profile into a hard filter.
- [ ] Full media verification.
- [ ] Full web verification including browser/screenshot/static scan.
- [ ] Whole-spec review and RED→GREEN fixes for any Critical/Important findings.
- [ ] Merge final PR and confirm post-merge Pages.

## Guardrails

- Do not persist recommendation preference unless an actual user interaction warrants it.
- `not_tonight` is not `not_interested`.
- Sparse partner evidence stays conservative.
- Couple disagreements remain visible; never average them into a hidden preference.
- Inferred preferences are hypotheses with evidence, never rewritten as explicit user statements.
- External discovery may use LLM knowledge for candidate generation, but fresh/precise facts must be verified with current external sources.

## Resume from here

Start Task 12 Step 1: run an internal-only recommendation smoke test against current `main`, prove returned candidates are local-index works, record the result in the final PR, then proceed to external discovery.