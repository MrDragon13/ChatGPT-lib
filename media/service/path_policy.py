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
_ALLOWED = {
    "record_viewing_feedback": _COMMON,
    "set_interest": _COMMON,
    "add_work": _COMMON,
    "refresh_metadata": _COMMON,
}


def allowed_paths_for_operation(operation: str) -> tuple[str, ...]:
    return _ALLOWED.get(operation, ())


def _is_allowed_path(path: str) -> bool:
    value = PurePosixPath(path)
    if value.parent == PurePosixPath("media/data/works") and value.suffix == ".yaml":
        return True
    if value == PurePosixPath("media/generated/index.jsonl"):
        return True
    if value.parent == PurePosixPath("media/generated/profiles") and value.suffix == ".yaml":
        return True
    if value.parent == PurePosixPath(".media/operations") and value.suffix == ".json":
        return True
    return False


def verify_changed_paths(operation: str, paths: Iterable[str]) -> None:
    if not allowed_paths_for_operation(operation):
        raise PathPolicyError(f"no write policy for operation: {operation}")
    rejected = [path for path in paths if not _is_allowed_path(path)]
    if rejected:
        raise PathPolicyError(f"operation {operation} may not modify: {', '.join(sorted(rejected))}")
