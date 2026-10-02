import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const operationsSource = readFileSync(new URL("../src/operations.ts", import.meta.url), "utf8");

describe("authoritative operation status contract", () => {
  it("queries only workflow_dispatch Media Check runs", () => {
    expect(operationsSource).toContain('event: "workflow_dispatch"');
  });

  it("matches the authoritative check to the current PR head sha", () => {
    expect(operationsSource).toMatch(/checkRuns\.find\([^\n]*head_sha[^\n]*pull\.head\.sha/);
  });

  it("maps privileged auto-merge runs back to the operation branch by run title", () => {
    expect(operationsSource).toContain("display_title?: string");
    expect(operationsSource).toContain("Media Auto Merge · ${branch}");
  });
});
