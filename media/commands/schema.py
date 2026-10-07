from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID

from media.domain.commands import (
    AddWorkCommand,
    AssessCandidateRequest,
    CloseReassessmentSessionCommand,
    CompleteReassessmentItemCommand,
    EditViewingFeedbackCommand,
    MediaCommand,
    ProviderWorkRef,
    ReadRequest,
    RecommendContextRequest,
    RecordMediaEntryCommand,
    RecordRecommendationInteractionCommand,
    RecordReassessmentModernizationCommand,
    RecordViewingFeedbackCommand,
    RefreshMetadataCommand,
    RefreshWorkMetadataCommand,
    RemoveWorkSimilarityCommand,
    ReserveReassessmentSessionCommand,
    SetInferredPreferencesCommand,
    SetInterestCommand,
    SetSemanticFingerprintCommand,
    SetWorkSimilarityCommand,
    TasteContextRequest,
)
from media.domain.errors import CommandValidationError
from media.domain.types import CreationContext, MediaEntryPreconditions, ProviderIdentity, SemanticSnapshot, TargetEdit, TargetUpdate, WorkRef
from media.tools.schema_utils import validate_against_schema

_SCHEMA_BY_OPERATION = {
    "record_media_entry": "record_media_entry.schema.json",
    "record_viewing_feedback": "record_viewing_feedback.schema.json",
    "edit_viewing_feedback": "edit_viewing_feedback.schema.json",
    "set_interest": "set_interest.schema.json",
    "add_work": "add_work.schema.json",
    "refresh_metadata": "refresh_metadata.schema.json",
    "refresh_work_metadata": "refresh_work_metadata.schema.json",
    "set_inferred_preferences": "set_inferred_preferences.schema.json",
    "set_semantic_fingerprint": "set_semantic_fingerprint.schema.json",
    "record_recommendation_interaction": "record_recommendation_interaction.schema.json",
    "set_work_similarity": "set_work_similarity.schema.json",
    "remove_work_similarity": "remove_work_similarity.schema.json",
    "reserve_reassessment_session": "reserve_reassessment_session.schema.json",
    "complete_reassessment_item": "complete_reassessment_item.schema.json",
    "close_reassessment_session": "close_reassessment_session.schema.json",
    "record_reassessment_modernization": "record_reassessment_modernization.schema.json",
    "recommend_context": "recommend_context.schema.json",
    "taste_context": "taste_context.schema.json",
    "assess_candidate": "assess_candidate.schema.json",
}

_READ_ONLY_OPERATIONS = {"recommend_context", "taste_context", "assess_candidate"}


def _work_ref(data: Mapping[str, Any]) -> WorkRef:
    return WorkRef(
        id=data.get("id"),
        title=data.get("title"),
        year=data.get("year"),
        tmdb_media_type=data.get("tmdb_media_type"),
        tmdb_id=data.get("tmdb_id"),
        imdb_id=data.get("imdb_id"),
    )


def _validate_uuid(value: str, label: str = "operation_id") -> None:
    try:
        parsed = UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise CommandValidationError(f"{label} must be a canonical UUID") from exc
    if str(parsed) != value:
        raise CommandValidationError(f"{label} must be canonical lowercase UUID text")


def parse_command(data: Mapping[str, Any], schema_dir: Path | None = None) -> MediaCommand | ReadRequest:
    schema_dir = schema_dir or Path(__file__).with_name("schemas")
    operation = data.get("operation")
    schema_name = _SCHEMA_BY_OPERATION.get(operation)
    if schema_name is None:
        raise CommandValidationError(f"unknown operation: {operation}")
    errors = validate_against_schema(dict(data), schema_name, schema_dir)
    if errors:
        raise CommandValidationError("; ".join(errors))
    if operation not in _READ_ONLY_OPERATIONS:
        _validate_uuid(str(data["operation_id"]))
    if operation == "record_media_entry":
        _validate_uuid(str(data["idempotency_key"]), "idempotency_key")
    if operation in {"reserve_reassessment_session", "complete_reassessment_item", "close_reassessment_session"}:
        _validate_uuid(str(data["session_id"]), "session_id")
    if operation == "close_reassessment_session" and data.get("scheduled_reanalysis_operation_id") is not None:
        _validate_uuid(str(data["scheduled_reanalysis_operation_id"]), "scheduled_reanalysis_operation_id")
    if operation == "record_reassessment_modernization":
        for key in ("metadata_operation_id", "semantic_operation_id"):
            if data.get(key) is not None:
                _validate_uuid(str(data[key]), key)
    if operation == "record_media_entry":
        updates = tuple(
            TargetUpdate(
                target=item["target"],
                viewing=item.get("viewing"),
                rating=item.get("rating"),
                reaction=item.get("reaction"),
                feedback=item.get("feedback"),
            )
            for item in data["target_updates"]
        )
        expected = dict(data["preconditions"].get("expected_viewer_digests") or {})
        if not data["create_if_missing"]:
            missing = sorted({update.target for update in updates} - set(expected))
            if missing:
                raise CommandValidationError(
                    "expected viewer digest is required for target(s): " + ", ".join(missing)
                )
        creation_context = None
        raw_creation = data.get("creation_context")
        if raw_creation is not None:
            raw_provider = raw_creation["provider_identity"]
            creation_context = CreationContext(
                resolved_identity=dict(raw_creation["resolved_identity"]),
                provider_identity=ProviderIdentity(raw_provider["media_type"], raw_provider["id"]),
                minimum_metadata=dict(raw_creation["minimum_metadata"]),
            )
        semantic_snapshot = None
        raw_semantic = data.get("semantic_snapshot")
        if raw_semantic is not None:
            semantic_snapshot = SemanticSnapshot(
                traits=tuple(dict(item) for item in raw_semantic["traits"]),
                semantic_input_digest=raw_semantic["semantic_input_digest"],
                vocabulary_digest=raw_semantic["vocabulary_digest"],
                algorithm_version=raw_semantic["algorithm_version"],
            )
        return RecordMediaEntryCommand(
            data["schema_version"],
            data["operation_id"],
            data["idempotency_key"],
            _work_ref(data["work_ref"]),
            data["create_if_missing"],
            updates,
            creation_context,
            semantic_snapshot,
            MediaEntryPreconditions(expected),
        )
    if operation == "record_viewing_feedback":
        updates = tuple(
            TargetUpdate(
                target=item["target"],
                viewing=item.get("viewing"),
                rating=item.get("rating"),
                reaction=item.get("reaction"),
                feedback=item.get("feedback"),
            )
            for item in data["target_updates"]
        )
        return RecordViewingFeedbackCommand(
            data["schema_version"], data["operation_id"], _work_ref(data["work_ref"]), updates, data.get("create_if_missing", False)
        )
    if operation == "edit_viewing_feedback":
        edits = tuple(
            TargetEdit(
                target=item["target"],
                set_values=dict(item.get("set") or {}),
                clear=tuple(item.get("clear") or ()),
                purge=bool(item.get("purge", False)),
            )
            for item in data["target_edits"]
        )
        return EditViewingFeedbackCommand(data["schema_version"], data["operation_id"], _work_ref(data["work_ref"]), edits)
    if operation == "set_interest":
        return SetInterestCommand(data["schema_version"], data["operation_id"], _work_ref(data["work_ref"]), data["target"], data["state"], data.get("priority"))
    if operation == "add_work":
        return AddWorkCommand(data["schema_version"], data["operation_id"], _work_ref(data["work_ref"]))
    if operation == "refresh_metadata":
        overrides = {work_id: ProviderWorkRef(value["media_type"], value["id"]) for work_id, value in (data.get("tmdb_overrides") or {}).items()}
        return RefreshMetadataCommand(data["schema_version"], data["operation_id"], data["scope"], overrides, dict(data.get("year_overrides") or {}))
    if operation == "refresh_work_metadata":
        return RefreshWorkMetadataCommand(
            data["schema_version"],
            data["operation_id"],
            _work_ref(data["work_ref"]),
            data["expected_work_digest"],
        )
    if operation == "set_inferred_preferences":
        return SetInferredPreferencesCommand(
            data["schema_version"],
            data["operation_id"],
            data["target"],
            tuple(dict(item) for item in data["hypotheses"]),
            dict(data["analysis"]) if data.get("analysis") is not None else None,
        )
    if operation == "set_semantic_fingerprint":
        return SetSemanticFingerprintCommand(data["schema_version"], data["operation_id"], _work_ref(data["work_ref"]), tuple(dict(item) for item in data["traits"]))
    if operation == "record_recommendation_interaction":
        return RecordRecommendationInteractionCommand(data["schema_version"], data["operation_id"], data["session_id"], data["target"], _work_ref(data["work_ref"]), data["event"], data.get("note"), data.get("at"))
    if operation == "set_work_similarity":
        return SetWorkSimilarityCommand(
            data["schema_version"],
            data["operation_id"],
            data["target"],
            _work_ref(data["left"]),
            _work_ref(data["right"]),
            tuple(data.get("terms") or ()),
            data.get("note"),
        )
    if operation == "remove_work_similarity":
        return RemoveWorkSimilarityCommand(
            data["schema_version"],
            data["operation_id"],
            data["target"],
            _work_ref(data["left"]),
            _work_ref(data["right"]),
        )
    if operation == "reserve_reassessment_session":
        return ReserveReassessmentSessionCommand(
            data["schema_version"],
            data["operation_id"],
            data["pilot_id"],
            data["session_id"],
            tuple(data["work_ids"]),
            data["expected_ledger_digest"],
        )
    if operation == "complete_reassessment_item":
        return CompleteReassessmentItemCommand(
            data["schema_version"],
            data["operation_id"],
            data["pilot_id"],
            data["session_id"],
            data["work_id"],
            data["expected_ledger_digest"],
            data["outcome"],
            dict(data["historical_exposure"]) if data.get("historical_exposure") is not None else None,
            dict(data["feedback_edit"]) if data.get("feedback_edit") is not None else None,
        )
    if operation == "close_reassessment_session":
        return CloseReassessmentSessionCommand(
            data["schema_version"],
            data["operation_id"],
            data["pilot_id"],
            data["session_id"],
            data["expected_ledger_digest"],
            data.get("scheduled_reanalysis_operation_id"),
        )
    if operation == "record_reassessment_modernization":
        return RecordReassessmentModernizationCommand(
            data["schema_version"],
            data["operation_id"],
            data["pilot_id"],
            data["work_id"],
            data["outcome"],
            data["expected_ledger_digest"],
            data["expected_work_digest"],
            data.get("metadata_operation_id"),
            data.get("semantic_operation_id"),
            data.get("vocabulary_digest"),
            data.get("blocker_code"),
        )
    if operation == "taste_context":
        return TasteContextRequest(data["schema_version"], data["target"], data.get("recent_limit", 10), data.get("representative_limit", 10))
    if operation == "assess_candidate":
        return AssessCandidateRequest(data["schema_version"], data["target"], _work_ref(data["candidate"]), data.get("text"))
    return RecommendContextRequest(data["schema_version"], data["target"], data.get("text"), data.get("only_unwatched", False), data.get("runtime_max"), data.get("include_not_interested", False), data.get("limit", 20))


def load_command(path: Path) -> MediaCommand | ReadRequest:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise CommandValidationError("command JSON root must be an object")
    return parse_command(data)
