import type { BrokerEnv } from "./env";

const encoder = new TextEncoder();

export class RequestBodyError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RequestBodyError";
  }
}

export function corsHeaders(origin: string | null, env: Pick<BrokerEnv, "ALLOWED_ORIGIN">): Headers {
  const headers = new Headers({ Vary: "Origin" });
  if (origin === env.ALLOWED_ORIGIN) {
    headers.set("Access-Control-Allow-Origin", env.ALLOWED_ORIGIN);
    headers.set("Access-Control-Allow-Headers", "Authorization, Content-Type");
    headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  }
  return headers;
}

export function jsonResponse(body: unknown, status = 200, headers?: HeadersInit): Response {
  const responseHeaders = new Headers(headers);
  responseHeaders.set("Content-Type", "application/json; charset=utf-8");
  responseHeaders.set("Cache-Control", "no-store");
  return new Response(JSON.stringify(body), { status, headers: responseHeaders });
}

export async function readJsonBody(request: Request, maxBytes = 16 * 1024): Promise<unknown> {
  const contentLength = request.headers.get("content-length");
  if (contentLength !== null) {
    const parsedLength = Number(contentLength);
    if (Number.isFinite(parsedLength) && parsedLength > maxBytes) {
      throw new RequestBodyError("request body exceeds limit");
    }
  }

  const text = await request.text();
  if (encoder.encode(text).byteLength > maxBytes) {
    throw new RequestBodyError("request body exceeds limit");
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    throw new RequestBodyError("invalid JSON body");
  }
}
