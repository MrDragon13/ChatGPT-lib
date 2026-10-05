from __future__ import annotations

from copy import deepcopy

from media.service.reassessment_validation import validate_reassessment_transition


SESSION = "123e4567-e89b-42d3-a456-426614174001"
OP = "123e4567-e89b-42d3-a456-426614174010"


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
    return {issue.code for issue in validate_reassessment_transition(base, head, operation=operation, receipt=_receipt(operation, **details))}


def _reserved() -> tuple[dict, dict]:
    base = _base(); head = deepcopy(base)
    head["items"]["a"] = {
        "status": "in_progress",
        "session_id": SESSION,
        "reserved_at": "2026-10-05T12:00:00Z",
        "pre_review_feedback_digest": "sha256:" + "6" * 64,
        "pre_review_work_file_digest": "sha256:" + "7" * 64,
    }
    head["sessions"].append({"session_id": SESSION, "reserved_work_ids": ["a"], "status": "open", "opened_at": "2026-10-05T12:00:00Z"})
    return base, head


def test_transition_rejects_frozen_or_baseline_mutation():
    for mutate in (
        lambda head: head.__setitem__("base_revision", "b" * 40),
        lambda head: head.__setitem__("baseline_path", "other.json"),
        lambda head: head["frozen_cohort"]["items"]["a"].__setitem__("order_rank", 9),
        lambda head: head["frozen_cohort"]["items"]["a"].__setitem__("pre_pilot_feedback_digest", "sha256:" + "9" * 64),
    ):
        base, head = _reserved(); mutate(head)
        assert "reassessment_transition_immutable" in _codes(base, head, "reserve_reassessment_session", session_id=SESSION, reserved_work_ids=["a"])


def test_valid_reserve_appends_one_open_session_and_moves_only_requested_items_to_in_progress():
    base, head = _reserved()
    assert _codes(base, head, "reserve_reassessment_session", session_id=SESSION, reserved_work_ids=["a"]) == set()

    bad = deepcopy(head); bad["items"]["b"] = deepcopy(bad["items"]["a"])
    assert "reassessment_transition_reserve" in _codes(base, bad, "reserve_reassessment_session", session_id=SESSION, reserved_work_ids=["a"])


def test_reviewed_item_is_globally_terminal_and_cannot_reopen_or_rewrite_provenance():
    base = _base()
    terminal = {"status": "reviewed", "outcome": "changed", "historical_exposure": {"timing": "none", "before_finalization": False}, "reviewed_at": "2026-10-05T12:00:00Z", "operation_id": OP}
    base["items"]["a"] = terminal
    for replacement in (
        {"status": "pending"},
        {**terminal, "outcome": "confirmed_unchanged"},
        {**terminal, "reviewed_at": "2026-10-05T13:00:00Z"},
        {**terminal, "historical_exposure": {"timing": "before_initial_response", "before_finalization": True}},
    ):
        head = deepcopy(base); head["items"]["a"] = replacement
        assert "reassessment_transition_terminal" in _codes(base, head, "complete_reassessment_item", session_id=SESSION, work_id="b")


def test_valid_complete_changes_exactly_one_reserved_item_and_preserves_sessions():
    base, reserved = _reserved()
    base = reserved
    head = deepcopy(base)
    head["items"]["a"] = {
        **head["items"]["a"],
        "status": "reviewed",
        "outcome": "confirmed_unchanged",
        "historical_exposure": {"timing": "none", "before_finalization": False},
        "reviewed_at": "2026-10-05T12:05:00Z",
        "operation_id": OP,
    }
    assert _codes(base, head, "complete_reassessment_item", session_id=SESSION, work_id="a", outcome="confirmed_unchanged") == set()

    bad = deepcopy(head); bad["sessions"][0]["reserved_work_ids"].append("b")
    assert "reassessment_transition_complete" in _codes(base, bad, "complete_reassessment_item", session_id=SESSION, work_id="a")


def test_closed_session_snapshot_is_immutable_across_later_operations():
    base = _base()
    base["sessions"] = [{"session_id": SESSION, "reserved_work_ids": ["a"], "status": "closed", "opened_at": "2026-10-05T12:00:00Z", "closed_at": "2026-10-05T12:10:00Z", "snapshot": {"reviewed_total": 1, "deferred_total": 0}}]
    head = deepcopy(base); head["sessions"][0]["snapshot"]["reviewed_total"] = 2
    assert "reassessment_transition_closed_session" in _codes(base, head, "reserve_reassessment_session", session_id="123e4567-e89b-42d3-a456-426614174002", reserved_work_ids=["b"])


def test_valid_close_changes_no_items_closes_one_open_session_and_may_advance_reanalysis():
    _, base = _reserved()
    base["items"]["a"] = {**base["items"]["a"], "status": "reviewed", "outcome": "changed", "historical_exposure": {"timing": "none", "before_finalization": False}, "reviewed_at": "2026-10-05T12:05:00Z", "operation_id": OP}
    head = deepcopy(base)
    head["sessions"][0] = {**head["sessions"][0], "status": "closed", "closed_at": "2026-10-05T12:10:00Z", "snapshot": {"reviewed_total": 1, "deferred_total": 0}}
    head["scheduled_reanalysis"]["last_completed"] = {"reviewed_count": 1, "operation_id": "123e4567-e89b-42d3-a456-426614174020", "completed_at": "2026-10-05T12:09:00Z"}
    assert _codes(base, head, "close_reassessment_session", session_id=SESSION, scheduled_reanalysis_operation_id="123e4567-e89b-42d3-a456-426614174020") == set()

    bad = deepcopy(head); bad["items"]["b"] = {"status": "deferred"}
    assert "reassessment_transition_close" in _codes(base, bad, "close_reassessment_session", session_id=SESSION)


def test_scheduled_reanalysis_state_cannot_move_backwards_or_be_changed_by_non_close_operation():
    base = _base(); base["scheduled_reanalysis"]["last_completed"] = {"reviewed_count": 15, "operation_id": OP, "completed_at": "2026-10-05T12:00:00Z"}
    head = deepcopy(base); head["scheduled_reanalysis"]["last_completed"] = None
    assert "reassessment_transition_reanalysis" in _codes(base, head, "complete_reassessment_item", session_id=SESSION, work_id="a")

    head = deepcopy(base); head["scheduled_reanalysis"]["last_completed"] = {"reviewed_count": 14, "operation_id": "123e4567-e89b-42d3-a456-426614174099", "completed_at": "2026-10-05T13:00:00Z"}
    assert "reassessment_transition_reanalysis" in _codes(base, head, "close_reassessment_session", session_id=SESSION)
