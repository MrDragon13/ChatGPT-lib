from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from media.domain.changeset import MutationPlan
from media.domain.commands import RecordRecommendationInteractionCommand
from media.domain.errors import CommandValidationError, NotFoundError
from media.repository.yaml_repo import YamlRepository
from media.service.resolve import resolve_target_kind, resolve_work


def _timestamp(command_at: str | None, now: datetime | None) -> datetime:
    if command_at:
        try:
            value=datetime.fromisoformat(command_at.replace("Z","+00:00"))
        except ValueError as exc:
            raise CommandValidationError(f"invalid interaction timestamp: {command_at}") from exc
    else:
        value=now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value=value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _external_ref(command: RecordRecommendationInteractionCommand) -> dict[str, Any]:
    ref=command.work_ref
    result: dict[str,Any]={}
    if ref.title: result["title"]=ref.title
    if ref.year is not None: result["year"]=ref.year
    if ref.tmdb_media_type: result["tmdb_media_type"]=ref.tmdb_media_type
    if ref.tmdb_id is not None: result["tmdb_id"]=ref.tmdb_id
    if ref.imdb_id: result["imdb_id"]=ref.imdb_id
    return result


def plan_record_recommendation_interaction(
    repo: YamlRepository,
    command: RecordRecommendationInteractionCommand,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    resolve_target_kind(repo, command.target)
    timestamp=_timestamp(command.at,now)
    event: dict[str,Any]={
        "schema_version":4,
        "id":command.operation_id,
        "entity_type":"interaction",
        "at":timestamp.isoformat().replace("+00:00","Z"),
        "target":command.target,
        "type":command.event,
        "session_id":command.session_id,
    }
    if command.note is not None: event["reason"]=command.note

    if command.work_ref.id:
        record=resolve_work(repo,command.work_ref)
        event["work_id"]=record.id
    else:
        try:
            record=resolve_work(repo,command.work_ref)
        except NotFoundError:
            external=_external_ref(command)
            if not external:
                raise CommandValidationError("external recommendation interaction requires stable work identity")
            event["work_ref"]=external
        else:
            event["work_id"]=record.id

    month=f"{timestamp.year:04d}-{timestamp.month:02d}"
    rel=f"media/data/interactions/{month}.jsonl"
    return MutationPlan(
        command.operation_id,
        "record_recommendation_interaction",
        (f"interaction:{command.operation_id}",),
        {},
        False,
        (command.target,),
        {"event_type":command.event,"session_id":command.session_id},
        {rel:(event,)},
    )
