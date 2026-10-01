from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Mapping

from media.domain.changeset import MutationPlan
from media.domain.commands import RecordViewingFeedbackCommand, SetInterestCommand
from media.domain.errors import CommandValidationError
from media.domain.types import TargetUpdate
from media.repository.yaml_repo import YamlRepository
from media.service.resolve import resolve_target_kind, resolve_work


def _at(now: datetime | None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _date(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).date().isoformat()


def profile_targets_for(repo: YamlRepository, targets: set[str]) -> tuple[str, ...]:
    viewers, groups = repo.configured_targets()
    result = set(targets)
    for target in list(targets):
        if target in viewers:
            for group_id, members in groups.items():
                if target in members:
                    result.add(group_id)
    return tuple(sorted(result))


def apply_feedback_updates(
    repo: YamlRepository,
    document: Mapping[str, Any],
    updates: tuple[TargetUpdate, ...],
    *,
    now: datetime | None = None,
) -> tuple[dict[str, Any], bool, set[str]]:
    doc = copy.deepcopy(dict(document))
    changed = False
    touched_targets: set[str] = set()
    for update in updates:
        kind = resolve_target_kind(repo, update.target)
        if kind == "group" and update.viewing is not None:
            raise CommandValidationError("group targets cannot carry viewing state")
        container_key = "viewer_signals" if kind == "viewer" else "group_signals"
        signals = doc.setdefault(container_key, {})
        signal = copy.deepcopy(signals.get(update.target) or {})
        previous: dict[str, Any] = {}
        current: dict[str, Any] = {}
        component_changed = False
        for key in ("viewing", "rating", "reaction", "feedback"):
            value = getattr(update, key)
            if value is None:
                continue
            incoming = copy.deepcopy(dict(value))
            if key in signal:
                previous[key] = copy.deepcopy(signal[key])
            current[key] = incoming
            if signal.get(key) != incoming:
                signal[key] = incoming
                component_changed = True
        if component_changed:
            signal.setdefault("history", []).append({"at": _at(now), "previous": previous, "current": current})
            signals[update.target] = signal
            changed = True
            touched_targets.add(update.target)
    if changed:
        doc.setdefault("provenance", {})["updated_at"] = _date(now)
    return doc, changed, touched_targets


def plan_record_viewing_feedback(
    repo: YamlRepository,
    command: RecordViewingFeedbackCommand,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    record = resolve_work(repo, command.work_ref)
    doc, changed, touched_targets = apply_feedback_updates(repo, record.data, command.target_updates, now=now)
    path = str(record.path.relative_to(repo.media_root.parent)).replace("\\", "/")
    return MutationPlan(
        command.operation_id,
        "record_viewing_feedback",
        (record.id,) if changed else (),
        {path: doc} if changed else {},
        changed,
        profile_targets_for(repo, touched_targets),
    )


def plan_set_interest(repo: YamlRepository, command: SetInterestCommand, *, now: datetime | None = None) -> MutationPlan:
    resolve_target_kind(repo, command.target)
    record = resolve_work(repo, command.work_ref)
    doc = copy.deepcopy(dict(record.data))
    interest = {"state": command.state}
    if command.state in {"candidate", "shortlist"} and command.priority is not None:
        interest["priority"] = command.priority
    states = doc.setdefault("target_states", {})
    target_state = copy.deepcopy(states.get(command.target) or {})
    changed = target_state.get("interest") != interest
    if changed:
        target_state["interest"] = interest
        states[command.target] = target_state
        doc.setdefault("provenance", {})["updated_at"] = _date(now)
    path = str(record.path.relative_to(repo.media_root.parent)).replace("\\", "/")
    return MutationPlan(
        command.operation_id,
        "set_interest",
        (record.id,) if changed else (),
        {path: doc} if changed else {},
        changed,
        profile_targets_for(repo, {command.target}) if changed else (),
    )
