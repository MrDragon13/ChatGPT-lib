import { describe, expect, it } from "vitest";

import type { WebManifest } from "./types";


describe("WebManifest v2 intelligence contract", () => {
  it("types structured semantic fingerprints and taste contexts", () => {
    const manifest: WebManifest = {
      schema_version: 2,
      default_target: "primary",
      targets: { viewers: ["primary", "partner"], groups: { couple: ["primary", "partner"] } },
      vocabulary: {
        "story.intrigue": { label_ru: "Интрига", kind: "trait" },
      },
      profiles: {},
      taste_contexts: {
        primary: {
          schema_version: 1,
          target: "primary",
          profile: {
            explicit_preferences: [],
            inferred_preferences: [
              {
                id: "intrigue-pattern",
                statement: "Повторяется любовь к интриге.",
                affinity: 0.8,
                confidence: "medium",
                terms: ["story.intrigue"],
                evidence: [{ entity_id: "arrival-2016", kind: "rating_correlation" }],
              },
            ],
            rules: [],
            constraints: [],
            strongest_affinities: [
              {
                term: "story.intrigue",
                score: 0.8,
                confidence: "medium",
                evidence_count: 1,
                evidence: [{ entity_id: "arrival-2016", source_kind: "rating_trait" }],
              },
            ],
            summary: {},
          },
          representative: { high: [], low: [] },
          recent_feedback: [],
          exclusions: { watched: [], not_interested: [] },
        },
      },
      recommendations: {},
      works: [
        {
          id: "arrival-2016",
          identity: {
            format: "movie",
            medium: "live_action",
            title_original: "Arrival",
            title_ru: "Прибытие",
            alternate_titles: [],
            year: 2016,
          },
          metadata: { external: {} },
          viewer_signals: {},
          group_signals: {},
          interest: {},
          traits: ["story.intrigue"],
          semantic_fingerprint: [
            { term: "story.intrigue", source: "llm_inferred", confidence: "high" },
          ],
          collections: [],
          provenance: {},
        },
      ],
    };

    expect(manifest.schema_version).toBe(2);
    expect(manifest.works[0].semantic_fingerprint[0].term).toBe("story.intrigue");
    expect(manifest.taste_contexts.primary.profile.inferred_preferences[0].affinity).toBe(0.8);
  });
});
