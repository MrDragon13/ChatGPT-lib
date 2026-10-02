import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WebManifest, WebWork } from "../../data/types";
import { WorkDetailView } from "./WorkDetailPage";
import { buildWorkDetailView } from "./selectors";

function work(overrides: Partial<WebWork> = {}): WebWork {
  return {
    id: "arrival-2016",
    identity: {
      format: "movie",
      title_original: "Arrival",
      title_ru: "Прибытие",
      alternate_titles: ["Story of Your Life"],
      year: 2016,
    },
    metadata: {
      external: {
        runtime_min: 116,
        genres: ["genre.science_fiction", "genre.drama"],
        synopsis_short: "Лингвист пытается понять язык пришельцев.",
        directors: [{ name: "Дени Вильнёв" }],
        main_cast: [{ name: "Эми Адамс", character: "Louise Banks" }],
        assets: {
          poster: { provider: "tmdb", path: "/poster.jpg" },
          backdrop: { provider: "tmdb", path: "/backdrop.jpg" },
        },
        external_metrics: { tmdb: { score: 7.6, votes: 19000 } },
      },
    },
    viewer_signals: {
      primary: {
        viewing: { status: "watched" },
        rating: { score: 8.5 },
        reaction: { value: "liked" },
        feedback: { summary: "Умная фантастика без суеты." },
      },
      partner: {
        viewing: { status: "watched" },
        reaction: { value: "mixed" },
      },
    },
    group_signals: {
      couple: {
        rating: { score: 8 },
        feedback: { summary: "Хорошо работает для совместного просмотра." },
      },
    },
    interest: {},
    traits: ["story.intrigue"],
    collections: [],
    provenance: { created_at: "2026-01-01", updated_at: "2026-02-01" },
    ...overrides,
  };
}

function manifest(item = work()): WebManifest {
  return {
    schema_version: 1,
    default_target: "couple",
    targets: { viewers: ["primary", "partner"], groups: { couple: ["primary", "partner"] } },
    vocabulary: {
      "genre.science_fiction": { kind: "genre", label_ru: "Фантастика" },
      "genre.drama": { kind: "genre", label_ru: "Драма" },
    },
    profiles: {},
    recommendations: {},
    works: [item],
  };
}

describe("work detail", () => {
  it("keeps identity and personal signal ahead of the external TMDB rating", () => {
    const data = manifest();
    const view = buildWorkDetailView(data, "arrival-2016", "primary");
    expect(view?.title).toBe("Прибытие");
    expect(view?.activeSignal?.rating).toBe(8.5);
    expect(view?.externalRating).toBe(7.6);

    const { container } = render(<WorkDetailView view={view!} activeTarget="primary" />);
    const text = container.textContent ?? "";
    expect(text.indexOf("8.5"));
    expect(text.indexOf("TMDB")).toBeGreaterThan(text.indexOf("8.5"));
  });

  it("renders primary, partner and couple signals independently without filling missing fields", () => {
    const view = buildWorkDetailView(manifest(), "arrival-2016", "couple")!;
    expect(view.signals.primary?.rating).toBe(8.5);
    expect(view.signals.partner?.rating).toBeNull();
    expect(view.signals.partner?.reaction).toBe("mixed");
    expect(view.signals.couple?.rating).toBe(8);
  });

  it("sizes the signal grid to the number of real panels instead of reserving empty columns", () => {
    const sparse = work({
      viewer_signals: {
        primary: {
          viewing: { status: "watched" },
          rating: { score: 8 },
          feedback: { summary: "Хороший." },
        },
      },
      group_signals: {},
    });
    const view = buildWorkDetailView(manifest(sparse), sparse.id, "couple")!;
    const { container } = render(<WorkDetailView view={view} activeTarget="couple" />);
    expect(container.querySelector(".signal-grid")).toHaveClass("signal-grid--1");
    expect(container.querySelectorAll(".signal-panel")).toHaveLength(1);
  });

  it("presents the public TMDB score to one decimal place", () => {
    const rated = work({
      metadata: {
        external: {
          external_metrics: { tmdb: { score: 8.272, votes: 18874 } },
        },
      },
    });
    const view = buildWorkDetailView(manifest(rated), rated.id, "primary")!;
    render(<WorkDetailView view={view} activeTarget="primary" />);
    expect(screen.getByText("8.3")).toBeInTheDocument();
    expect(screen.queryByText("8.272")).not.toBeInTheDocument();
  });

  it("does not crash when optional artwork, runtime, synopsis and external metrics are missing", () => {
    const sparse = work({ metadata: { external: {} } });
    const view = buildWorkDetailView(manifest(sparse), sparse.id, "primary")!;
    expect(view.posterUrl).toBeNull();
    expect(view.backdropUrl).toBeNull();
    expect(view.runtimeMin).toBeNull();
    expect(view.synopsis).toBeNull();
    expect(view.externalRating).toBeNull();
    render(<WorkDetailView view={view} activeTarget="primary" />);
    expect(screen.getByRole("heading", { name: "Прибытие" })).toBeInTheDocument();
  });

  it("keeps a read-only fallback when no edit control is supplied", () => {
    const view = buildWorkDetailView(manifest(), "arrival-2016", "primary")!;
    render(<WorkDetailView view={view} activeTarget="primary" />);
    expect(screen.getByTestId("future-edit-boundary")).toHaveTextContent("Режим только для чтения");
  });

  it("renders the edit control beside the still-published canonical signal", () => {
    const view = buildWorkDetailView(manifest(), "arrival-2016", "primary")!;
    render(<WorkDetailView
      view={view}
      activeTarget="primary"
      editControl={<button type="button">Изменить впечатление</button>}
    />);
    expect(screen.getByText("8.5/10")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Изменить впечатление" })).toBeInTheDocument();
    expect(screen.queryByTestId("future-edit-boundary")).not.toBeInTheDocument();
  });
});
