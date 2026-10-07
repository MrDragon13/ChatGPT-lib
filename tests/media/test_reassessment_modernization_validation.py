from __future__ import annotations

from copy import deepcopy

from media.service.reassessment_validation import validate_reassessment_snapshot, validate_reassessment_transition

OP = "123e4567-e89b-42d3-a456-426614174600"
WORK = "movie-a"


def _base():
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
            "work_ids": [WORK],
            "items": {WORK: {
                "viewing_status": "watched",
                "stratum": "central",
                "order_key": "sha256:" + "e" * 64,
                "order_rank": 0,
                "pre_pilot_feedback_digest": "sha256:" + "2" * 64,
            }},
        },
        "items": {WORK: {
            "status": "reviewed",
            "outcome": "changed",
            "historical_exposure": {"timing": "none", "before_finalization": False},
            "reviewed_at": "2026-10-06T12:00:00Z",
            "operation_id": "123e4567-e89b-42d3-a456-426614174599",
        }},
        "sessions": [],
        "scheduled_reanalysis": {"last_completed": None},
    }


def _receipt(outcome, modernization):
    return {
        "operation_id": OP,
        "operation": "record_reassessment_modernization",
        "status": "applied",
        "details": {
            "work_id": WORK,
            "outcome": outcome,
            "expected_ledger_digest": "sha256:" + "3" * 64,
            "expected_work_digest": "sha256:" + "4" * 64,
            "modernization": modernization,
        },
    }


def _codes(base, head, outcome, modernization):
    return {i.code for i in validate_reassessment_transition(
        base, head, operation="record_reassessment_modernization", receipt=_receipt(outcome, modernization)
    )}


def test_snapshot_accepts_valid_completed_and_blocked_modernization():
    for modernization in (
        {
            "status": "blocked",
            "blocker_code": "provider_identity_ambiguous",
            "recorded_at": "2026-10-07T01:00:00Z",
            "work_digest": "sha256:" + "4" * 64,
        },
        {
            "status": "completed",
            "metadata_operation_id": "123e4567-e89b-42d3-a456-426614174601",
            "semantic_operation_id": "123e4567-e89b-42d3-a456-426614174602",
            "completed_at": "2026-10-07T01:00:00Z",
            "work_digest": "sha256:" + "4" * 64,
            "vocabulary_digest": "sha256:" + "5" * 64,
        },
    ):
        doc = _base(); doc["items"][WORK]["modernization"] = modernization
        assert not {i.code for i in validate_reassessment_snapshot(doc, canonical_work_ids={WORK}) if "modernization" in i.code}


def test_snapshot_rejects_modernization_on_nonreviewed_or_malformed_record():
    doc = _base()
    doc["items"][WORK] = {
        "status": "pending",
        "modernization": {"status": "blocked", "blocker_code": "anything", "recorded_at": ""},
    }
    codes = {i.code for i in validate_reassessment_snapshot(doc, canonical_work_ids={WORK})}
    assert "reassessment_modernization" in codes


def test_transition_allows_absent_to_blocked_and_blocked_to_completed_while_preserving_human_fields():
    base = _base()
    blocked = {
        "status": "blocked",
        "blocker_code": "provider_identity_ambiguous",
        "recorded_at": "2026-10-07T01:00:00Z",
        "work_digest": "sha256:" + "4" * 64,
    }
    head = deepcopy(base); head["items"][WORK]["modernization"] = blocked
    assert _codes(base, head, "blocked", blocked) == set()

    completed = {
        "status": "completed",
        "metadata_operation_id": "123e4567-e89b-42d3-a456-426614174601",
        "semantic_operation_id": "123e4567-e89b-42d3-a456-426614174602",
        "completed_at": "2026-10-07T02:00:00Z",
        "work_digest": "sha256:" + "4" * 64,
        "vocabulary_digest": "sha256:" + "5" * 64,
    }
    done = deepcopy(head); done["items"][WORK]["modernization"] = completed
    assert _codes(head, done, "completed", completed) == set()


def test_transition_rejects_blocked_rewrite_completed_rewrite_and_human_field_changes():
    blocked = {
        "status": "blocked", "blocker_code": "provider_identity_ambiguous",
        "recorded_at": "2026-10-07T01:00:00Z", "work_digest": "sha256:" + "4" * 64,
    }
    base = _base(); base["items"][WORK]["modernization"] = blocked
    rewrite = deepcopy(base); rewrite["items"][WORK]["modernization"]["recorded_at"] = "2026-10-07T03:00:00Z"
    assert "reassessment_transition_modernization" in _codes(base, rewrite, "blocked", rewrite["items"][WORK]["modernization"])

    completed = {
        "status": "completed",
        "metadata_operation_id": "123e4567-e89b-42d3-a456-426614174601",
        "semantic_operation_id": "123e4567-e89b-42d3-a456-426614174602",
        "completed_at": "2026-10-07T02:00:00Z",
        "work_digest": "sha256:" + "4" * 64,
        "vocabulary_digest": "sha256:" + "5" * 64,
    }
    done = _base(); done["items"][WORK]["modernization"] = completed
    rewrite_done = deepcopy(done); rewrite_done["items"][WORK]["modernization"]["completed_at"] = "2026-10-07T04:00:00Z"
    assert "reassessment_transition_modernization" in _codes(done, rewrite_done, "completed", rewrite_done["items"][WORK]["modernization"])

    head = deepcopy(_base()); head["items"][WORK]["outcome"] = "confirmed_unchanged"; head["items"][WORK]["modernization"] = blocked
    assert "reassessment_transition_modernization" in _codes(_base(), head, "blocked", blocked)
