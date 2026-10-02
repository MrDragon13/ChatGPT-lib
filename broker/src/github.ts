import { base64UrlEncode } from "./crypto";
import type { BrokerEnv } from "./env";

const encoder = new TextEncoder();
const API_VERSION = "2026-03-10";
const USER_AGENT = "chatgpt-lib-media-broker";

export type GitHubApiStage =
  | "app_jwt"
  | "installation_token"
  | "github_api"
  | "main_ref"
  | "create_branch"
  | "write_request"
  | "create_pull_request"
  | "delete_branch";

function required(env: BrokerEnv, key: keyof BrokerEnv): string {
  const value = env[key];
  if (typeof value !== "string" || value.length === 0) throw new Error(`missing broker config: ${String(key)}`);
  return value;
}

function pemToPkcs8(pem: string): ArrayBuffer {
  const body = pem
    .replace(/-----BEGIN PRIVATE KEY-----/g, "")
    .replace(/-----END PRIVATE KEY-----/g, "")
    .replace(/\s+/g, "");
  if (!body) throw new Error("invalid GitHub App private key");
  const binary = atob(body);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;
}

async function createAppJwt(env: BrokerEnv, now = new Date()): Promise<string> {
  const iat = Math.floor(now.getTime() / 1000) - 60;
  const header = base64UrlEncode(encoder.encode(JSON.stringify({ alg: "RS256", typ: "JWT" })));
  const payload = base64UrlEncode(encoder.encode(JSON.stringify({
    iat,
    exp: iat + 600,
    iss: required(env, "GITHUB_APP_ID"),
  })));
  const signingInput = `${header}.${payload}`;
  const key = await crypto.subtle.importKey(
    "pkcs8",
    pemToPkcs8(required(env, "GITHUB_APP_PRIVATE_KEY")),
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, encoder.encode(signingInput));
  return `${signingInput}.${base64UrlEncode(new Uint8Array(signature))}`;
}

export class GitHubApiError extends Error {
  constructor(
    message: string,
    public readonly status: number | null,
    public readonly requestId: string | null = null,
    public readonly stage: GitHubApiStage = "github_api",
  ) {
    super(message);
    this.name = "GitHubApiError";
  }
}

export async function mintInstallationToken(env: BrokerEnv, now = new Date()): Promise<string> {
  let jwt: string;
  try {
    jwt = await createAppJwt(env, now);
  } catch (error) {
    throw new GitHubApiError(
      error instanceof Error ? error.message : "failed to create GitHub App JWT",
      null,
      null,
      "app_jwt",
    );
  }

  const response = await fetch(
    `https://api.github.com/app/installations/${encodeURIComponent(required(env, "GITHUB_APP_INSTALLATION_ID"))}/access_tokens`,
    {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${jwt}`,
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": USER_AGENT,
      },
      body: JSON.stringify({
        repositories: [env.REPO_NAME],
        permissions: {
          actions: "read",
          contents: "write",
          metadata: "read",
          pull_requests: "write",
        },
      }),
    },
  );
  if (!response.ok) {
    throw new GitHubApiError(
      "failed to mint installation token",
      response.status,
      response.headers.get("x-github-request-id"),
      "installation_token",
    );
  }
  const data = await response.json() as { token?: unknown };
  if (typeof data.token !== "string" || data.token.length === 0) {
    throw new GitHubApiError(
      "installation token missing from GitHub response",
      502,
      response.headers.get("x-github-request-id"),
      "installation_token",
    );
  }
  return data.token;
}

function repoBase(env: BrokerEnv): string {
  return `https://api.github.com/repos/${encodeURIComponent(env.REPO_OWNER)}/${encodeURIComponent(env.REPO_NAME)}`;
}

async function githubRequest(
  env: BrokerEnv,
  token: string,
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/vnd.github+json");
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("X-GitHub-Api-Version", API_VERSION);
  headers.set("User-Agent", USER_AGENT);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  return fetch(`${repoBase(env)}${path}`, { ...init, headers });
}

async function expectJson<T>(response: Response, action: string, stage: GitHubApiStage = "github_api"): Promise<T> {
  if (!response.ok) {
    throw new GitHubApiError(action, response.status, response.headers.get("x-github-request-id"), stage);
  }
  return response.json() as Promise<T>;
}

export async function getRepoJson<T>(
  env: BrokerEnv,
  token: string,
  path: string,
  action: string,
  stage: GitHubApiStage = "github_api",
): Promise<T> {
  return expectJson<T>(await githubRequest(env, token, path), action, stage);
}

export async function getMainSha(env: BrokerEnv, token: string): Promise<string> {
  const data = await getRepoJson<{ object?: { sha?: unknown } }>(
    env,
    token,
    "/git/ref/heads/main",
    "failed to read main ref",
    "main_ref",
  );
  if (typeof data.object?.sha !== "string" || !data.object.sha) {
    throw new GitHubApiError("main ref response missing sha", 502, null, "main_ref");
  }
  return data.object.sha;
}

export async function createBranch(env: BrokerEnv, token: string, branch: string, sha: string): Promise<void> {
  const response = await githubRequest(env, token, "/git/refs", {
    method: "POST",
    body: JSON.stringify({ ref: `refs/heads/${branch}`, sha }),
  });
  if (!response.ok) {
    throw new GitHubApiError(
      "failed to create operation branch",
      response.status,
      response.headers.get("x-github-request-id"),
      "create_branch",
    );
  }
}

export async function putRequestFile(
  env: BrokerEnv,
  token: string,
  branch: string,
  path: string,
  content: string,
  operationId: string,
): Promise<void> {
  const response = await githubRequest(env, token, `/contents/${path}`, {
    method: "PUT",
    body: JSON.stringify({
      message: `data: request media operation ${operationId}`,
      content,
      branch,
    }),
  });
  if (!response.ok) {
    throw new GitHubApiError(
      "failed to create operation request",
      response.status,
      response.headers.get("x-github-request-id"),
      "write_request",
    );
  }
}

export async function createOperationPullRequest(
  env: BrokerEnv,
  token: string,
  branch: string,
  operationId: string,
  workId: string,
): Promise<number> {
  const response = await githubRequest(env, token, "/pulls", {
    method: "POST",
    body: JSON.stringify({
      title: `data: update media feedback for ${workId}`,
      body: `Automated media feedback operation ${operationId}.`,
      head: branch,
      base: "main",
    }),
  });
  const data = await expectJson<{ number?: unknown }>(
    response,
    "failed to create operation pull request",
    "create_pull_request",
  );
  if (typeof data.number !== "number") {
    throw new GitHubApiError("pull request response missing number", 502, null, "create_pull_request");
  }
  return data.number;
}

export async function deleteBranch(env: BrokerEnv, token: string, branch: string): Promise<void> {
  const response = await githubRequest(env, token, `/git/refs/heads/${branch}`, { method: "DELETE" });
  if (!response.ok && response.status !== 404) {
    throw new GitHubApiError(
      "failed to clean up operation branch",
      response.status,
      response.headers.get("x-github-request-id"),
      "delete_branch",
    );
  }
}
