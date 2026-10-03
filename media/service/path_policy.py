from __future__ import annotations

from pathlib import PurePosixPath
from typing import Iterable

from media.domain.errors import PathPolicyError

_COMMON = (
    "media/data/works/*.yaml",
    "media/generated/index.jsonl",
    "media/generated/profiles/*.yaml",
    ".media/operations/*.json",
)
_INFERRED = (
    "media/preferences/inferred/*.yaml",
    "media/generated/index.jsonl",
    "media/generated/profiles/*.yaml",
    ".media/operations/*.json",
)
_INTERACTIONS = (
    "media/data/interactions/*.jsonl",
    "media/generated/profiles/*.yaml",
    ".media/operations/*.json",
)
_SIMILARITY = (
    "media/data/relations/similarity/*.yaml",
    ".media/operations/*.json",
)
_ALLOWED = {
    "record_viewing_feedback": _COMMON,
    "edit_viewing_feedback": _COMMON,
    "set_interest": _COMMON,
    "add_work": _COMMON,
    "refresh_metadata": _COMMON,
    "set_semantic_fingerprint": _COMMON,
    "set_inferred_preferences": _INFERRED,
    "record_recommendation_interaction": _INTERACTIONS,
    "set_work_similarity": _SIMILARITY,
    "remove_work_similarity": _SIMILARITY,
}


def allowed_paths_for_operation(operation: str) -> tuple[str, ...]:
    return _ALLOWED.get(operation, ())


def _matches(path: str, pattern: str) -> bool:
    value=PurePosixPath(path); expected=PurePosixPath(pattern)
    if "*" not in pattern: return value == expected
    return value.match(pattern)


def verify_changed_paths(operation: str, paths: Iterable[str]) -> None:
    allowed=allowed_paths_for_operation(operation)
    if not allowed: raise PathPolicyError(f"no write policy for operation: {operation}")
    rejected=[path for path in paths if not any(_matches(path,pattern) for pattern in allowed)]
    if rejected: raise PathPolicyError(f"operation {operation} may not modify: {', '.join(sorted(rejected))}")
