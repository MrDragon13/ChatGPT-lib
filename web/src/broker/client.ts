import type { FeedbackEditInput, OperationStatusResponse, SubmittedOperation } from "./types";

export class BrokerHttpError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    public readonly stage: string | null = null,
    public readonly upstreamStatus: number | null = null,
  ) {
    super(code);
    this.name = "BrokerHttpError";
  }
}

async function requestJson<T>(url: string, token: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("authorization", `Bearer ${token}`);
  if (init.body !== undefined) headers.set("content-type", "application/json");
  const response = await fetch(url, { ...init, headers });
  const payload = await response.json().catch(() => ({})) as {
    error?: unknown;
    stage?: unknown;
    upstream_status?: unknown;
  } & T;
  if (!response.ok) {
    throw new BrokerHttpError(
      response.status,
      typeof payload.error === "string" ? payload.error : "broker_error",
      typeof payload.stage === "string" ? payload.stage : null,
      typeof payload.upstream_status === "number" ? payload.upstream_status : null,
    );
  }
  return payload;
}

export async function submitFeedback(
  baseUrl: string,
  token: string,
  input: FeedbackEditInput,
): Promise<SubmittedOperation> {
  return requestJson<SubmittedOperation>(`${baseUrl}/v1/feedback`, token, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getOperationStatus(
  baseUrl: string,
  token: string,
  operationId: string,
): Promise<OperationStatusResponse> {
  return requestJson<OperationStatusResponse>(
    `${baseUrl}/v1/operations/${encodeURIComponent(operationId)}`,
    token,
  );
}
