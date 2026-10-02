import type { BrokerEnv } from "./env";
import type { FeedbackInput } from "./feedback";
import {
  GitHubApiError,
  createBranch,
  createOperationPullRequest,
  deleteBranch,
  getMainSha,
  getRepoJson,
  mintInstallationToken,
  putRequestFile,
} from "./github";

const encoder = new TextEncoder();
const decoder = new TextDecoder();

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

export type ActiveOperation = {
  operation_id: string;
  pr_number: number;
};

export type OperationPull = {
  number: number;
  state: string;
  merged_at: string | null;
  merge_commit_sha: string | null;
  html_url?: string;
  head: {
    ref: string;
    sha: string;
    repo?: { full_name?: string };
  };
  base?: { ref?: string };
};

export type WorkflowRun = {
  name?: string;
  status: string;
  conclusion: string | null;
  head_sha?: string;
  head_branch?: string;
  html_url?: string;
};

export type OperationFailureReason = "command_failed" | "check_failed" | "merge_failed" | "deploy_failed";
export type OperationStatus = "submitted" | "applying" | "checking" | "merged" | "published" | "failed";

export type OperationStatusResponse = {
  status: OperationStatus;
  reason?: OperationFailureReason;
  pr_number?: number;
  pr_url?: string;
  merge_sha?: string;
  actions_url?: string;
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

function decodeBase64Utf8(value: string): string {
  const binary = atob(value.replace(/\s+/g, ""));
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return decoder.decode(bytes);
}

function query(params: Record<string, string>): string {
  return new URLSearchParams(params).toString();
}

function failedConclusion(run: WorkflowRun | undefined): boolean {
  return Boolean(run && run.status === "completed" && run.conclusion !== "success");
}

function activeRun(run: WorkflowRun | undefined): boolean {
  return Boolean(run && run.status !== "completed");
}

async function listWorkflowRuns(
  env: BrokerEnv,
  token: string,
  workflow: string,
  params: Record<string, string>,
): Promise<WorkflowRun[]> {
  const data = await getRepoJson<{ workflow_runs?: WorkflowRun[] }>(
    env,
    token,
    `/actions/workflows/${workflow}/runs?${query({ ...params, per_page: "20" })}`,
    `failed to read ${workflow} runs`,
  );
  return Array.isArray(data.workflow_runs) ? data.workflow_runs : [];
}

async function findOperationPull(
  operationId: string,
  env: BrokerEnv,
  token: string,
): Promise<OperationPull | null> {
  const branch = `media/op-${operationId}`;
  const pulls = await getRepoJson<OperationPull[]>(
    env,
    token,
    `/pulls?${query({
      state: "all",
      base: "main",
      head: `${env.REPO_OWNER}:${branch}`,
      per_page: "100",
    })}`,
    "failed to read operation pull request",
  );
  return pulls.find((pull) => pull.head?.ref === branch) ?? null;
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

export async function findActiveOperation(
  workId: string,
  target: string,
  env: BrokerEnv,
): Promise<ActiveOperation | null> {
  const token = await mintInstallationToken(env);
  const pulls = await getRepoJson<OperationPull[]>(
    env,
    token,
    `/pulls?${query({ state: "open", base: "main", per_page: "100" })}`,
    "failed to list active operation pull requests",
  );

  for (const pull of pulls) {
    const branch = pull.head?.ref ?? "";
    if (!branch.startsWith("media/op-")) continue;
    if (pull.base?.ref && pull.base.ref !== "main") continue;
    if (pull.head.repo?.full_name && pull.head.repo.full_name !== `${env.REPO_OWNER}/${env.REPO_NAME}`) continue;
    const operationId = branch.slice("media/op-".length);
    if (!operationId) continue;

    const commits = await getRepoJson<Array<{ sha?: unknown }>>(
      env,
      token,
      `/pulls/${pull.number}/commits?per_page=100`,
      "failed to read operation commits",
    );
    const initialSha = commits.at(0)?.sha;
    if (typeof initialSha !== "string" || !initialSha) continue;

    try {
      const request = await getRepoJson<{ content?: unknown; encoding?: unknown }>(
        env,
        token,
        `/contents/.media/requests/${operationId}.json?${query({ ref: initialSha })}`,
        "failed to read original operation request",
      );
      if (request.encoding !== "base64" || typeof request.content !== "string") continue;
      const command = JSON.parse(decodeBase64Utf8(request.content)) as {
        work_ref?: { id?: unknown };
        target_updates?: Array<{ target?: unknown }>;
      };
      if (
        command.work_ref?.id === workId &&
        Array.isArray(command.target_updates) &&
        command.target_updates.some((update) => update.target === target)
      ) {
        return { operation_id: operationId, pr_number: pull.number };
      }
    } catch (error) {
      if (error instanceof GitHubApiError && error.status === 404) continue;
      throw error;
    }
  }
  return null;
}

export async function getOperationStatus(
  operationId: string,
  env: BrokerEnv,
): Promise<OperationStatusResponse> {
  const token = await mintInstallationToken(env);
  const pull = await findOperationPull(operationId, env, token);
  if (!pull) return { status: "failed", reason: "merge_failed" };

  const base = { pr_number: pull.number, pr_url: pull.html_url };
  if (pull.state === "closed" && !pull.merged_at) {
    return { ...base, status: "failed", reason: "merge_failed" };
  }

  if (pull.merged_at && pull.merge_commit_sha) {
    const pagesRuns = await listWorkflowRuns(env, token, "media-pages.yml", { head_sha: pull.merge_commit_sha });
    const exact = pagesRuns.find((run) => run.head_sha === pull.merge_commit_sha);
    const mergedBase = { ...base, merge_sha: pull.merge_commit_sha, actions_url: exact?.html_url };
    if (!exact || activeRun(exact)) return { ...mergedBase, status: "merged" };
    if (exact.conclusion === "success") return { ...mergedBase, status: "published" };
    return { ...mergedBase, status: "failed", reason: "deploy_failed" };
  }

  const branch = pull.head.ref;
  const commandRuns = await listWorkflowRuns(env, token, "media-command.yml", { branch });
  const commandRun = commandRuns.at(0);
  if (!commandRun) return { ...base, status: "submitted" };
  if (activeRun(commandRun)) return { ...base, status: "applying", actions_url: commandRun.html_url };
  if (failedConclusion(commandRun)) return { ...base, status: "failed", reason: "command_failed", actions_url: commandRun.html_url };

  const checkRuns = await listWorkflowRuns(env, token, "media-check.yml", { branch });
  const checkRun = checkRuns.at(0);
  if (!checkRun || activeRun(checkRun)) return { ...base, status: "checking", actions_url: checkRun?.html_url ?? commandRun.html_url };
  if (failedConclusion(checkRun)) return { ...base, status: "failed", reason: "check_failed", actions_url: checkRun.html_url };

  const mergeRuns = await listWorkflowRuns(env, token, "media-auto-merge.yml", { branch });
  const mergeRun = mergeRuns.at(0);
  if (failedConclusion(mergeRun)) return { ...base, status: "failed", reason: "merge_failed", actions_url: mergeRun?.html_url };
  return { ...base, status: "checking", actions_url: mergeRun?.html_url ?? checkRun.html_url };
}
