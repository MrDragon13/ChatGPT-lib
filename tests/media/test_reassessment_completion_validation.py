from __future__ import annotations

from copy import deepcopy

from media.service.reassessment_validation import (
    validate_reassessment_snapshot,
    validate_reassessment_transition,
)


SESSION = "123e4567-e89b-42d3-a456-426614174001"
OP = "123e4567-e89b-42d3-a456-426614174010"


def _document(*, phase: str) -> dict:
    return {
        "schema_version": 1,
        "pilot_id": "primary-legacy-v1",
        "pilot_status": "completed",
        "target": "primary",
        "base_revision": "a" * 40,
        "baseline_path": "media/baselines/intelligence-stage-a.json",
        "baseline_schema_version": 2,
        "baseline_canonical_input_digest": "sha256:" + "1" * 64,
        "frozen_cohort": {
            "cohort_revision": "a" * 40,
            "work_ids": ["a"],
            "items": {
                "a": {
                    "viewing_status": "watched",
                    "stratum": "central",
                    "order_key": "sha256:" + "2" * 64,
                    "order_rank": 0,
                    "pre_pilot_feedback_digest": "sha256:" + "3" * 64,
                }
            },
        },
        "items": {
            "a": {
                "status": "deferred",
                "session_id": SESSION,
                "reserved_at": "2026-10-05T12:00:00Z",
                "pre_review_feedback_digest": "sha256:" + "4" * 64,
                "pre_review_work_file_digest": "sha256:" + "5" * 64,
                "outcome": "deferred",
                "operation_id": OP,
            }
        },
        "sessions": [
            {
                "session_id": SESSION,
                "reserved_work_ids": ["a"],
                "status": "closed",
                "phase": phase,
                "opened_at": "2026-10-05T12:00:00Z",
                "closed_at": "2026-10-05T12:10:00Z",
                "snapshot": {"reviewed_total": 0, "deferred_total": 1},
            }
        ],
        "scheduled_reanalysis": {"last_completed": None},
    }


def test_snapshot_completed_pilot_requires_remaining_deferred_items_to_have_deferred_phase_provenance():
    invalid = _document(phase="pending")
    codes = {
        issue.code
        for issue in validate_reassessment_snapshot(invalid, canonical_work_ids={"a"})
    }
    assert "reassessment_incomplete_pilot" in codes

    valid = _document(phase="deferred")
    codes = {
        issue.code
        for issue in validate_reassessment_snapshot(valid, canonical_work_ids={"a"})
    }
    assert "reassessment_incomplete_pilot" not in codes


def test_close_transition_cannot_mark_pilot_completed_until_deferred_stop_condition_is_proven():
    head = _document(phase="pending")
    base = deepcopy(head)
    base["pilot_status"] = "active"
    base["sessions"][0].pop("closed_at")
    base["sessions"][0].pop("snapshot")
    base["sessions"][0]["status"] = "open"

    receipt = {
        "operation_id": "123e4567-e89b-42d3-a456-426614174011",
        "operation": "close_reassessment_session",
        "status": "applied",
        "details": {
            "session_id": SESSION,
            "scheduled_reanalysis_operation_id": None,
        },
    }
    codes = {
        issue.code
        for issue in validate_reassessment_transition(
            base,
            head,
            operation="close_reassessment_session",
            receipt=receipt,
        )
    }
    assert "reassessment_transition_close" in codes
