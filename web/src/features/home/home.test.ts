import { describe, expect, it } from "vitest";

import type { WebManifest, WebWork } from "../../data/types";
import { buildHomeViewModel } from "./selectors";

function work(
  id: string,
  options: {
    title?: string;
    primary?: Record<string, unknown>;
    partner?: Record<string, unknown>;
    provenance?: { created_at: string | null; updated_at: string | null };
  } = {},
): WebWork {
  return {
    id,
    identity: {
      title_ru: options.title ?? id,
      title_original: options.title ?? id,
      year: 2024,
    },
    metadata: { external: { runtime_min: 110, genres: ["genre.drama"] } },
    viewer_signals: {
      ...(options.primary ? { primary: options.primary } : {}),
      ...(options.partner ? { partner: options.partner } : {}),
    },
    group_signals: {},
    interest: {},
    traits: ["story.intrigue"],
    collections: [],
    provenance: options.provenance ?? { created_at: null, updated_at: null },
  };
}

function manifest(): WebManifest {
  return {
    schema_version: 1,
    default_target: "couple",
    targets: {
      viewers: ["partner", "primary"],
      groups: { couple: ["primary", "partner"] },
    },
    vocabulary: {
      "story.intrigue": { kind: "trait", label_ru: "Интрига" },
      "reaction.pacing_dragging": { kind: "feedback", label_ru: "Затянуто" },
      "genre.drama": { kind: "genre", label_ru: "Драма" },
    },
    profiles: {},
    recommendations: {
      primary: {
        target: "primary",
        request: { only_unwatched: true },
        candidates: [
          {
            id: "first-from-backend",
            title_ru: "Первый по контексту",
            evidence: {
              strengths: ["story.intrigue"],
              concerns: ["reaction.pacing_dragging"],
              viewing: { primary: "watched" },
            },
          },
          { id: "second", title_ru: "Второй", evidence: { strengths: [], concerns: [] } },
        ],
      },
      partner: {
        target: "partner",
        request: { only_unwatched: true },
        candidates: [{ id: "sparse-partner", title_ru: "Для партнёра", evidence: { strengths: [], concerns: [] } }],
      },
      couple: {
        target: "couple",
        request: { only_unwatched: true },
        candidates: [{ id: "together", title_ru: "Вместе", evidence: { strengths: ["story.intrigue"], concerns: [] } }],
      },
    },
    works: [
      work("first-from-backend", {
        title: "Первый по контексту",
        primary: { viewing: { status: "watched" }, rating: { score: 7 } },
      }),
      work("second", { title: "Второй" }),
      work("sparse-partner", {
        title: "Для партнёра",
        primary: { rating: { score: 9.5 }, reaction: { label: "loved" } },
        partner: { viewing: { status: "planned" } },
      }),
      work("together", { title: "Вместе" }),
      work("recent-explicit", {
        title: "Недавно явно",
        primary: { viewing: { status: "watched", last_watched_at: "2026-09-30T20:00:00Z" } },
        provenance: { created_at: "2026-01-01", updated_at: "2026-02-01" },
      }),
      work("recent-provenance", {
        title: "Недавно по записи",
        primary: { viewing: { status: "watched" } },
        provenance: { created_at: "2026-09-20", updated_at: "2026-09-29" },
      }),
      work("no-honest-date", {
        title: "Без даты",
        primary: { viewing: { status: "watched" } },
        provenance: { created_at: null, updated_at: null },
      }),
    ],
  };
}

describe("buildHomeViewModel", () => {
  it("uses the precomputed recommendation order without recalculating viewing eligibility", () => {
    const model = buildHomeViewModel(manifest(), "primary");
    expect(model.hero?.id).toBe("first-from-backend");
    expect(model.alternatives.map((item) => item.id)).toEqual(["second"]);
  });

  it("maps recommendation evidence through canonical vocabulary labels", () => {
    const model = buildHomeViewModel(manifest(), "primary");
    expect(model.hero?.reasonLabels).toEqual(["Интрига"]);
    expect(model.hero?.concernLabels).toEqual(["Затянуто"]);
    expect(model.hero?.genreLabels).toEqual(["Драма"]);
  });

  it("never copies primary rating or reaction into sparse partner data", () => {
    const model = buildHomeViewModel(manifest(), "partner");
    expect(model.hero?.id).toBe("sparse-partner");
    expect(model.hero?.personalRating).toBeNull();
    expect(model.hero?.personalReaction).toBeNull();
  });

  it("exposes a couple rail only when couple has usable precomputed candidates", () => {
    const withCouple = buildHomeViewModel(manifest(), "primary");
    expect(withCouple.couple.map((item) => item.id)).toEqual(["together"]);

    const withoutCoupleManifest = manifest();
    withoutCoupleManifest.recommendations.couple.candidates = [];
    expect(buildHomeViewModel(withoutCoupleManifest, "primary").couple).toEqual([]);
  });

  it("orders recent watched works by truthful watch/provenance dates and omits undated entries", () => {
    const model = buildHomeViewModel(manifest(), "primary");
    expect(model.recent.map((item) => [item.id, item.date])).toEqual([
      ["recent-explicit", "2026-09-30T20:00:00Z"],
      ["recent-provenance", "2026-09-29"],
    ]);
    expect(model.recent.some((item) => item.id === "no-honest-date")).toBe(false);
  });
});
