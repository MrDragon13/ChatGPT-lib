import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { AppShell } from "../../app/AppShell";
import { HomePage } from "./HomePage";

const manifest = {
  schema_version: 2,
  default_target: "primary",
  targets: { viewers: ["primary", "partner"], groups: { couple: ["primary", "partner"] } },
  vocabulary: { "story.intrigue": { kind: "trait", label_ru: "Интрига" } },
  profiles: {},
  taste_contexts: {
    primary: {
      schema_version: 1,
      target: "primary",
      profile: {
        explicit_preferences: [],
        inferred_preferences: [{
          id: "intrigue-pattern",
          statement: "Часто заходят истории с сильной интригой.",
          affinity: 0.7,
          confidence: "medium",
          terms: ["story.intrigue"],
          evidence: [{ entity_id: "arrival-2016", kind: "rating_correlation" }],
        }],
        rules: [], constraints: [], strongest_affinities: [], summary: {},
      },
      representative: { high: [], low: [] },
      recent_feedback: [],
      exclusions: { watched: [], not_interested: [] },
    },
  },
  recommendations: {
    primary: { target: "primary", request: {}, candidates: [{ id: "arrival-2016" }] },
  },
  works: [{
    id: "arrival-2016",
    identity: { title_ru: "Прибытие", title_original: "Arrival", year: 2016 },
    metadata: { external: {} },
    viewer_signals: {}, group_signals: {}, interest: {}, traits: [], semantic_fingerprint: [], collections: [],
    provenance: { created_at: null, updated_at: null },
  }],
};

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("taste evidence disclosure", () => {
  it("expands concrete evidence works for an inferred hypothesis", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, json: async () => manifest } as Response)));

    render(
      <MemoryRouter initialEntries={["/today?target=primary"]}>
        <AppShell><HomePage /></AppShell>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Часто заходят истории с сильной интригой.")).toBeInTheDocument();
    const disclosure = screen.getByText("Почему система так думает?");
    fireEvent.click(disclosure);
    expect(screen.getByRole("link", { name: "Прибытие" })).toHaveAttribute("href", "#/work/arrival-2016?target=primary");
  });
});
