import { tmdbImageUrl } from "../../data/assets";
import type { TargetId, WebManifest, WebWork } from "../../data/types";

type UnknownRecord = Record<string, unknown>;

export type DetailSignal = {
  target: TargetId;
  rating: number | null;
  reaction: string | null;
  viewingStatus: string | null;
  feedbackSummary: string | null;
};

export type DetailPerson = {
  name: string;
  character: string | null;
};

export type WorkDetailModel = {
  id: string;
  title: string;
  titleOriginal: string | null;
  year: number | null;
  format: string | null;
  runtimeMin: number | null;
  genreLabels: string[];
  synopsis: string | null;
  posterUrl: string | null;
  backdropUrl: string | null;
  directors: DetailPerson[];
  cast: DetailPerson[];
  activeSignal: DetailSignal | null;
  signals: Record<TargetId, DetailSignal | null>;
  externalRating: number | null;
  externalVotes: number | null;
};

function record(value: unknown): UnknownRecord | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null;
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function assetPath(external: UnknownRecord, kind: "poster" | "backdrop"): string | null {
  const asset = record(record(external.assets)?.[kind]);
  return stringValue(asset?.path);
}

function people(value: unknown): DetailPerson[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const entry = record(item);
    const name = stringValue(entry?.name);
    if (!name) return [];
    return [{ name, character: stringValue(entry?.character) }];
  });
}

function signalFor(work: WebWork, manifest: WebManifest, target: TargetId): DetailSignal | null {
  const source = manifest.targets.viewers.includes(target)
    ? record(work.viewer_signals[target])
    : record(work.group_signals[target]);
  if (!source) return null;

  return {
    target,
    rating: numberValue(record(source.rating)?.score),
    reaction: stringValue(record(source.reaction)?.value),
    viewingStatus: stringValue(record(source.viewing)?.status),
    feedbackSummary: stringValue(record(source.feedback)?.summary),
  };
}

function vocabularyLabels(manifest: WebManifest, terms: string[]): string[] {
  return terms.map((term) => manifest.vocabulary[term]?.label_ru ?? term);
}

export function buildWorkDetailView(
  manifest: WebManifest,
  workId: string,
  activeTarget: TargetId,
): WorkDetailModel | null {
  const work = manifest.works.find((item) => item.id === workId);
  if (!work) return null;

  const external = work.metadata.external;
  const tmdbMetric = record(record(external.external_metrics)?.tmdb);
  const targets = [...manifest.targets.viewers, ...Object.keys(manifest.targets.groups)];
  const signals = Object.fromEntries(targets.map((target) => [target, signalFor(work, manifest, target)])) as Record<
    TargetId,
    DetailSignal | null
  >;

  return {
    id: work.id,
    title: stringValue(work.identity.title_ru) ?? stringValue(work.identity.title_original) ?? work.id,
    titleOriginal: stringValue(work.identity.title_original),
    year: numberValue(work.identity.year),
    format: stringValue(work.identity.format),
    runtimeMin: numberValue(external.runtime_min),
    genreLabels: vocabularyLabels(manifest, stringArray(external.genres)),
    synopsis: stringValue(external.synopsis_short),
    posterUrl: tmdbImageUrl(assetPath(external, "poster"), "w500"),
    backdropUrl: tmdbImageUrl(assetPath(external, "backdrop"), "w1280"),
    directors: people(external.directors),
    cast: people(external.main_cast),
    activeSignal: signals[activeTarget] ?? null,
    signals,
    externalRating: numberValue(tmdbMetric?.score),
    externalVotes: numberValue(tmdbMetric?.votes),
  };
}
