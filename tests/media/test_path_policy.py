from pathlib import Path

import json
import pytest

from media.domain.errors import PathPolicyError
import media.service.path_policy as path_policy
from media.service.path_policy import allowed_paths_for_operation, verify_changed_paths


EXPECTED_POLICY = {
    "add_work": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
            "media/data/relations/similarity/*.yaml",
        ],
    },
    "record_viewing_feedback": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
            "media/data/relations/similarity/*.yaml",
        ],
    },
    "edit_viewing_feedback": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "set_interest": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "refresh_metadata": {
        "auto_merge": False,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "set_semantic_fingerprint": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/works/*.yaml",
            "media/generated/index.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "set_inferred_preferences": {
        "auto_merge": True,
        "allowed_paths": [
            "media/preferences/inferred/*.yaml",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "record_recommendation_interaction": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/interactions/*.jsonl",
            "media/generated/profiles/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "set_work_similarity": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/relations/similarity/*.yaml",
            ".media/operations/*.json",
        ],
    },
    "remove_work_similarity": {
        "auto_merge": True,
        "allowed_paths": [
            "media/data/relations/similarity/*.yaml",
            ".media/operations/*.json",
        ],
    },
}


def _policy_path() -> Path:
    return Path(path_policy.__file__).resolve().parents[1] / "config" / "operation_path_policy.json"


def test_declarative_policy_document_is_the_complete_operation_contract():
    policy=json.loads(_policy_path().read_text(encoding="utf-8"))
    assert policy=={"schema_version":1,"operations":EXPECTED_POLICY}
    for operation, entry in EXPECTED_POLICY.items():
        assert allowed_paths_for_operation(operation)==tuple(entry["allowed_paths"])


def test_set_inferred_preferences_runtime_scope_excludes_generated_index():
    allowed_paths_for_operation("set_inferred_preferences")
    verify_changed_paths("set_inferred_preferences",[
        "media/preferences/inferred/primary.yaml",
        "media/generated/profiles/primary.yaml",
        ".media/operations/123e4567-e89b-42d3-a456-426614174001.json",
    ])
    with pytest.raises(PathPolicyError):
        verify_changed_paths("set_inferred_preferences",["media/generated/index.jsonl"])


def test_missing_policy_file_fails_closed(tmp_path,monkeypatch):
    monkeypatch.setattr(path_policy,"_POLICY_PATH",tmp_path/"missing.json",raising=False)
    with pytest.raises(PathPolicyError):
        allowed_paths_for_operation("set_interest")


@pytest.mark.parametrize("document",[
    {},
    {"schema_version":2,"operations":EXPECTED_POLICY},
    {"schema_version":1,"operations":[]},
    {"schema_version":1,"operations":{"set_interest":{"auto_merge":True,"allowed_paths":[]}}},
])
def test_malformed_policy_fails_closed(tmp_path,monkeypatch,document):
    policy=tmp_path/"policy.json"
    policy.write_text(json.dumps(document),encoding="utf-8")
    monkeypatch.setattr(path_policy,"_POLICY_PATH",policy,raising=False)
    with pytest.raises(PathPolicyError):
        allowed_paths_for_operation("set_interest")


def test_unknown_operation_fails_closed():
    assert allowed_paths_for_operation("ghost") == ()
    with pytest.raises(PathPolicyError):
        verify_changed_paths("ghost",["media/data/works/arrival-2016.yaml"])


def test_normal_operations_reject_policy_workflow_service_tooling_and_guard_paths():
    protected=(
        "media/config/operation_path_policy.json",
        ".github/workflows/media-auto-merge.yml",
        "media/service/path_policy.py",
        "media/tools/rebuild.py",
        "tests/media/test_path_policy.py",
        "tests/media/test_auto_merge_dispatch_contract.py",
    )
    for operation,entry in EXPECTED_POLICY.items():
        if not entry["auto_merge"]:
            continue
        for path in protected:
            with pytest.raises(PathPolicyError):
                verify_changed_paths(operation,[path])


def test_edit_feedback_allows_only_work_generated_and_receipt_paths():
    verify_changed_paths("edit_viewing_feedback", [
        "media/data/works/arrival-2016.yaml",
        "media/generated/index.jsonl",
        "media/generated/profiles/primary.yaml",
        ".media/operations/123e4567-e89b-42d3-a456-426614174001.json",
    ])
    with pytest.raises(PathPolicyError):
        verify_changed_paths("edit_viewing_feedback", ["media/preferences/inferred/primary.yaml"])


def test_existing_feedback_operation_cannot_modify_future_intelligence_paths():
    for path in (
        "media/preferences/inferred/primary.yaml",
        "media/data/interactions/2026-10.jsonl",
    ):
        with pytest.raises(PathPolicyError):
            verify_changed_paths("record_viewing_feedback", [path])


def test_similarity_operations_allow_only_relation_and_receipt_paths():
    allowed = [
        "media/data/relations/similarity/primary.yaml",
        ".media/operations/123e4567-e89b-42d3-a456-426614174040.json",
    ]
    verify_changed_paths("set_work_similarity", allowed)
    verify_changed_paths("remove_work_similarity", allowed)

    for operation in ("set_work_similarity", "remove_work_similarity"):
        for forbidden in (
            "media/data/works/arrival-2016.yaml",
            "media/generated/index.jsonl",
            "media/preferences/inferred/primary.yaml",
        ):
            with pytest.raises(PathPolicyError):
                verify_changed_paths(operation, [forbidden])


def test_work_creation_paths_allow_similarity_reconciliation_but_regular_edits_do_not():
    relation_path = "media/data/relations/similarity/primary.yaml"
    verify_changed_paths("add_work", [relation_path])
    verify_changed_paths("record_viewing_feedback", [relation_path])

    for operation in ("edit_viewing_feedback", "set_interest", "set_semantic_fingerprint"):
        with pytest.raises(PathPolicyError):
            verify_changed_paths(operation, [relation_path])
