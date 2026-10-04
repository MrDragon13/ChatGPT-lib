from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from media.domain.errors import PathPolicyError

_POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "operation_path_policy.json"


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


def _matches(path: str, pattern: str) -> bool:
    value=PurePosixPath(path); expected=PurePosixPath(pattern)
    if "*" not in pattern: return value == expected
    return value.match(pattern)


def verify_changed_paths(operation: str, paths: Iterable[str]) -> None:
    allowed=allowed_paths_for_operation(operation)
    if not allowed: raise PathPolicyError(f"no write policy for operation: {operation}")
    rejected=[path for path in paths if not any(_matches(path,pattern) for pattern in allowed)]
    if rejected: raise PathPolicyError(f"operation {operation} may not modify: {', '.join(sorted(rejected))}")
