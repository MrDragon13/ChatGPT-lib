import { tmdbImageUrl } from "../../data/assets";
import type { TargetId, WebManifest, WebWork } from "../../data/types";

export type HistoryItemModel = {
  id: string;
  title: string;
  year: number | null;
  posterUrl: string | null;
  rating: number | null;
  reaction: string | null;
  feedbackSummary: string | null;
  activityAt: string;
  activityPrecision: "exact" | "day";
};

type UnknownRecord = Record<string, unknown>;

type Activity = {
  at: string;
  precision: "exact" | "day";
  sortTime: number;
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

function targetSignal(manifest: WebManifest, work: WebWork, target: TargetId): UnknownRecord | null {
  return manifest.targets.viewers.includes(target)
    ? record(work.viewer_signals[target])
    : record(work.group_signals[target]);
}

function eligible(signal: UnknownRecord | null): signal is UnknownRecord {
  if (!signal) return false;
  return ["viewing", "rating", "reaction", "feedback"].some(
    (key) => signal[key] !== undefined && signal[key] !== null,
  );
}

function parsedTime(value: string | null): number | null {
  if (!value) return null;
  const time = Date.parse(value);
  return Number.isFinite(time) ? time : null;
}

function exactActivity(signal: UnknownRecord): Activity | null {
  if (!Array.isArray(signal.history)) return null;
  let latest: Activity | null = null;
  for (const rawEntry of signal.history) {
    const entry = record(rawEntry);
    const at = stringValue(entry?.at);
    const sortTime = parsedTime(at);
    if (!at || sortTime === null) continue;
    if (!latest || sortTime > latest.sortTime) {
      latest = { at, precision: "exact", sortTime };
    }
  }
  return latest;
}

function provenanceActivity(work: WebWork): Activity | null {
  for (const at of [work.provenance.updated_at, work.provenance.created_at]) {
    const value = stringValue(at);
    const sortTime = parsedTime(value);
    if (value && sortTime !== null) return { at: value, precision: "day", sortTime };
  }
  return null;
}

function activityFor(work: WebWork, signal: UnknownRecord): Activity {
  return exactActivity(signal) ?? provenanceActivity(work) ?? { at: "", precision: "day", sortTime: -Infinity };
}

function assetPath(work: WebWork): string | null {
  const assets = record(work.metadata.external.assets);
  return stringValue(record(assets?.poster)?.path);
}

function titleFor(work: WebWork): string {
  return stringValue(work.identity.title_ru) ?? stringValue(work.identity.title_original) ?? work.id;
}

function reactionFor(signal: UnknownRecord): string | null {
  const reaction = record(signal.reaction);
  return stringValue(reaction?.label) ?? stringValue(reaction?.value) ?? stringValue(signal.reaction);
}

export function buildHistoryItems(manifest: WebManifest, target: TargetId): HistoryItemModel[] {
  return manifest.works
    .flatMap((work) => {
      const signal = targetSignal(manifest, work, target);
      if (!eligible(signal)) return [];
      const activity = activityFor(work, signal);
      const item: HistoryItemModel & { sortTime: number } = {
        id: work.id,
        title: titleFor(work),
        year: numberValue(work.identity.year),
        posterUrl: tmdbImageUrl(assetPath(work), "w500"),
        rating: numberValue(record(signal.rating)?.score),
        reaction: reactionFor(signal),
        feedbackSummary: stringValue(record(signal.feedback)?.summary),
        activityAt: activity.at,
        activityPrecision: activity.precision,
        sortTime: activity.sortTime,
      };
      return [item];
    })
    .sort((left, right) => right.sortTime - left.sortTime || left.id.localeCompare(right.id))
    .map(({ sortTime: _sortTime, ...item }) => item);
}
