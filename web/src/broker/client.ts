import type { FeedbackEditInput, OperationStatusResponse, SubmittedOperation } from "./types";

export class BrokerHttpError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
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
  const payload = await response.json().catch(() => ({})) as { error?: unknown } & T;
  if (!response.ok) {
    throw new BrokerHttpError(response.status, typeof payload.error === "string" ? payload.error : "broker_error");
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
