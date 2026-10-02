import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const operationsSource = readFileSync(new URL("../src/operations.ts", import.meta.url), "utf8");

describe("authoritative media check status contract", () => {
  it("queries only workflow_dispatch Media Check runs", () => {
    expect(operationsSource).toContain('event: "workflow_dispatch"');
  });

  it("matches the authoritative check to the current PR head sha", () => {
    expect(operationsSource).toMatch(/checkRuns\.find\([^\n]*head_sha[^\n]*pull\.head\.sha/);
  });
});
