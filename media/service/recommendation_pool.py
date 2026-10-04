from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from media.domain.errors import UnknownTargetError
from media.repository.index_repo import IndexRepository
from media.repository.yaml_repo import YamlRepository


def filter_eligible_candidate_rows(
    rows: Iterable[dict[str, Any]],
    *,
    target: str,
    viewers: set[str],
    groups: Mapping[str, list[str]],
    only_unwatched: bool,
    include_not_interested: bool,
    runtime_max: int | None,
) -> list[dict[str, Any]]:
    if target not in viewers and target not in groups:
        raise UnknownTargetError(f"unknown target: {target}")

    members = groups.get(target, [])
    result: list[dict[str, Any]] = []
    for row in rows:
        runtime = row.get("runtime_min")
        if runtime_max is not None and runtime is not None and runtime > runtime_max:
            continue

        interest = (row.get("interest") or {}).get(target) or {}
        if not include_not_interested and interest.get("state") == "not_interested":
            continue

        viewer = row.get("viewer") or {}
        if only_unwatched:
            if target in viewers:
                if (viewer.get(target) or {}).get("viewing") == "watched":
                    continue
            elif members and all(
                (viewer.get(member) or {}).get("viewing") == "watched"
                for member in members
            ):
                continue

        result.append(row)

    return result


def eligible_local_candidates(
    media_root: Path,
    *,
    target: str,
    only_unwatched: bool,
    include_not_interested: bool,
    runtime_max: int | None,
) -> list[dict[str, Any]]:
    media_root = Path(media_root)
    repo = YamlRepository(media_root)
    viewers, groups = repo.configured_targets()
    rows = IndexRepository(media_root / "generated" / "index.jsonl").rows()
    return filter_eligible_candidate_rows(
        rows,
        target=target,
        viewers=viewers,
        groups=groups,
        only_unwatched=only_unwatched,
        include_not_interested=include_not_interested,
        runtime_max=runtime_max,
    )
