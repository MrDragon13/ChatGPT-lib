import type { BrokerEnv } from "./env";
import { finishAuth, startAuth, verifySession } from "./auth";
import { FeedbackValidationError, parseFeedbackInput } from "./feedback";
import { GitHubApiError } from "./github";
import { RequestBodyError, corsHeaders, jsonResponse, readJsonBody } from "./http";
import {
  OperationSubmissionError,
  findActiveOperation,
  getOperationStatus,
  submitFeedback,
} from "./operations";

function responseWithCors(response: Response, origin: string | null, env: BrokerEnv): Response {
  const headers = new Headers(response.headers);
  const cors = corsHeaders(origin, env);
  cors.forEach((value, key) => headers.set(key, value));
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

function clientNetworkSignal(request: Request): string {
  return request.headers.get("cf-connecting-ip")?.trim() || "unknown";
}

async function authRateLimited(request: Request, env: BrokerEnv, route: string): Promise<boolean> {
  const result = await env.AUTH_RATE_LIMITER.limit({ key: `auth:${route}:${clientNetworkSignal(request)}` });
  return !result.success;
}

async function statusRateLimited(env: BrokerEnv, ownerId: string): Promise<boolean> {
  const result = await env.AUTH_RATE_LIMITER.limit({ key: `status:${ownerId}` });
  return !result.success;
}

function bearerToken(request: Request): string | null {
  const value = request.headers.get("authorization");
  if (!value) return null;
  const match = /^Bearer\s+(.+)$/i.exec(value);
  return match?.[1] ?? null;
}

async function authorizedOwner(request: Request, env: BrokerEnv): Promise<string | null> {
  const token = bearerToken(request);
  if (!token) return null;
  try {
    return (await verifySession(token, env)).sub;
  } catch {
    return null;
  }
}

const operationPath = /^\/v1\/operations\/([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$/i;

const worker = {
  async fetch(request: Request, env: BrokerEnv): Promise<Response> {
    const url = new URL(request.url);
    const origin = request.headers.get("origin");

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin, env) });
    }

    if (request.method === "GET" && (url.pathname === "/v1/auth/start" || url.pathname === "/v1/auth/callback")) {
      if (await authRateLimited(request, env, url.pathname)) {
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
      const ownerId = await authorizedOwner(request, env);
      if (!ownerId) return responseWithCors(jsonResponse({ error: "unauthorized" }, 401), origin, env);

      const rate = await env.WRITE_RATE_LIMITER.limit({ key: `write:${ownerId}:/v1/feedback` });
      if (!rate.success) return responseWithCors(jsonResponse({ error: "rate_limited" }, 429), origin, env);

      try {
        const body = await readJsonBody(request);
        const input = parseFeedbackInput(body);
        const active = await findActiveOperation(input.work_id, input.target, env);
        if (active) {
          return responseWithCors(jsonResponse({
            error: "active_operation",
            operation_id: active.operation_id,
            pr_number: active.pr_number,
          }, 409), origin, env);
        }
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
        if (error instanceof GitHubApiError) {
          return responseWithCors(jsonResponse({ error: "github_unavailable" }, 502), origin, env);
        }
        return responseWithCors(jsonResponse({ error: "broker_unavailable" }, 503), origin, env);
      }
    }

    const operationMatch = request.method === "GET" ? operationPath.exec(url.pathname) : null;
    if (operationMatch) {
      const ownerId = await authorizedOwner(request, env);
      if (!ownerId) return responseWithCors(jsonResponse({ error: "unauthorized" }, 401), origin, env);
      if (await statusRateLimited(env, ownerId)) {
        return responseWithCors(jsonResponse({ error: "rate_limited" }, 429), origin, env);
      }
      try {
        const status = await getOperationStatus(operationMatch[1], env);
        return responseWithCors(jsonResponse(status), origin, env);
      } catch (error) {
        if (error instanceof GitHubApiError) {
          return responseWithCors(jsonResponse({ error: "github_unavailable" }, 502), origin, env);
        }
        return responseWithCors(jsonResponse({ error: "broker_unavailable" }, 503), origin, env);
      }
    }

    return responseWithCors(jsonResponse({ error: "not_found" }, 404), origin, env);
  },
};

export default worker;
