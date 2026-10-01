import { describe, expect, it } from "vitest";

import { sanitizeLogFields } from "../src/logging";

describe("broker logging boundary", () => {
  it("keeps only approved operational metadata", () => {
    const safe = sanitizeLogFields({
      route: "/v1/feedback",
      method: "POST",
      status: 502,
      operation_id: "11111111-1111-4111-8111-111111111111",
      pr_number: 42,
      github_request_id: "ABC:123",
      failure: "check_failed",
      authorization: "Bearer hidden",
      oauth_code: "hidden-code",
      cookie: "broker_oauth=hidden",
      github_token: "hidden-token",
      private_key: "hidden-key",
      client_secret: "hidden-secret",
      feedback_summary: "private review text",
    });

    expect(safe).toEqual({
      route: "/v1/feedback",
      method: "POST",
      status: 502,
      operation_id: "11111111-1111-4111-8111-111111111111",
      pr_number: 42,
      github_request_id: "ABC:123",
      failure: "check_failed",
    });
    expect(JSON.stringify(safe)).not.toContain("hidden");
    expect(JSON.stringify(safe)).not.toContain("private review text");
  });

  it("drops nested or object values even for approved keys", () => {
    expect(sanitizeLogFields({ route: { secret: "x" }, status: [200] })).toEqual({});
  });
});
