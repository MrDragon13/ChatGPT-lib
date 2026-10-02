import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { WebManifest } from "../../data/types";
import type { BrokerSessionValue } from "../../broker/BrokerSessionProvider";
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
        group_signals: {
          couple: {
            rating: { score: 8 },
            reaction: { value: "mixed" },
            feedback: { summary: "Общее мнение." },
          },
        },
        interest: {},
        traits: [],
        collections: [],
        provenance: { created_at: "2026-01-01", updated_at: "2026-02-01" },
      },
    ],
  };
}

describe("work detail editor target scope", () => {
  it("prefills and saves an existing couple impression as couple", async () => {
    appContext = {
      manifest: manifest(),
      target: "couple",
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
      <MemoryRouter initialEntries={["/work/arrival-2016?target=couple"]}>
        <Routes>
          <Route path="/work/:id" element={<WorkDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    const coupleHeading = screen.getByRole("heading", { name: "Вместе" });
    const coupleCard = coupleHeading.closest("article");
    expect(coupleCard).not.toBeNull();
    const couple = within(coupleCard!);

    fireEvent.click(couple.getByRole("button", { name: "Изменить общее впечатление" }));

    const form = screen.getByRole("form", { name: "Редактирование впечатления — Вместе" });
    expect(coupleCard).not.toContainElement(form);
    expect(form.closest(".feedback-editor-panel")).not.toBeNull();
    expect(form.querySelector(".feedback-form__heading")).toHaveTextContent("Сохранится в: Вместе");
    expect(within(form).getByLabelText("Оценка")).toHaveValue(8);
    expect(within(form).getByLabelText("Реакция")).toHaveValue("mixed");
    expect(within(form).getByLabelText("Отзыв")).toHaveValue("Общее мнение.");

    fireEvent.change(within(form).getByLabelText("Оценка"), { target: { value: "9" } });
    fireEvent.click(within(form).getByRole("button", { name: "Сохранить" }));
    await waitFor(() => expect(submitFeedback).toHaveBeenCalledWith({
      work_id: "arrival-2016",
      target: "couple",
      rating: 9,
    }));
  });
});
