# Media feedback broker

This Cloudflare Worker is the protected write bridge for the static media site. It authenticates one GitHub owner, creates one typed `record_viewing_feedback` operation PR, and reports that operation's GitHub/Pages status. It never edits canonical media YAML directly.

## 1. Create the GitHub App

Create one GitHub App and install it **only** on `MrDragon13/ChatGPT-lib`.

Repository permissions:

- Metadata: Read-only
- Contents: Read and write
- Pull requests: Read and write
- Actions: Read-only

No workflow-write permission is needed.

Set the user authorization callback URL to:

```text
https://<worker-host>/v1/auth/callback
```

Record the App ID, Client ID, Client Secret, installation ID, and the numeric GitHub user ID that is allowed to edit.

Generate a GitHub App private key. The Worker imports PKCS#8 PEM. If GitHub gives you a different RSA PEM form, convert it before storing it:

```bash
openssl pkcs8 -topk8 -nocrypt -in github-app.pem -out github-app-pkcs8.pem
```

Do not commit either private-key file.

## 2. Cloudflare Worker configuration

`wrangler.jsonc` already contains the public repository/origin settings and two Rate Limiting bindings. Namespace IDs `1001` and `1002` must be unique within your Cloudflare account; change them before deployment if those IDs are already used by another Worker.

Wrangler must be authenticated to the target Cloudflare account. Store runtime configuration on the Worker, not in this repository:

```bash
cd broker
npx wrangler secret put GITHUB_APP_ID
npx wrangler secret put GITHUB_APP_CLIENT_ID
npx wrangler secret put GITHUB_APP_INSTALLATION_ID
npx wrangler secret put OWNER_GITHUB_USER_ID
npx wrangler secret put GITHUB_APP_CLIENT_SECRET
npx wrangler secret put BROKER_SESSION_SECRET
npx wrangler secret put GITHUB_APP_PRIVATE_KEY < github-app-pkcs8.pem
```

Use a high-entropy random value for `BROKER_SESSION_SECRET`.

The production allowed browser origin is fixed to:

```text
https://mrdragon13.github.io
```

The browser never receives any GitHub token or Worker secret.

## 3. GitHub Actions deployment credentials

For the manual `Broker Deploy` workflow, configure these repository Actions secrets:

- `CLOUDFLARE_API_TOKEN` — a Cloudflare API token able to deploy this Worker;
- `CLOUDFLARE_ACCOUNT_ID` — the target Cloudflare account ID.

Runtime GitHub App secrets stay in Cloudflare and are not copied into GitHub Actions.

`Broker Deploy` is deliberately manual. Run it from `main` and pass the exact main commit SHA that already passed repository checks. This prevents an unprovisioned Cloudflare account from making normal merges or GitHub Pages deployment fail.

## 4. Publish the broker URL to the site

After the Worker is deployed and owner login works, create the GitHub repository variable:

```text
MEDIA_BROKER_URL=https://<worker-host>
```

The Pages build exposes only this public URL as `VITE_MEDIA_BROKER_URL`. No write credential belongs in the Vite build or Pages artifact.

If `MEDIA_BROKER_URL` is absent, the site must continue to build and operate read-only.

## 5. Verification before enabling the web editor

Run locally or in CI:

```bash
cd broker
npm ci
npm run test:run
npm run typecheck
```

Then perform one controlled operation through the deployed broker and confirm this chain completes:

```text
POST /v1/feedback
  -> media/op-<uuid> PR
  -> Media Command
  -> Media Check
  -> Media Auto Merge
  -> Media Pages
  -> GET /v1/operations/<uuid> == published
```

Only after that end-to-end check should `MEDIA_BROKER_URL` be supplied to the production Pages build.
