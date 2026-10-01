import { describe, expect, it } from "vitest";

import worker from "../src/index";
import { corsHeaders, readJsonBody } from "../src/http";

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

  it("rejects invalid JSON in the bounded body reader", async () => {
    await expect(readJsonBody(new Request("https://broker.example", {
      method: "POST",
      body: "{",
    }))).rejects.toThrow(/invalid json/i);
  });

  it("rejects JSON bodies larger than 16 KiB", async () => {
    await expect(readJsonBody(new Request("https://broker.example", {
      method: "POST",
      body: JSON.stringify({ feedback_summary: "a".repeat(17000) }),
    }))).rejects.toThrow(/exceeds limit/i);
  });
});
