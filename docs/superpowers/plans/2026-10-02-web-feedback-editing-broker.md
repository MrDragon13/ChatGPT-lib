# Web Feedback Editing Broker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the single repository owner edit rating, reaction, and text feedback from the existing GitHub Pages work-detail page through a protected GitHub App/Cloudflare Worker broker while preserving Git/YAML as the only canonical source of truth.

**Architecture:** Add a small stateless TypeScript Cloudflare Worker under `broker/`. It authenticates one GitHub user, translates narrow web edit payloads into existing `record_viewing_feedback` operation PRs, and reconstructs operation status from GitHub; the React site keeps the broker session only in memory and refreshes the canonical manifest after publication. Existing `Media Command -> Media Check -> Media Auto Merge -> Media Pages` remains the mutation/publication path.

**Tech Stack:** Cloudflare Workers TypeScript, Wrangler >= 4.36, WebCrypto, `@cloudflare/vitest-plugin` + Vitest 5, GitHub App REST APIs, React 19/Vite 8/TypeScript 7, existing Vitest/Testing Library/Playwright web stack, existing Python media tooling and GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-02-web-feedback-editing-broker-design.md`

## Global Constraints

- Git/YAML remains canonical; the broker never edits canonical/generated media files directly.
- Browser code never receives GitHub user tokens, installation tokens, App private keys/client secrets, or Worker signing secrets.
- Only numeric `OWNER_GITHUB_USER_ID` may receive a broker session.
- The GitHub App is installed only on `MrDragon13/ChatGPT-lib` with Metadata read, Contents write, Pull requests write, and Actions read.
- Every edit becomes one server-generated UUID, one `media/op-<uuid>` branch, one `.media/requests/<uuid>.json`, and one PR to `main`.
- Broker input accepts only `work_id`, `target`, and changed `rating`/`reaction`/`feedback_summary`; it never accepts operation ids, refs, paths, patches, arbitrary command JSON, source/confidence, or timestamps.
- `record_viewing_feedback` uses `work_ref.id`, `create_if_missing:false`, and explicit/exact source/confidence for web-entered rating/reaction.
- Rating is `1..10` in `0.5` increments; rating deletion and viewing-status editing are out of scope.
- Feedback summary string replaces the summary; `null` clears it; omitted fields remain unchanged.
- Broker session lifetime is 15 minutes and the frontend stores it in memory only.
- OAuth uses random `state`, PKCE S256, exact-origin `postMessage`, and short-lived `Secure; HttpOnly; SameSite=Lax` callback cookie material.
- CORS allows only `https://mrdragon13.github.io`; CORS is never authentication.
- Use Cloudflare Rate Limiting bindings for auth/write endpoints; no KV/D1/Durable Object database is introduced.
- If broker configuration/service is unavailable, all existing reading behavior still works and editing degrades to read-only.
- No full feedback text or credentials may appear in Worker logs or PR title/body.

## Review Focus

1. **Replay/double-submit:** two clicks or retried requests must not create competing writes for the same work/target; Tasks 4 and 7 pin `409 active_operation` and submit locking.
2. **Popup spoofing:** messages from the wrong origin/source or invalid OAuth state must never install a session; Tasks 2 and 6 pin exact checks.
3. **Partial GitHub failure:** branch creation may succeed while request/PR creation fails; Task 3 pins cleanup-or-terminal-error behavior without false success.
4. **Publication race/cache:** merged is not published until the exact merge SHA has successful `Media Pages`, then the refreshed manifest must reflect canonical data; Tasks 4 and 7 pin this.
5. **Missing production configuration:** absent broker URL/secrets must leave Pages readable and must not cause broker deployment to masquerade as configured; Tasks 5, 6, and 8 pin this.

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
- Produces `BrokerEnv`, `FeedbackInput`, `parseFeedbackInput(value: unknown): FeedbackInput`, `jsonResponse(...)`, `corsHeaders(origin, env)`, and Worker `fetch(request, env)`.
- `BrokerEnv` contains repository/App identifiers, `OWNER_GITHUB_USER_ID`, `ALLOWED_ORIGIN`, secret bindings, and `AUTH_RATE_LIMITER`/`WRITE_RATE_LIMITER`.

- [ ] **Step 1: Scaffold the Worker package with pinned lockfile**

Use ES modules and scripts `test`, `test:run`, `typecheck`, `deploy`, `types`. Install Wrangler >=4.36, TypeScript, Vitest 5, and `@cloudflare/vitest-plugin`; configure `cloudflareTest()` against `wrangler.jsonc`.

- [ ] **Step 2: Write failing payload/CORS/router tests**

Assert valid `8.5/liked/summary` parses; `8.3`, out-of-range rating, unsupported reaction, empty mutation, unknown fields (`branch`, `operation_id`), invalid/oversized JSON return `422`; allowed origin gets CORS and arbitrary origin does not; unknown route is `404`.

- [ ] **Step 3: Run RED**

Run: `cd broker && npm run test:run -- feedback.test.ts http.test.ts`
Expected: FAIL because broker modules do not exist.

- [ ] **Step 4: Implement the minimal contract/router**

`parseFeedbackInput()` must distinguish omitted fields from explicit `null`; limit feedback summary to 8 KiB and total JSON body to 16 KiB. Later routes may return `501` until their task.

- [ ] **Step 5: Run GREEN/typecheck**

Run: `cd broker && npm run test:run && npm run typecheck`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add broker
git commit -m "feat: scaffold feedback broker"
```

---

### Task 2: Owner-only GitHub OAuth, PKCE, and broker session

**Files:**
- Create: `broker/src/crypto.ts`
- Create: `broker/src/auth.ts`
- Modify: `broker/src/index.ts`
- Test: `broker/test/auth.test.ts`

**Interfaces:**
- Produces `startAuth(request, env): Promise<Response>`, `finishAuth(request, env): Promise<Response>`, `issueSession(ownerId, env, now?): Promise<string>`, `verifySession(token, env, now?): Promise<SessionClaims>`.
- OAuth transient cookie lasts <=10 minutes and uses `Secure; HttpOnly; SameSite=Lax; Path=/v1/auth/callback`; bearer session lasts 15 minutes.

- [ ] **Step 1: Write failing auth/security tests**

Assert auth start includes random `state`, PKCE S256 and configured client/callback; missing/tampered state/cookie fails; matching numeric owner id yields callback/session; any other user is `403`; callback HTML `postMessage`s only to exact `ALLOWED_ORIGIN`; session expires after 15 minutes; credentials/raw code are absent from error/log data.

- [ ] **Step 2: Run RED**

Run: `cd broker && npm run test:run -- auth.test.ts`
Expected: FAIL because auth helpers do not exist.

- [ ] **Step 3: Implement OAuth/session with WebCrypto**

Use SHA-256 for PKCE and HMAC-SHA256 for signed transient/session tokens. Exchange GitHub code server-side, call `/user`, compare numeric id, discard the GitHub user token, and return only broker session to opener.

- [ ] **Step 4: Add auth rate limiting**

Call `AUTH_RATE_LIMITER.limit(...)` before GitHub exchange; return `429` on exhaustion without upstream request. Do not use raw bearer tokens as limiter keys.

- [ ] **Step 5: Run GREEN and commit**

Run: `cd broker && npm run test:run -- auth.test.ts && npm run typecheck`

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
- Produces `mintInstallationToken(env): Promise<string>`, `submitFeedback(input, env): Promise<SubmittedOperation>`, and exact `FeedbackCommand` mapping.
- `SubmittedOperation = {operation_id: string; pr_number: number; status: "submitted"}`.
- GitHub writes are limited to new `media/op-<uuid>` ref, one `.media/requests/<uuid>.json`, and one PR to `main`.

- [ ] **Step 1: Pin repository assumptions in Python workflow tests**

Assert `record_viewing_feedback` remains auto-merge eligible and `media-command.yml` still requires exactly one transient request file before execution.

- [ ] **Step 2: Write failing GitHub/submission tests**

Assert branch starts from current `main`; request maps only changed fields to `record_viewing_feedback`; sources are explicit/exact; `create_if_missing:false`; no second initial file; PR targets `main`; feedback text absent from PR title/body; install token never reaches response/log surface.

- [ ] **Step 3: Add partial-failure tests**

If request-file creation fails after branch creation, attempt to delete that new ref. If PR creation fails, never return `submitted`. Cleanup failure returns normalized upstream error without pretending success.

- [ ] **Step 4: Run RED**

Run:
```bash
python -m pytest tests/media/test_workflows.py -q
cd broker && npm run test:run -- github.test.ts submit.test.ts
```
Expected: broker tests fail because GitHub operation modules do not exist.

- [ ] **Step 5: Implement GitHub App JWT/install-token and operation creation**

Use WebCrypto RS256 and GitHub REST `fetch`; no generic GitHub proxy. Mint installation access for only the configured repository/required permissions.

- [ ] **Step 6: Wire `POST /v1/feedback`**

Verify session, enforce `WRITE_RATE_LIMITER`, parse payload, then submit. Normalize `401`, `422`, `429`, `502`, `503`.

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

### Task 4: Conflict detection and stateless status reconstruction

**Files:**
- Modify: `broker/src/github.ts`
- Modify: `broker/src/operations.ts`
- Modify: `broker/src/index.ts`
- Test: `broker/test/status.test.ts`
- Test: `broker/test/submit.test.ts`

**Interfaces:**
- Produces `findActiveOperation(workId, target, env): Promise<ActiveOperation | null>` and `getOperationStatus(operationId, env): Promise<OperationStatusResponse>`.
- Status: `submitted | applying | checking | merged | published | failed`; failures: `command_failed | check_failed | merge_failed | deploy_failed`.

- [ ] **Step 1: Write failing conflict/status tests**

Assert active same work/target -> `409`; unrelated pair may submit; PR-before-command -> `submitted`; Media Command running -> `applying`; command applied + checks/merge pending -> `checking`; merged -> `merged`; exact merge SHA with successful `Media Pages` -> `published`; terminal failures map correctly.

- [ ] **Step 2: Add publication-race tests**

Older successful Pages SHA cannot publish this operation; queued/in-progress Pages for merge SHA remains `merged`; only exact-SHA `success` is `published`.

- [ ] **Step 3: Run RED**

Run: `cd broker && npm run test:run -- status.test.ts submit.test.ts`
Expected: FAIL because status/conflict logic is absent.

- [ ] **Step 4: Implement GitHub-journal queries**

Inspect only broker-shaped `media/op-*` PRs and request/operation marker contents as needed; never infer work/target from PR title. Status endpoint is owner-authenticated and read-only.

- [ ] **Step 5: Run GREEN and commit**

Run: `cd broker && npm run test:run && npm run typecheck`

```bash
git add broker/src broker/test
git commit -m "feat: report feedback operation status"
```

---

### Task 5: Broker CI, deploy contract, redaction, and provisioning docs

**Files:**
- Create: `.github/workflows/broker-check.yml`
- Create: `.github/workflows/broker-deploy.yml`
- Create: `broker/README.md`
- Create: `broker/src/logging.ts`
- Modify: `tests/media/test_workflows.py`
- Test: `broker/test/logging.test.ts`

**Interfaces:**
- `broker-check.yml` runs `npm ci`, tests, and typecheck on broker changes with no production secrets.
- `broker-deploy.yml` is explicit `workflow_dispatch` and deploys the checked `main` revision using Cloudflare deployment credentials; it does not fire automatically before provisioning.

- [ ] **Step 1: Write failing redaction/workflow tests**

Assert log helper removes Authorization/OAuth cookie+code/GitHub tokens/App secrets/feedback text; workflows never echo secrets; broker deploy is manual and constrained to `main`; Pages remains independent of broker secrets.

- [ ] **Step 2: Run RED**

Run:
```bash
python -m pytest tests/media/test_workflows.py -q
cd broker && npm run test:run -- logging.test.ts
```
Expected: FAIL until logging/workflows exist.

- [ ] **Step 3: Implement safe logging and workflows**

Allowed log fields: route, HTTP status, operation id, PR number, GitHub request id, normalized failure category. Broker check uses Node 22.22.2+; deploy runs `wrangler deploy` from an explicitly selected `main` SHA/ref.

- [ ] **Step 4: Document external provisioning exactly**

`broker/README.md` lists GitHub App callback URL, single-repository installation, exact permissions, Worker vars/secrets, two rate-limit namespace ids, `wrangler secret put` commands, Cloudflare deploy credentials required by GitHub Actions, and public repository variable `MEDIA_BROKER_URL`. Never commit secret values.

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
- Produces `useBrokerSession()`, `submitFeedback(...)`, `getOperationStatus(...)`, optional `brokerBaseUrl()`.
- Session provider owns the token only in React memory and handles popup login/callback.
- Public Vite config is `VITE_MEDIA_BROKER_URL`; absent/empty means read-only mode.

- [ ] **Step 1: Write failing client/session tests**

Assert absent URL => app renders/read-only; login popup uses `/v1/auth/start`; callback accepted only when `event.origin` equals broker origin and `event.source` equals opened popup; malformed/foreign message ignored; token never reaches local/session storage; `401` clears session and permits relogin; local logout clears memory token only.

- [ ] **Step 2: Write Pages workflow contract test**

Assert `media-pages.yml` may pass `${{ vars.MEDIA_BROKER_URL }}` as `VITE_MEDIA_BROKER_URL`, never includes broker/GitHub write secrets, and still builds when variable is absent.

- [ ] **Step 3: Run RED**

Run:
```bash
python -m pytest tests/media/test_pages_contract.py -q
cd web && npm run test:run -- src/broker/client.test.ts src/broker/session.test.tsx
```
Expected: FAIL because broker client/session does not exist.

- [ ] **Step 4: Implement client/provider and wrap the app**

Use bearer token only on broker calls. Keep token in component/ref state; no local/session storage, URL, service worker, or manifest serialization.

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

### Task 7: Work-detail editor, polling, and canonical manifest refresh

**Files:**
- Create: `web/src/features/detail/FeedbackEditor.tsx`
- Create: `web/src/features/detail/feedback-editor.test.tsx`
- Create: `web/e2e/edit-feedback.spec.ts`
- Modify: `web/src/features/detail/WorkDetailPage.tsx`
- Modify: `web/src/features/detail/detail.css`
- Modify: `web/src/data/client.ts`
- Modify: `web/src/app/AppShell.tsx`
- Modify: `web/src/features/detail/detail.test.tsx`

**Interfaces:**
- `FeedbackEditor` consumes work id, active target, current `DetailSignal | null`, broker session/client, and `refreshManifest()`.
- `AppContextValue` gains `refreshManifest(cacheBust?: string): Promise<void>`.
- `loadManifest(cacheBust?: string): Promise<WebManifest>` appends cache-busting query only when requested.

- [ ] **Step 1: Write failing editor tests**

Assert active-target values prefill; only changed fields submit; rating range/step enforced; clear sends `feedback_summary:null`; no-op disables save; no viewing-status control; unauthenticated edit starts login; submit locks against double click; `409` renders active-operation state.

- [ ] **Step 2: Write failing pending/published tests**

Published canonical values stay visible while proposed values are pending; all status labels render; failure preserves canonical values; `published` triggers cache-busted manifest refresh; pending clears only after fresh manifest reflects submitted or later canonical state.

- [ ] **Step 3: Run RED**

Run: `cd web && npm run test:run -- src/features/detail/feedback-editor.test.tsx src/features/detail/detail.test.tsx`
Expected: FAIL because editor/refresh flow is absent.

- [ ] **Step 4: Implement editor and replace read-only boundary**

Keep editing only on detail. Reuse current Russian visual system, semantic form controls, focus management, and reduced-motion rules. Never render feedback as raw HTML.

- [ ] **Step 5: Implement bounded polling/refresh**

Poll only while mounted using modest interval/backoff; stop on `published`, `failed`, unmount, or session expiry. On `published`, call `refreshManifest(operation_id)` and rebuild views from canonical manifest.

- [ ] **Step 6: Add Playwright mocked-broker flow**

`web/e2e/edit-feedback.spec.ts` covers login -> edit -> submit -> progress -> published, expired session -> relogin, mobile usability, keyboard/a11y, reduced motion, and broker-unavailable read-only degradation.

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
- Modify only if verification reveals a real defect; no new feature scope.

**Interfaces:**
- Confirms code is releasable before external GitHub App/Cloudflare provisioning and before claiming editing is live.

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

Verify `web/dist` and broker source/config contain no App private key/client secret, user/install token, signing secret, authorization code, or bearer token. Public broker URL/client/app/install/user ids and origin are allowed where intended.

- [ ] **Step 3: Verify degradation/failure behavior**

Run broker tests with GitHub failures and web tests with missing/unavailable broker; reading must remain functional and no optimistic canonical overwrite may occur.

- [ ] **Step 4: Commit defect-only fixes and rerun affected full gates**

Do not weaken tests or security boundaries to make CI pass.

- [ ] **Step 5: External production provisioning gate**

Before claiming production editing live, the owner must create/install the GitHub App and configure Cloudflare/GitHub secrets/variables from `broker/README.md`. Then manually run `broker-deploy.yml`, set repository variable `MEDIA_BROKER_URL`, and verify owner login. Code/CI alone cannot satisfy this gate.

- [ ] **Step 6: Controlled production operation**

From production, change one known work signal, record operation id, verify initial operation PR contains only request, observe Media Command -> Media Check -> auto-merge -> exact-SHA Media Pages success, then confirm fresh detail and History display canonical change.

- [ ] **Step 7: Final review/merge**

Review whole diff against approved spec, ensure no Critical/Important findings remain, merge only verified head SHA, and confirm post-merge checks. Production activation remains a separate explicit gate if external credentials are not yet configured.
