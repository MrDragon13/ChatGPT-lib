import type { BrokerEnv } from "./env";
import { jsonResponse } from "./http";
import { randomUrlSafe, sha256UrlSafe, signJson, verifySignedJson } from "./crypto";

const OAUTH_COOKIE = "broker_oauth";
const OAUTH_TTL_SECONDS = 10 * 60;
const SESSION_TTL_SECONDS = 15 * 60;

type OAuthTransaction = {
  state: string;
  verifier: string;
  exp: number;
};

export type SessionClaims = {
  sub: string;
  iat: number;
  exp: number;
};

function required(env: BrokerEnv, key: keyof BrokerEnv): string {
  const value = env[key];
  if (typeof value !== "string" || value.length === 0) throw new Error(`missing broker config: ${String(key)}`);
  return value;
}

function seconds(date: Date): number {
  return Math.floor(date.getTime() / 1000);
}

function callbackUrl(request: Request): string {
  const url = new URL(request.url);
  return `${url.origin}/v1/auth/callback`;
}

function oauthCookie(value: string, maxAge: number): string {
  return `${OAUTH_COOKIE}=${value}; Max-Age=${maxAge}; Path=/v1/auth/callback; Secure; HttpOnly; SameSite=Lax`;
}

function getCookie(request: Request, name: string): string | null {
  const cookie = request.headers.get("cookie");
  if (!cookie) return null;
  for (const pair of cookie.split(";")) {
    const [key, ...parts] = pair.trim().split("=");
    if (key === name) return parts.join("=");
  }
  return null;
}

function callbackHtml(token: string, allowedOrigin: string): string {
  const message = JSON.stringify({ type: "media-broker-auth", token });
  return `<!doctype html><html lang="en"><meta charset="utf-8"><title>Authentication complete</title><script>const message=${message};window.opener?.postMessage(message,${JSON.stringify(allowedOrigin)});window.close();</script><body>Authentication complete.</body></html>`;
}

export async function issueSession(
  ownerId: string,
  env: BrokerEnv,
  now = new Date(),
): Promise<string> {
  const iat = seconds(now);
  const claims: SessionClaims = { sub: ownerId, iat, exp: iat + SESSION_TTL_SECONDS };
  return signJson(claims, required(env, "BROKER_SESSION_SECRET"));
}

export async function verifySession(
  token: string,
  env: BrokerEnv,
  now = new Date(),
): Promise<SessionClaims> {
  const claims = await verifySignedJson<SessionClaims>(token, required(env, "BROKER_SESSION_SECRET"));
  if (!claims || typeof claims.sub !== "string" || typeof claims.iat !== "number" || typeof claims.exp !== "number") {
    throw new Error("invalid session");
  }
  if (claims.sub !== required(env, "OWNER_GITHUB_USER_ID")) throw new Error("invalid session owner");
  if (claims.exp <= seconds(now)) throw new Error("session expired");
  return claims;
}

export async function startAuth(request: Request, env: BrokerEnv, now = new Date()): Promise<Response> {
  const clientId = required(env, "GITHUB_APP_CLIENT_ID");
  const secret = required(env, "BROKER_SESSION_SECRET");
  const state = randomUrlSafe(24);
  const verifier = randomUrlSafe(32);
  const codeChallenge = await sha256UrlSafe(verifier);
  const transaction: OAuthTransaction = { state, verifier, exp: seconds(now) + OAUTH_TTL_SECONDS };
  const signedTransaction = await signJson(transaction, secret);

  const location = new URL("https://github.com/login/oauth/authorize");
  location.searchParams.set("client_id", clientId);
  location.searchParams.set("redirect_uri", callbackUrl(request));
  location.searchParams.set("state", state);
  location.searchParams.set("code_challenge", codeChallenge);
  location.searchParams.set("code_challenge_method", "S256");

  return new Response(null, {
    status: 302,
    headers: {
      Location: location.toString(),
      "Set-Cookie": oauthCookie(signedTransaction, OAUTH_TTL_SECONDS),
      "Cache-Control": "no-store",
    },
  });
}

export async function finishAuth(request: Request, env: BrokerEnv, now = new Date()): Promise<Response> {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const signedTransaction = getCookie(request, OAUTH_COOKIE);
  if (!code || !state || !signedTransaction) return jsonResponse({ error: "invalid_oauth_state" }, 400);

  let transaction: OAuthTransaction;
  try {
    transaction = await verifySignedJson<OAuthTransaction>(signedTransaction, required(env, "BROKER_SESSION_SECRET"));
  } catch {
    return jsonResponse({ error: "invalid_oauth_state" }, 400);
  }
  if (
    transaction.state !== state ||
    typeof transaction.verifier !== "string" ||
    typeof transaction.exp !== "number" ||
    transaction.exp <= seconds(now)
  ) {
    return jsonResponse({ error: "invalid_oauth_state" }, 400);
  }

  const tokenBody = new URLSearchParams({
    client_id: required(env, "GITHUB_APP_CLIENT_ID"),
    client_secret: required(env, "GITHUB_APP_CLIENT_SECRET"),
    code,
    redirect_uri: callbackUrl(request),
    code_verifier: transaction.verifier,
  });
  const tokenResponse = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/x-www-form-urlencoded" },
    body: tokenBody,
  });
  if (!tokenResponse.ok) return jsonResponse({ error: "github_oauth_failed" }, 502);
  const tokenData = await tokenResponse.json() as { access_token?: unknown };
  if (typeof tokenData.access_token !== "string" || tokenData.access_token.length === 0) {
    return jsonResponse({ error: "github_oauth_failed" }, 502);
  }

  const userResponse = await fetch("https://api.github.com/user", {
    headers: {
      Authorization: `Bearer ${tokenData.access_token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "chatgpt-lib-media-broker",
    },
  });
  if (!userResponse.ok) return jsonResponse({ error: "github_identity_failed" }, 502);
  const userData = await userResponse.json() as { id?: unknown };
  const ownerId = required(env, "OWNER_GITHUB_USER_ID");
  if (String(userData.id ?? "") !== ownerId) return jsonResponse({ error: "forbidden" }, 403);

  const brokerToken = await issueSession(ownerId, env, now);
  return new Response(callbackHtml(brokerToken, env.ALLOWED_ORIGIN), {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "Set-Cookie": oauthCookie("", 0),
    },
  });
}
