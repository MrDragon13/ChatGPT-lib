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
  return new Response(JSON.stringify(value), { status, headers: { "content-type": "application/json" } });
}

function base64Json(value: unknown): string {
  const bytes = new TextEncoder().encode(JSON.stringify(value));
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

beforeAll(async () => {
  privateKeyPem = await generatePrivateKeyPem();
});

afterEach(() => vi.restoreAllMocks());

describe("active feedback conflicts", () => {
  it("returns 409 before creating another operation for the same work and target", async () => {
    const existingId = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
    const existingBranch = `media/op-${existingId}`;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request, init) => {
      const url = new URL(String(request));
      if (url.pathname.endsWith("/app/installations/67890/access_tokens")) return json({ token: "installation-token" }, 201);
      if (url.pathname.endsWith("/pulls") && (!init?.method || init.method === "GET")) {
        return json([{
          number: 77,
          state: "open",
          head: { ref: existingBranch, repo: { full_name: "MrDragon13/ChatGPT-lib" } },
          base: { ref: "main" },
        }]);
      }
      if (url.pathname.endsWith("/pulls/77/commits")) return json([{ sha: "initial-sha" }]);
      if (url.pathname.includes(`/contents/.media/requests/${existingId}.json`)) {
        return json({
          encoding: "base64",
          content: base64Json({
            operation: "record_viewing_feedback",
            work_ref: { id: "game-night-2018" },
            target_updates: [{ target: "primary", rating: { score: 7 } }],
          }),
        });
      }
      throw new Error(`unexpected GitHub call: ${init?.method ?? "GET"} ${url}`);
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
      body: JSON.stringify({ work_id: "game-night-2018", target: "primary", rating: 8.5 }),
    }), brokerEnv);

    expect(response.status).toBe(409);
    await expect(response.json()).resolves.toMatchObject({ error: "active_operation", operation_id: existingId, pr_number: 77 });
    expect(fetchMock.mock.calls.some(([request, init]) => String(request).endsWith("/git/refs") && init?.method === "POST")).toBe(false);
  });
});


it("treats an open record_media_entry as the active operation for the same work and target", async () => {
  const existingId = "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff";
  const existingBranch = `media/op-${existingId}`;
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request, init) => {
    const url = new URL(String(request));
    if (url.pathname.endsWith("/app/installations/67890/access_tokens")) return json({ token: "installation-token" }, 201);
    if (url.pathname.endsWith("/pulls") && (!init?.method || init.method === "GET")) {
      return json([{
        number: 88,
        state: "open",
        head: { ref: existingBranch, repo: { full_name: "MrDragon13/ChatGPT-lib" } },
        base: { ref: "main" },
      }]);
    }
    if (url.pathname.endsWith("/pulls/88/commits")) return json([{ sha: "initial-v6-sha" }]);
    if (url.pathname.includes(`/contents/.media/requests/${existingId}.json`)) {
      return json({
        encoding: "base64",
        content: base64Json({
          operation: "record_media_entry",
          work_ref: { id: "game-night-2018" },
          target_updates: [{ target: "primary", rating: { score: 8 } }],
          preconditions: { expected_viewer_digests: { primary: "sha256:" + "a".repeat(64) } },
        }),
      });
    }
    throw new Error(`unexpected GitHub call: ${init?.method ?? "GET"} ${url}`);
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
    body: JSON.stringify({ work_id: "game-night-2018", target: "primary", rating: 9 }),
  }), brokerEnv);

  expect(response.status).toBe(409);
  await expect(response.json()).resolves.toMatchObject({ error: "active_operation", operation_id: existingId, pr_number: 88 });
  expect(fetchMock.mock.calls.some(([request, init]) => String(request).endsWith("/git/refs") && init?.method === "POST")).toBe(false);
});
