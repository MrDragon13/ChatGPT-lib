const reactionValues = ["liked", "disliked", "neutral", "mixed", "unknown"] as const;

export type ReactionValue = (typeof reactionValues)[number];

export type FeedbackInput = {
  work_id: string;
  target: string;
  rating?: number;
  reaction?: ReactionValue;
  feedback_summary?: string | null;
};

export class FeedbackValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FeedbackValidationError";
  }
}

const allowedKeys = new Set(["work_id", "target", "rating", "reaction", "feedback_summary"]);
const encoder = new TextEncoder();

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requiredString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new FeedbackValidationError(`${field} must be a non-empty string`);
  }
  return value;
}

export function parseFeedbackInput(value: unknown): FeedbackInput {
  if (!isRecord(value)) {
    throw new FeedbackValidationError("request body must be an object");
  }

  for (const key of Object.keys(value)) {
    if (!allowedKeys.has(key)) {
      throw new FeedbackValidationError(`unsupported field: ${key}`);
    }
  }

  const work_id = requiredString(value.work_id, "work_id");
  const target = requiredString(value.target, "target");
  const hasRating = Object.hasOwn(value, "rating");
  const hasReaction = Object.hasOwn(value, "reaction");
  const hasSummary = Object.hasOwn(value, "feedback_summary");

  if (!hasRating && !hasReaction && !hasSummary) {
    throw new FeedbackValidationError("at least one editable field is required");
  }

  const result: FeedbackInput = { work_id, target };

  if (hasRating) {
    const rating = value.rating;
    if (
      typeof rating !== "number" ||
      !Number.isFinite(rating) ||
      rating < 1 ||
      rating > 10 ||
      !Number.isInteger(rating * 2)
    ) {
      throw new FeedbackValidationError("rating must be 1..10 in 0.5 increments");
    }
    result.rating = rating;
  }

  if (hasReaction) {
    if (typeof value.reaction !== "string" || !reactionValues.includes(value.reaction as ReactionValue)) {
      throw new FeedbackValidationError("unsupported reaction");
    }
    result.reaction = value.reaction as ReactionValue;
  }

  if (hasSummary) {
    const summary = value.feedback_summary;
    if (summary !== null && typeof summary !== "string") {
      throw new FeedbackValidationError("feedback_summary must be a string or null");
    }
    if (typeof summary === "string" && encoder.encode(summary).byteLength > 8192) {
      throw new FeedbackValidationError("feedback_summary exceeds 8 KiB");
    }
    result.feedback_summary = summary as string | null;
  }

  return result;
}
