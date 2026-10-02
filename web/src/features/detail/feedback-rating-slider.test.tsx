import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { BrokerSessionValue } from "../../broker/BrokerSessionProvider";
import type { DetailSignal } from "./selectors";
import { FeedbackEditor } from "./FeedbackEditor";

const signal: DetailSignal = {
  target: "primary",
  rating: 8.5,
  reaction: "liked",
  viewingStatus: "watched",
  feedbackSummary: "Хороший фильм.",
};

const broker: BrokerSessionValue = {
  configured: true,
  authenticated: true,
  login: vi.fn(),
  logout: vi.fn(),
  submitFeedback: vi.fn(async () => ({ operation_id: "op", pr_number: 1, status: "submitted" as const })),
  getOperationStatus: vi.fn(async () => ({ status: "submitted" as const, pr_number: 1 })),
};

function openEditor(signalValue: DetailSignal | null = signal) {
  render(
    <FeedbackEditor
      workId="arrival-2016"
      target="primary"
      signal={signalValue}
      broker={broker}
      refreshManifest={vi.fn(async () => undefined)}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: signalValue ? "Изменить впечатление" : "Добавить моё впечатление" }));
}

describe("FeedbackEditor rating slider", () => {
  it("keeps the numeric rating and slider synchronized in both directions", () => {
    openEditor();

    const input = screen.getByLabelText("Оценка");
    const slider = screen.getByRole("slider", { name: "Оценка, ползунок" });
    expect(input).toHaveValue(8.5);
    expect(slider).toHaveValue("8.5");

    fireEvent.change(slider, { target: { value: "9" } });
    expect(input).toHaveValue(9);

    fireEvent.change(input, { target: { value: "7.5" } });
    expect(slider).toHaveValue("7.5");
  });

  it("keeps an unrated numeric field empty until the slider is moved", () => {
    openEditor(null);

    const input = screen.getByLabelText("Оценка");
    const slider = screen.getByRole("slider", { name: "Оценка, ползунок" });
    expect(input).toHaveValue(null);
    expect(slider).toHaveValue("5.5");

    fireEvent.change(slider, { target: { value: "6" } });
    expect(input).toHaveValue(6);
  });
});
