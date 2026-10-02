import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { BrokerSessionValue } from "../../broker/BrokerSessionProvider";
import type { WebManifest } from "../../data/types";
import { WorkDetailPage } from "./WorkDetailPage";

let appContext: {
  manifest: WebManifest;
  target: string;
  refreshManifest(cacheBust?: string): Promise<void>;
};
let brokerValue: BrokerSessionValue;

vi.mock("../../app/AppShell", () => ({
  useAppContext: () => appContext,
}));

vi.mock("../../broker/BrokerSessionProvider", () => ({
  useBrokerSession: () => brokerValue,
}));

function manifest(): WebManifest {
  return {
    schema_version: 1,
    default_target: "primary",
    targets: { viewers: ["partner", "primary"], groups: { couple: ["primary", "partner"] } },
    vocabulary: {},
    profiles: {},
    recommendations: {},
    works: [
      {
        id: "arrival-2016",
        identity: { format: "movie", title_ru: "Прибытие", title_original: "Arrival", year: 2016 },
        metadata: { external: {} },
        viewer_signals: {
          primary: {
            viewing: { status: "watched" },
            rating: { score: 8.5 },
            reaction: { value: "liked" },
            feedback: { summary: "Умная фантастика без суеты." },
          },
        },
        group_signals: {},
        interest: {},
        traits: [],
        collections: [],
        provenance: { created_at: "2026-01-01", updated_at: "2026-02-01" },
      },
    ],
  };
}

function renderPage(target: "primary" | "couple") {
  appContext = {
    manifest: manifest(),
    target,
    refreshManifest: vi.fn(async () => undefined),
  };
  const submitFeedback = vi.fn(async () => ({
    operation_id: "11111111-2222-4333-8444-555555555555",
    pr_number: 42,
    status: "submitted" as const,
  }));
  brokerValue = {
    configured: true,
    authenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    submitFeedback,
    getOperationStatus: vi.fn(async () => ({ status: "submitted" as const, pr_number: 42 })),
  };

  render(
    <MemoryRouter initialEntries={[`/work/arrival-2016?target=${target}`]}>
      <Routes>
        <Route path="/work/:id" element={<WorkDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
  return submitFeedback;
}

describe("personal-first target editing", () => {
  it("uses Я consistently for the primary signal", () => {
    renderPage("primary");
    expect(screen.getByRole("heading", { name: "Я" })).toBeInTheDocument();
  });

  it("opens a target-named editor outside the compact signal panel", () => {
    renderPage("primary");

    const primaryPanel = screen.getByRole("heading", { name: "Я" }).closest(".signal-panel");
    expect(primaryPanel).not.toBeNull();

    const edit = within(primaryPanel as HTMLElement).getByRole("button", { name: "Изменить моё впечатление" });
    expect(edit).toHaveTextContent("Изменить");
    fireEvent.click(edit);

    const form = screen.getByRole("form", { name: "Редактирование впечатления — Я" });
    expect(primaryPanel).not.toContainElement(form);
    expect(form.closest(".feedback-editor-panel")).not.toBeNull();
    expect(screen.getByLabelText("Оценка")).toHaveValue(8.5);
    expect(screen.getByLabelText("Реакция")).toHaveValue("liked");
    expect(screen.getByLabelText("Отзыв")).toHaveValue("Умная фантастика без суеты.");
    expect(screen.getByText("Сохранится в: Я")).toBeInTheDocument();
  });

  it("keeps an empty Вместе record distinct and copies Я only on explicit request", async () => {
    const submitFeedback = renderPage("couple");

    expect(screen.getByText("Пока нет общего впечатления.")).toBeInTheDocument();
    const couplePanel = screen.getByRole("heading", { name: "Вместе" }).closest(".signal-panel");
    expect(couplePanel).not.toBeNull();
    const add = within(couplePanel as HTMLElement).getByRole("button", { name: "Добавить общее впечатление" });
    expect(add).toHaveTextContent("Добавить");
    fireEvent.click(add);

    expect(screen.getByRole("form", { name: "Редактирование впечатления — Вместе" })).toBeInTheDocument();
    expect(screen.getByText("Сохранится в: Вместе")).toBeInTheDocument();
    expect(screen.getByLabelText("Оценка")).toHaveValue(null);
    expect(screen.getByLabelText("Реакция")).toHaveValue("unknown");
    expect(screen.getByLabelText("Отзыв")).toHaveValue("");

    fireEvent.click(screen.getByRole("button", { name: "Взять «Я» за основу" }));

    expect(screen.getByText("Взято за основу: Я")).toBeInTheDocument();
    expect(screen.getByText("Сохранится в: Вместе")).toBeInTheDocument();
    expect(screen.getByLabelText("Оценка")).toHaveValue(8.5);
    expect(screen.getByLabelText("Реакция")).toHaveValue("liked");
    expect(screen.getByLabelText("Отзыв")).toHaveValue("Умная фантастика без суеты.");

    fireEvent.change(screen.getByLabelText("Оценка"), { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(submitFeedback).toHaveBeenCalledWith({
      work_id: "arrival-2016",
      target: "couple",
      rating: 9,
      reaction: "liked",
      feedback_summary: "Умная фантастика без суеты.",
    }));
  });
});
