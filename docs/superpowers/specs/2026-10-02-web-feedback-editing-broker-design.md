# Web Feedback Editing Broker Design

## Goal

Allow the single repository owner to edit a film/show rating, reaction, or text feedback directly from the existing GitHub Pages site while preserving the repository's current safety model:

- Git/YAML remains canonical;
- the browser never receives GitHub write credentials;
- every write goes through the existing typed `record_viewing_feedback` command path;
- existing `Media Command -> Media Check -> Media Auto Merge -> Media Pages` automation remains the only path from a user edit to published canonical data.

Success means the owner can open a work detail page, authenticate with GitHub, change the selected target's rating/reaction/feedback summary, submit it, observe the operation progress, and eventually see the new canonical value on the detail and history pages without manual repository work.

## Current architecture and constraints

The production web app is a static React/Vite application deployed to GitHub Pages. Its manifest is derived from canonical media YAML and is intentionally read-only.

The repository already has the protected write path needed for this feature:

- `record_viewing_feedback` is a strict typed command;
- operation branches must use the `media/op-*` prefix;
- an operation PR must initially contain exactly one `.media/requests/*.json` request;
- `media-command.yml` replays the branch onto current `main`, applies the semantic request, enforces changed-path policy, verifies the repository, commits the result, and dispatches `Media Check`;
- `Media Auto Merge` merges only verified normal data-operation PRs;
- `Media Pages` publishes the resulting main-branch state.

The web feature must reuse this machinery rather than writing canonical YAML, generated artifacts, or operation receipts itself.

## Chosen architecture

Add a small protected serverless broker between the static site and GitHub:

`GitHub Pages -> Cloudflare Worker broker -> GitHub App -> media/op-* PR -> existing repository automation -> GitHub Pages`

The broker has two responsibilities only:

1. authenticate the one allowed owner;
2. translate a narrow web edit request into one valid repository operation PR and report that operation's status.

The broker does not apply media mutations itself. It never edits `media/data/works/*.yaml`, `media/generated/**`, `.media/operations/**`, schemas, workflow files, vocabulary, or service code.

### Hosting choice

Use a Cloudflare Worker written in TypeScript under a dedicated repository directory (planned as `broker/`). No application framework is required unless implementation demonstrates a concrete need.

Use one GitHub App for both:

- GitHub user authorization, to prove who is using the edit UI;
- installation authentication, to perform the broker's narrow repository operations.

The GitHub App is installed only on `MrDragon13/ChatGPT-lib`.

Required repository permissions are kept minimal:

- Metadata: read;
- Contents: write;
- Pull requests: write;
- Actions: read.

No workflow-write permission is required because the broker never modifies workflows.

## Authentication and authorization

Only one GitHub account may use the write UI.

### Login flow

1. The frontend opens the broker's GitHub login endpoint in a popup.
2. The broker creates an OAuth `state` value and PKCE verifier/challenge.
3. The broker stores the callback-verification material in a short-lived authenticated cookie on the broker origin with `Secure`, `HttpOnly`, and `SameSite=Lax`; sensitive verifier material must not be exposed to frontend JavaScript, and no KV/D1 state store is required.
4. GitHub redirects the popup to the broker callback.
5. The broker verifies `state`, exchanges the authorization code server-side, and calls GitHub's authenticated user endpoint.
6. The broker compares the returned numeric GitHub user id with `OWNER_GITHUB_USER_ID`.
7. Any other user receives `403` and no broker session.
8. The broker discards the GitHub user token after identity verification and issues its own short-lived broker session token.
9. The callback page sends that broker token to the opener using `postMessage` with the exact production Pages origin, then closes the popup.
10. The frontend keeps the broker token in memory only. It is not written to `localStorage`, `sessionStorage`, IndexedDB, the URL, or the Pages artifact.

### Broker session

The broker session token is signed by a Worker secret and contains only the minimum claims needed for authorization (owner identity and expiration). Target lifetime is 15 minutes.

Because the broker remains stateless, logout means clearing the in-memory token in the frontend. There is no server-side revocation list; short expiration bounds the lifetime of a leaked broker token.

### GitHub App credentials

The browser never receives:

- GitHub App private key;
- GitHub App client secret;
- installation access token;
- GitHub user access token;
- Worker session-signing secret.

`GITHUB_APP_PRIVATE_KEY`, `GITHUB_APP_CLIENT_SECRET`, and the broker session-signing secret are Worker secrets. GitHub App id, installation id, client id, repository name, and owner GitHub user id may be Worker environment configuration; they are identifiers rather than write credentials.

Installation access tokens are minted server-side only and scoped to the single installed repository.

### Browser boundary

CORS permits only the production Pages origin (`https://mrdragon13.github.io`). The broker also verifies the bearer session on every protected endpoint. CORS is not treated as authentication.

The OAuth callback uses exact-origin `postMessage`; wildcard target origins are forbidden.

The web app must not render feedback using raw HTML and must not introduce `dangerouslySetInnerHTML` for this feature.

### Abuse protection

The broker applies a small rate limit to authentication starts, feedback submissions, and operation-status polling. Limits are intentionally conservative for a single-owner application and are enforced before expensive GitHub API work where possible.

Rate limiting is defense in depth, not an authorization mechanism. A request still needs a valid owner broker session for protected endpoints, and the broker still enforces the fixed repository/action allowlist after rate-limit checks.

The implementation must avoid feedback-text or token values in rate-limit keys. Suitable keys are coarse network/client signals for unauthenticated auth-start protection and the verified owner/session identity for authenticated write/status limits.

## Broker API

The public API is intentionally narrow.

### `GET /v1/auth/start`

Starts the GitHub authorization flow. It is intended for a popup and redirects to GitHub.

### `GET /v1/auth/callback`

Handles the GitHub callback, verifies the owner, issues the short-lived broker session, and returns the small callback page that posts the token to the opener.

### `POST /v1/feedback`

Requires a valid broker bearer token.

Accepted JSON fields:

```json
{
  "work_id": "game-night-2018",
  "target": "primary",
  "rating": 8.5,
  "reaction": "liked",
  "feedback_summary": "Очень удачная комедия."
}
```

All editable fields are optional individually, but at least one of `rating`, `reaction`, or `feedback_summary` must be present.

Semantics:

- omitted field -> leave that canonical component unchanged;
- `rating` -> number `1..10` in `0.5` increments;
- `reaction` -> one of the existing canonical reaction values;
- `feedback_summary` string -> replace the current summary;
- `feedback_summary: null` -> clear the current summary;
- rating deletion is not supported in this version because the existing typed command has no explicit `rating: null` mutation semantic.

The broker never accepts:

- operation id;
- branch name;
- repository path;
- arbitrary command JSON;
- source/confidence overrides;
- timestamps;
- YAML or patch content;
- shell/workflow fields.

For explicit web edits the broker maps values to the existing command contract:

- rating source: `explicit`, confidence: `exact`;
- reaction source: `explicit`, confidence: `exact`;
- feedback object contains only the supplied summary mutation.

The command uses `work_ref: {"id": work_id}` and `create_if_missing: false`.

A syntactically valid target is passed through to the typed command path; configured-target semantics remain authoritative in the existing media service rather than being duplicated in the broker.

Successful submission returns:

```json
{
  "operation_id": "<uuid>",
  "pr_number": 123,
  "status": "submitted"
}
```

### `GET /v1/operations/:operation_id`

Requires a valid broker bearer token.

Returns one normalized state:

- `submitted` — operation branch/request PR exists and command application has not completed;
- `applying` — `Media Command` is running;
- `checking` — command result exists and `Media Check`/auto-merge path is in progress;
- `merged` — the operation PR is merged into `main`, but Pages publication is not yet confirmed;
- `published` — `Media Pages` for the merge commit completed successfully;
- `failed` — a terminal command/check/merge/deploy failure is visible.

For authorized owner responses, the broker may also include safe navigation metadata such as PR number/URL, relevant Actions URL, merge SHA, and a normalized failure reason.

No operation status endpoint is public without the owner broker session.

## Creating the repository operation

For each `POST /v1/feedback`, the broker performs only these GitHub writes:

1. generate a UUID `operation_id` server-side;
2. create branch `media/op-<operation_id>` from the current `main` SHA;
3. create exactly one `.media/requests/<operation_id>.json` file containing the complete typed `record_viewing_feedback` command;
4. open one PR from that branch to `main`.

The broker does not add any second file to the initial operation PR. This preserves the existing `media-command.yml` precondition that the branch contain only the transient request before execution.

The PR title/body may identify the operation and work id, but should not duplicate the full free-text feedback in PR metadata.

### Concurrent edits

Before creating a new operation for the same `work_id` + `target`, the broker checks existing open `media/op-*` operation PRs and their pending request where necessary. If a write for that pair is still active, return `409 active_operation` rather than create competing operations.

This check is advisory concurrency control for UX. Canonical correctness continues to rely on the existing stale-base semantic replay in `Media Command`.

## Stateless operation status

The broker does not add KV, D1, Durable Objects, or another database in v1.

GitHub is the operation journal:

- branch name is derived from `operation_id`;
- the operation PR identifies the branch lifecycle;
- Actions/workflow runs identify command/check progress;
- the merged PR supplies the merge commit SHA;
- `Media Pages` on that merge SHA determines publication.

`GET /v1/operations/:id` reconstructs status from those GitHub resources. A merged branch may later be deleted without losing status because the merged PR remains queryable.

## Web UX

### Entry point

Replace the current `Режим только для чтения` boundary on the work detail page with an edit action for the active target.

Primary label: **«Изменить впечатление»**.

If no broker session exists, activating the action starts GitHub login. After successful login, the edit panel opens without requiring the user to navigate away from the work.

### Target behavior

The existing target switcher remains authoritative for whose signal is being edited:

- `primary` -> the owner's viewer signal;
- `partner` -> the partner viewer signal;
- a group such as `couple` -> that group signal.

Authentication answers **who is allowed to write**; the target answers **which canonical signal is being edited**. The sole authorized owner may edit any currently selected configured target.

### Edit panel

The panel is prefilled from the currently published manifest and offers only:

- rating: `1..10`, step `0.5`;
- reaction: existing reaction vocabulary, including `unknown`;
- text feedback summary: editable text, with an explicit clear action.

Viewing status is out of scope for this release.

The save button is disabled until at least one value differs from the published state.

### Pending operation UX

The frontend does not optimistically overwrite canonical values in the work model.

After submission it displays a separate pending-operation state, for example:

- `Изменение отправлено`;
- `Применяется`;
- `Проверяется`;
- `Смержено, публикуется`;
- `Опубликовано`;
- `Не удалось применить`.

The pending card may show the submitted rating/reaction/summary as a proposed change, visually distinct from the still-published canonical value.

When status becomes `published`, the client reloads the manifest using a cache-busting revision/query value and rebuilds the detail/history view from that fresh canonical data. The pending state disappears only after the refreshed manifest reflects the submitted result or a later canonical result.

### History page

No inline history editing is added in v1. Existing history items continue to link to work detail; editing happens in the one shared detail write flow.

After a published feedback change, existing history timestamp semantics move the changed work according to the service-generated history event.

### Read-only degradation

If the broker is unreachable or authentication fails, all existing pages remain usable for reading. Only the edit action becomes unavailable or shows a concise error state.

## Error model

HTTP-level broker responses:

- `401` — missing/expired broker session; frontend offers GitHub login again;
- `403` — authenticated GitHub user is not the configured owner;
- `409 active_operation` — another write for the same work/target is still active;
- `422` — malformed or unsupported edit payload;
- `429` — rate limit exceeded; frontend pauses/reduces retries and shows a concise temporary-limit state;
- `502/503` — temporary upstream GitHub failure.

After PR creation, terminal operation failures are normalized as:

- `command_failed`;
- `check_failed`;
- `merge_failed`;
- `deploy_failed`.

The frontend retains the published canonical state on every failure and offers retry by creating a new operation. It never attempts to reuse or mutate a failed operation branch client-side.

## Observability and privacy

Worker logs may contain:

- request route/method;
- HTTP status;
- `operation_id`;
- PR number;
- GitHub request/correlation id;
- normalized failure category.

Worker logs must not contain:

- broker bearer tokens;
- GitHub user/install tokens;
- App private key or client secret;
- full feedback text;
- raw authorization codes;
- raw OAuth cookies.

PR titles/bodies should not repeat the full feedback summary. The request file necessarily contains the intended canonical feedback and remains transient until `Media Command` removes it; the resulting canonical work YAML contains the applied feedback as it does today.

## Deployment and configuration

### Worker

The broker is deployed independently from the static site with Wrangler/Cloudflare CI.

Public/non-sensitive configuration includes:

- repository owner/name;
- GitHub App id;
- GitHub App client id;
- GitHub App installation id;
- allowed Pages origin;
- owner numeric GitHub user id.

Worker secrets include:

- GitHub App private key;
- GitHub App client secret;
- broker session-signing secret.

The production broker base URL is exposed to the web build as a public configuration value. No write credential is placed in `web/`, Vite env output, GitHub Pages artifacts, or browser storage.

### Rollout order

1. create/install the GitHub App for the single repository;
2. deploy the Worker with secrets and production origin allowlist;
3. verify owner login and a controlled test operation through the real typed-command path;
4. deploy the web edit UI pointing at the verified broker;
5. perform one end-to-end production edit and confirm detail/history reflect the new manifest after Pages deployment.

If the Worker is not configured, the web build must remain valid and readable; edit UI should degrade to read-only rather than block deployment.

## Testing

### Broker unit/contract tests

Cover at least:

- owner GitHub user id -> session issued;
- any other GitHub user id -> `403`;
- invalid/missing OAuth state -> rejected;
- OAuth verification cookie uses `Secure`, `HttpOnly`, and `SameSite=Lax` and expires quickly;
- expired broker session -> `401`;
- CORS does not allow arbitrary origins;
- rate limiting protects auth starts, submissions, and excessive polling without logging feedback/token values;
- rating range and `0.5` increment validation;
- reaction enum validation;
- all edit fields omitted -> `422`;
- arbitrary operation id/branch/path fields -> rejected;
- command mapping always uses `record_viewing_feedback`, `create_if_missing:false`, explicit/exact user signals, and work id reference;
- generated branch/request path follow the exact server-owned templates;
- repository writes are limited to branch + one request file + PR creation;
- same work/target active operation -> `409`;
- status reconstruction covers submitted/applying/checking/merged/published/failed;
- logs/redacted error objects do not contain token or feedback body values.

GitHub HTTP calls are mocked in unit tests; tests do not need production credentials.

### Web unit tests

Cover at least:

- existing read-only detail remains stable without broker configuration;
- unauthenticated edit action starts login;
- successful callback message is accepted only from the configured broker origin;
- broker session is kept in memory and not persisted;
- panel is prefilled from the active target's current signal;
- only changed fields are submitted;
- rating/reaction mapping and summary clearing are correct;
- save is disabled for a no-op;
- pending operation does not replace published canonical values;
- failed operation preserves published values;
- published status triggers cache-busted manifest refresh;
- `429` status polling/submission backs off instead of hammering the broker.

### Browser tests

Playwright uses a mocked broker to cover:

- login -> edit -> submit -> progress -> published;
- expired session -> relogin;
- mobile edit-panel usability;
- keyboard/focus behavior and accessible labels;
- reduced-motion behavior;
- broker unavailable -> read-only site still works.

### Repository integration checks

The existing media command/workflow tests remain authoritative for canonical mutation behavior. Add contract tests as needed to pin any assumptions the broker depends on, especially:

- initial operation PR may contain only one request file;
- `record_viewing_feedback` remains auto-merge eligible;
- first/subsequent feedback changes append service-owned history events;
- no-op commands do not create a second semantic effect;
- operation allowlists cannot touch architecture/schema/workflow paths.

Final verification includes the full Python/media checks, web unit/type/build/static/e2e checks, broker tests/build, and one controlled end-to-end operation before declaring production editing available.

## Compatibility

- Existing canonical YAML and manifest format remain valid.
- No schema migration is required for rating/reaction/feedback editing.
- Existing history ordering continues to use service-owned mutation history.
- Existing CLI/ChatGPT command workflows continue to work unchanged.
- The site remains publicly readable exactly as before unless repository visibility/site policy is changed separately.

## Out of scope

- partner login or multiple writer accounts;
- role/permission management UI;
- editing viewing status;
- deleting a rating component;
- inline editing directly in the History list;
- editing feedback term/signals individually;
- arbitrary YAML or repository file editing from the browser;
- adding works from the website;
- editing interest state from the website;
- a second broker database/KV store;
- long-lived browser sessions or refresh-token persistence;
- realtime push/WebSocket status updates; polling is sufficient for this scale;
- bypassing PR/CI/auto-merge for faster writes.
