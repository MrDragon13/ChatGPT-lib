from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping


@dataclass(frozen=True)
class MutationPlan:
    operation_id: str
    operation: str
    changed_entities: tuple[str, ...]
    documents: Mapping[str, Mapping[str, Any]]
    rebuild_index: bool
    rebuild_profile_targets: tuple[str, ...]
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationResult:
    status: Literal["planned", "applied", "no_change", "already_applied"]
    operation_id: str
    operation: str
    changed_entities: tuple[str, ...]
    changed_files: tuple[str, ...]
    details: Mapping[str, Any] = field(default_factory=dict)
