import { describe, expect, it } from "vitest";

import type { TargetId, WebManifest, WebWork } from "../../data/types";
import { buildHistoryItems } from "./selectors";

type Signal = Record<string, unknown>;

function work(
  id: string,
  options: {
    title?: string | null;
    year?: number | null;
    poster?: string | null;
    viewerSignals?: Record<string, Signal>;
    groupSignals?: Record<string, Signal>;
    createdAt?: string | null;
    updatedAt?: string | null;
  } = {},
): WebWork {
  const external: Record<string, unknown> = {};
  if (options.poster) external.assets = { poster: { provider: "tmdb", path: options.poster } };
  return {
    id,
    identity: {
      title_ru: options.title === undefined ? id : options.title,
      title_original: null,
      year: options.year ?? null,
    },
    metadata: { external },
    viewer_signals: options.viewerSignals ?? {},
    group_signals: options.groupSignals ?? {},
    interest: {},
    traits: [],
    collections: [],
    provenance: {
      created_at: options.createdAt ?? null,
      updated_at: options.updatedAt ?? null,
    },
  };
}

function manifest(works: WebWork[]): WebManifest {
  return {
    schema_version: 1,
    default_target: "couple",
    targets: { viewers: ["primary", "partner"], groups: { couple: ["primary", "partner"] } },
    vocabulary: {},
    profiles: {},
    recommendations: {},
    works,
  };
}

function itemIds(data: WebManifest, target: TargetId): string[] {
  return buildHistoryItems(data, target).map((item) => item.id);
}

describe("viewing history selector", () => {
  it("uses only the selected viewer signal", () => {
    const data = manifest([
      work("arrival", {
        viewerSignals: {
          primary: {
            rating: { score: 8.5 },
            feedback: { summary: "Мой отзыв" },
            history: [{ at: "2026-09-29T10:00:00Z" }],
          },
          partner: {
            rating: { score: 6 },
            feedback: { summary: "Другой отзыв" },
            history: [{ at: "2026-09-30T10:00:00Z" }],
          },
        },
        groupSignals: {
          couple: {
            rating: { score: 7 },
            feedback: { summary: "Общий отзыв" },
            history: [{ at: "2026-10-01T10:00:00Z" }],
          },
        },
      }),
    ]);

    const [item] = buildHistoryItems(data, "primary");
    expect(item.rating).toBe(8.5);
    expect(item.feedbackSummary).toBe("Мой отзыв");
    expect(item.activityAt).toBe("2026-09-29T10:00:00Z");
  });

  it("uses explicit group signals without inheriting member viewer history", () => {
    const data = manifest([
      work("grouped", {
        viewerSignals: {
          primary: { rating: { score: 10 }, history: [{ at: "2026-10-02T00:00:00Z" }] },
        },
        groupSignals: {
          couple: {
            reaction: { value: "liked" },
            history: [{ at: "2026-09-28T12:00:00Z" }],
          },
        },
      }),
      work("viewer-only", {
        viewerSignals: {
          primary: { rating: { score: 9 }, history: [{ at: "2026-10-03T00:00:00Z" }] },
        },
      }),
    ]);

    const items = buildHistoryItems(data, "couple");
    expect(items).toHaveLength(1);
    expect(items[0].id).toBe("grouped");
    expect(items[0].reaction).toBe("liked");
    expect(items[0].activityAt).toBe("2026-09-28T12:00:00Z");
  });

  it("does not treat viewing-only state as group history", () => {
    const data = manifest([
      work("invalid-group-viewing", {
        groupSignals: {
          couple: {
            viewing: { status: "watched" },
            history: [{ at: "2026-10-01T12:00:00Z" }],
          },
        },
      }),
    ]);

    expect(buildHistoryItems(data, "couple")).toEqual([]);
  });

  it("prefers the newest valid exact history timestamp over work provenance", () => {
    const data = manifest([
      work("exact", {
        viewerSignals: {
          primary: {
            viewing: { status: "watched" },
            history: [
              { at: "2026-09-29T20:00:00Z" },
              { at: "2026-09-30T20:00:00Z" },
            ],
          },
        },
        updatedAt: "2026-10-01",
      }),
    ]);

    expect(buildHistoryItems(data, "primary")[0]).toMatchObject({
      activityAt: "2026-09-30T20:00:00Z",
      activityPrecision: "exact",
    });
  });

  it("ignores malformed history timestamps and falls back to provenance", () => {
    const data = manifest([
      work("malformed", {
        viewerSignals: {
          primary: {
            viewing: { status: "watched" },
            history: [{ at: 42 }, { at: "not-a-date" }],
          },
        },
        createdAt: "2026-09-20",
        updatedAt: "2026-09-27",
      }),
    ]);

    expect(buildHistoryItems(data, "primary")[0]).toMatchObject({
      activityAt: "2026-09-27",
      activityPrecision: "day",
    });
  });

  it("uses created_at when a legacy signal has neither history nor updated_at", () => {
    const data = manifest([
      work("legacy", {
        viewerSignals: { primary: { reaction: { value: "mixed" } } },
        createdAt: "2026-09-18",
      }),
    ]);

    expect(buildHistoryItems(data, "primary")[0]).toMatchObject({
      activityAt: "2026-09-18",
      activityPrecision: "day",
    });
  });

  it("does not emit a phantom item for a signal containing only history", () => {
    const data = manifest([
      work("phantom", {
        viewerSignals: { primary: { history: [{ at: "2026-10-01T00:00:00Z" }] } },
        updatedAt: "2026-10-01",
      }),
    ]);

    expect(itemIds(data, "primary")).toEqual([]);
  });

  it("sorts newest first and uses ascending work id for equal activity", () => {
    const data = manifest([
      work("zeta", {
        viewerSignals: { primary: { rating: { score: 7 }, history: [{ at: "2026-10-01T10:00:00Z" }] } },
      }),
      work("alpha", {
        viewerSignals: { primary: { rating: { score: 8 }, history: [{ at: "2026-10-01T10:00:00Z" }] } },
      }),
      work("newest", {
        viewerSignals: { primary: { rating: { score: 9 }, history: [{ at: "2026-10-02T10:00:00Z" }] } },
      }),
    ]);

    expect(itemIds(data, "primary")).toEqual(["newest", "alpha", "zeta"]);
  });

  it("falls back safely when optional display metadata is absent", () => {
    const data = manifest([
      work("bare-id", {
        title: null,
        viewerSignals: { primary: { viewing: { status: "watched" } } },
        createdAt: "2026-09-10",
      }),
    ]);

    expect(buildHistoryItems(data, "primary")[0]).toMatchObject({
      id: "bare-id",
      title: "bare-id",
      year: null,
      posterUrl: null,
      rating: null,
      reaction: null,
      feedbackSummary: null,
    });
  });
});
