import { tmdbImageUrl } from "../../data/assets";
import type {
  RecommendationCandidate,
  TargetId,
  WebManifest,
  WebWork,
} from "../../data/types";

export type HomeCandidate = {
  id: string;
  title: string;
  titleOriginal: string | null;
  year: number | null;
  runtimeMin: number | null;
  posterUrl: string | null;
  backdropUrl: string | null;
  reasonLabels: string[];
  concernLabels: string[];
  genreLabels: string[];
  personalRating: number | null;
  personalReaction: string | null;
};

export type RecentWork = HomeCandidate & { date: string };

export type HomeTasteAffinity = {
  term: string;
  label: string;
  score: number;
  confidence: string;
  evidenceCount: number;
};

export type HomeTasteStatement = {
  id: string;
  statement: string;
  label: string | null;
  confidence: string | null;
};

export type HomeTasteModel = {
  strongest: HomeTasteAffinity[];
  explicit: HomeTasteStatement[];
  inferred: HomeTasteStatement[];
  couple: { agreements: number; disagreements: number } | null;
};

export type HomeViewModel = {
  target: TargetId;
  hero: HomeCandidate | null;
  alternatives: HomeCandidate[];
  next: HomeCandidate[];
  couple: HomeCandidate[];
  recent: RecentWork[];
  taste: HomeTasteModel | null;
};

type UnknownRecord = Record<string, unknown>;

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

function candidateId(candidate: RecommendationCandidate): string | null {
  return stringValue(candidate.id) ?? stringValue(candidate.work_id);
}

function targetSignal(manifest: WebManifest, work: WebWork, target: TargetId): UnknownRecord | null {
  if (manifest.targets.viewers.includes(target)) {
    return record(work.viewer_signals[target]);
  }
  return record(work.group_signals[target]);
}

function signalRating(signal: UnknownRecord | null): number | null {
  return numberValue(record(signal?.rating)?.score);
}

function signalReaction(signal: UnknownRecord | null): string | null {
  const reaction = record(signal?.reaction);
  return stringValue(reaction?.label) ?? stringValue(reaction?.value) ?? stringValue(signal?.reaction);
}

function vocabularyLabels(manifest: WebManifest, terms: string[]): string[] {
  return terms.map((term) => manifest.vocabulary[term]?.label_ru ?? term);
}

function vocabularyLabel(manifest: WebManifest, term: string | null): string | null {
  if (!term) return null;
  return manifest.vocabulary[term]?.label_ru ?? term;
}

function external(work: WebWork): UnknownRecord {
  return work.metadata.external;
}

function assetPath(work: WebWork, kind: "poster" | "backdrop"): string | null {
  const assets = record(external(work).assets);
  const asset = record(assets?.[kind]);
  return stringValue(asset?.path);
}

function titleFor(work: WebWork, candidate?: RecommendationCandidate): string {
  return (
    stringValue(candidate?.title_ru) ??
    stringValue(work.identity.title_ru) ??
    stringValue(candidate?.title_original) ??
    stringValue(work.identity.title_original) ??
    work.id
  );
}

function candidateToView(
  manifest: WebManifest,
  target: TargetId,
  work: WebWork,
  candidate?: RecommendationCandidate,
): HomeCandidate {
  const evidence = record(candidate?.evidence);
  const strengths = stringArray(evidence?.strengths);
  const concerns = stringArray(evidence?.concerns);
  const candidateGenres = stringArray(candidate?.genres);
  const genres = candidateGenres.length ? candidateGenres : stringArray(external(work).genres);
  const signal = targetSignal(manifest, work, target);

  return {
    id: work.id,
    title: titleFor(work, candidate),
    titleOriginal: stringValue(work.identity.title_original),
    year: numberValue(candidate?.year) ?? numberValue(work.identity.year),
    runtimeMin: numberValue(candidate?.runtime_min) ?? numberValue(external(work).runtime_min),
    posterUrl: tmdbImageUrl(assetPath(work, "poster"), "w500"),
    backdropUrl: tmdbImageUrl(assetPath(work, "backdrop"), "w1280"),
    reasonLabels: vocabularyLabels(manifest, strengths),
    concernLabels: vocabularyLabels(manifest, concerns),
    genreLabels: vocabularyLabels(manifest, genres),
    personalRating: signalRating(signal),
    personalReaction: signalReaction(signal),
  };
}

function recommendationViews(manifest: WebManifest, target: TargetId): HomeCandidate[] {
  const context = manifest.recommendations[target];
  if (!context) return [];
  const works = new Map(manifest.works.map((work) => [work.id, work]));
  return context.candidates.flatMap((candidate) => {
    const id = candidateId(candidate);
    if (!id) return [];
    const work = works.get(id);
    if (!work) return [];
    return [candidateToView(manifest, target, work, candidate)];
  });
}

function truthfulRecentDate(work: WebWork, signal: UnknownRecord | null): string | null {
  const viewing = record(signal?.viewing);
  const explicit = stringValue(viewing?.last_watched_at);
  if (explicit) return explicit;
  return stringValue(work.provenance.updated_at) ?? stringValue(work.provenance.created_at);
}

function watched(signal: UnknownRecord | null): boolean {
  const viewing = record(signal?.viewing);
  return viewing?.status === "watched" || viewing?.viewing === "watched" || signal?.viewing === "watched";
}

function recentViews(manifest: WebManifest, target: TargetId): RecentWork[] {
  if (!manifest.targets.viewers.includes(target)) return [];
  return manifest.works
    .flatMap((work) => {
      const signal = targetSignal(manifest, work, target);
      if (!watched(signal)) return [];
      const date = truthfulRecentDate(work, signal);
      if (!date) return [];
      return [{ ...candidateToView(manifest, target, work), date }];
    })
    .sort((left, right) => right.date.localeCompare(left.date))
    .slice(0, 12);
}

function tasteStatement(manifest: WebManifest, value: unknown): HomeTasteStatement | null {
  const item = record(value);
  if (!item) return null;
  const id = stringValue(item.id);
  const statement = stringValue(item.statement);
  if (!id || !statement) return null;
  return {
    id,
    statement,
    label: vocabularyLabel(manifest, stringValue(item.term)),
    confidence: stringValue(item.confidence),
  };
}

function tasteView(manifest: WebManifest, target: TargetId): HomeTasteModel | null {
  const context = manifest.taste_contexts?.[target];
  if (!context) return null;

  const strongest = context.profile.strongest_affinities.slice(0, 6).map((item) => ({
    term: item.term,
    label: manifest.vocabulary[item.term]?.label_ru ?? item.term,
    score: item.score,
    confidence: item.confidence,
    evidenceCount: item.evidence_count,
  }));

  const explicit = context.profile.explicit_preferences
    .map((item) => tasteStatement(manifest, item))
    .filter((item): item is HomeTasteStatement => item !== null)
    .slice(0, 4);

  const inferred = context.profile.inferred_preferences.slice(0, 4).map((item) => ({
    id: item.id,
    statement: item.statement,
    label: item.terms.length === 1 ? vocabularyLabel(manifest, item.terms[0]) : null,
    confidence: item.confidence,
  }));

  const couple = context.couple
    ? {
        agreements: context.couple.agreements.length,
        disagreements: context.couple.disagreements.length,
      }
    : null;

  if (!strongest.length && !explicit.length && !inferred.length && !couple) return null;
  return { strongest, explicit, inferred, couple };
}

export function buildHomeViewModel(manifest: WebManifest, target: TargetId): HomeViewModel {
  const recommendations = recommendationViews(manifest, target);
  return {
    target,
    hero: recommendations[0] ?? null,
    alternatives: recommendations.slice(1, 4),
    next: recommendations.slice(4, 16),
    couple: recommendationViews(manifest, "couple").slice(0, 12),
    recent: recentViews(manifest, target),
    taste: tasteView(manifest, target),
  };
}
