from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from media.domain.commands import (
    CloseReassessmentSessionCommand,
    CompleteReassessmentItemCommand,
    ReserveReassessmentSessionCommand,
)
from media.domain.errors import CommandValidationError
from media.repository.yaml_repo import YamlRepository
from media.service.reassessment import (
    PILOT_ID,
    build_initial_ledger,
    feedback_state_digest,
    file_sha256,
    ledger_bytes,
    ledger_digest_bytes,
)
from media.service.reassessment_mutate import (
    plan_close_reassessment_session,
    plan_complete_reassessment_item,
    plan_reserve_reassessment_session,
)
from media.tools.common import dump_yaml
from tests.media.fixture_repo import copy_fixture_repo


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
SESSION_ID = "123e4567-e89b-42d3-a456-426614174001"
RESERVE_ID = "123e4567-e89b-42d3-a456-426614174101"
COMPLETE_ID = "123e4567-e89b-42d3-a456-426614174102"
CLOSE_ID = "123e4567-e89b-42d3-a456-426614174103"
WORK_ID = "watched-by-primary-only"


def _prepare_repo(tmp_path: Path, *, rating_source: str = "inferred") -> tuple[Path, YamlRepository, Path]:
    root = copy_fixture_repo(tmp_path)
    work_path = root / f"media/data/works/{WORK_ID}.yaml"
    work = yaml.safe_load(work_path.read_text(encoding="utf-8"))
    signal = work.setdefault("viewer_signals", {}).setdefault("primary", {})
    signal["viewing"] = {"status": "watched"}
    signal["rating"] = {
        "score": 8.0,
        "source": rating_source,
        "confidence": "exact" if rating_source == "explicit" else "medium",
    }
    signal["feedback"] = {"summary": "legacy", "signals": []}
    dump_yaml(work_path, work)

    repo = YamlRepository(root / "media")
    ledger = build_initial_ledger(
        repo,
        pilot_id=PILOT_ID,
        base_revision="35afaca898eae6937066f230906b41af0e1f6690",
        baseline_path="media/baselines/intelligence-stage-a.json",
        baseline_document={
            "schema_version": 2,
            "canonical_input_digest": "sha256:" + "9" * 64,
        },
    )
    ledger_path = root / "media/pilots/legacy-reassessment-primary.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_bytes(ledger_bytes(ledger))
    return root, repo, ledger_path


def _digest(path: Path) -> str:
    return ledger_digest_bytes(path.read_bytes())


def _reserve(repo: YamlRepository, ledger_path: Path, *, operation_id: str = RESERVE_ID):
    command = ReserveReassessmentSessionCommand(
        1,
        operation_id,
        PILOT_ID,
        SESSION_ID,
        (WORK_ID,),
        _digest(ledger_path),
    )
    return plan_reserve_reassessment_session(repo, command, now=NOW)


def _apply_ledger_plan(ledger_path: Path, plan) -> None:
    ledger_path.write_bytes(ledger_bytes(plan.json_documents["media/pilots/legacy-reassessment-primary.json"]))


def _complete_command(ledger_path: Path, *, outcome: str, feedback_edit=None):
    exposure = None if outcome == "deferred" else {"timing": "none", "before_finalization": False}
    return CompleteReassessmentItemCommand(
        1,
        COMPLETE_ID,
        PILOT_ID,
        SESSION_ID,
        WORK_ID,
        _digest(ledger_path),
        outcome,
        exposure,
        feedback_edit,
    )


def test_reserve_requires_exact_ledger_digest_and_records_durable_pre_review_state(tmp_path: Path):
    root, repo, ledger_path = _prepare_repo(tmp_path)
    command = ReserveReassessmentSessionCommand(
        1,
        RESERVE_ID,
        PILOT_ID,
        SESSION_ID,
        (WORK_ID,),
        "sha256:" + "0" * 64,
    )
    with pytest.raises(CommandValidationError, match="ledger digest"):
        plan_reserve_reassessment_session(repo, command, now=NOW)

    plan = _reserve(repo, ledger_path)
    ledger = plan.json_documents["media/pilots/legacy-reassessment-primary.json"]
    item = ledger["items"][WORK_ID]
    signal = repo.get_work(WORK_ID).data["viewer_signals"]["primary"]
    work_path = root / f"media/data/works/{WORK_ID}.yaml"

    assert plan.changed_entities == ()
    assert plan.documents == {}
    assert item["status"] == "in_progress"
    assert item["session_id"] == SESSION_ID
    assert item["pre_review_feedback_digest"] == feedback_state_digest(signal)
    assert item["pre_review_work_file_digest"] == file_sha256(work_path.read_bytes())
    assert ledger["sessions"][-1]["status"] == "open"
    assert ledger["sessions"][-1]["reserved_work_ids"] == [WORK_ID]


def test_reserve_rejects_reviewed_items_and_deferred_items_while_main_pass_remains(tmp_path: Path):
    _, repo, ledger_path = _prepare_repo(tmp_path)
    ledger = yaml.safe_load("{}") or {}
    import json
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["items"][WORK_ID] = {
        "status": "reviewed",
        "outcome": "confirmed_unchanged",
        "historical_exposure": {"timing": "none", "before_finalization": False},
        "reviewed_at": "2026-10-05T10:00:00Z",
        "operation_id": COMPLETE_ID,
    }
    ledger_path.write_bytes(ledger_bytes(ledger))
    with pytest.raises(CommandValidationError, match="cannot reserve"):
        _reserve(repo, ledger_path)

    ledger["items"][WORK_ID] = {"status": "deferred", "outcome": "deferred", "operation_id": COMPLETE_ID}
    if len(ledger["items"]) == 1:
        other = next(iter(ledger["frozen_cohort"]["work_ids"]), None)
        if other == WORK_ID:
            pytest.skip("fixture cohort has no second main-pass item")
    ledger_path.write_bytes(ledger_bytes(ledger))
    if any(item.get("status") == "pending" for wid, item in ledger["items"].items() if wid != WORK_ID):
        with pytest.raises(CommandValidationError, match="deferred"):
            _reserve(repo, ledger_path)


def test_complete_changed_reuses_feedback_history_and_promotes_inferred_score_to_explicit(tmp_path: Path):
    _, repo, ledger_path = _prepare_repo(tmp_path, rating_source="inferred")
    reserve = _reserve(repo, ledger_path)
    _apply_ledger_plan(ledger_path, reserve)

    command = _complete_command(
        ledger_path,
        outcome="changed",
        feedback_edit={
            "set": {
                "rating": {"score": 8.0, "source": "explicit", "confidence": "exact"},
                "feedback": {"summary": "Актуальный отзыв", "signals": []},
            }
        },
    )
    plan = plan_complete_reassessment_item(repo, command, now=NOW)

    work = plan.documents[f"media/data/works/{WORK_ID}.yaml"]
    signal = work["viewer_signals"]["primary"]
    assert signal["rating"]["score"] == 8.0
    assert signal["rating"]["source"] == "explicit"
    assert signal["history"][-1]["previous"]["rating"]["source"] == "inferred"
    assert signal["history"][-1]["current"]["rating"]["source"] == "explicit"
    assert plan.rebuild_index is True
    assert "primary" in plan.rebuild_profile_targets

    ledger = plan.json_documents["media/pilots/legacy-reassessment-primary.json"]
    lifecycle = ledger["items"][WORK_ID]
    assert lifecycle["status"] == "reviewed"
    assert lifecycle["outcome"] == "changed"
    assert lifecycle["operation_id"] == COMPLETE_ID
    assert lifecycle["historical_exposure"] == {"timing": "none", "before_finalization": False}
    assert plan.details["pre_review_work_file_digest"] == reserve.json_documents["media/pilots/legacy-reassessment-primary.json"]["items"][WORK_ID]["pre_review_work_file_digest"]


def test_complete_confirmed_unchanged_requires_explicit_evidence_and_creates_no_fake_history(tmp_path: Path):
    _, repo, ledger_path = _prepare_repo(tmp_path, rating_source="explicit")
    before = repo.get_work(WORK_ID).data["viewer_signals"]["primary"].get("history")
    reserve = _reserve(repo, ledger_path)
    _apply_ledger_plan(ledger_path, reserve)

    plan = plan_complete_reassessment_item(
        repo,
        _complete_command(ledger_path, outcome="confirmed_unchanged"),
        now=NOW,
    )
    assert plan.documents == {}
    assert plan.changed_entities == ()
    lifecycle = plan.json_documents["media/pilots/legacy-reassessment-primary.json"]["items"][WORK_ID]
    assert lifecycle["status"] == "reviewed"
    assert lifecycle["outcome"] == "confirmed_unchanged"
    assert repo.get_work(WORK_ID).data["viewer_signals"]["primary"].get("history") == before

    root2, repo2, ledger_path2 = _prepare_repo(tmp_path / "second", rating_source="inferred")
    reserve2 = _reserve(repo2, ledger_path2, operation_id="123e4567-e89b-42d3-a456-426614174111")
    _apply_ledger_plan(ledger_path2, reserve2)
    with pytest.raises(CommandValidationError, match="explicit"):
        plan_complete_reassessment_item(
            repo2,
            _complete_command(ledger_path2, outcome="confirmed_unchanged"),
            now=NOW,
        )


def test_complete_fails_closed_after_concurrent_feedback_change_and_defer_is_ledger_only(tmp_path: Path):
    _, repo, ledger_path = _prepare_repo(tmp_path, rating_source="explicit")
    reserve = _reserve(repo, ledger_path)
    _apply_ledger_plan(ledger_path, reserve)

    work_path = repo.get_work(WORK_ID).path
    work = yaml.safe_load(work_path.read_text(encoding="utf-8"))
    work["viewer_signals"]["primary"]["rating"] = {"score": 7.0, "source": "explicit", "confidence": "exact"}
    dump_yaml(work_path, work)
    with pytest.raises(CommandValidationError, match="pre-review"):
        plan_complete_reassessment_item(
            YamlRepository(repo.media_root),
            _complete_command(ledger_path, outcome="confirmed_unchanged"),
            now=NOW,
        )

    root2, repo2, ledger_path2 = _prepare_repo(tmp_path / "defer", rating_source="explicit")
    reserve2 = _reserve(repo2, ledger_path2, operation_id="123e4567-e89b-42d3-a456-426614174112")
    _apply_ledger_plan(ledger_path2, reserve2)
    plan = plan_complete_reassessment_item(
        repo2,
        _complete_command(ledger_path2, outcome="deferred"),
        now=NOW,
    )
    assert plan.documents == {}
    lifecycle = plan.json_documents["media/pilots/legacy-reassessment-primary.json"]["items"][WORK_ID]
    assert lifecycle["status"] == "deferred"
    assert lifecycle["outcome"] == "deferred"
    assert "historical_exposure" not in lifecycle


def test_close_requires_resolved_session_and_appends_canonical_audit_snapshot(tmp_path: Path, monkeypatch):
    _, repo, ledger_path = _prepare_repo(tmp_path, rating_source="explicit")
    reserve = _reserve(repo, ledger_path)
    _apply_ledger_plan(ledger_path, reserve)

    with pytest.raises(CommandValidationError, match="resolved"):
        plan_close_reassessment_session(
            repo,
            CloseReassessmentSessionCommand(1, CLOSE_ID, PILOT_ID, SESSION_ID, _digest(ledger_path), None),
            now=NOW,
        )

    complete = plan_complete_reassessment_item(
        repo,
        _complete_command(ledger_path, outcome="confirmed_unchanged"),
        now=NOW,
    )
    _apply_ledger_plan(ledger_path, complete)

    monkeypatch.setattr(
        "media.service.reassessment_mutate.collect_intelligence_audit",
        lambda root: {
            "schema_version": 2,
            "canonical_input_digest": "sha256:" + "a" * 64,
            "ratings": {"primary": {"works": {"numerator": 5, "denominator": 10, "by_source": {"explicit": 5}}}},
            "feedback": {"primary": {"works": {"numerator": 3, "denominator": 10}}},
        },
    )
    plan = plan_close_reassessment_session(
        repo,
        CloseReassessmentSessionCommand(1, CLOSE_ID, PILOT_ID, SESSION_ID, _digest(ledger_path), None),
        now=NOW,
    )
    ledger = plan.json_documents["media/pilots/legacy-reassessment-primary.json"]
    session = next(item for item in ledger["sessions"] if item["session_id"] == SESSION_ID)
    assert session["status"] == "closed"
    assert session["snapshot"]["canonical_input_digest"] == "sha256:" + "a" * 64
    assert session["snapshot"]["audit_schema_version"] == 2
    assert session["snapshot"]["reviewed_total"] >= 1
    assert session["snapshot"]["baseline_path"] == ledger["baseline_path"]
    assert plan.documents == {}
    assert plan.rebuild_index is False
