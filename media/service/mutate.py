from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Mapping

from media.domain.changeset import MutationPlan
from media.domain.commands import EditViewingFeedbackCommand, RecordViewingFeedbackCommand, SetInterestCommand
from media.domain.errors import CommandValidationError
from media.domain.types import TargetEdit, TargetUpdate
from media.repository.yaml_repo import YamlRepository
from media.service.resolve import resolve_target_kind, resolve_work


def _at(now: datetime | None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _date(now: datetime | None) -> str:
    return (now or datetime.now(timezone.utc)).date().isoformat()


def apply_feedback_updates(repo: YamlRepository, document: Mapping[str, Any], updates: tuple[TargetUpdate, ...], *, now: datetime | None = None) -> tuple[dict[str, Any], bool, set[str]]:
    doc=copy.deepcopy(dict(document)); changed=False; touched_targets:set[str]=set()
    for update in updates:
        kind=resolve_target_kind(repo,update.target)
        if kind=="group" and update.viewing is not None: raise CommandValidationError("group targets cannot carry viewing state")
        container_key="viewer_signals" if kind=="viewer" else "group_signals"; signals=doc.setdefault(container_key,{})
        signal=copy.deepcopy(signals.get(update.target) or {}); previous={}; current={}; component_changed=False
        for key in ("viewing","rating","reaction","feedback"):
            value=getattr(update,key)
            if value is None: continue
            incoming=copy.deepcopy(dict(value))
            if key in signal: previous[key]=copy.deepcopy(signal[key])
            current[key]=incoming
            if signal.get(key)!=incoming: signal[key]=incoming; component_changed=True
        if component_changed:
            signal.setdefault("history",[]).append({"at":_at(now),"previous":previous,"current":current}); signals[update.target]=signal; changed=True; touched_targets.add(update.target)
    if changed: doc.setdefault("provenance",{})["updated_at"]=_date(now)
    return doc,changed,touched_targets


def _validate_target_edit(kind: str, edit: TargetEdit) -> None:
    set_keys=set(edit.set_values); clear_keys=set(edit.clear)
    if set_keys & clear_keys:
        raise CommandValidationError("feedback component cannot be both set and cleared")
    if edit.purge and (set_keys or clear_keys):
        raise CommandValidationError("purge cannot be combined with set or clear")
    if kind=="group" and ("viewing" in set_keys or "viewing" in clear_keys):
        raise CommandValidationError("group targets cannot carry viewing state")


def apply_feedback_edits(repo: YamlRepository, document: Mapping[str, Any], edits: tuple[TargetEdit, ...], *, now: datetime | None = None) -> tuple[dict[str, Any], bool, set[str]]:
    doc=copy.deepcopy(dict(document)); changed=False; touched_targets:set[str]=set()
    for edit in edits:
        kind=resolve_target_kind(repo,edit.target); _validate_target_edit(kind,edit)
        container_key="viewer_signals" if kind=="viewer" else "group_signals"; signals=doc.setdefault(container_key,{})
        existing=signals.get(edit.target)
        if edit.purge:
            if existing is not None:
                del signals[edit.target]; changed=True; touched_targets.add(edit.target)
            if not signals: doc.pop(container_key,None)
            continue
        signal=copy.deepcopy(existing or {}); previous={}; current={}; component_changed=False
        for key,value in edit.set_values.items():
            incoming=copy.deepcopy(dict(value))
            if key in signal: previous[key]=copy.deepcopy(signal[key])
            if signal.get(key)!=incoming:
                signal[key]=incoming; current[key]=incoming; component_changed=True
        for key in edit.clear:
            if key not in signal: continue
            previous[key]=copy.deepcopy(signal[key]); signal.pop(key,None); current[key]=None; component_changed=True
        if component_changed:
            signal.setdefault("history",[]).append({"at":_at(now),"previous":previous,"current":current}); signals[edit.target]=signal; changed=True; touched_targets.add(edit.target)
    if changed: doc.setdefault("provenance",{})["updated_at"]=_date(now)
    return doc,changed,touched_targets


def plan_record_viewing_feedback(repo: YamlRepository, command: RecordViewingFeedbackCommand, *, now: datetime | None = None) -> MutationPlan:
    record=resolve_work(repo,command.work_ref); doc,changed,touched_targets=apply_feedback_updates(repo,record.data,command.target_updates,now=now); path=str(record.path.relative_to(repo.media_root.parent)).replace("\\","/")
    return MutationPlan(command.operation_id,"record_viewing_feedback",(record.id,) if changed else (),{path:doc} if changed else {},tuple(sorted(f"viewer:{target}" for target in touched_targets)) if changed else ())


def plan_edit_viewing_feedback(repo: YamlRepository, command: EditViewingFeedbackCommand, *, now: datetime | None = None) -> MutationPlan:
    record=resolve_work(repo,command.work_ref); doc,changed,touched_targets=apply_feedback_edits(repo,record.data,command.target_edits,now=now); path=str(record.path.relative_to(repo.media_root.parent)).replace("\\","/")
    return MutationPlan(command.operation_id,"edit_viewing_feedback",(record.id,) if changed else (),{path:doc} if changed else {},tuple(sorted(f"viewer:{target}" for target in touched_targets)) if changed else ())


def plan_set_interest(repo: YamlRepository, command: SetInterestCommand, *, now: datetime | None = None) -> MutationPlan:
    resolve_target_kind(repo,command.target); record=resolve_work(repo,command.work_ref); doc=copy.deepcopy(dict(record.data)); interest={"state":command.state}
    if command.state in {"candidate","shortlist"} and command.priority is not None: interest["priority"]=command.priority
    states=doc.setdefault("target_states",{}); target_state=copy.deepcopy(states.get(command.target) or {}); changed=target_state.get("interest")!=interest
    if changed: target_state["interest"]=interest; states[command.target]=target_state; doc.setdefault("provenance",{})["updated_at"]=_date(now)
    path=str(record.path.relative_to(repo.media_root.parent)).replace("\\","/")
    return MutationPlan(command.operation_id,"set_interest",(record.id,) if changed else (),{path:doc} if changed else {},(f"interest:{command.target}",) if changed else ())
