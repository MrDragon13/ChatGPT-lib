export type TargetId = string;

export type VocabularyEntry = {
  kind: string;
  label_ru: string;
};

export type Confidence = "high" | "medium" | "low" | "none" | string;

export type SemanticTrait = {
  term: string;
  source: string;
  confidence: Confidence;
  [key: string]: unknown;
};

export type EvidencePointer = {
  entity_id?: string | null;
  source_target?: string | null;
  source_kind?: string;
  kind?: string;
  [key: string]: unknown;
};

export type InferredPreference = {
  id: string;
  statement: string;
  affinity: number;
  confidence: Confidence;
  terms: string[];
  evidence: EvidencePointer[];
};

export type TasteAffinity = {
  term: string;
  score: number;
  confidence: Confidence;
  evidence_count: number;
  evidence: EvidencePointer[];
};

export type TasteRepresentativeWork = {
  id: string;
  title_original?: string | null;
  title_ru?: string | null;
  year?: number | null;
  ratings?: Record<TargetId, number>;
  traits?: string[];
  [key: string]: unknown;
};

export type TasteContext = {
  schema_version: 1;
  target: TargetId;
  profile: {
    explicit_preferences: Record<string, unknown>[];
    inferred_preferences: InferredPreference[];
    rules: Record<string, unknown>[];
    constraints: Record<string, unknown>[];
    strongest_affinities: TasteAffinity[];
    summary: Record<string, number | string | boolean | null>;
  };
  representative: {
    high: TasteRepresentativeWork[];
    low: TasteRepresentativeWork[];
  };
  recent_feedback: Record<string, unknown>[];
  exclusions: {
    watched: string[];
    not_interested: string[];
  };
  couple?: {
    members: TargetId[];
    agreements: TasteRepresentativeWork[];
    disagreements: TasteRepresentativeWork[];
  };
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
  medium?: string;
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
  semantic_fingerprint?: SemanticTrait[];
  collections: string[];
  provenance: {
    created_at: string | null;
    updated_at: string | null;
  };
};

export type WebManifest = {
  // The exporter always emits v2. v1 remains readable during a staged static deploy/cache overlap.
  schema_version: 1 | 2;
  default_target: TargetId | null;
  targets: {
    viewers: TargetId[];
    groups: Record<TargetId, TargetId[]>;
  };
  vocabulary: Record<string, VocabularyEntry>;
  profiles: Record<string, Record<string, unknown>>;
  taste_contexts?: Record<TargetId, TasteContext>;
  recommendations: Record<TargetId, RecommendationContext>;
  works: WebWork[];
};

export type ManifestTargetConfig = Pick<WebManifest, "default_target" | "targets">;
