from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from media.commands.schema import parse_command
from media.domain.changeset import MutationPlan
from media.domain.errors import PathPolicyError, TransactionValidationError
from media.service.path_policy import verify_changed_paths
from media.service.transaction import execute_command, preview_command
from tests.media.fixture_repo import copy_fixture_repo

UUID = "123e4567-e89b-42d3-a456-426614174010"


def command(term=None):
    update = {"target": "primary", "viewing": {"status": "partial"}}
    if term:
        update["feedback"] = {
            "summary": "x",
            "signals": [
                {
                    "term": term,
                    "sentiment": "negative",
                    "strength": 2,
                    "source": "explicit",
                    "confidence": "high",
                }
            ],
        }
    return parse_command(
        {
            "schema_version": 1,
            "operation_id": UUID,
            "operation": "record_viewing_feedback",
            "work_ref": {"id": "arrival-2016"},
            "target_updates": [update],
        }
    )


def snapshot(root: Path):
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _fake_command(operation_id: str = UUID):
    return SimpleNamespace(operation_id=operation_id)


def _plan(*, json_documents=None):
    return SimpleNamespace(
        operation_id=UUID,
        operation="record_viewing_feedback",
        changed_entities=(),
        documents={},
        json_documents=json_documents or {},
        rebuild_index=False,
        rebuild_profile_targets=(),
        details={},
        jsonl_appends={},
    )


def test_json_only_plan_is_planned_and_applied_with_deterministic_json(tmp_path, monkeypatch):
    root = copy_fixture_repo(tmp_path)
    json_path = "media/pilots/test-ledger.json"
    plan = _plan(json_documents={json_path: {"z": 1, "a": "é"}})

    monkeypatch.setattr("media.service.transaction._plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr("media.service.transaction.verify_changed_paths", lambda *args, **kwargs: None)

    preview = preview_command(root, _fake_command())
    assert preview.status == "planned"
    assert preview.changed_files == (json_path,)

    result = execute_command(root, _fake_command(), now=datetime(2026, 10, 1, tzinfo=timezone.utc))
    assert result.status == "applied"
    assert json_path in result.changed_files
    assert (root / json_path).read_bytes() == '{\n  "a": "é",\n  "z": 1\n}\n'.encode("utf-8")


def test_empty_plan_remains_no_change(tmp_path, monkeypatch):
    root = copy_fixture_repo(tmp_path)
    plan = _plan()

    monkeypatch.setattr("media.service.transaction._plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr("media.service.transaction.verify_changed_paths", lambda *args, **kwargs: None)

    result = execute_command(root, _fake_command(), now=datetime(2026, 10, 1, tzinfo=timezone.utc))
    assert result.status == "no_change"


def test_same_operation_id_returns_already_applied_without_second_effect(tmp_path):
    root = copy_fixture_repo(tmp_path)
    cmd = command()
    first = execute_command(root, cmd, now=datetime(2026, 10, 1, tzinfo=timezone.utc))
    after = snapshot(root)
    second = execute_command(root, cmd, now=datetime(2026, 10, 2, tzinfo=timezone.utc))
    assert first.status == "applied"
    assert second.status == "already_applied"
    assert snapshot(root) == after


def test_invalid_vocabulary_term_leaves_original_tree_byte_identical(tmp_path):
    root = copy_fixture_repo(tmp_path)
    before = snapshot(root)
    with pytest.raises(TransactionValidationError):
        execute_command(root, command("missing.term"), now=datetime(2026, 10, 1, tzinfo=timezone.utc))
    assert snapshot(root) == before


def test_path_policy_rejects_schema_and_service_paths():
    with pytest.raises(PathPolicyError):
        verify_changed_paths("record_viewing_feedback", ["media/schemas/work.schema.json"])
    with pytest.raises(PathPolicyError):
        verify_changed_paths("record_viewing_feedback", ["media/service/mutate.py"])
    verify_changed_paths(
        "record_viewing_feedback",
        [
            "media/data/works/arrival-2016.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/primary.yaml",
        ],
    )
