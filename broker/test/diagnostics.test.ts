import { beforeAll, afterEach, describe, expect, it, vi } from "vitest";

import { issueSession } from "../src/auth";
import type { BrokerEnv } from "../src/env";
import worker from "../src/index";

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

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json" },
  });
}

beforeAll(async () => {
  privateKeyPem = await generatePrivateKeyPem();
});

afterEach(() => vi.restoreAllMocks());

describe("broker diagnostics", () => {
  it("returns a safe stage and upstream status when GitHub App token minting fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ message: "Not Found" }, 404));

    const brokerEnv = env();
    const token = await issueSession("197501470", brokerEnv);
    const response = await worker.fetch(new Request("https://broker.example/v1/feedback", {
      method: "POST",
      headers: {
        authorization: `Bearer ${token}`,
        "content-type": "application/json",
        origin: "https://mrdragon13.github.io",
      },
      body: JSON.stringify({ work_id: "arrival-2016", target: "primary", rating: 8.5 }),
    }), brokerEnv);

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toMatchObject({
      error: "github_unavailable",
      stage: "installation_token",
      upstream_status: 404,
    });
  });

  it("preserves the exact GitHub stage after operation submission has started", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request, init) => {
      const url = new URL(String(request));
      const method = init?.method ?? "GET";

      if (url.pathname.endsWith("/app/installations/67890/access_tokens")) {
        return json({ token: "installation-token" }, 201);
      }
      if (url.pathname.endsWith("/pulls") && method === "GET") {
        return json([]);
      }
      if (url.pathname.endsWith("/git/ref/heads/main") && method === "GET") {
        return json({ object: { sha: "main-sha" } });
      }
      if (url.pathname.endsWith("/git/refs") && method === "POST") {
        return json({ message: "Validation Failed" }, 422);
      }
      throw new Error(`unexpected GitHub call: ${method} ${url}`);
    });

    const brokerEnv = env();
    const token = await issueSession("197501470", brokerEnv);
    const response = await worker.fetch(new Request("https://broker.example/v1/feedback", {
      method: "POST",
      headers: {
        authorization: `Bearer ${token}`,
        "content-type": "application/json",
        origin: "https://mrdragon13.github.io",
      },
      body: JSON.stringify({ work_id: "arrival-2016", target: "primary", rating: 9 }),
    }), brokerEnv);

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toMatchObject({
      error: "github_operation_failed",
      stage: "create_branch",
      upstream_status: 422,
    });
  });
});
