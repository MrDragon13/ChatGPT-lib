import { describe, expect, it } from "vitest";

import worker from "../src/index";
import { corsHeaders } from "../src/http";

const env = {
  ALLOWED_ORIGIN: "https://mrdragon13.github.io",
} as never;

describe("HTTP boundary", () => {
  it("allows only the configured Pages origin", () => {
    expect(corsHeaders("https://mrdragon13.github.io", env).get("Access-Control-Allow-Origin"))
      .toBe("https://mrdragon13.github.io");
    expect(corsHeaders("https://evil.example", env).has("Access-Control-Allow-Origin")).toBe(false);
  });

  it("returns 404 for unknown routes", async () => {
    const response = await worker.fetch(new Request("https://broker.example/v1/nope"), env);
    expect(response.status).toBe(404);
  });

  it("returns 422 for invalid feedback JSON", async () => {
    const response = await worker.fetch(new Request("https://broker.example/v1/feedback", {
      method: "POST",
      headers: { "content-type": "application/json", origin: "https://mrdragon13.github.io" },
      body: "{",
    }), env);
    expect(response.status).toBe(422);
  });

  it("returns 422 before parsing JSON bodies larger than 16 KiB", async () => {
    const response = await worker.fetch(new Request("https://broker.example/v1/feedback", {
      method: "POST",
      headers: { "content-type": "application/json", origin: "https://mrdragon13.github.io" },
      body: JSON.stringify({ work_id: "x", target: "primary", feedback_summary: "a".repeat(17000) }),
    }), env);
    expect(response.status).toBe(422);
  });
});
