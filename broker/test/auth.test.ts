import { afterEach, describe, expect, it, vi } from "vitest";

import type { BrokerEnv } from "../src/env";
import worker from "../src/index";
import { finishAuth, issueSession, startAuth, verifySession } from "../src/auth";

function makeEnv(authAllowed = true): BrokerEnv {
  return {
    REPO_OWNER: "MrDragon13",
    REPO_NAME: "ChatGPT-lib",
    ALLOWED_ORIGIN: "https://mrdragon13.github.io",
    GITHUB_APP_CLIENT_ID: "client-id",
    GITHUB_APP_CLIENT_SECRET: "client-secret",
    OWNER_GITHUB_USER_ID: "197501470",
    BROKER_SESSION_SECRET: "test-session-secret-that-is-long-enough",
    AUTH_RATE_LIMITER: { limit: vi.fn(async () => ({ success: authAllowed })) },
    WRITE_RATE_LIMITER: { limit: vi.fn(async () => ({ success: true })) },
  };
}

function cookiePair(response: Response): string {
  const value = response.headers.get("set-cookie");
  if (!value) throw new Error("missing oauth cookie");
  return value.split(";", 1)[0];
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("GitHub owner authentication", () => {
  it("starts OAuth with random state, PKCE S256, exact callback, and hardened transient cookie", async () => {
    const response = await startAuth(new Request("https://broker.example/v1/auth/start"), makeEnv());
    expect(response.status).toBe(302);

    const location = new URL(response.headers.get("location")!);
    expect(location.origin + location.pathname).toBe("https://github.com/login/oauth/authorize");
    expect(location.searchParams.get("client_id")).toBe("client-id");
    expect(location.searchParams.get("redirect_uri")).toBe("https://broker.example/v1/auth/callback");
    expect(location.searchParams.get("state")).toMatch(/^[A-Za-z0-9_-]{20,}$/);
    expect(location.searchParams.get("code_challenge_method")).toBe("S256");
    expect(location.searchParams.get("code_challenge")).toMatch(/^[A-Za-z0-9_-]{40,}$/);

    const cookie = response.headers.get("set-cookie")!;
    expect(cookie).toContain("broker_oauth=");
    expect(cookie).toContain("Max-Age=600");
    expect(cookie).toContain("Path=/v1/auth/callback");
    expect(cookie).toContain("Secure");
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("SameSite=Lax");
  });

  it("accepts only the configured numeric owner id and posts a broker token to the exact Pages origin", async () => {
    const env = makeEnv();
    const start = await startAuth(new Request("https://broker.example/v1/auth/start"), env);
    const state = new URL(start.headers.get("location")!).searchParams.get("state")!;

    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "gh-user-token", token_type: "bearer" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 197501470 }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }));

    const callback = new Request(`https://broker.example/v1/auth/callback?code=raw-oauth-code&state=${state}`, {
      headers: { cookie: cookiePair(start) },
    });
    const response = await finishAuth(callback, env);
    expect(response.status).toBe(200);
    const html = await response.text();
    expect(html).toContain("https://mrdragon13.github.io");
    expect(html).toContain("postMessage");
    expect(html).not.toContain("postMessage(message, \"*\")");
    expect(html).not.toContain("gh-user-token");
    expect(html).not.toContain("raw-oauth-code");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("returns 403 for a different GitHub user", async () => {
    const env = makeEnv();
    const start = await startAuth(new Request("https://broker.example/v1/auth/start"), env);
    const state = new URL(start.headers.get("location")!).searchParams.get("state")!;

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "gh-user-token" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 42 }), { status: 200 }));

    const response = await finishAuth(new Request(
      `https://broker.example/v1/auth/callback?code=code&state=${state}`,
      { headers: { cookie: cookiePair(start) } },
    ), env);
    expect(response.status).toBe(403);
    expect(await response.text()).not.toContain("gh-user-token");
  });

  it("rejects missing or tampered OAuth state before contacting GitHub", async () => {
    const env = makeEnv();
    const start = await startAuth(new Request("https://broker.example/v1/auth/start"), env);
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await finishAuth(new Request(
      "https://broker.example/v1/auth/callback?code=secret-code&state=tampered",
      { headers: { cookie: cookiePair(start) } },
    ), env);
    expect(response.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(await response.text()).not.toContain("secret-code");
  });

  it("issues a signed broker session that expires after 15 minutes and rejects tampering", async () => {
    const env = makeEnv();
    const now = new Date("2026-10-01T20:00:00Z");
    const token = await issueSession("197501470", env, now);

    await expect(verifySession(token, env, new Date(now.getTime() + 14 * 60_000 + 59_000)))
      .resolves.toMatchObject({ sub: "197501470" });
    await expect(verifySession(token, env, new Date(now.getTime() + 15 * 60_000 + 1_000)))
      .rejects.toThrow(/expired/i);

    const tampered = `${token.slice(0, -1)}${token.endsWith("a") ? "b" : "a"}`;
    await expect(verifySession(tampered, env, now)).rejects.toThrow();
  });

  it("rate limits auth routes before starting OAuth", async () => {
    const env = makeEnv(false);
    const response = await worker.fetch(new Request("https://broker.example/v1/auth/start"), env);
    expect(response.status).toBe(429);
    expect(env.AUTH_RATE_LIMITER.limit).toHaveBeenCalledTimes(1);
  });

  it("scopes unauthenticated auth limiting to a coarse client network signal", async () => {
    const env = makeEnv();
    const response = await worker.fetch(new Request("https://broker.example/v1/auth/start", {
      headers: { "CF-Connecting-IP": "203.0.113.7" },
    }), env);

    expect(response.status).toBe(302);
    expect(env.AUTH_RATE_LIMITER.limit).toHaveBeenCalledWith({
      key: "auth:/v1/auth/start:203.0.113.7",
    });
  });
});
