from __future__ import annotations

from fnmatch import fnmatch
from typing import Iterable

from media.domain.errors import PathPolicyError

_COMMON = ("media/data/works/*.yaml", "media/generated/index.jsonl", "media/generated/profiles/*.yaml", ".media/operations/*.json")
_ALLOWED = {"record_viewing_feedback": _COMMON, "set_interest": _COMMON, "add_work": _COMMON}


def allowed_paths_for_operation(operation: str) -> tuple[str, ...]:
    return _ALLOWED.get(operation, ())


def verify_changed_paths(operation: str, paths: Iterable[str]) -> None:
    patterns = allowed_paths_for_operation(operation)
    if not patterns:
        raise PathPolicyError(f"no write policy for operation: {operation}")
    rejected = [path for path in paths if not any(fnmatch(path, pattern) for pattern in patterns)]
    if rejected:
        raise PathPolicyError(f"operation {operation} may not modify: {', '.join(sorted(rejected))}")
