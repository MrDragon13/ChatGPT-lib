import type { BrokerEnv } from "./env";
import { finishAuth, startAuth } from "./auth";
import { FeedbackValidationError, parseFeedbackInput } from "./feedback";
import { RequestBodyError, corsHeaders, jsonResponse, readJsonBody } from "./http";

function responseWithCors(response: Response, origin: string | null, env: BrokerEnv): Response {
  const headers = new Headers(response.headers);
  const cors = corsHeaders(origin, env);
  cors.forEach((value, key) => headers.set(key, value));
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

async function authRateLimited(env: BrokerEnv, route: string): Promise<boolean> {
  const result = await env.AUTH_RATE_LIMITER.limit({ key: `auth:${route}` });
  return !result.success;
}

const worker = {
  async fetch(request: Request, env: BrokerEnv): Promise<Response> {
    const url = new URL(request.url);
    const origin = request.headers.get("origin");

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin, env) });
    }

    if (request.method === "GET" && (url.pathname === "/v1/auth/start" || url.pathname === "/v1/auth/callback")) {
      if (await authRateLimited(env, url.pathname)) {
        return responseWithCors(jsonResponse({ error: "rate_limited" }, 429), origin, env);
      }
      try {
        const response = url.pathname === "/v1/auth/start"
          ? await startAuth(request, env)
          : await finishAuth(request, env);
        return responseWithCors(response, origin, env);
      } catch {
        return responseWithCors(jsonResponse({ error: "auth_unavailable" }, 503), origin, env);
      }
    }

    if (request.method === "POST" && url.pathname === "/v1/feedback") {
      try {
        const body = await readJsonBody(request);
        parseFeedbackInput(body);
        return responseWithCors(
          jsonResponse({ error: "not_implemented" }, 501),
          origin,
          env,
        );
      } catch (error) {
        if (error instanceof RequestBodyError || error instanceof FeedbackValidationError) {
          return responseWithCors(jsonResponse({ error: "invalid_request" }, 422), origin, env);
        }
        throw error;
      }
    }

    return responseWithCors(jsonResponse({ error: "not_found" }, 404), origin, env);
  },
};

export default worker;
