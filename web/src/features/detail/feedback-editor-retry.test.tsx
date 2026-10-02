import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BrokerHttpError } from "../../broker/client";
import type { BrokerSessionValue } from "../../broker/BrokerSessionProvider";
import type { DetailSignal } from "./selectors";
import { FeedbackEditor } from "./FeedbackEditor";

const signal: DetailSignal = {
  target: "primary",
  rating: 8.5,
  reaction: "liked",
  viewingStatus: "watched",
  feedbackSummary: "Умная фантастика без суеты.",
};

describe("FeedbackEditor failed-operation retry", () => {
  it("allows saving again after a terminal failure", async () => {
    const submitFeedback = vi.fn(async () => ({
      operation_id: "11111111-2222-4333-8444-555555555555",
      pr_number: 42,
      status: "submitted" as const,
    }));
    const broker: BrokerSessionValue = {
      configured: true,
      authenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      submitFeedback,
      getOperationStatus: vi.fn(async () => ({
        status: "failed" as const,
        reason: "check_failed" as const,
        pr_number: 42,
      })),
    };

    render(
      <FeedbackEditor
        workId="arrival-2016"
        target="primary"
        signal={signal}
        broker={broker}
        refreshManifest={vi.fn(async () => undefined)}
        pollIntervalMs={1}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
    fireEvent.change(screen.getByRole("spinbutton", { name: "Оценка" }), { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    expect(await screen.findByText("Не удалось применить")).toBeInTheDocument();
    const save = screen.getByRole("button", { name: "Сохранить" });
    expect(save).toBeEnabled();

    fireEvent.click(save);
    await waitFor(() => expect(submitFeedback).toHaveBeenCalledTimes(2));
  });

  it("adopts the existing operation when the first submit response is lost", async () => {
    const operationId = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
    const activeOperation = Object.assign(
      new BrokerHttpError(409, "active_operation"),
      { operationId, prNumber: 37 },
    );
    const submitFeedback = vi.fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockRejectedValueOnce(activeOperation);
    const broker: BrokerSessionValue = {
      configured: true,
      authenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      submitFeedback,
      getOperationStatus: vi.fn(async () => ({ status: "checking" as const, pr_number: 37 })),
    };

    render(
      <FeedbackEditor
        workId="game-night-2018"
        target="partner"
        signal={{ ...signal, target: "partner", rating: null }}
        broker={broker}
        refreshManifest={vi.fn(async () => undefined)}
        pollIntervalMs={60_000}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
    fireEvent.change(screen.getByRole("spinbutton", { name: "Оценка" }), { target: { value: "7" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(submitFeedback).toHaveBeenCalledTimes(2));
    expect(screen.getByText("Изменение отправлено")).toBeInTheDocument();
    expect(screen.queryByText("Не удалось отправить изменение. Попробуйте ещё раз.")).not.toBeInTheDocument();
  });
});
