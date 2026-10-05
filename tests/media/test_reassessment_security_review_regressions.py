from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from media.service.reassessment_mutate import _pilot_completion_ready
from media.service.reassessment_validation import validate_reassessment_transition


ROOT = Path(__file__).parents[2]
SESSION = "123e4567-e89b-42d3-a456-426614174001"
OTHER_SESSION = "123e4567-e89b-42d3-a456-426614174002"
OP = "123e4567-e89b-42d3-a456-426614174010"
REANALYSIS = "123e4567-e89b-42d3-a456-426614174020"


def _base() -> dict:
    return {
        "schema_version": 1,
        "pilot_id": "primary-legacy-v1",
        "pilot_status": "active",
        "target": "primary",
        "base_revision": "a" * 40,
        "baseline_path": "media/baselines/intelligence-stage-a.json",
        "baseline_schema_version": 2,
        "baseline_canonical_input_digest": "sha256:" + "1" * 64,
        "frozen_cohort": {
            "cohort_revision": "a" * 40,
            "work_ids": ["a", "b"],
            "items": {
                "a": {"viewing_status": "watched", "stratum": "central", "order_key": "sha256:" + "2" * 64, "order_rank": 0, "pre_pilot_feedback_digest": "sha256:" + "3" * 64},
                "b": {"viewing_status": "watched", "stratum": "high", "order_key": "sha256:" + "4" * 64, "order_rank": 1, "pre_pilot_feedback_digest": "sha256:" + "5" * 64},
            },
        },
        "items": {"a": {"status": "pending"}, "b": {"status": "pending"}},
        "sessions": [],
        "scheduled_reanalysis": {"last_completed": None},
    }


def _receipt(operation: str, **details) -> dict:
    return {"operation_id": OP, "operation": operation, "status": "applied", "details": details}


def _codes(base: dict, head: dict, operation: str, **details) -> set[str]:
    return {
        issue.code
        for issue in validate_reassessment_transition(
            base,
            head,
            operation=operation,
            receipt=_receipt(operation, **details),
        )
    }


def _reserved_base() -> dict:
    base = _base()
    base["items"]["a"] = {
        "status": "in_progress",
        "session_id": SESSION,
        "reserved_at": "2026-10-05T12:00:00Z",
        "pre_review_feedback_digest": "sha256:" + "6" * 64,
        "pre_review_work_file_digest": "sha256:" + "7" * 64,
    }
    base["sessions"] = [{
        "session_id": SESSION,
        "reserved_work_ids": ["a"],
        "status": "open",
        "phase": "pending",
        "opened_at": "2026-10-05T12:00:00Z",
    }]
    return base


def test_transition_reserve_rejects_second_open_session_and_duplicate_session_id():
    base = _base()
    base["sessions"] = [{
        "session_id": OTHER_SESSION,
        "reserved_work_ids": ["b"],
        "status": "open",
        "phase": "pending",
        "opened_at": "2026-10-05T11:00:00Z",
    }]
    head = deepcopy(base)
    head["items"]["a"] = {
        "status": "in_progress",
        "session_id": SESSION,
        "reserved_at": "2026-10-05T12:00:00Z",
        "pre_review_feedback_digest": "sha256:" + "6" * 64,
        "pre_review_work_file_digest": "sha256:" + "7" * 64,
    }
    head["sessions"].append({
        "session_id": SESSION,
        "reserved_work_ids": ["a"],
        "status": "open",
        "phase": "pending",
        "opened_at": "2026-10-05T12:00:00Z",
    })
    assert "reassessment_transition_reserve" in _codes(
        base, head, "reserve_reassessment_session", session_id=SESSION, reserved_work_ids=["a"], phase="pending"
    )

    base = _base()
    base["sessions"] = [{
        "session_id": SESSION,
        "reserved_work_ids": ["b"],
        "status": "closed",
        "phase": "pending",
        "opened_at": "2026-10-05T10:00:00Z",
        "closed_at": "2026-10-05T10:10:00Z",
        "snapshot": {},
    }]
    head = deepcopy(base)
    head["items"]["a"] = {
        "status": "in_progress",
        "session_id": SESSION,
        "reserved_at": "2026-10-05T12:00:00Z",
        "pre_review_feedback_digest": "sha256:" + "6" * 64,
        "pre_review_work_file_digest": "sha256:" + "7" * 64,
    }
    head["sessions"].append({
        "session_id": SESSION,
        "reserved_work_ids": ["a"],
        "status": "open",
        "phase": "pending",
        "opened_at": "2026-10-05T12:00:00Z",
    })
    assert "reassessment_transition_reserve" in _codes(
        base, head, "reserve_reassessment_session", session_id=SESSION, reserved_work_ids=["a"], phase="pending"
    )


def test_transition_complete_requires_session_membership_and_status_outcome_consistency():
    base = _reserved_base()
    base["sessions"][0]["reserved_work_ids"] = ["b"]
    head = deepcopy(base)
    head["items"]["a"] = {
        **head["items"]["a"],
        "status": "reviewed",
        "outcome": "confirmed_unchanged",
        "historical_exposure": {"timing": "none", "before_finalization": False},
        "reviewed_at": "2026-10-05T12:05:00Z",
        "operation_id": OP,
    }
    assert "reassessment_transition_complete" in _codes(
        base, head, "complete_reassessment_item", session_id=SESSION, work_id="a", outcome="confirmed_unchanged"
    )

    base = _reserved_base()
    head = deepcopy(base)
    head["items"]["a"] = {
        **head["items"]["a"],
        "status": "deferred",
        "outcome": "changed",
        "operation_id": OP,
    }
    assert "reassessment_transition_complete" in _codes(
        base, head, "complete_reassessment_item", session_id=SESSION, work_id="a", outcome="changed"
    )


def test_transition_close_requires_scheduled_reanalysis_operation_id_to_match_head_state():
    base = _reserved_base()
    base["items"]["a"] = {
        **base["items"]["a"],
        "status": "reviewed",
        "outcome": "changed",
        "historical_exposure": {"timing": "none", "before_finalization": False},
        "reviewed_at": "2026-10-05T12:05:00Z",
        "operation_id": OP,
    }
    head = deepcopy(base)
    head["sessions"][0] = {
        **head["sessions"][0],
        "status": "closed",
        "closed_at": "2026-10-05T12:10:00Z",
        "snapshot": {"reviewed_total": 1, "deferred_total": 0},
    }
    head["scheduled_reanalysis"]["last_completed"] = {
        "reviewed_count": 1,
        "operation_id": REANALYSIS,
        "completed_at": "2026-10-05T12:09:00Z",
    }
    assert "reassessment_transition_reanalysis" in _codes(
        base,
        head,
        "close_reassessment_session",
        session_id=SESSION,
        scheduled_reanalysis_operation_id="123e4567-e89b-42d3-a456-426614174099",
    )


def test_pilot_completion_waits_until_every_remaining_deferred_item_was_explicitly_left_in_deferred_pass():
    document = _base()
    document["items"] = {
        "a": {"status": "deferred", "session_id": SESSION, "outcome": "deferred", "operation_id": OP},
        "b": {"status": "reviewed", "outcome": "changed", "historical_exposure": {"timing": "none", "before_finalization": False}, "reviewed_at": "2026-10-05T12:00:00Z", "operation_id": OP},
    }
    document["sessions"] = [{
        "session_id": SESSION,
        "reserved_work_ids": ["a"],
        "status": "closed",
        "phase": "pending",
        "opened_at": "2026-10-05T11:00:00Z",
        "closed_at": "2026-10-05T11:10:00Z",
        "snapshot": {},
    }]
    assert _pilot_completion_ready(document) is False

    document["sessions"][0]["phase"] = "deferred"
    assert _pilot_completion_ready(document) is True


def test_workflow_requires_trusted_main_base_and_reserve_work_digest_without_embedded_operation_case():
    check = (ROOT / ".github/workflows/media-check.yml").read_text(encoding="utf-8")
    auto = (ROOT / ".github/workflows/media-auto-merge.yml").read_text(encoding="utf-8")

    base_block = check.split("base_sha:", 1)[1].split("permissions:", 1)[0]
    assert "required: true" in base_block
    assert "git fetch origin main" in check
    assert "git merge-base --is-ancestor" in check
    assert "expected_ledger_digest" in check
    assert "Base ledger digest does not match operation receipt" in check

    assert 'case "$OP_KIND" in' not in auto
    assert "reserved_items" in auto
    assert "Stale reserved work during reassessment reservation" in auto
