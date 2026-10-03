import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WebManifest, WebWork } from "../../data/types";
import { WorkDetailView } from "./WorkDetailPage";
import { buildWorkDetailView } from "./selectors";

function work(fingerprint: WebWork["semantic_fingerprint"]): WebWork {
  return {
    id: "arrival-2016",
    identity: { format: "movie", title_original: "Arrival", title_ru: "Прибытие", year: 2016 },
    metadata: { external: {} },
    viewer_signals: {},
    group_signals: {},
    interest: {},
    traits: fingerprint?.map((item) => item.term) ?? [],
    semantic_fingerprint: fingerprint,
    collections: [],
    provenance: { created_at: null, updated_at: null },
  };
}

function manifest(item: WebWork): WebManifest {
  return {
    schema_version: 2,
    default_target: "primary",
    targets: { viewers: ["primary", "partner"], groups: { couple: ["primary", "partner"] } },
    vocabulary: {
      "story.intrigue": { kind: "trait", label_ru: "Интрига" },
      "pacing.slow": { kind: "trait", label_ru: "Медленный темп" },
    },
    profiles: {},
    taste_contexts: {},
    recommendations: {},
    works: [item],
  };
}

describe("work semantic intelligence", () => {
  it("renders film traits separately from personal signals with human provenance and confidence", () => {
    const item = work([
      { term: "story.intrigue", source: "llm_inferred", confidence: "high" },
      { term: "pacing.slow", source: "external_source", confidence: "medium" },
    ]);
    const view = buildWorkDetailView(manifest(item), item.id, "primary")!;

    expect(view.fingerprint).toEqual([
      { term: "story.intrigue", label: "Интрига", source: "Вывод модели", confidence: "Высокая" },
      { term: "pacing.slow", label: "Медленный темп", source: "Внешний источник", confidence: "Средняя" },
    ]);

    render(<WorkDetailView view={view} activeTarget="primary" />);
    expect(screen.getByRole("heading", { name: "О фильме" })).toBeInTheDocument();
    expect(screen.getByText("Интрига")).toBeInTheDocument();
    expect(screen.getByText("Вывод модели · Высокая уверенность")).toBeInTheDocument();
  });

  it("does not invent or render a fingerprint section when canonical traits are absent", () => {
    const item = work([]);
    const view = buildWorkDetailView(manifest(item), item.id, "primary")!;
    expect(view.fingerprint).toEqual([]);
    render(<WorkDetailView view={view} activeTarget="primary" />);
    expect(screen.queryByRole("heading", { name: "О фильме" })).not.toBeInTheDocument();
  });
});
