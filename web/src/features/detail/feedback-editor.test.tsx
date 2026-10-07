import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BrokerHttpError } from "../../broker/client";
import type { BrokerSessionValue } from "../../broker/BrokerSessionProvider";
import type { DetailSignal } from "./selectors";
import { FeedbackEditor, type FeedbackEditorProps, operationStatusLabel } from "./FeedbackEditor";

const baseSignal: DetailSignal = {
  target: "primary",
  rating: 8.5,
  reaction: "liked",
  viewingStatus: "watched",
  feedbackSummary: "Умная фантастика без суеты.",
};

function broker(overrides: Partial<BrokerSessionValue> = {}): BrokerSessionValue {
  return {
    configured: true,
    authenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    submitFeedback: vi.fn(async () => ({
      operation_id: "11111111-2222-4333-8444-555555555555",
      pr_number: 42,
      status: "submitted" as const,
    })),
    getOperationStatus: vi.fn(async () => ({ status: "submitted" as const, pr_number: 42 })),
    ...overrides,
  };
}

function renderEditor(options: {
  signal?: DetailSignal | null;
  broker?: BrokerSessionValue;
  refreshManifest?: (cacheBust?: string) => Promise<void>;
  pollIntervalMs?: number;
} = {}) {
  const brokerValue = options.broker ?? broker();
  const refreshManifest = options.refreshManifest ?? vi.fn(async () => undefined);
  const props: FeedbackEditorProps = {
    workId: "arrival-2016",
    target: "primary",
    signal: options.signal === undefined ? baseSignal : options.signal,
    broker: brokerValue,
    refreshManifest,
    ...(options.pollIntervalMs === undefined ? {} : { pollIntervalMs: options.pollIntervalMs }),
  };
  return { ...render(<FeedbackEditor {...props} />), broker: brokerValue, refreshManifest, props };
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("FeedbackEditor", () => {
  it("keeps an unconfigured site read-only", () => {
    const brokerValue = broker({ configured: false, authenticated: false });
    renderEditor({ broker: brokerValue });
    expect(screen.getByText("Режим только для чтения")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Изменить впечатление" })).not.toBeInTheDocument();
  });

  it("starts GitHub login when editing is configured but unauthenticated", () => {
    const login = vi.fn();
    renderEditor({ broker: broker({ authenticated: false, login }) });
    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
    expect(login).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("form", { name: "Редактирование впечатления — Я" })).not.toBeInTheDocument();
  });

  it("prefills current values and submits only the changed field", async () => {
    const brokerValue = broker();
    renderEditor({ broker: brokerValue });
    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));

    expect(screen.getByLabelText("Оценка")).toHaveValue(8.5);
    expect(screen.getByLabelText("Реакция")).toHaveValue("liked");
    expect(screen.getByLabelText("Отзыв")).toHaveValue("Умная фантастика без суеты.");
    expect(screen.queryByLabelText(/статус просмотра/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Сохранить" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Оценка"), { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(brokerValue.submitFeedback).toHaveBeenCalledWith({
      work_id: "arrival-2016",
      target: "primary",
      rating: 9,
    }));
    expect(await screen.findByText("Изменение отправлено")).toBeInTheDocument();
  });

  it("rejects a rating that is not a half-point step", () => {
    renderEditor();
    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
    fireEvent.change(screen.getByLabelText("Оценка"), { target: { value: "8.3" } });
    expect(screen.getByText("Оценка меняется с шагом 0,5.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Сохранить" })).toBeDisabled();
  });

  it("clears feedback with an explicit null mutation", async () => {
    const brokerValue = broker();
    renderEditor({ broker: brokerValue });
    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
    fireEvent.click(screen.getByRole("button", { name: "Очистить отзыв" }));
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    await waitFor(() => expect(brokerValue.submitFeedback).toHaveBeenCalledWith({
      work_id: "arrival-2016",
      target: "primary",
      feedback_summary: null,
    }));
  });

  it("locks submission against a double click", async () => {
    let resolveSubmission: ((value: { operation_id: string; pr_number: number; status: "submitted" }) => void) | null = null;
    const submitFeedback = vi.fn(() => new Promise<{ operation_id: string; pr_number: number; status: "submitted" }>((resolve) => {
      resolveSubmission = resolve;
    }));
    const brokerValue = broker({ submitFeedback });
    renderEditor({ broker: brokerValue });
    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
    fireEvent.change(screen.getByLabelText("Оценка"), { target: { value: "9" } });
    const save = screen.getByRole("button", { name: "Сохранить" });
    fireEvent.click(save);
    await waitFor(() => expect(save).toBeDisabled());
    fireEvent.click(save);
    expect(submitFeedback).toHaveBeenCalledTimes(1);
    await act(async () => {
      resolveSubmission?.({ operation_id: "11111111-2222-4333-8444-555555555555", pr_number: 42, status: "submitted" });
      await Promise.resolve();
    });
    expect(await screen.findByText("Изменение отправлено")).toBeInTheDocument();
  });

  it("keeps default status polling within the broker read-rate budget", async () => {
    vi.useFakeTimers();
    const getOperationStatus = vi.fn(async () => ({ status: "submitted" as const, pr_number: 42 }));
    renderEditor({ broker: broker({ getOperationStatus }) });
    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
    fireEvent.change(screen.getByLabelText("Оценка"), { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText("Изменение отправлено")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4_999);
    });
    expect(getOperationStatus).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(getOperationStatus).toHaveBeenCalledTimes(1);
  });

  it("renders an active-operation conflict without overwriting canonical state", async () => {
    const brokerValue = broker({
      submitFeedback: vi.fn(async () => { throw new BrokerHttpError(409, "active_operation"); }),
    });
    renderEditor({ broker: brokerValue });
    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
    fireEvent.change(screen.getByLabelText("Оценка"), { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    expect(await screen.findByText("Изменение уже проверяется")).toBeInTheDocument();
    expect(screen.getByLabelText("Оценка")).toHaveValue(9);
  });

  it("maps every operation state to the agreed Russian label", () => {
    expect(operationStatusLabel("submitted")).toBe("Изменение отправлено");
    expect(operationStatusLabel("applying")).toBe("Применяется");
    expect(operationStatusLabel("checking")).toBe("Проверяется");
    expect(operationStatusLabel("merged")).toBe("Смержено, публикуется");
    expect(operationStatusLabel("published")).toBe("Опубликовано");
    expect(operationStatusLabel("failed")).toBe("Не удалось применить");
  });

  it("refreshes canonical data after publication and keeps pending state until the signal changes", async () => {
    const operationId = "11111111-2222-4333-8444-555555555555";
    const brokerValue = broker({
      getOperationStatus: vi.fn(async () => ({ status: "published" as const, pr_number: 42, merge_sha: "merge-sha" })),
    });
    const refreshManifest = vi.fn(async () => undefined);
    const rendered = renderEditor({ broker: brokerValue, refreshManifest, pollIntervalMs: 1 });
    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
    fireEvent.change(screen.getByLabelText("Оценка"), { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(refreshManifest).toHaveBeenCalledWith(operationId));
    expect(screen.getByText("Опубликовано")).toBeInTheDocument();

    rendered.rerender(<FeedbackEditor
      {...rendered.props}
      signal={{ ...baseSignal, rating: 9 }}
    />);
    await waitFor(() => expect(screen.queryByText("Опубликовано")).not.toBeInTheDocument());
  });

  it("shows a terminal failure while keeping the published signal as the edit baseline", async () => {
    const brokerValue = broker({
      getOperationStatus: vi.fn(async () => ({ status: "failed" as const, reason: "check_failed" as const, pr_number: 42 })),
    });
    renderEditor({ broker: brokerValue, pollIntervalMs: 1 });
    fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
    fireEvent.change(screen.getByLabelText("Оценка"), { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    expect(await screen.findByText("Не удалось применить")).toBeInTheDocument();
    expect(screen.getByText(/Опубликовано сейчас: 8.5\/10/)).toBeInTheDocument();
  });
});

it("keeps a second local draft while the first operation is pending and does not submit twice", async () => {
  const operationId = "cccccccc-dddd-4eee-8fff-111111111111";
  const submitFeedback = vi.fn(async () => ({
    operation_id: operationId,
    pr_number: 42,
    status: "submitted" as const,
  }));
  const getOperationStatus = vi.fn(async () => ({
    status: "published" as const,
    pr_number: 42,
    merge_sha: "merge-sha",
  }));
  const brokerValue = broker({ submitFeedback, getOperationStatus });
  const refreshManifest = vi.fn(async () => undefined);
  const rendered = renderEditor({
    broker: brokerValue,
    refreshManifest,
    pollIntervalMs: 60_000,
  });

  fireEvent.click(screen.getByRole("button", { name: "Изменить впечатление" }));
  fireEvent.change(screen.getByLabelText("Оценка"), { target: { value: "9" } });
  fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));
  await waitFor(() => expect(screen.getByText("Изменение отправлено")).toBeInTheDocument());

  const rating = screen.getByLabelText("Оценка");
  expect(rating).toBeEnabled();
  fireEvent.change(rating, { target: { value: "9.5" } });
  expect(screen.getByRole("button", { name: "Сохранить" })).toBeDisabled();
  expect(submitFeedback).toHaveBeenCalledTimes(1);

  fireEvent.focus(window);
  await waitFor(() => expect(refreshManifest).toHaveBeenCalledWith(operationId));

  rendered.rerender(<FeedbackEditor
    {...rendered.props}
    signal={{ ...baseSignal, rating: 9 }}
  />);

  await waitFor(() => expect(screen.queryByText("Опубликовано")).not.toBeInTheDocument());
  expect(screen.getByLabelText("Оценка")).toHaveValue(9.5);
  expect(screen.getByRole("button", { name: "Сохранить" })).toBeEnabled();
  expect(submitFeedback).toHaveBeenCalledTimes(1);
});
