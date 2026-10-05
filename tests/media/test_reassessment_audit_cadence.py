from __future__ import annotations

from pathlib import Path

from media.service.reassessment import ledger_bytes
from media.service.reassessment_mutate import _scheduled_reanalysis_due
from media.tools.audit_intelligence import canonical_input_digest
from tests.media.fixture_repo import copy_fixture_repo


def test_pilot_ledger_is_explicitly_outside_stage_a_canonical_input_digest(tmp_path: Path):
    root = copy_fixture_repo(tmp_path)
    before = canonical_input_digest(root)

    ledger_path = root / "media/pilots/legacy-reassessment-primary.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_bytes(ledger_bytes({"pilot_id": "primary-legacy-v1", "state": 1}))
    assert canonical_input_digest(root) == before

    ledger_path.write_bytes(ledger_bytes({"pilot_id": "primary-legacy-v1", "state": 2}))
    assert canonical_input_digest(root) == before


def _ledger(*, reviewed: int, pending: int, last_completed: int | None) -> dict:
    work_ids = [f"reviewed-{index}" for index in range(reviewed)] + [
        f"pending-{index}" for index in range(pending)
    ]
    items = {
        work_id: {"status": "reviewed" if work_id.startswith("reviewed-") else "pending"}
        for work_id in work_ids
    }
    last = None
    if last_completed is not None:
        last = {
            "reviewed_count": last_completed,
            "operation_id": "123e4567-e89b-42d3-a456-426614174099",
            "completed_at": "2026-10-05T12:00:00Z",
        }
    return {
        "frozen_cohort": {"work_ids": work_ids},
        "items": items,
        "scheduled_reanalysis": {"last_completed": last},
    }


def test_scheduled_reanalysis_due_every_fifteen_new_reviews_from_persistent_counter():
    assert _scheduled_reanalysis_due(_ledger(reviewed=14, pending=3, last_completed=None)) is False
    assert _scheduled_reanalysis_due(_ledger(reviewed=15, pending=3, last_completed=None)) is True
    assert _scheduled_reanalysis_due(_ledger(reviewed=29, pending=3, last_completed=15)) is False
    assert _scheduled_reanalysis_due(_ledger(reviewed=30, pending=3, last_completed=15)) is True


def test_end_of_main_pending_pass_triggers_reanalysis_only_when_reviewed_count_advanced():
    assert _scheduled_reanalysis_due(_ledger(reviewed=7, pending=0, last_completed=None)) is True
    assert _scheduled_reanalysis_due(_ledger(reviewed=7, pending=0, last_completed=7)) is False
    assert _scheduled_reanalysis_due(_ledger(reviewed=8, pending=0, last_completed=7)) is True


def test_manual_or_unrelated_operation_history_cannot_advance_scheduled_cadence():
    ledger = _ledger(reviewed=15, pending=2, last_completed=None)
    ledger["manual_reanalysis_operation_ids"] = ["123e4567-e89b-42d3-a456-426614174088"]
    assert _scheduled_reanalysis_due(ledger) is True
