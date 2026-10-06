from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from media.service.reassessment import ALLOWED_COHORT_VIEWING, STRATUM_ORDER, frozen_order_key


@dataclass(frozen=True)
class ReassessmentSnapshotIssue:
    code: str
    message: str


def _issue(issues: list[ReassessmentSnapshotIssue], code: str, message: str) -> None:
    issues.append(ReassessmentSnapshotIssue(code, message))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


_MODERNIZATION_BLOCKERS = {
    "provider_identity_missing",
    "provider_identity_ambiguous",
    "provider_identity_conflict",
    "semantic_context_insufficient",
}


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in value[7:]
    )


def _validate_modernization_snapshot(
    work_id: str,
    lifecycle: Mapping[str, Any],
    issues: list[ReassessmentSnapshotIssue],
) -> None:
    modernization_raw = lifecycle.get("modernization")
    if modernization_raw is None:
        return
    modernization = _mapping(modernization_raw)
    if lifecycle.get("status") != "reviewed":
        _issue(issues, "reassessment_modernization", f"only reviewed items may carry modernization: {work_id}")
        return
    status = modernization.get("status")
    if status == "blocked":
        if (
            modernization.get("blocker_code") not in _MODERNIZATION_BLOCKERS
            or not isinstance(modernization.get("recorded_at"), str)
            or not modernization.get("recorded_at")
            or not _sha256(modernization.get("work_digest"))
            or any(key in modernization for key in ("metadata_operation_id", "semantic_operation_id", "vocabulary_digest", "completed_at"))
        ):
            _issue(issues, "reassessment_modernization", f"blocked modernization provenance is invalid: {work_id}")
    elif status == "completed":
        if (
            not isinstance(modernization.get("metadata_operation_id"), str)
            or not modernization.get("metadata_operation_id")
            or not isinstance(modernization.get("semantic_operation_id"), str)
            or not modernization.get("semantic_operation_id")
            or not isinstance(modernization.get("completed_at"), str)
            or not modernization.get("completed_at")
            or not _sha256(modernization.get("work_digest"))
            or not _sha256(modernization.get("vocabulary_digest"))
            or any(key in modernization for key in ("blocker_code", "recorded_at"))
        ):
            _issue(issues, "reassessment_modernization", f"completed modernization provenance is invalid: {work_id}")
    else:
        _issue(issues, "reassessment_modernization", f"invalid modernization status for {work_id}: {status}")


def _completed_pilot_state_is_valid(document: Mapping[str, Any]) -> bool:
    lifecycle = _mapping(document.get("items"))
    if any(
        _mapping(item).get("status") in {"pending", "in_progress"}
        for item in lifecycle.values()
    ):
        return False

    deferred = {
        work_id: _mapping(item)
        for work_id, item in lifecycle.items()
        if _mapping(item).get("status") == "deferred"
    }
    if not deferred:
        return True

    sessions = {
        _mapping(session).get("session_id"): _mapping(session)
        for session in document.get("sessions") or []
        if isinstance(_mapping(session).get("session_id"), str)
    }
    return all(
        isinstance(item.get("session_id"), str)
        and _mapping(sessions.get(item.get("session_id"))).get("phase") == "deferred"
        for item in deferred.values()
    )


def validate_reassessment_snapshot(
    document: Mapping[str, Any],
    *,
    canonical_work_ids: set[str],
) -> list[ReassessmentSnapshotIssue]:
    issues: list[ReassessmentSnapshotIssue] = []
    pilot_id = document.get("pilot_id")
    frozen = _mapping(document.get("frozen_cohort"))
    work_ids_raw = frozen.get("work_ids")
    work_ids = list(work_ids_raw) if isinstance(work_ids_raw, list) else []
    frozen_items = _mapping(frozen.get("items"))
    lifecycle_items = _mapping(document.get("items"))

    base_revision = document.get("base_revision")
    cohort_revision = frozen.get("cohort_revision")
    if isinstance(base_revision, str) and isinstance(cohort_revision, str) and cohort_revision != base_revision:
        _issue(issues, "reassessment_cohort_revision", "frozen cohort revision must equal pilot base_revision")

    unique_work_ids = [work_id for work_id in work_ids if isinstance(work_id, str)]
    work_id_set = set(unique_work_ids)
    if len(unique_work_ids) != len(work_ids) or len(work_id_set) != len(unique_work_ids):
        _issue(issues, "reassessment_cohort_mismatch", "frozen cohort work_ids must be unique strings")
    if work_id_set != set(frozen_items) or work_id_set != set(lifecycle_items):
        _issue(issues, "reassessment_cohort_mismatch", "frozen cohort and lifecycle item keys must match work_ids exactly")

    for rank, work_id in enumerate(unique_work_ids):
        if work_id not in canonical_work_ids:
            _issue(issues, "reassessment_missing_work", f"frozen reassessment work is not canonical: {work_id}")
        item = _mapping(frozen_items.get(work_id))
        status = item.get("viewing_status")
        if status not in ALLOWED_COHORT_VIEWING:
            _issue(issues, "reassessment_membership", f"invalid frozen viewing status for {work_id}: {status}")
        stratum = item.get("stratum")
        if stratum not in STRATUM_ORDER:
            _issue(issues, "reassessment_order", f"invalid frozen stratum for {work_id}: {stratum}")
        expected_key = frozen_order_key(str(pilot_id), work_id) if isinstance(pilot_id, str) else None
        if item.get("order_key") != expected_key or item.get("order_rank") != rank:
            _issue(issues, "reassessment_order", f"frozen order metadata is inconsistent for {work_id}")

    for work_id, lifecycle_raw in lifecycle_items.items():
        lifecycle = _mapping(lifecycle_raw)
        _validate_modernization_snapshot(work_id, lifecycle, issues)
        if lifecycle.get("status") == "reviewed":
            if (
                lifecycle.get("outcome") not in {"changed", "confirmed_unchanged"}
                or not isinstance(lifecycle.get("historical_exposure"), Mapping)
                or not isinstance(lifecycle.get("reviewed_at"), str)
                or not lifecycle.get("reviewed_at")
                or not isinstance(lifecycle.get("operation_id"), str)
                or not lifecycle.get("operation_id")
            ):
                _issue(
                    issues,
                    "reassessment_reviewed_provenance",
                    f"reviewed item lacks terminal outcome/exposure/timestamp/operation provenance: {work_id}",
                )

    if document.get("pilot_status") == "completed" and not _completed_pilot_state_is_valid(document):
        _issue(
            issues,
            "reassessment_incomplete_pilot",
            "completed pilot has pending/in-progress work or deferred items without deferred-pass provenance",
        )

    previous_reviewed_total = -1
    previous_deferred_total = -1
    sessions = document.get("sessions")
    for session_raw in sessions if isinstance(sessions, list) else []:
        session = _mapping(session_raw)
        if session.get("status") != "closed":
            continue
        session_id = session.get("session_id")
        if isinstance(session_id, str) and any(
            _mapping(item_raw).get("status") == "in_progress"
            and _mapping(item_raw).get("session_id") == session_id
            for item_raw in lifecycle_items.values()
        ):
            _issue(
                issues,
                "reassessment_closed_session_in_progress",
                f"closed session still owns an in-progress item: {session_id}",
            )
        snapshot = _mapping(session.get("snapshot"))
        reviewed_total = snapshot.get("reviewed_total")
        deferred_total = snapshot.get("deferred_total")
        if isinstance(reviewed_total, int) and isinstance(deferred_total, int):
            if reviewed_total < previous_reviewed_total or deferred_total < previous_deferred_total:
                _issue(
                    issues,
                    "reassessment_nonmonotonic_session",
                    f"closed session cumulative counters moved backwards: {session_id}",
                )
            previous_reviewed_total = max(previous_reviewed_total, reviewed_total)
            previous_deferred_total = max(previous_deferred_total, deferred_total)
    return issues


_IMMUTABLE_TRANSITION_KEYS = (
    "schema_version",
    "pilot_id",
    "target",
    "base_revision",
    "baseline_path",
    "baseline_schema_version",
    "baseline_canonical_input_digest",
    "frozen_cohort",
)


def _changed_item_ids(base: Mapping[str, Any], head: Mapping[str, Any]) -> set[str]:
    base_items = _mapping(base.get("items"))
    head_items = _mapping(head.get("items"))
    return {
        work_id
        for work_id in set(base_items) | set(head_items)
        if base_items.get(work_id) != head_items.get(work_id)
    }


def _receipt_details(
    receipt: Mapping[str, Any],
    operation: str,
    issues: list[ReassessmentSnapshotIssue],
) -> Mapping[str, Any]:
    if receipt.get("operation") != operation:
        _issue(issues, "reassessment_transition_receipt", "operation receipt does not match requested transition operation")
    if receipt.get("status") not in {"applied", "no_change"}:
        _issue(issues, "reassessment_transition_receipt", "operation receipt is not successful")
    details = receipt.get("details")
    if not isinstance(details, Mapping):
        _issue(issues, "reassessment_transition_receipt", "operation receipt lacks trusted details")
        return {}
    return details


def _validate_terminal_items(
    base: Mapping[str, Any],
    head: Mapping[str, Any],
    *,
    operation: str,
    issues: list[ReassessmentSnapshotIssue],
) -> None:
    base_items = _mapping(base.get("items"))
    head_items = _mapping(head.get("items"))
    for work_id, item in base_items.items():
        if _mapping(item).get("status") != "reviewed" or head_items.get(work_id) == item:
            continue
        if operation == "record_reassessment_modernization":
            before = dict(_mapping(item)); before.pop("modernization", None)
            after = dict(_mapping(head_items.get(work_id))); after.pop("modernization", None)
            if before == after:
                continue
        _issue(issues, "reassessment_transition_terminal", f"reviewed reassessment item is immutable: {work_id}")


def _validate_closed_session_history(base: Mapping[str, Any], head: Mapping[str, Any], issues: list[ReassessmentSnapshotIssue]) -> None:
    base_sessions = list(base.get("sessions") or [])
    head_sessions = list(head.get("sessions") or [])
    for index, session in enumerate(base_sessions):
        if not isinstance(session, Mapping) or session.get("status") != "closed":
            continue
        if index >= len(head_sessions) or head_sessions[index] != session:
            _issue(issues, "reassessment_transition_closed_session", f"previously closed session changed or moved: {session.get('session_id')}")


def _validate_reanalysis_transition(
    base: Mapping[str, Any],
    head: Mapping[str, Any],
    *,
    operation: str,
    details: Mapping[str, Any],
    issues: list[ReassessmentSnapshotIssue],
) -> None:
    base_last = _mapping(base.get("scheduled_reanalysis")).get("last_completed")
    head_last = _mapping(head.get("scheduled_reanalysis")).get("last_completed")
    if operation != "close_reassessment_session":
        if base_last != head_last:
            _issue(issues, "reassessment_transition_reanalysis", "only close_reassessment_session may change scheduled reanalysis state")
        return
    if base_last == head_last:
        if details.get("scheduled_reanalysis_operation_id") is not None:
            _issue(issues, "reassessment_transition_reanalysis", "close receipt references reanalysis without advancing scheduled state")
        return
    if not isinstance(head_last, Mapping):
        _issue(issues, "reassessment_transition_reanalysis", "scheduled reanalysis history cannot move backwards or become malformed")
        return
    base_count = int(base_last.get("reviewed_count", -1)) if isinstance(base_last, Mapping) else -1
    head_count = head_last.get("reviewed_count")
    if not isinstance(head_count, int) or head_count <= base_count:
        _issue(issues, "reassessment_transition_reanalysis", "scheduled reanalysis reviewed_count must advance monotonically")
    expected_operation_id = details.get("scheduled_reanalysis_operation_id")
    if not isinstance(expected_operation_id, str) or head_last.get("operation_id") != expected_operation_id:
        _issue(issues, "reassessment_transition_reanalysis", "scheduled reanalysis operation id must match close receipt details")
    if not isinstance(head_last.get("completed_at"), str) or not head_last.get("completed_at"):
        _issue(issues, "reassessment_transition_reanalysis", "scheduled reanalysis state requires completed_at provenance")


def _validate_reserve_transition(
    base: Mapping[str, Any],
    head: Mapping[str, Any],
    details: Mapping[str, Any],
    issues: list[ReassessmentSnapshotIssue],
) -> None:
    session_id = details.get("session_id")
    reserved = details.get("reserved_work_ids")
    if not isinstance(session_id, str) or not isinstance(reserved, list) or not reserved or any(not isinstance(item, str) for item in reserved):
        _issue(issues, "reassessment_transition_reserve", "reserve receipt lacks session_id/reserved_work_ids")
        return

    base_sessions = list(base.get("sessions") or [])
    if any(_mapping(session).get("status") == "open" for session in base_sessions):
        _issue(issues, "reassessment_transition_reserve", "reserve cannot append a second open reassessment session")
    if any(_mapping(session).get("session_id") == session_id for session in base_sessions):
        _issue(issues, "reassessment_transition_reserve", "reserve session id must be unique")

    head_sessions = list(head.get("sessions") or [])
    if len(head_sessions) != len(base_sessions) + 1 or head_sessions[: len(base_sessions)] != base_sessions:
        _issue(issues, "reassessment_transition_reserve", "reserve must append exactly one session without rewriting history")
        new_session: Mapping[str, Any] = {}
    else:
        new_session = _mapping(head_sessions[-1])
        if (
            new_session.get("session_id") != session_id
            or new_session.get("status") != "open"
            or new_session.get("reserved_work_ids") != reserved
        ):
            _issue(issues, "reassessment_transition_reserve", "appended reserve session does not match receipt details")

    base_items = _mapping(base.get("items"))
    head_items = _mapping(head.get("items"))
    frozen_ids = list(_mapping(base.get("frozen_cohort")).get("work_ids") or [])
    pending = [work_id for work_id in frozen_ids if _mapping(base_items.get(work_id)).get("status") == "pending"]
    phase = "pending" if pending else "deferred"
    eligible = pending if pending else [work_id for work_id in frozen_ids if _mapping(base_items.get(work_id)).get("status") == "deferred"]
    if reserved != eligible[: len(reserved)]:
        _issue(issues, "reassessment_transition_reserve", "reserve work ids are not the next frozen-order eligible prefix")
    if new_session and new_session.get("phase") not in {None, phase}:
        _issue(issues, "reassessment_transition_reserve", "reserve session phase does not match eligible lifecycle phase")
    if details.get("phase") is not None and details.get("phase") != phase:
        _issue(issues, "reassessment_transition_reserve", "reserve receipt phase does not match eligible lifecycle phase")

    if _changed_item_ids(base, head) != set(reserved):
        _issue(issues, "reassessment_transition_reserve", "reserve may change only the reserved lifecycle items")
    for work_id in reserved:
        before = _mapping(base_items.get(work_id))
        after = _mapping(head_items.get(work_id))
        if before.get("status") not in {"pending", "deferred"} or after.get("status") != "in_progress" or after.get("session_id") != session_id:
            _issue(issues, "reassessment_transition_reserve", f"illegal reserve lifecycle transition for {work_id}")
        for field in ("reserved_at", "pre_review_feedback_digest", "pre_review_work_file_digest"):
            if not after.get(field):
                _issue(issues, "reassessment_transition_reserve", f"reserved item lacks {field}: {work_id}")
    if base.get("pilot_status") != head.get("pilot_status"):
        _issue(issues, "reassessment_transition_reserve", "reserve may not change pilot_status")
    if base.get("scheduled_reanalysis") != head.get("scheduled_reanalysis"):
        _issue(issues, "reassessment_transition_reserve", "reserve may not change scheduled reanalysis state")


def _find_session(document: Mapping[str, Any], session_id: str) -> Mapping[str, Any]:
    matches = [
        _mapping(session)
        for session in document.get("sessions") or []
        if _mapping(session).get("session_id") == session_id
    ]
    return matches[0] if len(matches) == 1 else {}


def _validate_complete_transition(
    base: Mapping[str, Any],
    head: Mapping[str, Any],
    receipt: Mapping[str, Any],
    details: Mapping[str, Any],
    issues: list[ReassessmentSnapshotIssue],
) -> None:
    work_id = details.get("work_id")
    session_id = details.get("session_id")
    if not isinstance(work_id, str) or not isinstance(session_id, str):
        _issue(issues, "reassessment_transition_complete", "complete receipt lacks work_id/session_id")
        return
    if _changed_item_ids(base, head) != {work_id}:
        _issue(issues, "reassessment_transition_complete", "complete must change exactly one lifecycle item")

    before = _mapping(_mapping(base.get("items")).get(work_id))
    after = _mapping(_mapping(head.get("items")).get(work_id))
    session = _find_session(base, session_id)
    if before.get("status") != "in_progress" or before.get("session_id") != session_id:
        _issue(issues, "reassessment_transition_complete", "complete base item is not reserved by the receipt session")
    if session.get("status") != "open" or work_id not in (session.get("reserved_work_ids") or []):
        _issue(issues, "reassessment_transition_complete", "complete work must belong to the matching open session")

    outcome = details.get("outcome")
    if outcome in {"changed", "confirmed_unchanged"}:
        if after.get("status") != "reviewed" or after.get("outcome") != outcome:
            _issue(issues, "reassessment_transition_complete", "reviewed completion status/outcome must match receipt")
    elif outcome == "deferred":
        if after.get("status") != "deferred" or after.get("outcome") != "deferred":
            _issue(issues, "reassessment_transition_complete", "deferred completion status/outcome must match receipt")
        if "historical_exposure" in after or "reviewed_at" in after:
            _issue(issues, "reassessment_transition_complete", "deferred completion may not carry reviewed provenance")
    elif after.get("status") not in {"reviewed", "deferred"}:
        _issue(issues, "reassessment_transition_complete", "complete target must become reviewed or deferred")

    if after.get("operation_id") != receipt.get("operation_id"):
        _issue(issues, "reassessment_transition_complete", "complete lifecycle operation provenance does not match receipt")
    for field in ("session_id", "reserved_at", "pre_review_feedback_digest", "pre_review_work_file_digest"):
        if after.get(field) != before.get(field):
            _issue(issues, "reassessment_transition_complete", f"complete may not rewrite reservation field {field}")
    if base.get("sessions") != head.get("sessions"):
        _issue(issues, "reassessment_transition_complete", "complete may not rewrite session records")
    if base.get("pilot_status") != head.get("pilot_status"):
        _issue(issues, "reassessment_transition_complete", "complete may not change pilot_status")
    if base.get("scheduled_reanalysis") != head.get("scheduled_reanalysis"):
        _issue(issues, "reassessment_transition_complete", "complete may not change scheduled reanalysis state")


def _validate_close_transition(
    base: Mapping[str, Any],
    head: Mapping[str, Any],
    details: Mapping[str, Any],
    issues: list[ReassessmentSnapshotIssue],
) -> None:
    session_id = details.get("session_id")
    if not isinstance(session_id, str):
        _issue(issues, "reassessment_transition_close", "close receipt lacks session_id")
        return
    if _mapping(base.get("items")) != _mapping(head.get("items")):
        _issue(issues, "reassessment_transition_close", "close may not change item lifecycle state")

    base_sessions = list(base.get("sessions") or [])
    head_sessions = list(head.get("sessions") or [])
    if len(base_sessions) != len(head_sessions):
        _issue(issues, "reassessment_transition_close", "close may not append/delete/reorder sessions")
        return
    changed_indexes = [index for index, pair in enumerate(zip(base_sessions, head_sessions)) if pair[0] != pair[1]]
    if len(changed_indexes) != 1:
        _issue(issues, "reassessment_transition_close", "close must change exactly one session")
        return
    index = changed_indexes[0]
    before = _mapping(base_sessions[index])
    after = _mapping(head_sessions[index])
    if before.get("session_id") != session_id or after.get("session_id") != session_id or before.get("status") != "open" or after.get("status") != "closed":
        _issue(issues, "reassessment_transition_close", "close must transition the receipt session from open to closed")
    for field in ("session_id", "reserved_work_ids", "opened_at", "phase"):
        if before.get(field) != after.get(field):
            _issue(issues, "reassessment_transition_close", f"close may not rewrite session field {field}")
    if not after.get("closed_at") or not isinstance(after.get("snapshot"), Mapping):
        _issue(issues, "reassessment_transition_close", "closed session must add closed_at and snapshot")
    unresolved = [
        work_id
        for work_id in before.get("reserved_work_ids") or []
        if _mapping(_mapping(base.get("items")).get(work_id)).get("status") not in {"reviewed", "deferred"}
    ]
    if unresolved:
        _issue(issues, "reassessment_transition_close", "close session still has unresolved reserved items")
    if base.get("pilot_status") == "completed" and head.get("pilot_status") != "completed":
        _issue(issues, "reassessment_transition_close", "completed pilot cannot be reopened")
    if head.get("pilot_status") not in {"active", "completed"}:
        _issue(issues, "reassessment_transition_close", "invalid pilot_status after close")
    if head.get("pilot_status") == "completed" and not _completed_pilot_state_is_valid(head):
        _issue(issues, "reassessment_transition_close", "close cannot complete pilot before deferred stop condition is proven")


def _validate_modernization_transition(
    base: Mapping[str, Any],
    head: Mapping[str, Any],
    details: Mapping[str, Any],
    issues: list[ReassessmentSnapshotIssue],
) -> None:
    work_id = details.get("work_id")
    outcome = details.get("outcome")
    expected_modernization = details.get("modernization")
    if not isinstance(work_id, str) or outcome not in {"blocked", "completed"} or not isinstance(expected_modernization, Mapping):
        _issue(issues, "reassessment_transition_modernization", "modernization receipt lacks work/outcome/provenance")
        return
    if _changed_item_ids(base, head) != {work_id}:
        _issue(issues, "reassessment_transition_modernization", "modernization must change exactly one reviewed item")
    before = _mapping(_mapping(base.get("items")).get(work_id))
    after = _mapping(_mapping(head.get("items")).get(work_id))
    before_human = dict(before); before_human.pop("modernization", None)
    after_human = dict(after); after_human.pop("modernization", None)
    if before.get("status") != "reviewed" or before_human != after_human:
        _issue(issues, "reassessment_transition_modernization", "modernization may not change human reassessment fields")
    before_modernization = _mapping(before.get("modernization"))
    after_modernization = _mapping(after.get("modernization"))
    before_status = before_modernization.get("status") if before_modernization else None
    after_status = after_modernization.get("status")
    if before_status is None:
        allowed = after_status in {"blocked", "completed"}
    elif before_status == "blocked":
        allowed = after_status == "completed"
    else:
        allowed = False
    if not allowed:
        _issue(issues, "reassessment_transition_modernization", f"illegal modernization transition: {before_status} -> {after_status}")
    if after_status != outcome or dict(after_modernization) != dict(expected_modernization):
        _issue(issues, "reassessment_transition_modernization", "modernization state must exactly match receipt details")
    if base.get("sessions") != head.get("sessions"):
        _issue(issues, "reassessment_transition_modernization", "modernization may not change session records")
    if base.get("pilot_status") != head.get("pilot_status"):
        _issue(issues, "reassessment_transition_modernization", "modernization may not change pilot_status")
    if base.get("scheduled_reanalysis") != head.get("scheduled_reanalysis"):
        _issue(issues, "reassessment_transition_modernization", "modernization may not change scheduled reanalysis state")


def validate_reassessment_transition(
    base: Mapping[str, Any],
    head: Mapping[str, Any],
    *,
    operation: str,
    receipt: Mapping[str, Any],
) -> list[ReassessmentSnapshotIssue]:
    issues: list[ReassessmentSnapshotIssue] = []
    details = _receipt_details(receipt, operation, issues)
    for key in _IMMUTABLE_TRANSITION_KEYS:
        if base.get(key) != head.get(key):
            _issue(issues, "reassessment_transition_immutable", f"immutable pilot region changed: {key}")
    _validate_terminal_items(base, head, operation=operation, issues=issues)
    _validate_closed_session_history(base, head, issues)
    _validate_reanalysis_transition(base, head, operation=operation, details=details, issues=issues)

    if operation == "reserve_reassessment_session":
        _validate_reserve_transition(base, head, details, issues)
    elif operation == "complete_reassessment_item":
        _validate_complete_transition(base, head, receipt, details, issues)
    elif operation == "close_reassessment_session":
        _validate_close_transition(base, head, details, issues)
    elif operation == "record_reassessment_modernization":
        _validate_modernization_transition(base, head, details, issues)
    else:
        _issue(issues, "reassessment_transition_operation", f"unsupported reassessment transition operation: {operation}")
    return issues
