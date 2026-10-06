from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, TypeAlias

from .types import TargetEdit, TargetUpdate, WorkRef


@dataclass(frozen=True)
class RecordViewingFeedbackCommand:
    schema_version: int
    operation_id: str
    work_ref: WorkRef
    target_updates: tuple[TargetUpdate, ...]
    create_if_missing: bool = False


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
class ReserveReassessmentSessionCommand:
    schema_version: int
    operation_id: str
    pilot_id: str
    session_id: str
    work_ids: tuple[str, ...]
    expected_ledger_digest: str


@dataclass(frozen=True)
class CompleteReassessmentItemCommand:
    schema_version: int
    operation_id: str
    pilot_id: str
    session_id: str
    work_id: str
    expected_ledger_digest: str
    outcome: Literal["changed", "confirmed_unchanged", "deferred"]
    historical_exposure: Mapping[str, Any] | None = None
    feedback_edit: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class CloseReassessmentSessionCommand:
    schema_version: int
    operation_id: str
    pilot_id: str
    session_id: str
    expected_ledger_digest: str
    scheduled_reanalysis_operation_id: str | None = None


@dataclass(frozen=True)
class RecordReassessmentModernizationCommand:
    schema_version: int
    operation_id: str
    pilot_id: str
    work_id: str
    outcome: Literal["completed", "blocked"]
    expected_ledger_digest: str
    expected_work_digest: str
    metadata_operation_id: str | None = None
    semantic_operation_id: str | None = None
    vocabulary_digest: str | None = None
    blocker_code: Literal[
        "provider_identity_missing",
        "provider_identity_ambiguous",
        "provider_identity_conflict",
        "semantic_context_insufficient",
    ] | None = None


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
    RecordViewingFeedbackCommand
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
    | ReserveReassessmentSessionCommand
    | CompleteReassessmentItemCommand
    | CloseReassessmentSessionCommand
    | RecordReassessmentModernizationCommand
)

ReadRequest: TypeAlias = RecommendContextRequest | TasteContextRequest | AssessCandidateRequest
