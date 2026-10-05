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
    """Validate single-revision pilot invariants without reinterpreting frozen evidence.

    Schema validation owns structural/type constraints. This layer checks cross-field
    semantics that require the canonical work inventory or comparison across ledger
    regions. It intentionally does not compare current mutable feedback/viewing values
    with the frozen pre-pilot snapshot.
    """

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
