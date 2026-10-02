export type FeedbackReaction = "liked" | "disliked" | "neutral" | "mixed" | "unknown";

export type FeedbackEditInput = {
  work_id: string;
  target: string;
  rating?: number;
  reaction?: FeedbackReaction;
  feedback_summary?: string | null;
};

export type SubmittedOperation = {
  operation_id: string;
  pr_number: number;
  status: "submitted";
};

export type OperationFailureReason = "command_failed" | "check_failed" | "merge_failed" | "deploy_failed";

export type OperationStatusResponse = {
  status: "submitted" | "applying" | "checking" | "merged" | "published" | "failed";
  reason?: OperationFailureReason;
  pr_number?: number;
  pr_url?: string;
  merge_sha?: string;
  actions_url?: string;
};
