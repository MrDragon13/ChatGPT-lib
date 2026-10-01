import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WebManifest, WebWork } from "../../data/types";
import { HistoryView } from "./HistoryPage";
import { buildHistoryItems } from "./selectors";

function work(
  id: string,
  title: string,
  viewerSignals: Record<string, Record<string, unknown>>,
): WebWork {
  return {
    id,
    identity: { format: "movie", title_original: title, title_ru: title, year: 2024 },
    metadata: { external: {} },
    viewer_signals: viewerSignals,
    group_signals: {},
    interest: {},
    traits: [],
    collections: [],
    provenance: { created_at: "2026-09-01", updated_at: null },
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

describe("viewing history page", () => {
  it("renders newest history activity before older activity", () => {
    const data = manifest([
      work("older", "Старый отзыв", {
        primary: { rating: { score: 7 }, history: [{ at: "2026-09-20T10:00:00Z" }] },
      }),
      work("newer", "Новый отзыв", {
        primary: { rating: { score: 9 }, history: [{ at: "2026-10-01T10:00:00Z" }] },
      }),
    ]);

    render(<HistoryView items={buildHistoryItems(data, "primary")} target="primary" reduceMotion />);
    const links = screen.getAllByRole("link");
    expect(links[0]).toHaveTextContent("Новый отзыв");
    expect(links[1]).toHaveTextContent("Старый отзыв");
  });

  it("shows the selected target rating, reaction and feedback summary", () => {
    const data = manifest([
      work("arrival", "Прибытие", {
        primary: {
          rating: { score: 8.5 },
          reaction: { value: "liked" },
          feedback: { summary: "Умная фантастика без суеты." },
          history: [{ at: "2026-10-01T12:00:00Z" }],
        },
      }),
    ]);

    render(<HistoryView items={buildHistoryItems(data, "primary")} target="primary" reduceMotion />);
    expect(screen.getByText("8.5/10")).toBeInTheDocument();
    expect(screen.getByText("Понравилось")).toBeInTheDocument();
    expect(screen.getByText("Умная фантастика без суеты.")).toBeInTheDocument();
  });

  it("changes visible history when the active target changes", () => {
    const data = manifest([
      work("mine", "Для меня", {
        primary: { reaction: { value: "liked" }, history: [{ at: "2026-10-01T11:00:00Z" }] },
      }),
      work("theirs", "Для партнёра", {
        partner: { reaction: { value: "mixed" }, history: [{ at: "2026-10-01T12:00:00Z" }] },
      }),
    ]);

    const { rerender } = render(
      <HistoryView items={buildHistoryItems(data, "primary")} target="primary" reduceMotion />,
    );
    expect(screen.getByText("Для меня")).toBeInTheDocument();
    expect(screen.queryByText("Для партнёра")).not.toBeInTheDocument();

    rerender(<HistoryView items={buildHistoryItems(data, "partner")} target="partner" reduceMotion />);
    expect(screen.queryByText("Для меня")).not.toBeInTheDocument();
    expect(screen.getByText("Для партнёра")).toBeInTheDocument();
  });

  it("preserves the active target in work links", () => {
    const data = manifest([
      work("arrival-2016", "Прибытие", {
        partner: { rating: { score: 8 }, history: [{ at: "2026-10-01T12:00:00Z" }] },
      }),
    ]);

    render(<HistoryView items={buildHistoryItems(data, "partner")} target="partner" reduceMotion />);
    expect(screen.getByRole("link", { name: /Прибытие/ })).toHaveAttribute(
      "href",
      "#/work/arrival-2016?target=partner",
    );
  });

  it("renders a concise empty state", () => {
    render(<HistoryView items={[]} target="couple" reduceMotion />);
    expect(screen.getByRole("heading", { name: "Здесь пока пусто" })).toBeInTheDocument();
    expect(screen.getByText("После просмотра или отзыва фильм появится здесь.")).toBeInTheDocument();
  });
});
