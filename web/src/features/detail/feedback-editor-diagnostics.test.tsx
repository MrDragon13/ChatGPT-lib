import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BrokerHttpError } from "../../broker/client";
import type { BrokerSessionValue } from "../../broker/BrokerSessionProvider";
import { FeedbackEditor } from "./FeedbackEditor";

function brokerWithFailure(): BrokerSessionValue {
  const error = new BrokerHttpError(502, "github_unavailable");
  Object.assign(error, { stage: "installation_token", upstreamStatus: 404 });
  return {
    configured: true,
    authenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    submitFeedback: vi.fn(async () => { throw error; }),
    getOperationStatus: vi.fn(),
  };
}

describe("FeedbackEditor diagnostics", () => {
  it("shows a safe broker code, stage, and upstream status when submission fails", async () => {
    render(<FeedbackEditor
      workId="arrival-2016"
      target="primary"
      signal={{
        target: "primary",
        rating: 8,
        reaction: "unknown",
        viewingStatus: "watched",
        feedbackSummary: "Хороший.",
      }}
      broker={brokerWithFailure()}
      refreshManifest={vi.fn(async () => undefined)}
    />);

    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
    fireEvent.change(screen.getByLabelText("Оценка"), { target: { value: "8.5" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    expect(await screen.findByText(
      "Не удалось отправить изменение. Код: github_unavailable · этап: installation_token · HTTP 502 · GitHub 404.",
    )).toBeInTheDocument();
  });
});
