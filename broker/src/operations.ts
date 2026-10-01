import type { BrokerEnv } from "./env";
import type { FeedbackInput } from "./feedback";
import {
  GitHubApiError,
  createBranch,
  createOperationPullRequest,
  deleteBranch,
  getMainSha,
  mintInstallationToken,
  putRequestFile,
} from "./github";

const encoder = new TextEncoder();

export type FeedbackCommand = {
  schema_version: 1;
  operation_id: string;
  operation: "record_viewing_feedback";
  work_ref: { id: string };
  create_if_missing: false;
  target_updates: Array<Record<string, unknown>>;
};

export type SubmittedOperation = {
  operation_id: string;
  pr_number: number;
  status: "submitted";
};

export class OperationSubmissionError extends Error {
  constructor(
    message: string,
    public readonly operationId: string,
    public readonly upstreamStatus: number | null = null,
    public readonly requestId: string | null = null,
  ) {
    super(message);
    this.name = "OperationSubmissionError";
  }
}

function utf8Base64(value: string): string {
  const bytes = encoder.encode(value);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

export function buildFeedbackCommand(input: FeedbackInput, operationId: string): FeedbackCommand {
  const update: Record<string, unknown> = { target: input.target };
  if (Object.hasOwn(input, "rating")) {
    update.rating = { score: input.rating, source: "explicit", confidence: "exact" };
  }
  if (Object.hasOwn(input, "reaction")) {
    update.reaction = { value: input.reaction, source: "explicit", confidence: "exact" };
  }
  if (Object.hasOwn(input, "feedback_summary")) {
    update.feedback = { summary: input.feedback_summary };
  }
  return {
    schema_version: 1,
    operation_id: operationId,
    operation: "record_viewing_feedback",
    work_ref: { id: input.work_id },
    create_if_missing: false,
    target_updates: [update],
  };
}

function submissionError(error: unknown, operationId: string): OperationSubmissionError {
  if (error instanceof GitHubApiError) {
    return new OperationSubmissionError(error.message, operationId, error.status, error.requestId);
  }
  return new OperationSubmissionError(
    error instanceof Error ? error.message : "feedback operation submission failed",
    operationId,
  );
}

export async function submitFeedback(input: FeedbackInput, env: BrokerEnv): Promise<SubmittedOperation> {
  const operationId = crypto.randomUUID();
  const branch = `media/op-${operationId}`;
  let token: string;
  let branchCreated = false;

  try {
    token = await mintInstallationToken(env);
    const mainSha = await getMainSha(env, token);
    await createBranch(env, token, branch, mainSha);
    branchCreated = true;

    const command = buildFeedbackCommand(input, operationId);
    const requestPath = `.media/requests/${operationId}.json`;
    const content = utf8Base64(`${JSON.stringify(command)}\n`);
    await putRequestFile(env, token, branch, requestPath, content, operationId);
    const prNumber = await createOperationPullRequest(env, token, branch, operationId, input.work_id);
    return { operation_id: operationId, pr_number: prNumber, status: "submitted" };
  } catch (error) {
    if (branchCreated && token!) {
      try {
        await deleteBranch(env, token, branch);
      } catch {
        // The original failure is authoritative; cleanup is best-effort.
      }
    }
    throw submissionError(error, operationId);
  }
}
