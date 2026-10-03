import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WebManifest, WebWork, WorkSimilarity } from "../../data/types";
import { WorkDetailView } from "./WorkDetailPage";
import { buildWorkDetailView } from "./selectors";

function work(
  fingerprint: WebWork["semantic_fingerprint"],
  similarities: Record<string, WorkSimilarity[]> = {},
): WebWork {
  return {
    id: "arrival-2016",
    identity: { format: "movie", title_original: "Arrival", title_ru: "Прибытие", year: 2016 },
    metadata: { external: {} },
    viewer_signals: {},
    group_signals: {},
    interest: {},
    traits: fingerprint?.map((item) => item.term) ?? [],
    semantic_fingerprint: fingerprint,
    similarities,
    collections: [],
    provenance: { created_at: null, updated_at: null },
  };
}

function manifest(item: WebWork): WebManifest {
  return {
    schema_version: 3,
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

  it("renders explicit similarity for the active target with local links and external cards", () => {
    const item = work([], {
      primary: [
        {
          other: {
            kind: "canonical",
            id: "source-code-2011",
            title_original: "Source Code",
            title_ru: "Исходный код",
            year: 2011,
          },
          terms: ["story.intrigue"],
          note: "Оба держат интригой",
          updated_at: "2026-10-03T20:00:00+00:00",
          provenance: { source: "explicit" },
        },
        {
          other: {
            kind: "external",
            provider: "tmdb",
            media_type: "movie",
            id: 99999,
            title: "External Pick",
            year: 2024,
          },
          terms: [],
          note: null,
          updated_at: "2026-10-03T20:00:00+00:00",
          provenance: { source: "explicit" },
        },
      ],
    });
    const view = buildWorkDetailView(manifest(item), item.id, "primary")!;

    expect(view.similarities).toHaveLength(2);
    render(<WorkDetailView view={view} activeTarget="primary" />);
    expect(screen.getByRole("heading", { name: "Похожие фильмы" })).toBeInTheDocument();
    expect(screen.getByText("По твоему мнению")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Исходный код/ })).toHaveAttribute("href", "#/work/source-code-2011?target=primary");
    expect(screen.getByText("External Pick")).toBeInTheDocument();
  });
});
