import { beforeAll, afterEach, describe, expect, it, vi } from "vitest";

import { issueSession } from "../src/auth";
import type { BrokerEnv } from "../src/env";
import type { FeedbackInput } from "../src/feedback";
import worker from "../src/index";
import { submitFeedbackV6 } from "../src/operations";

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

function env(writeAllowed = true): BrokerEnv {
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
    WRITE_RATE_LIMITER: { limit: vi.fn(async () => ({ success: writeAllowed })) },
  };
}

const input: FeedbackInput = {
  work_id: "game-night-2018",
  target: "primary",
  rating: 8.5,
  reaction: "liked",
  feedback_summary: "Очень удачная комедия.",
};

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "content-type": "application/json" } });
}

function decodedRequestCommand(init: RequestInit | undefined): Record<string, unknown> {
  const body = JSON.parse(String(init?.body)) as { content: string };
  const binary = atob(body.content);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return JSON.parse(new TextDecoder().decode(bytes)) as Record<string, unknown>;
}

beforeAll(async () => {
  privateKeyPem = await generatePrivateKeyPem();
});

afterEach(() => vi.restoreAllMocks());

describe("safe feedback operation submission", () => {
  it("requires a broker session before any GitHub write", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const response = await worker.fetch(new Request("https://broker.example/v1/feedback", {
      method: "POST",
      headers: { "content-type": "application/json", origin: "https://mrdragon13.github.io" },
      body: JSON.stringify(input),
    }), env());
    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rate limits writes after validating the owner session and before GitHub calls", async () => {
    const brokerEnv = env(false);
    const token = await issueSession("197501470", brokerEnv);
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const response = await worker.fetch(new Request("https://broker.example/v1/feedback", {
      method: "POST",
      headers: {
        authorization: `Bearer ${token}`,
        "content-type": "application/json",
        origin: "https://mrdragon13.github.io",
      },
      body: JSON.stringify(input),
    }), brokerEnv);
    expect(response.status).toBe(429);
    expect(brokerEnv.WRITE_RATE_LIMITER.limit).toHaveBeenCalledTimes(1);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});


describe("v6 feedback mapping", () => {
  it("reads the viewer digest at the exact main SHA and builds one record_media_entry request", async () => {
    const calls: Array<[RequestInfo | URL, RequestInit | undefined]> = [];
    const digest = "sha256:" + "a".repeat(64);
    const indexLine = JSON.stringify({
      id: "game-night-2018",
      viewer_digests: { primary: digest, partner: "sha256:" + "b".repeat(64) },
    }) + "\n";
    const indexBytes = new TextEncoder().encode(indexLine);
    let indexBinary = "";
    for (const byte of indexBytes) indexBinary += String.fromCharCode(byte);

    vi.spyOn(globalThis, "fetch").mockImplementation(async (request, init) => {
      calls.push([request, init]);
      const url = String(request);
      if (url.endsWith("/app/installations/67890/access_tokens")) return jsonResponse({ token: "installation-token" }, 201);
      if (url.endsWith("/git/ref/heads/main")) return jsonResponse({ object: { sha: "main-sha" } });
      if (url.includes("/contents/media/generated/index.jsonl?ref=main-sha")) {
        return jsonResponse({ encoding: "base64", content: btoa(indexBinary) });
      }
      if (url.endsWith("/git/refs") && init?.method === "POST") return jsonResponse({ ref: "created" }, 201);
      if (url.includes("/contents/.media/requests/") && init?.method === "PUT") return jsonResponse({ content: { sha: "request-sha" } }, 201);
      if (url.endsWith("/pulls") && init?.method === "POST") return jsonResponse({ number: 654 }, 201);
      throw new Error(`unexpected GitHub call: ${init?.method ?? "GET"} ${url}`);
    });

    const result = await submitFeedbackV6(input, env());
    expect(result).toMatchObject({ pr_number: 654, status: "submitted" });

    const refCall = calls.find(([url, init]) => String(url).endsWith("/git/refs") && init?.method === "POST")!;
    expect(JSON.parse(String(refCall[1]?.body))).toEqual({
      ref: `refs/heads/media/op-${result.operation_id}`,
      sha: "main-sha",
    });

    const indexCall = calls.find(([url]) => String(url).includes("/contents/media/generated/index.jsonl"))!;
    expect(String(indexCall[0])).toContain("ref=main-sha");

    const requestCall = calls.find(([url]) => String(url).includes("/contents/.media/requests/"))!;
    const command = decodedRequestCommand(requestCall[1]);
    expect(command).toMatchObject({
      schema_version: 1,
      operation_id: result.operation_id,
      operation: "record_media_entry",
      work_ref: { id: "game-night-2018" },
      create_if_missing: false,
      target_updates: [{
        target: "primary",
        rating: { score: 8.5, source: "explicit", confidence: "exact" },
        reaction: { value: "liked", source: "explicit", confidence: "exact" },
        feedback: { summary: "Очень удачная комедия." },
      }],
      preconditions: { expected_viewer_digests: { primary: digest } },
    });
    expect(command.idempotency_key).toMatch(/^[0-9a-f-]{36}$/i);
    expect(command.idempotency_key).not.toBe(result.operation_id);
  });
});
