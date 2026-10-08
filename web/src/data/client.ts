import type { WebManifest } from "./types";

const SUPPORTED_MANIFEST_SCHEMA_VERSIONS = new Set([1, 2, 3, 4]);

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

function assertSupportedManifest(value: unknown): asserts value is WebManifest {
  if (!isRecord(value)) {
    throw new ManifestLoadError("Данные медиатеки имеют неверный формат", "invalid_manifest");
  }
  if (typeof value.schema_version !== "number" || !SUPPORTED_MANIFEST_SCHEMA_VERSIONS.has(value.schema_version)) {
    throw new ManifestLoadError("Версия данных медиатеки не поддерживается", "unsupported_version");
  }
  if (!Array.isArray(value.works) || !isRecord(value.targets) || !isRecord(value.vocabulary)) {
    throw new ManifestLoadError("Данные медиатеки имеют неверный формат", "invalid_manifest");
  }
  if (value.schema_version >= 2 && !isRecord(value.taste_contexts)) {
    throw new ManifestLoadError("Данные медиатеки имеют неверный формат", "invalid_manifest");
  }
}

export async function loadManifest(cacheBust?: string): Promise<WebManifest> {
  const baseUrl = `${import.meta.env.BASE_URL}data/manifest.json`;
  const url = cacheBust ? `${baseUrl}?rev=${encodeURIComponent(cacheBust)}` : baseUrl;
  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
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

  assertSupportedManifest(payload);
  return payload;
}

export function vocabularyLabel(manifest: WebManifest, termId: string): string {
  return manifest.vocabulary[termId]?.label_ru ?? termId;
}
