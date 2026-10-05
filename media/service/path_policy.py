from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from media.domain.errors import PathPolicyError

_POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "operation_path_policy.json"
_UNSUPPORTED_PATTERN_CHARS = "?[]{}"


def _validate_repository_path(value: str, *, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise PathPolicyError(f"invalid {label}: empty path")
    if value.startswith("/") or "\\" in value or "//" in value:
        raise PathPolicyError(f"invalid {label}: {value}")
    segments=value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise PathPolicyError(f"invalid {label}: {value}")


def _validate_pattern(pattern: str) -> None:
    _validate_repository_path(pattern,label="policy pattern")
    if any(char in pattern for char in _UNSUPPORTED_PATTERN_CHARS):
        raise PathPolicyError(f"unsupported policy pattern syntax: {pattern}")
    if pattern.count("*") > 1:
        raise PathPolicyError(f"unsupported policy pattern syntax: {pattern}")


def matches_policy_path(path: str, pattern: str) -> bool:
    """Match the Stage A declarative path grammar, anchored to the whole path.

    A pattern is either exact or contains one `*`. The wildcard may match
    zero or more characters inside one path segment, but never `/`.
    """

    _validate_repository_path(path,label="repository path")
    _validate_pattern(pattern)
    if "*" not in pattern:
        return path == pattern

    prefix,suffix=pattern.split("*",1)
    if not path.startswith(prefix) or not path.endswith(suffix):
        return False
    if len(path) < len(prefix)+len(suffix):
        return False
    middle=path[len(prefix): len(path)-len(suffix) if suffix else None]
    return "/" not in middle


def _load_policy() -> dict[str, dict[str, Any]]:
    try:
        document = json.loads(_POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PathPolicyError(f"unable to read operation path policy: {_POLICY_PATH}") from exc

    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise PathPolicyError("invalid operation path policy schema_version")
    operations = document.get("operations")
    if not isinstance(operations, dict) or not operations:
        raise PathPolicyError("invalid operation path policy operations")

    normalized: dict[str, dict[str, Any]] = {}
    for operation, entry in operations.items():
        if not isinstance(operation, str) or not operation or not isinstance(entry, dict):
            raise PathPolicyError("invalid operation path policy entry")
        auto_merge = entry.get("auto_merge")
        allowed_paths = entry.get("allowed_paths")
        if not isinstance(auto_merge, bool):
            raise PathPolicyError(f"invalid auto_merge policy for operation: {operation}")
        if (
            not isinstance(allowed_paths, list)
            or not allowed_paths
            or any(not isinstance(path, str) or not path for path in allowed_paths)
        ):
            raise PathPolicyError(f"invalid allowed_paths policy for operation: {operation}")
        for pattern in allowed_paths:
            _validate_pattern(pattern)
        normalized[operation] = {
            "auto_merge": auto_merge,
            "allowed_paths": tuple(allowed_paths),
        }
    return normalized


def allowed_paths_for_operation(operation: str) -> tuple[str, ...]:
    entry = _load_policy().get(operation)
    if entry is None:
        return ()
    return entry["allowed_paths"]


def verify_changed_paths(operation: str, paths: Iterable[str]) -> None:
    allowed=allowed_paths_for_operation(operation)
    if not allowed: raise PathPolicyError(f"no write policy for operation: {operation}")
    rejected=[path for path in paths if not any(matches_policy_path(path,pattern) for pattern in allowed)]
    if rejected: raise PathPolicyError(f"operation {operation} may not modify: {', '.join(sorted(rejected))}")


def verify_operation_specific_paths(
    operation: str,
    paths: Iterable[str],
    details: Mapping[str, Any] | None = None,
) -> None:
    """Enforce write-shape constraints that the simple declarative wildcard grammar cannot express."""
    if operation != "complete_reassessment_item":
        return

    normalized = tuple(paths)
    work_paths = tuple(path for path in normalized if path.startswith("media/data/works/") and path.endswith(".yaml"))
    if len(work_paths) > 1:
        raise PathPolicyError("complete_reassessment_item may modify at most one canonical work")
    if not work_paths:
        return

    work_id = (details or {}).get("work_id")
    if not isinstance(work_id, str) or not work_id:
        raise PathPolicyError("complete_reassessment_item work-file mutation requires planner work_id")
    expected = f"media/data/works/{work_id}.yaml"
    if work_paths[0] != expected:
        raise PathPolicyError(
            f"complete_reassessment_item may modify only the reserved work {expected}, got {work_paths[0]}"
        )
