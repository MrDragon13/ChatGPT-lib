from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from media.domain.commands import RecordReassessmentModernizationCommand
from media.domain.errors import CommandValidationError
from media.repository.yaml_repo import YamlRepository
from media.service.reassessment import file_sha256, ledger_bytes, ledger_digest_bytes
from media.service.reassessment_mutate import plan_record_reassessment_modernization
from media.tools.common import dump_yaml

NOW = datetime(2026, 10, 7, 1, 0, tzinfo=timezone.utc)
WORK_ID = "movie-a-2020"
MARKER_OP = "123e4567-e89b-42d3-a456-426614174500"
METADATA_OP = "123e4567-e89b-42d3-a456-426614174501"
SEMANTIC_OP = "123e4567-e89b-42d3-a456-426614174502"


def _work():
    return {
        "schema_version": 4,
        "id": WORK_ID,
        "entity_type": "work",
        "identity": {
            "format": "movie",
            "title_original": "Movie A",
            "title_ru": "Movie A",
            "year": 2020,
            "external_ids": {"tmdb": {"media_type": "movie", "id": 10}},
        },
        "metadata": {"external": {}, "semantic": {"traits": []}},
        "viewer_signals": {
            "primary": {
                "viewing": {"status": "watched"},
                "rating": {"score": 8, "source": "explicit", "confidence": "exact"},
            }
        },
        "provenance": {"created_at": "2026-01-01", "updated_at": "2026-10-06"},
    }


def _ledger():
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
            "work_ids": [WORK_ID],
            "items": {
                WORK_ID: {
                    "viewing_status": "watched",
                    "stratum": "central",
                    "order_key": "sha256:" + "2" * 64,
                    "order_rank": 0,
                    "pre_pilot_feedback_digest": "sha256:" + "3" * 64,
                }
            },
        },
        "items": {
            WORK_ID: {
                "status": "reviewed",
                "outcome": "changed",
                "historical_exposure": {"timing": "none", "before_finalization": False},
                "reviewed_at": "2026-10-06T12:00:00Z",
                "operation_id": "123e4567-e89b-42d3-a456-426614174499",
                "session_id": "123e4567-e89b-42d3-a456-426614174498",
            }
        },
        "sessions": [],
        "scheduled_reanalysis": {"last_completed": None},
    }


def _root(tmp_path: Path):
    root = tmp_path / "repo"
    work_path = root / "media/data/works" / f"{WORK_ID}.yaml"
    dump_yaml(work_path, _work())
    dump_yaml(root / "media/vocabulary.yaml", {
        "schema_version": 1,
        "terms": {"story.intrigue": {"kind": "story"}},
    })
    ledger = _ledger()
    ledger_path = root / "media/pilots/legacy-reassessment-primary.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_bytes(ledger_bytes(ledger))
    return root, YamlRepository(root / "media"), ledger


def _receipt(root: Path, operation_id: str, operation: str, applied_at: str, *, status="applied", work_id=WORK_ID):
    path = root / ".media/operations" / f"{operation_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "operation_id": operation_id,
        "operation": operation,
        "status": status,
        "changed_entities": [work_id] if status == "applied" else [],
        "changed_files": [],
        "applied_at": applied_at,
        "details": {"work_id": work_id},
    }), encoding="utf-8")


def _command(root: Path, ledger: dict, *, outcome="completed", blocker_code=None):
    work_digest = file_sha256((root / "media/data/works" / f"{WORK_ID}.yaml").read_bytes())
    kwargs = dict(
        schema_version=1,
        operation_id=MARKER_OP,
        pilot_id="primary-legacy-v1",
        work_id=WORK_ID,
        outcome=outcome,
        expected_ledger_digest=ledger_digest_bytes(ledger_bytes(ledger)),
        expected_work_digest=work_digest,
    )
    if outcome == "completed":
        kwargs.update(
            metadata_operation_id=METADATA_OP,
            semantic_operation_id=SEMANTIC_OP,
            vocabulary_digest=file_sha256((root / "media/vocabulary.yaml").read_bytes()),
        )
    else:
        kwargs["blocker_code"] = blocker_code or "provider_identity_ambiguous"
    return RecordReassessmentModernizationCommand(**kwargs)


def _success_receipts(root: Path, *, metadata_status="applied", semantic_status="applied"):
    _receipt(root, METADATA_OP, "refresh_work_metadata", "2026-10-06T12:10:00Z", status=metadata_status)
    _receipt(root, SEMANTIC_OP, "set_semantic_fingerprint", "2026-10-06T12:20:00Z", status=semantic_status)


def test_completed_modernization_uses_authoritative_receipts_and_preserves_human_item(tmp_path):
    root, repo, ledger = _root(tmp_path)
    _success_receipts(root, metadata_status="no_change", semantic_status="no_change")
    before = deepcopy(ledger["items"][WORK_ID])

    plan = plan_record_reassessment_modernization(root, repo, _command(root, ledger), now=NOW)
    item = plan.json_documents["media/pilots/legacy-reassessment-primary.json"]["items"][WORK_ID]
    assert {k: v for k, v in item.items() if k != "modernization"} == before
    assert item["modernization"] == {
        "status": "completed",
        "metadata_operation_id": METADATA_OP,
        "semantic_operation_id": SEMANTIC_OP,
        "completed_at": "2026-10-07T01:00:00Z",
        "work_digest": _command(root, ledger).expected_work_digest,
        "vocabulary_digest": _command(root, ledger).vocabulary_digest,
    }
    assert plan.documents == {}
    assert plan.details["work_id"] == WORK_ID
    assert plan.details["outcome"] == "completed"
    assert plan.details["modernization"] == item["modernization"]


@pytest.mark.parametrize("mutator,match", [
    (lambda command: command.__class__(**{**command.__dict__, "expected_work_digest": "sha256:" + "0" * 64}), "work digest mismatch"),
    (lambda command: command.__class__(**{**command.__dict__, "expected_ledger_digest": "sha256:" + "0" * 64}), "ledger digest mismatch"),
])
def test_modernization_rejects_stale_digests(tmp_path, mutator, match):
    root, repo, ledger = _root(tmp_path)
    _success_receipts(root)
    with pytest.raises(CommandValidationError, match=match):
        plan_record_reassessment_modernization(root, repo, mutator(_command(root, ledger)), now=NOW)


@pytest.mark.parametrize("case", [
    "metadata_missing",
    "metadata_wrong_operation",
    "metadata_wrong_work",
    "metadata_before_review",
    "semantic_missing",
    "semantic_wrong_operation",
    "semantic_wrong_work",
    "semantic_before_metadata",
    "vocabulary_stale",
])
def test_completed_modernization_rejects_untrusted_or_out_of_order_evidence(tmp_path, case):
    root, repo, ledger = _root(tmp_path)
    command = _command(root, ledger)
    if case != "metadata_missing":
        _receipt(
            root, METADATA_OP,
            "set_semantic_fingerprint" if case == "metadata_wrong_operation" else "refresh_work_metadata",
            "2026-10-06T11:59:00Z" if case == "metadata_before_review" else "2026-10-06T12:10:00Z",
            work_id="other" if case == "metadata_wrong_work" else WORK_ID,
        )
    if case != "semantic_missing":
        _receipt(
            root, SEMANTIC_OP,
            "refresh_work_metadata" if case == "semantic_wrong_operation" else "set_semantic_fingerprint",
            "2026-10-06T12:05:00Z" if case == "semantic_before_metadata" else "2026-10-06T12:20:00Z",
            work_id="other" if case == "semantic_wrong_work" else WORK_ID,
        )
    if case == "vocabulary_stale":
        command = command.__class__(**{**command.__dict__, "vocabulary_digest": "sha256:" + "9" * 64})
    with pytest.raises(CommandValidationError):
        plan_record_reassessment_modernization(root, repo, command, now=NOW)


def test_blocked_modernization_records_controlled_state_without_touching_work(tmp_path):
    root, repo, ledger = _root(tmp_path)
    before_work = (root / "media/data/works" / f"{WORK_ID}.yaml").read_bytes()
    plan = plan_record_reassessment_modernization(
        root, repo, _command(root, ledger, outcome="blocked", blocker_code="provider_identity_conflict"), now=NOW
    )
    item = plan.json_documents["media/pilots/legacy-reassessment-primary.json"]["items"][WORK_ID]
    assert item["modernization"]["status"] == "blocked"
    assert item["modernization"]["blocker_code"] == "provider_identity_conflict"
    assert item["modernization"]["recorded_at"] == "2026-10-07T01:00:00Z"
    assert plan.documents == {}
    assert (root / "media/data/works" / f"{WORK_ID}.yaml").read_bytes() == before_work


def test_blocked_can_advance_to_completed_but_blocked_rewrite_and_completed_rewrite_fail(tmp_path):
    root, repo, ledger = _root(tmp_path)
    blocked_plan = plan_record_reassessment_modernization(root, repo, _command(root, ledger, outcome="blocked"), now=NOW)
    blocked = blocked_plan.json_documents["media/pilots/legacy-reassessment-primary.json"]
    ledger_path = root / "media/pilots/legacy-reassessment-primary.json"
    ledger_path.write_bytes(ledger_bytes(blocked))
    _success_receipts(root)

    completed = plan_record_reassessment_modernization(root, repo, _command(root, blocked), now=NOW)
    assert completed.json_documents["media/pilots/legacy-reassessment-primary.json"]["items"][WORK_ID]["modernization"]["status"] == "completed"

    with pytest.raises(CommandValidationError):
        plan_record_reassessment_modernization(root, repo, _command(root, blocked, outcome="blocked"), now=NOW)

    done = completed.json_documents["media/pilots/legacy-reassessment-primary.json"]
    ledger_path.write_bytes(ledger_bytes(done))
    with pytest.raises(CommandValidationError):
        plan_record_reassessment_modernization(root, repo, _command(root, done, outcome="blocked"), now=NOW)


def test_modernization_requires_reviewed_human_item(tmp_path):
    root, repo, ledger = _root(tmp_path)
    ledger["items"][WORK_ID] = {"status": "pending"}
    (root / "media/pilots/legacy-reassessment-primary.json").write_bytes(ledger_bytes(ledger))
    with pytest.raises(CommandValidationError, match="reviewed"):
        plan_record_reassessment_modernization(root, repo, _command(root, ledger, outcome="blocked"), now=NOW)
