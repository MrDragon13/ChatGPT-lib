from __future__ import annotations

from media.commands.schema import parse_command


UUID = "123e4567-e89b-42d3-a456-426614174000"
SESSION = "123e4567-e89b-42d3-a456-426614174001"
DIGEST = "sha256:" + "a" * 64


def test_reviewed_reassessment_allows_unexposed_final_evidence():
    command = parse_command(
        {
            "schema_version": 1,
            "operation_id": UUID,
            "operation": "complete_reassessment_item",
            "pilot_id": "primary-legacy-v1",
            "session_id": SESSION,
            "work_id": "arrival-2016",
            "expected_ledger_digest": DIGEST,
            "outcome": "confirmed_unchanged",
            "historical_exposure": {
                "timing": "none",
                "before_finalization": False,
            },
        }
    )

    assert command.historical_exposure == {
        "timing": "none",
        "before_finalization": False,
    }


def test_changed_reassessment_allows_history_only_after_finalization():
    command = parse_command(
        {
            "schema_version": 1,
            "operation_id": UUID,
            "operation": "complete_reassessment_item",
            "pilot_id": "primary-legacy-v1",
            "session_id": SESSION,
            "work_id": "arrival-2016",
            "expected_ledger_digest": DIGEST,
            "outcome": "changed",
            "historical_exposure": {
                "timing": "after_initial_response",
                "before_finalization": False,
            },
            "feedback_edit": {
                "set": {
                    "rating": {
                        "score": 8.5,
                        "source": "explicit",
                        "confidence": "exact",
                    }
                }
            },
        }
    )

    assert command.historical_exposure["before_finalization"] is False
