from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from media.domain.changeset import MutationPlan
from media.repository.yaml_repo import YamlRepository


@dataclass(frozen=True)
class DirtyPlan:
    rebuild_index: bool
    rebuild_profile_targets: tuple[str, ...]


def _profile_targets_for(repo: YamlRepository, target: str) -> set[str]:
    viewers, groups = repo.configured_targets()
    result = {target}
    if target in viewers:
        for group_id, members in groups.items():
            if target in members:
                result.add(group_id)
    return result


def _all_profile_targets(repo: YamlRepository) -> set[str]:
    viewers, groups = repo.configured_targets()
    return set(viewers) | set(groups)


def _has_numeric_rating(signal: Any) -> bool:
    if not isinstance(signal, Mapping):
        return False
    rating = signal.get("rating")
    if not isinstance(rating, Mapping):
        return False
    score = rating.get("score")
    return isinstance(score, (int, float)) and not isinstance(score, bool)


def _semantic_rating_targets(repo: YamlRepository, plan: MutationPlan) -> set[str]:
    result: set[str] = set()
    work_ids = {
        entity_id
        for entity_id in plan.changed_entities
        if isinstance(entity_id, str) and not entity_id.startswith(("preferences:", "interaction:", "similarity:"))
    }
    for work_id in work_ids:
        record = repo.get_work(work_id)
        if record is None:
            continue
        document = record.data
        for target, signal in (document.get("viewer_signals") or {}).items():
            if _has_numeric_rating(signal):
                result.update(_profile_targets_for(repo, target))
        for target, signal in (document.get("group_signals") or {}).items():
            if _has_numeric_rating(signal):
                result.add(target)
    return result


def derive_dirty_plan(repo: YamlRepository, plan: MutationPlan) -> DirtyPlan:
    rebuild_index = False
    profile_targets: set[str] = set()

    for domain in set(plan.changed_domains):
        if domain == "work.created":
            rebuild_index = True
            profile_targets.update(_all_profile_targets(repo))
        elif domain in {"work.identity", "work.metadata"}:
            rebuild_index = True
        elif domain == "work.semantics":
            rebuild_index = True
            profile_targets.update(_semantic_rating_targets(repo, plan))
        elif domain.startswith("viewer:"):
            rebuild_index = True
            profile_targets.update(_profile_targets_for(repo, domain.split(":", 1)[1]))
        elif domain.startswith("interest:"):
            rebuild_index = True
        elif domain.startswith("preferences.inferred:"):
            profile_targets.add(domain.split(":", 1)[1])
        elif domain.startswith("interaction:"):
            profile_targets.add(domain.split(":", 1)[1])
        elif domain.startswith("similarity:"):
            continue

    return DirtyPlan(
        rebuild_index=rebuild_index,
        rebuild_profile_targets=tuple(sorted(profile_targets)),
    )
