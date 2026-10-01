# Web Feedback Editing Broker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the single repository owner edit rating, reaction, and text feedback from the existing GitHub Pages work-detail page through a protected GitHub App/Cloudflare Worker broker while preserving Git/YAML as the only canonical source of truth.

**Architecture:** Add a small stateless TypeScript Cloudflare Worker under `broker/`. It authenticates one GitHub user, translates narrow web edit payloads into existing `record_viewing_feedback` operation PRs, and reconstructs operation status from GitHub; the React site keeps the broker session only in memory and refreshes the canonical manifest after publication. Existing `Media Command -> Media Check -> Media Auto Merge -> Media Pages` remains the mutation/publication path.

**Tech Stack:** Cloudflare Workers TypeScript, Wrangler >= 4.36, WebCrypto, `@cloudflare/vitest-plugin` + Vitest 5, GitHub App REST APIs, React 19/Vite 8/TypeScript 7, existing Vitest/Testing Library/Playwright web stack, existing Python media tooling and GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-02-web-feedback-editing-broker-design.md`

## Global Constraints

- Git/YAML remains canonical; the broker never edits canonical/generated media files directly.
- Browser code never receives GitHub user tokens, installation tokens, App private keys/client secrets, or Worker signing secrets.
- Only the configured numeric `OWNER_GITHUB_USER_ID` may receive a broker session.
- The GitHub App is installed only on `MrDragon13/ChatGPT-lib` with Metadata read, Contents write, Pull requests write, and Actions read.
- Every edit becomes one server-generated UUID, one `media/op-<uuid>` branch, one `.media/requests/<uuid>.json` file, and one PR to `main`.
- Broker input accepts only `work_id`, `target`, and changed `rating`/`reaction`/`feedback_summary`; it never accepts operation ids, refs, paths, patches, command JSON, source/confidence, or timestamps.
- `record_viewing_feedback` uses `work_ref.id`, `create_if_missing:false`, and explicit/exact source/confidence for web-entered rating/reaction.
- Rating is `1..10` in `0.5` increments; rating deletion and viewing-status editing are out of scope.
- Feedback summary string replaces the summary; `null` clears it; omitted fields remain unchanged.
- Broker session lifetime is 15 minutes and the frontend stores it in memory only.
- OAuth uses random `state`, PKCE S256, exact-origin `postMessage`, and short-lived `Secure; HttpOnly; SameSite=Lax` callback cookie material.
- CORS allows only `https://mrdragon13.github.io`; CORS is never treated as authentication.
- Use Cloudflare Rate Limiting bindings for auth/write endpoints; no KV/D1/Durable Object database is introduced.
- If broker configuration/service is unavailable, all existing reading behavior still works and editing degrades to read-only.
- No full feedback text or credentials may be written to Worker logs or PR title/body.

## Review Focus

1. **Replay/double-submit:** two clicks or retried HTTP requests must not create competing writes for the same work/target; Task 4 pins `409 active_operation` and client submit locking.
2. **Popup spoofing:** messages from the wrong origin/source or wrong state must never install a session; Tasks 2 and 6 pin exact-origin/source/state checks.
3. **Partial GitHub failure:** branch creation may succeed while request/PR creation fails; Task 3 pins cleanup-or-terminal-error behavior without pretending submission succeeded.
4. **Publication race/cache:** a merged operation is not `published` until the exact merge SHA has a successful `Media Pages` run and the refreshed manifest reflects canonical data; Tasks 4 and 7 pin this.
5. **Missing production configuration:** absent broker URL/secrets/repository variables must leave Pages readable and make deploy/check failures explicit rather than leaking credentials or breaking the site; Tasks 5, 6, and 8 pin this.

---

### Task 1: Broker project foundation and narrow HTTP contract

**Files:**
- Create: `broker/package.json`
- Create: `broker/package-lock.json`
- Create: `broker/tsconfig.json`
- Create: `broker/wrangler.jsonc`
- Create: `broker/vitest.config.ts`
- Create: `broker/src/env.ts`
- Create: `broker/src/http.ts`
- Create: `broker/src/feedback.ts`
- Create: `broker/src/index.ts`
- Test: `broker/test/feedback.test.ts`
- Test: `broker/test/http.test.ts`

**Interfaces:**
- Produces `BrokerEnv`, `FeedbackInput`, `parseFeedbackInput(value: unknown): FeedbackInput`, `jsonResponse(...)`, `corsHeaders(origin, env)`, and the Worker `fetch(request, env)` router.
- `BrokerEnv` contains public config (`REPO_OWNER`, `REPO_NAME`, `GITHUB_APP_ID`, `GITHUB_APP_CLIENT_ID`, `GITHUB_APP_INSTALLATION_ID`, `OWNER_GITHUB_USER_ID`, `ALLOWED_ORIGIN`) plus secrets and two `RateLimit` bindings.

- [ ] **Step 1: Scaffold the Worker package with pinned lockfile**

Use ES modules and scripts: `test`, `test:run`, `typecheck`, `deploy`, `types`. Install `wrangler` (>=4.36), TypeScript, Vitest 5, and `@cloudflare/vitest-plugin`; configure `cloudflareTest()` against `wrangler.jsonc`.

- [ ] **Step 2: Write failing payload/CORS/router tests**

Tests assert: valid 8.5/liked/summary parses; `8.3`, rating `0/11`, unsupported reaction, empty mutation, unknown fields such as `branch`/`operation_id`, and oversized/invalid JSON return `422`; allowed origin gets CORS headers and arbitrary origins do not; unknown route is `404`.

- [ ] **Step 3: Run RED**

Run: `cd broker && npm run test:run -- feedback.test.ts http.test.ts`
Expected: FAIL because broker modules do not exist.

- [ ] **Step 4: Implement the minimal contract and router**

`parseFeedbackInput()` accepts only the spec fields and returns changed-field presence distinctly from value. Limit feedback summary request size to 8 KiB and total JSON body to 16 KiB. Route placeholders may return `501` until later tasks; all responses use JSON except OAuth redirects/callback HTML.

- [ ] **Step 5: Run GREEN and typecheck**

Run: `cd broker && npm run test:run && npm run typecheck`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add broker
git commit -m "feat: scaffold feedback broker"
```

---

### Task 2: Owner-only GitHub OAuth, PKCE, and in-memory broker session contract

**Files:**
- Create: `broker/src/crypto.ts`
- Create: `broker/src/auth.ts`
- Modify: `broker/src/index.ts`
- Test: `broker/test/auth.test.ts`

**Interfaces:**
- Produces `startAuth(request, env): Promise<Response>`, `finishAuth(request, env): Promise<Response>`, `issueSession(ownerId, env, now?): Promise<string>`, `verifySession(token, env, now?): Promise<SessionClaims>`.
- OAuth transient cookie stores signed state/PKCE verifier for at most 10 minutes with `Secure; HttpOnly; SameSite=Lax; Path=/v1/auth/callback`.
- Broker bearer session expires after 15 minutes.

- [ ] **Step 1: Write failing auth/security tests**

Pin: auth start includes `state`, PKCE `code_challenge_method=S256`, configured client id/callback; invalid/missing/tampered cookie/state is rejected; GitHub identity equal to `OWNER_GITHUB_USER_ID` yields callback HTML/session; any other id yields `403`; callback page uses exact `ALLOWED_ORIGIN` in `postMessage`; token expires at 15 minutes; credentials/raw code are absent from errors/loggable objects.

- [ ] **Step 2: Run RED**

Run: `cd broker && npm run test:run -- auth.test.ts`
Expected: FAIL because auth helpers do not exist.

- [ ] **Step 3: Implement WebCrypto helpers and OAuth flow**

Use WebCrypto SHA-256 for PKCE and HMAC-SHA256 for signed transient/session tokens. Exchange the authorization code server-side, call GitHub `/user`, compare numeric user id, discard the GitHub user token after identity verification, and return only the broker token to the opener.

- [ ] **Step 4: Add rate limiting to auth endpoints**

Use `AUTH_RATE_LIMITER.limit({key: route + owner-class})`; on exhaustion return `429` without contacting GitHub. Keep rate-limit keys free of raw bearer tokens.

- [ ] **Step 5: Run GREEN**

Run: `cd broker && npm run test:run -- auth.test.ts && npm run typecheck`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add broker/src broker/test
git commit -m "feat: add owner github authentication"
```

---

### Task 3: GitHub App installation client and safe operation submission

**Files:**
- Create: `broker/src/github.ts`
- Create: `broker/src/operations.ts`
- Modify: `broker/src/index.ts`
- Test: `broker/test/github.test.ts`
- Test: `broker/test/submit.test.ts`
- Modify: `tests/media/test_workflows.py`

**Interfaces:**
- Produces `mintInstallationToken(env): Promise<string>`, `submitFeedback(input, env): Promise<SubmittedOperation>`, and `FeedbackCommand` mapping.
- `SubmittedOperation = {operation_id: string; pr_number: number; status: "submitted"}`.
- GitHub writes are limited to creating ref `refs/heads/media/op-<uuid>`, creating `.media/requests/<uuid>.json`, and opening a PR to `main`.

- [ ] **Step 1: Pin repository assumptions with failing/updated Python workflow contract tests**

Assert `record_viewing_feedback` remains auto-merge eligible and `media-command.yml` still requires exactly one transient request file before execution.

- [ ] **Step 2: Write failing broker GitHub/submission tests**

Tests assert: App JWT/install token is server-side only and scoped to the configured installation; branch starts from current `main`; request body exactly maps rating/reaction/summary semantics to `record_viewing_feedback`; sources are explicit/exact; `create_if_missing` is false; no second initial file is created; PR targets `main`; feedback text is absent from PR title/body.

- [ ] **Step 3: Add partial-failure tests**

If request-file creation fails after branch creation, broker attempts to delete the new ref; if cleanup also fails, return a terminal `502` with operation id/request id but no success payload. If PR creation fails, do not report `submitted`.

- [ ] **Step 4: Run RED**

Run:
```bash
python -m pytest tests/media/test_workflows.py -q
cd broker && npm run test:run -- github.test.ts submit.test.ts
```
Expected: broker tests fail because GitHub operation modules do not exist.

- [ ] **Step 5: Implement GitHub App JWT/install-token and operation creation**

Use WebCrypto RS256 for the GitHub App JWT and GitHub REST `fetch`; do not add a generic GitHub proxy or arbitrary endpoint passthrough. Request installation access with only the repository/permissions required by the spec.

- [ ] **Step 6: Wire `POST /v1/feedback` behind session + write rate limit**

Verify bearer session first, then `WRITE_RATE_LIMITER` keyed by owner id + route, then parse/submit. Return `401`, `422`, `429`, or normalized upstream `502/503` as appropriate.

- [ ] **Step 7: Run GREEN and commit**

Run:
```bash
python -m pytest tests/media/test_workflows.py -q
cd broker && npm run test:run && npm run typecheck
```

```bash
git add broker tests/media/test_workflows.py
git commit -m "feat: submit typed feedback operations"
```

---

### Task 4: Active-operation conflict detection and stateless status reconstruction

**Files:**
- Modify: `broker/src/github.ts`
- Modify: `broker/src/operations.ts`
- Modify: `broker/src/index.ts`
- Test: `broker/test/status.test.ts`
- Test: `broker/test/submit.test.ts`

**Interfaces:**
- Produces `findActiveOperation(workId, target, env): Promise<ActiveOperation | null>` and `getOperationStatus(operationId, env): Promise<OperationStatusResponse>`.
- Status union: `submitted | applying | checking | merged | published | failed` with normalized failure reason `command_failed | check_failed | merge_failed | deploy_failed`.

- [ ] **Step 1: Write failing conflict/status tests**

Pin: active same work/target -> `409 active_operation`; unrelated target/work may submit; open PR before command -> `submitted`; Media Command running -> `applying`; command applied + Media Check/auto-merge pending -> `checking`; merged PR -> `merged`; exact merge SHA with successful `Media Pages` -> `published`; failed command/check/deploy maps to the specified normalized reason.

- [ ] **Step 2: Add publication-race tests**

A successful Pages run for an older SHA must not publish the operation. A merge SHA with Pages queued/in-progress remains `merged`; only `conclusion=success` for that exact SHA yields `published`.

- [ ] **Step 3: Run RED**

Run: `cd broker && npm run test:run -- status.test.ts submit.test.ts`
Expected: FAIL because status/conflict logic is missing.

- [ ] **Step 4: Implement conflict/status queries using GitHub as the journal**

Search only broker-shaped `media/op-*` PRs. For active-pair detection, inspect the pending request or the applied operation marker as necessary; never infer from PR title text. Status queries are read-only and require a valid broker session.

- [ ] **Step 5: Run GREEN and commit**

Run: `cd broker && npm run test:run && npm run typecheck`

```bash
git add broker/src broker/test
git commit -m "feat: report feedback operation status"
```

---

### Task 5: Broker CI, deployment contract, redaction, and configuration docs

**Files:**
- Create: `.github/workflows/broker-check.yml`
- Create: `.github/workflows/broker-deploy.yml`
- Create: `broker/README.md`
- Modify: `tests/media/test_workflows.py`
- Test: `broker/test/logging.test.ts`

**Interfaces:**
- `broker-check.yml` runs install, broker tests, and typecheck on broker changes without production secrets.
- `broker-deploy.yml` deploys only from `main` after checks and requires Cloudflare deployment credentials via GitHub secrets; Worker runtime secrets remain Cloudflare secrets, not repository files.

- [ ] **Step 1: Write failing redaction/workflow contract tests**

Pin: log helper omits Authorization, OAuth code/cookie, GitHub token, private key/client secret, and feedback text; workflows never echo secrets; deploy runs only from `main`; Pages workflow remains independently deployable without broker secrets.

- [ ] **Step 2: Run RED**

Run:
```bash
python -m pytest tests/media/test_workflows.py -q
cd broker && npm run test:run -- logging.test.ts
```
Expected: FAIL until workflow/logging contracts exist.

- [ ] **Step 3: Implement safe structured logging and workflows**

Logs may include route, HTTP status, operation id, PR number, GitHub request id, and normalized failure category only. Broker check uses Node 22.22.2+ and `npm ci`; deploy uses `wrangler deploy` with Cloudflare API token/account id supplied by GitHub Actions secrets.

- [ ] **Step 4: Document external provisioning exactly**

`broker/README.md` lists GitHub App callback URL, single-repository installation, exact permissions, required Worker vars/secrets, two Rate Limiting binding namespace ids, `wrangler secret put` commands, and the public broker URL/repository variable used by Pages. Do not commit secret values.

- [ ] **Step 5: Run GREEN and commit**

Run:
```bash
python -m pytest tests/media/test_workflows.py -q
cd broker && npm run test:run && npm run typecheck
```

```bash
git add .github/workflows/broker-*.yml broker tests/media/test_workflows.py
git commit -m "ci: add feedback broker checks and deploy"
```

---

### Task 6: Web broker client and memory-only owner session

**Files:**
- Create: `web/src/broker/types.ts`
- Create: `web/src/broker/config.ts`
- Create: `web/src/broker/client.ts`
- Create: `web/src/broker/BrokerSessionProvider.tsx`
- Test: `web/src/broker/client.test.ts`
- Test: `web/src/broker/session.test.tsx`
- Modify: `web/src/main.tsx`
- Modify: `.github/workflows/media-pages.yml`
- Modify: `tests/media/test_pages_contract.py`

**Interfaces:**
- Produces `useBrokerSession()`, `submitFeedback(...)`, `getOperationStatus(...)`, and optional `brokerBaseUrl()`.
- Session provider owns the token in React memory only and handles popup login/callback messages.
- Public Vite config is `VITE_MEDIA_BROKER_URL`; absent/empty means read-only mode.

- [ ] **Step 1: Write failing client/session tests**

Pin: absent broker URL => editing unavailable but app renders; login popup uses broker auth start; callback accepted only when `event.origin` equals broker origin and `event.source` is the opened popup; malformed/foreign message ignored; token is not persisted to browser storage; expired `401` clears the session and allows relogin.

- [ ] **Step 2: Write Pages contract test for public broker config**

Assert `media-pages.yml` may pass `${{ vars.MEDIA_BROKER_URL }}` to Vite build but contains no broker/GitHub write secret and still builds when the variable is absent.

- [ ] **Step 3: Run RED**

Run:
```bash
python -m pytest tests/media/test_pages_contract.py -q
cd web && npm run test:run -- src/broker/client.test.ts src/broker/session.test.tsx
```
Expected: FAIL because broker client/session does not exist.

- [ ] **Step 4: Implement client/provider and wire it around the app**

Use `Authorization: Bearer <broker token>` only for broker calls. Keep token in component/ref state; no local/session storage, URL fragment/query, service worker cache, or manifest serialization.

- [ ] **Step 5: Run GREEN and commit**

Run:
```bash
python -m pytest tests/media/test_pages_contract.py -q
cd web && npm run test:run && npm run typecheck
```

```bash
git add web/src/broker web/src/main.tsx .github/workflows/media-pages.yml tests/media/test_pages_contract.py
git commit -m "feat: add owner broker session client"
```

---

### Task 7: Work-detail feedback editor, polling, and canonical manifest refresh

**Files:**
- Create: `web/src/features/detail/FeedbackEditor.tsx`
- Create: `web/src/features/detail/feedback-editor.test.tsx`
- Modify: `web/src/features/detail/WorkDetailPage.tsx`
- Modify: `web/src/features/detail/detail.css`
- Modify: `web/src/data/client.ts`
- Modify: `web/src/app/AppShell.tsx`
- Modify: `web/src/features/detail/detail.test.tsx`
- Modify: `web/tests/media-pages.spec.ts`

**Interfaces:**
- `FeedbackEditor` consumes work id, active target, current `DetailSignal | null`, broker session/client, and `refreshManifest()`.
- `AppContextValue` gains `refreshManifest(cacheBust?: string): Promise<void>`.
- `loadManifest(cacheBust?: string): Promise<WebManifest>` appends a cache-busting query only when requested.

- [ ] **Step 1: Write failing editor tests**

Pin: current target values prefill; only changed fields are submitted; rating step/range enforced; explicit clear sends `feedback_summary:null`; no-op disables save; viewing status is absent; unauthenticated edit initiates login; submit button locks against double-click while request is in flight; `409` presents active-operation state rather than creating another write.

- [ ] **Step 2: Write failing pending/published tests**

Published canonical values remain visible while proposed values are pending; status labels map to submitted/applying/checking/merged/published/failed; failed operation keeps canonical values; published triggers cache-busted manifest refresh; pending clears only after refreshed manifest reflects the submitted fields or a later canonical state.

- [ ] **Step 3: Run RED**

Run: `cd web && npm run test:run -- src/features/detail/feedback-editor.test.tsx src/features/detail/detail.test.tsx`
Expected: FAIL because editor/refresh flow is missing.

- [ ] **Step 4: Implement the editor and replace the read-only placeholder**

Keep one edit surface on detail only. Use existing Russian visual language/tokens, semantic form controls, keyboard focus management, and reduced-motion behavior. Do not use raw HTML for feedback text.

- [ ] **Step 5: Implement bounded polling and manifest refresh**

Poll operation status while the detail page is mounted using a modest interval/backoff; stop on `published`, `failed`, unmount, or session expiry. After `published`, call `refreshManifest(operation_id)` and rebuild views from canonical manifest data.

- [ ] **Step 6: Extend Playwright mocked-broker coverage**

Cover login -> edit -> submit -> progress -> published, expired session -> relogin, mobile form usability, keyboard/a11y, reduced motion, and broker-unavailable read-only degradation.

- [ ] **Step 7: Run GREEN and commit**

Run:
```bash
cd web
npm run test:run
npm run typecheck
npm run build
npm run scan:dist
npm run test:e2e
```

```bash
git add web
git commit -m "feat: edit feedback from work details"
```

---

### Task 8: Whole-system verification and production activation gate

**Files:**
- Modify only if verification finds a real defect in earlier tasks; no new feature scope.

**Interfaces:**
- Confirms the branch is releasable before GitHub App/Cloudflare production activation.

- [ ] **Step 1: Run full repository verification**

Run:
```bash
python -m pytest -q
python -m media.tools.validate .
python -m media.cli rebuild --check
python -m media.cli doctor --format json
cd broker
npm ci
npm run test:run
npm run typecheck
cd ../web
npm ci
npm run test:run
npm run typecheck
npm run build
npm run scan:dist
npx playwright install --with-deps chromium
npm run test:e2e
```
Expected: every command succeeds.

- [ ] **Step 2: Run secret/static-artifact audit**

Verify generated `web/dist` and broker source/config contain no App private key, client secret, installation/user token, broker signing secret, authorization code, or bearer token. Confirm only the public broker URL/client id/ids/origin may be present where intended.

- [ ] **Step 3: Verify failure/degradation behavior**

Run broker tests with GitHub upstream failures and web tests with missing broker URL/unavailable broker. Confirm reading remains functional and no optimistic canonical overwrite occurs.

- [ ] **Step 4: Commit any verification-only fixes and rerun the affected full gates**

Use defect-specific commits; do not weaken tests or security boundaries to make CI pass.

- [ ] **Step 5: Production provisioning gate**

Before claiming production editing is live, the owner must create/install the GitHub App and configure the Cloudflare/GitHub secrets/variables documented in `broker/README.md`. Then deploy the Worker, set repository variable `MEDIA_BROKER_URL`, and verify owner login. Do not claim this step complete from code/CI alone.

- [ ] **Step 6: Controlled end-to-end production operation**

From the production site, change one known work's rating/reaction/summary, record the returned operation id, verify the generated `media/op-*` PR contains only the request initially, observe `Media Command`, `Media Check`, auto-merge, and exact-SHA `Media Pages` success, then confirm fresh detail and History show the canonical change.

- [ ] **Step 7: Final branch review and merge**

Review the entire diff against the approved spec, ensure no Critical/Important findings remain, merge only the verified head SHA, and confirm post-merge broker/web workflows remain green.
