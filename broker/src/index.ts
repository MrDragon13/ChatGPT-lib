import type { BrokerEnv } from "./env";
import { FeedbackValidationError, parseFeedbackInput } from "./feedback";
import { RequestBodyError, corsHeaders, jsonResponse, readJsonBody } from "./http";

function responseWithCors(response: Response, origin: string | null, env: BrokerEnv): Response {
  const headers = new Headers(response.headers);
  const cors = corsHeaders(origin, env);
  cors.forEach((value, key) => headers.set(key, value));
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

const worker = {
  async fetch(request: Request, env: BrokerEnv): Promise<Response> {
    const url = new URL(request.url);
    const origin = request.headers.get("origin");

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin, env) });
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
