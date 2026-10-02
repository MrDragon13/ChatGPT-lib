import { fireEvent, render, screen } from "@testing-library/react";
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
    default_target: "couple",
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

describe("work detail editor prefill", () => {
  it("prefills the existing primary impression when the default couple target has no group signal", () => {
    appContext = {
      manifest: manifest(),
      target: "couple",
      refreshManifest: vi.fn(async () => undefined),
    };
    brokerValue = {
      configured: true,
      authenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      submitFeedback: vi.fn(),
      getOperationStatus: vi.fn(),
    };

    render(
      <MemoryRouter initialEntries={["/work/arrival-2016?target=couple"]}>
        <Routes>
          <Route path="/work/:id" element={<WorkDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));

    expect(screen.getByLabelText("Оценка")).toHaveValue(8.5);
    expect(screen.getByLabelText("Впечатление")).toHaveValue("liked");
    expect(screen.getByLabelText("Отзыв")).toHaveValue("Умная фантастика без суеты.");
  });
});
