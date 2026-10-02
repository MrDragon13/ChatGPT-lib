import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const requiredSecrets = [
  "GITHUB_APP_ID",
  "GITHUB_APP_CLIENT_ID",
  "GITHUB_APP_INSTALLATION_ID",
  "OWNER_GITHUB_USER_ID",
  "GITHUB_APP_PRIVATE_KEY",
  "GITHUB_APP_CLIENT_SECRET",
  "BROKER_SESSION_SECRET",
].sort();

describe("wrangler broker config", () => {
  it("declares every runtime secret as required for deploy", () => {
    const config = JSON.parse(readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8")) as {
      secrets?: { required?: string[] };
    };
    expect([...(config.secrets?.required ?? [])].sort()).toEqual(requiredSecrets);
  });
});
