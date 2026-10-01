from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID

from media.domain.commands import (
    AddWorkCommand,
    MediaCommand,
    RecommendContextRequest,
    RecordViewingFeedbackCommand,
    SetInterestCommand,
)
from media.domain.errors import CommandValidationError
from media.domain.types import TargetUpdate, WorkRef
from media.tools.schema_utils import validate_against_schema

_SCHEMA_BY_OPERATION = {
    "record_viewing_feedback": "record_viewing_feedback.schema.json",
    "set_interest": "set_interest.schema.json",
    "add_work": "add_work.schema.json",
    "recommend_context": "recommend_context.schema.json",
}


def _work_ref(data: Mapping[str, Any]) -> WorkRef:
    return WorkRef(
        id=data.get("id"),
        title=data.get("title"),
        year=data.get("year"),
        tmdb_media_type=data.get("tmdb_media_type"),
        tmdb_id=data.get("tmdb_id"),
        imdb_id=data.get("imdb_id"),
    )


def _validate_uuid(value: str) -> None:
    try:
        parsed = UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise CommandValidationError("operation_id must be a canonical UUID") from exc
    if str(parsed) != value:
        raise CommandValidationError("operation_id must be canonical lowercase UUID text")


def parse_command(data: Mapping[str, Any], schema_dir: Path | None = None) -> MediaCommand | RecommendContextRequest:
    schema_dir = schema_dir or Path(__file__).with_name("schemas")
    operation = data.get("operation")
    schema_name = _SCHEMA_BY_OPERATION.get(operation)
    if schema_name is None:
        raise CommandValidationError(f"unknown operation: {operation}")
    errors = validate_against_schema(dict(data), schema_name, schema_dir)
    if errors:
        raise CommandValidationError("; ".join(errors))
    if operation != "recommend_context":
        _validate_uuid(str(data["operation_id"]))
    if operation == "record_viewing_feedback":
        updates = tuple(TargetUpdate(target=item["target"], viewing=item.get("viewing"), rating=item.get("rating"), reaction=item.get("reaction"), feedback=item.get("feedback")) for item in data["target_updates"])
        return RecordViewingFeedbackCommand(data["schema_version"], data["operation_id"], _work_ref(data["work_ref"]), updates, data.get("create_if_missing", False))
    if operation == "set_interest":
        return SetInterestCommand(data["schema_version"], data["operation_id"], _work_ref(data["work_ref"]), data["target"], data["state"], data.get("priority"))
    if operation == "add_work":
        return AddWorkCommand(data["schema_version"], data["operation_id"], _work_ref(data["work_ref"]))
    return RecommendContextRequest(data["schema_version"], data["target"], data.get("text"), data.get("only_unwatched", False), data.get("runtime_max"), data.get("include_not_interested", False), data.get("limit", 20))


def load_command(path: Path) -> MediaCommand | RecommendContextRequest:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise CommandValidationError("command JSON root must be an object")
    return parse_command(data)
