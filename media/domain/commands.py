from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from .types import TargetUpdate, WorkRef


@dataclass(frozen=True)
class RecordViewingFeedbackCommand:
    schema_version: int
    operation_id: str
    work_ref: WorkRef
    target_updates: tuple[TargetUpdate, ...]
    create_if_missing: bool = False


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
class RecommendContextRequest:
    schema_version: int
    target: str
    text: str | None
    only_unwatched: bool
    runtime_max: int | None
    include_not_interested: bool
    limit: int


MediaCommand: TypeAlias = RecordViewingFeedbackCommand | SetInterestCommand | AddWorkCommand
