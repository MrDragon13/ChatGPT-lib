import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

const [distDir = "dist"] = process.argv.slice(2);
const expected = process.env.EXPECTED_BROKER_URL?.trim();

if (!expected) {
  throw new Error("EXPECTED_BROKER_URL is required");
}

const assetsDir = join(distDir, "assets");
const files = (await readdir(assetsDir)).filter((name) => name.endsWith(".js"));
const contents = await Promise.all(files.map((name) => readFile(join(assetsDir, name), "utf8")));

if (!contents.some((content) => content.includes(expected))) {
  throw new Error(`broker URL was not embedded in ${distDir}: ${expected}`);
}

console.log(`Broker build env embedded: ${expected}`);
