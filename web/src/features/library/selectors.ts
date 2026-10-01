import type { TargetId, WebManifest, WebWork } from "../../data/types";

export type ViewingFilter = "all" | "watched" | "unwatched";

export type LibraryFilters = {
  query: string;
  viewing: ViewingFilter;
  genre: string | null;
  year: number | null;
};

type UnknownRecord = Record<string, unknown>;

function record(value: unknown): UnknownRecord | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function normalize(value: string): string {
  return value.trim().toLocaleLowerCase("ru-RU");
}

function viewerStatus(work: WebWork, viewer: TargetId): string {
  const signal = record(work.viewer_signals[viewer]);
  return String(record(signal?.viewing)?.status ?? "unwatched");
}

function viewingStatus(manifest: WebManifest, work: WebWork, target: TargetId): string {
  if (manifest.targets.viewers.includes(target)) return viewerStatus(work, target);

  const groupSignal = record(work.group_signals[target]);
  const explicit = record(groupSignal?.viewing)?.status;
  if (typeof explicit === "string") return explicit;

  const members = manifest.targets.groups[target] ?? [];
  if (!members.length) return "unwatched";
  const statuses = members.map((member) => viewerStatus(work, member));
  if (statuses.every((status) => status === "watched")) return "watched";
  return "unwatched";
}

function matchesQuery(work: WebWork, query: string): boolean {
  const needle = normalize(query);
  if (!needle) return true;
  const titles = [
    work.identity.title_ru,
    work.identity.title_original,
    ...stringArray(work.identity.alternate_titles),
  ];
  return titles.some((value) => typeof value === "string" && normalize(value).includes(needle));
}

function matchesViewing(manifest: WebManifest, work: WebWork, target: TargetId, filter: ViewingFilter): boolean {
  if (filter === "all") return true;
  const status = viewingStatus(manifest, work, target);
  return filter === "watched" ? status === "watched" : status !== "watched";
}

function matchesGenre(work: WebWork, genre: string | null): boolean {
  if (!genre) return true;
  return stringArray(work.metadata.external.genres).includes(genre);
}

function matchesYear(work: WebWork, year: number | null): boolean {
  if (year === null) return true;
  return work.identity.year === year;
}

function sortTitle(work: WebWork): string {
  return String(work.identity.title_ru ?? work.identity.title_original ?? work.id);
}

export function filterLibrary(
  manifest: WebManifest,
  target: TargetId,
  filters: LibraryFilters,
): WebWork[] {
  return manifest.works
    .filter(
      (work) =>
        matchesQuery(work, filters.query) &&
        matchesViewing(manifest, work, target, filters.viewing) &&
        matchesGenre(work, filters.genre) &&
        matchesYear(work, filters.year),
    )
    .sort((left, right) => sortTitle(left).localeCompare(sortTitle(right), "ru-RU"));
}

export function libraryFiltersFromSearchParams(params: URLSearchParams): LibraryFilters {
  const viewing = params.get("viewing");
  const year = params.get("year");
  return {
    query: params.get("q") ?? "",
    viewing: viewing === "watched" || viewing === "unwatched" ? viewing : "all",
    genre: params.get("genre") || null,
    year: year && /^\d{4}$/.test(year) ? Number(year) : null,
  };
}

export function libraryFiltersToSearchParams(
  filters: LibraryFilters,
  target: TargetId,
): URLSearchParams {
  const params = new URLSearchParams({ target });
  if (filters.query.trim()) params.set("q", filters.query.trim());
  if (filters.viewing !== "all") params.set("viewing", filters.viewing);
  if (filters.genre) params.set("genre", filters.genre);
  if (filters.year !== null) params.set("year", String(filters.year));
  return params;
}
