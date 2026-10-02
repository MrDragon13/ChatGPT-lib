import type { WebManifest } from "./types";

const MANIFEST_SCHEMA_VERSION = 1;

export class ManifestLoadError extends Error {
  constructor(
    message: string,
    readonly code: "load_failed" | "unsupported_version" | "invalid_manifest",
  ) {
    super(message);
    this.name = "ManifestLoadError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertManifestV1(value: unknown): asserts value is WebManifest {
  if (!isRecord(value)) {
    throw new ManifestLoadError("Данные медиатеки имеют неверный формат", "invalid_manifest");
  }
  if (value.schema_version !== MANIFEST_SCHEMA_VERSION) {
    throw new ManifestLoadError("Версия данных медиатеки не поддерживается", "unsupported_version");
  }
  if (!Array.isArray(value.works) || !isRecord(value.targets) || !isRecord(value.vocabulary)) {
    throw new ManifestLoadError("Данные медиатеки имеют неверный формат", "invalid_manifest");
  }
}

export async function loadManifest(cacheBust?: string): Promise<WebManifest> {
  const baseUrl = `${import.meta.env.BASE_URL}data/manifest.json`;
  const url = cacheBust ? `${baseUrl}?rev=${encodeURIComponent(cacheBust)}` : baseUrl;
  let response: Response;
  try {
    response = await fetch(url, { headers: { Accept: "application/json" } });
  } catch {
    throw new ManifestLoadError("Не удалось загрузить медиатеку", "load_failed");
  }

  if (!response.ok) {
    throw new ManifestLoadError("Не удалось загрузить медиатеку", "load_failed");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ManifestLoadError("Данные медиатеки имеют неверный формат", "invalid_manifest");
  }

  assertManifestV1(payload);
  return payload;
}

export function vocabularyLabel(manifest: WebManifest, termId: string): string {
  return manifest.vocabulary[termId]?.label_ru ?? termId;
}
