import { readFile, readdir, stat } from "node:fs/promises";
import { extname, join, resolve } from "node:path";

const root = resolve(process.argv[2] ?? "dist");
const textExtensions = new Set([".css", ".html", ".js", ".json", ".map", ".svg", ".txt"]);
const exactMarkers = [
  ["tmdb", "read", "token"].join("_"),
  ["media", "write", "token"].join("_"),
  ["client", "secret"].join("_"),
];
const credentialPatterns = [
  /\bsk-[a-z0-9_-]{20,}\b/i,
  /\bghp_[a-z0-9]{20,}\b/i,
  /\bgithub_pat_[a-z0-9_]{20,}\b/i,
  /authorization:\s*bearer\s+[a-z0-9._-]{20,}/i,
  /-----begin (?:rsa |ec |openssh )?private key-----/i,
];

async function files(path) {
  const entries = await readdir(path);
  const result = [];
  for (const entry of entries) {
    const candidate = join(path, entry);
    const info = await stat(candidate);
    if (info.isDirectory()) result.push(...await files(candidate));
    else if (textExtensions.has(extname(entry).toLowerCase())) result.push(candidate);
  }
  return result;
}

const scannedFiles = await files(root);
const matches = [];
for (const file of scannedFiles) {
  const content = (await readFile(file, "utf8")).toLowerCase();
  for (const marker of exactMarkers) {
    if (content.includes(marker)) matches.push(`${file}: forbidden variable ${marker}`);
  }
  for (const pattern of credentialPatterns) {
    if (pattern.test(content)) matches.push(`${file}: credential-shaped value ${pattern.source}`);
  }
}

if (matches.length) {
  console.error("Static artifact contains forbidden credential material:\n" + matches.join("\n"));
  process.exit(1);
}

console.log(`Static artifact credential scan passed (${scannedFiles.length} text files).`);
