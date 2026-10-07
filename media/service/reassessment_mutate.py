from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from media.domain.changeset import MutationPlan
from media.domain.commands import (
    CloseReassessmentSessionCommand,
    CompleteReassessmentItemCommand,
    RecordReassessmentModernizationCommand,
    ReserveReassessmentSessionCommand,
)
from media.domain.errors import CommandValidationError, NotFoundError
from media.domain.types import TargetEdit
from media.repository.yaml_repo import YamlRepository
from media.service.mutate import apply_feedback_edits, profile_targets_for
from media.service.reassessment import (
    LEDGER_REL_PATH,
    PILOT_ID,
    feedback_state_digest,
    file_sha256,
    ledger_bytes,
    ledger_digest_bytes,
)
from media.tools.audit_intelligence import collect_intelligence_audit


def _at(now: datetime | None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _ledger_path(repo: YamlRepository) -> Path:
    return repo.media_root.parent / LEDGER_REL_PATH


def _load_ledger(
    repo: YamlRepository,
    *,
    pilot_id: str,
    expected_digest: str,
) -> tuple[Path, dict[str, Any], str]:
    path = _ledger_path(repo)
    if not path.exists():
        raise NotFoundError("reassessment pilot ledger is not active")
    raw = path.read_bytes()
    actual_digest = ledger_digest_bytes(raw)
    if actual_digest != expected_digest:
        raise CommandValidationError(
            f"reassessment ledger digest mismatch: expected {expected_digest}, current {actual_digest}"
        )
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CommandValidationError("reassessment ledger is not valid UTF-8 JSON") from exc
    if not isinstance(document, dict):
        raise CommandValidationError("reassessment ledger root must be an object")
    if pilot_id != PILOT_ID or document.get("pilot_id") != pilot_id:
        raise CommandValidationError("reassessment pilot id does not match active ledger")
    if document.get("target") != "primary":
        raise CommandValidationError("reassessment pilot target must be primary")
    return path, copy.deepcopy(document), actual_digest


def _find_session(document: Mapping[str, Any], session_id: str) -> tuple[int, Mapping[str, Any]]:
    matches = [
        (index, session)
        for index, session in enumerate(document.get("sessions") or [])
        if isinstance(session, Mapping) and session.get("session_id") == session_id
    ]
    if len(matches) != 1:
        raise CommandValidationError(f"expected exactly one reassessment session {session_id}")
    return matches[0]


def _primary_signal(record: Any) -> Mapping[str, Any]:
    signals = record.data.get("viewer_signals") or {}
    signal = signals.get("primary") or {}
    return signal if isinstance(signal, Mapping) else {}


def _work_rel_path(repo: YamlRepository, record: Any) -> str:
    return str(record.path.relative_to(repo.media_root.parent)).replace("\\", "/")


def _ordered_ids_with_status(document: Mapping[str, Any], status: str) -> list[str]:
    frozen = document.get("frozen_cohort") or {}
    lifecycle = document.get("items") or {}
    return [
        work_id
        for work_id in frozen.get("work_ids") or []
        if isinstance(work_id, str)
        and isinstance(lifecycle.get(work_id), Mapping)
        and lifecycle[work_id].get("status") == status
    ]


def _assert_next_reservation_batch(document: Mapping[str, Any], work_ids: tuple[str, ...]) -> str:
    lifecycle = document.get("items") or {}
    requested_states = {
        work_id: (lifecycle.get(work_id) or {}).get("status")
        if isinstance(lifecycle.get(work_id), Mapping)
        else None
        for work_id in work_ids
    }
    for work_id, status in requested_states.items():
        if status in {"reviewed", "in_progress"}:
            raise CommandValidationError(
                f"cannot reserve reassessment item {work_id} with status {status}"
            )
        if status not in {"pending", "deferred"}:
            raise CommandValidationError(
                f"cannot reserve reassessment item {work_id} with unknown lifecycle status {status}"
            )

    pending = _ordered_ids_with_status(document, "pending")
    if pending:
        phase = "pending"
        eligible = pending
    else:
        phase = "deferred"
        eligible = _ordered_ids_with_status(document, "deferred")
    if not eligible:
        raise CommandValidationError("no reassessment items are available for reservation")
    expected = tuple(eligible[: len(work_ids)])
    if tuple(work_ids) != expected:
        if phase == "pending" and any(status == "deferred" for status in requested_states.values()):
            raise CommandValidationError("cannot reserve deferred items while the main pending pass remains")
        raise CommandValidationError(
            f"reassessment reservation must use the next frozen-order {phase} batch: {expected}"
        )
    return phase


def _validate_fresh_explicit_edit(feedback_edit: Mapping[str, Any]) -> None:
    set_values = feedback_edit.get("set") or {}
    rating = set_values.get("rating")
    if isinstance(rating, Mapping) and rating.get("score") is not None and rating.get("source") != "explicit":
        raise CommandValidationError("reassessment rating evidence must use source=explicit")
    reaction = set_values.get("reaction")
    if isinstance(reaction, Mapping) and reaction.get("source") != "explicit":
        raise CommandValidationError("reassessment reaction evidence must use source=explicit")
    feedback = set_values.get("feedback")
    if isinstance(feedback, Mapping):
        for signal in feedback.get("signals") or []:
            if isinstance(signal, Mapping) and signal.get("source") != "explicit":
                raise CommandValidationError("reassessment feedback signals must use source=explicit")


def _current_evidence_is_explicit(signal: Mapping[str, Any]) -> bool:
    rating = signal.get("rating")
    if isinstance(rating, Mapping) and rating.get("score") is not None and rating.get("source") != "explicit":
        return False
    reaction = signal.get("reaction")
    if isinstance(reaction, Mapping) and reaction.get("source") != "explicit":
        return False
    feedback = signal.get("feedback")
    if isinstance(feedback, Mapping):
        for item in feedback.get("signals") or []:
            if isinstance(item, Mapping) and item.get("source") != "explicit":
                return False
    return True


def _reviewed_total(document: Mapping[str, Any]) -> int:
    return sum(
        1
        for item in (document.get("items") or {}).values()
        if isinstance(item, Mapping) and item.get("status") == "reviewed"
    )


def _deferred_total(document: Mapping[str, Any]) -> int:
    return sum(
        1
        for item in (document.get("items") or {}).values()
        if isinstance(item, Mapping) and item.get("status") == "deferred"
    )


def _deferred_phase_started(document: Mapping[str, Any]) -> bool:
    return any(
        isinstance(session, Mapping) and session.get("phase") == "deferred"
        for session in document.get("sessions") or []
    )


def _scheduled_reanalysis_due(document: Mapping[str, Any]) -> bool:
    reviewed_total = _reviewed_total(document)
    state = document.get("scheduled_reanalysis") or {}
    last = state.get("last_completed") if isinstance(state, Mapping) else None
    last_count = last.get("reviewed_count", 0) if isinstance(last, Mapping) else 0
    if reviewed_total - int(last_count) >= 15:
        return True
    main_pass_complete = not _ordered_ids_with_status(document, "pending")
    return (
        main_pass_complete
        and not _deferred_phase_started(document)
        and reviewed_total > int(last_count)
    )


def _pilot_completion_ready(document: Mapping[str, Any]) -> bool:
    lifecycle = document.get("items") or {}
    if any(
        isinstance(item, Mapping) and item.get("status") in {"pending", "in_progress"}
        for item in lifecycle.values()
    ):
        return False

    deferred = {
        work_id: item
        for work_id, item in lifecycle.items()
        if isinstance(item, Mapping) and item.get("status") == "deferred"
    }
    if not deferred:
        return True

    session_by_id = {
        session.get("session_id"): session
        for session in document.get("sessions") or []
        if isinstance(session, Mapping) and isinstance(session.get("session_id"), str)
    }
    return all(
        isinstance(item.get("session_id"), str)
        and isinstance(session_by_id.get(item.get("session_id")), Mapping)
        and session_by_id[item.get("session_id")].get("phase") == "deferred"
        for item in deferred.values()
    )


def _load_verified_reanalysis_receipt(
    repo: YamlRepository,
    operation_id: str,
    previous: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    path = repo.media_root.parent / ".media" / "operations" / f"{operation_id}.json"
    if not path.exists():
        raise CommandValidationError("scheduled reanalysis receipt is not present on current repository state")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CommandValidationError("scheduled reanalysis receipt is invalid") from exc
    if not isinstance(receipt, Mapping):
        raise CommandValidationError("scheduled reanalysis receipt must be an object")
    if receipt.get("operation") != "set_inferred_preferences":
        raise CommandValidationError("scheduled reanalysis receipt has wrong operation")
    if receipt.get("status") not in {"applied", "no_change"}:
        raise CommandValidationError("scheduled reanalysis receipt is not successful")
    details = receipt.get("details") or {}
    if not isinstance(details, Mapping) or details.get("target") != "primary":
        raise CommandValidationError("scheduled reanalysis receipt must target primary")
    if previous is not None:
        if previous.get("operation_id") == operation_id:
            raise CommandValidationError("scheduled reanalysis receipt was already recorded")
        previous_at = previous.get("completed_at")
        current_at = receipt.get("applied_at")
        if isinstance(previous_at, str) and isinstance(current_at, str) and current_at <= previous_at:
            raise CommandValidationError("scheduled reanalysis receipt is not newer than previous milestone")
    return receipt


def plan_reserve_reassessment_session(
    repo: YamlRepository,
    command: ReserveReassessmentSessionCommand,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    _, ledger, current_digest = _load_ledger(
        repo,
        pilot_id=command.pilot_id,
        expected_digest=command.expected_ledger_digest,
    )
    if any(
        isinstance(session, Mapping) and session.get("status") == "open"
        for session in ledger.get("sessions") or []
    ):
        raise CommandValidationError("cannot reserve a new reassessment session while another session is open")
    if any(
        isinstance(session, Mapping) and session.get("session_id") == command.session_id
        for session in ledger.get("sessions") or []
    ):
        raise CommandValidationError("reassessment session id already exists")

    phase = _assert_next_reservation_batch(ledger, command.work_ids)
    at = _at(now)
    items = ledger.get("items") or {}
    reserved_details: dict[str, dict[str, str]] = {}
    for work_id in command.work_ids:
        record = repo.get_work(work_id)
        if record is None:
            raise NotFoundError(f"reassessment work not found: {work_id}")
        signal = _primary_signal(record)
        feedback_digest = feedback_state_digest(signal)
        work_digest = file_sha256(record.path.read_bytes())
        items[work_id] = {
            "status": "in_progress",
            "session_id": command.session_id,
            "reserved_at": at,
            "pre_review_feedback_digest": feedback_digest,
            "pre_review_work_file_digest": work_digest,
        }
        reserved_details[work_id] = {
            "pre_review_feedback_digest": feedback_digest,
            "pre_review_work_file_digest": work_digest,
        }
    ledger["items"] = items
    ledger.setdefault("sessions", []).append(
        {
            "session_id": command.session_id,
            "reserved_work_ids": list(command.work_ids),
            "status": "open",
            "phase": phase,
            "opened_at": at,
        }
    )
    return MutationPlan(
        operation_id=command.operation_id,
        operation="reserve_reassessment_session",
        changed_entities=(),
        documents={},
        rebuild_index=False,
        rebuild_profile_targets=(),
        details={
            "pilot_id": command.pilot_id,
            "session_id": command.session_id,
            "phase": phase,
            "expected_ledger_digest": current_digest,
            "reserved_work_ids": list(command.work_ids),
            "reserved_items": reserved_details,
        },
        json_documents={LEDGER_REL_PATH: ledger},
    )


def plan_complete_reassessment_item(
    repo: YamlRepository,
    command: CompleteReassessmentItemCommand,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    _, ledger, current_digest = _load_ledger(
        repo,
        pilot_id=command.pilot_id,
        expected_digest=command.expected_ledger_digest,
    )
    _, session = _find_session(ledger, command.session_id)
    if session.get("status") != "open":
        raise CommandValidationError("reassessment item can only complete inside an open session")
    if command.work_id not in (session.get("reserved_work_ids") or []):
        raise CommandValidationError("reassessment work is not reserved by the requested session")

    items = ledger.get("items") or {}
    lifecycle = items.get(command.work_id)
    if not isinstance(lifecycle, Mapping) or lifecycle.get("status") != "in_progress":
        raise CommandValidationError("reassessment item is not in_progress")
    if lifecycle.get("session_id") != command.session_id:
        raise CommandValidationError("reassessment item reservation belongs to another session")

    record = repo.get_work(command.work_id)
    if record is None:
        raise NotFoundError(f"reassessment work not found: {command.work_id}")
    current_signal = _primary_signal(record)
    current_feedback_digest = feedback_state_digest(current_signal)
    reserved_feedback_digest = lifecycle.get("pre_review_feedback_digest")
    reserved_work_digest = lifecycle.get("pre_review_work_file_digest")
    current_work_digest = file_sha256(record.path.read_bytes())
    if current_feedback_digest != reserved_feedback_digest:
        raise CommandValidationError("pre-review feedback state changed after reservation")
    if current_work_digest != reserved_work_digest:
        raise CommandValidationError("pre-review canonical work file changed after reservation")

    at = _at(now)
    documents: dict[str, Mapping[str, Any]] = {}
    changed_entities: tuple[str, ...] = ()
    rebuild_index = False
    rebuild_targets: tuple[str, ...] = ()

    if command.outcome == "changed":
        if command.feedback_edit is None:
            raise CommandValidationError("changed reassessment requires feedback_edit")
        _validate_fresh_explicit_edit(command.feedback_edit)
        edit = TargetEdit(
            target="primary",
            set_values=dict(command.feedback_edit.get("set") or {}),
            clear=tuple(command.feedback_edit.get("clear") or ()),
            purge=False,
        )
        updated, changed, touched_targets = apply_feedback_edits(
            repo,
            record.data,
            (edit,),
            now=now,
        )
        if not changed:
            raise CommandValidationError("changed reassessment must produce an actual canonical feedback mutation")
        if touched_targets != {"primary"}:
            raise CommandValidationError("reassessment completion may mutate only primary feedback")
        documents[_work_rel_path(repo, record)] = updated
        changed_entities = (command.work_id,)
        rebuild_index = True
        rebuild_targets = profile_targets_for(repo, touched_targets)
    elif command.outcome == "confirmed_unchanged":
        if not _current_evidence_is_explicit(current_signal):
            raise CommandValidationError(
                "confirmed_unchanged requires current canonical evidence to already be explicit"
            )
    elif command.outcome != "deferred":
        raise CommandValidationError(f"unsupported reassessment outcome: {command.outcome}")

    terminal = dict(lifecycle)
    terminal["operation_id"] = command.operation_id
    terminal["outcome"] = command.outcome
    if command.outcome == "deferred":
        terminal["status"] = "deferred"
        terminal.pop("historical_exposure", None)
        terminal.pop("reviewed_at", None)
    else:
        terminal["status"] = "reviewed"
        terminal["historical_exposure"] = copy.deepcopy(dict(command.historical_exposure or {}))
        terminal["reviewed_at"] = at
    items[command.work_id] = terminal
    ledger["items"] = items

    return MutationPlan(
        operation_id=command.operation_id,
        operation="complete_reassessment_item",
        changed_entities=changed_entities,
        documents=documents,
        rebuild_index=rebuild_index,
        rebuild_profile_targets=rebuild_targets,
        details={
            "pilot_id": command.pilot_id,
            "session_id": command.session_id,
            "work_id": command.work_id,
            "outcome": command.outcome,
            "expected_ledger_digest": current_digest,
            "pre_review_feedback_digest": reserved_feedback_digest,
            "pre_review_work_file_digest": reserved_work_digest,
        },
        json_documents={LEDGER_REL_PATH: ledger},
    )


def plan_close_reassessment_session(
    repo: YamlRepository,
    command: CloseReassessmentSessionCommand,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    _, ledger, current_digest = _load_ledger(
        repo,
        pilot_id=command.pilot_id,
        expected_digest=command.expected_ledger_digest,
    )
    session_index, session = _find_session(ledger, command.session_id)
    if session.get("status") != "open":
        raise CommandValidationError("reassessment session is not open")

    lifecycle_items = ledger.get("items") or {}
    reserved_ids = list(session.get("reserved_work_ids") or [])
    unresolved = [
        work_id
        for work_id in reserved_ids
        if not isinstance(lifecycle_items.get(work_id), Mapping)
        or lifecycle_items[work_id].get("status") not in {"reviewed", "deferred"}
    ]
    if unresolved:
        raise CommandValidationError(
            f"reassessment session cannot close until all reserved items are resolved: {unresolved}"
        )

    reviewed_total = _reviewed_total(ledger)
    deferred_total = _deferred_total(ledger)
    due = _scheduled_reanalysis_due(ledger)
    scheduled_state = ledger.setdefault("scheduled_reanalysis", {"last_completed": None})
    previous = scheduled_state.get("last_completed")
    reanalysis_receipt: Mapping[str, Any] | None = None
    if due:
        if command.scheduled_reanalysis_operation_id is None:
            raise CommandValidationError("scheduled primary taste reanalysis is due before session close")
        reanalysis_receipt = _load_verified_reanalysis_receipt(
            repo,
            command.scheduled_reanalysis_operation_id,
            previous if isinstance(previous, Mapping) else None,
        )
    elif command.scheduled_reanalysis_operation_id is not None:
        raise CommandValidationError("scheduled reanalysis operation id supplied when no milestone is due")

    audit = collect_intelligence_audit(repo.media_root.parent)
    ratings_primary = (((audit.get("ratings") or {}).get("primary") or {}).get("works") or {})
    feedback_primary = (((audit.get("feedback") or {}).get("primary") or {}).get("works") or {})
    at = _at(now)
    newly_reviewed = sum(
        1
        for work_id in reserved_ids
        if isinstance(lifecycle_items.get(work_id), Mapping)
        and lifecycle_items[work_id].get("status") == "reviewed"
    )
    newly_deferred = sum(
        1
        for work_id in reserved_ids
        if isinstance(lifecycle_items.get(work_id), Mapping)
        and lifecycle_items[work_id].get("status") == "deferred"
    )
    snapshot = {
        "session_id": command.session_id,
        "completed_at": at,
        "newly_reviewed": newly_reviewed,
        "newly_deferred": newly_deferred,
        "reviewed_total": reviewed_total,
        "deferred_total": deferred_total,
        "primary_rating_sources": copy.deepcopy(dict(ratings_primary.get("by_source") or {})),
        "primary_structured_feedback": {
            "numerator": int(feedback_primary.get("numerator", 0)),
            "denominator": int(feedback_primary.get("denominator", 0)),
        },
        "canonical_input_digest": audit.get("canonical_input_digest"),
        "audit_schema_version": audit.get("schema_version"),
        "base_revision": ledger.get("base_revision"),
        "baseline_path": ledger.get("baseline_path"),
        "baseline_canonical_input_digest": ledger.get("baseline_canonical_input_digest"),
    }

    sessions = list(ledger.get("sessions") or [])
    closed_session = copy.deepcopy(dict(session))
    closed_session["status"] = "closed"
    closed_session["closed_at"] = at
    closed_session["snapshot"] = snapshot
    sessions[session_index] = closed_session
    ledger["sessions"] = sessions

    if reanalysis_receipt is not None:
        scheduled_state["last_completed"] = {
            "reviewed_count": reviewed_total,
            "operation_id": command.scheduled_reanalysis_operation_id,
            "completed_at": reanalysis_receipt.get("applied_at"),
        }
        ledger["scheduled_reanalysis"] = scheduled_state

    if _pilot_completion_ready(ledger):
        ledger["pilot_status"] = "completed"

    return MutationPlan(
        operation_id=command.operation_id,
        operation="close_reassessment_session",
        changed_entities=(),
        documents={},
        rebuild_index=False,
        rebuild_profile_targets=(),
        details={
            "pilot_id": command.pilot_id,
            "session_id": command.session_id,
            "expected_ledger_digest": current_digest,
            "reviewed_total": reviewed_total,
            "deferred_total": deferred_total,
            "scheduled_reanalysis_due": due,
            "scheduled_reanalysis_operation_id": command.scheduled_reanalysis_operation_id,
        },
        json_documents={LEDGER_REL_PATH: ledger},
    )



_MODERNIZATION_BLOCKERS = {
    "provider_identity_missing",
    "provider_identity_ambiguous",
    "provider_identity_conflict",
    "semantic_context_insufficient",
}


def _load_modernization_receipt(
    repo_root: Path,
    operation_id: str,
    *,
    operation: str,
    work_id: str,
    label: str,
) -> Mapping[str, Any]:
    path = repo_root / ".media" / "operations" / f"{operation_id}.json"
    if not path.exists():
        raise CommandValidationError(f"{label} modernization receipt is not present")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CommandValidationError(f"{label} modernization receipt is invalid") from exc
    if not isinstance(receipt, Mapping):
        raise CommandValidationError(f"{label} modernization receipt must be an object")
    if receipt.get("operation") != operation:
        raise CommandValidationError(f"{label} modernization receipt has wrong operation")
    if receipt.get("status") not in {"applied", "no_change"}:
        raise CommandValidationError(f"{label} modernization receipt is not successful")
    details = receipt.get("details")
    if not isinstance(details, Mapping) or details.get("work_id") != work_id:
        raise CommandValidationError(f"{label} modernization receipt is not bound to requested work")
    if not isinstance(receipt.get("applied_at"), str) or not receipt.get("applied_at"):
        raise CommandValidationError(f"{label} modernization receipt lacks applied_at")
    return receipt


def plan_record_reassessment_modernization(
    repo_root: Path,
    repo: YamlRepository,
    command: RecordReassessmentModernizationCommand,
    *,
    now: datetime | None = None,
) -> MutationPlan:
    _, ledger, current_ledger_digest = _load_ledger(
        repo,
        pilot_id=command.pilot_id,
        expected_digest=command.expected_ledger_digest,
    )
    frozen = ledger.get("frozen_cohort") or {}
    if command.work_id not in (frozen.get("work_ids") or []):
        raise CommandValidationError("modernization work is not in frozen reassessment cohort")

    items = ledger.get("items") or {}
    lifecycle = items.get(command.work_id)
    if not isinstance(lifecycle, Mapping) or lifecycle.get("status") != "reviewed":
        raise CommandValidationError("reassessment modernization requires a human reviewed item")

    existing = lifecycle.get("modernization")
    if isinstance(existing, Mapping) and existing.get("status") == "completed":
        raise CommandValidationError("completed reassessment modernization is terminal")
    if isinstance(existing, Mapping) and existing.get("status") == "blocked" and command.outcome == "blocked":
        raise CommandValidationError("blocked reassessment modernization cannot be rewritten")

    record = repo.get_work(command.work_id)
    if record is None:
        raise NotFoundError(f"reassessment modernization work not found: {command.work_id}")
    current_work_digest = file_sha256(record.path.read_bytes())
    if current_work_digest != command.expected_work_digest:
        raise CommandValidationError(
            f"work digest mismatch for {command.work_id}: expected {command.expected_work_digest}, current {current_work_digest}"
        )

    at = _at(now)
    if command.outcome == "blocked":
        if command.blocker_code not in _MODERNIZATION_BLOCKERS:
            raise CommandValidationError("invalid reassessment modernization blocker code")
        modernization = {
            "status": "blocked",
            "blocker_code": command.blocker_code,
            "recorded_at": at,
            "work_digest": current_work_digest,
        }
    elif command.outcome == "completed":
        if not command.metadata_operation_id or not command.semantic_operation_id or not command.vocabulary_digest:
            raise CommandValidationError("completed modernization requires metadata/semantic/vocabulary provenance")
        metadata_receipt = _load_modernization_receipt(
            Path(repo_root),
            command.metadata_operation_id,
            operation="refresh_work_metadata",
            work_id=command.work_id,
            label="metadata",
        )
        semantic_receipt = _load_modernization_receipt(
            Path(repo_root),
            command.semantic_operation_id,
            operation="set_semantic_fingerprint",
            work_id=command.work_id,
            label="semantic",
        )
        reviewed_at = lifecycle.get("reviewed_at")
        metadata_at = metadata_receipt.get("applied_at")
        semantic_at = semantic_receipt.get("applied_at")
        if not isinstance(reviewed_at, str) or not reviewed_at:
            raise CommandValidationError("reviewed item lacks reviewed_at provenance")
        if metadata_at <= reviewed_at:
            raise CommandValidationError("metadata modernization receipt must occur after human reassessment")
        if semantic_at <= metadata_at:
            raise CommandValidationError("semantic modernization receipt must occur after metadata refresh")

        vocabulary_path = Path(repo_root) / "media" / "vocabulary.yaml"
        if not vocabulary_path.exists():
            raise CommandValidationError("media vocabulary is missing")
        current_vocabulary_digest = file_sha256(vocabulary_path.read_bytes())
        if current_vocabulary_digest != command.vocabulary_digest:
            raise CommandValidationError(
                f"vocabulary digest mismatch: expected {command.vocabulary_digest}, current {current_vocabulary_digest}"
            )
        modernization = {
            "status": "completed",
            "metadata_operation_id": command.metadata_operation_id,
            "semantic_operation_id": command.semantic_operation_id,
            "completed_at": at,
            "work_digest": current_work_digest,
            "vocabulary_digest": current_vocabulary_digest,
        }
    else:
        raise CommandValidationError(f"unsupported reassessment modernization outcome: {command.outcome}")

    updated_item = copy.deepcopy(dict(lifecycle))
    updated_item["modernization"] = modernization
    items[command.work_id] = updated_item
    ledger["items"] = items
    return MutationPlan(
        operation_id=command.operation_id,
        operation="record_reassessment_modernization",
        changed_entities=(),
        documents={},
        rebuild_index=False,
        rebuild_profile_targets=(),
        details={
            "pilot_id": command.pilot_id,
            "work_id": command.work_id,
            "outcome": command.outcome,
            "expected_ledger_digest": current_ledger_digest,
            "expected_work_digest": current_work_digest,
            "modernization": copy.deepcopy(modernization),
        },
        json_documents={LEDGER_REL_PATH: ledger},
    )
