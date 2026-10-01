import { readFile, readdir, stat } from "node:fs/promises";
import { extname, join, resolve } from "node:path";

const root = resolve(process.argv[2] ?? "dist");
const textExtensions = new Set([".css", ".html", ".js", ".json", ".map", ".svg", ".txt"]);
const forbidden = [
  ["tmdb", "read", "token"].join("_"),
  ["github", "pat"].join("_"),
  ["client", "secret"].join("_"),
  ["private", "key"].join("_"),
  "ghp_",
  "sk-",
  "authorization: bearer",
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

const matches = [];
for (const file of await files(root)) {
  const content = (await readFile(file, "utf8")).toLowerCase();
  for (const marker of forbidden) {
    if (content.includes(marker)) matches.push(`${file}: ${marker}`);
  }
}

if (matches.length) {
  console.error("Static artifact contains forbidden credential markers:\n" + matches.join("\n"));
  process.exit(1);
}

console.log(`Static artifact credential scan passed (${(await files(root)).length} text files).`);
