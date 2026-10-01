import { Navigate, Route, Routes } from "react-router-dom";

import type { ManifestTargetConfig, TargetId } from "../data/types";
import { WorkDetailPage } from "../features/detail/WorkDetailPage";
import { HistoryPage } from "../features/history/HistoryPage";
import { HomePage } from "../features/home/HomePage";
import { LibraryPage } from "../features/library/LibraryPage";

export function configuredTargets(config: ManifestTargetConfig): Set<TargetId> {
  return new Set([...config.targets.viewers, ...Object.keys(config.targets.groups)]);
}

export function resolveTarget(config: ManifestTargetConfig, searchParams: URLSearchParams): TargetId {
  const requested = searchParams.get("target");
  const available = configuredTargets(config);
  if (requested && available.has(requested)) return requested;
  if (config.default_target && available.has(config.default_target)) return config.default_target;
  return [...available].sort()[0] ?? "primary";
}

export function workHref(workId: string, target: TargetId): string {
  const query = new URLSearchParams({ target });
  return `#/work/${encodeURIComponent(workId)}?${query.toString()}`;
}

export function historyHref(target: TargetId): string {
  const query = new URLSearchParams({ target });
  return `#/history?${query.toString()}`;
}

export function libraryHref(
  target: TargetId,
  filters: Record<string, string | null | undefined> = {},
): string {
  const query = new URLSearchParams({ target });
  for (const [key, value] of Object.entries(filters)) {
    if (value) query.set(key, value);
  }
  return `#/library?${query.toString()}`;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/today" element={<HomePage />} />
      <Route path="/history" element={<HistoryPage />} />
      <Route path="/library" element={<LibraryPage />} />
      <Route path="/work/:id" element={<WorkDetailPage />} />
      <Route path="*" element={<Navigate to="/today" replace />} />
    </Routes>
  );
}
