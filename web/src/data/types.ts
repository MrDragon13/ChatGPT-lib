export type TargetId = string;

export type VocabularyEntry = {
  kind: string;
  label_ru: string;
};

export type RecommendationCandidate = {
  id?: string;
  work_id?: string;
  title?: string;
  evidence?: unknown;
  [key: string]: unknown;
};

export type RecommendationContext = {
  target: TargetId;
  request: Record<string, unknown>;
  candidates: RecommendationCandidate[];
};

export type WorkIdentity = {
  format?: string;
  title_original?: string | null;
  title_ru?: string | null;
  alternate_titles?: string[];
  year?: number | null;
  external_ids?: Record<string, unknown>;
  [key: string]: unknown;
};

export type WebWork = {
  id: string;
  identity: WorkIdentity;
  metadata: { external: Record<string, unknown> };
  viewer_signals: Record<string, unknown>;
  group_signals: Record<string, unknown>;
  interest: Record<string, unknown>;
  traits: string[];
  collections: string[];
  provenance: {
    created_at: string | null;
    updated_at: string | null;
  };
};

export type WebManifest = {
  schema_version: 1;
  default_target: TargetId | null;
  targets: {
    viewers: TargetId[];
    groups: Record<TargetId, TargetId[]>;
  };
  vocabulary: Record<string, VocabularyEntry>;
  profiles: Record<string, Record<string, unknown>>;
  recommendations: Record<TargetId, RecommendationContext>;
  works: WebWork[];
};

export type ManifestTargetConfig = Pick<WebManifest, "default_target" | "targets">;
