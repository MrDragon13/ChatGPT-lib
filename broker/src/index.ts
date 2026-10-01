import type { BrokerEnv } from "./env";
import { finishAuth, startAuth, verifySession } from "./auth";
import { FeedbackValidationError, parseFeedbackInput } from "./feedback";
import { RequestBodyError, corsHeaders, jsonResponse, readJsonBody } from "./http";
import { OperationSubmissionError, submitFeedback } from "./operations";

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

function bearerToken(request: Request): string | null {
  const value = request.headers.get("authorization");
  if (!value) return null;
  const match = /^Bearer\s+(.+)$/i.exec(value);
  return match?.[1] ?? null;
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
      const token = bearerToken(request);
      if (!token) return responseWithCors(jsonResponse({ error: "unauthorized" }, 401), origin, env);

      let ownerId: string;
      try {
        ownerId = (await verifySession(token, env)).sub;
      } catch {
        return responseWithCors(jsonResponse({ error: "unauthorized" }, 401), origin, env);
      }

      const rate = await env.WRITE_RATE_LIMITER.limit({ key: `write:${ownerId}:/v1/feedback` });
      if (!rate.success) return responseWithCors(jsonResponse({ error: "rate_limited" }, 429), origin, env);

      try {
        const body = await readJsonBody(request);
        const input = parseFeedbackInput(body);
        const result = await submitFeedback(input, env);
        return responseWithCors(jsonResponse(result, 202), origin, env);
      } catch (error) {
        if (error instanceof RequestBodyError || error instanceof FeedbackValidationError) {
          return responseWithCors(jsonResponse({ error: "invalid_request" }, 422), origin, env);
        }
        if (error instanceof OperationSubmissionError) {
          return responseWithCors(jsonResponse({
            error: "github_operation_failed",
            operation_id: error.operationId,
          }, error.upstreamStatus === 503 ? 503 : 502), origin, env);
        }
        return responseWithCors(jsonResponse({ error: "broker_unavailable" }, 503), origin, env);
      }
    }

    return responseWithCors(jsonResponse({ error: "not_found" }, 404), origin, env);
  },
};

export default worker;
