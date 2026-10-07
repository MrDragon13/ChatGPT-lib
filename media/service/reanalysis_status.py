from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from media.domain.digests import material_evidence_projection
from media.domain.errors import UnknownTargetError
from media.repository.yaml_repo import YamlRepository
from media.tools.common import load_yaml


@dataclass(frozen=True)
class EvidenceCheckpoint:
    material_event_count: int
    material_event_prefix_digest: str


@dataclass(frozen=True)
class EvidenceSnapshot:
    checkpoint: EvidenceCheckpoint
    evidence_digest: str


@dataclass(frozen=True)
class ReanalysisStatus:
    target: str
    threshold: int
    outstanding_count: int
    due: bool
    checkpoint_valid: bool
    current_evidence_digest: str


@dataclass(frozen=True)
class _MaterialEvent:
    work_id: str
    history_index: int
    at: str
    event_id: str
    previous: Mapping[str, Any]
    current: Mapping[str, Any]

    def digest_value(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "history_index": self.history_index,
            "at": self.at,
            "event_id": self.event_id,
            "previous": copy.deepcopy(dict(self.previous)),
            "current": copy.deepcopy(dict(self.current)),
        }


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value)).hexdigest()


def _threshold(media_root: Path) -> int:
    path = Path(media_root) / "config" / "intelligence.yaml"
    document = load_yaml(path) if path.exists() else {}
    value = (document or {}).get("taste_reanalysis_threshold", 5)
    return int(value) if isinstance(value, int) and value > 0 else 5


def _material_events_from_documents(
    documents: list[Mapping[str, Any]],
    target: str,
) -> list[_MaterialEvent]:
    events: list[_MaterialEvent] = []
    for document in documents:
        work_id = document.get("id")
        if not isinstance(work_id, str):
            continue
        signal = ((document.get("viewer_signals") or {}).get(target) or {})
        for index, entry in enumerate(signal.get("history") or []):
            if not isinstance(entry, Mapping) or entry.get("material_evidence") is not True:
                continue
            event_id = entry.get("event_id")
            if not isinstance(event_id, str) or not event_id:
                continue
            events.append(
                _MaterialEvent(
                    work_id=work_id,
                    history_index=index,
                    at=str(entry.get("at") or ""),
                    event_id=event_id,
                    previous=copy.deepcopy(dict(entry.get("previous") or {})),
                    current=copy.deepcopy(dict(entry.get("current") or {})),
                )
            )
    events.sort(key=lambda item: (item.at, item.event_id, item.work_id, item.history_index))
    return events


def _material_events(media_root: Path, target: str) -> list[_MaterialEvent]:
    repo = YamlRepository(Path(media_root))
    documents = [record.data for record in repo.iter_works()]
    return _material_events_from_documents(documents, target)


def _prefix_digest(events: list[_MaterialEvent], count: int) -> str:
    return _digest([event.digest_value() for event in events[:count]])


def _current_material_state_from_documents(
    documents: list[Mapping[str, Any]],
    target: str,
) -> dict[str, dict[str, Any]]:
    state: dict[str, dict[str, Any]] = {}
    for document in documents:
        work_id = document.get("id")
        if not isinstance(work_id, str):
            continue
        signal = ((document.get("viewer_signals") or {}).get(target) or {})
        projected = dict(material_evidence_projection(signal))
        if projected:
            state[work_id] = projected
    return state


def _current_material_state(media_root: Path, target: str) -> dict[str, dict[str, Any]]:
    repo = YamlRepository(Path(media_root))
    documents = [record.data for record in repo.iter_works()]
    return _current_material_state_from_documents(documents, target)


def _state_digest(state: Mapping[str, Mapping[str, Any]]) -> str:
    return _digest(
        [
            {"work_id": work_id, "evidence": copy.deepcopy(dict(state[work_id]))}
            for work_id in sorted(state)
        ]
    )


def _undo_event(state: dict[str, dict[str, Any]], event: _MaterialEvent) -> None:
    signal = copy.deepcopy(state.get(event.work_id) or {})
    touched = set(event.previous) | set(event.current)
    for key in touched:
        projection_key = "feedback_signals" if key == "feedback" else key
        if key in event.previous:
            previous_value = event.previous[key]
            if key == "feedback":
                previous_projection = material_evidence_projection({"feedback": previous_value})
                if "feedback_signals" in previous_projection:
                    signal["feedback_signals"] = previous_projection["feedback_signals"]
                else:
                    signal.pop("feedback_signals", None)
            else:
                signal[projection_key] = copy.deepcopy(previous_value)
        else:
            signal.pop(projection_key, None)
    if signal:
        state[event.work_id] = signal
    else:
        state.pop(event.work_id, None)


def _state_at_checkpoint(
    media_root: Path,
    target: str,
    events: list[_MaterialEvent],
    count: int,
) -> dict[str, dict[str, Any]]:
    state = _current_material_state(media_root, target)
    for event in reversed(events[count:]):
        _undo_event(state, event)
    return state


def snapshot_evidence(media_root: Path, target: str) -> EvidenceSnapshot:
    media_root = Path(media_root)
    events = _material_events(media_root, target)
    state = _current_material_state(media_root, target)
    return EvidenceSnapshot(
        checkpoint=EvidenceCheckpoint(
            material_event_count=len(events),
            material_event_prefix_digest=_prefix_digest(events, len(events)),
        ),
        evidence_digest=_state_digest(state),
    )


def _stored_analysis(media_root: Path, target: str) -> Mapping[str, Any] | None:
    path = Path(media_root) / "preferences" / "inferred" / f"{target}.yaml"
    if not path.exists():
        return None
    document = load_yaml(path) or {}
    analysis = document.get("analysis") if isinstance(document, Mapping) else None
    return analysis if isinstance(analysis, Mapping) else None


def checkpoint_matches_current_evidence(
    media_root: Path,
    target: str,
    checkpoint: EvidenceCheckpoint,
    evidence_digest: str,
) -> bool:
    media_root = Path(media_root)
    events = _material_events(media_root, target)
    count = checkpoint.material_event_count
    if count < 0 or count > len(events):
        return False
    if _prefix_digest(events, count) != checkpoint.material_event_prefix_digest:
        return False
    reconstructed = _state_at_checkpoint(media_root, target, events, count)
    return _state_digest(reconstructed) == evidence_digest


def get_reanalysis_status_for_documents(
    media_root: Path,
    target: str,
    documents: list[Mapping[str, Any]],
) -> ReanalysisStatus:
    media_root = Path(media_root)
    threshold = _threshold(media_root)
    events = _material_events_from_documents(documents, target)
    current_state = _current_material_state_from_documents(documents, target)
    current_digest = _state_digest(current_state)
    analysis = _stored_analysis(media_root, target)

    if analysis is None:
        outstanding = len(events)
        return ReanalysisStatus(
            target=target,
            threshold=threshold,
            outstanding_count=outstanding,
            due=outstanding >= threshold,
            checkpoint_valid=True,
            current_evidence_digest=current_digest,
        )

    raw_checkpoint = analysis.get("evidence_checkpoint") or {}
    try:
        checkpoint = EvidenceCheckpoint(
            material_event_count=int(raw_checkpoint["material_event_count"]),
            material_event_prefix_digest=str(raw_checkpoint["material_event_prefix_digest"]),
        )
        stored_evidence_digest = str(analysis["evidence_digest"])
    except (KeyError, TypeError, ValueError):
        return ReanalysisStatus(target, threshold, len(events), True, False, current_digest)

    count = checkpoint.material_event_count
    valid = 0 <= count <= len(events)
    if valid:
        valid = _prefix_digest(events, count) == checkpoint.material_event_prefix_digest
    if valid:
        reconstructed = copy.deepcopy(current_state)
        for event in reversed(events[count:]):
            _undo_event(reconstructed, event)
        valid = _state_digest(reconstructed) == stored_evidence_digest

    outstanding = max(0, len(events) - count) if valid else len(events)
    return ReanalysisStatus(
        target=target,
        threshold=threshold,
        outstanding_count=outstanding,
        due=(not valid) or outstanding >= threshold,
        checkpoint_valid=valid,
        current_evidence_digest=current_digest,
    )


def get_reanalysis_status(media_root: Path, target: str) -> ReanalysisStatus:
    media_root = Path(media_root)
    repo = YamlRepository(media_root)
    documents = [record.data for record in repo.iter_works()]
    return get_reanalysis_status_for_documents(media_root, target, documents)


def _status_payload(status: ReanalysisStatus) -> dict[str, Any]:
    return {
        "target": status.target,
        "threshold": status.threshold,
        "outstanding_count": status.outstanding_count,
        "due": status.due,
        "checkpoint_valid": status.checkpoint_valid,
        "current_evidence_digest": status.current_evidence_digest,
    }


def _cached_status_payload(media_root: Path, target: str) -> dict[str, Any] | None:
    path = Path(media_root) / "generated" / "profiles" / f"{target}.yaml"
    if not path.exists():
        return None
    document = load_yaml(path) or {}
    status = document.get("reanalysis") if isinstance(document, Mapping) else None
    if not isinstance(status, Mapping) or status.get("target") != target:
        return None
    return copy.deepcopy(dict(status))


def _viewer_status_payload(media_root: Path, target: str) -> dict[str, Any]:
    cached = _cached_status_payload(media_root, target)
    if cached is not None:
        return cached
    return _status_payload(get_reanalysis_status(media_root, target))


def build_reanalysis_context(media_root: Path, target: str) -> dict[str, Any]:
    media_root = Path(media_root)
    repo = YamlRepository(media_root)
    viewers, groups = repo.configured_targets()
    if target in viewers:
        return _viewer_status_payload(media_root, target)
    if target in groups:
        members = {
            member: _viewer_status_payload(media_root, member)
            for member in groups[target]
        }
        return {
            "target": target,
            "due": any(status["due"] for status in members.values()),
            "members": members,
        }
    raise UnknownTargetError(f"unknown target: {target}")
