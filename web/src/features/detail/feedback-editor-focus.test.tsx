import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { BrokerSessionValue } from "../../broker/BrokerSessionProvider";
import { FeedbackEditor } from "./FeedbackEditor";

const operationId = "11111111-2222-4333-8444-555555555555";

function broker(overrides: Partial<BrokerSessionValue> = {}): BrokerSessionValue {
  return {
    configured: true,
    authenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    submitFeedback: vi.fn(async () => ({
      operation_id: operationId,
      pr_number: 42,
      status: "submitted" as const,
    })),
    getOperationStatus: vi.fn(async () => ({ status: "submitted" as const, pr_number: 42 })),
    ...overrides,
  };
}

function submitPartnerRating(brokerValue: BrokerSessionValue, pollIntervalMs?: number) {
  const refreshManifest = vi.fn(async () => undefined);
  render(
    <FeedbackEditor
      workId="groundhog-day-1993"
      target="partner"
      signal={null}
      broker={brokerValue}
      refreshManifest={refreshManifest}
      {...(pollIntervalMs === undefined ? {} : { pollIntervalMs })}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Добавить впечатление партнёра" }));
  fireEvent.change(screen.getByLabelText("Оценка"), { target: { value: "7" } });
  fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
  return refreshManifest;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("FeedbackEditor status refresh", () => {
  it("polls immediately when the window regains focus", async () => {
    const getOperationStatus = vi.fn(async () => ({
      status: "published" as const,
      pr_number: 42,
      merge_sha: "merge-sha",
    }));
    const brokerValue = broker({ getOperationStatus });
    const refreshManifest = submitPartnerRating(brokerValue, 60_000);

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText("Изменение отправлено")).toBeInTheDocument();
    expect(getOperationStatus).not.toHaveBeenCalled();

    await act(async () => {
      window.dispatchEvent(new Event("focus"));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(getOperationStatus).toHaveBeenCalledTimes(1);
    expect(refreshManifest).toHaveBeenCalledWith(operationId);
    expect(screen.getByText("Опубликовано")).toBeInTheDocument();
  });

  it("keeps default periodic polling below the broker rate limit", async () => {
    vi.useFakeTimers();
    const getOperationStatus = vi.fn(async () => ({ status: "submitted" as const, pr_number: 42 }));
    submitPartnerRating(broker({ getOperationStatus }));

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4_999);
    });
    expect(getOperationStatus).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(getOperationStatus).toHaveBeenCalledTimes(1);
  });
});
