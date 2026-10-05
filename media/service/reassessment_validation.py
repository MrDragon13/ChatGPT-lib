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


def validate_reassessment_snapshot(
    document: Mapping[str, Any],
    *,
    canonical_work_ids: set[str],
) -> list[ReassessmentSnapshotIssue]:
    """Validate single-revision pilot invariants without reinterpreting frozen evidence."""

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
        status = lifecycle.get("status")
        if status == "reviewed":
            outcome = lifecycle.get("outcome")
            exposure = lifecycle.get("historical_exposure")
            reviewed_at = lifecycle.get("reviewed_at")
            operation_id = lifecycle.get("operation_id")
            if (
                outcome not in {"changed", "confirmed_unchanged"}
                or not isinstance(exposure, Mapping)
                or not isinstance(reviewed_at, str)
                or not reviewed_at
                or not isinstance(operation_id, str)
                or not operation_id
            ):
                _issue(
                    issues,
                    "reassessment_reviewed_provenance",
                    f"reviewed item lacks terminal outcome/exposure/timestamp/operation provenance: {work_id}",
                )

    if document.get("pilot_status") == "completed":
        resumable = [
            work_id
            for work_id, item_raw in lifecycle_items.items()
            if _mapping(item_raw).get("status") in {"pending", "in_progress"}
        ]
        if resumable:
            _issue(
                issues,
                "reassessment_incomplete_pilot",
                "completed pilot still contains pending or in-progress main-pass items",
            )

    previous_reviewed_total = -1
    previous_deferred_total = -1
    sessions = document.get("sessions")
    for session_raw in sessions if isinstance(sessions, list) else []:
        session = _mapping(session_raw)
        if session.get("status") != "closed":
            continue
        session_id = session.get("session_id")
        if isinstance(session_id, str):
            if any(
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


def _receipt_details(receipt: Mapping[str, Any], operation: str, issues: list[ReassessmentSnapshotIssue]) -> Mapping[str, Any]:
    if receipt.get("operation") != operation:
        _issue(issues, "reassessment_transition_receipt", "operation receipt does not match requested transition operation")
    if receipt.get("status") not in {"applied", "no_change"}:
        _issue(issues, "reassessment_transition_receipt", "operation receipt is not successful")
    details = receipt.get("details")
    if not isinstance(details, Mapping):
        _issue(issues, "reassessment_transition_receipt", "operation receipt lacks trusted details")
        return {}
    return details


def _validate_reanalysis_transition(
    base: Mapping[str, Any],
    head: Mapping[str, Any],
    *,
    operation: str,
    issues: list[ReassessmentSnapshotIssue],
) -> None:
    base_last = _mapping(base.get("scheduled_reanalysis")).get("last_completed")
    head_last = _mapping(head.get("scheduled_reanalysis")).get("last_completed")
    if operation != "close_reassessment_session":
        if base_last != head_last:
            _issue(issues, "reassessment_transition_reanalysis", "only close_reassessment_session may change scheduled reanalysis state")
        return
    if base_last == head_last:
        return
    if head_last is None:
        _issue(issues, "reassessment_transition_reanalysis", "scheduled reanalysis history cannot move backwards")
        return
    if not isinstance(head_last, Mapping):
        _issue(issues, "reassessment_transition_reanalysis", "scheduled reanalysis state is malformed")
        return
    base_count = int(base_last.get("reviewed_count", -1)) if isinstance(base_last, Mapping) else -1
    head_count = head_last.get("reviewed_count")
    if not isinstance(head_count, int) or head_count <= base_count:
        _issue(issues, "reassessment_transition_reanalysis", "scheduled reanalysis reviewed_count must advance monotonically")


def _validate_closed_session_history(
    base: Mapping[str, Any],
    head: Mapping[str, Any],
    *,
    operation: str,
    target_session_id: str | None,
    issues: list[ReassessmentSnapshotIssue],
) -> None:
    base_sessions = list(base.get("sessions") or [])
    head_sessions = list(head.get("sessions") or [])
    for index, session in enumerate(base_sessions):
        if not isinstance(session, Mapping) or session.get("status") != "closed":
            continue
        if index >= len(head_sessions) or head_sessions[index] != session:
            _issue(issues, "reassessment_transition_closed_session", f"previously closed session changed or moved: {session.get('session_id')}")


def _validate_terminal_items(base: Mapping[str, Any], head: Mapping[str, Any], issues: list[ReassessmentSnapshotIssue]) -> None:
    base_items = _mapping(base.get("items"))
    head_items = _mapping(head.get("items"))
    for work_id, item in base_items.items():
        if _mapping(item).get("status") == "reviewed" and head_items.get(work_id) != item:
            _issue(issues, "reassessment_transition_terminal", f"reviewed reassessment item is immutable: {work_id}")


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
    head_sessions = list(head.get("sessions") or [])
    if len(head_sessions) != len(base_sessions) + 1 or head_sessions[: len(base_sessions)] != base_sessions:
        _issue(issues, "reassessment_transition_reserve", "reserve must append exactly one session without rewriting history")
    else:
        new_session = _mapping(head_sessions[-1])
        if (
            new_session.get("session_id") != session_id
            or new_session.get("status") != "open"
            or new_session.get("reserved_work_ids") != reserved
        ):
            _issue(issues, "reassessment_transition_reserve", "appended reserve session does not match receipt details")

    changed = _changed_item_ids(base, head)
    if changed != set(reserved):
        _issue(issues, "reassessment_transition_reserve", "reserve may change only the reserved lifecycle items")

    base_items = _mapping(base.get("items"))
    head_items = _mapping(head.get("items"))
    frozen_ids = list(_mapping(base.get("frozen_cohort")).get("work_ids") or [])
    pending = [work_id for work_id in frozen_ids if _mapping(base_items.get(work_id)).get("status") == "pending"]
    eligible = pending if pending else [work_id for work_id in frozen_ids if _mapping(base_items.get(work_id)).get("status") == "deferred"]
    if reserved != eligible[: len(reserved)]:
        _issue(issues, "reassessment_transition_reserve", "reserve work ids are not the next frozen-order eligible prefix")

    for work_id in reserved:
        before = _mapping(base_items.get(work_id)); after = _mapping(head_items.get(work_id))
        if before.get("status") not in {"pending", "deferred"} or after.get("status") != "in_progress" or after.get("session_id") != session_id:
            _issue(issues, "reassessment_transition_reserve", f"illegal reserve lifecycle transition for {work_id}")
        for field in ("reserved_at", "pre_review_feedback_digest", "pre_review_work_file_digest"):
            if not after.get(field):
                _issue(issues, "reassessment_transition_reserve", f"reserved item lacks {field}: {work_id}")
    if base.get("pilot_status") != head.get("pilot_status"):
        _issue(issues, "reassessment_transition_reserve", "reserve may not change pilot_status")
    if base.get("scheduled_reanalysis") != head.get("scheduled_reanalysis"):
        _issue(issues, "reassessment_transition_reserve", "reserve may not change scheduled reanalysis state")


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
    if before.get("status") != "in_progress" or before.get("session_id") != session_id:
        _issue(issues, "reassessment_transition_complete", "complete base item is not reserved by the receipt session")
    if after.get("status") not in {"reviewed", "deferred"}:
        _issue(issues, "reassessment_transition_complete", "complete target must become reviewed or deferred")
    outcome = details.get("outcome")
    if outcome is not None and after.get("outcome") != outcome:
        _issue(issues, "reassessment_transition_complete", "complete lifecycle outcome does not match receipt")
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
    changed_indexes = [index for index, (left, right) in enumerate(zip(base_sessions, head_sessions)) if left != right]
    if len(changed_indexes) != 1:
        _issue(issues, "reassessment_transition_close", "close must change exactly one session")
        return
    index = changed_indexes[0]
    before = _mapping(base_sessions[index]); after = _mapping(head_sessions[index])
    if before.get("session_id") != session_id or after.get("session_id") != session_id or before.get("status") != "open" or after.get("status") != "closed":
        _issue(issues, "reassessment_transition_close", "close must transition the receipt session from open to closed")
    for field in ("session_id", "reserved_work_ids", "opened_at"):
        if before.get(field) != after.get(field):
            _issue(issues, "reassessment_transition_close", f"close may not rewrite session field {field}")
    if not after.get("closed_at") or not isinstance(after.get("snapshot"), Mapping):
        _issue(issues, "reassessment_transition_close", "closed session must add closed_at and snapshot")
    if base.get("pilot_status") == "completed" and head.get("pilot_status") != "completed":
        _issue(issues, "reassessment_transition_close", "completed pilot cannot be reopened")
    if head.get("pilot_status") not in {"active", "completed"}:
        _issue(issues, "reassessment_transition_close", "invalid pilot_status after close")


def validate_reassessment_transition(
    base: Mapping[str, Any],
    head: Mapping[str, Any],
    *,
    operation: str,
    receipt: Mapping[str, Any],
) -> list[ReassessmentSnapshotIssue]:
    """Validate trusted base -> candidate head monotonicity for one typed pilot operation."""
    issues: list[ReassessmentSnapshotIssue] = []
    details = _receipt_details(receipt, operation, issues)

    for key in _IMMUTABLE_TRANSITION_KEYS:
        if base.get(key) != head.get(key):
            _issue(issues, "reassessment_transition_immutable", f"immutable pilot region changed: {key}")

    _validate_terminal_items(base, head, issues)
    _validate_closed_session_history(
        base,
        head,
        operation=operation,
        target_session_id=details.get("session_id") if isinstance(details.get("session_id"), str) else None,
        issues=issues,
    )
    _validate_reanalysis_transition(base, head, operation=operation, issues=issues)

    if operation == "reserve_reassessment_session":
        _validate_reserve_transition(base, head, details, issues)
    elif operation == "complete_reassessment_item":
        _validate_complete_transition(base, head, receipt, details, issues)
    elif operation == "close_reassessment_session":
        _validate_close_transition(base, head, details, issues)
    else:
        _issue(issues, "reassessment_transition_operation", f"unsupported reassessment transition operation: {operation}")

    return issues
