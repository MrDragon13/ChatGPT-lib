import { readFileSync } from "node:fs";

const requiredSecrets = [
  "GITHUB_APP_ID",
  "GITHUB_APP_CLIENT_ID",
  "GITHUB_APP_INSTALLATION_ID",
  "OWNER_GITHUB_USER_ID",
  "GITHUB_APP_PRIVATE_KEY",
  "GITHUB_APP_CLIENT_SECRET",
  "BROKER_SESSION_SECRET",
].sort();

const config = JSON.parse(readFileSync(new URL("../wrangler.jsonc", import.meta.url), "utf8"));
const actual = [...(config.secrets?.required ?? [])].sort();

if (JSON.stringify(actual) !== JSON.stringify(requiredSecrets)) {
  console.error("wrangler.jsonc must declare every broker runtime secret in secrets.required");
  console.error("expected:", requiredSecrets.join(", "));
  console.error("actual:", actual.join(", "));
  process.exit(1);
}

console.log("broker required-secret config: ok");
