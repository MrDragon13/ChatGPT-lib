import { afterEach, describe, expect, it, vi } from "vitest";

import { BrokerHttpError, getOperationStatus, submitFeedback } from "./client";
import { brokerBaseUrl } from "./config";

afterEach(() => vi.restoreAllMocks());

describe("broker client", () => {
  it("treats a missing or blank broker URL as read-only configuration", () => {
    expect(brokerBaseUrl(undefined)).toBeNull();
    expect(brokerBaseUrl("   ")).toBeNull();
    expect(brokerBaseUrl("https://broker.example/" )).toBe("https://broker.example");
  });

  it("submits feedback with the broker bearer token", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      operation_id: "11111111-2222-4333-8444-555555555555",
      pr_number: 42,
      status: "submitted",
    }), { status: 202, headers: { "content-type": "application/json" } }));

    const result = await submitFeedback("https://broker.example", "broker-token", {
      work_id: "game-night-2018",
      target: "primary",
      rating: 8.5,
    });

    expect(result.status).toBe("submitted");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [request, init] = fetchMock.mock.calls[0];
    expect(String(request)).toBe("https://broker.example/v1/feedback");
    expect(new Headers(init?.headers).get("authorization")).toBe("Bearer broker-token");
    expect(JSON.parse(String(init?.body))).toEqual({ work_id: "game-night-2018", target: "primary", rating: 8.5 });
  });

  it("preserves active operation metadata from a 409 response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      error: "active_operation",
      operation_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
      pr_number: 37,
    }), {
      status: 409,
      headers: { "content-type": "application/json" },
    }));

    await expect(submitFeedback("https://broker.example", "broker-token", {
      work_id: "game-night-2018",
      target: "partner",
      rating: 7,
    })).rejects.toMatchObject({
      status: 409,
      code: "active_operation",
      operationId: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
      prNumber: 37,
    });
  });

  it("surfaces 401 as a typed broker error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    }));

    await expect(getOperationStatus("https://broker.example", "expired", "11111111-2222-4333-8444-555555555555"))
      .rejects.toMatchObject<Partial<BrokerHttpError>>({ status: 401, code: "unauthorized" });
  });
});
