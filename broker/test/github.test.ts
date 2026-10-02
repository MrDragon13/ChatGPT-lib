import { beforeAll, afterEach, describe, expect, it, vi } from "vitest";

import { base64UrlDecode } from "../src/crypto";
import type { BrokerEnv } from "../src/env";
import { mintInstallationToken } from "../src/github";

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

beforeAll(async () => {
  privateKeyPem = await generatePrivateKeyPem();
});

afterEach(() => vi.restoreAllMocks());

describe("GitHub App installation authentication", () => {
  it("mints a repository- and permission-scoped installation token with an RS256 app JWT", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      token: "installation-token",
      expires_at: "2026-10-01T21:00:00Z",
    }), { status: 201, headers: { "content-type": "application/json" } }));

    await expect(mintInstallationToken(env(), new Date("2026-10-01T20:00:00Z")))
      .resolves.toBe("installation-token");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("https://api.github.com/app/installations/67890/access_tokens");
    expect(init?.method).toBe("POST");
    const headers = new Headers(init?.headers);
    const authorization = headers.get("authorization")!;
    expect(authorization).toMatch(/^Bearer [^.]+\.[^.]+\.[^.]+$/);

    const jwt = authorization.slice("Bearer ".length);
    const [headerSegment, payloadSegment] = jwt.split(".");
    const header = JSON.parse(new TextDecoder().decode(base64UrlDecode(headerSegment)));
    const payload = JSON.parse(new TextDecoder().decode(base64UrlDecode(payloadSegment)));
    expect(header).toEqual({ alg: "RS256", typ: "JWT" });
    expect(payload.iss).toBe("12345");
    expect(payload.exp - payload.iat).toBeLessThanOrEqual(600);

    expect(JSON.parse(String(init?.body))).toEqual({
      repositories: ["ChatGPT-lib"],
      permissions: {
        actions: "read",
        contents: "write",
        metadata: "read",
        pull_requests: "write",
      },
    });
    expect(headers.get("x-github-api-version")).toBe("2026-03-10");
  });
});
