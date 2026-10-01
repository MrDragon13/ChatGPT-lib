import { useEffect, useMemo, useState } from "react";

import { BrokerHttpError } from "../../broker/client";
import type { BrokerSessionValue } from "../../broker/BrokerSessionProvider";
import type { FeedbackEditInput, FeedbackReaction, OperationStatusResponse } from "../../broker/types";
import type { TargetId } from "../../data/types";
import type { DetailSignal } from "./selectors";

const REACTIONS: Array<{ value: FeedbackReaction; label: string }> = [
  { value: "liked", label: "Понравилось" },
  { value: "mixed", label: "Смешанное впечатление" },
  { value: "neutral", label: "Нейтрально" },
  { value: "disliked", label: "Не понравилось" },
  { value: "unknown", label: "Без оценки впечатления" },
];

const REACTION_VALUES = new Set<FeedbackReaction>(REACTIONS.map((entry) => entry.value));

type EditableSnapshot = {
  rating: number | null;
  reaction: FeedbackReaction | null;
  feedbackSummary: string | null;
};

type ProposedChange = Pick<FeedbackEditInput, "rating" | "reaction" | "feedback_summary">;

type PendingOperation = {
  operationId: string;
  status: OperationStatusResponse["status"];
  baseline: EditableSnapshot;
  proposed: ProposedChange;
};

export type FeedbackEditorProps = {
  workId: string;
  target: TargetId;
  signal: DetailSignal | null;
  broker: BrokerSessionValue;
  refreshManifest(cacheBust?: string): Promise<void>;
  pollIntervalMs?: number;
};

function reactionValue(value: string | null | undefined): FeedbackReaction | null {
  return value && REACTION_VALUES.has(value as FeedbackReaction) ? value as FeedbackReaction : null;
}

function snapshot(signal: DetailSignal | null): EditableSnapshot {
  return {
    rating: signal?.rating ?? null,
    reaction: reactionValue(signal?.reaction),
    feedbackSummary: signal?.feedbackSummary ?? null,
  };
}

function sameSnapshot(left: EditableSnapshot, right: EditableSnapshot): boolean {
  return left.rating === right.rating &&
    left.reaction === right.reaction &&
    left.feedbackSummary === right.feedbackSummary;
}

function proposalMatches(current: EditableSnapshot, proposed: ProposedChange): boolean {
  if (Object.hasOwn(proposed, "rating") && current.rating !== proposed.rating) return false;
  if (Object.hasOwn(proposed, "reaction") && current.reaction !== proposed.reaction) return false;
  if (Object.hasOwn(proposed, "feedback_summary")) {
    const proposedSummary = proposed.feedback_summary ?? null;
    if (current.feedbackSummary !== proposedSummary) return false;
  }
  return true;
}

function ratingError(value: string): string | null {
  if (!value.trim()) return null;
  const rating = Number(value);
  if (!Number.isFinite(rating) || rating < 1 || rating > 10) return "Оценка должна быть от 1 до 10.";
  if (Math.abs(rating * 2 - Math.round(rating * 2)) > 1e-9) return "Оценка меняется с шагом 0,5.";
  return null;
}

function proposedChange(
  baseline: EditableSnapshot,
  ratingInput: string,
  reaction: FeedbackReaction,
  feedbackSummary: string,
): ProposedChange {
  const change: ProposedChange = {};
  const trimmedRating = ratingInput.trim();
  if (trimmedRating) {
    const rating = Number(trimmedRating);
    if (Number.isFinite(rating) && rating !== baseline.rating) change.rating = rating;
  }

  const baselineReaction = baseline.reaction ?? "unknown";
  if (reaction !== baselineReaction) change.reaction = reaction;

  const baselineSummary = baseline.feedbackSummary ?? "";
  if (feedbackSummary !== baselineSummary) {
    change.feedback_summary = feedbackSummary.trim() ? feedbackSummary : null;
  }
  return change;
}

export function operationStatusLabel(status: OperationStatusResponse["status"]): string {
  switch (status) {
    case "submitted": return "Изменение отправлено";
    case "applying": return "Применяется";
    case "checking": return "Проверяется";
    case "merged": return "Смержено, публикуется";
    case "published": return "Опубликовано";
    case "failed": return "Не удалось применить";
  }
}

function publishedBaselineLabel(value: EditableSnapshot): string {
  const parts: string[] = [];
  if (value.rating !== null) parts.push(`${value.rating}/10`);
  if (value.reaction) {
    const label = REACTIONS.find((entry) => entry.value === value.reaction)?.label;
    if (label) parts.push(label.toLocaleLowerCase("ru-RU"));
  }
  if (value.feedbackSummary) parts.push("отзыв сохранён");
  return parts.length ? parts.join(" · ") : "пока без оценки и отзыва";
}

export function FeedbackEditor({
  workId,
  target,
  signal,
  broker,
  refreshManifest,
  pollIntervalMs = 2_500,
}: FeedbackEditorProps) {
  const current = useMemo(
    () => snapshot(signal),
    [signal?.rating, signal?.reaction, signal?.feedbackSummary],
  );
  const [open, setOpen] = useState(false);
  const [openAfterLogin, setOpenAfterLogin] = useState(false);
  const [ratingInput, setRatingInput] = useState(() => current.rating?.toString() ?? "");
  const [reaction, setReaction] = useState<FeedbackReaction>(() => current.reaction ?? "unknown");
  const [feedbackSummary, setFeedbackSummary] = useState(() => current.feedbackSummary ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [pending, setPending] = useState<PendingOperation | null>(null);
  const [refreshCompleted, setRefreshCompleted] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (openAfterLogin && broker.authenticated) {
      setOpenAfterLogin(false);
      setOpen(true);
    }
  }, [broker.authenticated, openAfterLogin]);

  useEffect(() => {
    if (pending || submitting) return;
    setRatingInput(current.rating?.toString() ?? "");
    setReaction(current.reaction ?? "unknown");
    setFeedbackSummary(current.feedbackSummary ?? "");
  }, [current.rating, current.reaction, current.feedbackSummary, pending, submitting]);

  useEffect(() => {
    if (!pending || pending.status === "failed" || pending.status === "published") return;
    let cancelled = false;
    let timer: number | undefined;

    const poll = async () => {
      try {
        const status = await broker.getOperationStatus(pending.operationId);
        if (cancelled) return;
        setPending((value) => value?.operationId === pending.operationId
          ? { ...value, status: status.status }
          : value);
        if (status.status === "published") {
          try {
            await refreshManifest(pending.operationId);
            if (!cancelled) setRefreshCompleted(true);
          } catch {
            if (!cancelled) setMessage("Опубликовано, но свежие данные пока не загрузились.");
          }
          return;
        }
        if (status.status === "failed") return;
        timer = window.setTimeout(poll, pollIntervalMs);
      } catch (error) {
        if (cancelled) return;
        if (error instanceof BrokerHttpError && error.status === 401) {
          setMessage("Сессия истекла. Войдите через GitHub снова.");
          return;
        }
        setMessage("Не удалось проверить статус. Повторяем…");
        timer = window.setTimeout(poll, Math.min(pollIntervalMs * 2, 10_000));
      }
    };

    timer = window.setTimeout(poll, pollIntervalMs);
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [pending?.operationId, broker.getOperationStatus, refreshManifest, pollIntervalMs]);

  useEffect(() => {
    if (!pending || pending.status !== "published" || !refreshCompleted) return;
    if (proposalMatches(current, pending.proposed) || !sameSnapshot(current, pending.baseline)) {
      setPending(null);
      setRefreshCompleted(false);
      setMessage(null);
      setOpen(false);
    }
  }, [current, pending, refreshCompleted]);

  const validationError = ratingError(ratingInput);
  const change = useMemo(
    () => proposedChange(current, ratingInput, reaction, feedbackSummary),
    [current, ratingInput, reaction, feedbackSummary],
  );
  const dirty = Object.keys(change).length > 0;

  const beginEdit = () => {
    setMessage(null);
    if (!broker.authenticated) {
      setOpenAfterLogin(true);
      broker.login();
      return;
    }
    setOpen((value) => !value);
  };

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting || validationError || !dirty) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const result = await broker.submitFeedback({ work_id: workId, target, ...change });
      setRefreshCompleted(false);
      setPending({ operationId: result.operation_id, status: result.status, baseline: current, proposed: change });
    } catch (error) {
      if (error instanceof BrokerHttpError && error.status === 409) {
        setMessage("Изменение уже проверяется");
      } else if (error instanceof BrokerHttpError && error.status === 401) {
        setMessage("Сессия истекла. Войдите через GitHub снова.");
      } else {
        setMessage("Не удалось отправить изменение. Попробуйте ещё раз.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (!broker.configured) {
    return (
      <div className="future-edit-boundary" data-testid="future-edit-boundary">
        <span>Режим только для чтения</span>
      </div>
    );
  }

  return (
    <div className="feedback-editor">
      <div className="feedback-editor__bar">
        <button className="feedback-editor__trigger" type="button" onClick={beginEdit}>
          Изменить впечатление
        </button>
        {pending ? (
          <div className={`feedback-operation feedback-operation--${pending.status}`} role="status" aria-live="polite">
            <strong>{operationStatusLabel(pending.status)}</strong>
            <span>Опубликовано сейчас: {publishedBaselineLabel(pending.baseline)}</span>
          </div>
        ) : null}
      </div>

      {message ? <p className="feedback-editor__message" role="status">{message}</p> : null}

      {open ? (
        <form className="feedback-form" aria-label="Редактирование впечатления" onSubmit={submit}>
          <div className="feedback-form__row">
            <label>
              <span>Оценка</span>
              <input
                type="number"
                min="1"
                max="10"
                step="0.5"
                inputMode="decimal"
                value={ratingInput}
                onChange={(event) => setRatingInput(event.currentTarget.value)}
                aria-describedby={validationError ? "feedback-rating-error" : undefined}
              />
            </label>
            <label>
              <span>Впечатление</span>
              <select value={reaction} onChange={(event) => setReaction(event.currentTarget.value as FeedbackReaction)}>
                {REACTIONS.map((entry) => <option key={entry.value} value={entry.value}>{entry.label}</option>)}
              </select>
            </label>
          </div>
          {validationError ? <p id="feedback-rating-error" className="feedback-form__error">{validationError}</p> : null}

          <label className="feedback-form__summary">
            <span>Отзыв</span>
            <textarea
              rows={5}
              value={feedbackSummary}
              onChange={(event) => setFeedbackSummary(event.currentTarget.value)}
            />
          </label>

          <div className="feedback-form__actions">
            <button type="button" className="feedback-form__secondary" onClick={() => setFeedbackSummary("")}>
              Очистить отзыв
            </button>
            <div>
              <button type="button" className="feedback-form__secondary" onClick={() => setOpen(false)}>
                Закрыть
              </button>
              <button type="submit" disabled={!dirty || Boolean(validationError) || submitting}>
                {submitting ? "Отправляем…" : "Сохранить"}
              </button>
            </div>
          </div>
        </form>
      ) : null}
    </div>
  );
}
