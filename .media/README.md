# Media operation transport

`.media/requests/*.json` files are transient typed requests used only to hand a normal media mutation to the trusted GitHub Actions runner. They are not canonical media data and are deleted by the command workflow after successful application.

`.media/operations/*.json` receipts are technical idempotency/audit records. A data-operation PR starts from current `main`, uses a same-repository `media/op-*` branch, and initially contains exactly one request file. The workflow replays the branch on current `main`, runs the deterministic Python service, verifies an operation-specific path allowlist, removes the request, runs the complete integrity gate, and commits the resulting data/generated/receipt changes back to that PR branch.

The automatic pull-request `Media Check` is skipped for request-only `media/op-*` branches. After the command result is committed and pushed, `Media Command` dispatches the read-only check for that exact new head SHA.

No model inference runs in GitHub Actions. `TMDB_READ_TOKEN` is exposed only to the provider-dependent apply step: `add_work`, or `record_viewing_feedback` with `create_if_missing: true`. Ordinary existing-work mutations run without the secret, and fork PRs are rejected before any secret-bearing step.
