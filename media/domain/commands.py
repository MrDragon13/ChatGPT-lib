from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, TypeAlias

from .types import CreationContext, MediaEntryPreconditions, SemanticSnapshot, TargetEdit, TargetUpdate, WorkRef


@dataclass(frozen=True)
class RecordMediaEntryCommand:
    schema_version: int
    operation_id: str
    idempotency_key: str
    work_ref: WorkRef
    create_if_missing: bool
    target_updates: tuple[TargetUpdate, ...]
    creation_context: CreationContext | None
    semantic_snapshot: SemanticSnapshot | None
    preconditions: MediaEntryPreconditions


@dataclass(frozen=True)
class EditViewingFeedbackCommand:
    schema_version: int
    operation_id: str
    work_ref: WorkRef
    target_edits: tuple[TargetEdit, ...]


@dataclass(frozen=True)
class SetInterestCommand:
    schema_version: int
    operation_id: str
    work_ref: WorkRef
    target: str
    state: Literal["unknown", "candidate", "shortlist", "not_interested"]
    priority: int | None


@dataclass(frozen=True)
class AddWorkCommand:
    schema_version: int
    operation_id: str
    work_ref: WorkRef


@dataclass(frozen=True)
class ProviderWorkRef:
    media_type: Literal["movie"]
    id: int


@dataclass(frozen=True)
class RefreshMetadataCommand:
    schema_version: int
    operation_id: str
    scope: Literal["all_movies"]
    tmdb_overrides: Mapping[str, ProviderWorkRef]
    year_overrides: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class RefreshWorkMetadataCommand:
    schema_version: int
    operation_id: str
    work_ref: WorkRef
    expected_work_digest: str


@dataclass(frozen=True)
class SetInferredPreferencesCommand:
    schema_version: int
    operation_id: str
    target: str
    hypotheses: tuple[Mapping[str, Any], ...]
    analysis: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class SetSemanticFingerprintCommand:
    schema_version: int
    operation_id: str
    work_ref: WorkRef
    traits: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class RecordRecommendationInteractionCommand:
    schema_version: int
    operation_id: str
    session_id: str
    target: str
    work_ref: WorkRef
    event: Literal["recommended", "selected", "already_watched", "not_tonight", "not_interested"]
    note: str | None = None
    at: str | None = None


@dataclass(frozen=True)
class SetWorkSimilarityCommand:
    schema_version: int
    operation_id: str
    target: str
    left: WorkRef
    right: WorkRef
    terms: tuple[str, ...]
    note: str | None = None


@dataclass(frozen=True)
class RemoveWorkSimilarityCommand:
    schema_version: int
    operation_id: str
    target: str
    left: WorkRef
    right: WorkRef



@dataclass(frozen=True)
class MediaEntryContextRequest:
    schema_version: int
    work_ref: WorkRef
    target: str


@dataclass(frozen=True)
class RecommendContextRequest:
    schema_version: int
    target: str
    text: str | None
    only_unwatched: bool
    runtime_max: int | None
    include_not_interested: bool
    limit: int


@dataclass(frozen=True)
class TasteContextRequest:
    schema_version: int
    target: str
    recent_limit: int
    representative_limit: int


@dataclass(frozen=True)
class AssessCandidateRequest:
    schema_version: int
    target: str
    candidate: WorkRef
    text: str | None


MediaCommand: TypeAlias = (
    RecordMediaEntryCommand
    | EditViewingFeedbackCommand
    | SetInterestCommand
    | AddWorkCommand
    | RefreshMetadataCommand
    | RefreshWorkMetadataCommand
    | SetInferredPreferencesCommand
    | SetSemanticFingerprintCommand
    | RecordRecommendationInteractionCommand
    | SetWorkSimilarityCommand
    | RemoveWorkSimilarityCommand
)

ReadRequest: TypeAlias = MediaEntryContextRequest | RecommendContextRequest | TasteContextRequest | AssessCandidateRequest
