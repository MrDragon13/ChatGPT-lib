# Media legacy reassessment pilot runbook

Status in PR A: **foundation implemented; pilot not activated**. The durable pilot ledger is created only by the separate manual activation PR after this foundation is reviewed and merged.

## Purpose and boundary

The pilot upgrades historical `primary` review evidence into current explicit rating/reaction/structured-feedback evidence before Stage B evaluation work. It does **not** perform semantic fingerprint backfill. Semantic vocabulary/provenance and targeted semantic enrichment are a separate later cycle.

The frozen comparison point is Stage A revision `35afaca898eae6937066f230906b41af0e1f6690` and `media/baselines/intelligence-stage-a.json`. Progress and later quality comparisons use that frozen Stage A baseline, not yesterday's generated profile.

The ledger lives at `media/pilots/legacy-reassessment-primary.json`. It is operational provenance, not taste truth. Canonical current opinion remains in work viewer signals and their existing history.

## Human session flow

Default session size is **5** works.

1. Read `python -m media.cli reassessment-context --limit 5 --format json`.
2. If there is an open session, resume its `in_progress` items. Otherwise the context returns the next frozen-order `pending` works; only after the main pending pass is exhausted may `deferred` items return.
3. For a new batch, run `reserve_reassessment_session` and wait until that reservation is authoritative on `main`. Do not present the first work from a new batch before durable reservation.
4. For each reserved work, show only a neutral factual memory jog before the first current answer: title/year, short factual synopsis and, if useful, factual director/cast. Do not expose old rating, reaction, feedback, structured signals or semantic traits by default.
5. Ask for the user's current opinion. If the user first asks what they previously wrote, historical evidence may be shown, but record that exposure truthfully.
6. If historical recall is needed after the independent first answer, use `python -m media.cli reassessment-history <work-id> --format json`. This is a separate second-phase route.
7. Record the result through `complete_reassessment_item`. Do not directly edit YAML/JSON.
8. Continue until all reserved works are resolved, then close the session and persist the audit snapshot.

Git/PR/workflow mechanics stay behind the scenes during the normal user conversation.

## Unanchored evidence and historical exposure

For reviewed outcomes the operation records:

- `historical_exposure.timing = none | before_initial_response | after_initial_response`;
- `historical_exposure.before_finalization = true | false`.

Examples:

- old record never shown: `none / false`;
- user asks for the old record before giving an independent answer: `before_initial_response / true`;
- user answers independently, then sees history and adjusts before saving: `after_initial_response / true`;
- history is shown only after canonical finalization: `after_initial_response / false`.

Never synthesize a fresh explicit signal from old v1 text without the user's current confirmation.

## Lifecycle and anti-loop

Lifecycle states are `pending`, `in_progress`, `reviewed`, and `deferred`.

- `reserve_reassessment_session` moves the exact next frozen-order batch into `in_progress`, records whether the session belongs to the `pending` or `deferred` phase, and must reach authoritative `main` before the first work from that new batch is presented.
- `complete_reassessment_item` atomically applies at most one `primary` feedback mutation and advances the corresponding ledger item.
- `close_reassessment_session` closes a fully resolved session and stores its Stage A audit progress snapshot.

A `reviewed` item is terminal for pilot `primary-legacy-v1` and must never automatically reopen. `deferred` means the user could not or did not want to give a reliable current opinion; it returns only in the deferred pass after all `pending` work is exhausted.

All three pilot writes serialize on the current ledger `expected_ledger_digest`. Reservation and completion also carry raw work-file digests used by guarded merge to fail closed if a reserved canonical work moved after planning. Stale ledger or work state must be replayed against current `main`.

## Completion outcomes

`changed` means canonical explicit evidence changed. This includes confirming the same numeric score when the old source was `inferred` or `explicit_approx`: provenance still changes to `explicit`.

`confirmed_unchanged` is valid only when the current canonical evidence is already explicit and the fresh confirmation does not require a canonical mutation. It must not create fake history just to prove the pilot ran; the ledger is the confirmation provenance.

`deferred` is ledger-only and does not mutate canonical opinion.

Fresh reassessment rating/reaction/feedback signals use explicit provenance. The pilot does not infer semantic traits from reactions and never writes `set_semantic_fingerprint`.

## Taste reanalysis cadence

Scheduled inferred-hypothesis replacement is not run after every work or every session. It is due after **15 newly reviewed works** since the previous scheduled pilot reanalysis and once at the end of the main `pending` pass if reviewed evidence advanced.

The end-of-main-pass trigger is one-shot. Once a `deferred`-phase session has started, later deferred sessions return to the normal 15-new-review cadence rather than retriggering end-of-main reanalysis after every reviewed item.

The persistent `scheduled_reanalysis.last_completed.reviewed_count` in the ledger is the cadence source. A user-requested manual taste reanalysis does not reset this scheduled pilot counter.

When scheduled reanalysis is due, `close_reassessment_session` requires provenance for a successful `set_inferred_preferences` operation targeting `primary` before it advances the cadence state.

## Session close and metrics

Every session close records a compact audit snapshot including cumulative reviewed/deferred counts, primary rating-source counts, primary structured-feedback coverage and the current Stage A `canonical_input_digest`.

The pilot ledger is deliberately excluded from the audit input inventory, so changing lifecycle state alone cannot change the intelligence digest.

Expected pilot effects are not regressions by themselves:

- many rating sources move from inferred to explicit;
- direct structured-feedback coverage rises;
- generated profiles and affinities may drift because direct evidence replaced weaker inferred evidence.

Interpret that drift against the frozen Stage A baseline, not against a previous generated profile revision.

## Failure and resume

If reserve has reached `main`, never ask the user to restart the whole session merely because a later write failed. Re-read `reassessment-context` and resume `in_progress` work.

If a reservation or completion PR is stale because the ledger or any reserved work changed concurrently, discard/replay it against current `main`. Do not force-merge around the digest guards.

A session cannot close while any of its reserved works remains `in_progress`.

## Activation and completion

PR A installs this foundation but creates no ledger. PR B manually initializes the frozen cohort from the exact Stage A revision, validates it, and activates the pilot.

The main pass is complete when no `pending` or resumable `in_progress` items remain. The deferred pass is complete when every remaining deferred item has been revisited in a `deferred`-phase session and the user either reviewed it or explicitly left it unresolved for this pilot epoch. At that point `pilot_status` may become `completed` even if some deliberately unresolved items still have lifecycle status `deferred`.

The ledger remains intact for Stage B benchmark construction; it is not deleted merely because reassessment conversations are finished.
