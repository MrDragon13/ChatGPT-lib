import { afterEach, describe, expect, it, vi } from "vitest";

import { tmdbImageUrl } from "./assets";
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

const validManifestV2 = {
  ...validManifest,
  schema_version: 2,
  taste_contexts: {},
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("loadManifest", () => {
  it("loads manifest v1 during rollout compatibility", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => validManifest }));
    await expect(loadManifest()).resolves.toEqual(validManifest);
  });

  it("loads the current manifest v2", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => validManifestV2 }));
    await expect(loadManifest()).resolves.toEqual(validManifestV2);
  });

  it("adds a cache-busting revision only when requested", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => validManifestV2 });
    vi.stubGlobal("fetch", fetchMock);
    await loadManifest("operation-123");
    expect(String(fetchMock.mock.calls[0][0])).toContain("data/manifest.json?rev=operation-123");
  });

  it("rejects an unsupported future schema version in Russian", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...validManifestV2, schema_version: 3 }) }));
    await expect(loadManifest()).rejects.toThrow("Версия данных медиатеки не поддерживается");
  });

  it("reports a missing manifest in Russian", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404 }));
    await expect(loadManifest()).rejects.toThrow("Не удалось загрузить медиатеку");
  });
});

describe("tmdbImageUrl", () => {
  it("returns null for a missing provider path", () => {
    expect(tmdbImageUrl(null, "w500")).toBeNull();
  });

  it("centralizes TMDB image URL construction", () => {
    expect(tmdbImageUrl("/poster.jpg", "w500")).toBe("https://image.tmdb.org/t/p/w500/poster.jpg");
  });
});
