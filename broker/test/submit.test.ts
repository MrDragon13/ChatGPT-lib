import { beforeAll, afterEach, describe, expect, it, vi } from "vitest";

import { issueSession } from "../src/auth";
import type { BrokerEnv } from "../src/env";
import type { FeedbackInput } from "../src/feedback";
import worker from "../src/index";
import { submitFeedback } from "../src/operations";

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
  it("creates one media/op branch, one typed request file, and one PR to main", async () => {
    const calls: Array<[RequestInfo | URL, RequestInit | undefined]> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request, init) => {
      calls.push([request, init]);
      const url = String(request);
      if (url.endsWith("/app/installations/67890/access_tokens")) return jsonResponse({ token: "installation-token" }, 201);
      if (url.endsWith("/git/ref/heads/main")) return jsonResponse({ object: { sha: "main-sha" } });
      if (url.endsWith("/git/refs") && init?.method === "POST") return jsonResponse({ ref: "created" }, 201);
      if (url.includes("/contents/.media/requests/") && init?.method === "PUT") return jsonResponse({ content: { sha: "request-sha" } }, 201);
      if (url.endsWith("/pulls") && init?.method === "POST") return jsonResponse({ number: 321 }, 201);
      throw new Error(`unexpected GitHub call: ${init?.method ?? "GET"} ${url}`);
    });

    const result = await submitFeedback(input, env());
    expect(result).toMatchObject({ pr_number: 321, status: "submitted" });
    expect(result.operation_id).toMatch(/^[0-9a-f-]{36}$/i);

    const refCall = calls.find(([url, init]) => String(url).endsWith("/git/refs") && init?.method === "POST")!;
    expect(JSON.parse(String(refCall[1]?.body))).toEqual({
      ref: `refs/heads/media/op-${result.operation_id}`,
      sha: "main-sha",
    });

    const requestCall = calls.find(([url]) => String(url).includes("/contents/.media/requests/"))!;
    expect(String(requestCall[0])).toContain(`.media/requests/${result.operation_id}.json`);
    const command = decodedRequestCommand(requestCall[1]);
    expect(command).toEqual({
      schema_version: 1,
      operation_id: result.operation_id,
      operation: "record_viewing_feedback",
      work_ref: { id: "game-night-2018" },
      create_if_missing: false,
      target_updates: [{
        target: "primary",
        rating: { score: 8.5, source: "explicit", confidence: "exact" },
        reaction: { value: "liked", source: "explicit", confidence: "exact" },
        feedback: { summary: "Очень удачная комедия." },
      }],
    });

    const prCall = calls.find(([url, init]) => String(url).endsWith("/pulls") && init?.method === "POST")!;
    const prBody = JSON.parse(String(prCall[1]?.body));
    expect(prBody.base).toBe("main");
    expect(prBody.head).toBe(`media/op-${result.operation_id}`);
    expect(JSON.stringify(prBody)).not.toContain("Очень удачная комедия.");
  });

  it("cleans up a created operation branch if request creation fails", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ token: "installation-token" }, 201))
      .mockResolvedValueOnce(jsonResponse({ object: { sha: "main-sha" } }))
      .mockResolvedValueOnce(jsonResponse({ ref: "created" }, 201))
      .mockResolvedValueOnce(jsonResponse({ message: "write failed" }, 500))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(submitFeedback(input, env())).rejects.toMatchObject({ operationId: expect.any(String) });
    expect(fetchMock).toHaveBeenCalledTimes(5);
    const [cleanupUrl, cleanupInit] = fetchMock.mock.calls[4];
    expect(String(cleanupUrl)).toContain("/git/refs/heads/media/op-");
    expect(cleanupInit?.method).toBe("DELETE");
  });

  it("does not report submitted when PR creation fails", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ token: "installation-token" }, 201))
      .mockResolvedValueOnce(jsonResponse({ object: { sha: "main-sha" } }))
      .mockResolvedValueOnce(jsonResponse({ ref: "created" }, 201))
      .mockResolvedValueOnce(jsonResponse({ content: { sha: "request-sha" } }, 201))
      .mockResolvedValueOnce(jsonResponse({ message: "PR failed" }, 500))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(submitFeedback(input, env())).rejects.toMatchObject({ operationId: expect.any(String) });
    expect(fetchMock).toHaveBeenCalledTimes(6);
  });

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
