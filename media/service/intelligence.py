from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from media.domain.changeset import MutationPlan
from media.domain.commands import SetSemanticFingerprintCommand
from media.domain.errors import CommandValidationError
from media.repository.yaml_repo import YamlRepository
from media.service.mutate import profile_targets_for
from media.service.resolve import resolve_work
from media.tools.common import load_yaml


def _date(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).date().isoformat()


def _vocabulary(repo: YamlRepository) -> dict[str, dict[str, Any]]:
    doc = load_yaml(repo.media_root / "vocabulary.yaml") or {}
    return dict(doc.get("terms") or {})


def _has_numeric_rating(signal: Any) -> bool:
    if not isinstance(signal, dict):
        return False
    rating = signal.get("rating")
    score = rating.get("score") if isinstance(rating, dict) else rating
    return isinstance(score, (int, float)) and not isinstance(score, bool)


def _rating_targets(document: dict[str, Any]) -> set[str]:
    targets: set[str] = set()
    for container_key in ("viewer_signals", "group_signals"):
        signals = document.get(container_key) or {}
        if not isinstance(signals, dict):
            continue
        for target, signal in signals.items():
            if isinstance(target, str) and _has_numeric_rating(signal):
                targets.add(target)
    return targets


def plan_set_semantic_fingerprint(
    repo: YamlRepository,
    command: SetSemanticFingerprintCommand,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    record = resolve_work(repo, command.work_ref)
    vocab = _vocabulary(repo)
    traits = []
    for item in command.traits:
        term = item["term"]
        meta = vocab.get(term)
        if meta is None:
            raise CommandValidationError(f"unknown vocabulary term: {term}")
        if meta.get("kind") == "reaction":
            raise CommandValidationError(f"reaction term cannot be a film trait: {term}")
        traits.append(copy.deepcopy(dict(item)))

    doc = copy.deepcopy(dict(record.data))
    metadata = doc.setdefault("metadata", {})
    semantic = metadata.setdefault("semantic", {})
    changed = semantic.get("traits") != traits
    if changed:
        semantic["traits"] = traits
        doc.setdefault("provenance", {})["updated_at"] = _date(now)

    profile_targets = profile_targets_for(repo, _rating_targets(doc)) if changed else ()
    path = str(record.path.relative_to(repo.media_root.parent)).replace("\\", "/")
    return MutationPlan(
        command.operation_id,
        "set_semantic_fingerprint",
        (record.id,) if changed else (),
        {path: doc} if changed else {},
        changed,
        profile_targets,
        details={"work_id": record.id},
    )
