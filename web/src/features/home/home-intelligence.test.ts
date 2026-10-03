import { describe, expect, it } from "vitest";

import type { WebManifest, WebWork } from "../../data/types";
import { buildHomeViewModel } from "./selectors";

function work(): WebWork {
  return {
    id: "arrival-2016",
    identity: { title_ru: "Прибытие", title_original: "Arrival", year: 2016 },
    metadata: { external: {} },
    viewer_signals: {},
    group_signals: {},
    interest: {},
    traits: ["story.intrigue"],
    semantic_fingerprint: [],
    collections: [],
    provenance: { created_at: null, updated_at: null },
  };
}

function manifest(): WebManifest {
  return {
    schema_version: 2,
    default_target: "primary",
    targets: { viewers: ["primary", "partner"], groups: { couple: ["primary", "partner"] } },
    vocabulary: {
      "story.intrigue": { kind: "trait", label_ru: "Интрига" },
      "pacing.slow": { kind: "trait", label_ru: "Медленный темп" },
    },
    profiles: {},
    taste_contexts: {
      primary: {
        schema_version: 1,
        target: "primary",
        profile: {
          explicit_preferences: [
            { id: "likes-intrigue", statement: "Люблю интригу", term: "story.intrigue", affinity: 1, confidence: "exact" },
          ],
          inferred_preferences: [
            {
              id: "slow-burn-pattern",
              statement: "Часто заходят медленные истории с сильной интригой.",
              affinity: 0.65,
              confidence: "medium",
              terms: ["pacing.slow", "story.intrigue"],
              evidence: [{ entity_id: "arrival-2016", kind: "rating_correlation" }],
            },
          ],
          rules: [],
          constraints: [],
          strongest_affinities: [
            {
              term: "story.intrigue",
              score: 0.82,
              confidence: "high",
              evidence_count: 4,
              evidence: [{ entity_id: "arrival-2016", source_kind: "explicit_feedback" }],
            },
          ],
          summary: {},
        },
        representative: { high: [], low: [] },
        recent_feedback: [],
        exclusions: { watched: [], not_interested: [] },
      },
      couple: {
        schema_version: 1,
        target: "couple",
        profile: {
          explicit_preferences: [], inferred_preferences: [], rules: [], constraints: [], strongest_affinities: [], summary: {},
        },
        representative: { high: [], low: [] },
        recent_feedback: [],
        exclusions: { watched: [], not_interested: [] },
        couple: {
          members: ["primary", "partner"],
          agreements: [{ id: "arrival-2016", ratings: { primary: 9, partner: 8.5 } }],
          disagreements: [{ id: "other-2019", ratings: { primary: 9, partner: 4 } }],
        },
      },
    },
    recommendations: {
      primary: { target: "primary", request: {}, candidates: [{ id: "arrival-2016" }] },
      couple: { target: "couple", request: {}, candidates: [] },
    },
    works: [work()],
  };
}

describe("home taste intelligence", () => {
  it("maps explicit and inferred taste separately with vocabulary labels and evidence", () => {
    const model = buildHomeViewModel(manifest(), "primary");
    expect(model.taste?.strongest).toEqual([
      { term: "story.intrigue", label: "Интрига", score: 0.82, confidence: "high", evidenceCount: 4 },
    ]);
    expect(model.taste?.explicit[0]).toMatchObject({ statement: "Люблю интригу", label: "Интрига" });
    expect(model.taste?.inferred[0]).toMatchObject({ statement: "Часто заходят медленные истории с сильной интригой.", confidence: "medium" });
  });

  it("exposes couple agreement and disagreement counts without averaging them", () => {
    const model = buildHomeViewModel(manifest(), "couple");
    expect(model.taste?.couple).toEqual({ agreements: 1, disagreements: 1 });
  });

  it("keeps the legacy v1/read-overlap state graceful when taste contexts are absent", () => {
    const value = manifest();
    value.schema_version = 1;
    delete value.taste_contexts;
    expect(buildHomeViewModel(value, "primary").taste).toBeNull();
  });
});
