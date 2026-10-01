import { beforeAll, afterEach, describe, expect, it, vi } from "vitest";

import type { BrokerEnv } from "../src/env";
import { getOperationStatus } from "../src/operations";

let privateKeyPem = "";

async function generatePrivateKeyPem(): Promise<string> {
  const pair = await crypto.subtle.generateKey({
    name: "RSASSA-PKCS1-v1_5",
    modulusLength: 2048,
    publicExponent: new Uint8Array([1, 0, 1]),
    hash: "SHA-256",
  }, true, ["sign", "verify"]) as CryptoKeyPair;
  const pkcs8 = new Uint8Array(await crypto.subtle.exportKey("pkcs8", pair.privateKey));
  let binary = "";
  for (const byte of pkcs8) binary += String.fromCharCode(byte);
  const lines = btoa(binary).match(/.{1,64}/g) ?? [];
  return `-----BEGIN PRIVATE KEY-----\n${lines.join("\n")}\n-----END PRIVATE KEY-----`;
}

function env(): BrokerEnv {
  return {
    REPO_OWNER: "MrDragon13",
    REPO_NAME: "ChatGPT-lib",
    ALLOWED_ORIGIN: "https://mrdragon13.github.io",
    GITHUB_APP_ID: "12345",
    GITHUB_APP_CLIENT_ID: "client-id",
    GITHUB_APP_INSTALLATION_ID: "67890",
    OWNER_GITHUB_USER_ID: "197501470",
    GITHUB_APP_PRIVATE_KEY: privateKeyPem,
    GITHUB_APP_CLIENT_SECRET: "client-secret",
    BROKER_SESSION_SECRET: "session-secret-that-is-long-enough",
    AUTH_RATE_LIMITER: { limit: vi.fn(async () => ({ success: true })) },
    WRITE_RATE_LIMITER: { limit: vi.fn(async () => ({ success: true })) },
  };
}

const operationId = "11111111-2222-4333-8444-555555555555";
const branch = `media/op-${operationId}`;

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "content-type": "application/json" } });
}

type Scenario = {
  pr?: Record<string, unknown>;
  commandRuns?: Array<Record<string, unknown>>;
  checkRuns?: Array<Record<string, unknown>>;
  mergeRuns?: Array<Record<string, unknown>>;
  pagesRuns?: Array<Record<string, unknown>>;
};

function openPr(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    number: 42,
    state: "open",
    merged_at: null,
    merge_commit_sha: null,
    html_url: "https://github.com/MrDragon13/ChatGPT-lib/pull/42",
    head: { ref: branch, sha: "operation-head", repo: { full_name: "MrDragon13/ChatGPT-lib" } },
    base: { ref: "main" },
    ...overrides,
  };
}

function mockScenario(scenario: Scenario): void {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
    const url = new URL(String(request));
    if (url.pathname.endsWith("/app/installations/67890/access_tokens")) {
      return json({ token: "installation-token" }, 201);
    }
    if (url.pathname.endsWith("/pulls")) {
      return json(scenario.pr ? [scenario.pr] : []);
    }
    if (url.pathname.includes("/actions/workflows/media-command.yml/runs")) {
      return json({ workflow_runs: scenario.commandRuns ?? [] });
    }
    if (url.pathname.includes("/actions/workflows/media-check.yml/runs")) {
      return json({ workflow_runs: scenario.checkRuns ?? [] });
    }
    if (url.pathname.includes("/actions/workflows/media-auto-merge.yml/runs")) {
      return json({ workflow_runs: scenario.mergeRuns ?? [] });
    }
    if (url.pathname.includes("/actions/workflows/media-pages.yml/runs")) {
      return json({ workflow_runs: scenario.pagesRuns ?? [] });
    }
    throw new Error(`unexpected GitHub call: ${url}`);
  });
}

beforeAll(async () => {
  privateKeyPem = await generatePrivateKeyPem();
});

afterEach(() => vi.restoreAllMocks());

describe("feedback operation status", () => {
  it("reports submitted before Media Command starts", async () => {
    mockScenario({ pr: openPr() });
    await expect(getOperationStatus(operationId, env())).resolves.toMatchObject({ status: "submitted", pr_number: 42 });
  });

  it("reports applying while Media Command is running", async () => {
    mockScenario({ pr: openPr(), commandRuns: [{ status: "in_progress", conclusion: null, head_sha: "operation-head" }] });
    await expect(getOperationStatus(operationId, env())).resolves.toMatchObject({ status: "applying" });
  });

  it("reports command failure", async () => {
    mockScenario({ pr: openPr(), commandRuns: [{ status: "completed", conclusion: "failure", head_sha: "operation-head" }] });
    await expect(getOperationStatus(operationId, env())).resolves.toMatchObject({ status: "failed", reason: "command_failed" });
  });

  it("reports checking after command success while Media Check is pending", async () => {
    mockScenario({
      pr: openPr(),
      commandRuns: [{ status: "completed", conclusion: "success", head_sha: "operation-head" }],
      checkRuns: [{ status: "in_progress", conclusion: null, head_sha: "operation-head" }],
    });
    await expect(getOperationStatus(operationId, env())).resolves.toMatchObject({ status: "checking" });
  });

  it("reports check failure", async () => {
    mockScenario({
      pr: openPr(),
      commandRuns: [{ status: "completed", conclusion: "success", head_sha: "operation-head" }],
      checkRuns: [{ status: "completed", conclusion: "failure", head_sha: "operation-head" }],
    });
    await expect(getOperationStatus(operationId, env())).resolves.toMatchObject({ status: "failed", reason: "check_failed" });
  });

  it("reports merge failure after a successful check when auto merge fails", async () => {
    mockScenario({
      pr: openPr(),
      commandRuns: [{ status: "completed", conclusion: "success", head_sha: "operation-head" }],
      checkRuns: [{ status: "completed", conclusion: "success", head_sha: "operation-head" }],
      mergeRuns: [{ status: "completed", conclusion: "failure", head_branch: branch }],
    });
    await expect(getOperationStatus(operationId, env())).resolves.toMatchObject({ status: "failed", reason: "merge_failed" });
  });

  it("reports merged until Pages succeeds for the exact merge sha", async () => {
    mockScenario({
      pr: openPr({ state: "closed", merged_at: "2026-10-02T10:00:00Z", merge_commit_sha: "merge-sha" }),
      pagesRuns: [{ status: "completed", conclusion: "success", head_sha: "older-sha" }],
    });
    await expect(getOperationStatus(operationId, env())).resolves.toMatchObject({ status: "merged", merge_sha: "merge-sha" });
  });

  it("reports published only after successful Pages for the exact merge sha", async () => {
    mockScenario({
      pr: openPr({ state: "closed", merged_at: "2026-10-02T10:00:00Z", merge_commit_sha: "merge-sha" }),
      pagesRuns: [{ status: "completed", conclusion: "success", head_sha: "merge-sha", html_url: "https://github.com/actions/runs/1" }],
    });
    await expect(getOperationStatus(operationId, env())).resolves.toMatchObject({ status: "published", merge_sha: "merge-sha" });
  });

  it("reports deploy failure for the exact merge sha", async () => {
    mockScenario({
      pr: openPr({ state: "closed", merged_at: "2026-10-02T10:00:00Z", merge_commit_sha: "merge-sha" }),
      pagesRuns: [{ status: "completed", conclusion: "failure", head_sha: "merge-sha" }],
    });
    await expect(getOperationStatus(operationId, env())).resolves.toMatchObject({ status: "failed", reason: "deploy_failed" });
  });

  it("reports merge failure when the operation PR closes without merging", async () => {
    mockScenario({ pr: openPr({ state: "closed", merged_at: null, merge_commit_sha: null }) });
    await expect(getOperationStatus(operationId, env())).resolves.toMatchObject({ status: "failed", reason: "merge_failed" });
  });
});
