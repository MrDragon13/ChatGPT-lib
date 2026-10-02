const allowedFields = new Set([
  "route",
  "method",
  "status",
  "operation_id",
  "pr_number",
  "github_request_id",
  "failure",
]);

export type SafeLogFields = Record<string, string | number | boolean | null>;

export function sanitizeLogFields(input: Record<string, unknown>): SafeLogFields {
  const output: SafeLogFields = {};
  for (const [key, value] of Object.entries(input)) {
    if (!allowedFields.has(key)) continue;
    if (value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      output[key] = value;
    }
  }
  return output;
}

export function logBrokerEvent(input: Record<string, unknown>): void {
  console.info(JSON.stringify(sanitizeLogFields(input)));
}
