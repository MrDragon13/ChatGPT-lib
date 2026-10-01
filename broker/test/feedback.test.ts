import { describe, expect, it } from "vitest";

import { parseFeedbackInput } from "../src/feedback";

describe("parseFeedbackInput", () => {
  it("accepts an explicit rating, reaction, and summary", () => {
    expect(parseFeedbackInput({
      work_id: "game-night-2018",
      target: "primary",
      rating: 8.5,
      reaction: "liked",
      feedback_summary: "Очень удачная комедия.",
    })).toEqual({
      work_id: "game-night-2018",
      target: "primary",
      rating: 8.5,
      reaction: "liked",
      feedback_summary: "Очень удачная комедия.",
    });
  });

  it.each([8.3, 0, 11])("rejects invalid rating %s", (rating) => {
    expect(() => parseFeedbackInput({ work_id: "x", target: "primary", rating })).toThrow();
  });

  it("rejects unsupported reactions", () => {
    expect(() => parseFeedbackInput({ work_id: "x", target: "primary", reaction: "love" })).toThrow();
  });

  it("rejects requests with no editable fields", () => {
    expect(() => parseFeedbackInput({ work_id: "x", target: "primary" })).toThrow();
  });

  it("rejects server-owned fields", () => {
    expect(() => parseFeedbackInput({ work_id: "x", target: "primary", rating: 8, branch: "main" })).toThrow();
    expect(() => parseFeedbackInput({ work_id: "x", target: "primary", rating: 8, operation_id: "123" })).toThrow();
  });

  it("preserves explicit null summary as a clear operation", () => {
    expect(parseFeedbackInput({ work_id: "x", target: "primary", feedback_summary: null })).toEqual({
      work_id: "x",
      target: "primary",
      feedback_summary: null,
    });
  });

  it("rejects feedback summaries larger than 8 KiB", () => {
    expect(() => parseFeedbackInput({ work_id: "x", target: "primary", feedback_summary: "a".repeat(8193) })).toThrow();
  });
});
