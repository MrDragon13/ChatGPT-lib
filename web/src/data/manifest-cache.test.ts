import { afterEach, describe, expect, it, vi } from "vitest";

import { loadManifest } from "./client";

const validManifest = {
  schema_version: 1,
  default_target: "couple",
  targets: { viewers: ["partner", "primary"], groups: { couple: ["primary", "partner"] } },
  vocabulary: {},
  profiles: {},
  recommendations: {},
  works: [],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("manifest cache policy", () => {
  it("bypasses the HTTP cache for initial and refreshed manifest loads", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => validManifest });
    vi.stubGlobal("fetch", fetchMock);

    await loadManifest();
    await loadManifest("operation-123");

    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    expect(String(fetchMock.mock.calls[1][0])).toContain("data/manifest.json?rev=operation-123");
  });
});
